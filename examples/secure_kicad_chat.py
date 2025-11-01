#!/usr/bin/env python3
"""
Secure KiCAD-Chat: Enhanced version with security framework integration.

This example shows how to integrate the security framework into the main
KiCAD-Chat application for production use.
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Load environment variables
load_dotenv()

# Import core components
from kicad_chat import KiCadSchematicParser, SchematicTools
from security_utils import (
    validate_security_configuration,
    generate_security_report,
    SecureAIProvider
)

console = Console()


def check_security_config() -> bool:
    """
    Check and validate security configuration before proceeding.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    validation = validate_security_configuration()
    
    if not validation['valid']:
        console.print("\n[bold red]❌ Security Configuration Errors:[/bold red]")
        for error in validation['errors']:
            console.print(f"  • {error}")
        console.print("\n[yellow]Please fix configuration in .env file before proceeding.[/yellow]")
        return False
    
    # Display warnings if any
    if validation['warnings']:
        console.print("\n[bold yellow]⚠️  Security Warnings:[/bold yellow]")
        for warning in validation['warnings']:
            console.print(f"  • {warning}")
    
    # Display recommendations
    if validation['recommendations']:
        console.print("\n[bold cyan]💡 Recommendations:[/bold cyan]")
        for rec in validation['recommendations']:
            console.print(f"  • {rec}")
    
    return True


def display_security_banner(schematic_path: Path):
    """Display security information banner."""
    report = generate_security_report(schematic_path)
    console.print(Panel(report, title="[bold]Security Status[/bold]", border_style="cyan"))


def secure_chat_session(schematic_path: Path):
    """
    Run a secure chat session with security framework enabled.
    
    Args:
        schematic_path: Path to the KiCAD schematic file
    """
    # 1. Validate security configuration
    if not check_security_config():
        sys.exit(1)
    
    # 2. Display security banner
    console.print("\n[bold cyan]🔒 Secure KiCAD-Chat[/bold cyan]")
    display_security_banner(schematic_path)
    
    # 3. Parse schematic
    console.print(f"\n[green]Loading schematic: {schematic_path}[/green]")
    try:
        parser = KiCadSchematicParser(schematic_path)
        schematic = parser.parse()
        console.print(f"[green]✓[/green] Parsed: {len(schematic.components)} components, "
                     f"{len(schematic.nets)} nets, {len(schematic.wires)} wires\n")
    except Exception as e:
        console.print(f"[red]Error parsing schematic: {e}[/red]")
        sys.exit(1)
    
    # 4. Initialize secure AI provider
    try:
        secure_provider = SecureAIProvider()
        provider_name = os.getenv("AI_PROVIDER", "openai")
        console.print(f"[green]✓[/green] Using {provider_name.upper()} with security framework\n")
    except Exception as e:
        console.print(f"[red]Error initializing AI provider: {e}[/red]")
        console.print("[yellow]Ensure required packages are installed:[/yellow]")
        if "anthropic" in str(e).lower():
            console.print("  pip install anthropic")
        if "boto3" in str(e).lower():
            console.print("  pip install boto3")
        sys.exit(1)
    
    # 5. Display security metadata
    metadata = secure_provider.get_security_metadata()
    console.print("[dim]Security Settings:[/dim]")
    console.print(f"  Provider: {metadata['provider']}")
    console.print(f"  Encryption: {'Enabled' if metadata['encryption_enabled'] else 'Disabled'}")
    console.print(f"  Zero Retention: {'Yes' if metadata['zero_retention'] else 'No'}")
    console.print(f"  Audit Logging: {'Enabled' if metadata['audit_logging'] else 'Disabled'}")
    console.print()
    
    # 6. Create schematic tools
    tools = SchematicTools(schematic)
    
    # 7. Example: Sanitize schematic data before processing
    if metadata['encryption_enabled']:
        console.print("[cyan]ℹ️  Data will be encrypted before transmission to AI[/cyan]\n")
    
    # 8. Interactive demo with security
    console.print("[bold]Security Framework Demo[/bold]")
    console.print("[dim]This demo shows security features in action[/dim]\n")
    
    # Demo query 1: List components
    console.print("[bold blue]Example Query:[/bold blue] List all components")
    components = tools.list_components()
    console.print(f"[green]Response:[/green] Found {len(components)} components")
    for comp in components[:3]:  # Show first 3
        console.print(f"  • {comp['reference']}: {comp['value']}")
    if len(components) > 3:
        console.print(f"  ... and {len(components) - 3} more")
    console.print()
    
    # Demo query 2: Find power nets
    console.print("[bold blue]Example Query:[/bold blue] Find power nets")
    power_nets = tools.find_power_nets()
    console.print(f"[green]Response:[/green] Found {len(power_nets)} power nets")
    for net in power_nets:
        console.print(f"  • {net}")
    console.print()
    
    # Demo: Show PII sanitization
    if hasattr(secure_provider.encryption_manager, 'sanitize_for_ai'):
        console.print("[bold blue]Example:[/bold blue] PII Sanitization")
        test_comment = "Designer: john.doe@company.com, Phone: 555-1234"
        sanitized = secure_provider.encryption_manager.sanitize_for_ai(test_comment)
        console.print(f"[yellow]Original:[/yellow] {test_comment}")
        console.print(f"[green]Sanitized:[/green] {sanitized}")
        console.print()
    
    # Summary
    console.print(Panel(
        "[bold green]✅ Security Framework Active[/bold green]\n\n"
        "Your schematic data is protected with:\n"
        f"• {metadata['provider'].upper()} API with security hardening\n"
        f"• {'Client-side encryption (AWS KMS)' if metadata['encryption_enabled'] else 'Standard transmission'}\n"
        f"• {'Zero data retention policy' if metadata['zero_retention'] else 'Standard retention'}\n"
        f"• {'Full audit logging' if metadata['audit_logging'] else 'Basic logging'}\n"
        "• Automatic PII sanitization\n\n"
        "[dim]For production use with full AI chat, see kicad_chat.py[/dim]",
        title="[bold]Summary[/bold]",
        border_style="green"
    ))


def main():
    """Main entry point."""
    console.print("[bold cyan]Secure KiCAD-Chat - Security Framework Demo[/bold cyan]")
    console.print("=" * 70)
    console.print()
    
    # Get schematic file
    if len(sys.argv) < 2:
        console.print("[yellow]Usage: python secure_kicad_chat.py <schematic.kicad_sch>[/yellow]")
        console.print("\nExample:")
        console.print("  python secure_kicad_chat.py examples/simple.kicad_sch")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    if not filepath.exists():
        console.print(f"[red]Error: File not found: {filepath}[/red]")
        sys.exit(1)
    
    # Run secure session
    secure_chat_session(filepath)


if __name__ == "__main__":
    main()
