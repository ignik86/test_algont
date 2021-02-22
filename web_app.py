import os
from datetime import datetime, timedelta

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired
from flask_bootstrap import Bootstrap
from flask_nav import Nav
from flask_nav.elements import *

from flask import Flask, render_template, redirect, request, url_for
from log_to_db import Db_log
from threading import Thread
import psutil
import time

DB_CONNECT = 'sqlite:///db3.db'
nav = Nav()
SECRET_KEY = os.urandom(32)


@nav.navigation()
def mynavbar():
    return Navbar(
        'Test App',
        View('Home', 'main'),
        View('Values', 'values'),

    )


class SelectTag(FlaskForm):
    tag = SelectField(u'Параметр', validators=[DataRequired()])


class Logging_to_db(Thread):
    """
    Thread for write values in DB
    """

    def run(self):
        while True:
            cpu = psutil.cpu_percent(interval=5)
            memory = psutil.virtual_memory()
            try:
                logger.write_value('CPU', cpu)
                logger.write_value('Memory', memory.percent)
                logger.write_value('Memory in use', round(memory.used/(1024*1024)))
            except Exception as e:
                print(e)
            logger.session.close()


def create_app():
    application = Flask(__name__)

    nav.init_app(application)
    Bootstrap(application)
    application.config['SECRET_KEY'] = SECRET_KEY

    return application


app = create_app()
logger = Db_log(DB_CONNECT)


@app.route('/values', methods=('GET', 'POST'))
def values():
    # take all params in params table
    params = logger.take_params()

    select_form = SelectTag()
    select_form.tag.choices = [(g.id, g.name) for g in params]  # send all params  in params table to select form
    current_time = datetime.now()
    # take last hour values  for selected params

    records = logger.read_value(select_form.tag.data,
                                current_time - timedelta(hours=1),
                                current_time)  # send last hour values to values.html

    name = ' '
    show_chart = False # flag for chart visualisation
    if select_form.validate_on_submit():
        show_chart = True
        try:
            name = logger.get_parameter_name(select_form.tag.data)  # send parameter name to values.html
        except Exception as e:
            print(e)

    # calculate average values 
    delta1 = 60
    delta2 = 55
    average_values = {}
    while delta2 >= 0:
        average_records = []
        start_interval = current_time - timedelta(minutes=delta1)
        end_interval = current_time - timedelta(minutes=delta2)
        for record in records:
            if (record.timestamp >= start_interval) and (record.timestamp <= end_interval):
                average_records.append(record)
        if len(average_records) != 0:  # check if we have values in interval
            # calculate average
            values_sum = 0
            for i in range(len(average_records)):
                values_sum += average_records[i].value
            timestamp = start_interval + timedelta(minutes=2.5)
            average_values[timestamp] = values_sum / len(average_records)  # send to values.html
        # next interval
        delta1 -= 5
        delta2 -= 5

    logger.session.close()

    return render_template('values.html',
                           values=records,
                           tags=params,
                           select=select_form,
                           average_values=average_values,
                           show_chart=show_chart,
                           name=name)


@app.route('/', methods=['GET'])
def main():
    return render_template('index.html')


if __name__ == "__main__":
    Logging_to_db().start()
    app.run(host='127.0.0.1', port=5000, debug=False)
