import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger("envvar")


def loadvar(envVarName: str, defaultValue: str = None):
    """
    Load a specific environment variable and log that.

    Parameters
    ----------
    envVarName : str
        The name of the environment variable
    defaultValue : str
        The default value of the environment variable

    Returns
    -------
    The value of the environment variable
    """

    envVar = os.getenv(envVarName, defaultValue)
    logger.info("Environment variable: %s = %s", envVarName, envVar)
    return envVar


def loadenv():
    """
    Load all environment variables for the application and set them to global variables in this package.
    """

    global logLevel
    global downloadPath
    global appCredentials
    global apiToken
    global query
    global contentType
    global recordPath

    load_dotenv()
    logLevel = loadvar('ATTACH_LOG_LEVEL', 'INFO')
    downloadPath = loadvar('ATTACH_DOWNLOAD_PATH', './')
    appCredentials = loadvar('ATTACH_APP_CREDENTIALS', './credentials.json')
    apiToken = loadvar('ATTACH_API_TOKEN', './token.pickle')
    query = loadvar('ATTACH_GMAIL_SEARCH', '')
    contentType = loadvar('ATTACH_CONTENT_TYPE', '')
    recordPath = loadvar('ATTACH_RECORD_PATH', './')

    # TODO: verify logLevel is a valid option

    if downloadPath[-1] != '/' and downloadPath[-1] != '\\':
        downloadPath = downloadPath + '/'
        if not os.path.isdir(downloadPath):
            logger.error(
                "Download directory does not exist, please create it first: %s", downloadPath)
            exit("Invalid download location proivded")
    if recordPath[-1] != '/' and recordPath[-1] != '\\':
        recordPath = recordPath + '/'
        if not os.path.isdir(recordPath):
            logger.error(
                "Record directory does not exist, please create it first: %s", recordPath)
            exit("Invalid Record location provided")
