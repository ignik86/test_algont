from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import orm
from sqlalchemy import exc
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

DB_CONNECT ='sqlite:///test_db.db'
nav = Nav()
SECRET_KEY = os.urandom(32)

@nav.navigation()
def mynavbar():
    return Navbar(
        'Test App',
        View('Home', 'main'),
        View('Values', 'values'),
       
    )

class Values(object):
    def __init__(self, param_id, value, timestamp):
        self.param_id = param_id
        self.value = value
        self.timestamp = timestamp
    def __repr__(self):
        return "Value('%s')" % (self.value)


class Params(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "Params('%s')" % (self.name)
      
class SelectTag(FlaskForm):
    #tag = SelectField(u'Параметр', coerce=int)
    tag = SelectField(u'Параметр', validators=[DataRequired()])
    #date_from = DateField('Начало:', validators=[DataRequired()])
    
    
def create_app():

  application = Flask(__name__)

  nav.init_app(application)
  Bootstrap(application)
  application.config['SECRET_KEY'] = SECRET_KEY

  return application


app = create_app()
engine = create_engine(DB_CONNECT, echo=False)
meta = MetaData(bind=engine, reflect=True)
orm.Mapper(Values, meta.tables['values'])
orm.Mapper(Params, meta.tables['params'])


@app.route('/values',  methods=('GET', 'POST'))
def values():

    session = orm.Session(bind=engine)
    q = session.query(Params)
    params = q.all()
    
    select_form = SelectTag()
    select_form.tag.choices = [(g.id, g.name) for g in params]
    q = session.query(Values)\
        .filter(Values.param_id == select_form.tag.data)\
        .filter(Values.timestamp <= datetime.utcnow())\
        .filter(Values.timestamp >= datetime.utcnow() - timedelta(hours=1))
    values = q.all()
    
    # calculate average values 
    delta1=60
    delta2=55
    average_values = {}
    
    while delta2 >0:
      # take records in 5 min interval
      q = session.query(Values)\
        .filter(Values.param_id == select_form.tag.data)\
        .filter(Values.timestamp <= datetime.utcnow()- timedelta(minutes=delta2))\
        .filter(Values.timestamp >= datetime.utcnow() - timedelta(minutes=delta1))
      
      record = q.all()
      
      if len(record) !=0: # check if we have values in interval
        sum = 0
        for i in range(len(record)):
          sum += record[i].value
        timestamp = datetime.utcnow()- timedelta(minutes=delta2-2.5)
        average_values[timestamp] = sum/len(record)
      delta1 -=5
      delta2 -=5
      
    session.close()

    return render_template('values.html', values=values, tags=params, select=select_form, average_values=average_values)


@app.route('/', methods=['GET'])
def main():
    return render_template('index.html')
    
if __name__ == "__main__":  
    app.run(host='0.0.0.0', port=3000, debug= True)