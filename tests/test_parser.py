#!/usr/bin/env python3
"""
Basic tests for KiCad-Chat MVP
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import kicad_chat
sys.path.insert(0, str(Path(__file__).parent.parent))

from kicad_chat import KiCadSchematicParser, SchematicTools


def test_parser():
    """Test that the parser can load the example schematic."""
    print("Testing parser...")

    # Path to example schematic
    example_path = Path(__file__).parent.parent / "examples" / "simple.kicad_sch"

    if not example_path.exists():
        print(f"❌ Example schematic not found: {example_path}")
        return False

    try:
        parser = KiCadSchematicParser(example_path)
        schematic = parser.parse()

        print("✅ Parser loaded schematic successfully")
        print(f"   Version: {schematic.version}")
        print(f"   Components: {len(schematic.components)}")
        print(f"   Nets: {len(schematic.nets)}")
        print(f"   Wires: {len(schematic.wires)}")
        print(f"   Junctions: {len(schematic.junctions)}")

        # Check that we found the expected components
        expected_refs = ["R1", "R2", "C1"]
        found_refs = list(schematic.components.keys())

        for ref in expected_refs:
            if ref in found_refs:
                comp = schematic.components[ref]
                print(f"   ✅ {ref}: {comp.value} ({comp.lib_id})")
            else:
                print(f"   ❌ Missing component: {ref}")
                return False

        # Check nets
        expected_nets = ["VCC", "GND"]
        found_nets = list(schematic.nets.keys())

        for net in expected_nets:
            if net in found_nets:
                print(f"   ✅ Net: {net}")
            else:
                print(f"   ❌ Missing net: {net}")
                return False

        return True

    except Exception as e:
        print(f"❌ Parser failed: {e}")
        return False

    except Exception as e:
        print(f"❌ Parser failed: {e}")
        return False


def test_tools():
    """Test that the tool functions work."""
    print("\nTesting tools...")

    example_path = Path(__file__).parent.parent / "examples" / "simple.kicad_sch"

    try:
        parser = KiCadSchematicParser(example_path)
        schematic = parser.parse()
        tools = SchematicTools(schematic)

        # Test list_components
        all_comps = tools.list_components()
        print(f"✅ list_components(): {len(all_comps)} components")

        # Test filtering
        resistors = tools.list_components("R")
        print(f"✅ list_components('R'): {len(resistors)} resistors")

        capacitors = tools.list_components("C")
        print(f"✅ list_components('C'): {len(capacitors)} capacitors")

        # Test get_component
        r1 = tools.get_component("R1")
        if r1 and r1["value"] == "10k":
            print("✅ get_component('R1'): correct value 10k")
        else:
            print("❌ get_component('R1'): wrong value")
            return False

        # Test find_components_by_value
        ten_k_resistors = tools.find_components_by_value("10k")
        if len(ten_k_resistors) == 1 and ten_k_resistors[0]["reference"] == "R1":
            print("✅ find_components_by_value('10k'): found R1")
        else:
            print("❌ find_components_by_value('10k'): wrong results")
            return False

        # Test list_nets
        nets = tools.list_nets()
        if len(nets) >= 2 and "VCC" in nets and "GND" in nets:
            print(f"✅ list_nets(): {len(nets)} nets including VCC and GND")
        else:
            print("❌ list_nets(): missing expected nets")
            return False

        # Test find_power_nets
        power_nets = tools.find_power_nets()
        if len(power_nets) >= 2 and "VCC" in power_nets and "GND" in power_nets:
            print(f"✅ find_power_nets(): {len(power_nets)} power nets")
        else:
            print("❌ find_power_nets(): missing power nets")
            return False

        return True

    except Exception as e:
        print(f"❌ Tools test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 KiCad-Chat MVP Tests\n")

    success = True

    success &= test_parser()
    success &= test_tools()

    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)