from mcp.server.fastmcp import FastMCP

import ifc_util
from ifc_util import *

mcp=FastMCP("ifcMCP")

@mcp.tool()
def greet(name:str) -> str:
    return f"Hello, {name}"

@mcp.tool()
def get_entities(file_path:str, entity_type:str):
    """
    Get IFC entities with a specific type in an ifc file, only globalId and name of each entity are returned
    
    Parameters:
        file_path: path to the ifc file
        entity_type: type of IFC entity (e.g., "IfcDoor")
    """
    #print('method called')
    ifc_model=open_ifc(file_path)
    if ifc_model is None: return "error, the file is not found or broken"
    #print('ifc file opened')
    entities=ifc_model.by_type(entity_type)
    #print('entities retrieved')
    
    results=[]
    
    for i,entity in enumerate(entities):
        
        globalId=get_prop(entity,'GlobalId')
        name=get_prop(entity,'Name')
        results.append({
            'globalId':globalId,
            'name':name,
            'type':entity_type
        })
     
    return results

@mcp.tool()
def get_named_property_of_entities(file_path:str, globalIds:list[str], prop_name:str):
    """
    Get property with a certain name of all entities
    
    Parameters:
        file_path: path to the ifc file
        globalIds: globalIds of all the entities
        prop_name: name of the property
    """
    #print('method called')
    ifc_model=open_ifc(file_path)
    if ifc_model is None: return "error, the file is not found or broken"
        
    results=[]
    
    for globalId in globalIds:
        entity=ifc_model.by_guid(globalId)
        if entity is None: continue
        
        prop=get_prop(entity,prop_name)
        results.append({
            'globalId':globalId,
            prop_name:prop
        })
     
    return results

@mcp.tool()
def get_entity_properties(file_path:str, globalId:str):
    """
    Get all properties of an entity with a certain GlobalId in an ifc file
    
    Parameters:
        file_path: path to the ifc file
        globalId: GlobalId of IFC entity
    """
    ifc_model=open_ifc(file_path)
    if ifc_model is None: return "error, the file is not found or broken"
    
    entity=ifc_model.by_guid(globalId)
    if entity is None: return "error, the entity is not found"
    
    prop_data={
        'globalId':get_prop(entity,'GlobalId'),
        'name':get_prop(entity,'Name'),
        'description':get_prop(entity,'Description'),
        'type':entity.is_a(),
        'property_sets':{}
    }
    
    psets=get_psets(entity)
    for ps_name,pset_props in psets.items():
        prop_data['property_sets'][ps_name]=pset_props
    
    return prop_data

@mcp.tool()
def get_entity_location(file_path:str, globalId:str):
    """
    Get location of an entity with a certain GlobalId in an ifc file
    
    Parameters:
        file_path: path to the ifc file
        globalId: GlobalId of IFC entity
    """
    ifc_model=open_ifc(file_path)
    if ifc_model is None: return "error, the file is not found or broken"
    
    entity=ifc_model.by_guid(globalId)
    if entity is None: return "error, the entity is not found"
    
    loc=get_location(entity)
    return loc

@mcp.tool()
def get_entities_in_spatial(file_path:str, globalId:str):
    """
    Get globalIds of entities in a spatial structure (IfcSpace, IfcBuildingStorey, IfcBuilding, IfcSite) with globalId in an ifc file
    
    Parameters:
        file_path: path to the ifc file
        globalId: GlobalId of the spatial structure
    """
    ifc_model=open_ifc(file_path)
    if ifc_model is None: return "error, the file is not found or broken"
    
    spatial=ifc_model.by_guid(globalId)
    if spatial is None: return "error, the spatial structure is not found"
    
    globalIds=[]
    for ele in get_elements_in_spatial(spatial):
        globalIds.append(ele.GlobalId)
    
    return globalIds


@mcp.tool()
def get_openings_on_wall(file_path:str, globalId:str):
    """
    Get globalId, type, name of openings (IfcWindow, IfcDoor) on a certain wall in an ifc file
    
    Parameters:
        file_path: path to the ifc file
        globalId: GlobalId of the wall
    """
    ifc_model=open_ifc(file_path)
    if ifc_model is None: return "error, the file is not found or broken"
    
    wall=ifc_model.by_guid(globalId)
    if wall is None: return "error, the wall is not found"
    
    results=[]
    if wall.HasOpenings and len(wall.HasOpenings)>0:
        for relOpening in wall.HasOpenings:
            opening=relOpening.RelatedOpeningElement
            if not (opening and opening.HasFillings and len(opening.HasFillings)>0): continue
            for relFilling in opening.HasFillings:
                ele=relFilling.RelatedBuildingElement
                if ele:
                    results.append({
                        'globalId':ele.GlobalId,
                        'type':ele.is_a(),
                        'name':ele.Name
                    })
    return results

@mcp.tool()
def get_space_boundaries(file_path:str, globalId:str):
    """
    Get globalId, type, name of boundaries (IfcWindow, IfcDoor, IfcWall, etc.) of a certain space in an ifc file
    
    Parameters:
        file_path: path to the ifc file
        globalId: GlobalId of the space
    """
    ifc_model=open_ifc(file_path)
    if ifc_model is None: return "error, the file is not found or broken"
    
    space=ifc_model.by_guid(globalId)
    if space is None: return "error, the space is not found"
    
    results=[]
    if space.BoundedBy and len(space.BoundedBy)>0:
        for boundedBy in space.BoundedBy:
            ele=boundedBy.RelatedBuildingElement
            if ele:
                results.append({
                    'globalId':ele.GlobalId,
                    'type':ele.is_a(),
                    'name':ele.Name
                })
    return results


@mcp.tool()
def create_ifc_model(
    output_file_path:str,
    schema:str="IFC4X3",
    author:str="AI",
    organization:str="Michael Baker International",
    originating_system:str="ifcMCP"
):
    """
    Create a new IFC model file with initialized header metadata.

    Parameters:
        output_file_path: path to the IFC file to create
        schema: IFC schema to use (e.g., "IFC4X3")
        author: author written into the IFC header
        organization: organization written into the IFC header
        originating_system: originating system written into the IFC header
    """
    try:
        return ifc_util.create_ifc_model(
            output_file_path,
            schema=schema,
            author=author,
            organization=organization,
            originating_system=originating_system
        )
    except Exception as exc:
        return f"error, failed to create IFC model: {exc}"

@mcp.tool()
def create_ifc_project(
    file_path:str,
    name:str="Sample Project"
):
    """
    Create an IfcProject entity in an IFC model.

    Parameters:
        file_path: path to the IFC file to update
        name: project name
    """
    try:
        return ifc_util.create_ifc_project(file_path, name=name)
    except Exception as exc:
        return f"error, failed to create IfcProject: {exc}"

@mcp.tool()
def set_ifc_units(
    file_path:str,
    length_unit_name:str="inch",
    area_unit_name:str="square inch"
):
    """
    Set the length and area units of an IFC model.

    Parameters:
        file_path: path to the IFC file to update
        length_unit_name: length unit name (e.g., "inch")
        area_unit_name: area unit name (e.g., "square inch")
    """
    try:
        return ifc_util.set_ifc_units(
            file_path,
            length_unit_name=length_unit_name,
            area_unit_name=area_unit_name
        )
    except Exception as exc:
        return f"error, failed to set IFC units: {exc}"

@mcp.tool()
def create_model_context(
    file_path:str,
    context_type:str="Model"
):
    """
    Create a top-level geometric representation context in an IFC model.

    Parameters:
        file_path: path to the IFC file to update
        context_type: context type to create
    """
    try:
        return ifc_util.create_model_context(file_path, context_type=context_type)
    except Exception as exc:
        return f"error, failed to create model context: {exc}"

@mcp.tool()
def create_body_context(
    file_path:str,
    parent_context_type:str="Model",
    context_identifier:str="Body",
    target_view:str="MODEL_VIEW"
):
    """
    Create a body subcontext under an existing geometric representation context.

    Parameters:
        file_path: path to the IFC file to update
        parent_context_type: parent context type to attach to
        context_identifier: subcontext identifier
        target_view: target view for the subcontext
    """
    try:
        return ifc_util.create_body_context(
            file_path,
            parent_context_type=parent_context_type,
            context_identifier=context_identifier,
            target_view=target_view
        )
    except Exception as exc:
        return f"error, failed to create body context: {exc}"

@mcp.tool()
def create_ifc_site(
    file_path:str,
    name:str="Project Site"
):
    """
    Create an IfcSite entity in an IFC model.

    Parameters:
        file_path: path to the IFC file to update
        name: site name
    """
    try:
        return ifc_util.create_ifc_site(file_path, name=name)
    except Exception as exc:
        return f"error, failed to create IfcSite: {exc}"

@mcp.tool()
def create_ifc_bridge(
    file_path:str,
    name:str="Sample Bridge"
):
    """
    Create an IfcBridge entity in an IFC model.

    Parameters:
        file_path: path to the IFC file to update
        name: bridge name
    """
    try:
        return ifc_util.create_ifc_bridge(file_path, name=name)
    except Exception as exc:
        return f"error, failed to create IfcBridge: {exc}"

@mcp.tool()
def create_ifc_bridge_part(
    file_path:str,
    predefined_type:str,
    name:str,
    usage_type:str="NOTDEFINED"
):
    """
    Create an IfcBridgePart entity in an IFC model.

    Parameters:
        file_path: path to the IFC file to update
        predefined_type: IfcBridgePart predefined type (e.g., "SUBSTRUCTURE", "PIER")
        name: bridge part name
        usage_type: bridge part usage type
    """
    try:
        return ifc_util.create_ifc_bridge_part(
            file_path,
            predefined_type=predefined_type,
            name=name,
            usage_type=usage_type
        )
    except Exception as exc:
        return f"error, failed to create IfcBridgePart: {exc}"

@mcp.tool()
def assign_ifc_aggregation(
    file_path:str,
    parent_globalId:str,
    child_globalIds:list[str]
):
    """
    Assign one or more IFC entities as aggregated children of a parent entity.

    Parameters:
        file_path: path to the IFC file to update
        parent_globalId: GlobalId of the parent IFC entity
        child_globalIds: GlobalIds of the child IFC entities
    """
    try:
        return ifc_util.assign_ifc_aggregation(
            file_path,
            parent_globalId=parent_globalId,
            child_globalIds=child_globalIds
        )
    except Exception as exc:
        return f"error, failed to assign IFC aggregation: {exc}"


if __name__ == '__main__':
    mcp.run(transport="stdio")  # Default, so transport argument is optional
    #mcp.run(transport="streamable-http") # default port 8000, access streamable-http mcp server via http://127.0.01:8000/mcp
    #mcp.run(transport="sse")