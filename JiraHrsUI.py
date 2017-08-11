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

# secret_key is used for flash messages
app.config.update(dict(
    SECRET_KEY='development key'
))


from functools import wraps
from flask import request, Response


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'admin' and password == 'secret2'

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated



@app.route('/issues/csv/', methods=['GET'])
@requires_auth
def issuescsv():
    global entries_child

    # todo - test for empty file, display an alert

    print('entries_child - csv')
    print(entries_child)

    keys = entries_child[0].keys()

    output = io.StringIO()
    dict_writer = csv.DictWriter(output, keys)
    dict_writer.writeheader()
    dict_writer.writerows(entries_child)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename={0}'. \
        format('WFDtime{0}.csv'.format(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')))
    response.mimetype = 'text/csv'

    return response



@app.route('/')
@app.route('/issues/', methods=['GET', 'POST'])
@requires_auth
def issues():
    global entries_parent
    global entries_child
    global last_search
    global total_hours

    if request.method == 'POST':
        search = {'startdate': request.form["startdate"],
                  'enddate': request.form["enddate"]}
        logging.debug('search:' + str(search))

        last_search = search
        entries_parent, entries_child, total_hours = HrsGet('WFD', search['startdate'], search['enddate'])

        # sort for presentation
        entries_parent = sorted(entries_parent, key=lambda k: (k['customer'] or "") + k['key'])
        # entries_child = sorted(entries_child, key=lambda k: k['parentkey'] + k['key'])

    return render_template('issues.html', entries=entries_parent, search=last_search, total_hours=total_hours)



@app.route('/issues/<id>')
@requires_auth
def issuesid(id=None):
    global entries_parent
    global entries_child

    # print('id:', id)
    # print('parent:', entries_parent)
    # print('child:', entries_child)
    # print('parent', [v for v in entries_parent if v['key'] == id])
    # print('child', [v for v in entries_child if v['parentkey'] == id])
    return render_template('issue.html', parent_entry=[v for v in entries_parent if v['key'] == id],
                           child_entry=[v for v in entries_child if v['parentkey'] == id])



if __name__ == '__main__':
    app.run(debug=True, port=5001)
