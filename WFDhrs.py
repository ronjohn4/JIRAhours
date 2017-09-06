import requests
import json
from timeit import default_timer as timer
import logging

jira_sub_dict = {}
jira_parent_dict = {}
tempo_list = []

# Set to True to run offline.  There are a set of print statements below that output the mock data
# when online.  The results can be copied and pasted into the lines that hardcode the mock data.
_offline = True


def LoadJiraSub(keylist):
    global jira_sub_dict

    # if _debug then the mock data has already been set
    if  not _offline:
        jira_url = 'https://levelsbeyond.atlassian.net/rest/api/2/search?' + \
                   'jql=key%20in%20({0})&expand=names&fields=key,summary,' \
                   'customfield_13500,issuetype,parent,status&maxResults=500'
        url = jira_url.format(keylist)

        r = requests.get(url, auth=GetAuth())
        json_return = json.loads(r.text)
        json_return = json_return['issues']

        for entry in json_return:
            jira_entry = {'key': entry['key'],
                          'parentkey': entry['fields']['parent']['key']
                         }

            jira_sub_dict[jira_entry['key']] = jira_entry
    return


def LoadJiraParent(keylist):
    global jira_parent_dict

    # if _debug then the mock data has already been set
    if  not _offline:
        jira_url = 'https://levelsbeyond.atlassian.net/rest/api/2/search?' + \
                        'jql=key%20in%20({0})&expand=names&fields=key,summary,' \
                        'customfield_13500,customfield_13900,issuetype,parent,status&maxResults=500'
        url = jira_url.format(keylist)

        r = requests.get(url, auth=GetAuth())
        json_return = json.loads(r.text)
        json_return = json_return['issues']

        for entry in json_return:
            jira_entry = {'key': entry['key'],
                          'customer': None,
                          'totaltimeSpentSeconds': 0,
                          'summary': entry['fields']['summary'],
                          'issuetype': entry['fields']['issuetype']['name'],
                          'billstate': None,
                          'status': entry['fields']['status']['name']}

            if 'customfield_13500' in entry['fields']:
                if entry['fields']['customfield_13500'] != None:
                    jira_entry['customer'] = entry['fields']['customfield_13500']['value']

            if 'customfield_13900' in entry['fields']:
                if entry['fields']['customfield_13900'] != None:
                    jira_entry['billstate'] = entry['fields']['customfield_13900']['value']

            jira_parent_dict[jira_entry['key']] = jira_entry
    return


# Aggregates Tempo and JIRA data for presentation
def HrsGet(projectKey, fromDate, toDate):
    global tempo_list
    global jira_sub_dict
    global jira_parent_dict


    logging.basicConfig(level=logging.DEBUG)
    time_start = timer()

    jira_sub_dict = {}
    jira_parent_dict = {}
    tempo_list = []

    # --Tempo url doesn't allow for limiting the fields returned
    tempo_url = 'https://levelsbeyond.atlassian.net/rest/tempo-timesheets/3/worklogs?' + \
                'dateFrom={0}&dateTo={1}&projectKey={2}'
    url = tempo_url.format(fromDate, toDate, projectKey)
    logging.debug('tempo_url: {0}'.format(url))

    if _offline:
        SetMockData()
        # pass  #testing no results, comment the line above
    else:
        r = requests.get(url, auth=GetAuth())
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
                                   'key': entry['issue']['key'],
                                   'customer': None,
                                   'timeSpentSeconds': entry['timeSpentSeconds'],
                                   'issuetype': entry['issue']['issueType']['name'],
                                   'summary': entry['issue']['summary'],
                                   'tempocomment': entry['comment'],
                                   'parentsummary': entry['issue']['summary']})


    time_current = timer()
    logging.debug('Tempo done - start:{0}, current:{1}, duration:{2}'.format(time_start, time_current,
                                                                             time_current - time_start))

    #========= the sequence of events is very important in this section
    # it's balancing loading sub-tasks, and stories while loading the parent stories for the sub-tasks
    
    # build sub list
    keylistsub = []
    for entry in tempo_list:
        if entry['issuetype'] == "Sub-task":
            keylistsub.append(entry['key'])

    if len(keylistsub) > 0:
        uniquelist = set(keylistsub)
        keystring = ",".join(uniquelist)
        LoadJiraSub(keystring)


    keylistparent = []
    tempo_list = tempo_list
    for entry in tempo_list:
        if entry['issuetype'] == 'Sub-task':
            entry['parentkey'] = jira_sub_dict[entry['key']]['parentkey']
            keylistparent.append(jira_sub_dict[entry['key']]['parentkey'])  #add parents to non sub-task list


    tempo_list = tempo_list
    for entry in tempo_list:
        if entry['issuetype'] != "Sub-task":
            keylistparent.append(entry['key'])  #add all non sub-tasks to list

    if len(keylistparent) > 0:
        uniquelist = set(keylistparent)
        keystring = ",".join(uniquelist)
        LoadJiraParent(keystring)


    tempo_list = tempo_list
    total_hours = 0
    hours_billable = 0
    hours_nonbillable = 0
    for entry in tempo_list:
        # sum hours per JIRA ticket and total
        total_hours += entry['timeSpentSeconds']
        # add up Tempo time for each Jira ticket
        jira_parent_dict[entry['parentkey']]['totaltimeSpentSeconds'] += entry['timeSpentSeconds']

        if jira_parent_dict[entry['parentkey']]['billstate'] in ('Billable','Billable but Not Billed'):
            hours_billable += entry['timeSpentSeconds']
        else:
            hours_nonbillable += entry['timeSpentSeconds']

    for entry in tempo_list:
        if entry['issuetype'] == "Sub-task":
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


    return [jira_parent_list, tempo_list,  hours_billable, hours_nonbillable]


def GetAuth():
    return ('rjohnson', 'Miter9le')


def SetMockData():
    global tempo_list
    global jira_sub_dict
    global jira_parent_dict

    tempo_list.append(
        {'id': 122540, 'parentkey': 'WFD-3350', 'key': 'WFD-3419', 'customer': 'AFHV', 'timeSpentSeconds': 5400,
         'issuetype': 'Sub-task', 'summary': 'Testing',
         'tempocomment': 'Changed convert video to a subflow due to finding out AFV is on AWS. Finished testing.',
         'parentsummary': 'Testing'})
    tempo_list.append(
        {'id': 122541, 'parentkey': 'WFD-3350', 'key': 'WFD-3421', 'customer': 'AFHV', 'timeSpentSeconds': 1800,
         'issuetype': 'Sub-task', 'summary': 'Create README', 'tempocomment': 'Created README and uploaded to Github',
         'parentsummary': 'Create README'})
    tempo_list.append(
        {'id': 123144, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 7200,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'WFD - add new Jira fields RE Version and RE Type', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123145, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 5400,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'WFD - cycle sprints, stats, build board', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123148, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'WFD - team hours with Customer to Korinne', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123149, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'WFD - AFHV POC discussion', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123152, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD - gitprime stats',
         'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 122661, 'parentkey': 'WFD-2859', 'key': 'WFD-3474', 'customer': 'Spotify', 'timeSpentSeconds': 2040,
         'issuetype': 'Sub-task', 'summary': 'Look over workflows', 'tempocomment': 'Done.',
         'parentsummary': 'Look over workflows'})
    tempo_list.append(
        {'id': 122662, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 2700,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Scrum and scoping',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122795, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Kafka meeting',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122666, 'parentkey': 'WFD-3347', 'key': 'WFD-3347', 'customer': 'Amazon', 'timeSpentSeconds': 13380,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-3193 | Create Movie Placeholders',
         'tempocomment': 'Made changes to the workflow and ran a test of the new requirements. Analyzed result and emailed the client to ask them to take a look/run some tests and then have a call to hash out what I hope to be the tail end of this request',
         'parentsummary': 'UAT | WFD-3193 | Create Movie Placeholders'})
    tempo_list.append(
        {'id': 122814, 'parentkey': 'WFD-3352', 'key': 'WFD-3408', 'customer': 'AFHV', 'timeSpentSeconds': 14400,
         'issuetype': 'Sub-task', 'summary': '(6) Testing',
         'tempocomment': 'Tested ALMOST all of the workflow successfully, in context of the app. However, one call (the call to start the muscially app) is not working for me still. ',
         'parentsummary': '(6) Testing'})
    tempo_list.append(
        {'id': 122700, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 2700,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD Standup/Grooming',
         'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 122782, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 900,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Standup',
         'parentsummary': 'Meetings'})
    tempo_list.append({'id': 122783, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation',
                       'tempocomment': 'Grooming', 'parentsummary': 'Estimation'})
    tempo_list.append(
        {'id': 122887, 'parentkey': 'WFD-3351', 'key': 'WFD-3413', 'customer': 'AFHV', 'timeSpentSeconds': 2700,
         'issuetype': 'Sub-task', 'summary': 'Testing Workflow',
         'tempocomment': 'discussing how to proceed with AFV ReAndroid project', 'parentsummary': 'Testing Workflow'})
    tempo_list.append(
        {'id': 122888, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 900,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'time tracking',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122784, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Meet with Mark on WF Team plan',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122889, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 900,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scrum',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122785, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Learning about Kafka',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122786, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'AFV Android POC talk',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122890, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 2700,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scoping',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122891, 'parentkey': 'WFD-3310', 'key': 'WFD-3310', 'customer': 'Spotify', 'timeSpentSeconds': 2700,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-3104  Prepare Assets for CMS',
         'tempocomment': 'WFD-3310 checking if Spotify Vantage templates were ready. They weren’t',
         'parentsummary': 'UAT | WFD-3104  Prepare Assets for CMS'})
    tempo_list.append(
        {'id': 122892, 'parentkey': 'WFD-3432', 'key': 'WFD-3432', 'customer': 'NFL', 'timeSpentSeconds': 3600,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement',
         'tempocomment': 'communicating with NFL about Vodzilla UAT. Getting setup to continue working on it',
         'parentsummary': 'UAT | WFD-2275 NFL Vodzilla Replacement'})
    tempo_list.append(
        {'id': 122893, 'parentkey': 'WFD-3432', 'key': 'WFD-3432', 'customer': 'NFL', 'timeSpentSeconds': 15300,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement',
         'tempocomment': 'Testing the workflows to get success when handling files on their system and interfacing with elemental live',
         'parentsummary': 'UAT | WFD-2275 NFL Vodzilla Replacement'})
    tempo_list.append(
        {'id': 122797, 'parentkey': 'WFD-3352', 'key': 'WFD-3352', 'customer': 'AFHV', 'timeSpentSeconds': 7200,
         'issuetype': 'Story', 'summary': 'SCOPE(23) - musical.ly - Social Network Distribution',
         'tempocomment': 'Helping move this along as best as possible',
         'parentsummary': 'SCOPE(23) - musical.ly - Social Network Distribution'})
    tempo_list.append(
        {'id': 122798, 'parentkey': 'WFD-3351', 'key': 'WFD-3351', 'customer': 'AFHV', 'timeSpentSeconds': 1800,
         'issuetype': 'Story', 'summary': 'SCOPE(23) - Instagram - Social Network Distribution',
         'tempocomment': 'Helping move this along as best as possible',
         'parentsummary': 'SCOPE(23) - Instagram - Social Network Distribution'})
    tempo_list.append(
        {'id': 122799, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'Catching up after vacation', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 122800, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'Looking into open source csv libraries to see if there is a better way to parse csvs in Java for our workflow functions',
         'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 122801, 'parentkey': 'WFD-2859', 'key': 'WFD-2859', 'customer': 'Spotify', 'timeSpentSeconds': 900,
         'issuetype': 'Story', 'summary': 'SCOPE(12) - Share Assets with NY', 'tempocomment': 'Help',
         'parentsummary': 'SCOPE(12) - Share Assets with NY'})
    tempo_list.append(
        {'id': 122802, 'parentkey': 'WFD-3086', 'key': 'WFD-3439', 'customer': 'Herbalife', 'timeSpentSeconds': 1740,
         'issuetype': 'Sub-task', 'summary': '(.5) Review Workflows', 'tempocomment': 'Done',
         'parentsummary': '(.5) Review Workflows'})
    tempo_list.append(
        {'id': 122806, 'parentkey': 'WFD-3086', 'key': 'WFD-3443', 'customer': 'Herbalife', 'timeSpentSeconds': 4740,
         'issuetype': 'Sub-task', 'summary': '(1) Make change to use proxy to regen proxy', 'tempocomment': 'Done',
         'parentsummary': '(1) Make change to use proxy to regen proxy'})
    tempo_list.append(
        {'id': 122807, 'parentkey': 'WFD-2859', 'key': 'WFD-3004', 'customer': 'Spotify', 'timeSpentSeconds': 7500,
         'issuetype': 'Sub-task', 'summary': 'bulk transfer collection assets',
         'tempocomment': 'Updated code for Aspera information. Ran some tests but was unable to successfully transer. Seems to be due to bad credentials from client.',
         'parentsummary': 'bulk transfer collection assets'})
    tempo_list.append(
        {'id': 122808, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 600,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Standup',
         'parentsummary': 'Meetings'})
    tempo_list.append({'id': 122809, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 2100, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation',
                       'tempocomment': 'Scoping', 'parentsummary': 'Estimation'})
    tempo_list.append({'id': 122810, 'parentkey': 'WFD-2024', 'key': 'WFD-2024', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Other',
                       'tempocomment': 'Testing what I thought was a query step bug', 'parentsummary': 'Other'})
    tempo_list.append(
        {'id': 122811, 'parentkey': 'WFD-3352', 'key': 'WFD-3352', 'customer': 'AFHV', 'timeSpentSeconds': 1800,
         'issuetype': 'Story', 'summary': 'SCOPE(23) - musical.ly - Social Network Distribution',
         'tempocomment': 'Helping Alex with some Groovy step logic.',
         'parentsummary': 'SCOPE(23) - musical.ly - Social Network Distribution'})
    tempo_list.append(
        {'id': 122843, 'parentkey': 'WFD-3352', 'key': 'WFD-3408', 'customer': 'AFHV', 'timeSpentSeconds': 7440,
         'issuetype': 'Sub-task', 'summary': '(6) Testing',
         'tempocomment': 'Completed testing, everything is looking good, Lior confirmed',
         'parentsummary': '(6) Testing'})
    tempo_list.append(
        {'id': 123132, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 2700,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD standup/grooming',
         'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123157, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD - UAT review',
         'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123159, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD - Internal training',
         'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123163, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'WFD - updating UAT tickets with SA and links to story',
         'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 122844, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 900,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Standup',
         'parentsummary': 'Meetings'})
    tempo_list.append({'id': 122845, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation',
                       'tempocomment': 'Grooming', 'parentsummary': 'Estimation'})
    tempo_list.append(
        {'id': 122846, 'parentkey': 'WFD-3478', 'key': 'WFD-3478', 'customer': 'WB Archive', 'timeSpentSeconds': 3600,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-3231 | Duplicate Asset Report WB',
         'tempocomment': "Talked with Lior and completed pushing the workflow to the new branch I created on the levels beyond repo. Didn't realize I hadn't pushed it there and it took some time to sort it out",
         'parentsummary': 'UAT | WFD-3231 | Duplicate Asset Report WB'})
    tempo_list.append(
        {'id': 122847, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings',
         'tempocomment': 'scrum and scope and task up new work', 'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122864, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Workflow Team Direction',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122876, 'parentkey': 'WFD-3486', 'key': 'WFD-3486', 'customer': 'WB Archive', 'timeSpentSeconds': 10800,
         'issuetype': 'Story', 'summary': 'Resume Retrieve/Export Testing', 'tempocomment': 'Modifications and Testing',
         'parentsummary': 'Resume Retrieve/Export Testing'})
    tempo_list.append(
        {'id': 122877, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'Discussing Kanban transitioning topics', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 122878, 'parentkey': 'WFD-2739', 'key': 'WFD-2739', 'customer': 'WBITV', 'timeSpentSeconds': 5520,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2372 | Updates to OAP',
         'tempocomment': 'Completed dev for what will hopefully prove to be the end of this ticket. Will wait for client confirmation and will close the request out upon once I get positive feedback from the client',
         'parentsummary': 'UAT | WFD-2372 | Updates to OAP'})
    tempo_list.append(
        {'id': 122904, 'parentkey': 'WFD-2859', 'key': 'WFD-3004', 'customer': 'Spotify', 'timeSpentSeconds': 8880,
         'issuetype': 'Sub-task', 'summary': 'bulk transfer collection assets',
         'tempocomment': 'Did more testing with aspera on Spotifys system. Still running into issues. Need to get on a call with client.',
         'parentsummary': 'bulk transfer collection assets'})
    tempo_list.append(
        {'id': 122879, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 5100,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Internal Workflow meeting',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122885, 'parentkey': 'WFD-3377', 'key': 'WFD-3480', 'customer': 'AFHV', 'timeSpentSeconds': 5400,
         'issuetype': 'Sub-task', 'summary': '(1.5) Develop Parent Workflows',
         'tempocomment': 'Dev-ed parent workflows and started subflow',
         'parentsummary': '(1.5) Develop Parent Workflows'})
    tempo_list.append(
        {'id': 122880, 'parentkey': 'WFD-3377', 'key': 'WFD-3377', 'customer': 'AFHV', 'timeSpentSeconds': 1800,
         'issuetype': 'Story', 'summary': 'SCOPE(12) - mRSS Single Distribution ',
         'tempocomment': 'Help with Spring Expressions', 'parentsummary': 'SCOPE(12) - mRSS Single Distribution '})
    tempo_list.append(
        {'id': 122881, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support',
         'tempocomment': 'Help with Hallmark Delete issue', 'parentsummary': 'Workflow Support'})
    tempo_list.append(
        {'id': 122894, 'parentkey': 'WFD-3432', 'key': 'WFD-3432', 'customer': 'NFL', 'timeSpentSeconds': 4500,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement',
         'tempocomment': 'NFL UAT- testing xml report delivery',
         'parentsummary': 'UAT | WFD-2275 NFL Vodzilla Replacement'})
    tempo_list.append(
        {'id': 122895, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 900,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scrum',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122896, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scoping',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122897, 'parentkey': 'WFD-3432', 'key': 'WFD-3432', 'customer': 'NFL', 'timeSpentSeconds': 900,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement',
         'tempocomment': 'NFL UAT working on ftp step', 'parentsummary': 'UAT | WFD-2275 NFL Vodzilla Replacement'})
    tempo_list.append(
        {'id': 122898, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings',
         'tempocomment': 'meeting to discuss future of workflow team', 'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122899, 'parentkey': 'WFD-3432', 'key': 'WFD-3432', 'customer': 'NFL', 'timeSpentSeconds': 900,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement',
         'tempocomment': 'NFL UAT - figured out ftp isnt right to connect to NFL',
         'parentsummary': 'UAT | WFD-2275 NFL Vodzilla Replacement'})
    tempo_list.append(
        {'id': 122900, 'parentkey': 'WFD-3432', 'key': 'WFD-3432', 'customer': 'NFL', 'timeSpentSeconds': 3600,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement',
         'tempocomment': 'NFL UAT - discovered the Vitac uses FTPS and the FTPStep doesn’t support that. Using groovy to get around this',
         'parentsummary': 'UAT | WFD-2275 NFL Vodzilla Replacement'})
    tempo_list.append(
        {'id': 122901, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'customer': 'Levels Beyond', 'timeSpentSeconds': 7200,
         'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support',
         'tempocomment': 'Robin - hallmark weird issue that shouldn’t happen\nwriting test workflow to confirm issue on Hallmark system',
         'parentsummary': 'Workflow Support'})
    tempo_list.append(
        {'id': 122902, 'parentkey': 'WFD-3432', 'key': 'WFD-3432', 'customer': 'NFL', 'timeSpentSeconds': 5400,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement',
         'tempocomment': 'Failed to get groovy working for FTPS. Trying curl now. Curl works on Command Line but it is failing in workflow. ',
         'parentsummary': 'UAT | WFD-2275 NFL Vodzilla Replacement'})
    tempo_list.append(
        {'id': 122903, 'parentkey': 'WFD-3086', 'key': 'WFD-3444', 'customer': 'Herbalife', 'timeSpentSeconds': 4380,
         'issuetype': 'Sub-task', 'summary': '(1.5) Test',
         'tempocomment': 'Tested on Herbalifes dev server. Testing was slow due to TV', 'parentsummary': '(1.5) Test'})
    tempo_list.append(
        {'id': 122905, 'parentkey': 'WFD-3314', 'key': 'WFD-3314', 'customer': 'Hallmark', 'timeSpentSeconds': 3000,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-3143 | Ingest Bulk Metadata From CSV',
         'tempocomment': 'Spent more time looking into issues for client. Again it was user error and issues with Microsoft Excel auto formatting fields.',
         'parentsummary': 'UAT | WFD-3143 | Ingest Bulk Metadata From CSV'})
    tempo_list.append(
        {'id': 122906, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1200,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings',
         'tempocomment': 'Meeting with team about future work.', 'parentsummary': 'Meetings'})
    tempo_list.append({'id': 122907, 'parentkey': 'WFD-2024', 'key': 'WFD-2024', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 1200, 'issuetype': 'Time Tracking Task', 'summary': 'Other',
                       'tempocomment': 'Emails/communication', 'parentsummary': 'Other'})
    tempo_list.append(
        {'id': 122917, 'parentkey': 'WFD-2739', 'key': 'WFD-2739', 'customer': 'WBITV', 'timeSpentSeconds': 4500,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2372 | Updates to OAP',
         'tempocomment': 'Responded to a failed run of the Ingest to OAP workflow which was caused by what should have been a known error case. Responded to Brad. Additionally, it appears that WBITVs filesystem may have come unmounted on Dev. I was unable to test/prove my statement to Brad because of this. I have suggested that support be notified --- responded to several questions throughout the day',
         'parentsummary': 'UAT | WFD-2372 | Updates to OAP'})
    tempo_list.append(
        {'id': 123007, 'parentkey': 'WFD-3377', 'key': 'WFD-3481', 'customer': 'AFHV', 'timeSpentSeconds': 18900,
         'issuetype': 'Sub-task', 'summary': '(3) Get contents of XML and Replace with reachengine variables',
         'tempocomment': 'Had to work with lior back and forth a lot regarding what the expectations were and to get the acs clearly defined. Additionally, parsing the thumbnail timecode was a little bit more involved than originally anticipated',
         'parentsummary': '(3) Get contents of XML and Replace with reachengine variables'})
    tempo_list.append(
        {'id': 123006, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scrum n scoping n tasking',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 123133, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 2700,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD standup/grooming',
         'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123008, 'parentkey': 'WFD-3378', 'key': 'WFD-3484', 'customer': 'AFHV', 'timeSpentSeconds': 4320,
         'issuetype': 'Sub-task', 'summary': '(1) Dev',
         'tempocomment': 'decided that the best route to take with this was to combine the processes from 3377 and 3378, dev completed, will test together',
         'parentsummary': '(1) Dev'})
    tempo_list.append(
        {'id': 123151, 'parentkey': 'WFD-3351', 'key': 'WFD-3413', 'customer': 'AFHV', 'timeSpentSeconds': 5400,
         'issuetype': 'Sub-task', 'summary': 'Testing Workflow', 'tempocomment': 'WFD-3413 Instagram testing',
         'parentsummary': 'Testing Workflow'})
    tempo_list.append(
        {'id': 123156, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scoping',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 123158, 'parentkey': 'WFD-3351', 'key': 'WFD-3413', 'customer': 'AFHV', 'timeSpentSeconds': 5400,
         'issuetype': 'Sub-task', 'summary': 'Testing Workflow', 'tempocomment': 'WFD-3413 Instagram testing',
         'parentsummary': 'Testing Workflow'})
    tempo_list.append(
        {'id': 123160, 'parentkey': 'WFD-3351', 'key': 'WFD-3413', 'customer': 'AFHV', 'timeSpentSeconds': 1800,
         'issuetype': 'Sub-task', 'summary': 'Testing Workflow', 'tempocomment': 'WFD-3413 Instagram testing',
         'parentsummary': 'Testing Workflow'})
    tempo_list.append(
        {'id': 123162, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'customer': 'Levels Beyond', 'timeSpentSeconds': 4500,
         'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support', 'tempocomment': 'Robin',
         'parentsummary': 'Workflow Support'})
    tempo_list.append(
        {'id': 123165, 'parentkey': 'WFD-3351', 'key': 'WFD-3413', 'customer': 'AFHV', 'timeSpentSeconds': 3600,
         'issuetype': 'Sub-task', 'summary': 'Testing Workflow',
         'tempocomment': "fixing vm - needed to test something out on my vm. It wouldn't start. ",
         'parentsummary': 'Testing Workflow'})
    tempo_list.append(
        {'id': 123167, 'parentkey': 'WFD-3351', 'key': 'WFD-3413', 'customer': 'AFHV', 'timeSpentSeconds': 4500,
         'issuetype': 'Sub-task', 'summary': 'Testing Workflow', 'tempocomment': 'WFD-3413 testing instagram',
         'parentsummary': 'Testing Workflow'})
    tempo_list.append(
        {'id': 123169, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 5400,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'WFD - prep for process flow change meeting', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123171, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'WFD - process change meeting with Korinne', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123173, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 5400,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'WFD - start new Kanban board POC', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123023, 'parentkey': 'WFD-2898', 'key': 'WFD-2898', 'customer': None, 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings (billable)',
         'tempocomment': 'AFV - SPIKE - Youtube and Facebook analytics', 'parentsummary': 'Meetings (billable)'})
    tempo_list.append(
        {'id': 122937, 'parentkey': 'WFD-3086', 'key': 'WFD-3444', 'customer': 'Herbalife', 'timeSpentSeconds': 1500,
         'issuetype': 'Sub-task', 'summary': '(1.5) Test', 'tempocomment': 'Finished testing. Pushed to Github',
         'parentsummary': '(1.5) Test'})
    tempo_list.append(
        {'id': 122932, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'workflow testing meeting',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122933, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 2700,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Leads Meeting',
         'parentsummary': 'Meetings'})
    tempo_list.append({'id': 122934, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 2700, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation',
                       'tempocomment': 'Grooming', 'parentsummary': 'Estimation'})
    tempo_list.append(
        {'id': 122982, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'engineering team discussion',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122979, 'parentkey': 'WFD-2859', 'key': 'WFD-3004', 'customer': 'Spotify', 'timeSpentSeconds': 7140,
         'issuetype': 'Sub-task', 'summary': 'bulk transfer collection assets',
         'tempocomment': "Got on a call with Spotify. Still couldn't get the API call working. Talked to Bill for a little help.",
         'parentsummary': 'bulk transfer collection assets'})
    tempo_list.append(
        {'id': 122952, 'parentkey': 'WFD-3491', 'key': 'WFD-3491', 'customer': 'WBITV', 'timeSpentSeconds': 900,
         'issuetype': 'Story',
         'summary': 'SCOPE(9) - Update WBITV Workflows for 2.X - Fixes, query WBITV, WBITV request',
         'tempocomment': 'Planning',
         'parentsummary': 'SCOPE(9) - Update WBITV Workflows for 2.X - Fixes, query WBITV, WBITV request'})
    tempo_list.append(
        {'id': 122953, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Kanban official kickoff meeting',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 122955, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 4500,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'Team discussion with Ron.', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 122957, 'parentkey': 'WFD-3377', 'key': 'WFD-3377', 'customer': 'AFHV', 'timeSpentSeconds': 1800,
         'issuetype': 'Story', 'summary': 'SCOPE(12) - mRSS Single Distribution ', 'tempocomment': 'Help',
         'parentsummary': 'SCOPE(12) - mRSS Single Distribution '})
    tempo_list.append(
        {'id': 122958, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'various interruptions',
         'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 122960, 'parentkey': 'WFD-2859', 'key': 'WFD-2859', 'customer': 'Spotify', 'timeSpentSeconds': 1800,
         'issuetype': 'Story', 'summary': 'SCOPE(12) - Share Assets with NY', 'tempocomment': 'Help',
         'parentsummary': 'SCOPE(12) - Share Assets with NY'})
    tempo_list.append(
        {'id': 122990, 'parentkey': 'WFD-3383', 'key': 'WFD-3518', 'customer': 'JC Penney', 'timeSpentSeconds': 6420,
         'issuetype': 'Sub-task', 'summary': 'Subtract start time from given time code',
         'tempocomment': 'Started working on calculating an offset timecode.',
         'parentsummary': 'Subtract start time from given time code'})
    tempo_list.append(
        {'id': 123079, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 900,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Standup',
         'parentsummary': 'Meetings'})
    tempo_list.append({'id': 123080, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 2700, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation',
                       'tempocomment': 'Scoping', 'parentsummary': 'Estimation'})
    tempo_list.append({'id': 123081, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 3600, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation',
                       'tempocomment': 'Planning JCP and other tickets from scoping', 'parentsummary': 'Estimation'})
    tempo_list.append(
        {'id': 123082, 'parentkey': 'WFD-2024', 'key': 'WFD-2024', 'customer': 'Levels Beyond', 'timeSpentSeconds': 900,
         'issuetype': 'Time Tracking Task', 'summary': 'Other', 'tempocomment': 'Looking over native connectors sheet',
         'parentsummary': 'Other'})
    tempo_list.append({'id': 123083, 'parentkey': 'WFD-2024', 'key': 'WFD-2024', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 2400, 'issuetype': 'Time Tracking Task', 'summary': 'Other',
                       'tempocomment': 'Updating UAT tickets', 'parentsummary': 'Other'})
    tempo_list.append(
        {'id': 123084, 'parentkey': 'WFD-2898', 'key': 'WFD-2898', 'customer': None, 'timeSpentSeconds': 1200,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings (billable)',
         'tempocomment': 'AFV - Talking to Lior about Facebook and Twitter tickets',
         'parentsummary': 'Meetings (billable)'})
    tempo_list.append(
        {'id': 123085, 'parentkey': 'WFD-2024', 'key': 'WFD-2024', 'customer': 'Levels Beyond', 'timeSpentSeconds': 900,
         'issuetype': 'Time Tracking Task', 'summary': 'Other', 'tempocomment': 'Emails/communication',
         'parentsummary': 'Other'})
    tempo_list.append(
        {'id': 123134, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 2700,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD standup/grooming',
         'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123024, 'parentkey': 'WFD-3377', 'key': 'WFD-3482', 'customer': 'AFHV', 'timeSpentSeconds': 11040,
         'issuetype': 'Sub-task', 'summary': '(1.5) Transcode, Thumbnail, and Deliver XML',
         'tempocomment': 'Had to redevelop some aspects of the workflow after slack conversations with Lior. Also, I neglected to take into account that the client system will be running in aws, so had to make some additional changes. ',
         'parentsummary': '(1.5) Transcode, Thumbnail, and Deliver XML'})
    tempo_list.append(
        {'id': 123174, 'parentkey': 'WFD-3300', 'key': 'WFD-3300', 'customer': 'Hallmark', 'timeSpentSeconds': 4500,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-3142 Export Metadata From Search Results',
         'tempocomment': 'testing hallmark export',
         'parentsummary': 'UAT | WFD-3142 Export Metadata From Search Results'})
    tempo_list.append(
        {'id': 123176, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 900,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scrum',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 123177, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scoping',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 123178, 'parentkey': 'WFD-3351', 'key': 'WFD-3413', 'customer': 'AFHV', 'timeSpentSeconds': 3600,
         'issuetype': 'Sub-task', 'summary': 'Testing Workflow', 'tempocomment': 'WFD-3413 testing instagram',
         'parentsummary': 'Testing Workflow'})
    tempo_list.append(
        {'id': 123180, 'parentkey': 'WFD-3432', 'key': 'WFD-3432', 'customer': 'NFL', 'timeSpentSeconds': 900,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement', 'tempocomment': 'nfl response',
         'parentsummary': 'UAT | WFD-2275 NFL Vodzilla Replacement'})
    tempo_list.append(
        {'id': 123182, 'parentkey': 'WFD-3351', 'key': 'WFD-3413', 'customer': 'AFHV', 'timeSpentSeconds': 900,
         'issuetype': 'Sub-task', 'summary': 'Testing Workflow', 'tempocomment': 'testing instagram',
         'parentsummary': 'Testing Workflow'})
    tempo_list.append(
        {'id': 123184, 'parentkey': 'WFD-3351', 'key': 'WFD-3413', 'customer': 'AFHV', 'timeSpentSeconds': 2700,
         'issuetype': 'Sub-task', 'summary': 'Testing Workflow', 'tempocomment': 'WFD-3413 testing instagram',
         'parentsummary': 'Testing Workflow'})
    tempo_list.append(
        {'id': 123185, 'parentkey': 'WFD-3351', 'key': 'WFD-3414', 'customer': 'AFHV', 'timeSpentSeconds': 900,
         'issuetype': 'Sub-task', 'summary': 'Wind Down', 'tempocomment': 'WFD-3414 wrote the readme',
         'parentsummary': 'Wind Down'})
    tempo_list.append(
        {'id': 123186, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': "WFD - add status' for new Kanban fl", 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123187, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support', 'tempocomment': 'Robin',
         'parentsummary': 'Workflow Support'})
    tempo_list.append(
        {'id': 123188, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'customer': 'Levels Beyond', 'timeSpentSeconds': 1800,
         'issuetype': 'Time Tracking Task', 'summary': 'Project Management',
         'tempocomment': 'WFD - review AFHV with Amy and Korinne', 'parentsummary': 'Project Management'})
    tempo_list.append(
        {'id': 123189, 'parentkey': 'WFD-3351', 'key': 'WFD-3413', 'customer': 'AFHV', 'timeSpentSeconds': 1800,
         'issuetype': 'Sub-task', 'summary': 'Testing Workflow',
         'tempocomment': 'WFD-3413 testing and discussing what to do with the project.',
         'parentsummary': 'Testing Workflow'})
    tempo_list.append(
        {'id': 123190, 'parentkey': 'WFD-3432', 'key': 'WFD-3432', 'customer': 'NFL', 'timeSpentSeconds': 1800,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement',
         'tempocomment': 'Modifying the FTP call to get it to work.',
         'parentsummary': 'UAT | WFD-2275 NFL Vodzilla Replacement'})
    tempo_list.append(
        {'id': 123191, 'parentkey': 'WFD-3432', 'key': 'WFD-3432', 'customer': 'NFL', 'timeSpentSeconds': 7200,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement',
         'tempocomment': 'Got the FTP call working by taking the curl command and running it from groovy.',
         'parentsummary': 'UAT | WFD-2275 NFL Vodzilla Replacement'})
    tempo_list.append(
        {'id': 123192, 'parentkey': 'WFD-3310', 'key': 'WFD-3310', 'customer': 'Spotify', 'timeSpentSeconds': 900,
         'issuetype': 'UAT', 'summary': 'UAT | WFD-3104  Prepare Assets for CMS',
         'tempocomment': 'call with Spotify to test out the workflow with Nick Hybl.',
         'parentsummary': 'UAT | WFD-3104  Prepare Assets for CMS'})
    tempo_list.append(
        {'id': 123021, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 3600,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scrum n scope',
         'parentsummary': 'Meetings'})
    tempo_list.append(
        {'id': 123030, 'parentkey': 'WFD-3383', 'key': 'WFD-3518', 'customer': 'JC Penney', 'timeSpentSeconds': 3360,
         'issuetype': 'Sub-task', 'summary': 'Subtract start time from given time code',
         'tempocomment': 'Done. Had to put a bunch of calculations into the workflow to get the offset from 0 in a timecode format.',
         'parentsummary': 'Subtract start time from given time code'})
    tempo_list.append(
        {'id': 123205, 'parentkey': 'WFD-3377', 'key': 'WFD-3483', 'customer': 'AFHV', 'timeSpentSeconds': 16680,
         'issuetype': 'Sub-task', 'summary': '(4) Test',
         'tempocomment': 'Tested, ran into some issues, will finish testing tomorrow', 'parentsummary': '(4) Test'})
    tempo_list.append(
        {'id': 123033, 'parentkey': 'WFD-3383', 'key': 'WFD-3519', 'customer': 'JC Penney', 'timeSpentSeconds': 3600,
         'issuetype': 'Sub-task', 'summary': 'Testing',
         'tempocomment': 'Did some testing and bug fixing locally. Timecode seems to be calculating correctly.',
         'parentsummary': 'Testing'})
    tempo_list.append(
        {'id': 123065, 'parentkey': 'WFD-3471', 'key': 'WFD-3525', 'customer': 'Hallmark', 'timeSpentSeconds': 3480,
         'issuetype': 'Sub-task', 'summary': 'Planning',
         'tempocomment': 'Done. Had some issues with merge conflicts when trying to merge to local repo. Planning took a little longer than expected.',
         'parentsummary': 'Planning'})
    tempo_list.append(
        {'id': 123066, 'parentkey': 'WFD-3471', 'key': 'WFD-3526', 'customer': 'Hallmark', 'timeSpentSeconds': 1380,
         'issuetype': 'Sub-task', 'summary': 'Update asset name for timeline and non-timeline', 'tempocomment': 'Done',
         'parentsummary': 'Update asset name for timeline and non-timeline'})
    tempo_list.append(
        {'id': 123070, 'parentkey': 'WFD-3471', 'key': 'WFD-3527', 'customer': 'Hallmark', 'timeSpentSeconds': 1740,
         'issuetype': 'Sub-task', 'summary': 'Verify collections and categories',
         'tempocomment': 'Added logic for verifying categories', 'parentsummary': 'Verify collections and categories'})
    tempo_list.append(
        {'id': 123071, 'parentkey': 'WFD-3471', 'key': 'WFD-3527', 'customer': 'Hallmark', 'timeSpentSeconds': 1200,
         'issuetype': 'Sub-task', 'summary': 'Verify collections and categories', 'tempocomment': 'Done.',
         'parentsummary': 'Verify collections and categories'})
    tempo_list.append(
        {'id': 123072, 'parentkey': 'WFD-3471', 'key': 'WFD-3528', 'customer': 'Hallmark', 'timeSpentSeconds': 1800,
         'issuetype': 'Sub-task', 'summary': 'Add/remove categories from asset', 'tempocomment': 'Done.',
         'parentsummary': 'Add/remove categories from asset'})
    tempo_list.append(
        {'id': 123074, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'customer': 'Levels Beyond', 'timeSpentSeconds': 900,
         'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Standup',
         'parentsummary': 'Meetings'})
    tempo_list.append({'id': 123075, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation',
                       'tempocomment': 'Scoping', 'parentsummary': 'Estimation'})
    tempo_list.append({'id': 123076, 'parentkey': 'WFD-2024', 'key': 'WFD-2024', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 2700, 'issuetype': 'Time Tracking Task', 'summary': 'Other',
                       'tempocomment': 'Update/closing UAT tickets', 'parentsummary': 'Other'})
    tempo_list.append(
        {'id': 123077, 'parentkey': 'WFD-3377', 'key': 'WFD-3377', 'customer': 'AFHV', 'timeSpentSeconds': 1800,
         'issuetype': 'Story', 'summary': 'SCOPE(12) - mRSS Single Distribution ', 'tempocomment': 'Helping Alex',
         'parentsummary': 'SCOPE(12) - mRSS Single Distribution '})
    tempo_list.append({'id': 123078, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'customer': 'Levels Beyond',
                       'timeSpentSeconds': 5400, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation',
                       'tempocomment': 'Planning Hallmark ticket and talking to Matt about said ticket.',
                       'parentsummary': 'Estimation'})
    tempo_list.append(
        {'id': 123203, 'parentkey': 'WFD-3471', 'key': 'WFD-3529', 'customer': 'Hallmark', 'timeSpentSeconds': 7080,
         'issuetype': 'Sub-task', 'summary': 'Add/remove collections from asset', 'tempocomment': 'Done.',
         'parentsummary': 'Add/remove collections from asset'})
    {'WFD-3529': {'key': 'WFD-3529', 'parentkey': 'WFD-3471'}, 'WFD-3528': {'key': 'WFD-3528', 'parentkey': 'WFD-3471'},
     'WFD-3527': {'key': 'WFD-3527', 'parentkey': 'WFD-3471'}, 'WFD-3526': {'key': 'WFD-3526', 'parentkey': 'WFD-3471'},
     'WFD-3525': {'key': 'WFD-3525', 'parentkey': 'WFD-3471'}, 'WFD-3519': {'key': 'WFD-3519', 'parentkey': 'WFD-3383'},
     'WFD-3518': {'key': 'WFD-3518', 'parentkey': 'WFD-3383'}, 'WFD-3484': {'key': 'WFD-3484', 'parentkey': 'WFD-3378'},
     'WFD-3483': {'key': 'WFD-3483', 'parentkey': 'WFD-3377'}, 'WFD-3482': {'key': 'WFD-3482', 'parentkey': 'WFD-3377'},
     'WFD-3481': {'key': 'WFD-3481', 'parentkey': 'WFD-3377'}, 'WFD-3480': {'key': 'WFD-3480', 'parentkey': 'WFD-3377'},
     'WFD-3474': {'key': 'WFD-3474', 'parentkey': 'WFD-2859'}, 'WFD-3444': {'key': 'WFD-3444', 'parentkey': 'WFD-3086'},
     'WFD-3443': {'key': 'WFD-3443', 'parentkey': 'WFD-3086'}, 'WFD-3439': {'key': 'WFD-3439', 'parentkey': 'WFD-3086'},
     'WFD-3421': {'key': 'WFD-3421', 'parentkey': 'WFD-3350'}, 'WFD-3419': {'key': 'WFD-3419', 'parentkey': 'WFD-3350'},
     'WFD-3414': {'key': 'WFD-3414', 'parentkey': 'WFD-3351'}, 'WFD-3413': {'key': 'WFD-3413', 'parentkey': 'WFD-3351'},
     'WFD-3408': {'key': 'WFD-3408', 'parentkey': 'WFD-3352'}, 'WFD-3004': {'key': 'WFD-3004', 'parentkey': 'WFD-2859'}}
    jira_sub_dict['WFD-3529'] = {'key': 'WFD-3529', 'parentkey': 'WFD-3471'}
    jira_sub_dict['WFD-3528'] = {'key': 'WFD-3528', 'parentkey': 'WFD-3471'}
    jira_sub_dict['WFD-3527'] = {'key': 'WFD-3527', 'parentkey': 'WFD-3471'}
    jira_sub_dict['WFD-3526'] = {'key': 'WFD-3526', 'parentkey': 'WFD-3471'}
    jira_sub_dict['WFD-3525'] = {'key': 'WFD-3525', 'parentkey': 'WFD-3471'}
    jira_sub_dict['WFD-3519'] = {'key': 'WFD-3519', 'parentkey': 'WFD-3383'}
    jira_sub_dict['WFD-3518'] = {'key': 'WFD-3518', 'parentkey': 'WFD-3383'}
    jira_sub_dict['WFD-3484'] = {'key': 'WFD-3484', 'parentkey': 'WFD-3378'}
    jira_sub_dict['WFD-3483'] = {'key': 'WFD-3483', 'parentkey': 'WFD-3377'}
    jira_sub_dict['WFD-3482'] = {'key': 'WFD-3482', 'parentkey': 'WFD-3377'}
    jira_sub_dict['WFD-3481'] = {'key': 'WFD-3481', 'parentkey': 'WFD-3377'}
    jira_sub_dict['WFD-3480'] = {'key': 'WFD-3480', 'parentkey': 'WFD-3377'}
    jira_sub_dict['WFD-3474'] = {'key': 'WFD-3474', 'parentkey': 'WFD-2859'}
    jira_sub_dict['WFD-3444'] = {'key': 'WFD-3444', 'parentkey': 'WFD-3086'}
    jira_sub_dict['WFD-3443'] = {'key': 'WFD-3443', 'parentkey': 'WFD-3086'}
    jira_sub_dict['WFD-3439'] = {'key': 'WFD-3439', 'parentkey': 'WFD-3086'}
    jira_sub_dict['WFD-3421'] = {'key': 'WFD-3421', 'parentkey': 'WFD-3350'}
    jira_sub_dict['WFD-3419'] = {'key': 'WFD-3419', 'parentkey': 'WFD-3350'}
    jira_sub_dict['WFD-3414'] = {'key': 'WFD-3414', 'parentkey': 'WFD-3351'}
    jira_sub_dict['WFD-3413'] = {'key': 'WFD-3413', 'parentkey': 'WFD-3351'}
    jira_sub_dict['WFD-3408'] = {'key': 'WFD-3408', 'parentkey': 'WFD-3352'}
    jira_sub_dict['WFD-3004'] = {'key': 'WFD-3004', 'parentkey': 'WFD-2859'}
    jira_parent_dict['WFD-3491'] = {'key': 'WFD-3491', 'customer': 'WBITV', 'totaltimeSpentSeconds': 0,
                                    'summary': 'SCOPE(9) - Update WBITV Workflows for 2.X - Fixes, query WBITV, WBITV request',
                                    'issuetype': 'Story', 'billstate': 'Billable', 'status': 'To Do'}
    jira_parent_dict['WFD-3486'] = {'key': 'WFD-3486', 'customer': 'WB Archive', 'totaltimeSpentSeconds': 0,
                                    'summary': 'Resume Retrieve/Export Testing', 'issuetype': 'Story',
                                    'billstate': None, 'status': 'In Progress'}
    jira_parent_dict['WFD-3478'] = {'key': 'WFD-3478', 'customer': 'WB Archive', 'totaltimeSpentSeconds': 0,
                                    'summary': 'UAT | WFD-3231 | Duplicate Asset Report WB', 'issuetype': 'UAT',
                                    'billstate': None, 'status': 'In Progress'}
    jira_parent_dict['WFD-3471'] = {'key': 'WFD-3471', 'customer': 'Hallmark', 'totaltimeSpentSeconds': 0,
                                    'summary': 'SCOPE(4) - Updates to M(m)etadata ingest workflow',
                                    'issuetype': 'Story', 'billstate': 'Billable', 'status': 'In Progress'}
    jira_parent_dict['WFD-3432'] = {'key': 'WFD-3432', 'customer': 'NFL', 'totaltimeSpentSeconds': 0,
                                    'summary': 'UAT | WFD-2275 NFL Vodzilla Replacement', 'issuetype': 'UAT',
                                    'billstate': 'Billable', 'status': 'In Progress'}
    jira_parent_dict['WFD-3383'] = {'key': 'WFD-3383', 'customer': 'JC Penney', 'totaltimeSpentSeconds': 0,
                                    'summary': 'SCOPE(4) - Export To KeyFrame - fix timecode discrepancies -',
                                    'issuetype': 'Story', 'billstate': 'Billable', 'status': 'In Progress'}
    jira_parent_dict['WFD-3378'] = {'key': 'WFD-3378', 'customer': 'AFHV', 'totaltimeSpentSeconds': 0,
                                    'summary': 'SCOPE(2) - Multi - mRSS Distribution ', 'issuetype': 'Story',
                                    'billstate': 'Billable', 'status': 'In Progress'}
    jira_parent_dict['WFD-3377'] = {'key': 'WFD-3377', 'customer': 'AFHV', 'totaltimeSpentSeconds': 0,
                                    'summary': 'SCOPE(12) - mRSS Single Distribution ', 'issuetype': 'Story',
                                    'billstate': 'Billable', 'status': 'In Progress'}
    jira_parent_dict['WFD-3352'] = {'key': 'WFD-3352', 'customer': 'AFHV', 'totaltimeSpentSeconds': 0,
                                    'summary': 'SCOPE(23) - musical.ly - Social Network Distribution',
                                    'issuetype': 'Story', 'billstate': 'Billable', 'status': 'UAT'}
    jira_parent_dict['WFD-3351'] = {'key': 'WFD-3351', 'customer': 'AFHV', 'totaltimeSpentSeconds': 0,
                                    'summary': 'SCOPE(23) - Instagram - Social Network Distribution',
                                    'issuetype': 'Story', 'billstate': 'Billable', 'status': 'UAT'}
    jira_parent_dict['WFD-3350'] = {'key': 'WFD-3350', 'customer': 'AFHV', 'totaltimeSpentSeconds': 0,
                                    'summary': 'SCOPE(23) - Twitter - Social Network Distribution',
                                    'issuetype': 'Story', 'billstate': 'Billable', 'status': 'UAT'}
    jira_parent_dict['WFD-3347'] = {'key': 'WFD-3347', 'customer': 'Amazon', 'totaltimeSpentSeconds': 0,
                                    'summary': 'UAT | WFD-3193 | Create Movie Placeholders', 'issuetype': 'UAT',
                                    'billstate': 'Billable', 'status': 'In Progress'}
    jira_parent_dict['WFD-3314'] = {'key': 'WFD-3314', 'customer': 'Hallmark', 'totaltimeSpentSeconds': 0,
                                    'summary': 'UAT | WFD-3143 | Ingest Bulk Metadata From CSV', 'issuetype': 'UAT',
                                    'billstate': 'Billable', 'status': 'Done'}
    jira_parent_dict['WFD-3310'] = {'key': 'WFD-3310', 'customer': 'Spotify', 'totaltimeSpentSeconds': 0,
                                    'summary': 'UAT | WFD-3104  Prepare Assets for CMS', 'issuetype': 'UAT',
                                    'billstate': 'Billable', 'status': 'Done'}
    jira_parent_dict['WFD-3300'] = {'key': 'WFD-3300', 'customer': 'Hallmark', 'totaltimeSpentSeconds': 0,
                                    'summary': 'UAT | WFD-3142 Export Metadata From Search Results', 'issuetype': 'UAT',
                                    'billstate': 'Billable', 'status': 'Done'}
    jira_parent_dict['WFD-3086'] = {'key': 'WFD-3086', 'customer': 'Herbalife', 'totaltimeSpentSeconds': 0,
                                    'summary': 'SCOPE(4): Herbalife -- Change Proxy Workflows to Use Proxy to regen Proxy if Source is Truncated',
                                    'issuetype': 'Story', 'billstate': 'Billable', 'status': 'UAT'}
    jira_parent_dict['WFD-2898'] = {'key': 'WFD-2898', 'customer': None, 'totaltimeSpentSeconds': 0,
                                    'summary': 'Meetings (billable)', 'issuetype': 'Time Tracking Task',
                                    'billstate': None, 'status': 'New'}
    jira_parent_dict['WFD-2859'] = {'key': 'WFD-2859', 'customer': 'Spotify', 'totaltimeSpentSeconds': 0,
                                    'summary': 'SCOPE(12) - Share Assets with NY', 'issuetype': 'Story',
                                    'billstate': 'Billable', 'status': 'In Progress'}
    jira_parent_dict['WFD-2739'] = {'key': 'WFD-2739', 'customer': 'WBITV', 'totaltimeSpentSeconds': 0,
                                    'summary': 'UAT | WFD-2372 | Updates to OAP', 'issuetype': 'UAT',
                                    'billstate': 'Billable but Not Billed', 'status': 'In Progress'}
    jira_parent_dict['WFD-2432'] = {'key': 'WFD-2432', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 0,
                                    'summary': 'Estimation', 'issuetype': 'Time Tracking Task',
                                    'billstate': 'Not Billable', 'status': 'New'}
    jira_parent_dict['WFD-2024'] = {'key': 'WFD-2024', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 0,
                                    'summary': 'Other', 'issuetype': 'Time Tracking Task', 'billstate': 'Not Billable',
                                    'status': 'New'}
    jira_parent_dict['WFD-340'] = {'key': 'WFD-340', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 0,
                                   'summary': 'Project Management', 'issuetype': 'Time Tracking Task',
                                   'billstate': 'Not Billable', 'status': 'New'}
    jira_parent_dict['WFD-312'] = {'key': 'WFD-312', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 0,
                                   'summary': 'Workflow Support', 'issuetype': 'Time Tracking Task',
                                   'billstate': 'Not Billable', 'status': 'New'}
    jira_parent_dict['WFD-311'] = {'key': 'WFD-311', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 0,
                                   'summary': 'Meetings', 'issuetype': 'Time Tracking Task',
                                   'billstate': 'Not Billable', 'status': 'New'}
