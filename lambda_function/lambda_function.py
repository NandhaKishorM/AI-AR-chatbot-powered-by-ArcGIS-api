from botocore.vendored import requests

import time
import os
import logging
import json
import string
import random


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def build_response(message):
    return {
        "dialogAction":{
            "type":"Close",
            "fulfillmentState":"Fulfilled",
            "message":{
                "contentType":"PlainText",
                "content": message
            }
        }
    }


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }



def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n


def try_ex(func):
    try:
        return func()
    except KeyError:
        return None



def get(intent_request):
    source = intent_request['invocationSource']
    slots = intent_request['currentIntent']['slots']
    place = slots['place']
    myplace = slots['myplace']
    service = slots['service']
    sentiment = intent_request['sentimentResponse']['sentimentLabel']
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    userText = str(intent_request['inputTranscript'])
    if source == 'DialogCodeHook':
        return delegate(session_attributes, slots)
    if source == 'FulfillmentCodeHook':
        desired = "{a} in {b}".format(a=service,b=place)
        initial  = myplace
        req = {'q': initial, 'n': desired}
        server = "http://ec2-54-235-25-41.compute-1.amazonaws.com/"
        server_response = requests.post(server, data=req)
        result = server_response.json()
        result = result["content"]
        result = ','.join(result)

        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': result
            }
        )
            

def dispatch(intent_request):
    # logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'BookHotel_dev':
        return get(intent_request)
        

    raise Exception('Intent with name ' + intent_name + ' not supported')




def lambda_handler(event, context):
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
