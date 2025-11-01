#!/usr/bin/env python3
"""
Security utilities for KiCAD-Chat.

This module provides high-level security functions that integrate
encryption, sanitization, and secure AI provider communication.
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import security modules with graceful degradation
try:
    from encryption import EncryptionManager, EncryptionConfig
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    EncryptionManager = None
    EncryptionConfig = None

try:
    from anthropic_client import SecureAnthropicClient, AnthropicConfig, convert_openai_tools_to_anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    SecureAnthropicClient = None
    AnthropicConfig = None


class SecureAIProvider:
    """
    Unified interface for secure AI provider communication.
    
    Handles provider selection, encryption, and data sanitization.
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        enable_encryption: bool = False,
        encryption_config: Optional[EncryptionConfig] = None
    ):
        """
        Initialize secure AI provider.
        
        Args:
            provider: AI provider ('openai' or 'anthropic'). 
                     If None, reads from AI_PROVIDER env var.
            enable_encryption: Whether to enable client-side encryption.
            encryption_config: Custom encryption configuration.
        """
        self.provider = provider or os.getenv("AI_PROVIDER", "openai")
        self.encryption_enabled = enable_encryption or (
            os.getenv("ENABLE_ENCRYPTION", "false").lower() == "true"
        )
        
        # Initialize encryption if enabled
        self.encryption_manager = None
        if self.encryption_enabled:
            if not ENCRYPTION_AVAILABLE:
                raise ImportError(
                    "Encryption requires boto3. Install with: pip install boto3"
                )
            self.encryption_manager = EncryptionManager(encryption_config)
        
        # Initialize AI client based on provider
        self.client = None
        if self.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError(
                    "Anthropic provider requires anthropic package. "
                    "Install with: pip install anthropic"
                )
            self.client = SecureAnthropicClient()
    
    def sanitize_schematic_data(self, schematic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize schematic data before transmission to AI.
        
        - Removes PII from comments and properties
        - Optionally encrypts sensitive fields
        
        Args:
            schematic_data: Raw schematic data
            
        Returns:
            Sanitized (and possibly encrypted) schematic data
        """
        sanitized = schematic_data.copy()
        
        # Sanitize text fields to remove PII
        if self.encryption_manager:
            # Process components
            if 'components' in sanitized:
                for comp_ref, comp in sanitized['components'].items():
                    if 'properties' in comp:
                        for key, value in comp['properties'].items():
                            if isinstance(value, str):
                                comp['properties'][key] = self.encryption_manager.sanitize_for_ai(value)
        
        # Encrypt sensitive data if encryption is enabled
        if self.encryption_enabled and self.encryption_manager:
            sanitized = self.encryption_manager.encrypt_schematic_data(sanitized)
        
        return sanitized
    
    def get_security_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about current security configuration.
        
        Returns:
            Dictionary with security settings
        """
        metadata = {
            "provider": self.provider,
            "encryption_enabled": self.encryption_enabled,
            "zero_retention": os.getenv("ZERO_RETENTION", "false").lower() == "true",
            "audit_logging": os.getenv("AUDIT_LOGGING", "false").lower() == "true"
        }
        
        if self.encryption_enabled and self.encryption_manager:
            metadata["encryption_config"] = {
                "kms_key_id": self.encryption_manager.config.kms_key_id,
                "aws_region": self.encryption_manager.config.aws_region
            }
        
        return metadata


def validate_security_configuration() -> Dict[str, Any]:
    """
    Validate security configuration and return warnings/recommendations.
    
    Returns:
        Dictionary with validation results and recommendations
    """
    results = {
        "valid": True,
        "warnings": [],
        "recommendations": [],
        "errors": []
    }
    
    # Check AI provider configuration
    provider = os.getenv("AI_PROVIDER", "openai")
    
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            results["errors"].append("OPENAI_API_KEY not set")
            results["valid"] = False
    elif provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            results["errors"].append("ANTHROPIC_API_KEY not set")
            results["valid"] = False
        if not ANTHROPIC_AVAILABLE:
            results["errors"].append("anthropic package not installed")
            results["valid"] = False
    else:
        results["errors"].append(f"Unknown AI provider: {provider}")
        results["valid"] = False
    
    # Check encryption configuration
    encryption_enabled = os.getenv("ENABLE_ENCRYPTION", "false").lower() == "true"
    if encryption_enabled:
        if not ENCRYPTION_AVAILABLE:
            results["errors"].append("boto3 package required for encryption")
            results["valid"] = False
        
        if not os.getenv("AWS_KMS_KEY_ID"):
            results["errors"].append("AWS_KMS_KEY_ID not set when encryption is enabled")
            results["valid"] = False
    else:
        results["warnings"].append(
            "Encryption disabled - design data will be sent unencrypted to AI provider"
        )
        results["recommendations"].append(
            "Enable ENABLE_ENCRYPTION=true and configure AWS KMS for maximum security"
        )
    
    # Check zero retention
    zero_retention = os.getenv("ZERO_RETENTION", "false").lower() == "true"
    if zero_retention and provider != "anthropic":
        results["warnings"].append(
            "ZERO_RETENTION requires Anthropic Enterprise DPA"
        )
    
    if provider == "anthropic" and not zero_retention:
        results["recommendations"].append(
            "Enable ZERO_RETENTION=true with Anthropic Enterprise DPA for maximum data protection"
        )
    
    # Check audit logging
    audit_logging = os.getenv("AUDIT_LOGGING", "false").lower() == "true"
    if not audit_logging:
        results["recommendations"].append(
            "Enable AUDIT_LOGGING=true for compliance and security monitoring"
        )
    
    # Check for PrivateLink
    if provider == "anthropic":
        endpoint = os.getenv("ANTHROPIC_ENDPOINT", "https://api.anthropic.com")
        if "api.anthropic.com" in endpoint:
            results["recommendations"].append(
                "Consider using AWS PrivateLink for Anthropic API (set ANTHROPIC_ENDPOINT)"
            )
    
    return results


def generate_security_report(schematic_path: Path) -> str:
    """
    Generate a security report for a schematic processing session.
    
    Args:
        schematic_path: Path to the schematic file
        
    Returns:
        Formatted security report as string
    """
    validation = validate_security_configuration()
    provider = SecureAIProvider()
    metadata = provider.get_security_metadata()
    
    report = []
    report.append("=" * 70)
    report.append("SECURITY REPORT")
    report.append("=" * 70)
    report.append(f"\nSchematic: {schematic_path.name}")
    report.append(f"Provider: {metadata['provider']}")
    report.append(f"Encryption: {'Enabled' if metadata['encryption_enabled'] else 'Disabled'}")
    report.append(f"Zero Retention: {'Yes' if metadata['zero_retention'] else 'No'}")
    report.append(f"Audit Logging: {'Enabled' if metadata['audit_logging'] else 'Disabled'}")
    
    if metadata['encryption_enabled']:
        enc_config = metadata.get('encryption_config', {})
        report.append(f"\nEncryption Configuration:")
        report.append(f"  KMS Key: {enc_config.get('kms_key_id', 'Not set')}")
        report.append(f"  AWS Region: {enc_config.get('aws_region', 'Not set')}")
    
    if validation['errors']:
        report.append("\n❌ ERRORS:")
        for error in validation['errors']:
            report.append(f"  - {error}")
    
    if validation['warnings']:
        report.append("\n⚠️  WARNINGS:")
        for warning in validation['warnings']:
            report.append(f"  - {warning}")
    
    if validation['recommendations']:
        report.append("\n💡 RECOMMENDATIONS:")
        for rec in validation['recommendations']:
            report.append(f"  - {rec}")
    
    if validation['valid']:
        report.append("\n✅ Configuration is valid")
    else:
        report.append("\n❌ Configuration has errors - please fix before proceeding")
    
    report.append("\n" + "=" * 70)
    
    return "\n".join(report)
