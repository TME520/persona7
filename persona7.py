import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import time
import re
import urllib.request
import urllib.parse
import json
import traceback
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from joblib import load
from argparse import ArgumentParser
import boto3
from colorama import Fore, Style, init
import random

init(autoreset=True)

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

publicname='Persona/7 M3'
version='0.13'

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# starterbot's user ID in Slack: value is assigned after the bot starts up
chatbotone_id = None
eventsList = {}

# Variables
dadJokes = ['What does a baby computer call his father? Data.', 'I only seem to get sick on weekdays. I must have a weekend immune system', 'Which days are the strongest? Saturday and Sunday. The rest are weekdays.', 'Have you heard about the restaurant on the moon? Great food, no atmosphere.', 'What did Yoda say when he saw himself in 4K? HDMI.', 'How many tickles does it take to make an octopus laugh? Ten tickles.', 'That car looks nice but the muffler seems exhausted.', 'I used to play piano by ear. Now I use my hands.', 'What did the vet say to the cat? How are you feline?', 'What do you call a fake noodle? An impasta.', 'What do you call a belt made of watches? A waist of time.', 'Where do young trees go to learn? Elementree school.', 'Can February March? No, but April May!', 'When does a joke become a dad joke? When it becomes apparent.', 'Why are spiders so smart? They can find everything on the web.', 'What do you call a sad strawberry? A blueberry.', 'What runs around a baseball field but never moves? A fence.', 'Why did the coach go to the bank? To get his quarter back.', 'Which bear is the most condescending? A pan-duh!', 'Why was the robot so tired after his road trip? He had a hard drive.']

# Constants
EXAMPLE_COMMAND = 'do'

# Path to data folder (contains ML stuff)
cb1DataFolder = os.environ.get('CB1DATAFOLDER')
if not os.path.exists(cb1DataFolder):
    os.makedirs(cb1DataFolder)

# Listens to incoming messages that contain "hello"
# To learn available listener arguments,
# visit https://slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html
@app.message("hello")
def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    say(f"Hey there <@{message['user']}>!")

@app.message("debug")
def message_help(message, say):
    print(f"{message.values()}")
    say(f"Debug info: <{message['user']}> - <{message['channel']}> - <{message['ts']}> - <{message['text']}>")

@app.event("message")
def reply_to_message(message, say):
    print(f"{message.values()}")
    print(f"{dict(message)}")
    print(f"{message['blocks']}")
    say(f"{handle_command(message['text'], message['channel'], message['ts'], message['user'])}")

def cleanupIncDesc(pathToCB1File):
    print(Fore.LIGHTGREEN_EX + 'cleanupIncDesc')
    stopWords = set(stopwords.words('english'))
    crapWords = [';', ':', '-', '.', ',', '(', ')', '[', ']', '&', '--', '#']
    wordnet_lemmatizer = WordNetLemmatizer()
    wordsFiltered = []

    currentCB1File = open(pathToCB1File, 'r')
    currentDescription = currentCB1File.readlines()
    currentCB1File.close()
    for g in currentDescription:
        currentCB1File = open(pathToCB1File + '.processed', 'w')
        currentCB1File.write('--- FILTERED DATA ---\n')
        # Remove empty lines + crap characters
        if g != '' and g!='\n':
            tokens = nltk.word_tokenize(g)
            for w in tokens:
                if (w.lower() not in stopWords) and (w.lower() not in crapWords):
                    word_lemme = wordnet_lemmatizer.lemmatize(w.lower())
                    wordsFiltered.append(word_lemme)
    currentCB1File.write(str(wordsFiltered))
    currentCB1File.write('\n--- *** ---')
    currentCB1File.close()
    print('Cleaned up description:\n')
    print(str(wordsFiltered))

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

def writeDataToFile(targetFile, dataToWrite, successMsg, failureMsg, mode):
    print(Fore.LIGHTGREEN_EX + 'writeDataToFile')
    try:
        if mode == 'overwrite':
            newCB1File = open(targetFile,'w+')
        elif mode == 'append':
            newCB1File = open(targetFile,'a')
        newCB1File.write(dataToWrite)
        newCB1File.close()
        print(successMsg)
    except Exception as e:
        print(failureMsg, e)
        traceback.print_exc()
        pass

def handle_command(command, channel, ts, user):
    print(Fore.LIGHTGREEN_EX + 'handle_command')
    print(f'command: {command}, channel: {channel}, ts: {ts}, user: {user}')
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = 'Not sure what you mean. Try *{}*.'.format(EXAMPLE_COMMAND)

    # Finds and executes the given command, filling in response
    response = None

    # Create a directory for user if required
    if not os.path.exists(f'{cb1DataFolder}{user}'):
        os.makedirs(f'{cb1DataFolder}{user}')
        print(f'Folder created: {cb1DataFolder}{user}')
    
    # Log user action
    writeDataToFile(f'{cb1DataFolder}{user}/commands.log', f'User entered command: {command}', 'Event log - OK', 'Event log - KO', 'append')

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
        print('\n\n---> help\n')
        response = "*Available commands*\n\n"
        response = response + "- `bilbo`: Start the fabulous Bilbo interactive game,\n"
        response = response + "- `version`,\n"
        response = response + "- `joke`,\n"
        response = response + "- `debug`,\n"
        response = response + "- `hello`,\n"
    elif command == 'bilbo':
        print('\n\n---> bilbo\n')
        initEventsTree(channel, 'bilbo', eventsList)
        response = eventsList[channel]['text']
    elif 'hi' in command:
        response = f'Hi <@{user}>!\n'
    elif command == 'joke':
        response = random.choice(dadJokes)
    elif command == 'version':
        response = 'Running Persona7 version ' + f'{version}'

    # Sends the response back to the channel
    return response or default_response

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
    print(Fore.RED + '#############################')
    print(Fore.RED + '#        Persona/7 M3       #')
    print(Fore.RED + '#############################')
    print(Fore.GREEN + f'\n\nVersion {version} connected and running !\nREADY>')
