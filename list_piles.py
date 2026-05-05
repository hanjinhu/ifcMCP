from mcp.server.fastmcp import FastMCP

mcp=FastMCP("ifcMCP")

from ifc_util import open_ifc, get_prop

@mcp.tool()
def list_piles(file_path):
    """
    List all piles (IFCBUILDINGELEMENTPROXY entities) in an IFC file
    
    Parameters:
        file_path: path to the ifc file
    """
    # Open the IFC file
    ifc_model = open_ifc(file_path)
    if ifc_model is None:
        return "Error: The file is not found or broken"
    
    # Get all IFCBUILDINGELEMENTPROXY entities
    building_element_proxies = ifc_model.by_type("IFCBUILDINGELEMENTPROXY")
    pile_count = 0
    
    print(f"Found {len(building_element_proxies)} IFCBUILDINGELEMENTPROXY entities.")
    print("Listing pile elements:")
    print()
    
    # Print details for each pile
    for i, element in enumerate(building_element_proxies):
        # Extract properties
        global_id = get_prop(element, 'GlobalId')
        name = get_prop(element, 'Name')
        description = get_prop(element, 'Description')
        
        # Get all property sets to check if this is a pile
        psets = get_prop(element, 'IsDefinedBy')
        object_type = get_prop(element, 'ObjectType')
        
        # For this specific file, all piles are IFCBUILDINGELEMENTPROXY with descriptions containing "HP14X117-Pile-"
        is_pile = False
        if description and isinstance(description, str) and "HP14X117-Pile-" in description:
            is_pile = True
        elif name and isinstance(name, str) and ("pile" in name.lower() or "hp14x117" in name.lower()):
            is_pile = True
        elif object_type and isinstance(object_type, str) and "pile" in object_type.lower():
            is_pile = True
            
        if is_pile:
            pile_count += 1
            # Get position if available
            position = get_prop(element, 'Position')
            
            # Print details
            print(f"{pile_count}. ID: {global_id}")
            print(f"   Name: {name or 'Not specified'}")
            if description:
                print(f"   Description: {description}")
            if object_type:
                print(f"   Object Type: {object_type}")
            if position is not None:
                print(f"   Position: {position}")
            print()
    
    print(f"Total piles found: {pile_count}")

if __name__ == "__main__":
    # Use the specified file path
    file_path = r"C:\Temp\four_hp14x117_piles_DEMONSTRATION.ifc"
    list_piles(file_path)
