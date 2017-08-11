#!/Users/rjohnson/Projects/jirahours/venv/bin/python
"""
JIRA Hours.

Usage:
  jirahrs.py
  jirahrs.py <project> <from> <to>

Options:
  -h --help     Show this screen

"""
import sys
from docopt import docopt
import csv
import datetime
import WFDhrs


def main():
    project = arguments['<project>']
    from_date = arguments['<from>']
    to_date = arguments['<to>']

    # todo - validate project is valid
    try:
        datetime.datetime.strptime(from_date, '%Y-%m-%d')
    except ValueError:
        print("Incorrect 'from' date format, should be YYYY-MM-DD")
        exit(0)

    try:
        datetime.datetime.strptime(to_date, '%Y-%m-%d')
    except ValueError:
        print("Incorrect 'to' date format, should be YYYY-MM-DD")
        exit(0)

    if datetime.datetime.strptime(to_date, '%Y-%m-%d') < datetime.datetime.strptime(from_date, '%Y-%m-%d'):
        print("'to' date should be after 'from' date")
        exit(0)

    # print('project: {0}, from: {1}, to: {2}'.format(project, from_date, to_date))

    list_parent, list_child = WFDhrs.HrsGet(project, from_date, to_date)
    # list_parent = [{'key1': 'value1', 'key2': 'value2'},{'key1': 'value3', 'key2': 'value4'}]
    # list_child = [{'key1': 'value5', 'key2': 'value6'},{'key1': 'value7', 'key2': 'value8'}]


    w = csv.DictWriter(sys.stdout, list_parent[0].keys(), quoting=csv.QUOTE_ALL)
    w.writeheader()
    w.writerows(list_parent+list_child)



if __name__ == '__main__':
    arguments = docopt(__doc__, version='JIRA Hours 1.0')
    # print('arguments:', arguments)
    main()
