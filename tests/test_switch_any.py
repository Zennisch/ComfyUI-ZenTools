#!/usr/bin/env python

"""Tests for SwitchAny node and validation utilities."""

import pytest
from src.comfyui_zns_utils.switch_any import (
    SwitchAny,
    find_switch_any,
    resolve_switch_boolean,
    block_switch,
    recursive_delete_dependents,
)


@pytest.fixture
def switch_any_node():
    """Fixture to create a SwitchAny node instance."""
    return SwitchAny()


# =============================================================================
# NODE EXECUTION TESTS
# =============================================================================


class TestSwitchAnyNode:
    """Tests for the SwitchAny node class."""

    def test_node_initialization(self, switch_any_node):
        """Test that the node can be instantiated."""
        assert isinstance(switch_any_node, SwitchAny)

    def test_input_types(self):
        """Test the node's input types."""
        input_types = SwitchAny.INPUT_TYPES()
        assert "required" in input_types
        assert "source" in input_types["required"]
        assert "switch" in input_types["required"]

    def test_return_types(self):
        """Test the node's return types."""
        assert SwitchAny.RETURN_TYPES == ("ANY",)
        assert SwitchAny.RETURN_NAMES == ("ANY",)

    def test_function_name(self):
        """Test the node's function name."""
        assert SwitchAny.FUNCTION == "pass_through"

    def test_category(self):
        """Test the node's category."""
        assert SwitchAny.CATEGORY == "utils"

    def test_pass_through_with_switch_on(self, switch_any_node):
        """Test that pass_through returns source when switch is ON."""
        source_data = {"test": "data"}
        result = switch_any_node.pass_through(source_data, True)
        assert result == (source_data,)

    def test_pass_through_with_switch_off(self, switch_any_node):
        """Test that pass_through returns source even when switch is OFF."""
        # The actual blocking happens in the validation hook, not in the node
        source_data = {"test": "data"}
        result = switch_any_node.pass_through(source_data, False)
        assert result == (source_data,)

    def test_pass_through_with_various_types(self, switch_any_node):
        """Test pass_through with various data types."""
        test_data = [
            "string",
            123,
            45.67,
            {"complex": "dict"},
            ["list", "items"],
            None,
        ]

        for data in test_data:
            result = switch_any_node.pass_through(data, True)
            assert result == (data,)


# =============================================================================
# VALIDATION UTILITY TESTS
# =============================================================================


class TestFindSwitchAny:
    """Tests for find_switch_any function."""

    def test_find_no_switches(self):
        """Test finding switches in an empty prompt."""
        prompt = {}
        result = find_switch_any(prompt)
        assert result == []

    def test_find_single_switch(self):
        """Test finding a single SwitchAny node."""
        prompt = {
            "1": {"class_type": "SwitchAny", "inputs": {}},
        }
        result = find_switch_any(prompt)
        assert result == ["1"]

    def test_find_multiple_switches(self):
        """Test finding multiple SwitchAny nodes."""
        prompt = {
            "1": {"class_type": "SwitchAny", "inputs": {}},
            "2": {"class_type": "SwitchAny", "inputs": {}},
            "3": {"class_type": "OtherNode", "inputs": {}},
            "4": {"class_type": "SwitchAny", "inputs": {}},
        }
        result = find_switch_any(prompt)
        assert set(result) == {"1", "2", "4"}

    def test_find_switches_with_mixed_nodes(self):
        """Test finding switches among other node types."""
        prompt = {
            "load_image": {"class_type": "LoadImage", "inputs": {}},
            "switch1": {"class_type": "SwitchAny", "inputs": {}},
            "save_image": {"class_type": "SaveImage", "inputs": {}},
            "switch2": {"class_type": "SwitchAny", "inputs": {}},
        }
        result = find_switch_any(prompt)
        assert set(result) == {"switch1", "switch2"}


class TestResolveSwitchBoolean:
    """Tests for resolve_switch_boolean function."""

    def test_resolve_direct_boolean_true(self):
        """Test resolving a direct boolean True value."""
        prompt = {}
        result = resolve_switch_boolean(prompt, True)
        assert result is True

    def test_resolve_direct_boolean_false(self):
        """Test resolving a direct boolean False value."""
        prompt = {}
        result = resolve_switch_boolean(prompt, False)
        assert result is False

    def test_resolve_connected_boolean_true(self):
        """Test resolving a boolean from a connected node."""
        prompt = {
            "1": {"inputs": {"output": True}},
            "2": {"inputs": {"switch": [1, 0]}},
        }
        result = resolve_switch_boolean(prompt, [1, 0])
        assert result is True

    def test_resolve_connected_boolean_false(self):
        """Test resolving a boolean from a connected node."""
        prompt = {
            "1": {"inputs": {"output": False}},
            "2": {"inputs": {"switch": [1, 0]}},
        }
        result = resolve_switch_boolean(prompt, [1, 0])
        assert result is False

    def test_resolve_invalid_boolean_raises_error(self):
        """Test that invalid boolean raises ValueError."""
        prompt = {"1": {"inputs": {"output": "not_a_boolean"}}}
        with pytest.raises(ValueError):
            resolve_switch_boolean(prompt, [1, 0])

    def test_resolve_empty_list_raises_error(self):
        """Test that empty list raises ValueError."""
        prompt = {}
        with pytest.raises(ValueError):
            resolve_switch_boolean(prompt, [])


class TestBlockSwitch:
    """Tests for block_switch function."""

    def test_block_switch_enabled_does_nothing(self):
        """Test that block_switch with enabled=True doesn't remove nodes."""
        prompt = {
            "1": {"class_type": "SwitchAny", "inputs": {"source": "data", "switch": True}},
            "2": {"class_type": "SomeNode", "inputs": {"input": [1, 0]}},
        }
        result = block_switch(prompt, "1", True)
        assert len(result) == 2
        assert "1" in result
        assert "2" in result

    def test_block_switch_disabled_removes_connected_nodes(self):
        """Test that block_switch with enabled=False removes downstream nodes."""
        prompt = {
            "1": {"class_type": "SwitchAny", "inputs": {"source": "data", "switch": False}},
            "2": {"class_type": "SomeNode", "inputs": {"input": [1, 0]}},
            "3": {"class_type": "OtherNode", "inputs": {"input": "other"}},
        }
        result = block_switch(prompt, "1", False)
        assert "1" in result  # Switch itself remains
        assert "2" not in result  # Connected node removed
        assert "3" in result  # Unconnected node remains

    def test_block_switch_removes_multiple_downstream_nodes(self):
        """Test blocking multiple nodes connected to the switch."""
        prompt = {
            "1": {"class_type": "SwitchAny", "inputs": {"source": "data", "switch": False}},
            "2": {"class_type": "Node", "inputs": {"input": [1, 0]}},
            "3": {"class_type": "Node", "inputs": {"input": [1, 0]}},
            "4": {"class_type": "Node", "inputs": {"input": "other"}},
        }
        result = block_switch(prompt, "1", False)
        assert "1" in result
        assert "2" not in result
        assert "3" not in result
        assert "4" in result


class TestRecursiveDeleteDependents:
    """Tests for recursive_delete_dependents function."""

    def test_recursive_delete_no_dependents(self):
        """Test recursive delete with no dependent nodes."""
        prompt = {
            "1": {"class_type": "Node", "inputs": {}},
            "2": {"class_type": "Node", "inputs": {"input": "other"}},
        }
        result = recursive_delete_dependents(prompt, ["1"])
        assert len(result) == 1
        assert "2" in result

    def test_recursive_delete_single_dependent(self):
        """Test recursive delete with a single dependent node."""
        prompt = {
            "1": {"class_type": "Node", "inputs": {}},
            "2": {"class_type": "Node", "inputs": {"input": [1, 0]}},
            "3": {"class_type": "Node", "inputs": {"input": "other"}},
        }
        result = recursive_delete_dependents(prompt, ["1"])
        assert "1" not in result  # Original is not in result (already deleted)
        assert "2" not in result  # Dependent removed
        assert "3" in result  # Unrelated node remains

    def test_recursive_delete_cascading(self):
        """Test that deletion cascades through dependent nodes."""
        prompt = {
            "1": {"class_type": "Node", "inputs": {}},
            "2": {"class_type": "Node", "inputs": {"input": [1, 0]}},
            "3": {"class_type": "Node", "inputs": {"input": [2, 0]}},
            "4": {"class_type": "Node", "inputs": {"input": "other"}},
        }
        result = recursive_delete_dependents(prompt, ["1"])
        assert "1" not in result  # Original
        assert "2" not in result  # Direct dependent
        assert "3" not in result  # Transitive dependent
        assert "4" in result  # Unrelated remains

    def test_recursive_delete_multiple_sources(self):
        """Test recursive delete starting from multiple source nodes."""
        prompt = {
            "1": {"class_type": "Node", "inputs": {}},
            "2": {"class_type": "Node", "inputs": {}},
            "3": {"class_type": "Node", "inputs": {"input": [1, 0]}},
            "4": {"class_type": "Node", "inputs": {"input": [2, 0]}},
            "5": {"class_type": "Node", "inputs": {"input": [3, 0]}},
            "6": {"class_type": "Node", "inputs": {"input": "other"}},
        }
        result = recursive_delete_dependents(prompt, ["1", "2"])
        assert "1" not in result
        assert "2" not in result
        assert "3" not in result
        assert "4" not in result
        assert "5" not in result  # Cascades from 3 and 4
        assert "6" in result


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestSwitchAnyIntegration:
    """Integration tests for SwitchAny flow control."""

    def test_workflow_with_switch_enabled(self):
        """Test a workflow with switch enabled."""
        prompt = {
            "1": {"class_type": "LoadImage", "inputs": {}},
            "2": {"class_type": "SwitchAny", "inputs": {"source": [1, 0], "switch": True}},
            "3": {"class_type": "SaveImage", "inputs": {"image": [2, 0]}},
        }

        switches = find_switch_any(prompt)
        assert switches == ["2"]

        for switch_id in switches:
            switch_value = prompt[switch_id]["inputs"]["switch"]
            switch_enabled = resolve_switch_boolean(prompt, switch_value)
            if not switch_enabled:
                prompt = block_switch(prompt, switch_id, switch_enabled)

        # All nodes should remain
        assert len(prompt) == 3
        assert "1" in prompt
        assert "2" in prompt
        assert "3" in prompt

    def test_workflow_with_switch_disabled(self):
        """Test a workflow with switch disabled."""
        prompt = {
            "1": {"class_type": "LoadImage", "inputs": {}},
            "2": {"class_type": "SwitchAny", "inputs": {"source": [1, 0], "switch": False}},
            "3": {"class_type": "SaveImage", "inputs": {"image": [2, 0]}},
        }

        switches = find_switch_any(prompt)
        assert switches == ["2"]

        for switch_id in switches:
            switch_value = prompt[switch_id]["inputs"]["switch"]
            switch_enabled = resolve_switch_boolean(prompt, switch_value)
            if not switch_enabled:
                prompt = block_switch(prompt, switch_id, switch_enabled)

        # SaveImage should be removed due to cascading deletion
        assert "1" in prompt  # LoadImage remains
        assert "2" in prompt  # Switch remains
        assert "3" not in prompt  # SaveImage removed (depends on switch)

    def test_workflow_with_multiple_switches(self):
        """Test a workflow with multiple switches."""
        prompt = {
            "1": {"class_type": "LoadImage", "inputs": {}},
            "2": {"class_type": "SwitchAny", "inputs": {"source": [1, 0], "switch": True}},
            "3": {"class_type": "Filter", "inputs": {"image": [2, 0]}},
            "4": {"class_type": "SwitchAny", "inputs": {"source": [3, 0], "switch": False}},
            "5": {"class_type": "SaveImage", "inputs": {"image": [4, 0]}},
        }

        switches = find_switch_any(prompt)
        assert set(switches) == {"2", "4"}

        for switch_id in switches:
            switch_value = prompt[switch_id]["inputs"]["switch"]
            switch_enabled = resolve_switch_boolean(prompt, switch_value)
            if not switch_enabled:
                prompt = block_switch(prompt, switch_id, switch_enabled)

        # Switch 2 is ON, so filter remains
        # Switch 4 is OFF, so SaveImage is removed
        assert "1" in prompt
        assert "2" in prompt
        assert "3" in prompt
        assert "4" in prompt
        assert "5" not in prompt
