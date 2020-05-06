#from __future__ import print_function

import json
import logging
import mimetypes
import os
import os.path
import pickle
import re
import time

from oauthlib.oauth2.rfc6749.errors import OAuth2Error

import envvar
from emailMsg import Attachment, Email, EmailMsg, GoogleAuth

logger = logging.getLogger("attachBack")

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

RECORD_FILENAME = 'records.txt'


def authenticate(tokenFileName: str, credFileName: str):
    """
    Reads previous tokens and credentials if they exist, and uses them to to authenticate with Google APIs by
    creating a GoogleAuth object.

    Parameter:
    ----------
    tokenFileName : str
    credFileName : str

    Returns:
    --------
    GoogleAuth object
    """

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(tokenFileName):
        with open(tokenFileName, 'rb') as token:
            creds = pickle.load(token)
            logger.info("Credentials read from %s", tokenFileName)

    # Load the secrets
    with open(credFileName, 'r') as json_file:
        client_config = json.load(json_file)
        logger.info("App secrets read from %s", credFileName)

    try:
        auth = GoogleAuth(SCOPES, GoogleAuth.API_GMAIL,
                          GoogleAuth.API_VER_1, client_config, creds)

        # Save the credentials for the next run
        with open(tokenFileName, 'wb') as token:
            pickle.dump(auth.creds, token)
            logger.info("Credentials saved to %s for future use.",
                        tokenFileName)
        logging.info("Successfully authenticated to gmail.")
    except OAuth2Error as e:
        logging.error("Failure to authenticate to gmail: %s", e)
        raise e
    return auth


def isValidFileName(name: str):
    """
    Returns true or false based on if the provided string is a valid filename based on Windows filename limitations.
    It tests for invalid characters 
        \\ / : " ? < > | and on if the filename or the extension ends in a period.

    Parameters:
    ------------
    name : str
        the filename to be tested

    Returns:
    --------
    true if the file name is valid, false otherwise.
    """

    if not name:
        logger.debug("Testing filename failed on missing name.")
        return False

    # reg check for invalid characters: [\\\/:\"\?<>|]+
    p = re.compile(r"[\\\/:\"\?<>|]+")
    if p.search(name):
        logger.debug(
            "Testing filename failed on invalid character \\/:\"?<>| : %s", name)
        return False

    # check that filename doesn't end in a . and the extension doesn't end in a .
    chunks = name.split('.')
    if len(chunks) > 0 and not chunks[-1]:
        logger.debug(
            "Testing filename failed on extension or filename ended in period: %s", name)
        return False
    if len(chunks) > 2 and not chunks[-2]:
        logger.debug(
            "Testing filename failed on filename ended in period: %s", name)
        return False

    return True


def downloadAttachmentsFromGmail(auth: GoogleAuth, downloadPath: str, recordFile: str, records: list, query: str = '', contentType: str = ''):
    """
    Downloads the attachments from gmail filtered by the query str and the desired content type.

    Parameters
    ----------
    auth : GoogleAuth
        Authentication object into Google APIs
    downloadPath : str
        Path to download attachments into
    recordFile : str
        Path and file name to record downloaded attachments into to ensure they are not duplicated on subsequent runs
    query : str
        gmail query string, used to filter emails that will be checked for attachments
    contentType : str
        string or substring that represents content-types of attachments, such as "application/pdf" or "image/jpeg" or "image/"
    """

    records = []
    recf = open(recordFile, 'a+', encoding="utf-8")
    records = [record.rstrip() for record in recf.readlines()]

    emails = Email(auth, query=query)

    for email in emails:
        logger.debug("Email ID: %s Subject: %s", email.msgId, email.subject)
        for attachment in email:
            # skip if the attachment has already been downloaded
            if (email.msgId + attachment.filename) in records:
                logger.info(
                    "Attachment already downloaded, skipping. Email was: %s", email.subject)
                continue

            if contentType in attachment.contentType:
                logger.debug("Content-type string of attachment: %s",
                             attachment.contentType)
                mimetype = attachment.contentType.split(';')[0].strip()
                logger.debug("Mimetype determined to be: %s", mimetype)
                filename = attachment.filename

                logger.debug("Attachment filename: %s", attachment.filename)
                # if there's no filename or its invalid, we make one up and guess the extension from content-type
                if not attachment.filename or not isValidFileName(attachment.filename):
                    extension = mimetypes.guess_extension(
                        mimetype)
                    if not extension:
                        logger.warning(
                            "Skipping attachment. Unable to determine extension from content-type for unnamed attachment in email: %s.", email.subject)
                        continue

                    filename = "temp" + str(time.time()) + extension
                    logger.info("Invalid name: %s - new name: %s",
                                attachment.filename, filename)
                if filename:
                    logger.debug("Filename: %s", filename)

                    # create a name modifier if there's already a file with the same name
                    diff = ''
                    if os.path.exists(''.join([downloadPath, filename])):
                        logger.info("Duplicate file %s found.", filename)
                        diff = str(time.time())+'-'

                    path = ''.join(
                        [downloadPath, diff, filename])
                    logger.info("Writing: %s", path)
                    f = open(path, 'wb')
                    f.write(attachment.bytes)
                    f.close()

                    newRecord = email.msgId + attachment.filename
                    records.append(newRecord)

                    recf.write(newRecord + "\n")
    recf.close()


def main():
    """
    Main execution point for the application.
    Sets the log level and reads input parameters.
    """

    LOGFORMAT = "%(asctime)s %(levelname)s - %(name)s.%(funcName)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=LOGFORMAT)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)

    envvar.loadenv()
    logger.setLevel(envvar.logLevel)

    recordFile = envvar.recordPath + RECORD_FILENAME

    auth = authenticate(envvar.apiToken, envvar.appCredentials)

    downloadAttachmentsFromGmail(
        auth, envvar.downloadPath, recordFile, envvar.query, envvar.contentType)


if __name__ == '__main__':
    main()
