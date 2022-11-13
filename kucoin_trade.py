# -*- coding: utf-8 -*-
import configparser
import ccxt
import logging
import json
import os
import asyncio
from flask import request, abort,Flask


# 读取配置文件，优先读取json格式，如果没有就读取ini格式
config = {}
if os.path.exists('./config.json'):
    config = json.load(open('./config.json',encoding="UTF-8"))
elif os.path.exists('./config.ini'):
    conf = configparser.ConfigParser()
    conf.read("./config.ini", encoding="UTF-8")
    for i in dict(conf._sections):
        config[i] = {}
        for j in dict(conf._sections[i]):
            config[i][j] = conf.get(i, j)
else:
    logging.info("配置文件 config.json 不存在，程序即将退出")
    exit()

# 服务配置
apiSec = config['service']['api_sec']
listenHost = config['service']['listen_host']
listenPort = config['service']['listen_port']
debugMode = config['service']['debug_mode']
ipWhiteList = config['service']['ip_white_list'].split(",")

# 交易对
symbol = config['trading']['symbol']
amount = config['trading']['amount']
tdMode = config['trading']['td_mode']
lever = config['trading']['lever']

# 交易所API账户配置
accountConfig = {
    'apiKey': config['account']['api_key'],
    'secret': config['account']['secret'],
    'password': config['account']['password'],
    'enable_proxies': config['account']['enable_proxies'],
    'proxies': {
        'http': config['account']['proxies'],  # these proxies won't work for you, they are here for example
        'https': config['account']['proxies'],
    }
}


# CCXT初始化
exchange = ccxt.kucoin({
    'enableRateLimit': True,
    'apiKey': accountConfig['apiKey'],
    'secret': accountConfig['secret'],
    'password': accountConfig['password'],
    'verbose': False,  # for debug output
})

# 获取账户信息
def get_my_accounts():
    return exchange.fetch_accounts()

# 现货，以市场价进行买入
def trade_market_buy_order(symbol, amount, params={}):
   return exchange.create_order(symbol,'market','buy',amount,'None',params)

#现货，以市场价进行卖出
def trade_market_sell_order(symbol,amount,params={}):
    return exchange.create_order(symbol,'market','sell',amount,'None',params)

# 现货，限价买入
def trade_limit_buy_order(symbol,amount,price,params={}):
    return exchange.create_order(symbol,'limit','buy',amount,price,params)

# 现货，限价卖出
def trade_limit_sell_order(symbol,amount,price,params={}):
    return exchange.create_order(symbol,'limit','sell',amount,price,params)
    

app = Flask(__name__)

@app.before_request
def before_req():
    if request.json is None:
        abort(400)
    if request.remote_addr not in ipWhiteList:
        abort(403)
    if "apiSec" not in request.json or request.json["apiSec"] != apiSec:
        abort(401)

# 现货订单
@app.route('/spot_order', methods=['POST'])
def spot_order():
    _params = request.json
    ret = {
        "statusCode": 200,
        "msg": "操作成功"
    }
    if "apiSec" not in _params or _params["apiSec"] != apiSec:
        ret['msg'] = "Permission Denied."
        ret["statusCode"] = 201
        return ret
    if "symbol" not in _params or _params["symbol"] == '':
        ret['msg'] = "symbol参数不正确"
        ret["statusCode"] = 202
        return ret
    if "amount" not in _params or _params["amount"] == '':
        ret['msg'] = "amount参数不正确"
        ret["statusCode"] = 203
        return ret
    if "type" not in _params or _params["type"] == '':
        ret['msg'] = "type参数不正确"
        ret["statusCode"] = 204
        return ret
    match _params['side']:
        case 'buy':
            if _params['type'] == 'market':
                ret['msg'] = trade_market_buy_order(_params['symbol'],_params['amount'])
            else:
               ret['msg'] = trade_limit_buy_order(symbol = _params['symbol'],amount = _params['amount'],price=_params['price']) 
        case 'sell':
            if _params['type'] == 'limit':
                ret['msg'] = trade_limit_sell_order(symbol = _params['symbol'],amount = _params['amount'],price=_params['price'])
            else:
               ret['msg'] = trade_market_sell_order(_params['symbol'],_params['amount']) 
        case _:
            ret['msg'] = "参数side不正确"
    return ret

# 撤销所有的订单
@app.route('/cancel_all_orders',methods=['POST'])
def cancel_all_orders():
    ret = {
        "statusCode": 200,
        "msg": "操作成功"
    }
    ret['msg'] = exchange.cancel_all_orders()
    return ret




if __name__ == '__main__':
    app.run(debug=True)