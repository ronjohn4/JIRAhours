# Ron Johnson
# 9/24/2017
import json
from JIRAhandler import JIRAhandler

class JIRAhandlerhours(JIRAhandler):
    """JIRAhandlerhours compiles JIRA and Tempo data specific to this application's needs for a given
    date range and project.

    JIRAhandlerhours subclasses JIRAhandler that manages JIRA authentication and session.

    Methods:
        HrsGet    Returns the compile JIRA and Tempo date given a JIRA project key and a date range.
    """

    def __init__(self):
        super.__init__(self)

    def HrsGet(self, projectKey, fromDate, toDate):
        jira_sub_dict = {}
        jira_parent_dict = {}
        tempo_list = []

        # Load Tempo hours for date range
        # --Tempo url doesn't allow for limiting the fields returned
        tempo_url = 'https://levelsbeyond.atlassian.net/rest/tempo-timesheets/3/worklogs?' + \
                    'dateFrom={0}&dateTo={1}&projectKey={2}'
        url = tempo_url.format(fromDate, toDate, projectKey)
        # print('tempo url:', url)

        r = self._JIRAsession.get(url)
        if r.status_code == 200:
            json_return = json.loads(r.text)

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


        # Load JIRA Sub Tasks ---------
        keylistsub = []
        # tempo_list = tempo_list  #rewind
        for entry in tempo_list:
            if entry['issuetype'] == 'sub-task':  #Tempo uses a capital 'T' in Task
                keylistsub.append(entry['key'])

        uniquelist = set(keylistsub)
        while len(uniquelist) > 0:
            keystring = ",".join(uniquelist)
            # Key in () format doesn't allow a maxResults greater than 100
            # if more than 100 is needed we need to manually page
            jira_url = 'https://levelsbeyond.atlassian.net/rest/api/2/search?' + \
                       'jql=key%20in%20({0})&expand=names&fields=key,summary,' \
                       'customfield_13500,issuetype,parent,status&maxResults=100'
            url = jira_url.format(keystring)
            # print('url for keylistsub:', url)

            r = self._JIRAsession.get(url)
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
            # Key in () format doesn't allow a maxResults greater than 100
            # maxResults should be set to 100 or will default to 50, doubling the number of calls

            # if more than 100 is needed we need to manually page
            jira_url = 'https://levelsbeyond.atlassian.net/rest/api/2/search?' + \
                       'jql=key%20in%20({0})&expand=names&fields=key,summary,' \
                       'customfield_13500,customfield_13900,issuetype,parent,status&maxResults=100'
            url = jira_url.format(keystring)
            # print('url for keylistparent:', url)

            r = self._JIRAsession.get(url)
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

                # Custom fields are handled here.  They are presented in the UI so will be blank if not found
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

        return [jira_parent_list, tempo_list, hours]
