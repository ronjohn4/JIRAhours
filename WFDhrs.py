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

    # set JIRA mock data
    if  _debug:
        jira_sub_dict = {'WFD-2432': {'key': 'WFD-2432', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 3600, 'summary': 'Estimation', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-3040': {'key': 'WFD-3040', 'parentkey': None, 'customer': 'Showtime NY', 'totaltimeSpentSeconds': 11400, 'summary': 'UAT | WFD-2942 | Showtime | Clip Metadata Updates', 'issuetype': 'UAT', 'status': 'Done'}, 'WFD-3135': {'key': 'WFD-3135', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 25800, 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-340': {'key': 'WFD-340', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 5400, 'summary': 'Project Management', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-3087': {'key': 'WFD-3087', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 13440, 'summary': 'SCOPED(24): NHL 2.x Upgrade - Archive and Restore', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-3061': {'key': 'WFD-3061', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 45120, 'summary': 'SCOPED(28): NHL 2.x Upgrade - INGEST', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-311': {'key': 'WFD-311', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 14100, 'summary': 'Meetings', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-3045': {'key': 'WFD-3045', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 8100, 'summary': 'UAT | WFD-2954 Deluxe Digitized Fix Timecodes', 'issuetype': 'UAT', 'status': 'Done'}, 'WFD-2739': {'key': 'WFD-2739', 'parentkey': None, 'customer': 'WBITV', 'totaltimeSpentSeconds': 4860, 'summary': 'UAT | WFD-2372 | Updates to OAP', 'issuetype': 'UAT', 'status': 'In Progress'}, 'WFD-2898': {'key': 'WFD-2898', 'parentkey': None, 'customer': None, 'totaltimeSpentSeconds': 3000, 'summary': 'Meetings (billable)', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-3031': {'key': 'WFD-3031', 'parentkey': None, 'customer': 'DirecTV DFW', 'totaltimeSpentSeconds': 9900, 'summary': 'UAT2 | WFD-2879 Modify MP5 workflows to accept Kafka messages', 'issuetype': 'UAT', 'status': 'Done'}, 'WFD-2454': {'key': 'WFD-2454', 'parentkey': None, 'customer': 'Sirius XM (Howard Stern)', 'totaltimeSpentSeconds': 3600, 'summary': 'UAT | WFD-2282 | Changes to LTFS Ingest process', 'issuetype': 'UAT', 'status': 'In Progress'}, 'WFD-3137': {'key': 'WFD-3137', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 42900, 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-312': {'key': 'WFD-312', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 3900, 'summary': 'Workflow Support', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-2024': {'key': 'WFD-2024', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 1080, 'summary': 'Other', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-3221': {'key': 'WFD-3221', 'parentkey': None, 'customer': 'AXS TV', 'totaltimeSpentSeconds': 2700, 'summary': 'NOT READY - Archive/Restore Using XenData XML API', 'issuetype': 'Story', 'status': 'New'}, 'WFD-3228': {'key': 'WFD-3228', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 6300, 'summary': 'Update Panel Clip WF to set multi-picklist metadata properly', 'issuetype': 'Story', 'status': 'Done'}, 'WFD-3136': {'key': 'WFD-3136', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 4500, 'summary': 'SCOPED(9): NHL 2.x Upgrade - Game Collection, Update Asset Data', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-3230': {'key': 'WFD-3230', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 3600, 'summary': 'SCOPE(12) - Repair Timelines with null or invalid Primary Track', 'issuetype': 'Story', 'status': 'UAT'}}
    else:
        jira_url = 'https://levelsbeyond.atlassian.net/rest/api/2/search?' + \
                   'jql=key%20in%20({0})&expand=names&fields=key,summary,customfield_13500,issuetype,parent,status&maxResults=500'
        url = jira_url.format(keylist)

        r = requests.get(url, auth=('rjohnson', 'Miter9le'))
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

    # set JIRA Parent mock data
    if  _debug:
        jira_parent_dict = {'WFD-2432': {'key': 'WFD-2432', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 3600, 'summary': 'Estimation', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-3040': {'key': 'WFD-3040', 'parentkey': None, 'customer': 'Showtime NY', 'totaltimeSpentSeconds': 11400, 'summary': 'UAT | WFD-2942 | Showtime | Clip Metadata Updates', 'issuetype': 'UAT', 'status': 'Done'}, 'WFD-3135': {'key': 'WFD-3135', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 25800, 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-340': {'key': 'WFD-340', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 5400, 'summary': 'Project Management', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-3087': {'key': 'WFD-3087', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 13440, 'summary': 'SCOPED(24): NHL 2.x Upgrade - Archive and Restore', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-3061': {'key': 'WFD-3061', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 45120, 'summary': 'SCOPED(28): NHL 2.x Upgrade - INGEST', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-311': {'key': 'WFD-311', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 14100, 'summary': 'Meetings', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-3045': {'key': 'WFD-3045', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 8100, 'summary': 'UAT | WFD-2954 Deluxe Digitized Fix Timecodes', 'issuetype': 'UAT', 'status': 'Done'}, 'WFD-2739': {'key': 'WFD-2739', 'parentkey': None, 'customer': 'WBITV', 'totaltimeSpentSeconds': 4860, 'summary': 'UAT | WFD-2372 | Updates to OAP', 'issuetype': 'UAT', 'status': 'In Progress'}, 'WFD-2898': {'key': 'WFD-2898', 'parentkey': None, 'customer': None, 'totaltimeSpentSeconds': 3000, 'summary': 'Meetings (billable)', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-3031': {'key': 'WFD-3031', 'parentkey': None, 'customer': 'DirecTV DFW', 'totaltimeSpentSeconds': 9900, 'summary': 'UAT2 | WFD-2879 Modify MP5 workflows to accept Kafka messages', 'issuetype': 'UAT', 'status': 'Done'}, 'WFD-2454': {'key': 'WFD-2454', 'parentkey': None, 'customer': 'Sirius XM (Howard Stern)', 'totaltimeSpentSeconds': 3600, 'summary': 'UAT | WFD-2282 | Changes to LTFS Ingest process', 'issuetype': 'UAT', 'status': 'In Progress'}, 'WFD-3137': {'key': 'WFD-3137', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 42900, 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-312': {'key': 'WFD-312', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 3900, 'summary': 'Workflow Support', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-2024': {'key': 'WFD-2024', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 1080, 'summary': 'Other', 'issuetype': 'Time Tracking Task', 'status': 'New'}, 'WFD-3221': {'key': 'WFD-3221', 'parentkey': None, 'customer': 'AXS TV', 'totaltimeSpentSeconds': 2700, 'summary': 'NOT READY - Archive/Restore Using XenData XML API', 'issuetype': 'Story', 'status': 'New'}, 'WFD-3228': {'key': 'WFD-3228', 'parentkey': None, 'customer': 'Levels Beyond', 'totaltimeSpentSeconds': 6300, 'summary': 'Update Panel Clip WF to set multi-picklist metadata properly', 'issuetype': 'Story', 'status': 'Done'}, 'WFD-3136': {'key': 'WFD-3136', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 4500, 'summary': 'SCOPED(9): NHL 2.x Upgrade - Game Collection, Update Asset Data', 'issuetype': 'Story', 'status': 'UAT'}, 'WFD-3230': {'key': 'WFD-3230', 'parentkey': None, 'customer': 'NHL', 'totaltimeSpentSeconds': 3600, 'summary': 'SCOPE(12) - Repair Timelines with null or invalid Primary Track', 'issuetype': 'Story', 'status': 'UAT'}}
    else:
        jira_url = 'https://levelsbeyond.atlassian.net/rest/api/2/search?' + \
                   'jql=key%20in%20({0})&expand=names&fields=key,summary,customfield_13500,issuetype,parent,status&maxResults=500'
        url = jira_url.format(keylist)
        r = requests.get(url, auth=('rjohnson', 'Miter9le'))
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
        # set tempo mock data
        tempo_list = [{'id': 120528, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation'}, {'id': 120633, 'parentkey': 'WFD-3040', 'key': 'WFD-3040', 'timeSpentSeconds': 10800, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2942 | Showtime | Clip Metadata Updates'}, {'id': 120644, 'parentkey': 'WFD-3135', 'key': 'WFD-3171', 'timeSpentSeconds': 4500, 'issuetype': 'Sub-Task', 'summary': '(.5) Update batchMetaUpdater'}, {'id': 120647, 'parentkey': 'WFD-3135', 'key': 'WFD-3172', 'timeSpentSeconds': 3600, 'issuetype': 'Sub-Task', 'summary': '(.5) Test batchMetaUpdater'}, {'id': 120933, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'timeSpentSeconds': 2700, 'issuetype': 'Time Tracking Task', 'summary': 'Project Management'}, {'id': 120525, 'parentkey': 'WFD-3087', 'key': 'WFD-3217', 'timeSpentSeconds': 5040, 'issuetype': 'Sub-Task', 'summary': '(1) Alter workflows for testing'}, {'id': 120535, 'parentkey': 'WFD-3061', 'key': 'WFD-3079', 'timeSpentSeconds': 5460, 'issuetype': 'Sub-Task', 'summary': 'Update Proxy Ingest'}, {'id': 120526, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 3600, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings'}, {'id': 120527, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings'}, {'id': 120536, 'parentkey': 'WFD-3087', 'key': 'WFD-3150', 'timeSpentSeconds': 5400, 'issuetype': 'Sub-Task', 'summary': '(2) Test Archive Bucket Workflows'}, {'id': 120537, 'parentkey': 'WFD-3087', 'key': 'WFD-3152', 'timeSpentSeconds': 1320, 'issuetype': 'Sub-Task', 'summary': '(2) Test Restore Workflows'}, {'id': 120539, 'parentkey': 'WFD-3087', 'key': 'WFD-3154', 'timeSpentSeconds': 780, 'issuetype': 'Sub-Task', 'summary': '(1) Test Status Verification Workflows'}, {'id': 120553, 'parentkey': 'WFD-3061', 'key': 'WFD-3080', 'timeSpentSeconds': 8940, 'issuetype': 'Sub-Task', 'summary': 'Update Source Ingest'}, {'id': 120541, 'parentkey': 'WFD-3045', 'key': 'WFD-3045', 'timeSpentSeconds': 8100, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2954 Deluxe Digitized Fix Timecodes'}, {'id': 120649, 'parentkey': 'WFD-2739', 'key': 'WFD-2739', 'timeSpentSeconds': 4860, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2372 | Updates to OAP'}, {'id': 120635, 'parentkey': 'WFD-3061', 'key': 'WFD-3080', 'timeSpentSeconds': 3540, 'issuetype': 'Sub-Task', 'summary': 'Update Source Ingest'}, {'id': 120667, 'parentkey': 'WFD-2898', 'key': 'WFD-2898', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings (billable)'}, {'id': 120824, 'parentkey': 'WFD-3031', 'key': 'WFD-3031', 'timeSpentSeconds': 5400, 'issuetype': 'UAT', 'summary': 'UAT2 | WFD-2879 Modify MP5 workflows to accept Kafka messages'}, {'id': 120825, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings'}, {'id': 120826, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings'}, {'id': 120827, 'parentkey': 'WFD-3031', 'key': 'WFD-3031', 'timeSpentSeconds': 4500, 'issuetype': 'UAT', 'summary': 'UAT2 | WFD-2879 Modify MP5 workflows to accept Kafka messages'}, {'id': 120828, 'parentkey': 'WFD-2454', 'key': 'WFD-2454', 'timeSpentSeconds': 2700, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2282 | Changes to LTFS Ingest process'}, {'id': 120829, 'parentkey': 'WFD-2454', 'key': 'WFD-2454', 'timeSpentSeconds': 900, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2282 | Changes to LTFS Ingest process'}, {'id': 120830, 'parentkey': 'WFD-3137', 'key': 'WFD-3222', 'timeSpentSeconds': 6300, 'issuetype': 'Sub-Task', 'summary': 'Upgrade VM to 2.1.4'}, {'id': 120831, 'parentkey': 'WFD-3137', 'key': 'WFD-3199', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': '2016 photos with collection metadata'}, {'id': 120832, 'parentkey': 'WFD-3137', 'key': 'WFD-3201', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': 'Custom Game Collection (x1 wf)'}, {'id': 120833, 'parentkey': 'WFD-3137', 'key': 'WFD-3202', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': 'Game ID Fix (x2 wf) '}, {'id': 120834, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'timeSpentSeconds': 900, 'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support'}, {'id': 120835, 'parentkey': 'WFD-3137', 'key': 'WFD-3202', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': 'Game ID Fix (x2 wf) '}, {'id': 120643, 'parentkey': 'WFD-3061', 'key': 'WFD-3070', 'timeSpentSeconds': 3480, 'issuetype': 'Sub-Task', 'summary': 'Update Clips'}, {'id': 120636, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1200, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings'}, {'id': 120637, 'parentkey': 'WFD-2432', 'key': 'WFD-2432', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Estimation'}, {'id': 120638, 'parentkey': 'WFD-2024', 'key': 'WFD-2024', 'timeSpentSeconds': 1080, 'issuetype': 'Time Tracking Task', 'summary': 'Other'}, {'id': 120639, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support'}, {'id': 120640, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120641, 'parentkey': 'WFD-3135', 'key': 'WFD-3135', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete'}, {'id': 120642, 'parentkey': 'WFD-2898', 'key': 'WFD-2898', 'timeSpentSeconds': 1200, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings (billable)'}, {'id': 120645, 'parentkey': 'WFD-3061', 'key': 'WFD-3061', 'timeSpentSeconds': 3600, 'issuetype': 'Story', 'summary': 'SCOPED(28): NHL 2.x Upgrade - INGEST'}, {'id': 120646, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 2700, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120650, 'parentkey': 'WFD-3221', 'key': 'WFD-3221', 'timeSpentSeconds': 2700, 'issuetype': 'Story', 'summary': 'NOT READY - Archive/Restore Using XenData XML API'}, {'id': 120681, 'parentkey': 'WFD-3135', 'key': 'WFD-3172', 'timeSpentSeconds': 7200, 'issuetype': 'Sub-Task', 'summary': '(.5) Test batchMetaUpdater'}, {'id': 120712, 'parentkey': 'WFD-3135', 'key': 'WFD-3173', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': '(.5) Update Delete'}, {'id': 120713, 'parentkey': 'WFD-3135', 'key': 'WFD-3174', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': '(.5) Test Delete'}, {'id': 120763, 'parentkey': 'WFD-3228', 'key': 'WFD-3228', 'timeSpentSeconds': 4500, 'issuetype': 'Story', 'summary': 'Update Panel Clip WF to set multi-picklist metadata properly'}, {'id': 120777, 'parentkey': 'WFD-3136', 'key': 'WFD-3175', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': '(.5) Update Game Collections'}, {'id': 120778, 'parentkey': 'WFD-3136', 'key': 'WFD-3177', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': '(1) Update update asset data'}, {'id': 120779, 'parentkey': 'WFD-3136', 'key': 'WFD-3178', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': '(1) Test update asset data'}, {'id': 120934, 'parentkey': 'WFD-340', 'key': 'WFD-340', 'timeSpentSeconds': 2700, 'issuetype': 'Time Tracking Task', 'summary': 'Project Management'}, {'id': 120693, 'parentkey': 'WFD-3061', 'key': 'WFD-3070', 'timeSpentSeconds': 9420, 'issuetype': 'Sub-Task', 'summary': 'Update Clips'}, {'id': 120757, 'parentkey': 'WFD-3061', 'key': 'WFD-3077', 'timeSpentSeconds': 4020, 'issuetype': 'Sub-Task', 'summary': 'Update Ongoing Image Ingest'}, {'id': 120714, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 900, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings'}, {'id': 120758, 'parentkey': 'WFD-3135', 'key': 'WFD-3135', 'timeSpentSeconds': 2700, 'issuetype': 'Story', 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete'}, {'id': 120762, 'parentkey': 'WFD-3061', 'key': 'WFD-3081', 'timeSpentSeconds': 3000, 'issuetype': 'Sub-Task', 'summary': 'Update Misc Image Ingest'}, {'id': 120836, 'parentkey': 'WFD-3137', 'key': 'WFD-3203', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': 'Get All Asset Metadata ( x1 wf) '}, {'id': 120837, 'parentkey': 'WFD-3137', 'key': 'WFD-3222', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': 'Upgrade VM to 2.1.4'}, {'id': 120838, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1800, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings'}, {'id': 120839, 'parentkey': 'WFD-3137', 'key': 'WFD-3222', 'timeSpentSeconds': 5400, 'issuetype': 'Sub-Task', 'summary': 'Upgrade VM to 2.1.4'}, {'id': 120840, 'parentkey': 'WFD-3137', 'key': 'WFD-3203', 'timeSpentSeconds': 3600, 'issuetype': 'Sub-Task', 'summary': 'Get All Asset Metadata ( x1 wf) '}, {'id': 120841, 'parentkey': 'WFD-3135', 'key': 'WFD-3135', 'timeSpentSeconds': 1800, 'issuetype': 'Story', 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete'}, {'id': 120842, 'parentkey': 'WFD-3137', 'key': 'WFD-3203', 'timeSpentSeconds': 3600, 'issuetype': 'Sub-Task', 'summary': 'Get All Asset Metadata ( x1 wf) '}, {'id': 120843, 'parentkey': 'WFD-3137', 'key': 'WFD-3204', 'timeSpentSeconds': 1800, 'issuetype': 'Sub-Task', 'summary': 'Submission Metadata (x4 wf)'}, {'id': 120844, 'parentkey': 'WFD-3137', 'key': 'WFD-3204', 'timeSpentSeconds': 8100, 'issuetype': 'Sub-Task', 'summary': 'Submission Metadata (x4 wf)'}, {'id': 120764, 'parentkey': 'WFD-3061', 'key': 'WFD-3078', 'timeSpentSeconds': 1860, 'issuetype': 'Sub-Task', 'summary': 'Update Deluxe Replacement Ingest'}, {'id': 120765, 'parentkey': 'WFD-3061', 'key': 'WFD-3079', 'timeSpentSeconds': 900, 'issuetype': 'Sub-Task', 'summary': 'Update Proxy Ingest'}, {'id': 120766, 'parentkey': 'WFD-3228', 'key': 'WFD-3228', 'timeSpentSeconds': 1800, 'issuetype': 'Story', 'summary': 'Update Panel Clip WF to set multi-picklist metadata properly'}, {'id': 120767, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 1800, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120768, 'parentkey': 'WFD-3087', 'key': 'WFD-3087', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Archive and Restore'}, {'id': 120770, 'parentkey': 'WFD-311', 'key': 'WFD-311', 'timeSpentSeconds': 1200, 'issuetype': 'Time Tracking Task', 'summary': 'Meetings'}, {'id': 120769, 'parentkey': 'WFD-3061', 'key': 'WFD-3061', 'timeSpentSeconds': 900, 'issuetype': 'Story', 'summary': 'SCOPED(28): NHL 2.x Upgrade - INGEST'}, {'id': 120771, 'parentkey': 'WFD-3135', 'key': 'WFD-3135', 'timeSpentSeconds': 600, 'issuetype': 'Story', 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete'}, {'id': 120772, 'parentkey': 'WFD-3137', 'key': 'WFD-3137', 'timeSpentSeconds': 600, 'issuetype': 'Story', 'summary': 'SCOPED(24): NHL 2.x Upgrade - Update Metadata'}, {'id': 120773, 'parentkey': 'WFD-312', 'key': 'WFD-312', 'timeSpentSeconds': 1200, 'issuetype': 'Time Tracking Task', 'summary': 'Workflow Support'}, {'id': 120863, 'parentkey': 'WFD-3230', 'key': 'WFD-3230', 'timeSpentSeconds': 3600, 'issuetype': 'Story', 'summary': 'SCOPE(12) - Repair Timelines with null or invalid Primary Track'}, {'id': 120774, 'parentkey': 'WFD-3040', 'key': 'WFD-3040', 'timeSpentSeconds': 600, 'issuetype': 'UAT', 'summary': 'UAT | WFD-2942 | Showtime | Clip Metadata Updates'}, {'id': 120775, 'parentkey': 'WFD-3135', 'key': 'WFD-3135', 'timeSpentSeconds': 1800, 'issuetype': 'Story', 'summary': 'SCOPED(8): NHL 2.x Upgrade - Add Asset to Collection, BatchMetaUpdater, and Delete'}]

    else:
        r = requests.get(url, auth=('rjohnson', 'Miter9le'))
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
    # print('JIRA mock Sub-Task data')
    # print(jira_subtask_dict)
    # print('JIRA mock Story data')
    # print(jira_dict)
    # print('tempo mock data')
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
