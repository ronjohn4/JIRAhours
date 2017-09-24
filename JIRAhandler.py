# Ron Johnson
# 9/24/2017
import requests

class JIRAhandler():
    """A generic handler that helps manage permission checking with JIRA.

    If additional interactions against
    JIRA are planned, best practice would be to subclass JIRAhandler.  The additional code can then be added to the
    new class using the session established here.

    Attributes:
        isAuth     Returns True or False if the current session is authenticated.

    Methods:
        auth       Authenticate the given auth information against JIRA.
        logout     Clears the current authentication information and sets isAuth to False.
    """
    _JIRAsession = None
    _JIRAbaseurl = None

    def __init__(self, JiraBaseUrl):
        self._JIRAsession = requests.session()
        self._JIRAbaseurl = JiraBaseUrl
        self._JIRAsession.auth = None

    def auth(self, s, auth):
        self._JIRAsession.auth = auth
        r = self._JIRAsession.get(self._JIRAbaseurl + '/rest/auth/1/session')
        if r.status_code != 200:
            self._JIRAsession.auth = None
            s['isAuthenticated'] = False
        else:
            s['isAuthenticated'] = True
        return r.status_code == 200

    def is_auth(self):
        return self._JIRAsession.auth != None

    def logout(self, s):
        self._JIRAsession.auth = None
        s['isAuthenticated'] = False


