FROM python:3-slim

MAINTAINER David fwump38@gmail.com

# Setup script directory
RUN mkdir /home/modbot
ADD ./requirements.txt /home/modbot/requirements.txt

#Update python requeriments
RUN pip install -r /home/modbot/requirements.txt

#Add python script to docker container and grant execution rights
ADD ./modbot.py /home/modbot/modbot.py
RUN chmod +x /home/modbot/modbot.py

# Start the script
CMD python /home/modbot/modbot.py