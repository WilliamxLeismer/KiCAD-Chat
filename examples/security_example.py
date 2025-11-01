#!/usr/bin/env python3
"""
Example: Using KiCAD-Chat with Anthropic Claude and encryption.

This example demonstrates how to use the secure data transmission framework
with Anthropic's Claude API and client-side encryption.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kicad_chat import KiCadSchematicParser, SchematicTools
from security_utils import generate_security_report, validate_security_configuration
from anthropic_client import SecureAnthropicClient, convert_openai_tools_to_anthropic
from rich.console import Console
from rich.markdown import Markdown

# Load environment variables
load_dotenv()

console = Console()


def example_with_security_report():
    """Example: Generate security report before processing."""
    console.print("[bold cyan]Example 1: Security Report[/bold cyan]\n")
    
    # Use the example schematic
    schematic_path = Path(__file__).parent.parent / "examples" / "simple.kicad_sch"
    
    if not schematic_path.exists():
        console.print("[red]Example schematic not found[/red]")
        return
    
    # Generate and display security report
    report = generate_security_report(schematic_path)
    console.print(report)


def example_with_validation():
    """Example: Validate security configuration."""
    console.print("\n[bold cyan]Example 2: Configuration Validation[/bold cyan]\n")
    
    validation = validate_security_configuration()
    
    console.print(f"Configuration Valid: {validation['valid']}")
    
    if validation['errors']:
        console.print("\n[red]Errors:[/red]")
        for error in validation['errors']:
            console.print(f"  ❌ {error}")
    
    if validation['warnings']:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in validation['warnings']:
            console.print(f"  ⚠️  {warning}")
    
    if validation['recommendations']:
        console.print("\n[blue]Recommendations:[/blue]")
        for rec in validation['recommendations']:
            console.print(f"  💡 {rec}")


def example_anthropic_tools():
    """Example: Using Anthropic Claude with tool calling (if available)."""
    console.print("\n[bold cyan]Example 3: Anthropic Tool Conversion[/bold cyan]\n")
    
    # Example OpenAI-style tool definition
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "list_components",
                "description": "List all components in the schematic",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "component_type": {
                            "type": "string",
                            "description": "Filter by component type (e.g., 'R', 'C')"
                        }
                    }
                }
            }
        }
    ]
    
    # Convert to Anthropic format
    from anthropic_client import convert_openai_tools_to_anthropic
    anthropic_tools = convert_openai_tools_to_anthropic(openai_tools)
    
    console.print("[green]OpenAI Tool Format:[/green]")
    console.print(openai_tools[0])
    
    console.print("\n[green]Anthropic Tool Format:[/green]")
    console.print(anthropic_tools[0])


def example_sanitization():
    """Example: PII sanitization."""
    console.print("\n[bold cyan]Example 4: PII Sanitization[/bold cyan]\n")
    
    from encryption import EncryptionManager, EncryptionConfig
    
    config = EncryptionConfig(enabled=False)
    manager = EncryptionManager(config)
    
    # Test data with PII
    test_comments = [
        "Designer: john.doe@company.com",
        "Contact: 555-123-4567",
        "Designed by: Jane Smith",
        "Customer: ACME Corp (contact@acme.com)"
    ]
    
    console.print("[yellow]Original comments:[/yellow]")
    for comment in test_comments:
        console.print(f"  {comment}")
    
    console.print("\n[green]Sanitized comments:[/green]")
    for comment in test_comments:
        sanitized = manager.sanitize_for_ai(comment)
        console.print(f"  {sanitized}")


def example_minimal_usage():
    """Example: Minimal secure usage pattern."""
    console.print("\n[bold cyan]Example 5: Minimal Secure Usage Pattern[/bold cyan]\n")
    
    code = '''
import os
from pathlib import Path
from kicad_chat import KiCadSchematicParser
from security_utils import validate_security_configuration, generate_security_report

# 1. Validate configuration
validation = validate_security_configuration()
if not validation['valid']:
    print("Security configuration has errors!")
    exit(1)

# 2. Generate security report
schematic_path = Path("my_design.kicad_sch")
report = generate_security_report(schematic_path)
print(report)

# 3. Parse schematic
parser = KiCadSchematicParser(schematic_path)
schematic = parser.parse()

# 4. Use with your preferred AI provider
# See kicad_chat.py for full implementation
'''
    
    console.print(Markdown(f"```python\n{code}\n```"))


def main():
    """Run all examples."""
    console.print("[bold]KiCAD-Chat Security Framework Examples[/bold]")
    console.print("=" * 70)
    console.print()
    
    example_with_security_report()
    example_with_validation()
    example_anthropic_tools()
    example_sanitization()
    example_minimal_usage()
    
    console.print("\n" + "=" * 70)
    console.print("[bold green]Examples completed![/bold green]")
    console.print("\nFor more information, see SECURITY.md")


if __name__ == "__main__":
    main()
