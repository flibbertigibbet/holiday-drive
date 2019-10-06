#!/bin/bash

./manage.py sqlclear holiday | ./manage.py dbshell
./manage.py syncdb

