import ifcopenshell
import ifcopenshell.util
import ifcopenshell.util.element

import os

class Bearing:
    def __init__(self, hole_diameter, pad_length, pad_width, pad_diameter, pad_height, steel_shim_quantity, 
                 steel_shim_clear_cover, steel_shim_height, steel_shim_spacing, steel_shim_length,
                 steel_shim_width, steel_shim_diameter, hardness):
        self.hole_diameter = hole_diameter
        self.pad_length = pad_length
        self.pad_width = pad_width
        self.pad_diameter = pad_diameter
        self.pad_height = pad_height
        self.steel_shim_quantity = steel_shim_quantity
        self.steel_shim_clear_cover = steel_shim_clear_cover
        self.steel_shim_height = steel_shim_height        
        self.steel_shim_spacing = steel_shim_spacing
        self.steel_shim_length = steel_shim_length
        self.steel_shim_width = steel_shim_width
        self.steel_shim_diameter = steel_shim_diameter
        self.hardness = hardness

    def __str__(self):
        return f"pad length: {self.pad_length}, pad width: {self.pad_width}, pad diameter: {self.pad_diameter}, hole diameter: {self.hole_diameter}"


def read_bearing(ifc_file_path, is_pier_bearing) -> Bearing:
    model = load_ifc_file(ifc_file_path)
    substructure = get_bridge_substructure(model)

    if substructure is None:
        print("No substructure found in the IFC file.")
        raise ValueError("No substructure found in the IFC file.")

    structural_elements = get_structural_elements(substructure)
    
    if is_pier_bearing:
        return get_pier_bearing(structural_elements['piers'])
    else:
        return get_abutment_bearing(structural_elements['abutments'])


def load_ifc_file(ifc_file_path):
    if not os.path.exists(ifc_file_path):
        print(f"IFC file not found at {ifc_file_path}")
        raise FileNotFoundError(f"IFC file not found at {ifc_file_path}")
    
    print(f"Start opening IFC file: {ifc_file_path}")
    model = ifcopenshell.open(ifc_file_path)
    print(f"IFC file opened: {ifc_file_path}")
    return model


def get_bridge_substructure(model):
    project = model.by_type("IfcProject")[0]
    site = project.IsDecomposedBy[0].RelatedObjects[0]
    bridge = site.IsDecomposedBy[0].RelatedObjects[0]
    bridge_parts = bridge.IsDecomposedBy[0].RelatedObjects

    for bridge_part in bridge_parts:
        if bridge_part.is_a('IfcBridgePart') and bridge_part.PredefinedType == 'SUBSTRUCTURE':
            print("Bridge substructure found.")
            return bridge_part
    
    return None


def get_structural_elements(substructure):
    piers = []
    abutments = []
    
    for element in substructure.IsDecomposedBy[0].RelatedObjects:
        if element.is_a('IfcBridgePart'):
            if element.PredefinedType == 'PIER':
                piers.append(element)
            elif element.PredefinedType == 'ABUTMENT':
                abutments.append(element)
    
    return {'piers': piers, 'abutments': abutments}


def get_pier_bearing(piers) -> Bearing:
    if len(piers) == 0:
        print("No piers found in the IFC file.")
        raise ValueError("No piers found in the IFC file.")
    
    pier = piers[0]
    bearings = get_bearings_from_element(pier)
    return create_bearing_from_ifc(bearings[0])


def get_abutment_bearing(abutments) -> Bearing:
    if len(abutments) == 0:
        print("No abutments found in the IFC file.")
        raise ValueError("No abutments found in the IFC file.")
    
    abutment = abutments[0]
    bearings = get_bearings_from_element(abutment)
    return create_bearing_from_ifc(bearings[0])


def get_bearings_from_element(element):
    bearings = []
    for related_object in element.ContainsElements[0].RelatedElements:
        if related_object.is_a("IfcBearing"):
            bearings.append(related_object)
    return bearings


def create_bearing_from_ifc(ifc_bearing) -> Bearing:
    if not ifc_bearing.is_a('IfcBearing'):
        raise ValueError(f"Expected IfcBearing object, got {ifc_bearing.is_a()}")
    
    bearing_psets = ifcopenshell.util.element.get_psets(ifc_bearing)
    pset_properties = bearing_psets['Dimensions']

    hole_diameter_in = get_property_value(pset_properties, 'Hole Diameter [in]') or 0.0
    pad_length_in = get_property_value(pset_properties, 'Pad Length [in]') or 0.0
    pad_width_in = get_property_value(pset_properties, 'Pad Width [in]') or 0.0
    pad_diameter_in = get_property_value(pset_properties, 'Pad Diameter [in]') or 0.0
    pad_height_in = get_property_value(pset_properties, 'Pad Height [in]') or 0.0
    steel_shim_quantity = get_property_value(pset_properties, 'Quantity of Steel Shims') or 0
    steel_shim_clear_cover_in = get_property_value(pset_properties, 'Steel Shim Clear Cover [in]') or 0.0
    steel_shim_height_in = get_property_value(pset_properties, 'Steel Shim Thickness [in]') or 0.0
    steel_shim_spacing_in = get_property_value(pset_properties, 'Steel Shim Spacing [in]') or 0.0
    steel_shim_length_in = get_property_value(pset_properties, 'Steel Shim Length [in]') or 0.0
    steel_shim_width_in = get_property_value(pset_properties, 'Steel Shim Width [in]') or 0.0
    steel_shim_diameter_in = get_property_value(pset_properties, 'Steel Shim Diameter [in]') or 0.0
    hardness = get_property_value(pset_properties, 'Hardness') or 0

    return Bearing(
        hole_diameter_in,
        pad_length_in,
        pad_width_in,
        pad_diameter_in,
        pad_height_in,
        steel_shim_quantity,
        steel_shim_clear_cover_in,
        steel_shim_height_in, 
        steel_shim_spacing_in,
        steel_shim_length_in,
        steel_shim_width_in,
        steel_shim_diameter_in,
        hardness
    )


def get_property_value(pset, property_name):
    if property_name in pset:
        property_value = pset[property_name]
        print(property_name + ": " + str(property_value))
        return property_value
    else:
        print(property_name + " not found in the propertie set.")
        return None


if __name__ == "__main__":
    read_bearing()