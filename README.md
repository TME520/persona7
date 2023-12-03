# Persona/7

An Open Source personal assistant, part of Protocol/7.

> Linux
> Python
> Slack
> DynamoDB

## Install
### AWS CLI

```
apt install awscli
aws configure
```

Enter made up creds just so that DynamoDB will start:

```
[default]
aws_access_key_id = AAAABBBBCCCCDDDD
aws_secret_access_key = EEEEFFFFGGGGHHHH
region = ap-southeast-2
```

Check config:

```
aws configure list
```

### DynamoDB

Download and install [AWS DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.DownloadingAndRunning.html)

### OpenJDK

```
apt install openjdk-17-jre
```

### Python3 and friends

```
$ apt install build-essential libssl-dev libffi-dev python3 python3-pip python3-dev python3-venv python3-full python3-pil.imagetk
```

```
cd ./persona7/
python3 -m venv ./venv/
./venv/bin/pip3 install slack_bolt
./venv/bin/pip3 install nltk
./venv/bin/pip3 install boto3
./venv/bin/pip3 install colorama
```

### Prepare startup scripts
#### For DynamoDB
#### For Persona/7
## Background story and lore
### A guardian angel with silicon wings
*Persona/7* is my humble attempt at transforming virtual assistants into *personal* assistants, always looking after you, always having your wellbeing and best interest in mind. You can see *Persona/7* as a guardian angel with silicon wings.
### What v1 will look like?
Milestone 1 is very likely to be a Slack bot. I can't see further than that and I would be the happiest man on Earth if *Persona/7* got that far.
## Features
### UI: None, talk to your Persona/7 via Slack
### Local weather
### Mailbox monitoring (GMail)
### Reminders (Google Calendar)
- Public holidays
- Days off work
- Saints
- Birthdays
- Events scheduled in calendar: meetings, appointments...
### Suggestions
### Warnings
## Requirements
### Google account
- Mailbox with p7 subfolder
- Calendar
### GPS receptor
- For position & weather
- POI suggestions
