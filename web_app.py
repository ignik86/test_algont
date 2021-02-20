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
from log_to_db import Values,Params,Db_log
from threading import Thread
import psutil
import time

DB_CONNECT ='sqlite:///db3.db'
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
    def run(self):
        while True:
          cpu = psutil.cpu_percent(interval=5)
          logger.write_value('CPU', cpu)
          memory = psutil.virtual_memory()
          logger.write_value('Memory', memory.percent)
          

    
def create_app():

  application = Flask(__name__)

  nav.init_app(application)
  Bootstrap(application)
  application.config['SECRET_KEY'] = SECRET_KEY

  return application


app = create_app()
logger = Db_log(DB_CONNECT)

@app.route('/values',  methods=('GET', 'POST'))
def values():
    # take all params in params table
    q = logger.session.query(Params)
    params = q.all() 
    
    select_form = SelectTag()
    select_form.tag.choices = [(g.id, g.name) for g in params] # send all params  in params table to select form
    #take last hour values  for selected params 
    q = logger.session.query(Values)\
        .filter(Values.param_id == select_form.tag.data)\
        .filter(Values.timestamp <= datetime.utcnow())\
        .filter(Values.timestamp >= datetime.utcnow() - timedelta(hours=1))
    values = q.all() # send last hour values to values.html
    
    # calculate average values 
    delta1=60
    delta2=55
    average_values = {}
    show_average = False
    while delta2 >0:
      
      # take records in 5 min interval
      q = logger.session.query(Values)\
        .filter(Values.param_id == select_form.tag.data)\
        .filter(Values.timestamp <= datetime.utcnow() - timedelta(minutes=delta2))\
        .filter(Values.timestamp >= datetime.utcnow() - timedelta(minutes=delta1))
      
      record = q.all()
      
      if len(record) !=0: # check if we have values in interval
        #calculate average
        sum = 0
        for i in range(len(record)):
          sum += record[i].value
        timestamp = datetime.utcnow()- timedelta(minutes=delta2-2.5)
        average_values[timestamp] = sum/len(record) # send to values.html
        show_average = True
      #next interval
      delta1 -=5
      delta2 -=5
      
    logger.session.close()

    return render_template('values.html', 
                           values=values, 
                           tags=params, 
                           select=select_form, 
                           average_values=average_values,
                           show_average=show_average)


@app.route('/', methods=['GET'])
def main():
    return render_template('index.html')


if __name__ == "__main__": 
  
    Logging_to_db().start()
    app.run(host='0.0.0.0', port=3000, debug= False)