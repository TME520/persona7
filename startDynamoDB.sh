#!/bin/bash

echo "Starting DynamoDB, listening on port 8001..."
nohup java -Djava.library.path=/home/tme520/Documents/GIT/protocol7/DynamoDBLocal_lib -jar /home/tme520/Documents/GIT/protocol7/DynamoDBLocal.jar -port 8001 &
ps -ef | grep '[D]ynamoDBLocal_lib'
echo "...done."

exit 0
