'''
.. module:: preprocess
   :platform: Unix, Windows
   :synopsis: This module includes functions related to preprocessing of multi-spectral satellite images.

.. moduleauthor:: Mostapha Harb <mostapha.harb@eucentre.it>
.. moduleauthor:: Daniele De Vecchi <daniele.devecchi03@universitadipavia.it>
.. moduleauthor:: Daniel Aurelio Galeazzo <dgaleazzo@gmail.com>
   :organization: EUCENTRE Foundation / University of Pavia
'''
'''
---------------------------------------------------------------------------------
                                preprocess.py
---------------------------------------------------------------------------------
Created on May 13, 2013
Last modified on Mar 19, 2014
---------------------------------------------------------------------------------
Project: Framework to integrate Space-based and in-situ sENSing for dynamic 
         vUlnerability and recovery Monitoring (SENSUM)

Co-funded by the European Commission under FP7 (Seventh Framework Programme)
THEME [SPA.2012.1.1-04] Support to emergency response management
Grant agreement no: 312972

---------------------------------------------------------------------------------
License: This file is part of SensumTools.

    SensumTools is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SensumTools is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SensumTools.  If not, see <http://www.gnu.org/licenses/>.
---------------------------------------------------------------------------------
'''


import os
import sys
sys.path.append("C:\\OSGeo4W64\\apps\\Python27\\Lib\\site-packages")
sys.path.append("C:\\OSGeo4W64\\apps\\orfeotoolbox\\python")
os.environ["PATH"] = os.environ["PATH"] + "C:\\OSGeo4W64\\bin"
print os.environ["PATH"]
import osgeo.gdal
from gdalconst import *
import cv2
import numpy as np
import osgeo.ogr
import otbApplication
from sensum.conversion import *

if os.name == 'posix': 
    separator = '/'
else:
    separator = '\\'


def clip_rectangular(input_raster,data_type,input_shape,output_raster):
    
    '''Clip a raster with a rectangular shape based on the provided polygon
    
    :param input_raster: path and name of the input raster file (*.TIF,*.tiff) (string)
    :param data_type: numpy type used to read the image (e.g. np.uint8, np.int32; 0 for default: np.uint16) (numpy type)
    :param input_shape: path and name of the input shapefile (*.shp) (string)
    :param output_raster: path and name of the output raster file (*.TIF,*.tiff) (string)
    :returns:  an output file is created
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    ''' 

    #TODO: Why not use gdalwarp?
    #TODO: would use only one argument to define input image and one to define input shp.
        
    #os.system('gdalwarp -q -cutline ' + shapefile + ' -crop_to_cutline -of GTiff ' + path + name +' '+ path + name[:-4] + '_city.TIF')

    x_list = []
    y_list = []
    # get the shapefile driver
    driver = osgeo.ogr.GetDriverByName('ESRI Shapefile')
    # open the data source
    datasource = driver.Open(input_shape, 0)
    if datasource is None:
        print 'Could not open shapefile'
        sys.exit(1)

    layer = datasource.GetLayer() #get the shapefile layer
    
    inb = osgeo.gdal.Open(input_raster, GA_ReadOnly)
    if inb is None:
        print 'Could not open'
        sys.exit(1)
        
    geoMatrix = inb.GetGeoTransform()
    driver = inb.GetDriver()
    cols = inb.RasterXSize
    rows = inb.RasterYSize
    nbands = inb.RasterCount  
    # loop through the features in the layer
    feature = layer.GetNextFeature()
    while feature:
        # get the x,y coordinates for the point
        geom = feature.GetGeometryRef()
        ring = geom.GetGeometryRef(0)
        n_vertex = ring.GetPointCount()
        for i in range(0,n_vertex-1):
            lon,lat,z = ring.GetPoint(i)
            x_matrix,y_matrix = world2pixel(geoMatrix,lon,lat)
            x_list.append(x_matrix)
            y_list.append(y_matrix)
        # destroy the feature and get a new one
        feature.Destroy()
        feature = layer.GetNextFeature()
    #regularize the shape
    x_list.sort()
    x_min = x_list[0]
    y_list.sort()
    y_min = y_list[0]
    x_list.sort(None, None, True)
    x_max = x_list[0]
    y_list.sort(None, None, True)
    y_max = y_list[0]
    
    #compute the new starting coordinates
    lon_min = float(x_min*geoMatrix[1]+geoMatrix[0]) 
    lat_min = float(geoMatrix[3]+y_min*geoMatrix[5])

    geotransform = [lon_min,geoMatrix[1],0.0,lat_min,0.0,geoMatrix[5]]
    cols_out = x_max-x_min
    rows_out = y_max-y_min
    
    gdal_data_type = data_type2gdal_data_type(data_type)
    output=driver.Create(output_raster,cols_out,rows_out,nbands,gdal_data_type) #to check
    
    for b in range (1,nbands+1):
        inband = inb.GetRasterBand(b)
        data = inband.ReadAsArray(x_min,y_min,cols_out,rows_out).astype(data_type)
        outband=output.GetRasterBand(b)
        outband.WriteArray(data,0,0) #write to output image
    
    output.SetGeoTransform(geotransform) #set the transformation
    output.SetProjection(inb.GetProjection())
    # close the data source and text file
    datasource.Destroy()
    

def layer_stack(input_raster_list,output_raster,data_type):
    
    '''Merge single-band files into one multi-band file
    
    :param input_raster_list: list with paths and names of the input raster files (*.TIF,*.tiff) (list of strings)
    :param output_raster: path and name of the output raster file (*.TIF,*.tiff) (string)
    :param data_type: numpy type used to read the image (e.g. np.uint8, np.int32; 0 for default: np.uint16) (numpy type)
    :returns:  an output file is created
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 19/03/2014
    ''' 
    
    final_list = []
    for f in range(0,len(input_raster_list)): #read image by image
        band_list = read_image(input_raster_list[f],data_type,0)
        rows,cols,nbands,geo_transform,projection = read_image_parameters(input_raster_list[f])
        final_list.append(band_list[0]) #append every band to a unique list
        
    write_image(final_list,data_type,0,output_raster,rows,cols,geo_transform,projection) #write the list to output file
    
    
def layer_split(input_raster,band_selection,data_type):
    
    '''Split a multi-band input file into single-band files
    
    :param input_raster: path and name of the input raster file (*.TIF,*.tiff) (string)
    :param band_selection: number associated with the band to extract (0: all bands, 1: blue, 2: greeen, 3:red, 4:infrared) (integer)
    :param data_type: numpy type used to read the image (e.g. np.uint8, np.int32; 0 for default: np.uint16) (numpy type)
    :returns:  an output file is created for single-band
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 18/03/2014
    '''

    #TODO: Do we need this?
    #TODO: Would rename arguments merge(src_img, dst_dir, option)
    
    band_list = read_image(input_raster,data_type,band_selection)
    rows,cols,nbands,geo_transform,projection = read_image_parameters(input_raster)
    if band_selection == 0:
        for b in range(1,nbands+1):
            write_image(band_list,data_type,b,input_raster[:-4]+'_B'+str(b)+'.TIF',rows,cols,geo_transform,projection)
    else:
        write_image(band_list,data_type,band_selection,input_raster[:-4]+'_B'+str(band_selection)+'.TIF',rows,cols,geo_transform,projection)  
    

def gcp_extraction_old(input_band_ref,input_band,ref_geo_transform,output_option):
    
    '''GCP extraction and filtering using the SURF algorithm
    
    :param input_band_ref: 2darray byte format (numpy array) (unsigned integer 8bit)
    :param input_band: 2darray byte format (numpy array) (unsigned integer 8bit)
    :param ref_geo_transform: geomatrix related to the reference image
    :param output_option: 0 for indexes, 1 for coordinates (default 0) (integer)
    :param data_type: numpy type used to read the image (e.g. np.uint8, np.int32; 0 for default: np.uint16) (numpy type)
    :returns:  an output file is created for single-band
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 19/03/2014
    '''
    #TODO: It takes only a 2d array (so only one image band) and not the full image content?
    #TODO: 2d array is created by using Read_Image() -> band_list[i]?
    #TODO: So we have two type of functions: 1. functions that take directly a file (e.g. geotiff) and 2. functions that take an array?
    #TODO: Would rename function to something like auto_gcp()
    #TODO: Output a list of gcps following the structure required by gdal_transform -> this way we could use gdal for the actual transformation and only focus on a robuts and flexible gcp detection
    #TODO: We should think of an option to manually adjust auto gcps for example using QGIS georeferencer (comment from Dilkushi during skype call 7.3.2014)
    #C:\OSGeo4W\bin
    detector = cv2.FeatureDetector_create("SURF") 
    descriptor = cv2.DescriptorExtractor_create("BRIEF")
    matcher = cv2.DescriptorMatcher_create("BruteForce-Hamming")
    
    # detect keypoints
    kp1 = detector.detect(input_band_ref)
    kp2 = detector.detect(input_band)
    
    # descriptors
    k1, d1 = descriptor.compute(input_band_ref, kp1)
    k2, d2 = descriptor.compute(input_band, kp2)
    
    # match the keypoints
    matches = matcher.match(d1, d2)
    
    # visualize the matches
    dist = [m.distance for m in matches] #extract the distances
    a=sorted(dist) #order the distances
    fildist=np.zeros(1) #use 1 in order to select the most reliable matches
    
    for i in range(0,1):
        fildist[i]=a[i]
    thres_dist = max(fildist)
    # keep only the reasonable matches
    sel_matches = [m for m in matches if m.distance <= thres_dist] 
    
    i=0
    points=np.zeros(shape=(len(sel_matches),4))
    points_coordinates = np.zeros(shape=(len(sel_matches),4)).astype(np.float32)
    for m in sel_matches:
        #matrix containing coordinates of the matching points
        points[i][:]= [int(k1[m.queryIdx].pt[0]),int(k1[m.queryIdx].pt[1]),int(k2[m.trainIdx].pt[0]),int(k2[m.trainIdx].pt[1])]
        i=i+1
    #include new filter, slope filter not good for rotation
    #include conversion from indexes to coordinates
    #print 'Feature Extraction - Done'
    if output_option == None or output_option == 0:
        return points #return indexes
    else: #conversion to coordinates
        for j in range(0,len(points)):
            lon_ref,lat_ref = pixel2world(ref_geo_transform, points[j][0], points[j][1])
            lon_tg,lat_tg = pixel2world(ref_geo_transform, points[j][2], points[j][3]) #check how the gdal correction function works
            points_coordinates[j][:] = [lon_ref,lat_ref,lon_tg,lat_tg]
        return points_coordinates 


def linear_offset_comp(common_points):
    
    '''Linear offset computation using points extracted by gcp_extraction
    
    :param common_points: matrix with common points extracted by gcp_extraction (matrix of integers)
    :returns:  list with x and y offset
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 19/03/2014
    '''
    
    xoff1=np.zeros(len(common_points)) 
    yoff1=np.zeros(len(common_points))
    
    #Offset calculation band1
    for l in range(0,len(common_points)):
        xoff1[l]=common_points[l][2]-common_points[l][0]
        yoff1[l]=common_points[l][3]-common_points[l][1]
   
    #Final offset calculation - mean of calculated offsets
    xoff=round((xoff1.mean())) #mean computed in case of more than one common point
    yoff=round((yoff1.mean())) #mean computed in case of more than one common point
    
    return xoff,yoff
        

def pansharp(input_raster_multiband,input_raster_panchromatic,output_raster):
    
    '''Pansharpening operation using OTB library
    
    :param input_raster_multiband: path and name of the input raster multi-band file (*.TIF,*.tiff) (string)
    :param input_raster_panchromatic: path and name of the input raster panchromatic file (*.TIF,*.tiff) (string)
    :param output_raster: path and name of the output raster file (*.TIF,*.tiff) (string)
    :returns:  an output file is created
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb - Daniel Aurelio Galeazzo
    Last modified: 23/05/2014
    '''

    #TODO: Specify in description which pansharpening algorithm iss used by this function
    fix_tiling_raster(input_raster_multiband,input_raster_panchromatic)
    rowsp,colsp,nbands,geo_transform,projection = read_image_parameters(input_raster_panchromatic)
    rowsxs,colsxs,nbands,geo_transform,projection = read_image_parameters(input_raster_multiband)
 
    scale_rows = round(float(rowsp)/float(rowsxs),6)
    scale_cols = round(float(colsp)/float(colsxs),6)
    print scale_rows,scale_cols
    #Resampling
    RigidTransformResample = otbApplication.Registry.CreateApplication("RigidTransformResample") 
    # The following lines set all the application parameters: 
    RigidTransformResample.SetParameterString("in", input_raster_multiband) 
    RigidTransformResample.SetParameterString("out", input_raster_multiband[:-4]+'_resampled.tif') 
    RigidTransformResample.SetParameterString("transform.type","id") 
    RigidTransformResample.SetParameterFloat("transform.type.id.scalex", scale_cols) 
    RigidTransformResample.SetParameterFloat("transform.type.id.scaley", scale_rows) 
    #RigidTransformResample.SetParameterInt("ram", 2000)
    RigidTransformResample.ExecuteAndWriteOutput()
 
    Pansharpening = otbApplication.Registry.CreateApplication("Pansharpening") 
    # Application parameters
    Pansharpening.SetParameterString("inp", input_raster_panchromatic) 
    Pansharpening.SetParameterString("inxs", input_raster_multiband[:-4]+'_resampled.tif') 
    #Pansharpening.SetParameterInt("ram", 2000) 
    Pansharpening.SetParameterString("out", output_raster) 
    Pansharpening.SetParameterOutputImagePixelType("out", 3) 
     
    Pansharpening.ExecuteAndWriteOutput()
    
    
def resampling(input_raster,output_raster,output_resolution,resampling_algorithm):
    
    '''Resampling operation using OTB library
    
    :param input_raster: path and name of the input raster file (*.TIF,*.tiff) (string)
    :param output_raster: path and name of the output raster file (*.TIF,*.tiff) (string)
    :param output_resolution: resolution of the outout raster file (float)
    :param resampling_algorithm: choice among different algorithms (nearest_neigh,linear,bicubic)
    :returns:  an output file is created
    :raises: AttributeError, KeyError
    
    Author: Daniele De Vecchi - Mostapha Harb
    Last modified: 19/03/2014
    '''
    
    rows,cols,nbands,geo_transform,projection = read_image_parameters(input_raster)
    scale_value = round(float(geo_transform[1])/float(output_resolution),4)
    RigidTransformResample = otbApplication.Registry.CreateApplication("RigidTransformResample") 
    # The following lines set all the application parameters: 
    RigidTransformResample.SetParameterString("in", input_raster) 
    RigidTransformResample.SetParameterString("out", output_raster) 
    RigidTransformResample.SetParameterString("transform.type","id") 
    RigidTransformResample.SetParameterFloat("transform.type.id.scalex", scale_value) 
    RigidTransformResample.SetParameterFloat("transform.type.id.scaley", scale_value) 
    
    if resampling_algorithm == 'nearest_neigh': 
        RigidTransformResample.SetParameterString("interpolator","nn")
    if resampling_algorithm == 'linear':
        RigidTransformResample.SetParameterString("interpolator","linear")
    if resampling_algorithm == 'bicubic':
        RigidTransformResample.SetParameterString("interpolator","bco")
    
    RigidTransformResample.SetParameterInt("ram", 2000) 
    
    RigidTransformResample.ExecuteAndWriteOutput()
    
    
def fix_tiling_raster(input_raster1,input_raster2):
    '''Fix two images dimension for pansharpening issue instroducted by otb 4.0 version (seem to be otb 4.0 bug)

    :param input_raster1: path and name of the input raster file (*.TIF,*.tiff) (string)
    :param input_raster1: path and name of the input raster file (*.TIF,*.tiff) (string)
    
    Author: Daniel Aurelio Galeazzo - Daniele De Vecchi - Mostapha Harb
    Last modified: 23/05/2014
    '''
    minx1,miny1,maxx1,maxy1 = get_coordinate_limit(input_raster1)
    minx2,miny2,maxx2,maxy2 = get_coordinate_limit(input_raster2)

    #Get cordinate of intersation from 2 raster

    if minx1-minx2 >= 0:
        new_minx = minx1
    else:
        new_minx = minx2
    if miny1-miny2 >= 0:
        new_miny = miny1
    else:
        new_miny = miny2
    if maxx1-maxx2 <= 0:
        new_maxx = maxx1
    else:
        new_maxx = maxx2
    if maxy1-maxy2 <= 0:
        new_maxy = maxy1
    else:
        new_maxy = maxy2

    #Rewrite a raster with new cordinate
    #TODO   FIX CASE WITHOUT os.getcwd() WHEN FULL PATH IS DECLARED
    os.system("gdal_translate -of GTiff -projwin "+str(minx)+" "+str(maxy)+" "+str(maxx)+" "+str(miny)+" "+os.getcwd()+'/'+input_raster+" "+os.getcwd()+'/'+input_raster+"_tmp.tif")
    if os.name == 'posix': 
        os.system("mv "+os.getcwd()+'/'+input_raster+"_tmp.tif "+os.getcwd()+'/'+input_raster)
    else:
        os.system("rename "+os.getcwd()+'/'+input_raster+"_tmp.tif "+os.getcwd()+'/'+input_raster)


def get_coordinate_limit(input_raster):
    '''Get corner cordinate from a raster

    :param input_raster: path and name of the input raster file (*.TIF,*.tiff) (string)
    :returs: minx,miny,maxx,maxy: points taken from geomatrix (string)
    
    Author: Daniel Aurelio Galeazzo - Daniele De Vecchi - Mostapha Harb
    Last modified: 23/05/2014
    '''
    dataset = osgeo.gdal.Open(input_raster, GA_ReadOnly)
    if dataset is None:
        print 'Could not open'
        sys.exit(1)
    driver = dataset.GetDriver()
    band = dataset.GetRasterBand(1)

    width = dataset.RasterXSize
    height = dataset.RasterYSize
    geoMatrix = dataset.GetGeoTransform()
    minx = geoMatrix[0]
    miny = geoMatrix[3] + width*geoMatrix[4] + height*geoMatrix[5] 
    maxx = geoMatrix[0] + width*geoMatrix[1] + height*geoMatrix[2]
    maxy = geoMatrix[3]

    return minx,miny,maxx,maxy


def gcp_extraction(image_ref,image_target):
    
    '''GCP extraction and filtering using the SURF algorithm
    
    :param image_ref: path and name of the input reference file (*.TIF,*.tiff) (string)
    :param image_target: path and name of the input target file (*.TIF,*.tiff) (string)
    :returns:  array with best matching points is returned
    :raises: AttributeError, KeyError
    
    Author: Mostapha Harb - Daniele De Vecchi - Daniel Aurelio Galeazzo
    Last modified: 23/05/2014
    '''

    detector = cv2.FeatureDetector_create("SURF") 
    descriptor = cv2.DescriptorExtractor_create("BRIEF")
    matcher = cv2.DescriptorMatcher_create("BruteForce-Hamming")

    img_ref = read_image(image_ref,np.uint8,1)
    rows_ref,cols_ref,nbands_ref,geotransform_ref,projection_ref = read_image_parameters(image_ref)
    img_ref_m = np.ma.masked_values(img_ref[0], 0).astype('uint8')

    kp1 = detector.detect(img_ref[0], mask=img_ref_m)
    k1, d1 = descriptor.compute(img_ref[0], kp1)
    img_ref = []
    
    img_target = read_image(image_target,np.uint8,0)
    rows_target,cols_target,nbands_target,geotransform_target,projection_target = read_image_parameters(image_target)
    img_target_m = np.ma.masked_values(img_target[0], 0).astype('uint8')
    
    kp2 = detector.detect(img2, mask = img2_m)
    k2, d2 = descriptor.compute(img2, kp2)
    img_target = []

    # match the keypoints
    matches = matcher.match(d1, d2)
    
    # visualize the matches
    dist = [m.distance for m in matches] #extract the distances
  
    thres_dist = 100
    sel_matches = [m for m in matches if m.distance <= thres_dist]

    points=np.zeros(shape=(len(sel_matches),4))
    points_shift = np.zeros(shape=(len(sel_matches),2))
    points_shift_abs = np.zeros(shape=(len(sel_matches),1))

    #Output variable where where for every matching point it is written hamming distance, shift and slope
    compar_stack = np.array([100,1.5,0.0,1,1,2,2])

    #visualization(img1,img2,sel_matches)
    i = 0
    for m in sel_matches:
        points[i][:]= [int(k1[m.queryIdx].pt[0]),int(k1[m.queryIdx].pt[1]),int(k2[m.trainIdx].pt[0]),int(k2[m.trainIdx].pt[1])]
        points_shift[i][:] = [int(k2[m.trainIdx].pt[0])-int(k1[m.queryIdx].pt[0]),int(k2[m.trainIdx].pt[1])-int(k1[m.queryIdx].pt[1])]
        points_shift_abs [i][:] = [np.sqrt((int(cols + k2[m.trainIdx].pt[0])-int(k1[m.queryIdx].pt[0]))**2+
                                           (int(k2[m.trainIdx].pt[1])-int(k1[m.queryIdx].pt[1]))**2)]
        
        deltax = np.float(int(k2[m.trainIdx].pt[0])-int(k1[m.queryIdx].pt[0]))
        deltay = np.float(int(k2[m.trainIdx].pt[1])-int(k1[m.queryIdx].pt[1]))
        
        if deltax == 0 and deltay != 0:
            slope = 90
        elif deltax == 0 and deltay == 0:
            slope = 0
        else:
            slope = (np.arctan(deltay/deltax)*360)/(2*np.pi)
        
        compar_stack = np.vstack([compar_stack,[m.distance,points_shift_abs [i][:],slope,
                                                int(k1[m.queryIdx].pt[0]),
                                                int(k1[m.queryIdx].pt[1]),
                                                int(k2[m.trainIdx].pt[0]),
                                                int(k2[m.trainIdx].pt[1])]])
        i=i+1

        
        
    #Ordino lo stack
    compar_stack = compar_stack[compar_stack[:,0].argsort()]#Returns the indices that would sort an array.
    print len(compar_stack)

    best = select_best_matching(compar_stack[0:90])#The number of sorted points to be passed
    '''   
    report = os.path.join(os.path.dirname(image1),'report.txt')
    out_file = open(report,"a")
    out_file.write("\n")
    out_file.write("Il migliore ha un reliability value pari a "+str(best[0])+" \n")
    out_file.close()
    '''
    best_match = [best[3:7]]
    return best_match


def select_best_matching(compstack):

    '''Determine the best matching points among the extracted ones

    :param compstack: array with points and distances extracted by the gcp_extraction function
    :returs: index of the row with the best matching points
    
    Author: Mostapha Harb - Daniele De Vecchi - Daniel Aurelio Galeazzo
    Last modified: 23/05/2014
    '''
    
    # Sort
    compstack = compstack[compstack[:,2].argsort()]
    spl_slope = np.append(np.where(np.diff(compstack[:,2])>0.1)[0]+1,len(compstack[:,0]))
    
    step = 0
    best_variability = 5
    len_bestvariab = 0
    best_row = np.array([100,1.5,0.0,1,1,2,2])

    for i in spl_slope:
        slope = compstack[step:i][:,2]
        temp = compstack[step:i][:,1]
        variab_temp = np.var(temp)
        count_list=[]
        if variab_temp <= best_variability and len(temp) >3:
            count_list.append(len(temp))

            if variab_temp < best_variability:
                
                best_variability = variab_temp
                len_bestvariab = len(temp)                
                best_row = compstack[step:i][compstack[step:i][:,0].argsort()][0]
                all_rows = compstack[step:i]
            if variab_temp == best_variability:
                if len(temp)>len_bestvariab:
                    best_variability = variab_temp
                    len_bestvariab = len(temp)                
                    best_row = compstack[step:i][compstack[step:i][:,0].argsort()][0]
                    all_rows = compstack[step:i]
        step = i
    return best_row #,,point_list1,point_list2


def affine_correction(input_band,best_match):
    
    '''Perform the correction using warpAffine from OpenCV

    :param input_band: 2darray containing a single band of the original image (numpy array)
    :param best_match: array returned by the gcp_extraction function with the best matching points to be used for correction  
    :returs: 2darray with the corrected band
    
    Author: Mostapha Harb - Daniele De Vecchi - Daniel Aurelio Galeazzo
    Last modified: 23/05/2014
    '''
    
    rows,cols = input_band.shape  
    delta_x = best_match[0][2] - best_match[0][0]
    delta_y = best_match[0][3] - best_match[0][1]
    M = np.float32([[1,0,delta_x],[0,1,delta_y]])
    dst = cv2.warpAffine(input_band,M,(cols,rows))
    return dst


def F_B(path,floating,ref):
    
    '''Get corner cordinate from a raster

    :param input_raster: path and name of the input raster file (*.TIF,*.tiff) (string)
    :returs: minx,miny,maxx,maxy: points taken from geomatrix (string)
    
    Author: Daniel Aurelio Galeazzo - Daniele De Vecchi - Mostapha Harb
    Last modified: 23/05/2014
    '''
    
    dir1 = os.listdir(floating)
    dir2 = os.listdir(ref)
    a_list=[]
    for i in [1]:#range(1,6):#(1,6):
        floating_list = [s for s in dir1 if "_B"+str(i)+'_city' in s ]
        if len(floating_list):
            ref_list = [s for s in dir2 if "_B"+str(i)+'_city' in s ]
            rows,cols_q,nbands,geotransform,projection = read_image_parameters(floating+floating_list[0])
            rows,cols_q,nbands,geotransform,projection = read_image_parameters(ref+ref_list[0])
            band_list0 = read_image(floating+floating_list[0],np.uint8,0)
            band_list1 = read_image(ref+ref_list[0],np.uint8,0)
            im0=band_list0[0]
            im1=band_list1[0]       
            a=gcp_extraction(floating+floating_list[0],ref+ref_list[0])# the coordinates of the max point which is supposed to be the invariant point
            a_list.append(a[0][0] - a[0][2])
            a_list.append(a[0][1] - a[0][3])
            b=affine_correction(im0,a)
            out_list=[]
            out_list.append(b)
            write_image(out_list,0,i,floating+floating_list[0][:-4]+'_adj.tif',rows,cols_q,geotransform,projection)       
    return a_list