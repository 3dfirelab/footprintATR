#!/usr/bin/env python3

"""
Description :
-------------
    Récupère les paramètres suivants de la centrale par MQTT afin de réaliser
    les calculs de la marque au sol des caméras de l'ATR :
        - longitude
        - latitude
        - altitude
        - cap
        - roulis
        - tangage
    Le script se lance comme un script python standard, sans argument.
    CTRL+C doit être utilisé pour terminer le script, ou fermer le terminal.

Options :
---------
    * aucune

Utilisation :
-------------
    ./data2groundmark.py

Auteur :
--------
    Olivier Henry (SAFIRE)

Version :
---------
    * 0.1.0 : première version du script

"""


__author__ = 'Olivier Henry <olivier.henry@safire.fr>'
__version__ = '0.1.0'
__creation_date__ = '07/05/2025'
__modification_date__ = '07/05/2025'


import time
import struct
import logging
import pathlib
import tempfile
import paho.mqtt.client as mqtt

#ronan
import footprint
import os 
import warnings 
import shutil
import pyproj
from datetime import datetime
import pandas as pd 
import matplotlib.pyplot as plt 
import requests
import planete_api
import pdb 
import json 
import numpy as np 
roll, pitch, thead, altitude, longitude, latitude = None, None, None, None, None, None


def preparation_logging(log_file):
    """
    prépare le fichier de log : le format, sa localisation et le format des messages.

    :param pathlib.Path log_file:
        nom du fichier de log, au format pathlib.Path
    """

    logging.getLogger('').handlers = []
    logging.basicConfig(filename=log_file, level=logging.DEBUG, filemode='w',
                        format='%(asctime)s : %(levelname)s : %(message)s')


def mqtt_on_connect(client, userdata, flags, rc):
    """
    callback de la fonction on_connect du client MQTT.
    grosso modo : ce que doit faire le script lors de la connexion au broker MQTT.

    :param client:
    :param userdata:
    :param flags:
    :param rc:
        result code : résultat de la connexion ; 0 = success, 1 = failed.
    """

    if rc == 0:
        print('connection to mosquitto successfull !')
        logging.info('connection to mosquitto successfull !')
    else:
        print('connection to mosquitto not successfull !')
        logging.warning('impossible to connect to mosquitto ; please check that mosquitto has been started or is '
                        'running')


def mqtt_on_disconnect(client, userdata, rc):
    """
    callback de la fonction on_disconnect du client MQTT.
    grosso modo : ce que doit faire le script lors de la déconnexion du broker MQTT.

    :param client:
    :param userdata:
    :param rc:
    """

    print('disconnection from mosquitto successfull !')
    logging.info('disconnection from mosquitto successfull !')


def mqtt_on_message(client, userdata, message):
    """
    callback de la fonction on_message du client MQTT.
    grosso modo : ce que doit faire le script lors de la réception d'un message

    :param client:
    :param userdata:
    :param message:
        message reçu par mqtt, normalement, c'est du binaire.
    """

    logging.info(f'message has been received from mosquitto : {[message.topic, message.payload]}')

    global roll, pitch, thead, altitude, longitude, latitude

    data = struct.unpack('f', message.payload)[0]
    if 'alt' in message.topic:
        altitude = data
    elif 'thead' in message.topic:
        thead = data
    elif 'pitch' in message.topic:
        pitch = data
    elif 'roll' in message.topic:
        roll = data
    elif 'lat' in message.topic:
        latitude = data
    elif 'lon' in message.topic:
        longitude = data


##################
#      MAIN      #
##################
flag_plot=False
flag_toplanete=True
flag_saveAllfootprint=True # for comparaison with orthorectification later on
if flag_plot: 
    flag_saveAllfootprint = True
 
#ip_server_planete =  '84.37.21.236'
ip_server_planete =  'safire.atmosphere.aero'
mission_id = 'SILEX'
user_name = os.environ['planete_username']
password  = os.environ['planete_username_passwd']

#download dem and dummy image if not present.
url = ["https://www.dropbox.com/scl/fi/it70yyp1do53ntdjtu2y3/dem.tif?rlkey=izsx7loep9p7quw1w0n3q2fhr&st=hcd2frpw&dl=1",
       "https://www.dropbox.com/scl/fi/jhzj02teomnn1zrhd3xgz/template_atr42_visible.tif?rlkey=hd8i9gt4yzf90mowb27xib6wp&st=zespd51w&dl=1"]
# Path to save
path = ["../data_static/dem/dem.tif", "../data_static/template_atr42_visible.tif"]

# Download
for path_, url_ in zip(path,url):
    if not(os.path.isfile(path_)):
        print('download ', path_)
        response = requests.get(url_)
        with open(path_, "wb") as f:
            f.write(response.content)


# preparation du système de log
logfile = pathlib.Path(tempfile.gettempdir()).joinpath('data2groundmark.log')
preparation_logging(logfile)


# initialisation des variables
logging.info('initializing variables...')
loop_time = 10 # temps d'exécution du calcul en seconde
host = '127.0.0.1' # à changer lorsque le script tournera en environnement opérationnel
port = 1883
mqtt_name = 'data2groundmark'
topics = ['aipov/altitude/alt_imu1_m/synchro',
          'aipov/attitude/thead_imu1_deg/synchro',
          'aipov/attitude/pitch_imu1_deg/synchro',
          'aipov/attitude/roll_imu1_deg/synchro',
          'aipov/position_horizontale/lat_imu1/synchro',
          'aipov/position_horizontale/lon_imu1/synchro']
logging.info(f'variables initialized - mqtt_name: {mqtt_name} ; host: {host} ; topics: {topics}')


# connexion au broker MQTT
logging.info('tentative de connexion à mosquitto ...')
print('connecting to mosquitto...')
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=mqtt_name)
mqtt_client.on_connect = mqtt_on_connect
mqtt_client.on_disconnect = mqtt_on_disconnect
mqtt_client.on_message = mqtt_on_message
mqtt_client.connect(host, port)
mqtt_client.subscribe([(topic, 0) for topic in topics])
mqtt_client.loop_start()
start_time = time.time()

#initialization calcul footprint
crs_code = 32631

wkdir = '/tmp/paugam/footprint_wkdir/'
if os.path.isdir(wkdir): shutil.rmtree(wkdir)
os.makedirs(wkdir, exist_ok=True)

script_dir = os.path.dirname(os.path.abspath(__file__))

warnings.filterwarnings("ignore", category=UserWarning, module="pyproj")
intparamFile = "{:s}/../data_static/io/as240051_int_param.yaml".format(script_dir)
correction_xyz = [-4.54166272e-05,  1.46991992e-04,  3.92582905e-04]
correction_opk = [ -4.62240706e-01,2.50020186e+00,  1.76677744e-04]
    
crs_code=32631
crs = pyproj.CRS.from_epsg(crs_code)
# Define the coordinate systems
wgs84 = pyproj.CRS('EPSG:4326')  # WGS84 (lat/lon)
# Initialize the transformer
transformer     = pyproj.Transformer.from_crs(wgs84, crs, always_xy=True)
transformer_inv = pyproj.Transformer.from_crs(crs, wgs84, always_xy=True)

#question:
##########
#time.time() is the time of the data

# boucle de calcul
params = {}
params['correction_xyz'] = correction_xyz
params['correction_opk'] = correction_opk
params['wkdir']          = wkdir
params['crs_code']       = crs_code
params['transformer_inv']= transformer_inv
params['transformer']    = transformer
params['script_dir']     = script_dir
params['wkdir']          = wkdir
params['demFile']        =  '{:s}/../data_static/dem/dem.tif'.format(script_dir)
params['intparamFile']   =  '{:s}/../data_static/io/as240051_int_param.yaml'.format(script_dir)

gdf_footprint = None
if flag_plot:
    # Set up the plot
    plt.ion()  # Turn on interactive mode
    fig, ax = plt.subplots()

geomarker_time = []
geomarker_id = []
wrapped_feature_prev = None

while True:
    try:

        if (roll is not None and pitch is not None and thead is not None and altitude is not None
            and longitude is not None and latitude is not None):

            # insérer ici le calcul
            if altitude < 200: continue 
            current_timestamp = time.time()
            current_time = datetime.fromtimestamp(current_timestamp)
            print(current_timestamp - start_time, roll, pitch, thead, altitude, longitude, latitude)
        
            file_path = "{:s}/../data_static/template_atr42_visible.tif".format(script_dir)
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")  # ExifTool format: YYYY:MM:DD HH:MM:SS
            row_dummy_file = wkdir+'now_visible_atr42.tif'
            footprint.zero_out_image_and_update_time(file_path, current_time_str, row_dummy_file)

            gdf_ = footprint.orthro(row_dummy_file, time.time(), 
                                    latitude,longitude,altitude,roll,pitch,thead, 
                                    params)
            gdf_['geometry'] = gdf_['geometry'].simplify(tolerance=100, preserve_topology=True)
            if flag_saveAllfootprint: 
                if gdf_footprint is None:
                    gdf_footprint = gdf_
                else:
                    gdf_footprint = pd.concat([gdf_,gdf_footprint])
           
            if flag_plot:
                ax.clear()
                if len(gdf_footprint) > 1:
                    gdf_footprint.iloc[1:].plot(ax=ax, edgecolor="black", facecolor="none",zorder=1, alpha=0.5)
                gdf_footprint.iloc[[0]].plot(ax=ax, edgecolor="none", facecolor="red", zorder=0, alpha=0.2)
                gdf_footprint.iloc[[0]].plot(ax=ax, edgecolor="red", facecolor="none", zorder=0)
                
                ax.set_title(f"{current_time_str}")
                plt.draw()
                plt.pause(0.5)  # Pause to allow update (adjust time as needed)
            
            #transfert vers planete
            if flag_toplanete: 
                token = planete_api.get_token(ip_server_planete, mission_id,user_name,password)

                # Creation d'un point
                #pdb.set_trace()
                if wrapped_feature_prev is not None:
                    #change color of prev
                    wrapped_feature_prev['feature']['properties']['color']='#000000'
                    
                    #planete_api.delete_geomarker(mission_id, token, geomarker_id[-1])
                    #time_prev = geomarker_time[-1]
                    #del geomarker_id[-1]
                    #del geomarker_time[-1]
                    #geomarker_id.append( planete_api.add_geomarker(mission_id, token, wrapped_feature_prev) )
                    #geomarker_time.append(time_prev)
                    
                    planete_api.modify_geomarker(ip_server_planete, mission_id, token, wrapped_feature_prev, geomarker_id[-1])

                feature =  json.loads(gdf_.to_crs(4326).to_json())['features'][0] 
                feature['properties'] = {"group":"footprint","color":"#ff0000"}
                wrapped_feature = {"feature": feature}
                geomarker_id.append( planete_api.add_geomarker(ip_server_planete, mission_id, token, wrapped_feature) )
                geomarker_time.append(current_timestamp)
                
                id_to_remove = np.where(np.array(geomarker_time) < geomarker_time[-1]-900)[0] #keep last 15min
                for ii in id_to_remove:
                    planete_api.delete_geomarker(ip_server_planete, mission_id, token, geomarker_id[ii])

            wrapped_feature_prev = wrapped_feature
            
        else:
            logging.error(f'impossible d\'effectuer le calcul, l\'une des variables est None : '
                          f'    roll {roll} | pitch {pitch} | thead {thead} | altitude {altitude} | longitude '
                          f'{longitude} | latitude {latitude} | ')

        # mise en pause du script pour respecter une boucle de XX secondes
        sleep = loop_time - ((time.time() - start_time) % loop_time)
        time.sleep(sleep)

    except KeyboardInterrupt:
        if flag_saveAllfootprint:
            print('save all footPrint')
            outdir = f"{script_dir}/../save_footPrint/"
            os.makedirs(outdir, exist_ok=True)
            dt = datetime.now()
            formatted = dt.strftime("%Y%m%d-%H%M")
            gdf_footprint.to_file(f"{outdir}/footprint_{formatted}.gpkg",driver='GPKG') 
        logging.info('interruption volontaire du script')
        print('disconnecting from mosquitto...')
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        break
