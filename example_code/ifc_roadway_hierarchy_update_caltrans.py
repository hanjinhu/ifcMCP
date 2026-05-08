"""
IFC Roadway Hierarchy - Update Existing IFC Files (Caltrans Example)

This script updates an existing IFC file to follow the roadway hierarchy structure for Caltrans example models.
"""


import ifcopenshell
import ifcopenshell.api.root
import ifcopenshell.api.unit
import ifcopenshell.api.context
import ifcopenshell.api.project
import ifcopenshell.api.geometry
import ifcopenshell.api.aggregate
import ifcopenshell.api.spatial
import ifcopenshell.api.pset

import os
import csv


def update_caltrans_ifc(file_name, output_filename="Caltrans Roadway Railing Example.ifc"):
    # Update the Caltrans IFC file to follow the roadway hierarchy structure.
    print("Starting Caltrans IFC update...")
    model = ifcopenshell.open(file_name)

    project_name = "Caltrans example project"
    road_name = "C1"
    site_name = "O1-OG921"
    road_segment_name = "RoadSegment1"
    roadside_part_name = "RoadsidePart1"

    project = update_project(model, project_name)
    print(f"Updated project name to: {project_name}")

    road = update_road(model, project, road_name)
    print(f"Updated road name to: {road_name} and break relationship with project")

    site = create_site(model, site_name)
    print(f"Created site with name: {site_name}")

    assign_hierarchy(model, project, site, road)
    print("Assigned hierarchy: Project -> Site -> Road")

    road_segment = create_road_segment(model, road, road_segment_name)
    print(f"Created road segment with name: {road_segment_name}")

    roadside_part = create_roadside_part(model, road_segment, roadside_part_name)
    print(f"Created roadside part with name: {roadside_part_name}")

    move_built_elements_to_roadside(model, road, roadside_part)
    print("Converted IfcBuiltElement to IfcRailing and assigned to roadside part")

    # Add psets and properties from CSVs
    add_properties_project(model, project)
    print("Added property sets and properties from CSVs")

    # Write out to a file in the same folder as this script
    base_dir = os.path.dirname(__file__)
    output_path = os.path.join(base_dir, output_filename)
    model.write(output_path)
    print(f"Caltrans IFC update complete. Output saved to: {output_path}")


def update_project(model, project_name):
    project = model.by_type("IfcProject")[0]
    project.Name = project_name
    return project


def update_road(model, project, road_name):
    road = project.IsDecomposedBy[0].RelatedObjects[0]
    road.Name = road_name
    # Break the relationship between road and project
    ifcopenshell.api.aggregate.unassign_object(model, [project, road])
    return road


def create_site(model, site_name):
    return ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name=site_name)


def assign_hierarchy(model, project, site, road):
    # Project -> Site -> Road
    ifcopenshell.api.aggregate.assign_object(model, relating_object=project, products=[site])
    ifcopenshell.api.aggregate.assign_object(model, relating_object=site, products=[road])


def create_road_segment(model, road, road_segment_name="RoadSegment1"):
    road_segment = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", predefined_type="ROADSEGMENT", name=road_segment_name)
    ifcopenshell.api.aggregate.assign_object(model, relating_object=road, products=[road_segment])
    return road_segment


def create_roadside_part(model, road_segment, roadside_part_name="RoadsidePart1"):
    roadside_part = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", predefined_type="ROADSIDEPART", name=roadside_part_name)
    ifcopenshell.api.aggregate.assign_object(model, relating_object=road_segment, products=[roadside_part])
    return roadside_part


def move_built_elements_to_roadside(model, road, roadside_part):
    road_contained_elements = road.ContainsElements[0].RelatedElements
    base_dir = os.path.dirname(__file__)
    guardrail_csv = os.path.join(base_dir, "guardrail.csv")
    for obj in list(road_contained_elements):
        if obj.is_a("IfcBuiltElement"):
            name = obj.Name
            local_placement = obj.ObjectPlacement
            representation = obj.Representation
            tag = obj.Tag
            # Remove the original built element
            model.remove(obj)
            # Create a new IfcRailing
            railing = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRailing", name=name)
            railing.ObjectPlacement = local_placement
            railing.Representation = representation
            railing.Tag = tag
            railing.PredefinedType = "GUARDRAIL"
            ifcopenshell.api.spatial.assign_container(model, relating_structure=roadside_part, products=[railing])
            # Add psets/properties from guardrail.csv
            add_psets_from_csv(model, railing, guardrail_csv)


# --- Property/pset helpers for Caltrans ---
def add_properties_project(model, project):
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, "project.csv")
    add_psets_from_csv(model, project, csv_path)
    # Add site properties as well
    site = project.IsDecomposedBy[0].RelatedObjects[0]
    add_properties_site(model, site)


def add_properties_site(model, site):
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, "site.csv")
    add_psets_from_csv(model, site, csv_path)


def add_psets_from_csv(model, entity, csv_path):
    pset_dict = {}
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        return
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


if __name__ == "__main__":
    # Example usage
    ifc_path = os.path.join(os.path.dirname(__file__), "0117000220_N_CT_DX_M3_D-RD_000001.ifc")
    if not os.path.exists(ifc_path):
        print(f"File does not exist: {ifc_path}")
    else:
        update_caltrans_ifc(ifc_path)
