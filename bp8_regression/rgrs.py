from flask import Blueprint, render_template, request, session, g
from flask import current_app
from fbprophet import Prophet
from datetime import datetime, timedelta
import os
import pandas as pd
import pandas_datareader as pdr
import numpy as np
from my_util.weather import get_weather
from sklearn.linear_model import LinearRegression

rgrs_bp = Blueprint('rgrs_bp', __name__)

def get_weather_main():
    ''' weather = None
    try:
        weather = session['weather']
    except:
        current_app.logger.info("get new weather info")
        weather = get_weather()
        session['weather'] = weather
        session.permanent = True
        current_app.permanent_session_lifetime = timedelta(minutes=60) '''
    weather = get_weather()
    return weather

@rgrs_bp.route('/iris', methods=['GET', 'POST'])
def iris():
    menu = {'ho':0, 'da':0, 'ml':10, 
            'se':0, 'co':0, 'cg':0, 'cr':0, 'wc':0,
            'cf':0, 'ac':0, 're':1, 'cu':0}
    if request.method == 'GET':
        return render_template('regression/iris.html', menu=menu, weather=get_weather())
    else:
        index = int(request.form['index'])
        feature_name = request.form['feature']
        column_dict = {'sl':'Sepal length', 'sw':'Sepal width', 
                        'pl':'Petal length', 'pw':'Petal width', 
                        'species':['Setosa', 'Versicolor', 'Virginica']}
        column_list = list(column_dict.keys())

        df = pd.read_csv('static/data/iris_train.csv')
        df.columns = column_list
        X = df.drop(columns=feature_name, axis=1).values
        y = df[feature_name].values

        lr = LinearRegression()
        lr.fit(X, y)
        weight, bias = lr.coef_, lr.intercept_

        df_test = pd.read_csv('static/data/iris_test.csv')
        df_test.columns = column_list
        X_test = df_test.drop(columns=feature_name, axis=1).values[index]
        pred_value = np.dot(X_test, weight.T) + bias

        x_test = list(df_test.iloc[index,:-1].values)
        x_test.append(column_dict['species'][int(df_test.iloc[index,-1])])
        org = dict(zip(column_list, x_test))
        pred = dict(zip(column_list[:-1], [0,0,0,0]))
        pred[feature_name] = np.round(pred_value, 2)
        return render_template('regression/iris_res.html', menu=menu, weather=get_weather(),
                                index=index, org=org, pred=pred, feature=column_dict[feature_name])

kospi_dict, kosdaq_dict, nyse_dict, nasdaq_dict = {}, {}, {}, {}
@rgrs_bp.before_app_first_request
def before_app_first_request():
    kospi = pd.read_csv('./static/data/KOSPI.csv', dtype={'종목코드': str})
    for i in kospi.index:
        kospi_dict[kospi['종목코드'][i]] = kospi['기업명'][i]
    kosdaq = pd.read_csv('./static/data/KOSDAQ.csv', dtype={'종목코드': str})
    for i in kosdaq.index:
        kosdaq_dict[kosdaq['종목코드'][i]] = kosdaq['기업명'][i]
    nyse = pd.read_excel('./static/data/NYSE.xlsx', dtype={'Ticker': str})
    for i in nyse.index:
        nyse_dict[nyse['Ticker'][i]] = nyse['Company'][i]
    nasdaq = pd.read_excel('./static/data/NASDAQ.xlsx', dtype={'Ticker': str})
    for i in nasdaq.index:
        nasdaq_dict[nasdaq['Ticker'][i]] = nasdaq['Company'][i]

@rgrs_bp.route('/stock', methods=['GET', 'POST'])
def stock():
    menu = {'ho':0, 'da':0, 'ml':10, 
            'se':0, 'co':0, 'cg':0, 'cr':0, 'wc':0,
            'cf':0, 'ac':0, 're':1, 'cu':0}
    if request.method == 'GET':
        return render_template('regression/stock.html', menu=menu, weather=get_weather(),
                                kospi=kospi_dict, kosdaq=kosdaq_dict, 
                                nyse=nyse_dict, nasdaq=nasdaq_dict)
    else:
        market = request.form['market']
        if market == 'KS':
            code = request.form['kospi_code']
            company = kospi_dict[code]
            code += '.KS'
        elif market == 'KQ':
            code = request.form['kosdaq_code']
            company = kosdaq_dict[code]
            code += '.KQ'
        elif market == 'NY':
            code = request.form['nyse_code']
            company = nyse_dict[code]
        else:
            code = request.form['nasdaq_code']
            company = nasdaq_dict[code]
        learn_period = int(request.form['learn'])
        pred_period = int(request.form['pred'])
        current_app.logger.debug(f'{market}, {code}, {learn_period}, {pred_period}')

        today = datetime.now()
        start_learn = today - timedelta(days=learn_period*365)
        end_learn = today - timedelta(days=1)

        stock_data = pdr.DataReader(code, data_source='yahoo', start=start_learn, end=end_learn)
        current_app.logger.info(f"get stock data: {company}({code})")
        df = pd.DataFrame({'ds': stock_data.index, 'y': stock_data.Close})
        df.reset_index(inplace=True)
        try:
            del df['Date']
        except:
            current_app.logger.error('Date error')

        model = Prophet(daily_seasonality=True)
        model.fit(df)
        future = model.make_future_dataframe(periods=pred_period)
        forecast = model.predict(future)

        fig = model.plot(forecast);
        img_file = os.path.join(current_app.root_path, 'static/img/stock.png')
        fig.savefig(img_file)
        mtime = int(os.stat(img_file).st_mtime)

        return render_template('regression/stock_res.html', menu=menu, weather=get_weather_main(), 
                                mtime=mtime, company=company, code=code)