#!/usr/bin/env python3
import requests #librairie pour faire les requetes
import json #permet de traiter les réponses des requetes
import time #timer pour l'exemple
import sys
import os 


#ip_server_planet =  '84.37.21.236'
ip_server_planet =  'safire.atmosphere.aero'

def get_token(ip_server_planete, mission_id,user_name,password):
    """ Récuperation du token d'identification pour pouvoir faire les requetes """
    #user_name = #format str
    #password =  #format str
    #requete pour obtenir le token d'identification du compte utilise
    result= requests.post(f'https://{ip_server_planete}/api/v1/auth/token/login/', 
                          data= {"username":user_name,"password":password}) 
    # permet d'afficher le resultat d'une requete , utilisable aussi pour les autres requetes , 
    # utile pour le debug ou recolte d'info comme dans la fonction add_geomarker
    #print(result.text) 
    token=json.loads(result.text)["auth_token"] #conversion de la reponse et conversion en dictionnaire pour extraction du parametre auth_token
    #print(type(token))
    return token 

"""Utilisation de l'API pour ajout/modification/suppression geomarker

--> utilisation des fonctions post, put et delete de la librairie requests. 
--> fonctionne avec les elements suivants : url + contenu au format json + headers avec les credentials
"""

#Ajout d'un nouveau geomarker et recuperation de son id
def add_geomarker (ip_server_planete, mission_id,token, data):
    add= requests.post(f'https://{ip_server_planete}/api/v1/geomarkers/'+mission_id+'/',
                   json=data,
                   headers={'Authorization': 'Token '+token})
    add_result = json.loads(add.text)
    id_geomarker = add_result["id"]
    return id_geomarker

#modification d'un geomarker a partir de son id
def modify_geomarker(ip_server_planete, mission_id, token, data,ID):

    modify= requests.put(f'https://{ip_server_planete}/api/v1/geomarkers/'+mission_id+'/'+ID+'/',
              json=data,
              headers={"Authorization": "Token "+token})
    #print(modify.text) 

#suppression d'un geomarker a partir de son id
def delete_geomarker(ip_server_planete, mission_id, token, ID):
    delete= requests.delete(f'https://{ip_server_planete}/api/v1/geomarkers/'+mission_id+'/'+ID+'/',
              headers={"Authorization": "Token "+token})


##############################
if __name__ == '__main__':
##############################

    """ Exemple d'utilisation """
    mission_id = 'SILEX'
    user_name = os.environ['planete_username']
    password  = os.environ['planete_username_passwd']

    token = get_token(mission_id,user_name,password)

    #différents types de geomarker
    circle_data_json = {"feature":{"type":"Feature","geometry":{"type":"Point","coordinates":[0.536886,26.442872]},"properties":{"radius":507,"group":"misc","color":"#008000"}}}
    line_data_json ={"feature":{"type":"Feature","geometry":{"type":"LineString","coordinates":[[-59.567413,41.932729],[-43.606702,41.503416],[-38.574045,49.728719],[-26.351879,51.012583]]},"properties":{"group":"misc","color":"#ff0000"}}}
    polygon_data_json = {"feature":{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[-53.959596,31.350068],[-46.338716,22.915948],[-28.364942,21.317498],[-27.07083,31.962044],[-35.842032,37.511477],[-53.959596,31.350068]]]},"properties":{"group":"misc","color":"#0000ff"}}}
    point_data_json = {"feature":{"type":"Feature","geometry":{"type":"Point","coordinates":[4.84,48.03]},"properties":{"label": "ronan","group":"misc","color":"#ffff00"}}}

    # Creation d'un point
    id_geomarker_1 = add_geomarker(mission_id, token, point_data_json)
    time.sleep(3)

    sys.exit()
    #modification du point
    relocate_point_data_json = {"feature":{"type":"Feature","geometry":{"type":"Point","coordinates":[-20,45]},"properties":{"group":"misc","color":"#ffff00"}}}
    modify_geomarker(mission_id, token, relocate_point_data_json, id_geomarker_1)
    time.sleep(3)

    #suppression du point
    delete_geomarker(mission_id, token, id_geomarker_1)
