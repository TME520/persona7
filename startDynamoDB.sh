#!/bin/bash

echo "Starting DynamoDB, listening on port 8001..."
cd /home/tme520/p7prep/
nohup java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -port 8001 &
echo "...done."

exit 0
