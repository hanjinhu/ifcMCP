"""
IFC Roadway Hierarchy Converter - Functional Version

This script converts IFC building models to proper roadway hierarchy structures.
It transforms IfcBuilding and IfcBuildingElementProxy entities into appropriate
roadway elements like IfcRoad, IfcRoadPart, and IfcCourse.

Author: Hanjin Hu
Organization: Michael Baker International
"""

import site
import ifcopenshell
import ifcopenshell.api.root
import ifcopenshell.api.unit
import ifcopenshell.api.context
import ifcopenshell.api.project
import ifcopenshell.api.spatial
import ifcopenshell.api.geometry
import ifcopenshell.api.aggregate
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.style
import ifcopenshell.api.layer

from xml.parsers.expat import model
import os
import csv
import datetime


# Configuration Constants
CARRIAGEWAY_TOP_LAYER_INDICES = {21}
CARRIAGEWAY_BASE_LAYER_INDICES = {20}
CARRIAGEWAY_SUBBASE_LAYER_INDICES = {25}
INTERSECTION1_TOP_LAYER_INDICES = {35}
INTERSECTION1_BASE_LAYER_INDICES = {36, 53, 76}
INTERSECTION1_SUBBASE_LAYER_INDICES = {37, 55, 80}
INTERSECTION2_TOP_LAYER_INDICES = {32, 136}
INTERSECTION2_BASE_LAYER_INDICES = {28, 33, 63, 100, 106, 95, 86}
INTERSECTION2_SUBBASE_LAYER_INDICES = {30, 34, 65, 87, 91, 71, 104}
DRIVEWAY_BASE_LAYER_INDICES = {38, 40, 43, 48}
DRIVEWAY_SUBBASE_LAYER_INDICES = {39, 41, 44, 49}
ROADSIDE_EARTHWORKSFILL_SLOPEFILL_INDICES = {23, 135}

# Indices to skip during processing
SKIPPED_INDICES = {121}


def convert_ifc_roadway_hierarchy(file_name, output_filename=None):
    """Main conversion function that orchestrates the entire process."""
    print("="*50)
    print("Starting IFC Roadway Hierarchy Conversion")
    print("="*50)

    if output_filename is None:
        current_time = datetime.datetime.now().strftime('%Y%m%d_%H%M').lower()
        output_filename = f"TxDOT Roadway Example_{current_time}.ifc"

    try:
        # Load the model
        model, project, site1, site2 = load_ifc_model(file_name)

        # Update the project context
        project.Name = "project_" + project.Name

        #person = ifcopenshell.api.owner.add_person(model, identification="HHu", family_name="Hu", given_name="Hanjin")
        #organisation = ifcopenshell.api.owner.add_organisation(model, identification="MBI", name="Michael Baker International")
        #person_and_org = ifcopenshell.api.owner.add_person_and_organisation(model, person=person, organisation=organisation)
        #ifcopenshell.api.owner.add_role(model, assigned_object=person_and_org, role="ENGINEER")
        #ifcopenshell.api.owner.assign_actor(model, relating_actor=organisation, related_object=project)

        # Get the resolved file path for saving
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ifc_dir = os.path.join(script_dir, "IFC")
        csv_dir = os.path.join(script_dir, "csv")
        if not os.path.dirname(file_name):
            resolved_file_path = os.path.join(ifc_dir, file_name)
        else:
            resolved_file_path = file_name

        # Create the road and road part entities
        road = create_road_entity(model, site1)

        roadpart_road_segment = create_roadpart_road_segment(model, road)
        roadpart_carriageway = create_roadpart(
            model, roadpart_road_segment, "CARRIAGEWAY")
        roadpart_intersection1 = create_roadpart(
            model, roadpart_road_segment, "INTERSECTION")
        roadpart_intersection2 = create_roadpart(
            model, roadpart_road_segment, "INTERSECTION")
        roadpart_userdefined_driveway = create_roadpart(
            model, roadpart_road_segment, "USERDEFINED:DRIVEWAY")
        roadpart_roadside = create_roadpart(
            model, roadpart_road_segment, "ROADSIDE")
        
        roadpart_intersection1.Name = "Intersection_FM621"
        roadpart_intersection2.Name = "Intersection_ParkAve"

        # Remove all the existing layer styles
        remove_rep_layer_with_style(model)

        # Process building element proxies
        process_building_element_proxies(model, site1, roadpart_carriageway, roadpart_intersection1,
                                                      roadpart_intersection2, roadpart_userdefined_driveway, roadpart_roadside)

        # Process buildings (starting from where proxies left off)
        process_buildings(model, site1, roadpart_carriageway, roadpart_intersection1, roadpart_intersection2,
                          roadpart_userdefined_driveway, roadpart_roadside)

        # Merge sites
        merge_sites(model, site1, site2)

        # Remove annotations from site
        remove_annotations_from_site(model, site1)

        # Remove all orphaned entities
        remove_all_orphaned_entities(model)

        # Add psets and properties
        add_properties_project(model, project)

        # Save the model
        output_path = save_model(model, resolved_file_path, output_filename)

        print("="*50)
        print("Conversion completed successfully!")
        print(f"Output file: {output_path}")
        print("="*50)

        return output_path
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def remove_rep_layer_with_style(model):
    styles = model.by_type("IfcPresentationLayerWithStyle")

    for style in styles:
        #if style.Name == "Road_Pave_SealCoat":
        model.remove(style)


def initialize_styles(model):
    """Initialize and return commonly used styles."""
    top_layer_rep_layerwithstyle, top_layer_surface_style = create_layer_with_style(
        model,
        layer_name="TopLayer",
        surface_colour={"Red": 0.6, "Green": 1.0, "Blue": 0.6},
        transparency=0.0,
    )

    base_layer_rep_layerwithstyle, base_layer_surface_style = create_layer_with_style(
        model,
        layer_name="BaseLayer",
        surface_colour={"Red": 0.4, "Green": 1.0, "Blue": 1.0},
        transparency=0.0,
    )

    subgrade_rep_layerwithstyle, subgrade_surface_style = create_layer_with_style(
        model,
        layer_name="SubgradeLayer",
        surface_colour={"Red": 1.0, "Green": 1.0, "Blue": 0.8},
        transparency=0.0,
    )

    slopefill_rep_layerwithstyle, slopefill_surface_style = create_layer_with_style(
        model,
        layer_name="SlopeFillLayer",
        surface_colour={"Red": 1.0, "Green": 0.6, "Blue": 1.0},
        transparency=0.0,
    )

    return {
        "top_layer": {
            "rep_layer_with_style": top_layer_rep_layerwithstyle,
            "surface_style": top_layer_surface_style,
        },
        "base_layer": {
            "rep_layer_with_style": base_layer_rep_layerwithstyle,
            "surface_style": base_layer_surface_style,
        },
        "subgrade_layer": {
            "rep_layer_with_style": subgrade_rep_layerwithstyle,
            "surface_style": subgrade_surface_style,
        },
        "slopefill_layer": {
            "rep_layer_with_style": slopefill_rep_layerwithstyle,
            "surface_style": slopefill_surface_style,
        },
    }


def assign_style_and_layer(model, layer, surface_style, layer_with_style):
    """Assigns style and layer to the given layer."""
    layer_rep = layer.Representation
    layer_shape_rep = layer_rep.Representations[0]
    tessellation = layer_shape_rep.Items[0]
    _ = ifcopenshell.api.style.assign_item_style(model, style=surface_style, item=tessellation)
    ifcopenshell.api.layer.assign_layer(model, items=[tessellation], layer=layer_with_style)


def add_surface_style(model, project):
    carriageway_style = ifcopenshell.api.style.add_style(model)

    carriageway_surface_style = ifcopenshell.api.style.add_surface_style(model,
        style=carriageway_style, ifc_class="IfcSurfaceStyleShading", attributes={
        "SurfaceColour": { "Name": None, "Red": 1.0, "Green": 0.8, "Blue": 0.8 },
        "Transparency": 1., # 0 is opaque, 1 is transparent
    })

    site = project.IsDecomposedBy[0].RelatedObjects[0]
    road = site.IsDecomposedBy[0].RelatedObjects[0]
    roadpart_road_segment = road.IsDecomposedBy[0].RelatedObjects[0]

    for roadpart in roadpart_road_segment.IsDecomposedBy[0].RelatedObjects:
        if roadpart.PredefinedType == "CARRIAGEWAY":
            #add_properties_roadpart_carriageway(model, roadpart)
            #ifcopenshell.api.style.assign_item_style(model, style=style, item=roadpart.representation)
            if 'TopLayer' in roadpart.Name:
                roadpart.get_info()
                roadpart_rep = roadpart.Representation
                roadpart_shape_rep = roadpart_rep.Representations[0]
                ifcopenshell.api.style.assign_item_style(model, style=carriageway_style, item=roadpart_shape_rep.Items[0])
        elif roadpart.PredefinedType == "INTERSECTION" and roadpart.Name == "INTER_FM621":
            #add_properties_roadpart_intersection1(model, roadpart)
            pass
        elif roadpart.PredefinedType == "INTERSECTION" and roadpart.Name == "INTER_PARK_AVE":
            # Currently no specific properties for intersection2
            pass
        elif roadpart.PredefinedType == "USERDEFINED":
            #add_properties_roadpart_userdefined_driveway(model, roadpart)
            pass
        elif roadpart.PredefinedType == "ROADSIDE":
            #add_properties_roadpart_roadside(model, roadpart)
            pass
        else:
            # Python equivalent of C# Debug.Assert
            assert roadpart.PredefinedType in {
                "CARRIAGEWAY", "INTERSECTION", "USERDEFINED", "ROADSIDE"}, f"Unexpected road part type: {roadpart.PredefinedType}"
            print(f"Unknown road part type: {roadpart.PredefinedType}")


def load_ifc_model(file_name):
    """Load the IFC model and return basic elements."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # If file_name is just a filename (no path), look in the script directory
    if not os.path.dirname(file_name):
        file_path = os.path.join(script_dir, file_name)
    else:
        file_path = file_name

    print(f"Loading IFC model: {file_path}")

    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"IFC file not found: {file_path}")

    model = ifcopenshell.open(file_path)
    project = model.by_type("IfcProject")[0]

    # Get the two sites
    project_related_objects = project.IsDecomposedBy[0].RelatedObjects
    for obj in project_related_objects:
        print(f"Project related object: {obj.get_info()}")

    # Check if we have at least two sites
    if len(project_related_objects) < 2:
        raise ValueError(f"Expected at least 2 sites under project, but found {len(project_related_objects)}. "
                         f"Available sites: {[obj.Name for obj in project_related_objects]}")

    site1 = project_related_objects[0]  # "Road" site
    # "143402005-FM1977-RDW-CORR-MASTER-3D" site
    site2 = project_related_objects[1]

    print(f"Site1: {site1.Name}")
    print(f"Site2: {site2.Name}")

    return model, project, site1, site2


def create_road_entity(model, site1):
    """Create a new IfcRoad entity and assign it to site1."""
    print("Creating IfcRoad entity...")
    road = ifcopenshell.api.root.create_entity(
        model,
        ifc_class="IfcRoad",
        name="FM1977"
    )
    ifcopenshell.api.aggregate.assign_object(
        model,
        relating_object=site1,
        products=[road]
    )
    print(f"Created road: {road.Name}")
    return road


def create_roadpart_road_segment(model, road):
    """Create a new IfcRoadPart.ROADSEGMENT and assign it to road."""
    print("Creating IfcRoadPart entity...")
    roadpart_road_segment = ifcopenshell.api.root.create_entity(
        model,
        ifc_class="IfcRoadPart",
        predefined_type="ROADSEGMENT",
        name="FM1977_Segment1"
    )
    ifcopenshell.api.aggregate.assign_object(
        model,
        relating_object=road,
        products=[roadpart_road_segment]
    )
    print(f"Created road part: {roadpart_road_segment.Name}")
    return roadpart_road_segment


def create_roadpart(model, roadpart_road_segment, predefined_type, name=None):
    """
    Create a new IfcRoadPart with the given predefined_type and assign it to road segment.
    Supported predefined_types: 'CARRIAGEWAY', 'ROADSIDE', 'INTERSECTION', 'USERDEFINED' (with name 'DRIVEWAY')
    """
    print(f"Creating IfcRoadPart entity of type {predefined_type}...")

    # Default names for standard types
    if name is None:
        if predefined_type == "CARRIAGEWAY":
            name = "Lane"
        elif predefined_type == "ROADSIDE":
            name = "RoadsideGrading"
        elif predefined_type == "INTERSECTION":
            name = "Intersection"
        elif predefined_type == "USERDEFINED:DRIVEWAY":
            name = "Driveways"
        else:
            name = "RoadPart"

    roadpart = ifcopenshell.api.root.create_entity(
        model,
        ifc_class="IfcRoadPart",
        predefined_type=predefined_type,
        name=name
    )

    ifcopenshell.api.aggregate.assign_object(
        model,
        relating_object=roadpart_road_segment,
        products=[roadpart]
    )

    print(f"Created road part: {roadpart.Name}")
    return roadpart


def convert_building_elem_proxy_to_roadpart(model, building_elem_proxy):
    """Convert IfcBuildingElementProxy to IfcRoadPart."""
    if not building_elem_proxy.is_a("IfcBuildingElementProxy"):
        return None

    # Create a new IfcRoadPart entity
    roadpart = ifcopenshell.api.root.create_entity(
        model,
        ifc_class="IfcRoadPart",
        predefined_type="ROADSEGMENT",
        name=building_elem_proxy.Name
    )

    # Copy properties
    if building_elem_proxy.OwnerHistory:
        roadpart.OwnerHistory = building_elem_proxy.OwnerHistory

    if building_elem_proxy.ObjectPlacement:
        roadpart.ObjectPlacement = building_elem_proxy.ObjectPlacement

    if building_elem_proxy.Representation:
        roadpart.Representation = building_elem_proxy.Representation

    if building_elem_proxy.Tag:
        roadpart.LongName = building_elem_proxy.Tag

    return roadpart


def convert_building_element_proxy_to_entity(model, building_element_proxy, target_class, predefined_type):
    """Convert IfcBuildingElementProxy to specified IFC entity type.

    Args:
        model: The IFC model
        building_element_proxy: The source IfcBuildingElementProxy
        target_class: Target IFC class (e.g., "IfcCourse", "IfcEarthworksFill")
        predefined_type: Predefined type for the target entity (e.g., "PAVEMENT", "SLOPEFILL")

    Returns:
        The newly created entity or None if conversion fails
    """
    if not building_element_proxy.is_a("IfcBuildingElementProxy"):
        return None

    # Create a new entity of the specified type
    new_entity = ifcopenshell.api.root.create_entity(
        model,
        ifc_class=target_class,
        predefined_type=predefined_type,
        name=building_element_proxy.Name
    )

    # Warning: the psets and properties of the building element proxy are not copied over!!

    # Copy properties
    if building_element_proxy.OwnerHistory:
        new_entity.OwnerHistory = building_element_proxy.OwnerHistory

    if building_element_proxy.ObjectPlacement:
        new_entity.ObjectPlacement = building_element_proxy.ObjectPlacement

    if building_element_proxy.Representation:
        new_entity.Representation = building_element_proxy.Representation

    if building_element_proxy.Tag:
        new_entity.Tag = building_element_proxy.Tag

    return new_entity


# Helper functions for specific entity types
def create_pavement_layer(model, building_element_proxy):
    """Create an IfcCourse with PAVEMENT predefined type."""
    return convert_building_element_proxy_to_entity(model, building_element_proxy, "IfcCourse", "PAVEMENT")


def create_earthworks_fill(model, building_element_proxy, predefined_type):
    """Create an IfcEarthworksFill with a predefined type."""
    return convert_building_element_proxy_to_entity(model, building_element_proxy, "IfcEarthworksFill", predefined_type)


def convert_building_to_building_element_proxy(model, building):
    """Convert IfcBuilding to IfcBuildingElementProxy."""
    if not building.is_a("IfcBuilding"):
        return None

    # Create a new IfcBuildingElementProxy entity
    building_element_proxy = ifcopenshell.api.root.create_entity(
        model,
        ifc_class="IfcBuildingElementProxy",
        name=building.Name
    )

    # Copy properties
    if building.OwnerHistory:
        building_element_proxy.OwnerHistory = building.OwnerHistory

    if building.ObjectPlacement:
        building_element_proxy.ObjectPlacement = building.ObjectPlacement

    if building.Representation:
        building_element_proxy.Representation = building.Representation

    if building.LongName:
        building_element_proxy.Tag = building.LongName

    return building_element_proxy


def process_building_element_proxies(model, site1, roadpart_carriageway, roadpart_intersection1,
                                     roadpart_intersection2, roadpart_userdefined_driveway, roadpart_roadside):
    """Process all IfcBuildingElementProxy entities under site1."""
    print("Processing IfcBuildingElementProxy entities...")

    # Get all the IfcBuildingElementProxy entities and IfcAnnotation entities that hang under site1
    site_related_elements = site1.ContainsElements[0].RelatedElements

    # Move all the IfcBuildingElementProxy entities and IfcAnnotation entities under site1 to hang under the new IfcRoad
    styles = initialize_styles(model)

    top_layer_rep_layerwithstyle = styles["top_layer"]["rep_layer_with_style"]
    top_layer_surface_style = styles["top_layer"]["surface_style"]

    base_layer_rep_layerwithstyle = styles["base_layer"]["rep_layer_with_style"]
    base_layer_surface_style = styles["base_layer"]["surface_style"]

    subgrade_rep_layerwithstyle = styles["subgrade_layer"]["rep_layer_with_style"]
    subgrade_surface_style = styles["subgrade_layer"]["surface_style"]

    slopefill_rep_layerwithstyle = styles["slopefill_layer"]["rep_layer_with_style"]
    slopefill_surface_style = styles["slopefill_layer"]["surface_style"]

    # Process IfcBuildingElementProxy entities
    processed_count = 0
    for elem in site_related_elements:
        if not elem.is_a("IfcBuildingElementProxy"):
            continue

        ifcopenshell.api.spatial.unassign_container(model, products=[elem])

        index = get_index_from_name(elem.Name)

        if index is None:
            AssertionError(f"Failed to get index from name: {elem.Name}")

        # Handle different layer types based on index
        if index in CARRIAGEWAY_TOP_LAYER_INDICES:
            layer = create_pavement_layer(model, elem)
            if layer is not None:
                layer.Name = f"[{index}]_TopLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_carriageway,
                    products=[layer]
                )

                # Assign style to the top layer
                assign_style_and_layer(model, layer, top_layer_surface_style, top_layer_rep_layerwithstyle)
        elif index in CARRIAGEWAY_BASE_LAYER_INDICES:
            layer = create_pavement_layer(model, elem)
            if layer is not None:
                layer.Name = f"[{index}]_BaseLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_carriageway,
                    products=[layer]
                )

                # Assign style to the base layer
                assign_style_and_layer(model, layer, base_layer_surface_style, base_layer_rep_layerwithstyle)
        elif index in CARRIAGEWAY_SUBBASE_LAYER_INDICES:
            earthworks = create_earthworks_fill(model, elem, "SUBGRADE")
            if earthworks is not None:
                earthworks.Name = f"[{index}]_Earthworks_Fill_SUBGRADE"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_carriageway,
                    products=[earthworks]
                )

                # Assign style to the subgrade layer
                assign_style_and_layer(model, earthworks, subgrade_surface_style, subgrade_rep_layerwithstyle)
        elif index in INTERSECTION1_TOP_LAYER_INDICES:
            layer = create_pavement_layer(model, elem)
            if layer is not None:
                layer.Name = f"[{index}]_TopLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection1,
                    products=[layer]
                )

                # Assign style to the top layer
                assign_style_and_layer(model, layer, top_layer_surface_style, top_layer_rep_layerwithstyle)
        elif index in INTERSECTION1_BASE_LAYER_INDICES:
            layer = create_pavement_layer(model, elem)
            if layer is not None:
                layer.Name = f"[{index}]_BaseLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection1,
                    products=[layer]
                )

                # Assign style to the base layer
                assign_style_and_layer(model, layer, base_layer_surface_style, base_layer_rep_layerwithstyle)
        elif index in INTERSECTION1_SUBBASE_LAYER_INDICES:
            earthworks = create_earthworks_fill(model, elem, "SUBGRADE")
            if earthworks is not None:
                earthworks.Name = f"[{index}]_Earthworks_Fill_SUBGRADE"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection1,
                    products=[earthworks]
                )

                # Assign style to the subgrade layer
                assign_style_and_layer(model, earthworks, subgrade_surface_style, subgrade_rep_layerwithstyle)
        elif index in INTERSECTION2_TOP_LAYER_INDICES:
            layer = create_pavement_layer(model, elem)
            if layer is not None:
                layer.Name = f"[{index}]_TopLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection2,
                    products=[layer]
                )

                # Assign style to the top layer
                assign_style_and_layer(model, layer, top_layer_surface_style, top_layer_rep_layerwithstyle)
        elif index in INTERSECTION2_BASE_LAYER_INDICES:
            layer = create_pavement_layer(model, elem)
            if layer is not None:
                layer.Name = f"[{index}]_BaseLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection2,
                    products=[layer]
                )

                # Assign style to the base layer
                assign_style_and_layer(model, layer, base_layer_surface_style, base_layer_rep_layerwithstyle)
        elif index in INTERSECTION2_SUBBASE_LAYER_INDICES:
            earthworks = create_earthworks_fill(model, elem, "SUBGRADE")
            if earthworks is not None:
                earthworks.Name = f"[{index}]_Earthworks_Fill_SUBGRADE"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection2,
                    products=[earthworks]
                )

                # Assign style to the subgrade layer
                assign_style_and_layer(model, earthworks, subgrade_surface_style, subgrade_rep_layerwithstyle)
        elif index in DRIVEWAY_BASE_LAYER_INDICES:
            layer = create_pavement_layer(model, elem)
            if layer is not None:
                layer.Name = f"[{index}]_BaseLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_userdefined_driveway,
                    products=[layer]
                )

                # Assign style to the base layer
                assign_style_and_layer(model, layer, base_layer_surface_style, base_layer_rep_layerwithstyle)
        elif index in DRIVEWAY_SUBBASE_LAYER_INDICES:
            earthworks = create_earthworks_fill(model, elem, "SUBGRADE")
            if earthworks is not None:
                earthworks.Name = f"[{index}]_Earthworks_Fill_SUBGRADE"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_userdefined_driveway,
                    products=[earthworks]
                )

                # Assign style to the subgrade layer
                assign_style_and_layer(model, earthworks, subgrade_surface_style, subgrade_rep_layerwithstyle)
        else:
            earthworks = create_earthworks_fill(model, elem, "SLOPEFILL")
            if earthworks is not None:
                earthworks.Name = f"[{index}]_Earthworks_Fill_SLOPEFILL"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_roadside,
                    products=[earthworks]
                )
                # Assign style to the slope fill layer
                assign_style_and_layer(model, earthworks, slopefill_surface_style, slopefill_rep_layerwithstyle)

        processed_count += 1

    print(f"Processed {processed_count} IfcBuildingElementProxy entities")


def process_buildings(model, site1, roadpart_carriageway, roadpart_intersection1,
                      roadpart_intersection2, roadpart_userdefined_driveway, roadpart_roadside):
    """Process all IfcBuilding entities under site1."""
    print("Processing IfcBuilding entities...")

    # Get all the IfcBuilding entities under site1
    site_related_objects = site1.IsDecomposedBy[0].RelatedObjects

    styles = initialize_styles(model)

    top_layer_rep_layerwithstyle = styles["top_layer"]["rep_layer_with_style"]
    top_layer_surface_style = styles["top_layer"]["surface_style"]

    base_layer_rep_layerwithstyle = styles["base_layer"]["rep_layer_with_style"]
    base_layer_surface_style = styles["base_layer"]["surface_style"]

    subgrade_rep_layerwithstyle = styles["subgrade_layer"]["rep_layer_with_style"]
    subgrade_surface_style = styles["subgrade_layer"]["surface_style"]

    slopefill_rep_layerwithstyle = styles["slopefill_layer"]["rep_layer_with_style"]
    slopefill_surface_style = styles["slopefill_layer"]["surface_style"]

    processed_count = 0

    # Remove all the IfcBuilding entities under site1
    for obj in site_related_objects:
        if not obj.is_a("IfcBuilding"):
            continue

        building_element_proxy = convert_building_to_building_element_proxy(
            model, obj)

        if building_element_proxy is None:
            continue

        #building_element_proxy.Name = f"[{index}]_BuildingElementProxy"

        ifcopenshell.api.spatial.unassign_container(
            model,
            products=[building_element_proxy]
        )

        index = get_index_from_name(obj.Name)

        if index in SKIPPED_INDICES:
            continue

        if index is None:
            AssertionError(f"Failed to get index from name: {obj.Name}")

        if index in CARRIAGEWAY_TOP_LAYER_INDICES:
            layer = create_pavement_layer(model, building_element_proxy)
            if layer is not None:
                layer.Name = f"[{index}]_TopLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_carriageway,
                    products=[layer]
                )
                assign_style_and_layer(model, layer, top_layer_surface_style, top_layer_rep_layerwithstyle)
        elif index in CARRIAGEWAY_BASE_LAYER_INDICES:
            layer = create_pavement_layer(model, building_element_proxy)
            if layer is not None:
                layer.Name = f"[{index}]_BaseLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_carriageway,
                    products=[layer]
                )
                assign_style_and_layer(model, layer, base_layer_surface_style, base_layer_rep_layerwithstyle)
        elif index in CARRIAGEWAY_SUBBASE_LAYER_INDICES:
            earthworks = create_earthworks_fill(
                model, building_element_proxy, "SUBGRADE")
            if earthworks is not None:
                earthworks.Name = f"[{index}]_Earthworks_Fill_SUBGRADE"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_carriageway,
                    products=[earthworks]
                )
                assign_style_and_layer(model, earthworks, subgrade_surface_style, subgrade_rep_layerwithstyle)
        elif index in INTERSECTION1_TOP_LAYER_INDICES:
            layer = create_pavement_layer(model, building_element_proxy)
            if layer is not None:
                layer.Name = f"[{index}]_TopLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection1,
                    products=[layer]
                )
                assign_style_and_layer(model, layer, top_layer_surface_style, top_layer_rep_layerwithstyle)
        elif index in INTERSECTION1_BASE_LAYER_INDICES:
            layer = create_pavement_layer(model, building_element_proxy)
            if layer is not None:
                layer.Name = f"[{index}]_BaseLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection1,
                    products=[layer]
                )
                assign_style_and_layer(model, layer, base_layer_surface_style, base_layer_rep_layerwithstyle)
        elif index in INTERSECTION1_SUBBASE_LAYER_INDICES:
            earthworks = create_earthworks_fill(
                model, building_element_proxy, "SUBGRADE")
            if earthworks is not None:
                earthworks.Name = f"[{index}]_Earthworks_Fill_SUBGRADE"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection1,
                    products=[earthworks]
                )
                assign_style_and_layer(model, earthworks, subgrade_surface_style, subgrade_rep_layerwithstyle)
        elif index in INTERSECTION2_TOP_LAYER_INDICES:
            layer = create_pavement_layer(model, building_element_proxy)
            if layer is not None:
                layer.Name = f"[{index}]_TopLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection2,
                    products=[layer]
                )
                assign_style_and_layer(model, layer, top_layer_surface_style, top_layer_rep_layerwithstyle)
        elif index in INTERSECTION2_BASE_LAYER_INDICES:
            layer = create_pavement_layer(model, building_element_proxy)
            if layer is not None:
                layer.Name = f"[{index}]_BaseLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection2,
                    products=[layer]
                )
                assign_style_and_layer(model, layer, base_layer_surface_style, base_layer_rep_layerwithstyle)
        elif index in INTERSECTION2_SUBBASE_LAYER_INDICES:
            earthworks = create_earthworks_fill(
                model, building_element_proxy, "SUBGRADE")
            if earthworks is not None:
                earthworks.Name = f"[{index}]_Earthworks_Fill_SUBGRADE"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_intersection2,
                    products=[earthworks]
                )
                assign_style_and_layer(model, earthworks, subgrade_surface_style, subgrade_rep_layerwithstyle)
        elif index in DRIVEWAY_BASE_LAYER_INDICES:
            layer = create_pavement_layer(model, building_element_proxy)
            if layer is not None:
                layer.Name = f"[{index}]_BaseLayer"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_userdefined_driveway,
                    products=[layer]
                )
                assign_style_and_layer(model, layer, base_layer_surface_style, base_layer_rep_layerwithstyle)
        elif index in DRIVEWAY_SUBBASE_LAYER_INDICES:
            earthworks = create_earthworks_fill(
                model, building_element_proxy, "SUBGRADE")
            if earthworks is not None:
                earthworks.Name = f"[{index}]_Earthworks_Fill_SUBGRADE"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_userdefined_driveway,
                    products=[earthworks]
                )
                assign_style_and_layer(model, earthworks, subgrade_surface_style, subgrade_rep_layerwithstyle)
        else:
            earthworks = create_earthworks_fill(
                model, building_element_proxy, "SLOPEFILL")
            if earthworks is not None:
                earthworks.Name = f"[{index}]_Earthworkss_Fill_SLOPEFILL"
                ifcopenshell.api.spatial.assign_container(
                    model,
                    relating_structure=roadpart_roadside,
                    products=[earthworks]
                )
                assign_style_and_layer(model, earthworks, slopefill_surface_style, slopefill_rep_layerwithstyle)

        processed_count += 1

    print(f"Processed {processed_count} IfcBuilding entities")


def merge_sites(model, site1, site2):
    """Move all property sets from site2 to site1 and remove site2."""
    print("Merging sites...")

    # Move all the Psets from site2 to site1
    for rel in site2.IsDefinedBy:
        pset = rel.RelatingPropertyDefinition
        ifcopenshell.api.pset.assign_pset(model, [site1], pset=pset)

    # Update the name of site1 to be the name of site2
    old_site1_name = site1.Name
    site1.Name = "site_" + site2.Name

    # Remove site2 from the model
    model.remove(site2)

    print(f"Merged sites: {old_site1_name} -> {site1.Name}")


def remove_all_orphaned_entities(model):
    """Remove all orphaned IfcBuilding and IfcBuildingElementProxy entities from the model.

    These are entities that are no longer needed after conversion
    to roadway hierarchy elements. They become orphaned because their spatial
    relationships have been transferred to the new roadway elements.
    """
    print("Removing all orphaned IfcBuilding and IfcBuildingElementProxy entities...")

    # Get all the IfcBuilding entities in the model
    buildings = model.by_type("IfcBuilding")
    proxies = model.by_type("IfcBuildingElementProxy")

    print(f"Found {len(buildings)} orphaned IfcBuilding entities to remove")
    print(f"Found {len(proxies)} orphaned IfcBuildingElementProxy entities to remove")

    # Remove all the orphaned IfcBuilding entities
    building_count = 0
    for obj in buildings:
        # Do not use ifcopenshell.api.root.remove_product here, as it may remove entities that are still referenced and needed by other entities
        model.remove(obj)
        building_count += 1

    # Remove all the orphaned IfcBuildingElementProxy entities
    proxy_count = 0
    for obj in proxies:
        # Do not use ifcopenshell.api.root.remove_product here, as it may remove entities that are still referenced and needed by other entities
        model.remove(obj)
        proxy_count += 1

    print(f"Successfully removed {building_count} orphaned IfcBuilding entities and {proxy_count} orphaned IfcBuildingElementProxy entities")


def remove_annotations_from_site(model, site):
    """Remove all IfcAnnotation entities from the specified site.

    These annotations are typically no longer needed after the roadway
    hierarchy conversion and should be cleaned up.

    Args:
        model: The IFC model
        site: The IfcSite containing the annotations to remove
    """
    print("Removing IfcAnnotation entities from site...")

    # Check if site has ContainsElements relationship
    if not hasattr(site, 'ContainsElements') or not site.ContainsElements:
        print("No ContainsElements relationship found in site")
        return

    # Get all elements contained in the site
    site_related_elements = site.ContainsElements[0].RelatedElements

    # Find all IfcAnnotation entities
    annotations = [
        elem for elem in site_related_elements if elem.is_a("IfcAnnotation")]

    print(f"Found {len(annotations)} IfcAnnotation entities to remove")

    # Remove each annotation
    for annotation in annotations:
        print(f"Removing IfcAnnotation: {annotation.Name}")

        # First unassign from spatial container
        ifcopenshell.api.spatial.unassign_container(
            model, products=[annotation])

        # Then remove from model
        model.remove(annotation)

    print(f"Successfully removed {len(annotations)} IfcAnnotation entities")


def save_model(model, file_name, output_filename="TxDOT Roadway Example.ifc"):
    """Save the converted model to a file."""
    # Get the directory where the input file is located
    if os.path.dirname(file_name):
        output_dir = os.path.dirname(file_name)
    else:
        # If input file has no path, use the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = script_dir

    output_path = os.path.join(output_dir, output_filename)
    model.write(output_path)
    print(f"Model saved to: {output_path}")
    return output_path


def add_properties_project(model, project):
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, "csv", "project.csv")
    add_psets_from_csv(model, project, csv_path)

    site = project.IsDecomposedBy[0].RelatedObjects[0]
    add_properties_site(model, site)


def add_properties_site(model, site):
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, "csv", "site.csv")
    add_psets_from_csv(model, site, csv_path)

    road = site.IsDecomposedBy[0].RelatedObjects[0]
    roadpart_road_segment = road.IsDecomposedBy[0].RelatedObjects[0]

    add_properties_roadpart_roadsegment(model, roadpart_road_segment)

    for roadpart in roadpart_road_segment.IsDecomposedBy[0].RelatedObjects:
        if roadpart.PredefinedType == "CARRIAGEWAY":
            add_properties_roadpart_carriageway(model, roadpart)
        elif roadpart.PredefinedType == "INTERSECTION" and roadpart.Name == "Intersection_FM621":
            add_properties_roadpart_intersection1(model, roadpart)
        elif roadpart.PredefinedType == "INTERSECTION" and roadpart.Name == "Intersection_ParkAve":
            # Currently no specific properties for intersection2
            pass
        elif roadpart.PredefinedType == "USERDEFINED":
            add_properties_roadpart_userdefined_driveway(model, roadpart)
        elif roadpart.PredefinedType == "ROADSIDE":
            add_properties_roadpart_roadside(model, roadpart)
        else:
            # Python equivalent of C# Debug.Assert
            assert roadpart.PredefinedType in {
                "CARRIAGEWAY", "INTERSECTION", "USERDEFINED", "ROADSIDE"}, f"Unexpected road part type: {roadpart.PredefinedType}"
            print(f"Unknown road part type: {roadpart.PredefinedType}")


def add_psets_from_csv(model, entity, csv_path):
    pset_dict = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            pset = row["pset"].strip()
            prop = row["property"].strip()
            val = row["value"].strip()
            if pset not in pset_dict:
                pset_dict[pset] = {}
            pset_dict[pset][prop] = val
    for pset_name, properties in pset_dict.items():
        pset_entity = ifcopenshell.api.pset.add_pset(
            model, product=entity, name=pset_name)
        ifcopenshell.api.pset.edit_pset(
            model, pset=pset_entity, properties=properties)


def add_properties_roadpart_carriageway(model, roadpart):
    base_dir = os.path.dirname(__file__)
    csv_files = {
        "TopLayer": os.path.join(base_dir, "csv", "carriageway_toplayer.csv"),
        "BaseLayer": os.path.join(base_dir, "csv", "carriageway_baselayer.csv"),
        "Subgrade": os.path.join(base_dir, "csv", "carriageway_subgrade.csv"),
    }
    # Add carriageway psets to roadpart
    add_psets_from_csv(model, roadpart, os.path.join(base_dir, "csv", "carriageway.csv"))

    for road_segment in roadpart.ContainsElements[0].RelatedElements:
        if road_segment.is_a("IfcCourse") and road_segment.PredefinedType == "PAVEMENT":
            if "TopLayer" in road_segment.Name:
                csv_path = csv_files["TopLayer"]
            elif "BaseLayer" in road_segment.Name:
                csv_path = csv_files["BaseLayer"]
            else:
                csv_path = None
            if csv_path:
                add_psets_from_csv(model, road_segment, csv_path)
        elif road_segment.is_a("IfcEarthworksFill") and road_segment.PredefinedType == "SUBGRADE":
            csv_path = csv_files["Subgrade"]
            add_psets_from_csv(model, road_segment, csv_path)


def add_properties_roadpart_intersection1(model, roadpart):
    base_dir = os.path.dirname(__file__)
    add_psets_from_csv(model, roadpart, os.path.join(base_dir, "csv", "intersection.csv"))


def add_properties_roadpart_userdefined_driveway(model, roadpart):
    pass


def add_properties_roadpart_roadside(model, roadpart):
    for roadside_elem in roadpart.ContainsElements[0].RelatedElements:
        if roadside_elem.is_a("IfcEarthworksFill") and roadside_elem.PredefinedType == "SLOPEFILL":
            index = get_index_from_name(roadside_elem.Name)

            if index in ROADSIDE_EARTHWORKSFILL_SLOPEFILL_INDICES:
                add_psets_from_csv(model, roadside_elem, os.path.join(os.path.dirname(__file__), "csv", "roadside_earthworksfill_slopefill.csv"))


def add_properties_roadpart_roadsegment(model, roadpart_road_segment):
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, "csv", "roadway_roadsegment.csv")
    add_psets_from_csv(model, roadpart_road_segment, csv_path)


def debug_model_structure(file_name):
    """Debug function to examine the model structure."""
    print("="*50)
    print("DEBUG: Analyzing Model Structure")
    print("="*50)

    model, project, site1, site2 = load_ifc_model(file_name)

    print(f"\\nProject: {project.get_info()}")
    print(f"\\nSite1 ({site1.Name}):")
    if hasattr(site1, 'ContainsElements') and site1.ContainsElements:
        elements = site1.ContainsElements[0].RelatedElements
        print(f"  Contains {len(elements)} elements:")
        for i, elem in enumerate(elements):
            print(f"    {i+1}. {elem.is_a()}: {elem.Name}")

    if hasattr(site1, 'IsDecomposedBy') and site1.IsDecomposedBy:
        objects = site1.IsDecomposedBy[0].RelatedObjects
        print(f"  Decomposes into {len(objects)} objects:")
        for i, obj in enumerate(objects):
            print(f"    {i+1}. {obj.is_a()}: {obj.Name}")

    print(f"\\nSite2 ({site2.Name}):")
    if hasattr(site2, 'IsDefinedBy'):
        print(f"  Has {len(site2.IsDefinedBy)} property definitions")


def create_layer_with_style(model, layer_name, surface_colour, transparency):
    """Creates a layer with style and returns the layer and surface style."""
    layer_style = ifcopenshell.api.style.add_style(model, name=f"{layer_name}Style")

    surface_style = ifcopenshell.api.style.add_surface_style(
        model,
        style=layer_style,
        ifc_class="IfcSurfaceStyleShading",
        attributes={
            "SurfaceColour": {
                "Name": None,
                "Red": surface_colour["Red"],
                "Green": surface_colour["Green"],
                "Blue": surface_colour["Blue"]
            },
            "Transparency": transparency,
        },
    )

    layer_with_style = ifcopenshell.api.layer.add_layer_with_style(
        model, name=f"{layer_name}_surface_layer_style", on=True, styles=[layer_style]
    )

    return layer_with_style, layer_style


def get_index_from_name(elem_name):
    """Retrieve the index from the name of an element.

    Args:
        elem_name (str): The name of the element, e.g., "[1]_BuildingElementProxy".

    Returns:
        int: The index extracted from the name, or None if the format is invalid.
    """
    try:
        # Extract the part within square brackets
        index_part = elem_name.split("_")[0]
        # Remove the square brackets and convert to integer
        return int(index_part.strip("[]"))
    except (ValueError, IndexError):
        # Return None if the format is invalid
        return None

# Example usage
# index = get_index_from_name("[1]_BuildingElementProxy")


if __name__ == "__main__":
    # Configuration
    #file_name = "TxDOT 4x3 Test.ifc"
    file_name = "TxDOT 4x3 Test_indexing.ifc"
    file_full_name = os.path.join(os.path.dirname(__file__), "IFC", file_name)

    # For debugging, uncomment this line:
    # debug_model_structure(file_full_name)

    # Run the conversion
    output_file = convert_ifc_roadway_hierarchy(file_full_name)

    print(f"\nConversion complete. Output saved to: {output_file}")
