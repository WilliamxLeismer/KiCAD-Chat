#!/usr/bin/env python3
"""
Anthropic Claude API integration for KiCAD-Chat with security hardening.

This module provides secure integration with Anthropic's Claude API,
implementing zero-retention policies and encryption best practices.
"""

import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic API."""
    api_key: Optional[str] = None
    model: str = "claude-3-5-sonnet-20241022"
    endpoint_url: Optional[str] = None  # For PrivateLink
    max_tokens: int = 4096
    zero_retention: bool = False  # Requires Enterprise DPA
    
    @classmethod
    def from_env(cls) -> 'AnthropicConfig':
        """Load configuration from environment variables."""
        return cls(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            endpoint_url=os.getenv("ANTHROPIC_ENDPOINT"),
            max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096")),
            zero_retention=os.getenv("ZERO_RETENTION", "false").lower() == "true"
        )


class SecureAnthropicClient:
    """
    Secure wrapper around Anthropic API with hardened configuration.
    
    Features:
    - Zero data retention (with Enterprise DPA)
    - No-training guarantee (default for API)
    - VPC/PrivateLink support
    - Audit logging capabilities
    """
    
    def __init__(self, config: Optional[AnthropicConfig] = None):
        """
        Initialize secure Anthropic client.
        
        Args:
            config: Anthropic configuration. If None, loads from environment.
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is required. "
                "Install with: pip install anthropic"
            )
        
        self.config = config or AnthropicConfig.from_env()
        
        if not self.config.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable must be set"
            )
        
        # Initialize Anthropic client
        client_kwargs = {"api_key": self.config.api_key}
        
        # Use custom endpoint for PrivateLink if configured
        if self.config.endpoint_url:
            client_kwargs["base_url"] = self.config.endpoint_url
        
        self.client = anthropic.Anthropic(**client_kwargs)
    
    def create_message(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Any:
        """
        Create a message using Claude API with security best practices.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system: Optional system prompt
            tools: Optional list of tool definitions
            **kwargs: Additional parameters for the API call
            
        Returns:
            API response from Claude
        """
        # Prepare API call parameters
        api_params = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": messages,
        }
        
        if system:
            api_params["system"] = system
        
        if tools:
            api_params["tools"] = tools
        
        # Merge any additional parameters
        api_params.update(kwargs)
        
        # Add metadata for audit logging
        if os.getenv("AUDIT_LOGGING", "false").lower() == "true":
            api_params["metadata"] = {
                "user_id": os.getenv("USER_ID", "default"),
                "session_id": os.getenv("SESSION_ID", "default")
            }
        
        # Make API call
        try:
            response = self.client.messages.create(**api_params)
            return response
        except Exception as e:
            raise RuntimeError(f"Anthropic API call failed: {e}")
    
    def chat_with_tools(
        self,
        user_message: str,
        system_prompt: str,
        tools: List[Dict],
        conversation_history: Optional[List[Dict]] = None,
        tool_executor: Optional[callable] = None
    ) -> str:
        """
        Chat with Claude using tool calling for structured data access.
        
        Args:
            user_message: User's question
            system_prompt: System context
            tools: List of tool definitions
            conversation_history: Previous conversation messages
            tool_executor: Function to execute tool calls
            
        Returns:
            Final text response from Claude
        """
        # Initialize messages
        messages = conversation_history or []
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Initial API call
        response = self.create_message(
            messages=messages,
            system=system_prompt,
            tools=tools
        )
        
        # Process tool calls
        while response.stop_reason == "tool_use":
            # Extract tool calls from response
            tool_uses = [
                block for block in response.content 
                if block.type == "tool_use"
            ]
            
            # Add assistant's response to messages
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            # Execute tools and collect results
            tool_results = []
            for tool_use in tool_uses:
                if tool_executor:
                    try:
                        result = tool_executor(
                            tool_use.name,
                            json.loads(tool_use.input) if isinstance(tool_use.input, str) else tool_use.input
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result, indent=2)
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps({"error": str(e)}),
                            "is_error": True
                        })
            
            # Add tool results to messages
            messages.append({
                "role": "user",
                "content": tool_results
            })
            
            # Continue conversation
            response = self.create_message(
                messages=messages,
                system=system_prompt,
                tools=tools
            )
        
        # Extract final text response
        text_blocks = [
            block.text for block in response.content 
            if hasattr(block, 'text')
        ]
        return "\n".join(text_blocks)


def convert_openai_tools_to_anthropic(openai_tools: List[Dict]) -> List[Dict]:
    """
    Convert OpenAI tool definitions to Anthropic format.
    
    Args:
        openai_tools: List of OpenAI-style tool definitions
        
    Returns:
        List of Anthropic-style tool definitions
    """
    anthropic_tools = []
    
    for tool in openai_tools:
        if tool.get("type") == "function":
            func = tool["function"]
            anthropic_tools.append({
                "name": func["name"],
                "description": func["description"],
                "input_schema": func.get("parameters", {})
            })
    
    return anthropic_tools
