import os
import time
import re
import urllib.request
import urllib.parse
import json
from slackclient import SlackClient
import traceback
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from joblib import load
from argparse import ArgumentParser
import boto3
from colorama import Fore, Style, init
import threading

init(autoreset=True)

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

publicname='Persona/7'
version='0.10'

# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

# starterbot's user ID in Slack: value is assigned after the bot starts up
chatbotone_id = None
eventsList = {}

# Path to data folder (contains ML stuff)
cb1DataFolder = os.environ.get('CB1DATAFOLDER')
if not os.path.exists(cb1DataFolder):
    os.makedirs(cb1DataFolder)

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = 'do'
MENTION_REGEX = '^<@(|[WU].+?)>(.*)'

def testMultithread(argument):
    print(threading.currentThread().getName(), f'Running with argument {argument}...')

def publishToSlack(msg, chan, icon, creds):
    try:
        print(Fore.LIGHTGREEN_EX + 'publishToSlack')
        slackCallbackId=''
        slackColor='#3AA3E3'
        slackActionName=''
        slackActionText=''
        slackActionType=''
        slackActionValue=''
        creds.api_call(
            'chat.postMessage',
            channel=chan,
            text=msg,
            icon_emoji=icon,
            as_user='true',
            attachments=[{
                'text': '',
                'callback_id': slackCallbackId + 'autoassign_feedback',
                'color': slackColor,
                'attachment_type': 'default',
                'actions': [{
                'name': slackActionName,
                'text': slackActionText,
                'type': slackActionType,
                'value': slackActionValue
                }]
            }]
        )
    except Exception as e:
        print(Fore.RED + '[ERROR] A problem occured while publishing on Slack.', e)
        pass

def callURL(url2call, creds):
    try:
        print(Fore.LIGHTGREEN_EX + 'callURL')
        url = url2call
        req = urllib.request.Request(url, headers=creds)
        response = urllib.request.urlopen(req)
        payload = response.read()
        return payload
    except urllib.error.HTTPError:
        print(Fore.RED + '[HTTPError] Failed to call ' + str(url) + '\nProvider might be down or credentials might have expired.')
        return 'HTTPERROR'
        pass
    except urllib.error.URLError:
        print(Fore.RED + '[URLError] Failed to call ' + str(url) + '\nNetwork connection issue (check Internet access).')
        return "URLERROR"
        pass

def dynamodbTableCheck(databaseURL, tableName):
    try:
        print(Fore.LIGHTGREEN_EX + 'dynamodbTableCheck')
        dynamodb = boto3.client('dynamodb', endpoint_url=databaseURL)
        response = dynamodb.describe_table(TableName=tableName)
    # except dynamodb.exceptions.ResourceNotFoundException:
    except Exception as e:
        print('[DEBUG] DynamoDB table ' + tableName + ' not found')
        response = 'Table not found'
        # traceback.print_exc()
        pass
    return str(response)

def dynamodbListTableItems(databaseURL, tableName):
    try:
        print(Fore.LIGHTGREEN_EX + 'dynamodbListTableItems')
        dynamodb = boto3.resource('dynamodb', endpoint_url=databaseURL)
        tableToList = dynamodb.Table(tableName)
        tableToList.scan()
        response = tableToList.scan()
    except Exception as e:
        print('[ERROR] Failed to list content of database table ' + tableName + '.\n', e)
        response = 'Table listing failed'
        traceback.print_exc()
        pass
    return response

def initEventsTree(userId, eventsTreeName, eventsList):
    print(Fore.LIGHTGREEN_EX + 'initEventsTree')
    print("initEventsTree: " + str(userId) + ", " + str(eventsTreeName) + ", " + str(eventsList))
    if eventsTreeName == 'bilbo':
        # Menu
        eventsList[userId] = {'ts': 1550056556.000300, 'expires': 1550111111.000300, 'text': '*Welcome to Bilbo interactive game*\n\nStart new game ?\n- yes\n- no', 'option1': 'yes', 'action1': 'bilbo_yes', 'option2': 'no', 'action2': 'bilbo_no', 'option3': None, 'action3': None, 'url': None, 'eventId': 'bilbo_start', 'callFunction': None, 'step': 'ping'}
        # bilbo_yes
        eventsList['bilbo_yes'] = {'ts': 0, 'expires': 0, 'text': '*Initializing a new game...*\nYou now are in a hobbit hole.\n- explore\n- leave', 'option1': 'explore', 'action1': 'bilbo_explore', 'option2': 'leave', 'action2': 'bilbo_leave', 'option3': None, 'action3': None, 'url': None, 'eventId': None, 'callFunction': None, 'step': 'ping'}
        # bilbo_no
        eventsList['bilbo_no'] = {'ts': 0, 'expires': 0, 'text': '*Goodbye, come again !*', 'option1': None, 'action1': None, 'option2': None, 'action2': None, 'option3': None, 'action3': None, 'url': None, 'eventId': None, 'callFunction': None, 'step': 'ping'}
        # bilbo_explore
        eventsList['bilbo_explore'] = {'ts': 0, 'expires': 0, 'text': 'The inside of the hole is very clean. The wooden floor shines. The windows are round.\n- leave', 'option1': 'leave', 'action1': 'bilbo_leave', 'option2': None, 'action2': None, 'option3': None, 'action3': None, 'url': None, 'eventId': None, 'callFunction': None, 'step': 'ping'}
        # bilbo_leave
        eventsList['bilbo_leave'] = {'ts': 0, 'expires': 0, 'text': 'The sky is cloudy and you feel a few drops falling on your arms and head.\n*This very short game ends here.*', 'option1': None, 'action1': None, 'option2': None, 'action2': None, 'option3': None, 'action3': None, 'url': None, 'eventId': None, 'callFunction': None, 'step': 'ping'}
    return eventsList

def writeDataToFile(targetFile,dataToWrite,successMsg,failureMsg):
    print(Fore.LIGHTGREEN_EX + 'writeDataToFile')
    newCB1File = open(targetFile,'w')
    newCB1File.write(dataToWrite)
    newCB1File.close()
    print(successMsg)

def parse_bot_commands(slack_events):
    # print(Fore.LIGHTGREEN_EX + 'parse_bot_commands')
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event['type'] == 'message' and not 'subtype' in event:
            # Expecting CB1 name at the beginning of the message
            user_id, message = parse_direct_mention(event['text'])
            if user_id == chatbotone_id:
                return message, event['user']   
    return None, None

def parse_direct_mention(message_text):
    print(Fore.LIGHTGREEN_EX + 'parse_direct_mention')
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
    print(Fore.LIGHTGREEN_EX + 'handle_command')
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = 'Not sure what you mean. Try *{}*.'.format(EXAMPLE_COMMAND)

    # Finds and executes the given command, filling in response
    response = None

    global snowBase64
    global snowURL
    global yestIncQuery
    global freshIncQuery
    global recentIncQuery
    global oldIncQuery
    global pickIncQuery
    global statsIncQuery
    global statsChgQuery
    global statsReqQuery
    global p1AlertsQuery
    global p2AlertsQuery

    # Check if we are waiting for a specific answer from user
    for key in eventsList:
        # If this is the case, change Step to pong...
        if str(key) == str(channel):
            print('We have some business to do...')
            print('ts: ' + str(eventsList[key]['ts']))
            print('expires: ' + str(eventsList[key]['expires']))
            print('text: ' + str(eventsList[key]['text']))
            print('o1: ' + str(eventsList[key]['option1']))
            print('a1: ' + str(eventsList[key]['action1']))
            print('o2: ' + str(eventsList[key]['option2']))
            print('a2: ' + str(eventsList[key]['action2']))
            print('o3: ' + str(eventsList[key]['option3']))
            print('a3: ' + str(eventsList[key]['action3']))
            print('url: ' + str(eventsList[key]['url']))
            print('eventId: ' + str(eventsList[key]['eventId']))
            print('callFunction: ' + str(eventsList[key]['callFunction']))
            print('step: ' + eventsList[key]['step'])
            eventsList[key]['step'] = 'pong'
            print('step: ' + eventsList[key]['step'])
            # ...then perform the required action
            if command == str(eventsList[key]['option1']):
                response = str(eventsList[eventsList[key]['action1']]['text'])
                eventsList[channel] = {'ts': 0, 'expires': 0, 'text': eventsList[eventsList[key]['action1']]['text'], 'option1': eventsList[eventsList[key]['action1']]['option1'], 'action1': eventsList[eventsList[key]['action1']]['action1'], 'option2': eventsList[eventsList[key]['action1']]['option2'], 'action2': eventsList[eventsList[key]['action1']]['action2'], 'option3': eventsList[eventsList[key]['action1']]['option3'], 'action3': eventsList[eventsList[key]['action1']]['action3'], 'url': eventsList[eventsList[key]['action1']]['url'], 'eventId': eventsList[eventsList[key]['action1']]['eventId'], 'callFunction': eventsList[eventsList[key]['action1']]['callFunction'], 'step': 'ping'}
                print('New event: ' + str(eventsList[channel]))
            elif command == str(eventsList[key]['option2']):
                response = str(eventsList[eventsList[key]['action2']]['text'])
                eventsList[channel] = {'ts': 0, 'expires': 0, 'text': eventsList[eventsList[key]['action2']]['text'], 'option1': eventsList[eventsList[key]['action2']]['option1'], 'action1': eventsList[eventsList[key]['action2']]['action1'], 'option2': eventsList[eventsList[key]['action2']]['option2'], 'action2': eventsList[eventsList[key]['action2']]['action2'], 'option3': eventsList[eventsList[key]['action2']]['option3'], 'action3': eventsList[eventsList[key]['action2']]['action3'], 'url': eventsList[eventsList[key]['action2']]['url'], 'eventId': eventsList[eventsList[key]['action2']]['eventId'], 'callFunction': eventsList[eventsList[key]['action2']]['callFunction'], 'step': 'ping'}
                print('New event: ' + str(eventsList[channel]))
            elif command == str(eventsList[key]['option3']):
                response = str(eventsList[eventsList[key]['action3']]['text'])
                eventsList[channel] = {'ts': 0, 'expires': 0, 'text': eventsList[eventsList[key]['action3']]['text'], 'option1': eventsList[eventsList[key]['action3']]['option1'], 'action1': eventsList[eventsList[key]['action3']]['action1'], 'option2': eventsList[eventsList[key]['action3']]['option2'], 'action2': eventsList[eventsList[key]['action3']]['action2'], 'option3': eventsList[eventsList[key]['action3']]['option3'], 'action3': eventsList[eventsList[key]['action3']]['action3'], 'url': eventsList[eventsList[key]['action3']]['url'], 'eventId': eventsList[eventsList[key]['action3']]['eventId'], 'callFunction': eventsList[eventsList[key]['action3']]['callFunction'], 'step': 'ping'}
                print('New event: ' + str(eventsList[channel]))

    # This is where you start to implement more commands!
    print(f'Command: {command}')
    if command.startswith(EXAMPLE_COMMAND):
        response = 'Sure...write some more code then I can do that!'
    elif command == 'help':
        response = "*Available commands*\n\n"
        response = response + "- `[ fresh | recent | yest | old ] inc`: SNow incidents opened [ today | last 7 days | yesterday | last 3 months ],\n"
        response = response + "- `p1` or `p2`: List P1/P2 alerts currently active,\n"
        response = response + "- `bilbo`: Start the fabulous Bilbo interactive game,\n"
        response = response + "- `snow switch prod` or `snow switch meng`: Switch between Prod & Meng ServiceNow,\n"
        response = response + "- `show contacts`: Link to a list of contacts on the wiki,\n"
        response = response + "- `snow check <INC>`: Determine if an INCident should be assigned to PENG Ops or not,\n"
        response = response + "- `snow stats`: Show number of INC, REQ & CHG,\n"
        response = response + "- `snow [ ignore | forget ] <INC>`: Set/Unset ignore flag on a ServiceNow INCident.\n"
    elif command == 'bilbo':
        print('\n\n---> bilbo\n')
        initEventsTree(channel, 'bilbo', eventsList)
        response = eventsList[channel]['text']
    elif command == 'show contacts':
        print('\n\n---> show contacts\n')
        response = '*MIM*: 1 300 000 000\n'
        response = response + '*MUM*: 0123 456 789\n'
        response = response + '*DAD*: 0123 456 789\n'
        response = response + '*DOCTOR*: 0123 456 789\n'
        response = response + '*PIZZA*: 0123 456 789\n'
        response = response + '*GHOSTBUSTAZ*: 0123 456 789\n'
        response = response + '\n> https://example.jira.com/wiki/spaces/DBMW/pages/0123456789/The+Big+What+To+Do+Page#TheBigWhatToDoPage-...Ineedtocontactadepartment/service'

    # Sends the response back to the channel
    publishToSlack(response or default_response, channel, ':coc1:', slack_client)

if __name__ == '__main__':
    if slack_client.rtm_connect(with_team_state=False, auto_reconnect=True):
        print(Fore.RED + '#############################')
        print(Fore.RED + '#        Persona/7 M1       #')
        print(Fore.RED + '#############################')
        print(Fore.GREEN + f'\n\nVersion {version} connected and running !\nREADY>')
        # Read bot's user ID by calling Web API method `auth.test`
        chatbotone_id = slack_client.api_call('auth.test')['user_id']
        # print('Chatbotone_id: ' + str(chatbotone_id))
        while True:
            try:
                command, channel = parse_bot_commands(slack_client.rtm_read())
            except Exception as e:
                print(Fore.RED + '[ERROR] Failed to connect to Slack\n', e)
                traceback.print_exc()
                pass
                try:
                    print(Fore.RED + '[ERROR] Damn Slack')
                except Exception as f:
                    print(Fore.RED + '[ERROR] Damn damn\n', f)
                    pass
                time.sleep(4)
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print(Fore.RED + '[ERROR] Connection failed. Exception traceback printed above.')
