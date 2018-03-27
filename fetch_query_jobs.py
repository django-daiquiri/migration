#!/usr/bin/env python

import ipaddress
import json
import uuid

from datetime import timedelta

import MySQLdb

from settings import DAIQUIRI_DATABASE
from settings import QUERY_JOB_PHASES, QUERY_JOB_TYPES, QUERY_JOB_LANGUAGE

# init fixture list (will be serialized to json at the end)
fixtures = []

# get a connection to the daiquiri database
daiquiri_connection = MySQLdb.connect(**DAIQUIRI_DATABASE)
daiquiri_cursor = daiquiri_connection.cursor()

# query all groups
daiquiri_cursor.execute('''
    SELECT id, name FROM Query_Groups
''')

groups = {}
for group_id, name in daiquiri_cursor.fetchall():
    groups[group_id] = name

# query all messages from the daiquiri database
daiquiri_cursor.execute('''
    SELECT `table`, `database`, query, user_id, status_id, type_id, ip, group_id, `time`, ip
    FROM Query_Jobs
''')

# fetch users and create fixtures for every user, profile and email address (for allauth)
for table_name, schema_name, query, user_id, status_id, type_id, ip, group_id, time, ip \
        in daiquiri_cursor.fetchall():

    job_id = str(uuid.uuid4())
    run_id = groups[group_id] if group_id else None
    job_type = QUERY_JOB_TYPES[type_id] if type_id else 'INTERFACE'
    phase = QUERY_JOB_PHASES[status_id]
    creation_time = (time - timedelta(hours=1)).isoformat() + 'Z'
    username = 'foo'

    # mask client ip for more privacy
    interface = ipaddress.IPv4Interface('%s/%i' % (ip, 16))
    client_ip = str(interface.network.network_address)

    # remove comments from query string
    query_string = '\n'.join([line for line in query.split('\n') if not line.startswith('--')])

    # create a job fixture
    fixtures.append({
        'model': 'daiquiri_jobs.job',
        'pk': job_id,
        'fields': {
            'owner': user_id,
            'client_ip': client_ip,
            'response_format': 'votable',
            'max_records': None,
            'run_id': run_id,
            'phase': phase,
            'creation_time': creation_time,
            'start_time': None,
            'end_time': None,
            'execution_duration': 0,
            'destruction_time': None,
            'error_summary': None,
            'job_type': job_type
        }
    })

    # create a queryjob fixture
    fixtures.append({
        'model': 'daiquiri_query.queryjob',
        'pk': job_id,
        'fields': {
            'schema_name': schema_name,
            'table_name': table_name,
            'query_language': QUERY_JOB_LANGUAGE,
            'query': query_string,
            'native_query': None,
            'actual_query': None,
            'queue': None,
            'nrows': None,
            'size': None,
            'metadata': '{}',
            'pid': None
        }
    })

print(json.dumps(fixtures, indent=2, sort_keys=True))
