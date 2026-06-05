"""
SwitchAny Node - Flow control node that passes or blocks data based on a boolean switch.

When switch is ON: data passes through normally.
When switch is OFF: the node and all downstream nodes are removed from the DAG before execution.

Uses validation hook pattern (similar to FloodGate) to intercept and modify the prompt DAG.
"""

from comfy.comfy_types.node_typing import IO, ComfyNodeABC, InputTypeDict


class SwitchAny(ComfyNodeABC):
    """
    A simple pass-through node with a boolean switch control.
    
    The node always returns the input source on execution, but the validation hook
    controls whether downstream nodes execute based on the switch state.
    """

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "source": (IO.ANY,),
                "switch": (IO.BOOLEAN, {"default": False}),
            }
        }

    RETURN_TYPES = (IO.ANY,)
    RETURN_NAMES = ("ANY",)

    FUNCTION = "pass_through"
    CATEGORY = "utils"

    def pass_through(self, source, switch):
        """
        Pass the source through regardless of switch value.
        
        The actual flow control happens in the validation hook,
        which deletes downstream nodes based on switch state.
        """
        return (source,)


# =============================================================================
# VALIDATION UTILITIES - DAG manipulation for flow control
# =============================================================================


def find_switch_any(prompt: dict) -> list:
    """Find all SwitchAny node IDs in the prompt DAG."""
    switch_ids = []
    for k, v in prompt.items():
        if v.get("class_type") == "SwitchAny":
            switch_ids.append(k)
    return switch_ids


def resolve_switch_boolean(prompt: dict, switch_value) -> bool:
    """
    Resolve the switch boolean value from direct value or connected node.
    
    Args:
        prompt: The prompt DAG
        switch_value: Either a direct boolean, or a list [source_node_id, output_index]
        
    Returns:
        The resolved boolean value
        
    Raises:
        ValueError: If boolean cannot be determined
    """
    # Case 1: Direct boolean value
    if isinstance(switch_value, bool):
        return switch_value

    # Case 2: Connected from another node (list: [source_node_id, output_index])
    if isinstance(switch_value, (list, tuple)) and len(switch_value) >= 2:
        source_id, conn_index = switch_value[0], switch_value[1]
        
        # Get the output value from source node
        source_inputs = prompt[source_id]["inputs"]
        
        # The nth output corresponds to the nth input value (simplified model)
        # In a real ComfyUI context, we'd need to track actual output values
        # For now, just check if we can extract a boolean
        output_value = list(source_inputs.values())[conn_index] if conn_index < len(source_inputs) else None
        
        if isinstance(output_value, bool):
            return output_value
        
        # Recursively resolve if it's also a connection
        if isinstance(output_value, (list, tuple)):
            return resolve_switch_boolean(prompt, output_value)
        
        raise ValueError(f"Source node does not output a boolean value: {output_value}")

    # Case 3: Empty or invalid
    raise ValueError(f"Cannot determine boolean value from: {switch_value}")


def block_switch(prompt: dict, switch_id: str, switch_enabled: bool) -> dict:
    """
    Remove downstream nodes from the DAG based on switch state.
    
    If switch is OFF (False): removes all nodes connected to this SwitchAny.
    If switch is ON (True): keeps all nodes connected.
    
    Args:
        prompt: The prompt DAG
        switch_id: The ID of the SwitchAny node
        switch_enabled: The state of the switch (True = pass through, False = block)
        
    Returns:
        Modified prompt with blocked nodes removed
    """
    if switch_enabled:
        # Switch is ON - let all downstream nodes pass through
        return prompt

    # Switch is OFF - find all nodes connected to this switch and remove them
    nodes_to_remove = []

    for node_id, node_data in prompt.items():
        # Skip the switch node itself
        if node_id == switch_id:
            continue

        # Check if this node is connected to the switch
        for input_name, input_value in node_data.get("inputs", {}).items():
            # Connections are represented as [source_node_id, output_index]
            if isinstance(input_value, (list, tuple)) and len(input_value) >= 1:
                if switch_id in input_value:
                    nodes_to_remove.append(node_id)
                    break

    # Remove the nodes
    for node_id in nodes_to_remove:
        del prompt[node_id]

    # Recursively remove dependent nodes (nodes that depend on the removed nodes)
    if nodes_to_remove:
        return recursive_delete_dependents(prompt, nodes_to_remove)

    return prompt


def recursive_delete_dependents(prompt: dict, node_ids: list) -> dict:
    """
    Recursively delete nodes that depend on the given nodes.
    
    This ensures no orphaned nodes are left after removing a node in the DAG.
    
    Args:
        prompt: The prompt DAG
        node_ids: List of node IDs to find dependents of
        
    Returns:
        Modified prompt with all dependent nodes removed
    """
    nodes_to_delete = []

    for node_id, node_data in prompt.items():
        # Check if this node depends on any of the given nodes
        for input_name, input_value in node_data.get("inputs", {}).items():
            if isinstance(input_value, (list, tuple)) and len(input_value) >= 1:
                # Check if this connection comes from any of the nodes being deleted
                if any(to_remove_id in input_value for to_remove_id in node_ids):
                    nodes_to_delete.append(node_id)
                    break

    # Delete the nodes
    for node_id in nodes_to_delete:
        del prompt[node_id]

    # Recurse if we found more nodes to delete
    if nodes_to_delete:
        return recursive_delete_dependents(prompt, nodes_to_delete)

    return prompt
