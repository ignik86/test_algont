import os
from datetime import datetime, timedelta
import time

from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import DataRequired
from flask_bootstrap import Bootstrap
from flask_nav import Nav
from flask_nav.elements import *

from flask import Flask, render_template
from log_to_db import Db_log, Values
from threading import Thread
import psutil
from flask_socketio import SocketIO, emit

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
                logger.write_value('Memory percent', memory.percent)
                logger.write_value('Memory in use', round(memory.used/(1024*1024)))
            except Exception as e:
                print(e)
            logger.session.close()
            socketio.emit('give_id')
        

class Socket_send(Thread):
    def run(self):
      while True:
        
        time.sleep(5)
        
        
def create_app():
    application = Flask(__name__)

    nav.init_app(application)
    Bootstrap(application)
    application.config['SECRET_KEY'] = SECRET_KEY

    return application


app = create_app()
socketio = SocketIO(app)
logger = Db_log(DB_CONNECT)
id_param = 0

@app.route('/values', methods=('GET', 'POST'))
def values():

    params = logger.take_params()  # take all params in params table

    select_form = SelectTag()  # create select form
    select_form.tag.choices = [(g.id, g.name) for g in params]  # send all params  in params table to select form
    
    # init variables
    current_time = datetime.now()
    name = ' '  # parameter name to values.html
    show_chart = False  # flag for showing chart visualisation
    records = [Values(0, 0, datetime.now())]  # create empty records if no choice
    
    
    if select_form.validate_on_submit():  # if submit
        id_param = select_form.tag.data
        try:
            # take last hour values  for selected params
            records = logger.read_value(select_form.tag.data,
                                        current_time - timedelta(hours=1),
                                        current_time)  # send last hour values to values.html
            name = logger.get_parameter_name(select_form.tag.data)  # send parameter name to values.html
            show_chart = True
        except Exception as e:
            print(e)
            show_chart = False

    # calculate average values
    delta1 = 60  # first start_interval:  current time minus 60 minutes
    delta2 = 55  # first end_interval: current time minus 55 minutes
    average_values = {}  # create empty tuple for average values in 5 minutes intervals
    while delta2 >= 0:
        average_records = []  # create empty list to save records in current interval
        start_interval = current_time - timedelta(minutes=delta1)
        end_interval = current_time - timedelta(minutes=delta2)
        for record in records:
            # take records in current interval
            if (record.timestamp >= start_interval) and (record.timestamp <= end_interval):
                average_records.append(record)
        if len(average_records) != 0:  # check if we have values in interval
            # calculate average
            values_sum = 0
            for i in range(len(average_records)):
                values_sum += average_records[i].value
            timestamp = start_interval + timedelta(minutes=2.5)  # timestamp at the middle of interval
            average_values[timestamp] = round(values_sum / len(average_records), 2)  # save to send to
            # values.html
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
  
  
@socketio.on('connect')
def test_connect():
    print('¯\_(ツ)_/¯-conneted')
    emit('my response', {'data': 'Connected'})

    
@socketio.on('response_id')
def get_id(message):
  
   print('¯\_(ツ)_/¯-id')


if __name__ == "__main__":
    Logging_to_db().start()
    #Socket_send().start()
    socketio.run(app, host='0.0.0.0', port=3000, debug=False)
