## Author: Simon Brennan
## Date: 18 Jan 2016
## Purpose: This code will backup all the databases on a postgresql server to an Hitachi Content Platform system
## TODO:
## Clean up the temporary file created by the script in /tmp
## Better error handling (Slack post on errors)
## Slack post on success
## Move Token and Tenant configuration to OS Environment variables

#!/bin/python
import slackweb #Used to send notifications to slack on failure or success. Need to pip install slackweb.
import subprocess #Used to fire up the postgresql backup via a shell
import pycurl #Wrapper around curl to push files into the HCP
import os
import socket #used to mainly get the hostname of the system this script runs on
from datetime import datetime
from fileinput import filename

# Native HCP auth settings.
HCP_TOKEN = "Authorization: HCP usernamebase64:passwordmd5" #TODO: move this out to the os.environment
HCP_TENANT_URL = "https://namespace.tenant.domain/rest/"
SLACK_TOKEN = ""
DEBUG = True #Set to True for addition logging on the console.

def main():
    slack = slackweb.Slack(url=SLACK_TOKEN)
    now = datetime.now()
    hostname = socket.gethostname()
    filename = now.strftime("%Y%m%d%H%M%S") + "-pgdump-" + hostname + ".xz"
    fullpath = "/tmp/" + filename
    postgrescommand = "pg_dumpall | pxz -1 >" + fullpath

    print "Backing up postgresql to HCP"
    try:
        ps = subprocess.Popen(postgrescommand, shell=True)
        output = ps.communicate()[0]
        if DEBUG:
            print output
            print now.strftime("%Y%m%d%H%M%S")
            print hostname
            print "Uploading to HCP native..."
    except ValueError:
        print "There was an error running pg_dumpall" #Barf if an error occurs running pg_dumpall
    #Check to see if pg_dumpall actually created a file
        slack.notify(text="There was an error running pg_dumpall")
    try:
        isfilename = os.path.isfile(filename)
    except ValueError:
        print "Something went wrong, I can't find the pgdump file in /tmp. I expected one!"
        slack.notify(text="I couldn't find the postgresql dump file!")
    """
    Upload the backup file to an HCP tenant/namespace using the native HTTPS protocol.
    """
    try:
        filehandle = open(fullpath, 'rb')
        hcpurl = HCP_TENANT_URL + filename
        if DEBUG:
            print hcpurl
        curl = pycurl.Curl()
        curl.setopt(pycurl.HTTPHEADER, [HCP_TOKEN])
        curl.setopt(pycurl.URL, hcpurl)
        curl.setopt(pycurl.SSL_VERIFYPEER, 0)
        curl.setopt(pycurl.SSL_VERIFYHOST, 0)
        curl.setopt(pycurl.UPLOAD, 1)
        curl.setopt(pycurl.INFILESIZE, os.path.getsize(fullpath))
        curl.setopt(pycurl.READFUNCTION, filehandle.read)
        curl.perform()
        response = curl.getinfo(curl.RESPONSE_CODE)
        if DEBUG:
            print('Status: %d' % curl.getinfo(curl.RESPONSE_CODE))
            # Elapsed time for the transfer.
        if DEBUG:
            print('Status: %f' % curl.getinfo(curl.TOTAL_TIME))
            curl.close()
        if response != 201:
            raise SystemError
    except:
        print "An error occured went wrong uploading the object to the HCP!"
        slack.notify(text="Something went wrong uploading the PostgreSQL dump to the HCP!")
    else:
        slack.notify(text="Service postgresql backup successful.")

if __name__ == '__main__':
    main()
