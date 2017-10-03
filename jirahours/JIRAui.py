import calendar
import csv
import io
import logging
from datetime import datetime
from functools import wraps

import dateutil.parser  # for python3 use   pip3 install python-dateutil
from flask import Flask, render_template, request, make_response, redirect, url_for, session

from jirahours.JIRAhandlerhours import JIRAhandlerhours

JIRA_BASE_URL = 'https://levelsbeyond.atlassian.net'
app = Flask('JIRAhrs')
JiraHandle = JIRAhandlerhours(JIRA_BASE_URL)

# secret_key is used for flash messages
app.config.update(dict(
    SECRET_KEY='development key goes here, should be complex'
))

today = datetime.today()
last_search = {
    'startdate': '{0}-{1}-{2}'.format(today.year, today.month, '1'),
    'enddate': '{0}-{1}-{2}'.format(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
}
hours = {
    'billable': 0,
    'nonbillable': 0
}
entries_parent = []
entries_child = []

logging.basicConfig(level=logging.DEBUG)

# decorator used to secure Flask routes
def authenticated_resource(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if JiraHandle.is_auth():
            return f(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for('login'))
    return decorated

@app.route('/')
@app.route('/issues/', methods=['GET', 'POST'])
@authenticated_resource
def issues():
    global entries_parent
    global entries_child
    global last_search
    global hours

    if request.method == 'POST':
        search = {'startdate': request.form["startdate"],
                  'enddate': request.form["enddate"]}
        logging.debug('last_search:' + str(last_search) + ' - search:' + str(search))

        last_search = search
        entries_parent, entries_child, hours = JiraHandle.HrsGet('WFD', search['startdate'], search['enddate'])

        # sort for presentation
        entries_parent = sorted(entries_parent, key=lambda k: (k['customer'] or "") + k['key'])
        entries_child = sorted(entries_child, key=lambda k: k['key'] + k['tempocomment'])
    return render_template('issues.html', entries=entries_parent, search=last_search, hours=hours)

@app.route('/issues/csvall/', methods=['GET'])
@authenticated_resource
def issuescsvall():
    csv_list = []

    for v in entries_child:
        d = dateutil.parser.parse(v['dateCreated'])
        csv_list.append({'customer': v['customer'],
                        'issuetype': v['issuetype'],
                        'key': v['key'],
                        'author': v['author'],
                        'dateCreated': d.strftime('%m/%d/%Y %H:%M'),
                        'hours': '{0:0.2f}'.format(v['timeSpentSeconds'] / 3600),
                        'summary': v['summary'],''
                        'tempocomment': v['tempocomment']})

    keys = csv_list[0].keys()
    output = io.StringIO()
    dict_writer = csv.DictWriter(output, keys)
    dict_writer.writeheader()
    dict_writer.writerows(csv_list)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename={0}'. \
        format('WFDtime{0}.csv'.format(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')))
    response.mimetype = 'text/csv'

    return response

@app.route('/issues/csv/', methods=['GET'])
@authenticated_resource
def issuescsv():
    csv_list = []

    for v in entries_parent:
        csv_list.append({'customer': v['customer'],
            'issuetype': v['issuetype'],
            'key': v['key'],
            'hours': '{0:0.2f}'.format(v['totaltimeSpentSeconds'] / 3600),
            'summary': v['summary'],''
            'tempocomment': None})

    keys = csv_list[0].keys()
    output = io.StringIO()
    dict_writer = csv.DictWriter(output, keys)
    dict_writer.writeheader()
    dict_writer.writerows(csv_list)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename={0}'. \
        format('WFDtime{0}.csv'.format(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')))
    response.mimetype = 'text/csv'

    return response

@app.route('/issues/<id>')
@authenticated_resource
def issuesid(id=None):
    return render_template('issue.html', parent_entry=[v for v in entries_parent if v['key'] == id],
                           child_entry=[v for v in entries_child if v['parentkey'] == id])

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if JiraHandle.auth(session, (request.form['username'], request.form['password'])):
            return redirect(session["wants_url"])
        else:
            error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    JiraHandle.logout(session)
    return redirect(url_for('issues'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)
