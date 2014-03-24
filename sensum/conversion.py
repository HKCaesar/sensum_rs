'''
.. module:: conversion
   :platform: Unix, Windows
   :synopsis: This module includes functions related to conversions between different data types and reference systems.

.. moduleauthor:: Mostapha Harb <mostapha.harb@eucentre.it>
.. moduleauthor:: Daniele De Vecchi <daniele.devecchi03@universitadipavia.it>
'''
'''
---------------------------------------------------------------------------------
                                conversion.py
---------------------------------------------------------------------------------
Created on May 13, 2013
Last modified on Mar 18, 2014
---------------------------------------------------------------------------------
Project: Framework to integrate Space-based and in-situ sENSing for dynamic 
         vUlnerability and recovery Monitoring (SENSUM)

Co-funded by the European Commission under FP7 (Seventh Framework Programme)
THEME [SPA.2012.1.1-04] Support to emergency response management
Grant agreement no: 312972

---------------------------------------------------------------------------------
License: This program is free software; you can redistribute it and/or modify
         it under the terms of the GNU General Public License as published by
         the Free Software Foundation; either version 2 of the License, or
         (at your option) any later version.
---------------------------------------------------------------------------------
'''

import os
import sys
import osgeo.osr
import osgeo.ogr
import osgeo.gdal
from gdalconst import *
import numpy as np

if os.name == 'posix':
    separator = '/'
else:
    separator = '\\'


def data_type2gdal_data_type(data_type):
    
    '''Conversion from numpy data type to GDAL data type
    
    :param data_type: numpy type (e.g. np.uint8, np.int32; 0 for default: np.uint16) (numpy type).
    :returns: corresponding GDAL data type
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    ''' 
    
    if data_type == np.uint16:
        return GDT_UInt16
    if data_type == np.uint8:
        return GDT_Byte
    if data_type == np.int32:
        return GDT_Int32
    if data_type == np.float32:
        return GDT_Float32
    if data_type == np.float64:
        return GDT_Float64
    

def read_image(input_raster,data_type,band_selection):
    
    '''Read raster using GDAL
    
    :param input_raster: path and name of the input raster file (*.TIF,*.tiff) (string).
    :param data_type: numpy type used to read the image (e.g. np.uint8, np.int32; 0 for default: np.uint16) (numpy type).
    :param band_selection: number associated with the band to extract (0: all bands, 1: blue, 2: greeen, 3:red, 4:infrared) (integer).
    :returns:  a list containing the desired bands as ndarrays (list of arrays).
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    ''' 
    
    #TODO: Why not restrict this function to return band_list only? Would make it more clear and not redundant with Read_Image_Parameters.
    #TODO: You use as default import type uint16 but for export of images you use gdt_float32. 
    #TODO: Is this the general function to make rasters available to functions? How do you deal with GDAL to OpenCV matrices?
    band_list = []
    
    if data_type == 0: #most of the images (MR and HR) can be read as unsigned int 16
        data_type = np.uint16
        
    inputimg = osgeo.gdal.Open(input_raster, GA_ReadOnly)
    cols=inputimg.RasterXSize
    rows=inputimg.RasterYSize
    nbands=inputimg.RasterCount
    
    if band_selection == 0:
        #read all the bands
        for i in range(1,nbands+1):
            inband = inputimg.GetRasterBand(i) 
            mat_data = inband.ReadAsArray(0,0,cols,rows).astype(data_type)
            band_list.append(mat_data) 
    else:
        #read the single band
        inband = inputimg.GetRasterBand(band_selection) 
        mat_data = inband.ReadAsArray(0,0,cols,rows).astype(data_type)
        band_list.append(mat_data)
    
    inputimg = None    
    return band_list


def read_image_parameters(input_raster):
    
    '''Read raster parameters using GDAL
    
    :param input_raster: path and name of the input raster file (*.TIF,*.tiff) (string).
    :returns:  a list containing rows, columns, number of bands, geo-transformation matrix and projection.
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    ''' 
   
    inputimg = osgeo.gdal.Open(input_raster, GA_ReadOnly)
    cols=inputimg.RasterXSize
    rows=inputimg.RasterYSize
    nbands=inputimg.RasterCount
    geo_transform = inputimg.GetGeoTransform()
    projection = inputimg.GetProjection()
    
    inputimg = None
    return rows,cols,nbands,geo_transform,projection


def write_image(band_list,data_type,band_selection,output_raster,rows,cols,geo_transform,projection):
   
    '''Write array to file as raster using GDAL
    
    :param band_list: list of arrays containing the different bands to write (list of arrays).
    :param data_type: numpy data type of the output image (e.g. np.uint8, np.int32; 0 for default: np.uint16) (numpy type)
    :param band_selection: number associated with the band to write (0: all, 1: blue, 2: green, 3: red, 4: infrared) (integer)
    :param output_raster: path and name of the output raster to create (*.TIF, *.tiff) (string)
    :param rows: rows of the output raster (integer)
    :param cols: columns of the output raster (integer)
    :param geo_transform: geo-transformation matrix containing coordinates and resolution of the output (array of 6 elements, float)
    :param projection: projection of the output image (string)
    :returns: An output file is created
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    '''

    if data_type == 0:
        gdal_data_type = GDT_UInt16 #default data type
    else:
        gdal_data_type = data_type2gdal_data_type(data_type)
    driver = osgeo.gdal.GetDriverByName('GTiff')

    if band_selection == 0:
        nbands = len(band_list)
    else:
        nbands = 1
    outDs = driver.Create(output_raster, cols, rows,nbands, gdal_data_type)
    if outDs is None:
        print 'Could not create output file'
        sys.exit(1)
        
    if band_selection == 0:
        #write all the bands to file
        for i in range(0,nbands): 
            outBand = outDs.GetRasterBand(i+1)
            outBand.WriteArray(band_list[i], 0, 0)
    else:
        #write the specified band to file
        outBand = outDs.GetRasterBand(1)   
        outBand.WriteArray(band_list[band_selection-1], 0, 0)
    #assign geomatrix and projection
    outDs.SetGeoTransform(geo_transform)
    outDs.SetProjection(projection)
    outDs = None


def shp2rast(input_shape,output_raster,rows,cols,field_name,px_W,px_H,x_min,x_max,y_min,y_max):
    
    '''Conversion from shapefile to raster using GDAL
    
    :param input_shape: path and name of the input shapefile (*.shp) (string)
    :param output_raster: path and name of the output raster to create (*.TIF, *.tiff) (string)
    :param rows: rows of the output raster (integer)
    :param cols: columns of the output raster (integer)
    :param field_name: name of the attribute field of the shapefile used to differentiate pixels (string)
    :param 
    :returns: An output file is created
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    '''
  
    #TODO: Explain additional arguments px_W,px_H,x_min,x_max,y_min,y_max
    
    driver_shape=osgeo.ogr.GetDriverByName('ESRI Shapefile')
    data_source = driver_shape.Open(input_shape)
    source_layer = data_source.GetLayer()
    source_srs = source_layer.GetSpatialRef()
    if x_min==0 or x_max==0 or y_min==0 or y_max==0:
        x_min, x_max, y_min, y_max = source_layer.GetExtent()
    
    if rows!=0 and cols!=0 and px_W!=0 and px_H!=0 and x_min!=0 and y_max!=0:
        pixel_size_x = px_W
        pixel_size_y = abs(px_H)
        
    else:
        if rows != 0 and cols != 0:
            pixel_size_x = float((x_max-x_min)) / float(cols)
            pixel_size_y = float((y_max-y_min)) / float(rows)
        else:
            pixel_size_x = px_W
            pixel_size_y = abs(px_H)
            cols = int(float((x_max-x_min)) / float(pixel_size_x))
            rows = int(float((y_max-y_min)) / float(pixel_size_y))
    if rows!=0 and cols!=0:    
        target_ds = osgeo.gdal.GetDriverByName('GTiff').Create(output_raster, cols,rows, 1, GDT_Float32)
        target_ds.SetGeoTransform((x_min, pixel_size_x, 0,y_max, 0, -pixel_size_y))
        if source_srs:
            # Make the target raster have the same projection as the source
            target_ds.SetProjection(source_srs.ExportToWkt())
        else:
            # Source has no projection (needs GDAL >= 1.7.0 to work)
            target_ds.SetProjection('LOCAL_CS["arbitrary"]')
        
        # Rasterize
        err = osgeo.gdal.RasterizeLayer(target_ds,[1], source_layer,burn_values=[0],options=["ATTRIBUTE="+field_name])
        if err != 0:
            raise Exception("error rasterizing layer: %s" % err)
        
    return x_min,x_max,y_min,y_max


def polygon2array(input_layer,output_band,geo_transform): 
    
    '''Conversion from polygon to array
    
    :param input_shape: path and name of the input shapefile (*.shp) (string)
    :param output_raster: path and name of the output raster to create (*.TIF, *.tiff) (string)
    :param rows: rows of the output raster (integer)
    :param cols: columns of the output raster (integer)
    :param field_name: name of the attribute field of the shapefile used to differentiate pixels (string)
    :param 
    :returns: An output file is created
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 24/03/2014
    
    Reference: http://pcjericks.github.io/py-gdalogr-cookbook/vector_layers.html
    '''
    
    x_list = []
    y_list = []
    x_min, x_max, y_min, y_max = input_layer.GetExtent()
    '''
    ring = input_polygon.GetGeometryRef(0)
    n_vertex = ring.GetPointCount()
    
    for i in range(0,n_vertex-1):
        lon,lat,z = ring.GetPoint(i)
        x_matrix,y_matrix = world2pixel(geo_transform,lon,lat)
        x_list.append(x_matrix)
        y_list.append(y_matrix)
    
    x_list.sort()
    x_min = x_list[0]
    y_list.sort()
    y_min = y_list[0]
    x_list.sort(None, None, True)
    x_max = x_list[0]
    y_list.sort(None, None, True)
    y_max = y_list[0]
    
    lon_min = float(x_min*geo_transform[1]+geo_transform[0]) 
    lat_min = float(geo_transform[3]+y_min*geo_transform[5])
    # Create the destination data source
    '''
    x_res = int((x_max - x_min) / geo_transform[1])
    y_res = int((y_max - y_min) / abs(geo_transform[5]))
    target_ds = osgeo.gdal.GetDriverByName('MEM').Create('', x_res, y_res, GDT_Byte)
    target_ds.SetGeoTransform((x_min, geo_transform[1], 0, y_max, 0, geo_transform[5]))
    band = target_ds.GetRasterBand(1)
    
    # Rasterize
    osgeo.gdal.RasterizeLayer(target_ds, [1], input_layer, burn_values=[1])
    
    # Read as array
    array = band.ReadAsArray()
    
    return array


def rast2shp(input_raster,output_shape):
    
    '''Conversion from raster to shapefile using GDAL
    
    :param input_raster: path and name of the input raster (*.TIF, *.tiff) (string)
    :param output_shape: path and name of the output shapefile to create (*.shp) (string)
    :returns: An output shapefile is created 
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    '''

    src_image = osgeo.gdal.Open(input_raster)
    src_band = src_image.GetRasterBand(1)
    projection = src_image.GetProjection()
    #mask = np.equal(src_band,1)
    
    driver_shape=osgeo.ogr.GetDriverByName('ESRI Shapefile')
    outfile=driver_shape.CreateDataSource(output_shape)
    outlayer=outfile.CreateLayer('Conversion',geom_type=osgeo.ogr.wkbPolygon)
    dn = osgeo.ogr.FieldDefn('DN',osgeo.ogr.OFTInteger)
    outlayer.CreateField(dn)
    
    #Polygonize
    osgeo.gdal.Polygonize(src_band,src_band.GetMaskBand(),outlayer,0)
    
    outprj=osgeo.osr.SpatialReference(projection)
    outprj.MorphToESRI()
    file_prj = open(output_shape[:-4]+'.prj', 'w')
    file_prj.write(outprj.ExportToWkt())
    file_prj.close()
    src_image = None
    outfile = None
  

def world2pixel(geo_transform, long, lat):
    
    '''Conversion from geographic coordinates to matrix-related indexes
    
    :param geo_transform: geo-transformation matrix containing coordinates and resolution of the output (array of 6 elements, float)
    :param long: longitude of the desired point (float)
    :param lat: latitude of the desired point (float)
    :returns: A list with matrix-related x and y indexes (x,y)
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    '''
    
    ulX = geo_transform[0] #starting longitude
    ulY = geo_transform[3] #starting latitude
    xDist = geo_transform[1] #x resolution
    yDist = geo_transform[5] #y resolution

    pixel_x = int((long - ulX) / xDist)
    pixel_y = int((ulY - lat) / xDist)
    return (pixel_x, pixel_y)


def pixel2world(geo_transform, cols, rows):
    
    '''Calculation of the geo-spatial coordinates of top-left and down-right pixel
    
    :param geo_transform: geo-transformation matrix containing coordinates and resolution of the output (array of 6 elements, float)
    :param rows: number of rows (integer)
    :param cols: number of columns (integer)
    :returns: A list with top-left and down-right coordinates
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    '''
    
    minx = geo_transform[0]
    miny = geo_transform[3] + cols*geo_transform[4] + rows*geo_transform[5] 
    maxx = geo_transform[0] + cols*geo_transform[1] + rows*geo_transform[2]
    maxy = geo_transform[3]     
    return (maxx,miny)


def utm2wgs84(easting, northing, zone):
    
    '''Conversion from UTM projection to WGS84
    
    :param easting: east coordinate (float)
    :param northing: north coordinate (float)
    :param zone: number of the utm zone (integer)
    :returns: A list with coordinates in the WGS84 system (longitude,latitude,altitude)
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    '''
    '''
    ###################################################################################################################
    Reference:
     http://monkut.webfactional.com/blog/archive/2012/5/2/understanding-raster-basic-gis-concepts-and-the-python-gdal-library/
    ###################################################################################################################
    '''
    #TODO: Do we really need this function?
    
    utm_coordinate_system = osgeo.osr.SpatialReference()
    utm_coordinate_system.SetWellKnownGeogCS("WGS84") # Set geographic coordinate system to handle lat/lon
    is_northern = northing > 0    
    utm_coordinate_system.SetUTM(zone, is_northern)
    
    wgs84_coordinate_system = utm_coordinate_system.CloneGeogCS() # Clone ONLY the geographic coordinate system 
    
    # create transform component
    utm_to_wgs84_geo_transform = osgeo.osr.CoordinateTransformation(utm_coordinate_system, wgs84_coordinate_system) # (, )
    return utm_to_wgs84_geo_transform.TransformPoint(easting, northing, 0) # returns lon, lat, altitude


def reproject_shapefile(input_shape,output_shape,output_projection):
    
    '''Reproject a shapefile using the provided EPSG code
    
    :param input_shape: path and name of the input shapefile (*.shp) (string)
    :param output_shape: path and name of the output shapefile (*.shp) (string)
    :param output_projection: epsg code (integer)
    :param geometry_type: geometry type of the output ('line','polygon','point') (string)
    :returns:  an output shapefile is created
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 24/03/2014
    ''' 

    #TODO: It seems that you transform from a default epsg 4326 and don't allow to define the input or simply read it from the input file
    #TODO: would use only one argument to define input. 
    #driver definition for shapefile
    driver=osgeo.ogr.GetDriverByName('ESRI Shapefile')
    
    #select input file and create an output file
    infile=driver.Open(input_shape,0)
    inlayer=infile.GetLayer()
    inprj = inlayer.GetSpatialRef()
    if inprj == None:
        inprj = 4326
    
    outprj=osgeo.osr.SpatialReference()
    outprj.ImportFromEPSG(output_projection)
    
    newcoord=osgeo.osr.CoordinateTransformation(inprj,outprj)
    
    feature=inlayer.GetNextFeature()
    gm = feature.GetGeometryRef()
    geometry_type = gm.GetGeometryName() 

    if geometry_type == 'LINE':
        type = osgeo.ogr.wkbLineString
    if geometry_type == 'POLYGON':
        type = osgeo.ogr.wkbPolygon
    if geometry_type == 'POINT':
        type = osgeo.ogr.wkbPoint 
    outfile=driver.CreateDataSource(output_shape)
    outlayer=outfile.CreateLayer('rpj',geom_type=type)
    
    layer_defn = inlayer.GetLayerDefn() #get definitions of the layer
    field_names = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())] #store the field names as a list of strings
    #print field_names
    for i in range(0,len(field_names)):
        field = feature.GetFieldDefnRef(field_names[i])
        outlayer.CreateField(field)
        
    # get the FeatureDefn for the output shapefile
    feature_def = outlayer.GetLayerDefn()
    inlayer.ResetReading()
    # loop through the input features
    infeature = inlayer.GetNextFeature()
    while infeature:
        # get the input geometry
        geom = infeature.GetGeometryRef()
        # reproject the geometry
        geom.Transform(newcoord)
        # create a new feature
        outfeature = osgeo.ogr.Feature(feature_def)
        # set the geometry and attribute
        outfeature.SetGeometry(geom)
        #field_names = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]
        for i in range(0,len(field_names)):
            #print infeature.GetField(field_names[i])
            outfeature.SetField(field_names[i],infeature.GetField(field_names[i]))
            # add the feature to the shapefile
        outlayer.CreateFeature(outfeature)

        # destroy the features and get the next input feature
        outfeature.Destroy
        infeature.Destroy
        infeature = inlayer.GetNextFeature()

    # close the shapefiles
    infile.Destroy()
    outfile.Destroy()

    # create the *.prj file
    outprj.MorphToESRI()
    prjfile = open(output_shape[:-4]+'.prj', 'w')
    prjfile.write(outprj.ExportToWkt())
    prjfile.close()