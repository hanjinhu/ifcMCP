import ifcopenshell
import ifcopenshell.api.root
import ifcopenshell.api.unit
import ifcopenshell.api.context
import ifcopenshell.api.spatial
import ifcopenshell.api.geometry
import ifcopenshell.api.aggregate
import ifcopenshell.util.shape_builder

import os
import numpy as np

def create_bearing(pad, output_file_path):
    """Create an IFC bearing model from a pad object and save it to a file."""

    file_name = "bearing.ifc"

    # Extract pad properties
    pad_props = extract_pad_properties(pad)
    shim_props = calculate_shim_properties(pad_props)
    
    # Create IFC model structure
    model = create_ifc_model(file_name)
    project, pier = create_project_structure(model)
    
    # Create bearing pad
    bearing_pad = create_bearing_element(model, pier)
    
    # Create geometry
    create_shape_representation(model, bearing_pad, pad_props)
    
    # Set properties
    pset = ifcopenshell.api.pset.add_pset(model, product=bearing_pad, name="Dimensions")
    set_pad_properties(model, pset, pad_props)
    set_shim_properties(model, pset, shim_props)
    set_properties_general(model, bearing_pad)
    #set_properties_layout(model, bearing_pad)
    set_properties_penndot_bearing(model, bearing_pad)
    set_properties_penndot_bearing_payitem(model, bearing_pad)
    #set_properties_penndot_soleplate_payitem(model, bearing_pad)
    #set_properties_penndot_anchorbolt_payitem(model, bearing_pad)
    
    # Write file
    output_file_path = os.path.join(output_file_path, file_name)
    model.write(output_file_path)
    print("Finished writing IFC file")


def extract_pad_properties(pad):
    """Extract basic properties from the pad object."""
    # unit: inch
    props = {
        'is_rectangular': str(pad.Shape) == "Rectangular",
        'length': pad.Length,
        'width': pad.Width,
        'thickness': pad.Thickness,
        'min_thickness': pad.MinPadThickness if pad.MinPadThickness else 1.0,
        'hardness': pad.Hardness,
        'shear_modulus': pad.ElastomerShearModulus if pad.ElastomerShearModulus else 0.0,
        'has_hole': pad.HoleInPad,
        'hole_diameter': pad.HoleDiameter if pad.HoleDiameter else 0.0,
        'is_laminated': "LaminatedPad" in str(type(pad))
    }
    
    if props['is_laminated']:
        props.update({
            'num_layers': pad.NumberOfLayers,
            'interior_thickness': pad.ElastomerInteriorThickness,
            'cover_thickness': pad.ElastomerCoverThickness,
            'shim_thickness': pad.ShimThickness
        })

    # Print properties for debugging
    for key, value in props.items():
        print(f"{key}: {value}")
    
    return props


def calculate_shim_properties(pad_props):
    """Calculate steel shim properties based on pad properties."""
    if not pad_props['is_laminated']:
        return {
            'num_shims': 0,
            'height': 0.0,
            'length': 0.0,
            'width': 0.0,
            'spacing': 0.0,
            'clear_cover': 0.0
        }
    
    clear_cover = 1.0
    num_shims = pad_props['num_layers'] - 1
    
    props = {
        'num_shims': num_shims,
        'height': pad_props['shim_thickness'],
        'length': pad_props['length'] - clear_cover * 2,
        'width': pad_props['width'] - clear_cover * 2,
        'spacing': pad_props['interior_thickness'],
        'clear_cover': clear_cover
    }
    
    # Print properties for debugging
    for key, value in props.items():
        print(f"Steel shim {key}: {value}")
    
    return props


def create_ifc_model(file_name):
    """Create and initialize the IFC model."""
    model = ifcopenshell.file(schema="IFC4X3")

    model.header.file_description.description = ['ViewDefinition [Alignment-basedView]']
    model.header.file_name.name = file_name
    model.header.file_name.author = ['Hanjin Hu']
    model.header.file_name.organization = ['Michael Baker International']
    model.header.file_name.originating_system = 'Michael Baker International - BPLRFD - 1.0.0.0'

    print("Created model")
    return model


def create_project_structure(model):
    """Create the basic IFC project structure."""
    # Create project
    project = ifcopenshell.api.root.create_entity(model, 
        ifc_class="IfcProject", 
        name="Sample Project",)
    
    # Set units
    length_unit = ifcopenshell.api.unit.add_conversion_based_unit(model, name="inch")
    area_unit = ifcopenshell.api.unit.add_conversion_based_unit(model, name="square inch")
    ifcopenshell.api.unit.assign_unit(model, units=[length_unit, area_unit])
    
    # Create geometry context
    model3d = ifcopenshell.api.context.add_context(model, context_type="Model")
    _ = ifcopenshell.api.context.add_context(model, 
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model3d)
    
    # Create structure hierarchy
    site = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Project Site")
    bridge = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBridge", name="Sample Bridge")
    substructure = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBridgePart", predefined_type="SUBSTRUCTURE", name="Substructure")
    pier = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBridgePart", predefined_type="PIER", name="Pier")

    substructure.UsageType = 'NOTDEFINED'
    pier.UsageType = 'NOTDEFINED'
    
    # Set up aggregation
    ifcopenshell.api.aggregate.assign_object(model, relating_object=project, products=[site])
    ifcopenshell.api.aggregate.assign_object(model, relating_object=site, products=[bridge])
    ifcopenshell.api.aggregate.assign_object(model, relating_object=bridge, products=[substructure])
    ifcopenshell.api.aggregate.assign_object(model, relating_object=substructure, products=[pier])
    
    return project, pier


def create_bearing_element(model, pier):
    """Create the bearing pad element."""
    bearing_pad = ifcopenshell.api.root.create_entity(model,
        ifc_class="IfcBearing",
        name="PierG1Bearing",
        predefined_type="ELASTOMERIC")
    
    ifcopenshell.api.aggregate.assign_object(model, relating_object=pier, products=[bearing_pad])

    # Give the bearing a local origin at (0, 0, 0)
    # Create a 4x4 identity matrix. This matrix is at the origin with no rotation.
    bearing_pad_1_place_matrix = np.eye(4)

    # Set the X, Y, Z coordinates. Notice how we rotate first then translate.
    # This is because the rotation origin is always at 0, 0, 0.
    bearing_pad_1_place_matrix[:,3][0:3] = (0, 0, 0)

    ifcopenshell.api.geometry.edit_object_placement(model, product=bearing_pad, matrix=bearing_pad_1_place_matrix)
    ifcopenshell.api.spatial.assign_container(model, products=[bearing_pad], relating_structure=pier)

    return bearing_pad


def create_shape_representation(model, bearing_pad, props):
    """Create the geometric representation of the bearing pad."""
    builder = ifcopenshell.util.shape_builder.ShapeBuilder(model)
    
    # Create outer profile
    if props['is_rectangular']:
        outer_curve = builder.polyline([
            (props['width']/2.0, props['length']/2.0),
            (props['width']/2.0, -props['length']/2.0),
            (-props['width']/2.0, -props['length']/2.0),
            (-props['width']/2.0, props['length']/2.0)
        ], closed=True)
    else:
        outer_curve = builder.circle((0.,0.), radius=props['length']/2.0)
    
    # Create hole if needed
    if props['has_hole']:
        inner_curve = builder.circle((0.,0.), radius=props['hole_diameter']/2.0)
        profile = builder.profile(outer_curve, inner_curves=[inner_curve], name="bearing pad profile")
    else:
        profile = builder.profile(outer_curve, name="bearing pad profile")
    
    # Create representation    
    inch_to_m_factor = 0.0254
    profile_representation = ifcopenshell.api.geometry.add_profile_representation(
        model,
        context=model.by_type("IfcGeometricRepresentationContext")[0],
        profile=profile,
        depth=props['thickness'] * inch_to_m_factor
    )
    profile_representation.RepresentationIdentifier = "Body"
    
    # Assign representation
    ifcopenshell.api.geometry.assign_representation(
        model,
        product=bearing_pad,
        representation=profile_representation
    )
    print("Created shape representation")


def set_pad_properties(model, pset, props):
    """Set the pad properties in the IFC model."""
    
    # Set basic properties
    ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={
        "Hole Diameter [in]": props['hole_diameter'],
        #"Pad Material Designation": "Neoprene"
    })
    
    # Set dimensional properties based on shape
    if props['is_rectangular']:
        ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={
            "Pad Length [in]": props['length'],
            "Pad Width [in]": props['width'],
        })
    else:
        ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={
            "Pad Diameter [in]": props['length']
        })
    
    # Set thickness
    ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={
        "Pad Height [in]": props['thickness'],
    })

    ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={
        "Hardness": props['hardness'],
    })


def set_shim_properties(model, pset, props):
    """Set the steel shim properties in the IFC model."""
    
    # Set basic shim properties
    ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={
        "Quantity of Steel Shims": props['num_shims'],
        #"Steel Shim Clear Cover [in]": props['clear_cover'],
        "Steel Shim Thickness [in]": props['height'],
        "Steel Shim Spacing [in]": props['spacing'],
        #"Steel Shim Material Designation": "ASTM A709 Grade 36" if props['num_shims'] > 0 else ""
    })
    
    # Set dimensional properties based on shape
    if props['length'] > 0:
        ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={
            "Steel Shim Length [in]": props['length'],
            "Steel Shim Width [in]": props['width'],
        })
    else:
        ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={
            "Steel Shim Diameter [in]": props['length']
        })


def set_properties_general(model, bearing_pad):
    pset_generalproperties = ifcopenshell.api.pset.add_pset(model, product=bearing_pad, name="General Properties")

    ifcopenshell.api.pset.edit_pset(model, pset=pset_generalproperties, properties={"Location for Quantity": "Superstructure"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_generalproperties, properties={"Material": "Varies"})


def set_properties_layout(model, bearing_pad):
    pset_layout = ifcopenshell.api.pset.add_pset(model, product=bearing_pad, name="Layout")

    ifcopenshell.api.pset.edit_pset(model, pset=pset_layout, properties={"Centerline of Bearing Offset from Horizontal Control Line (HCL) [ft]": -15.5})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_layout, properties={"Distance from Centerline of Bearing to Centerline of Support [ft]": 0.0})


def set_properties_penndot_bearing(model, bearing_pad):
    pset_penndot_bearing = ifcopenshell.api.pset.add_pset(model, product=bearing_pad, name="PennDOT_Bearing")

    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearing, properties={"Details/Notes": "See 2D Details and Notes"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearing, properties={"NBI#": "310"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearing, properties={"Element Detail Designation (EDD)": "D-2"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearing, properties={"Element Information Designation (EID)": "I-2"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearing, properties={"Applicable BC Standards": "BC-755M"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearing, properties={"Fixity": "Fixed"})


def set_properties_penndot_bearing_payitem(model, bearing_pad):
    pset_penndot_bearingpayitem = ifcopenshell.api.pset.add_pset(model, product=bearing_pad, name="PennDOT_BearingPayItem")

    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearingpayitem, properties={"Designation": "None"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearingpayitem, properties={"ECMS Pay Item": "(Part of LS 8120-0001)"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearingpayitem, properties={"Description": "Laminated neoprene bearing pad"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearingpayitem, properties={"Unit": "Each"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearingpayitem, properties={"Note1": "See approximate quantity table in 2D Details and Notes."})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_bearingpayitem, properties={"Note2": "None"})


def set_properties_penndot_soleplate_payitem(model, bearing_pad):
    pset_penndot_soleplatepayitem = ifcopenshell.api.pset.add_pset(model, product=bearing_pad, name="PennDOT_SolePlatePayItem")

    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_soleplatepayitem, properties={"Designation": "None"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_soleplatepayitem, properties={"ECMS Pay Item": "(Part Of LS 8120-0001)"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_soleplatepayitem, properties={"Description": "Fabricated structural steel"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_soleplatepayitem, properties={"Unit": "lb"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_soleplatepayitem, properties={"Note1": "See approximate quantity table in 2D Details and Notes."})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_soleplatepayitem, properties={"Note2": "None"})


def set_properties_penndot_anchorbolt_payitem(model, bearing_pad):
    pset_penndot_anchorboltpayitem = ifcopenshell.api.pset.add_pset(model, product=bearing_pad, name="PennDOT_AnchorBoltPayItem")

    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_anchorboltpayitem, properties={"Designation": "None"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_anchorboltpayitem, properties={"ECMS Pay Item": "(Part Of LS 8120-0001)"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_anchorboltpayitem, properties={"Description": "Fabricated structural steel, galvanized"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_anchorboltpayitem, properties={"Unit": "lb"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_anchorboltpayitem, properties={"Note1": "See approximate quantity table in 2D Details and Notes."})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_anchorboltpayitem, properties={"Note2": "None"})


def set_properties_penndot_anchorbolt(model, bearing_pad):
    pset_penndot_anchorbolt = ifcopenshell.api.pset.add_pset(model, product=bearing_pad, name="PennDOT_AnchorBolt")

    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_anchorbolt, properties={"Diameter [in]": 1.5})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_anchorbolt, properties={"Length [in]": 22.5})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_anchorbolt, properties={"Location": "Pier 1 Girder 1"})
    ifcopenshell.api.pset.edit_pset(model, pset=pset_penndot_anchorbolt, properties={"Type": "Bearing anchor bolt"})


def get_bearing(pad):
    print(f"pad length [in]: {pad.Length}")
    print(f"pad width [in]: {pad.Width}")
    print(f"pad height [in]: {pad.Thickness}")

    pad_type = type(pad)
    print(f"The type is: {pad_type}")

    if "LaminatedPad" in str(pad_type):
        print(f"Number of layers: {pad.NumberOfLayers}")
        print(f"Elastomer Interior Thickness [in]: {pad.ElastomerInteriorThickness}")
        print(f"Elastomer Cover Thickness [in]: {pad.ElastomerCoverThickness}")
        print(f"Thickness of shim plates [in]: {pad.ShimThickness}")

    if str(pad.Shape) == "Rectangular":
        print(f"Pad is rectangular")
    elif str(pad.Shape) == "Circular":
        print(f"Pad is circular")