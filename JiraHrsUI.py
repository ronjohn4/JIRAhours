# todo - add user authentication (against JIRA)

from flask import Flask, render_template, flash, request, make_response, session, redirect, url_for, current_app
from WFDhrs import HrsGet
import io
import csv
import logging
from datetime import datetime
import calendar

app = Flask('JIRAhrs')

logging.basicConfig(level=logging.DEBUG)

today = datetime.today()
last_search = {
    'startdate': '{0}-{1}-{2}'.format(today.year, today.month, '1'),
    'enddate': '{0}-{1}-{2}'.format(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
}
entries_parent = []
entries_child = []
total_hours = 0
hours_billable = 0
hours_nonbillable = 0

# secret_key is used for flash messages
app.config.update(dict(
    SECRET_KEY='development key'
))


@app.route('/issues/csvall/', methods=['GET'])
def issuescsvall():
    csv_list = []

    for v in entries_child:
        csv_list.append({'customer': v['customer'],
            'issuetype': v['issuetype'],
            'key': v['key'],
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


@app.route('/')
@app.route('/issues/', methods=['GET', 'POST'])
def issues():
    global entries_parent
    global entries_child
    global last_search
    global hours_billable
    global hours_nonbillable

    if request.method == 'POST':
        search = {'startdate': request.form["startdate"],
                  'enddate': request.form["enddate"]}
        logging.debug('search:' + str(search))

        last_search = search
        entries_parent, entries_child, hours_billable, hours_nonbillable = HrsGet('WFD', search['startdate'],
                                                                                  search['enddate'])

        # sort for presentation
        entries_parent = sorted(entries_parent, key=lambda k: (k['customer'] or "") + k['key'])
        entries_child = sorted(entries_child, key=lambda k: k['key'] + k['tempocomment'])
    return render_template('issues.html', entries=entries_parent, search=last_search, hours_billable=hours_billable,
                           hours_nonbillable=hours_nonbillable)


@app.route('/issues/<id>')
def issuesid(id=None):
    global entries_parent
    global entries_child

    return render_template('issue.html', parent_entry=[v for v in entries_parent if v['key'] == id],
                           child_entry=[v for v in entries_child if v['parentkey'] == id])



if __name__ == '__main__':
    app.run(debug=True, port=5001)
