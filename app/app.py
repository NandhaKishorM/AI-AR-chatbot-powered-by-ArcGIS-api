import json
from flask import json,request,Flask,make_response,jsonify
import requests
import arcgis
from arcgis.gis import GIS
from arcgis.geocoding import geocode
import boto3
import urllib
import json
import arcgis
from botocore.exceptions import ClientError

import re

app = Flask(__name__)

def get_result(token,value, dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb', 'ap-south-1')

    table = dynamodb.Table('gis')

    try:
        response = table.get_item(Key={'token':token, 'value': value})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        return response['Item']


def generateToken(username, password, portalUrl):
    '''Retrieves a token to be used with API requests.'''
    parameters = urllib.parse.urlencode({'username' : username,
                                   'password' : password,
                                   'client' : 'referer',
                                   'referer': portalUrl,
                                   'expiration': 60,
                                   'f' : 'json'}).encode("utf-8")
    response = urllib.request.urlopen(portalUrl + '/sharing/rest/generateToken?',
                              parameters).read()

    jsonResponse = json.loads(response)
    if 'token' in jsonResponse:
        return jsonResponse['token']
    elif 'error' in jsonResponse:
        print (jsonResponse['error']['message'])
        for detail in jsonResponse['error']['details']:
            print (detail)


def update_value(token,value,updated_token, dynamodb=None):
    session = boto3.Session(
    aws_access_key_id="aws access key",
    aws_secret_access_key="aws secret key",
)
    if not dynamodb:
        dynamodb = session.resource('dynamodb', 'ap-south-1')

    table = dynamodb.Table('gis')

    response = table.update_item(
        Key={
            'token': token,
            'value': value
        },
        UpdateExpression="set info.updated_token=:t",
        ExpressionAttributeValues={
            ':t': updated_token
          
        },
        ReturnValues="UPDATED_NEW"
    )
    return response


#input geocode
def rest_function(initial,final):
    try:
        result = get_result("token","string")
        token = result['info']['updated_token']
        portal =  arcgis.GIS(token =token,
        referer="https://www.arcgis.com")
        print("token accepted")
    except Exception as e:
        print("generating token")
        token_generated = generateToken('username','password','https://www.arcgis.com')
        update_response = update_value("token","string",token_generated)
        token_generated = update_response['Attributes']['info']['updated_token']
        print("Update succeeded:")
        portal =  arcgis.GIS(token =token_generated,
        referer="https://www.arcgis.com")
    geocode_result_input = geocode(address=initial, as_featureset=True)
    res_input = geocode_result_input.features[0]
    g_input = res_input.geometry
    g_x_input = g_input["x"]
    g_y_input = g_input["y"]
    g_attributes_input = res_input.attributes
    g_attributes_input = g_attributes_input["Match_addr"]


    #nearby hospital geocode dict
    geocode_result = geocode(address=final, as_featureset=True)
    res_0 = geocode_result.features[0]
    init_res = geocode_result.features[0].geometry['spatialReference']
    g_0 = res_0.geometry
    g_0_x = g_0["x"]
    g_0_y = g_0["y"]
    g_0_attributes = res_0.attributes
    g_0_attributes = g_0_attributes["Match_addr"]
    values = [{
                "geometry": {
                    "x": g_0_x,
                    "y":g_0_y
                },
                "attributes": {
                    "Name":g_0_attributes
                }
            }]

    for i  in range (1,len(geocode_result)):
        res = geocode_result.features[i]
        g = res.geometry
        g_x = g["x"]
        g_y = g["y"]
        g_attributes = res.attributes
        g_attributes = g_attributes["Match_addr"]
        #print(i)
        

        update = {
                "geometry": {
                    "x": g_x,
                    "y": g_y
                },
                "attributes": {
                    "Name":g_attributes 
                }
            }
            
        values.append(update)
        #print(new_dicts)


    # the wkid and latestwkid
    wkid = init_res['wkid']
    latestWkid = init_res['latestWkid']

    # inputs
    incidents = {
        "spatialReference": {
            "latestWkid": latestWkid,
            "wkid": wkid 
        },
        "features": [
            {
                "geometry": {
                    "x": g_x_input ,
                    "y": g_y_input
                },
                "attributes": {
                    "Name": g_attributes_input
                }
            }
        ]
    }
    facilities = {
        "spatialReference": {
            "latestWkid": latestWkid,
            "wkid": wkid
        },
        "features": values
    }

    # Connect to the closest facility service and call it
    #api_key = "YOUR_API_KEY"
  
  

        
    closest_facility = arcgis.network.ClosestFacilityLayer(portal.properties.helperServices.closestFacility.url,
                                                               gis=portal)
    result = closest_facility.solve_closest_facility(facilities=facilities,
                                                     incidents=incidents,
                                                     default_target_facility_count=8,
                                                     return_facilities=True,
                                                     return_cf_routes=True)
    return print_result(result)


def listing(output):
    output_facility = output.replace("-ER","")
    
    list_val =  output_facility.split('\n')
    res = []
    for i in range(1,len(list_val)):
        s = list_val[i]
        value = re.sub('\s{2,}', ' ', s)
        try:
            value = value.split("-")[1]
            res.append(value)
        except:
            res.append(value)
        #res.append(time)

    list_val = list(set(res))
    return list_val
   
def print_result(result):
    output_routes = arcgis.features.FeatureSet.from_dict(result["routes"]).sdf
    #output = output_routes[["Name", "Total_TravelTime", "Total_Kilometers"]].to_string(index=False)
    name = output_routes[["Name"]].to_string(index=False)
    total_distance = output_routes[["Total_Kilometers"]].to_string(index=False)
    time = output_routes[["Total_TravelTime"]].to_string(index=False)
    name = listing(name)
    time = listing(time)
    total_distance = listing(total_distance)
    output = []
    for i in range(0,len(name)):
        res = name[i] + ' ' + "you can reach in {} minutes".format(round(float(time[i]))) + ' ' +  " and it's within {} kilometers".format(round(float(total_distance[i])))
        output.append(res)
    return output





# route http posts to this method
@app.route('/', methods=['POST'])
def test():
    #the search query you want
    initial= request.form.get("q")
  
    desired = request.form.get("n")
    output = rest_function(initial,desired)


    
    result = dict(content = desired)
 
    
    return json.dumps(result)

if __name__ == "__main__":
    app.run()