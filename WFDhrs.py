import requests
import json
from timeit import default_timer as timer
import logging

jira_sub_dict = {}
jira_parent_dict = {}
tempo_list = []

# Set to True to run offline.  There are a set of print statements below that output the mock data
# when online.  The results can be copied and pasted into the lines that hardcode the mock data.
_debug = False


def LoadJiraSub(keylist):
    global jira_sub_dict

    # if _debug then the mock data has already been set
    if not  _debug:
        jira_url = 'https://levelsbeyond.atlassian.net/rest/api/2/search?' + \
                   'jql=key%20in%20({0})&expand=names&fields=key,summary,customfield_13500,issuetype,parent,status&maxResults=500'
        url = jira_url.format(keylist)

        r = requests.get(url, auth=GetAuth())
        json_return = json.loads(r.text)
        json_return = json_return['issues']

        for entry in json_return:
            # load final structure required
            jira_entry = {'key': entry['key'],
                          'parentkey': entry['fields']['parent']['key']
                         }

            jira_sub_dict[jira_entry['key']] = jira_entry
    return


def LoadJiraParent(keylist):
    global jira_parent_dict

    # if _debug then the mock data has already been set
    if  not _debug:
        jira_url = 'https://levelsbeyond.atlassian.net/rest/api/2/search?' + \
                   'jql=key%20in%20({0})&expand=names&fields=key,summary,customfield_13500,issuetype,parent,status&maxResults=500'
        url = jira_url.format(keylist)
        r = requests.get(url, auth=GetAuth())
        json_return = json.loads(r.text)
        json_return = json_return['issues']

        for entry in json_return:
            # load final structure required
            jira_entry = {'key': entry['key'],
                          # 'parentkey': entry['fields']['parent']['key'],
                          'customer': None,
                          'totaltimeSpentSeconds': 0,
                          'summary': entry['fields']['summary'],
                          # 'parentsummary': entry['fields']['parent']['fields']['summary'],
                          'issuetype': entry['fields']['issuetype']['name'],
                          'status': entry['fields']['status']['name']
                          }

            if 'customfield_13500' in entry['fields']:
                if entry['fields']['customfield_13500'] != None:
                    jira_entry['customer'] = entry['fields']['customfield_13500']['value']

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

    if  _debug:
        SetMockData()
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
        if entry['issuetype'] == "Sub-Task":
            keylistsub.append(entry['key'])

    if len(keylistsub) > 0:
        uniquelist = set(keylistsub)
        keystring = ",".join(uniquelist)
        LoadJiraSub(keystring)


    keylistparent = []
    tempo_list = tempo_list
    for entry in tempo_list:
        if entry['issuetype'] == 'Sub-Task':
            entry['parentkey'] = jira_sub_dict[entry['key']]['parentkey']
            keylistparent.append(jira_sub_dict[entry['key']]['parentkey'])  #add parents to non sub-task list


    tempo_list = tempo_list
    for entry in tempo_list:
        if entry['issuetype'] == "Sub-Task":
            pass
        else:
            keylistparent.append(entry['key'])  #add all non sub-tasks to list


    if len(keylistparent) > 0:
        uniquelist = set(keylistparent)
        keystring = ",".join(uniquelist)
        LoadJiraParent(keystring)


    tempo_list = tempo_list
    total_hours = 0
    for entry in tempo_list:
        # sum hours per JIRA ticket and total
        total_hours += entry['timeSpentSeconds']
        # add up Tempo time for each Jira ticket
        jira_parent_dict[entry['parentkey']]['totaltimeSpentSeconds'] += entry['timeSpentSeconds']


    for entry in tempo_list:
        if entry['issuetype'] == "Sub-Task":
            entry['parentkey'] = jira_sub_dict[entry['key']]['parentkey']
        else:
            entry['parentkey'] = entry['key']


    # output mock data from real data to be copied into code. Uncomment line below,
    # run a search, copy results and paste where mock data is set after the _debug test.
    # print('jira_sub_dict')
    # print(jira_sub_dict)
    # print('jira_parent_dict')
    # print(jira_parent_dict)
    # print('tempo_list')
    # print(tempo_list)


    # convert JIRA to a list
    jira_parent_list = []
    for k, v in jira_parent_dict.items():
        jira_parent_list.append(v)

    time_current = timer()
    logging.debug(
        'Final - start:{0}, current:{1}, duration:{2}'.format(time_start, time_current, time_current - time_start))

    # print('tempo_list')
    # for v in tempo_list:
    #     print(v)

    # print('jira_sub_dict')
    # print(jira_sub_dict)
    # for v in jira_sub_dict:
    #     print(v)
    #     print(v, v['key'])

    # print('jira_parent_list')
    # for v in jira_parent_list:
    #     print(v)

    return [jira_parent_list, tempo_list, total_hours]


def GetAuth():
    return ('rjohnson', 'Miter9le')


def SetMockData():
    global tempo_list
    global jira_sub_dict
    global jira_parent_dict

    tempo_list = [{'id': 120528, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation', 'tempocomment': 'Grooming', 'parentsummary': 'Estimation'}, {'id': 120633, 'parentkey': 'WFD-3040', 'key': 'WFD-3040', 'timeSpentSeconds': 10800, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2942 | Showtime | Clip Metadata Updates', 'tempocomment': 'Extremely slow to do anything with our connection method to Showtime. Also, some issues I had to investigate outside of updates I made for their request.', 'parentsummary': 'UAT | WFD-2942 | Showtime | Clip Metadata Updates'}, {'id': 120644, 'parentkey': 'WFD-3135', 'key': 'WFD-3171', 'timeSpentSeconds': 4500, 'issuetype': 'Sub-Task', 'summary': '(.5) Update batchMetaUpdater', 'tempocomment': 'Underestimated the groovy involvement with metadata on this one. Old logic was doing some funky stuff that took awhile to understand how to update properly.', 'parentsummary': '(.5) Update batchMetaUpdater'}, {'id': 120647, 'parentkey': 'WFD-3135', 'key': 'WFD-3172', 'timeSpentSeconds': 3600, 'issuetype': 'Sub-Task', 'summary': '(.5) Test batchMetaUpdater', 'tempocomment': 'Having Issues with metadata association not working in a groovy built query', 'parentsummary': '(.5) Test batchMetaUpdater'}, {'id': 120933, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'timeSpentSeconds': 2700, 'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD standup/sizing', 'parentsummary': 'Project Management'}, {'id': 120525, 'parentkey': 'WFD-3087', 'key': 'WFD-3217', 'timeSpentSeconds': 5040, 'issuetype': 'Sub-Task', 'summary': '(1) Alter workflows for testing', 'tempocomment': 'Updated workflows and imported to .85 server\n', 'parentsummary': '(1) Alter workflows for testing'}, {'id': 120535, 'parentkey': 'WFD-3061', 'key': 'WFD-3079', 'timeSpentSeconds': 5460, 'issuetype': 'Sub-Task', 'summary': 'Update Proxy Ingest', 'tempocomment': 'Updated the code for the proxy workflows.', 'parentsummary': 'Update Proxy Ingest'}, {'id': 120526, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 3600, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scrum and scoping', 'parentsummary': 'Meetings'}, {'id': 120527, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Standup + Extra discussion', 'parentsummary': 'Meetings'}, {'id': 120536, 'parentkey': 'WFD-3087', 'key': 'WFD-3150', 'timeSpentSeconds': 5400, 'issuetype': 'Sub-Task', 'summary': '(2) Test Archive Bucket Workflows', 'tempocomment': 'Testing completed for archive. There were some issues with the new build of RE on .85, those got resolved, but added time to testing', 'parentsummary': '(2) Test Archive Bucket Workflows'}, {'id': 120537, 'parentkey': 'WFD-3087', 'key': 'WFD-3152', 'timeSpentSeconds': 1320, 'issuetype': 'Sub-Task', 'summary': '(2) Test Restore Workflows', 'tempocomment': 'Testing completed up to this point', 'parentsummary': '(2) Test Restore Workflows'}, {'id': 120539, 'parentkey': 'WFD-3087', 'key': 'WFD-3154', 'timeSpentSeconds': 780, 'issuetype': 'Sub-Task', 'summary': '(1) Test Status Verification Workflows', 'tempocomment': 'Tested status verification as was able to', 'parentsummary': '(1) Test Status Verification Workflows'}, {'id': 120553, 'parentkey': 'WFD-3061', 'key': 'WFD-3080', 'timeSpentSeconds': 8940, 'issuetype': 'Sub-Task', 'summary': 'Update Source Ingest', 'tempocomment': 'Updated all the source ingest workflows.', 'parentsummary': 'Update Source Ingest'}, {'id': 120541, 'parentkey': 'WFD-3045', 'key': 'WFD-3045', 'timeSpentSeconds': 8100, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2954 Deluxe Digitized Fix Timecodes', 'tempocomment': 'Meeting with DK about results and new issues around clip creation\n\n-- Discussed issues with additional assets outside the scope of this workflow request that seem to be broken as well. The timecode fix will not work with these assets. ', 'parentsummary': 'UAT | WFD-2954 Deluxe Digitized Fix Timecodes'}, {'id': 120649, 'parentkey': 'WFD-2739', 'key': 'WFD-2739', 'timeSpentSeconds': 4860, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2372 | Updates to OAP', 'tempocomment': "UAT with client, identified some issues that had previously been 'unknowns' to me because we do not have visibility into OAP without the client. Remedied all issues with the exception of posting FrameRate to OAP. FrameRate is in the JSON sent to OAP, assuming that the field name for FrameRate may be different or the value isn't in the expected format. Waiting for docs or a time to talk to the Devs at OAP. ", 'parentsummary': 'UAT | WFD-2372 | Updates to OAP'}, {'id': 120635, 'parentkey': 'WFD-3061', 'key': 'WFD-3080', 'timeSpentSeconds': 3540, 'issuetype': 'Sub-Task', 'summary': 'Update Source Ingest', 'tempocomment': 'Started testing locally', 'parentsummary': 'Update Source Ingest'}, {'id': 120667, 'parentkey': 'WFD-2898', 'key': 'WFD-2898', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings (billable)', 'tempocomment': 'NHL Conversion - 2.1.5? 2.2?', 'parentsummary': 'Meetings (billable)'}, {'id': 120824, 'parentkey': 'WFD-3031', 'key': 'WFD-3031', 'timeSpentSeconds': 5400, 'issuetype': 'UAT', 'summary': 'UAT2 | WFD-2879 Modify MP5 workflows to accept Kafka messages', 'tempocomment': 'WFD-3031 DTV UAT - Modifications based on feedback for the Kafka metadata workflow', 'parentsummary': 'UAT2 | WFD-2879 Modify MP5 workflows to accept Kafka messages'}, {'id': 120825, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scoping', 'parentsummary': 'Meetings'}, {'id': 120826, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scrum', 'parentsummary': 'Meetings'}, {'id': 120827, 'parentkey': 'WFD-3031', 'key': 'WFD-3031', 'timeSpentSeconds': 4500, 'issuetype': 'UAT', 'summary': 'UAT2 | WFD-2879 Modify MP5 workflows to accept Kafka messages', 'tempocomment': 'WFD-3031 DTV uat and discussing with Bill', 'parentsummary': 'UAT2 | WFD-2879 Modify MP5 workflows to accept Kafka messages'}, {'id': 120828, 'parentkey': 'WFD-2454', 'key': 'WFD-2454', 'timeSpentSeconds': 2700, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2282 | Changes to LTFS Ingest process', 'tempocomment': 'WFD-2454 fixing issues for Howard Stern', 'parentsummary': 'UAT | WFD-2282 | Changes to LTFS Ingest process'}, {'id': 120829, 'parentkey': 'WFD-2454', 'key': 'WFD-2454', 'timeSpentSeconds': 900, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2282 | Changes to LTFS Ingest process', 'tempocomment': 'WFD-2454 discussing HS issue with DG', 'parentsummary': 'UAT | WFD-2282 | Changes to LTFS Ingest process'}, {'id': 120830, 'parentkey': 'WFD-3137', 'key': 'WFD-3222', 'timeSpentSeconds': 6300, 'issuetype': 'Sub-Task', 'summary': 'Upgrade VM to 2.1.4', 'tempocomment': 'trying to get 2.x vm up\n', 'parentsummary': 'Upgrade VM to 2.1.4'}, {'id': 120831, 'parentkey': 'WFD-3137', 'key': 'WFD-3199', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': '2016 photos with collection metadata', 'tempocomment': 'WFD-3199 going through workflows no changes needed', 'parentsummary': '2016 photos with collection metadata'}, {'id': 120832, 'parentkey': 'WFD-3137', 'key': 'WFD-3201', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': 'Custom Game Collection (x1 wf)', 'tempocomment': 'WFD-3201 making changes to workflow and testing to make sure logic works on 2.x', 'parentsummary': 'Custom Game Collection (x1 wf)'}, {'id': 120833, 'parentkey': 'WFD-3137', 'key': 'WFD-3202', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': 'Game ID Fix (x2 wf) ', 'tempocomment': 'WFD-3202 no changes required. Dealt with image assets only', 'parentsummary': 'Game ID Fix (x2 wf) '}, {'id': 120834, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'timeSpentSeconds': 900, 'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support', 'tempocomment': 'helped out engineer with categories stuff', 'parentsummary': 'Workflow Support'}, {'id': 120835, 'parentkey': 'WFD-3137', 'key': 'WFD-3202', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': 'Game ID Fix (x2 wf) ', 'tempocomment': 'WFD-3202 getting the low down on using (RE) java classes in groovy\nfixing workflow\ntrying to fix vm', 'parentsummary': 'Game ID Fix (x2 wf) '}, {'id': 120643, 'parentkey': 'WFD-3061', 'key': 'WFD-3070', 'timeSpentSeconds': 3480, 'issuetype': 'Sub-Task', 'summary': 'Update Clips', 'tempocomment': 'Tested a little over half the workflows locally.', 'parentsummary': 'Update Clips'}, {'id': 120636, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1200, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Standup', 'parentsummary': 'Meetings'}, {'id': 120637, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation', 'tempocomment': 'Scoping', 'parentsummary': 'Estimation'}, {'id': 120638, 'parentkey': 'WFD-2024', 'key': 'WFD-2024', 'timeSpentSeconds': 1080, 'issuetype': 'Time Tracking Task', 'summary': 'Other', 'tempocomment': 'Updating UAT tickets.', 'parentsummary': 'Other'}, {'id': 120639, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support', 'tempocomment': 'Robin', 'parentsummary': 'Workflow Support'}, {'id': 120640, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'tempocomment': 'Helping Mitch with VM upgrade.', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120641, 'parentkey': 'WFD-3135', 'key': 'WFD-3135', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete', 'tempocomment': 'Helping Tyler with groovy stuff', 'parentsummary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete'}, {'id': 120642, 'parentkey': 'WFD-2898', 'key': 'WFD-2898', 'timeSpentSeconds': 1200, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings (billable)', 'tempocomment': 'AXS.TV - Helping Alex and Daniel write a story', 'parentsummary': 'Meetings (billable)'}, {'id': 120645, 'parentkey': 'WFD-3061', 'key': 'WFD-3061', 'timeSpentSeconds': 3600, 'issuetype': 'Story', 'summary': 'SCOPED(28): NHL 2.x Upgrade - INGEST', 'tempocomment': 'Help', 'parentsummary': 'SCOPED(28): NHL 2.x Upgrade - INGEST'}, {'id': 120646, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 2700, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'tempocomment': 'Help', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120650, 'parentkey': 'WFD-3221', 'key': 'WFD-3221', 'timeSpentSeconds': 2700, 'issuetype': 'Story', 'summary': 'NOT READY - Archive/Restore Using XenData XML API', 'tempocomment': 'Worked with DGonzales and Dylan to get this ticket into a workable state. ', 'parentsummary': 'NOT READY - Archive/Restore Using XenData XML API'}, {'id': 120681, 'parentkey': 'WFD-3135', 'key': 'WFD-3172', 'timeSpentSeconds': 7200, 'issuetype': 'Sub-Task', 'summary': '(.5) Test batchMetaUpdater', 'tempocomment': 'Testing logic using other data objects, works with other asset types. Tried a query step instead of groovy, still breaks. Narrowed down the issue, submitted a bug [REACH-19472]. Created a test workflow and talked to Siri.', 'parentsummary': '(.5) Test batchMetaUpdater'}, {'id': 120712, 'parentkey': 'WFD-3135', 'key': 'WFD-3173', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': '(.5) Update Delete', 'tempocomment': 'Updates', 'parentsummary': '(.5) Update Delete'}, {'id': 120713, 'parentkey': 'WFD-3135', 'key': 'WFD-3174', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': '(.5) Test Delete', 'tempocomment': 'Tests', 'parentsummary': '(.5) Test Delete'}, {'id': 120763, 'parentkey': 'WFD-3228', 'key': 'WFD-3228', 'timeSpentSeconds': 4500, 'issuetype': 'Story', 'summary': 'Update Panel Clip WF to set multi-picklist metadata properly', 'tempocomment': 'Screenshare with Lody + make update + test', 'parentsummary': 'Update Panel Clip WF to set multi-picklist metadata properly'}, {'id': 120777, 'parentkey': 'WFD-3136', 'key': 'WFD-3175', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': '(.5) Update Game Collections', 'tempocomment': 'Reviewed workflows, no updates required.', 'parentsummary': '(.5) Update Game Collections'}, {'id': 120778, 'parentkey': 'WFD-3136', 'key': 'WFD-3177', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': '(1) Update update asset data', 'tempocomment': 'Dev - Less work than anticipated with the WF names', 'parentsummary': '(1) Update update asset data'}, {'id': 120779, 'parentkey': 'WFD-3136', 'key': 'WFD-3178', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': '(1) Test update asset data', 'tempocomment': 'Test', 'parentsummary': '(1) Test update asset data'}, {'id': 120934, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'timeSpentSeconds': 2700, 'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD standup/sizing', 'parentsummary': 'Project Management'}, {'id': 120693, 'parentkey': 'WFD-3061', 'key': 'WFD-3070', 'timeSpentSeconds': 9420, 'issuetype': 'Sub-Task', 'summary': 'Update Clips', 'tempocomment': 'Tested all clip workflows locally', 'parentsummary': 'Update Clips'}, {'id': 120757, 'parentkey': 'WFD-3061', 'key': 'WFD-3077', 'timeSpentSeconds': 4020, 'issuetype': 'Sub-Task', 'summary': 'Update Ongoing Image Ingest', 'tempocomment': 'Tested workflows locally.', 'parentsummary': 'Update Ongoing Image Ingest'}, {'id': 120714, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 900, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Standup', 'parentsummary': 'Meetings'}, {'id': 120758, 'parentkey': 'WFD-3135', 'key': 'WFD-3135', 'timeSpentSeconds': 2700, 'issuetype': 'Story', 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete', 'tempocomment': 'github PR stuff', 'parentsummary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete'}, {'id': 120762, 'parentkey': 'WFD-3061', 'key': 'WFD-3081', 'timeSpentSeconds': 3000, 'issuetype': 'Sub-Task', 'summary': 'Update Misc Image Ingest', 'tempocomment': 'Tested workflows locally.', 'parentsummary': 'Update Misc Image Ingest'}, {'id': 120836, 'parentkey': 'WFD-3137', 'key': 'WFD-3203', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': 'Get All Asset Metadata ( x1 wf) ', 'tempocomment': 'WFD-3203 working on fixing extract metadata logic', 'parentsummary': 'Get All Asset Metadata ( x1 wf) '}, {'id': 120837, 'parentkey': 'WFD-3137', 'key': 'WFD-3222', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': 'Upgrade VM to 2.1.4', 'tempocomment': 'WFD-3222 upgrading vm', 'parentsummary': 'Upgrade VM to 2.1.4'}, {'id': 120838, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scrum', 'parentsummary': 'Meetings'}, {'id': 120839, 'parentkey': 'WFD-3137', 'key': 'WFD-3222', 'timeSpentSeconds': 5400, 'issuetype': 'Sub-Task', 'summary': 'Upgrade VM to 2.1.4', 'tempocomment': 'upgrading vm from scratch to get a good install of 2.1.4', 'parentsummary': 'Upgrade VM to 2.1.4'}, {'id': 120840, 'parentkey': 'WFD-3137', 'key': 'WFD-3203', 'timeSpentSeconds': 3600, 'issuetype': 'Sub-Task', 'summary': 'Get All Asset Metadata ( x1 wf) ', 'tempocomment': 'WFD-3203 figuring out metadata objects in java', 'parentsummary': 'Get All Asset Metadata ( x1 wf) '}, {'id': 120841, 'parentkey': 'WFD-3135', 'key': 'WFD-3135', 'timeSpentSeconds': 1800, 'issuetype': 'Story', 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete', 'tempocomment': 'WFD-3135 reviewing Tyler’s code', 'parentsummary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete'}, {'id': 120842, 'parentkey': 'WFD-3137', 'key': 'WFD-3203', 'timeSpentSeconds': 3600, 'issuetype': 'Sub-Task', 'summary': 'Get All Asset Metadata ( x1 wf) ', 'tempocomment': 'WFD-3203  figuring out metadata objects in java', 'parentsummary': 'Get All Asset Metadata ( x1 wf) '}, {'id': 120843, 'parentkey': 'WFD-3137', 'key': 'WFD-3204', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': 'Submission Metadata (x4 wf)', 'tempocomment': 'WFD-3204 fixing metadata references', 'parentsummary': 'Submission Metadata (x4 wf)'}, {'id': 120844, 'parentkey': 'WFD-3137', 'key': 'WFD-3204', 'timeSpentSeconds': 8100, 'issuetype': 'Sub-Task', 'summary': 'Submission Metadata (x4 wf)', 'tempocomment': 'WFD-3204 going down a rabbit hole and having Kemm drop me a ladder', 'parentsummary': 'Submission Metadata (x4 wf)'}, {'id': 120764, 'parentkey': 'WFD-3061', 'key': 'WFD-3078', 'timeSpentSeconds': 1860, 'issuetype': 'Sub-Task', 'summary': 'Update Deluxe Replacement Ingest', 'tempocomment': 'Tested locally.', 'parentsummary': 'Update Deluxe Replacement Ingest'}, {'id': 120765, 'parentkey': 'WFD-3061', 'key': 'WFD-3079', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': 'Update Proxy Ingest', 'tempocomment': 'Started testing.', 'parentsummary': 'Update Proxy Ingest'}, {'id': 120766, 'parentkey': 'WFD-3228', 'key': 'WFD-3228', 'timeSpentSeconds': 1800, 'issuetype': 'Story', 'summary': 'Update Panel Clip WF to set multi-picklist metadata properly', 'tempocomment': 'Working out github and version/release', 'parentsummary': 'Update Panel Clip WF to set multi-picklist metadata properly'}, {'id': 120767, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 1800, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'tempocomment': 'Help', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120768, 'parentkey': 'WFD-3087', 'key': 'WFD-3087', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Archive and Restore', 'tempocomment': 'Looking over PR', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Archive and Restore'}, {'id': 120770, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1200, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Standup', 'parentsummary': 'Meetings'}, {'id': 120769, 'parentkey': 'WFD-3061', 'key': 'WFD-3061', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(28): NHL 2.x Upgrade - INGEST', 'tempocomment': 'Help', 'parentsummary': 'SCOPED(28): NHL 2.x Upgrade - INGEST'}, {'id': 120771, 'parentkey': 'WFD-3135', 'key': 'WFD-3135', 'timeSpentSeconds': 600, 'issuetype': 'Story', 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete', 'tempocomment': 'Helped with more Groovy code.', 'parentsummary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete'}, {'id': 120772, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 600, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'tempocomment': 'Helped more with VM upgrade.', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120773, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'timeSpentSeconds': 1200, 'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support', 'tempocomment': 'Robin', 'parentsummary': 'Workflow Support'}, {'id': 120863, 'parentkey': 'WFD-3230', 'key': 'WFD-3230', 'timeSpentSeconds': 3600, 'issuetype': 'Story', 'summary': 'SCOPE(12) - Repair Timelines with null or invalid Primary Track', 'tempocomment': 'Looking into the timline track/clip issue', 'parentsummary': 'SCOPE(12) - Repair Timelines with null or invalid Primary Track'}, {'id': 120774, 'parentkey': 'WFD-3040', 'key': 'WFD-3040', 'timeSpentSeconds': 600, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2942 | Showtime | Clip Metadata Updates', 'tempocomment': 'PR review', 'parentsummary': 'UAT | WFD-2942 | Showtime | Clip Metadata Updates'}, {'id': 120775, 'parentkey': 'WFD-3135', 'key': 'WFD-3135', 'timeSpentSeconds': 1800, 'issuetype': 'Story', 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete', 'tempocomment': '2 PR reviews.', 'parentsummary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete'}, {'id': 120801, 'parentkey': 'WFD-3228', 'key': 'WFD-3228', 'timeSpentSeconds': 7200, 'issuetype': 'Story', 'summary': 'Update Panel Clip WF to set multi-picklist metadata properly', 'tempocomment': "Working with Lody's slow machine to test. Made fixes. Had Stephan help me release app-workflows", 'parentsummary': 'Update Panel Clip WF to set multi-picklist metadata properly'}, {'id': 120805, 'parentkey': 'WFD-3137', 'key': 'WFD-3200', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': 'Clean Metadata (x53 wf)', 'tempocomment': 'Basic Changes', 'parentsummary': 'Clean Metadata (x53 wf)'}, {'id': 120869, 'parentkey': 'WFD-3136', 'key': 'WFD-3136', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(9): NHL 2.x Upgrade - Game Collection, Update Asset Data', 'tempocomment': 'Github stuff', 'parentsummary': 'SCOPED(9): NHL 2.x Upgrade - Game Collection, Update Asset Data'}, {'id': 120870, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'tempocomment': 'Github stuff', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120935, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'timeSpentSeconds': 2700, 'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD standup/sizing', 'parentsummary': 'Project Management'}, {'id': 120967, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'timeSpentSeconds': 3600, 'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD - GitPrime stats for last week', 'parentsummary': 'Project Management'}, {'id': 120968, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD - update customers and associated Quick Searches ', 'parentsummary': 'Project Management'}, {'id': 120969, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'timeSpentSeconds': 7200, 'issuetype': 'Time Tracking Task', 'summary': 'Project Management', 'tempocomment': 'WFD - sprint planning', 'parentsummary': 'Project Management'}, {'id': 120806, 'parentkey': 'WFD-3061', 'key': 'WFD-3079', 'timeSpentSeconds': 2820, 'issuetype': 'Sub-Task', 'summary': 'Update Proxy Ingest', 'tempocomment': 'Tested workflows locally.', 'parentsummary': 'Update Proxy Ingest'}, {'id': 120800, 'parentkey': 'WFD-3011', 'key': 'WFD-3011', 'timeSpentSeconds': 7200, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2364 | Ravens: Increment Duplicate Asset + Filenames', 'tempocomment': 'Had a call with Brad and Jack. Moved workflows over to production. Did some testing and made some tweaks.', 'parentsummary': 'UAT | WFD-2364 | Ravens: Increment Duplicate Asset + Filenames'}, {'id': 120802, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 7200, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'tempocomment': 'Helping work through Groovy issues. Found a bug with Mitch to submit, testing MetadataService functions.', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120803, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 900, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'standup', 'parentsummary': 'Meetings'}, {'id': 120804, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'timeSpentSeconds': 900, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation', 'tempocomment': 'Grooming', 'parentsummary': 'Estimation'}, {'id': 120862, 'parentkey': 'WFD-3061', 'key': 'WFD-3080', 'timeSpentSeconds': 4980, 'issuetype': 'Sub-Task', 'summary': 'Update Source Ingest', 'tempocomment': 'Tested all workflows locally. Made a PR to Github.', 'parentsummary': 'Update Source Ingest'}, {'id': 120807, 'parentkey': 'WFD-3137', 'key': 'WFD-3209', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': 'Update Image Game IDs ( x1 wf )', 'tempocomment': 'Update Groovy and Test', 'parentsummary': 'Update Image Game IDs ( x1 wf )'}, {'id': 120811, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'tempocomment': 'Testing more metadata groovy stuff', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120815, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 7200, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Planning', 'parentsummary': 'Meetings'}, {'id': 120845, 'parentkey': 'WFD-3137', 'key': 'WFD-3204', 'timeSpentSeconds': 7200, 'issuetype': 'Sub-Task', 'summary': 'Submission Metadata (x4 wf)', 'tempocomment': 'WFD-3204 fixing the workflows', 'parentsummary': 'Submission Metadata (x4 wf)'}, {'id': 120846, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 900, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scrum', 'parentsummary': 'Meetings'}, {'id': 120847, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 900, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'scoping', 'parentsummary': 'Meetings'}, {'id': 120848, 'parentkey': 'WFD-3137', 'key': 'WFD-3204', 'timeSpentSeconds': 4500, 'issuetype': 'Sub-Task', 'summary': 'Submission Metadata (x4 wf)', 'tempocomment': 'WFD-3204 finishing fixing the workflows', 'parentsummary': 'Submission Metadata (x4 wf)'}, {'id': 120849, 'parentkey': 'WFD-3137', 'key': 'WFD-3204', 'timeSpentSeconds': 2700, 'issuetype': 'Sub-Task', 'summary': 'Submission Metadata (x4 wf)', 'tempocomment': 'writing up and submitting bug REACH-19495', 'parentsummary': 'Submission Metadata (x4 wf)'}, {'id': 120850, 'parentkey': 'WFD-3137', 'key': 'WFD-3204', 'timeSpentSeconds': 2700, 'issuetype': 'Sub-Task', 'summary': 'Submission Metadata (x4 wf)', 'tempocomment': 'WFD-3204 fixing the workflows', 'parentsummary': 'Submission Metadata (x4 wf)'}, {'id': 120851, 'parentkey': 'WFD-3137', 'key': 'WFD-3205', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': 'Update Category On Image WIth Game ID (x2 wf) ', 'tempocomment': 'WFD-3205 reviewing workflows for changes. No changes needed', 'parentsummary': 'Update Category On Image WIth Game ID (x2 wf) '}, {'id': 120852, 'parentkey': 'WFD-3137', 'key': 'WFD-3206', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': 'Update From Exif (x1 wf)', 'tempocomment': 'WFD-3206 reviewing for changes. No changes needed', 'parentsummary': 'Update From Exif (x1 wf)'}, {'id': 120853, 'parentkey': 'WFD-3137', 'key': 'WFD-3207', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': 'Update From Media Info (x1 wf)', 'tempocomment': 'WFD-3207 reviewing. Changed subject to VideoAssetMaster. Corrected how the mezzanine file was being accessed.', 'parentsummary': 'Update From Media Info (x1 wf)'}, {'id': 120854, 'parentkey': 'WFD-3137', 'key': 'WFD-3210', 'timeSpentSeconds': 3600, 'issuetype': 'Sub-Task', 'summary': 'Update Picklist ( x1 wf )', 'tempocomment': 'WFD-3210 reviewing and updating picklist to use the most recent java functions', 'parentsummary': 'Update Picklist ( x1 wf )'}, {'id': 120855, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 5400, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'grooming', 'parentsummary': 'Meetings'}, {'id': 120856, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 900, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'timetracking', 'parentsummary': 'Meetings'}, {'id': 120858, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 3000, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'tempocomment': 'PR review.', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120859, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 600, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'tempocomment': 'PR review', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120860, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 600, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'tempocomment': 'PR review.', 'parentsummary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120861, 'parentkey': 'WFD-3136', 'key': 'WFD-3136', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(9): NHL 2.x Upgrade - Game Collection, Update Asset Data', 'tempocomment': 'PR review.', 'parentsummary': 'SCOPED(9): NHL 2.x Upgrade - Game Collection, Update Asset Data'}, {'id': 120864, 'parentkey': 'WFD-3230', 'key': 'WFD-3230', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPE(12) - Repair Timelines with null or invalid Primary Track', 'tempocomment': 'Talking with Bill about this issue.', 'parentsummary': 'SCOPE(12) - Repair Timelines with null or invalid Primary Track'}, {'id': 120865, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 600, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Standup', 'parentsummary': 'Meetings'}, {'id': 120866, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'timeSpentSeconds': 1200, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation', 'tempocomment': 'Scoping', 'parentsummary': 'Estimation'}, {'id': 120867, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 3600, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings', 'tempocomment': 'Planning', 'parentsummary': 'Meetings'}, {'id': 120868, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support', 'tempocomment': 'Robin', 'parentsummary': 'Workflow Support'}]


    jira_parent_dict = {'WFD-3230': {'key': 'WFD-3230', 'customer': 'NHL', 'totaltimeSpentSeconds': 4500, 'summary': 'SCOPE(12) - Repair Timelines with null or invalid Primary Track', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-3228': {'key': 'WFD-3228', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 13500, 'summary': 'Update Panel Clip WF to set multi-picklist metadata properly', 'issuetype': 'Story', 'status': 'Done'}, 'WFD-3221': {'key': 'WFD-3221', 'customer': 'AXS TV', 'totaltimeSpentSeconds': 2700, 'summary': 'NOT READY - Archive/Restore Using XenData XML API', 'issuetype': 'Story', 'status': 'New'}, 'WFD-3137': {'key': 'WFD-3137', 'customer': 'NHL', 'totaltimeSpentSeconds': 82200, 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-3136': {'key': 'WFD-3136', 'customer': 'NHL', 'totaltimeSpentSeconds': 6300, 'summary': 'SCOPED(9): NHL 2.x Upgrade - Game Collection, Update Asset Data', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-3135': {'key': 'WFD-3135', 'customer': 'NHL', 'totaltimeSpentSeconds': 25800, 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-3087': {'key': 'WFD-3087', 'customer': 'NHL', 'totaltimeSpentSeconds': 13440, 'summary': 'SCOPED(24): NHL 2.x Upgrade - Archive and Restore', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-3061': {'key': 'WFD-3061', 'customer': 'NHL', 'totaltimeSpentSeconds': 52920, 'summary': 'SCOPED(28): NHL 2.x Upgrade - INGEST', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-3045': {'key': 'WFD-3045', 'customer': 'NHL', 'totaltimeSpentSeconds': 8100, 'summary': 'UAT | WFD-2954 Deluxe Digitized Fix Timecodes', 'issuetype': 'UAT', 'status': 'Done'}, 'WFD-3040': {'key': 'WFD-3040', 'customer': 'Showtime NY', 'totaltimeSpentSeconds': 11400, 'summary': 'UAT | WFD-2942 | Showtime | Clip Metadata Updates', 'issuetype': 'UAT', 'status': 'Done'}, 'WFD-3031': {'key': 'WFD-3031', 'customer': 'DirecTV DFW', 'totaltimeSpentSeconds': 9900, 'summary': 'UAT2 | WFD-2879 Modify MP5 workflows to accept Kafka messages', 'issuetype': 'UAT', 'status': 'Done'}, 'WFD-3011': {'key': 'WFD-3011', 'customer': 'Baltimore Ravens', 'totaltimeSpentSeconds': 7200, 'summary': 'UAT | WFD-2364 | Ravens: Increment Duplicate Asset + Filenames', 'issuetype': 'UAT', 'status': 'Done'}, 'WFD-2898': {'key': 'WFD-2898', 'customer': None, 'totaltimeSpentSeconds': 3000, 'summary': 'Meetings (billable)', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-2739': {'key': 'WFD-2739', 'customer': 'WBITV', 'totaltimeSpentSeconds': 4860, 'summary': 'UAT | WFD-2372 | Updates to OAP', 'issuetype': 'UAT', 'status': 'In Progress'}, 'WFD-2454': {'key': 'WFD-2454', 'customer': 'Sirius XM (Howard Stern)', 'totaltimeSpentSeconds': 3600, 'summary': 'UAT | WFD-2282 | Changes to LTFS Ingest process', 'issuetype': 'UAT', 'status': 'In Progress'}, 'WFD-2432': {'key': 'WFD-2432', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 5700, 'summary': 'Estimation', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-2024': {'key': 'WFD-2024', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 1080, 'summary': 'Other', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-340': {'key': 'WFD-340', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 20700, 'summary': 'Project Management', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-312': {'key': 'WFD-312', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 5700, 'summary': 'Workflow Support', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-311': {'key': 'WFD-311', 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 34500, 'summary': 'Meetings', 'issuetype': 'Time Tracking Task', 'status': 'New'}}


    jira_sub_dict = {'WFD-3222': {'key': 'WFD-3222', 'parentkey': 'WFD-3137'}, 'WFD-3217': {'key': 'WFD-3217', 'parentkey': 'WFD-3087'}, 'WFD-3210': {'key': 'WFD-3210', 'parentkey': 'WFD-3137'}, 'WFD-3209': {'key': 'WFD-3209', 'parentkey': 'WFD-3137'}, 'WFD-3207': {'key': 'WFD-3207', 'parentkey': 'WFD-3137'}, 'WFD-3206': {'key': 'WFD-3206', 'parentkey': 'WFD-3137'}, 'WFD-3205': {'key': 'WFD-3205', 'parentkey': 'WFD-3137'}, 'WFD-3204': {'key': 'WFD-3204', 'parentkey': 'WFD-3137'}, 'WFD-3203': {'key': 'WFD-3203', 'parentkey': 'WFD-3137'}, 'WFD-3202': {'key': 'WFD-3202', 'parentkey': 'WFD-3137'}, 'WFD-3201': {'key': 'WFD-3201', 'parentkey': 'WFD-3137'}, 'WFD-3200': {'key': 'WFD-3200', 'parentkey': 'WFD-3137'}, 'WFD-3199': {'key': 'WFD-3199', 'parentkey': 'WFD-3137'}, 'WFD-3178': {'key': 'WFD-3178', 'parentkey': 'WFD-3136'}, 'WFD-3177': {'key': 'WFD-3177', 'parentkey': 'WFD-3136'}, 'WFD-3175': {'key': 'WFD-3175', 'parentkey': 'WFD-3136'}, 'WFD-3174': {'key': 'WFD-3174', 'parentkey': 'WFD-3135'}, 'WFD-3173': {'key': 'WFD-3173', 'parentkey': 'WFD-3135'}, 'WFD-3172': {'key': 'WFD-3172', 'parentkey': 'WFD-3135'}, 'WFD-3171': {'key': 'WFD-3171', 'parentkey': 'WFD-3135'}, 'WFD-3154': {'key': 'WFD-3154', 'parentkey': 'WFD-3087'}, 'WFD-3152': {'key': 'WFD-3152', 'parentkey': 'WFD-3087'}, 'WFD-3150': {'key': 'WFD-3150', 'parentkey': 'WFD-3087'}, 'WFD-3081': {'key': 'WFD-3081', 'parentkey': 'WFD-3061'}, 'WFD-3080': {'key': 'WFD-3080', 'parentkey': 'WFD-3061'}, 'WFD-3079': {'key': 'WFD-3079', 'parentkey': 'WFD-3061'}, 'WFD-3078': {'key': 'WFD-3078', 'parentkey': 'WFD-3061'}, 'WFD-3077': {'key': 'WFD-3077', 'parentkey': 'WFD-3061'}, 'WFD-3070': {'key': 'WFD-3070', 'parentkey': 'WFD-3061'}}
