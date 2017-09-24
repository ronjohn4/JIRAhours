# JIRAhours
This sample project show some best practices to use when integrating JIRA and Tempo data in a Python/Flask/requests driven app.

Using the code is straight forward:
1. Clone the repo
2. Build your virtual environment using:
    pip3 install –r requirements.txt
3. python JIRAui.py

Below is the post introducing this sample.

# Tempo Cloud API Released
Tempo Cloud API was officially released on 9/21. Here I cover my initial tests with integrating Tempo and JIRA data.  Included are a handful of lessons learned, tricks and the Python code.

This code sample shows the integration of JIRA and Tempo data.  Your requirements determine which source is the driver.  

If you are looking at specific issue data (either by Epic, Issue, Project, etc) you perform your JIRA query first and then pull the associated Tempo hours for those issues in the JIRA result.

If you want all the time in a date range, first query Tempo for the time then pull the associated issue data from JIRA.  This sample takes this approach.

First, pull the Tempo data by date range.  A secondary Tempo filter can be added as appropriate.  Your API call querying for the date range 2017-09-01 to 2017-09-15 for project XYZ will looks something like this:

https://yourdomain.atlassian.net/rest/tempo-timesheets/3/worklogs?dateFrom=2017-09-01&dateTo=2017-09-15&projectKey=XYZ
Of course, you need to use your domain.

The tricky part comes when pulling the associated issue data from JIRA.  We need to limit the records in our query result as much as possible; set the max records return in the query; then manually page when the results are over the max record limit.

To limit the JIRA records in the query result to only the is issue in focus, use the ‘Key in (comma separated issue key list)’ format.  Iterate through the list of Tempo entries, build a list of JIRA keys, reduce the list (remember there can be multiple time entries for a single issue), create a comma separated list and use this to query JIRA.  

Supporting the 100 max is easy.  Simply set the JIRA maxResults=100 on your query.  More than 100 gave unpredictable results in my testing.  Not setting maxResults gives the default of 50. Your API call may look something like this:

https://yourdomain.atlassian.net/rest/api/2/search?jql=key%20in%20({0})&expand=names&fields=key,summary,issuetype,parent,status&maxResults=100
Again, you need to use your domain.


Manually paging the results is easier than you think.  At this point remember that your list of keys may be greater than 100 AND you set the max results to 100.  To get all the keys in your list, remove each key from the original list when processing the results.  Then put a ‘while len(list) > 0’ around the whole works and you are now paging.  

This snippet of pseudo code pulls it all together and should give you the general idea:

key_list = buildJIRAlist()  #based on your Tempo results
While len(key_list) > 0:
	results_list = GetJIRAkeys(key_list)
	for entry in results_list:
		process(entry)
		key_list.discard(entry.key)


For authentication, I used basic auth before the Tempo API was officially released.  The new API doesn’t mention basic auth but suggests Token auth.  I retested basic auth and all seems good.  If you find otherwise please let me know and I’ll update the sample code.

The email announcing the API release has a couple helpful links to additional information, they are:

API Docs - https://tempo-io.github.io/tempo-mtm-docs/

“Managing access control for integrations” - https://support.tempo.io/hc/en-us/articles/115011300208-Managing-access-control-for-integrations

