from flask import json
import requests
import json
from timeit import default_timer as timer
import logging
from mockdata import SetMockData


class JIRAhandler():
    _JiraSession = None
    _JiraBaseUrl = None

    def __init__(self, JiraBaseUrl):
        self._JiraSession = requests.session()  # NOT a Flask session
        self._JiraBaseUrl = JiraBaseUrl
        self._JiraSession.auth = None

    # gather JIRA information about the current user and format
    def user(self):
        error = None
        r = self._JiraSession.get(self._JiraBaseUrl + '/rest/api/2/myself')

        formatted = {}
        if r.status_code == 200:
            json_return = json.loads(r.text)
            formatted['self'] = json_return['self']
            formatted['key'] = json_return['key']
            formatted['name'] = json_return['name']
            formatted['displayName'] = json_return['displayName']
            formatted['active'] = json_return['active']
            formatted['timeZone'] = json_return['timeZone']
        else:
            error = 'There was a problem with the JIRA call, status_code=' + str(r.status_code)

        return r.text, formatted, error


    # authenticate the specified auth against JIRA
    def auth(self, s, auth):
        self._JiraSession.auth = auth
        r = self._JiraSession.get(self._JiraBaseUrl + '/rest/auth/1/session')
        if r.status_code != 200:
            self._JiraSession.auth = None
            s['isAuthenticated'] = False
        else:
            s['isAuthenticated'] = True
        return r.status_code == 200


    def isAuth(self):
        return self._JiraSession.auth != None


    def logout(self, s):
        self._JiraSession.auth = None
        s['isAuthenticated'] = False


    # Aggregates Tempo and JIRA data for presentation
    def HrsGet(self, projectKey, fromDate, toDate):
        jira_sub_dict = {}
        jira_parent_dict = {}
        tempo_list = []

        # Set to True to run offline.  There are a set of print statements below that output the mock data
        # when online.  The results can be copied and pasted into the lines that hardcode the mock data.
        _offline = False

        logging.basicConfig(level=logging.DEBUG)
        time_start = timer()

        if _offline:
            SetMockData()


        # Load Tempo hours for date range
        if not _offline:
            # --Tempo url doesn't allow for limiting the fields returned
            tempo_url = 'https://levelsbeyond.atlassian.net/rest/tempo-timesheets/3/worklogs?' + \
                        'dateFrom={0}&dateTo={1}&projectKey={2}'
            url = tempo_url.format(fromDate, toDate, projectKey)
            # print('tempo url:', url)
            logging.debug('tempo_url: {0}'.format(url))

            r = self._JiraSession.get(url)
            logging.debug('return status: {0}'.format(r.status_code))
            if r.status_code == 200:
                json_return = json.loads(r.text)
                logging.debug('length:{0}'.format(len(json_return)))
                if len(json_return) > 0:
                    logging.debug('first row: {0}'.format(json_return[1]))

                # create clean Tempo list
                for entry in json_return:
                    tempo_list.append({'id': entry['id'],
                                       'parentkey': entry['issue']['key'],
                                       'author': entry['author']['name'],
                                       'dateCreated': entry['dateCreated'],
                                       'key': entry['issue']['key'],
                                       'customer': None,
                                       'timeSpentSeconds': entry['timeSpentSeconds'],
                                       'issuetype': entry['issue']['issueType']['name'].lower(),
                                       'summary': entry['issue']['summary'],
                                       'tempocomment': entry['comment'],
                                       'parentsummary': entry['issue']['summary']})

        time_current = timer()
        logging.debug('Tempo done - start:{0}, current:{1}, duration:{2}'.format(time_start, time_current,
                                                                                 time_current - time_start))


        # Load JIRA Sub Tasks ---------
        keylistsub = []
        # tempo_list = tempo_list  #rewind
        for entry in tempo_list:
            if entry['issuetype'] == 'sub-task':  #Tempo uses a capital 'T' in Task
                keylistsub.append(entry['key'])

        uniquelist = set(keylistsub)
        while len(uniquelist) > 0:
            keystring = ",".join(uniquelist)
            if not _offline:
                # Key in () format doesn't allow a maxResults greater than 100
                # if more than 100 is needed we need to manually page
                jira_url = 'https://levelsbeyond.atlassian.net/rest/api/2/search?' + \
                           'jql=key%20in%20({0})&expand=names&fields=key,summary,' \
                           'customfield_13500,issuetype,parent,status&maxResults=100'
                url = jira_url.format(keystring)
                # print('url for keylistsub:', url)

                r = self._JiraSession.get(url)
                json_return = json.loads(r.text)
                json_return = json_return['issues']

                for entry in json_return:
                    uniquelist.discard(entry['key'])  #list will be processed again until empty
                    jira_entry = {'key': entry['key'],
                                  'parentkey': entry['fields']['parent']['key']
                                  }

                    jira_sub_dict[jira_entry['key']] = jira_entry


        # Load JIRA Parent ----------------
        keylistparent = []
        # tempo_list = tempo_list
        for entry in tempo_list:
            if entry['issuetype'] == 'sub-task':  #JIRA uses a lower case 't' in task
                entry['parentkey'] = jira_sub_dict[entry['key']]['parentkey']
                keylistparent.append(jira_sub_dict[entry['key']]['parentkey'])  # add parents to non sub-task list
            else:
                keylistparent.append(entry['key'])  # add all non sub-tasks to list

        uniquelist = set(keylistparent)
        while len(uniquelist) > 0:
            keystring = ",".join(uniquelist)
            if not _offline:
                # Key in () format doesn't allow a maxResults greater than 100
                # maxResults should be set to 100 or will default to 50, doubling the number of calls

                # if more than 100 is needed we need to manually page
                jira_url = 'https://levelsbeyond.atlassian.net/rest/api/2/search?' + \
                           'jql=key%20in%20({0})&expand=names&fields=key,summary,' \
                           'customfield_13500,customfield_13900,issuetype,parent,status&maxResults=100'
                url = jira_url.format(keystring)
                # print('url for keylistparent:', url)

                r = self._JiraSession.get(url)
                json_return = json.loads(r.text)
                json_return = json_return['issues']

                for entry in json_return:
                    uniquelist.discard(entry['key'])  #list will be processed again until empty
                    jira_entry = {'key': entry['key'],
                                  'customer': None,
                                  'totaltimeSpentSeconds': 0,
                                  'summary': entry['fields']['summary'],
                                  'issuetype': entry['fields']['issuetype']['name'].lower(),
                                  'billstate': None,
                                  'status': entry['fields']['status']['name']}

                    if 'customfield_13500' in entry['fields']:
                        if entry['fields']['customfield_13500'] != None:
                            jira_entry['customer'] = entry['fields']['customfield_13500']['value']

                    if 'customfield_13900' in entry['fields']:
                        if entry['fields']['customfield_13900'] != None:
                            jira_entry['billstate'] = entry['fields']['customfield_13900']['value']

                    jira_parent_dict[jira_entry['key']] = jira_entry

        hours = {
            'billable': 0,
            'nonbillable': 0
        }
        for entry in tempo_list:
            # sum hours per JIRA ticket and total
            # add up Tempo time for each Jira ticket
            jira_parent_dict[entry['parentkey']]['totaltimeSpentSeconds'] += entry['timeSpentSeconds']

            if jira_parent_dict[entry['parentkey']]['billstate'] in ('Billable', 'Billable but Not Billed'):
                hours['billable'] += entry['timeSpentSeconds']
            else:
                hours['nonbillable'] += entry['timeSpentSeconds']

        for entry in tempo_list:
            if entry['issuetype'] == 'sub-task':
                entry['parentkey'] = jira_sub_dict[entry['key']]['parentkey']
            else:
                entry['parentkey'] = entry['key']

            entry['customer'] = jira_parent_dict[entry['parentkey']]['customer']

        # convert JIRA to a list
        jira_parent_list = []
        for k, v in jira_parent_dict.items():
            jira_parent_list.append(v)

        time_current = timer()
        logging.debug(
            'Final - start:{0}, current:{1}, duration:{2}'.format(time_start, time_current, time_current - time_start))

        # output mock data from real data to be copied into code. Uncomment line below,
        # run a search, copy results and paste where mock data is set after the _debug test.
        # print('Mock data')
        # for v in tempo_list:
        #     print('tempo_list.append({0})'.format(v))
        #
        # print(jira_sub_dict)
        # for k, v in jira_sub_dict.items():
        #     print("jira_sub_dict['{0}'] =  {1}".format(k,v))
        #
        # for k, v in jira_parent_dict.items():
        #     v['totaltimeSpentSeconds'] = 0
        #     print("jira_parent_dict['{0}'] =  {1}".format(k,v))


        return [jira_parent_list, tempo_list, hours]

