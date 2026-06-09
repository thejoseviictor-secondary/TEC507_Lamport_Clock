# TEC507_Lamport_Clock

## How to run:
• Download the files on the two computers;
<br>• Edit "app/docker-compose.yml" for each computer;
<br>• Open the terminal on the folder "app";
<br>• Stop and remove other Docker containers:
```
docker stop $(docker ps -aq)
docker-compose down --rmi all

docker rm $(docker ps -aq)
docker rmi $(docker images -aq)
```
• Run on the terminal:
```
docker-compose up --build
```
