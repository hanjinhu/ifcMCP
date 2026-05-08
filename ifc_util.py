# author: Jia-Rui Lin@Tsinghua
# date: Jan 08, 2014
# site: https://linjiarui.net

from pathlib import Path

import numpy as np
import ifcopenshell as ios
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.root
import ifcopenshell.api.unit
import ifcopenshell.geom as igm

#==========Util Functions for Geometric Properties============
# @Shilpa what's shown in your screenshot is not the coordinates of a vertex. It is the coordinates of the object placement. This can be done with one line of code using ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement). This will give you a matrix which includes that location in absolute coordinates.
# Note that these are global engineering coordinates. If your file contains georeferencing map conversions, you may want to then further apply the map conversion to get map grid coordinates. You can use ifcopenshell.util.geolocation.local2global or ifcopenshell.util.geolocation.xyz2enh for this.
# Then, should you wish to find the absolute coordinate of a local coordinate of a particular vertex within the shape, you may multiply the coordinate by the matrix.
def get_location(ifc_obj):
    if hasattr(ifc_obj,'ObjectPlacement'):
        from ifcopenshell.util.placement import get_local_placement
        local_matrix=get_local_placement(ifc_obj.ObjectPlacement)
        return local_matrix[0:3,3]
    return None

def distance(pos1,pos2):
    return np.linalg.norm(pos2-pos1)

def max_distance(positions):
    count=len(positions)
    max_dist=float('-inf')
    for i in range(count):
        p1=positions[i]
        for j in range(i+1,count):
            p2=positions[j]
            dist=distance(p1,p2)
            if dist>max_dist:max_dist=dist
    return max_dist

def min_distance(positions):
    count=len(positions)
    min_dist=float('inf')
    for i in range(count):
        p1=positions[i]
        for j in range(i+1,count):
            p2=positions[j]
            dist=distance(p1,p2)
            if dist<min_dist:min_dist=dist
    return min_dist
#===============================

def get_attr(ifc_obj,name):
    if name.lower()=='position' or name.lower()=='objectplacement':#hack object position
        return get_location(ifc_obj)
    if name.lower()=='type' and ifc_obj is not None:#hack object type
        return ifc_obj.is_a()
    
    if hasattr(ifc_obj,name):
        return getattr(ifc_obj,name)
    return None

# one can retrieve a data attribute via obj.AttrA.AttrC
def get_chained_attr(ifc_obj,name):
    import itertools
    from collections.abc import Iterable
    
    attrs=name.split('.')
    attrs.reverse()
    
        
    results=[]
    results.append(ifc_obj)
    while len(attrs)>0:
        attr=attrs.pop()
        if len(attr.strip())==0:break
        
        temp=[]
        temp=[get_attr(obj,attr) for obj in results]
        
        temp=[item for item in temp if item is not None]
        
        results=list(itertools.chain.from_iterable(temp)) if isinstance(temp[0],Iterable) and not isinstance(temp[0],str) else temp
        if len(results)==0: return None #this means no attribute is found or no value is returned
    
    #print(results)
    return results[0] if len(results)==1 else results

def get_single_prop(ifc_obj,name):
    prop_sets=[]
    for rel in ifc_obj.IsDefinedBy:
        if rel.is_a('IfcRelDefinesByProperties'):
            prop_def=rel.RelatingPropertyDefinition
            prop_sets.append(prop_def)
        elif rel.is_a('IfcRelDefinesByType'):
            obj_type=rel.RelatingType
            psets=obj_type.HasPropertySets
            if psets is not None: prop_sets.extend(psets)
        else:
            continue
    
    for prop_def in prop_sets:
        if prop_def.is_a('IfcElementQuantity'):
            for quantity in prop_def.Quantities:
                if quantity.is_a('IfcQuantityLength'):
                    if quantity.Name==name: return quantity.LengthValue
                elif quantity.is_a('IfcQuantityArea'):
                    if quantity.Name==name: return quantity.AreaValue
                elif quantity.is_a('IfcQuantityVolume'):
                    if quantity.Name==name: return quantity.VolumeValue
                elif quantity.is_a('IfcQuantityCount'):
                    if quantity.Name==name: return quantity.CountValue
                elif quantity.is_a('IfcQuantityWeight'):
                    if quantity.Name==name: return quantity.WeightValue
                elif quantity.is_a('IfcQuantityTime'):
                    if quantity.Name==name: return quantity.TimeValue
                else:continue #there are more complex quantity types
        elif prop_def.is_a('IfcPropertySet'):
            for property in prop_def.HasProperties:
                if property.is_a('IfcPropertySingleValue'):
                    if property.Name==name: return property.NominalValue.wrappedValue if property.NominalValue else None
                else:continue #there are more types
        else:continue #there are more types

    return None

def get_prop(ifc_obj,name):
    val=get_chained_attr(ifc_obj,name) if '.' in name else get_attr(ifc_obj,name)
    return val if val is not None else get_single_prop(ifc_obj,name)

def get_psets(ifc_obj):
    return ios.util.element.get_psets(ifc_obj)

def get_elements_in_spatial(ifc_spatial):
    elements=[]
    if ifc_spatial.ContainsElements and len(ifc_spatial.ContainsElements)>0:
        for relContain in ifc_spatial.ContainsElements:
            if not (relContain.RelatedElements and len(relContain.RelatedElements)>0): continue
            elements.extend(relContain.RelatedElements)
    
    if ifc_spatial.IsDecomposedBy and len(ifc_spatial.IsDecomposedBy)>0:
        for relAgg in ifc_spatial.IsDecomposedBy:
            if not (relAgg.RelatedObjects and len(relAgg.RelatedObjects)>0): continue
            for relObj in relAgg.RelatedObjects:
                elems=get_elements_in_spatial(relObj)
                elements.extend(elems)
    
    return elements

def open_ifc(file_path):
    #print('ifc_util called')
    return ios.open(file_path)

def create_ifc_model(file_path, schema='IFC4X3', author='AI', organization='Michael Baker International', originating_system='ifcMCP'):
    output_path=Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model=ios.file(schema=schema)
    model.header.file_description.description=['ViewDefinition [Alignment-basedView]']
    model.header.file_name.name=output_path.name
    model.header.file_name.author=[author]
    model.header.file_name.organization=[organization]
    model.header.file_name.originating_system=originating_system
    model.write(str(output_path))

    return {
        'file_path': str(output_path),
        'schema': schema,
        'file_name': output_path.name
    }

def create_ifc_project(file_path, name='Sample Project'):
    output_path=Path(file_path)
    model=open_ifc(str(output_path))
    if model is None:
        raise ValueError('the file is not found or broken')

    project=ifcopenshell.api.root.create_entity(model, ifc_class='IfcProject', name=name)
    model.write(str(output_path))

    return {
        'file_path': str(output_path),
        'globalId': project.GlobalId,
        'name': project.Name,
        'type': project.is_a()
    }

def set_ifc_units(file_path, length_unit_name='inch', area_unit_name='square inch'):
    output_path=Path(file_path)
    model=open_ifc(str(output_path))
    if model is None:
        raise ValueError('the file is not found or broken')

    length_unit=ifcopenshell.api.unit.add_conversion_based_unit(model, name=length_unit_name)
    area_unit=ifcopenshell.api.unit.add_conversion_based_unit(model, name=area_unit_name)
    ifcopenshell.api.unit.assign_unit(model, units=[length_unit, area_unit])
    model.write(str(output_path))

    return {
        'file_path': str(output_path),
        'length_unit': length_unit_name,
        'area_unit': area_unit_name
    }

def create_model_context(file_path, context_type='Model'):
    output_path=Path(file_path)
    model=open_ifc(str(output_path))
    if model is None:
        raise ValueError('the file is not found or broken')
    if len(model.by_type('IfcProject'))==0:
        raise ValueError('IfcProject is required before creating geometric representation contexts')

    context=ifcopenshell.api.context.add_context(model, context_type=context_type)
    model.write(str(output_path))

    return {
        'file_path': str(output_path),
        'context_type': context.ContextType,
        'context_identifier': context.ContextIdentifier
    }

def create_body_context(file_path, parent_context_type='Model', context_identifier='Body', target_view='MODEL_VIEW'):
    output_path=Path(file_path)
    model=open_ifc(str(output_path))
    if model is None:
        raise ValueError('the file is not found or broken')

    parent_context=None
    for context in model.by_type('IfcGeometricRepresentationContext'):
        if context.ContextType==parent_context_type:
            parent_context=context
            break

    if parent_context is None:
        raise ValueError(f'parent context with type {parent_context_type} is not found')

    context=ifcopenshell.api.context.add_context(
        model,
        context_type=parent_context_type,
        context_identifier=context_identifier,
        target_view=target_view,
        parent=parent_context
    )
    model.write(str(output_path))

    return {
        'file_path': str(output_path),
        'context_type': context.ContextType,
        'context_identifier': context.ContextIdentifier,
        'target_view': context.TargetView
    }

def create_ifc_site(file_path, name='Project Site'):
    output_path=Path(file_path)
    model=open_ifc(str(output_path))
    if model is None:
        raise ValueError('the file is not found or broken')

    site=ifcopenshell.api.root.create_entity(model, ifc_class='IfcSite', name=name)
    model.write(str(output_path))

    return {
        'file_path': str(output_path),
        'globalId': site.GlobalId,
        'name': site.Name,
        'type': site.is_a()
    }

def create_ifc_bridge(file_path, name='Sample Bridge'):
    output_path=Path(file_path)
    model=open_ifc(str(output_path))
    if model is None:
        raise ValueError('the file is not found or broken')

    bridge=ifcopenshell.api.root.create_entity(model, ifc_class='IfcBridge', name=name)
    model.write(str(output_path))

    return {
        'file_path': str(output_path),
        'globalId': bridge.GlobalId,
        'name': bridge.Name,
        'type': bridge.is_a()
    }

def create_ifc_bridge_part(file_path, predefined_type, name, usage_type='NOTDEFINED'):
    output_path=Path(file_path)
    model=open_ifc(str(output_path))
    if model is None:
        raise ValueError('the file is not found or broken')

    bridge_part=ifcopenshell.api.root.create_entity(
        model,
        ifc_class='IfcBridgePart',
        predefined_type=predefined_type,
        name=name
    )
    bridge_part.UsageType=usage_type
    model.write(str(output_path))

    return {
        'file_path': str(output_path),
        'globalId': bridge_part.GlobalId,
        'name': bridge_part.Name,
        'type': bridge_part.is_a(),
        'predefined_type': predefined_type,
        'usage_type': usage_type
    }

def assign_ifc_aggregation(file_path, parent_globalId, child_globalIds):
    output_path=Path(file_path)
    model=open_ifc(str(output_path))
    if model is None:
        raise ValueError('the file is not found or broken')

    parent=model.by_guid(parent_globalId)
    if parent is None:
        raise ValueError(f'parent entity with GlobalId {parent_globalId} is not found')

    children=[]
    for child_globalId in child_globalIds:
        child=model.by_guid(child_globalId)
        if child is None:
            raise ValueError(f'child entity with GlobalId {child_globalId} is not found')
        children.append(child)

    ifcopenshell.api.aggregate.assign_object(model, relating_object=parent, products=children)
    model.write(str(output_path))

    return {
        'file_path': str(output_path),
        'parent_globalId': parent_globalId,
        'child_globalIds': child_globalIds
    }