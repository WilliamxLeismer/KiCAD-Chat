#!/usr/bin/env python3
"""
KiCad-Chat: Minimal MVP for querying KiCad schematics with LLMs
Single-file implementation without unnecessary complexity.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

import sexpdata
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

console = Console()


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Component:
    """Represents a schematic component/symbol."""
    lib_id: str
    reference: str
    value: str
    unit: int
    position: tuple[float, float]
    uuid: str
    properties: Dict[str, str] = field(default_factory=dict)
    pins: Dict[str, str] = field(default_factory=dict)  # pin_number: pin_name


@dataclass
class Net:
    """Represents an electrical net (connection)."""
    name: str
    nodes: List[tuple[str, str]] = field(default_factory=list)  # [(ref, pin), ...]


@dataclass
class Wire:
    """Represents a wire connection."""
    start: tuple[float, float]
    end: tuple[float, float]
    uuid: str


@dataclass
class Schematic:
    """Parsed KiCad schematic data."""
    version: str
    components: Dict[str, Component]  # ref -> Component
    nets: Dict[str, Net]  # net_name -> Net
    wires: List[Wire]
    junctions: List[tuple[float, float]]
    filepath: Path


# ============================================================================
# S-Expression Parser
# ============================================================================

class KiCadSchematicParser:
    """Parses .kicad_sch files (S-expression format) into Python objects."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.raw_data = None

    def parse(self) -> Schematic:
        """Main parsing entry point."""
        content = self.filepath.read_text(encoding='utf-8')
        self.raw_data = sexpdata.loads(content)

        # Extract version
        version = self._find_token_value("version", self.raw_data)

        # Parse components (symbols)
        components = self._parse_symbols()

        # Parse nets
        nets = self._parse_nets()

        # Parse wires
        wires = self._parse_wires()

        # Parse junctions
        junctions = self._parse_junctions()

        return Schematic(
            version=version,
            components=components,
            nets=nets,
            wires=wires,
            junctions=junctions,
            filepath=self.filepath
        )

    def _find_token_value(self, token_name: str, sexp: Any, default: Any = "") -> Any:
        """Find value of a token in S-expression."""
        if not isinstance(sexp, list):
            return default
        for item in sexp:
            if isinstance(item, list) and len(item) > 1:
                if hasattr(item[0], 'value') and item[0].value() == token_name:
                    return item[1] if len(item) > 1 else default
        return default

    def _find_all_tokens(self, token_name: str, sexp: Any) -> List[Any]:
        """Find all tokens with given name."""
        results = []
        if not isinstance(sexp, list):
            return results
        for item in sexp:
            if isinstance(item, list) and len(item) > 0:
                if hasattr(item[0], 'value') and item[0].value() == token_name:
                    results.append(item)
        return results

    def _parse_symbols(self) -> Dict[str, Component]:
        """Parse all symbol instances in schematic."""
        components = {}
        symbols = self._find_all_tokens("symbol", self.raw_data)

        for sym in symbols:
            # Extract properties
            lib_id = self._find_token_value("lib_id", sym)
            uuid = self._find_token_value("uuid", sym)
            unit = self._find_token_value("unit", sym, 1)

            # Parse position
            at_token = self._find_all_tokens("at", sym)
            position = (0.0, 0.0)
            if at_token:
                coords = at_token[0][1:3]
                position = (float(coords[0]), float(coords[1]))

            # Parse properties (Reference, Value, etc.)
            props = {}
            reference = ""
            value = ""

            prop_tokens = self._find_all_tokens("property", sym)
            for prop in prop_tokens:
                if len(prop) >= 3:
                    key = str(prop[1]).strip('"')
                    val = str(prop[2]).strip('"')
                    props[key] = val
                    if key == "Reference":
                        reference = val
                    elif key == "Value":
                        value = val

            if reference and reference not in components:
                components[reference] = Component(
                    lib_id=lib_id,
                    reference=reference,
                    value=value,
                    unit=unit,
                    position=position,
                    uuid=uuid,
                    properties=props
                )

        return components

    def _parse_nets(self) -> Dict[str, Net]:
        """Parse net labels and connections."""
        nets = {}

        # Find net labels
        labels = self._find_all_tokens("label", self.raw_data)
        for label in labels:
            if len(label) >= 2:
                net_name = str(label[1]).strip('"')
                if net_name not in nets:
                    nets[net_name] = Net(name=net_name)

        # Find hierarchical labels
        hier_labels = self._find_all_tokens("hierarchical_label", self.raw_data)
        for label in hier_labels:
            if len(label) >= 2:
                net_name = str(label[1]).strip('"')
                if net_name not in nets:
                    nets[net_name] = Net(name=net_name)

        # Parse connections (this is simplified - real implementation needs junction analysis)
        # For MVP, we'll rely on LLM to infer connections from component positions and wires

        return nets

    def _parse_wires(self) -> List[Wire]:
        """Parse wire connections."""
        wires = []
        wire_tokens = self._find_all_tokens("wire", self.raw_data)

        for wire in wire_tokens:
            # Find pts token
            pts_tokens = self._find_all_tokens("pts", wire)
            if pts_tokens:
                pts = pts_tokens[0]
                # Extract xy coordinates
                xy_tokens = [item for item in pts if isinstance(item, list) and
                           len(item) > 0 and hasattr(item[0], 'value') and
                           item[0].value() == "xy"]

                if len(xy_tokens) >= 2:
                    start = (float(xy_tokens[0][1]), float(xy_tokens[0][2]))
                    end = (float(xy_tokens[1][1]), float(xy_tokens[1][2]))
                    uuid = self._find_token_value("uuid", wire, "")
                    wires.append(Wire(start=start, end=end, uuid=uuid))

        return wires

    def _parse_junctions(self) -> List[tuple[float, float]]:
        """Parse junction points."""
        junctions = []
        junction_tokens = self._find_all_tokens("junction", self.raw_data)

        for junc in junction_tokens:
            at_tokens = self._find_all_tokens("at", junc)
            if at_tokens and len(at_tokens[0]) >= 3:
                x = float(at_tokens[0][1])
                y = float(at_tokens[0][2])
                junctions.append((x, y))

        return junctions


# ============================================================================
# LLM Tool Functions
# ============================================================================

class SchematicTools:
    """Tool functions for LLM to query schematic data."""

    def __init__(self, schematic: Schematic):
        self.schematic = schematic

    def list_components(self, component_type: Optional[str] = None) -> List[Dict]:
        """List all components, optionally filtered by type (e.g., 'R' for resistors)."""
        components = []
        for ref, comp in self.schematic.components.items():
            if component_type is None or ref.startswith(component_type):
                components.append({
                    "reference": comp.reference,
                    "value": comp.value,
                    "lib_id": comp.lib_id,
                    "position": comp.position
                })
        return components

    def get_component(self, reference: str) -> Optional[Dict]:
        """Get detailed information about a specific component by reference (e.g., 'R1')."""
        comp = self.schematic.components.get(reference)
        if comp:
            return {
                "reference": comp.reference,
                "value": comp.value,
                "lib_id": comp.lib_id,
                "position": comp.position,
                "properties": comp.properties,
                "unit": comp.unit
            }
        return None

    def find_components_by_value(self, value_pattern: str) -> List[Dict]:
        """Find components with value matching pattern (e.g., '10k', 'LM358')."""
        results = []
        for comp in self.schematic.components.values():
            if value_pattern.lower() in comp.value.lower():
                results.append({
                    "reference": comp.reference,
                    "value": comp.value,
                    "lib_id": comp.lib_id
                })
        return results

    def list_nets(self) -> List[str]:
        """List all named nets in the schematic."""
        return list(self.schematic.nets.keys())

    def trace_net(self, net_name: str) -> Dict:
        """Trace all connections on a specific net."""
        net = self.schematic.nets.get(net_name)
        if net:
            return {
                "name": net.name,
                "connections": [{"ref": ref, "pin": pin} for ref, pin in net.nodes]
            }
        return {"error": f"Net '{net_name}' not found"}

    def get_wire_connections(self) -> List[Dict]:
        """Get all wire connections in the schematic."""
        return [
            {"start": w.start, "end": w.end, "uuid": w.uuid}
            for w in self.schematic.wires
        ]

    def find_power_nets(self) -> List[str]:
        """Find nets that appear to be power rails (VCC, GND, etc.)."""
        power_keywords = ['vcc', 'vdd', 'gnd', 'vss', '+', '-', 'power']
        power_nets = []
        for net_name in self.schematic.nets.keys():
            if any(kw in net_name.lower() for kw in power_keywords):
                power_nets.append(net_name)
        return power_nets


# ============================================================================
# LLM Integration
# ============================================================================

class KiCadChatBot:
    """Chatbot for interacting with KiCad schematics via OpenAI."""

    def __init__(self, schematic: Schematic, api_key: str):
        self.schematic = schematic
        self.tools_instance = SchematicTools(schematic)
        # OpenAI v2 automatically reads from OPENAI_API_KEY environment variable
        self.client = OpenAI()
        self.conversation_history = []

        # Define tools for OpenAI v2
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_components",
                    "description": "List all components in the schematic, optionally filtered by type prefix (e.g., 'R' for resistors, 'U' for ICs, 'C' for capacitors)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "component_type": {
                                "type": "string",
                                "description": "Optional prefix to filter components (e.g., 'R', 'C', 'U')"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_component",
                    "description": "Get detailed information about a specific component by its reference designator",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reference": {
                                "type": "string",
                                "description": "Component reference designator (e.g., 'R1', 'U2', 'C3')"
                            }
                        },
                        "required": ["reference"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_components_by_value",
                    "description": "Find components with a specific value or value pattern",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value_pattern": {
                                "type": "string",
                                "description": "Value or pattern to search for (e.g., '10k', 'LM358')"
                            }
                        },
                        "required": ["value_pattern"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_nets",
                    "description": "List all named nets in the schematic",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "trace_net",
                    "description": "Trace all connections on a specific net",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "net_name": {
                                "type": "string",
                                "description": "Name of the net to trace"
                            }
                        },
                        "required": ["net_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_power_nets",
                    "description": "Find all power and ground nets in the schematic",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_wire_connections",
                    "description": "Get all wire connections showing start and end coordinates",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a tool function."""
        method = getattr(self.tools_instance, tool_name, None)
        if method:
            return method(**tool_input)
        return {"error": f"Tool '{tool_name}' not found"}

    def chat(self, user_message: str) -> str:
        """Send a message and get response with tool calling."""
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # System prompt with schematic context
        system_prompt = f"""You are an expert electrical engineer analyzing a KiCad schematic.

Schematic: {self.schematic.filepath.name}
Version: {self.schematic.version}
Components: {len(self.schematic.components)}
Nets: {len(self.schematic.nets)}
Wires: {len(self.schematic.wires)}

You have access to tools to query this schematic. Use them to answer questions accurately.
Provide clear, technical explanations suitable for electrical engineers."""

        # Prepare messages for OpenAI
        messages = [
            {"role": "system", "content": system_prompt}
        ] + self.conversation_history

        # Initial API call
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

        # Process tool calls
        while response.choices[0].message.tool_calls:
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response.choices[0].message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    } for tool_call in response.choices[0].message.tool_calls
                ]
            })

            # Execute tool calls
            tool_results = []
            for tool_call in response.choices[0].message.tool_calls:
                tool_name = tool_call.function.name
                tool_input = json.loads(tool_call.function.arguments)
                tool_result = self.execute_tool(tool_name, tool_input)

                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": json.dumps(tool_result, indent=2)
                })

            # Add tool results to history
            self.conversation_history.extend(tool_results)

            # Continue conversation
            messages = [
                {"role": "system", "content": system_prompt}
            ] + self.conversation_history

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )

        # Extract final text response
        final_response = response.choices[0].message.content

        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": final_response
        })

        return final_response


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Main entry point for CLI."""
    console.print("[bold cyan]KiCad-Chat MVP[/bold cyan]", style="bold")
    console.print("Query KiCad schematics with natural language\n")

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENAI_API_KEY not found in environment[/red]")
        console.print("Set it in .env file or export it")
        sys.exit(1)

    # Get schematic file
    if len(sys.argv) < 2:
        console.print("[yellow]Usage: python kicad_chat.py <schematic.kicad_sch>[/yellow]")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        console.print(f"[red]Error: File not found: {filepath}[/red]")
        sys.exit(1)

    # Parse schematic
    console.print(f"[green]Loading schematic: {filepath}[/green]")
    try:
        parser = KiCadSchematicParser(filepath)
        schematic = parser.parse()
        console.print(f"[green]✓[/green] Parsed: {len(schematic.components)} components, "
                     f"{len(schematic.nets)} nets, {len(schematic.wires)} wires\n")
    except Exception as e:
        console.print(f"[red]Error parsing schematic: {e}[/red]")
        sys.exit(1)

    # Initialize chatbot
    chatbot = KiCadChatBot(schematic, api_key)

    # Check if input is piped or interactive
    import select

    if select.select([sys.stdin], [], [], 0.0)[0]:
        # Piped input available
        question = sys.stdin.read().strip()
        if question:
            console.print(f"[bold blue]Question:[/bold blue] {question}")
            try:
                with console.status("[yellow]Thinking...[/yellow]"):
                    response = chatbot.chat(question)
                console.print(f"\n[bold green]Assistant:[/bold green]")
                console.print(Markdown(response))
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(0)
    else:
        # Interactive mode
        console.print("[dim]Type your question or 'quit' to exit[/dim]\n")

        while True:
            try:
                question = console.input("[bold blue]You:[/bold blue] ")

                if question.lower() in ['quit', 'exit', 'q']:
                    console.print("\n[cyan]Goodbye![/cyan]")
                    break

                if not question.strip():
                    continue

                # Get response
                with console.status("[yellow]Thinking...[/yellow]"):
                    response = chatbot.chat(question)

                # Display response
                console.print(f"\n[bold green]Assistant:[/bold green]")
                console.print(Markdown(response))
                console.print()

            except KeyboardInterrupt:
                console.print("\n\n[cyan]Goodbye![/cyan]")
                break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]\n")


if __name__ == "__main__":
    main()