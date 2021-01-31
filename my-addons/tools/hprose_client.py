# -*- coding: utf-8 -*-
import telnetlib
import hprose
import json
import os

class OdooHproseClient(object):

    def __init__(self):
        self.client = None
        self.base_url = None

    def create_http_client(self, address, url):
        """
        创建HTTP客户端连接
        """
        self.base_url = 'http://' + address + url
        print('Creating Session : %s' % self.base_url)
        self.client = hprose.HproseHttpClient(self.base_url)

    def set_header(self, key, value):
        """
        设置连接头
        """
        print('Set Header : { "%s": "%s" }' % (key, value))
        self.client.setHeader(key, value)

    def set_parameter(self, *args):
        """
        设置参数值
        """
        arg_list = list()
        for arg in args:
            if isinstance(arg, str):
                try:
                    arg = eval(arg)
                except Exception as e:
                    logger.error(e)
            arg_list.append(arg)
        print('Set Parameter : %s' % str(arg_list))
        return arg_list

    def invoke_method(self, method, args):
        """
        调用方法
        """
        result = {
            'type': None,
            'msg': None,
            'value': None
        }
        print('Invoke Method : method={0}, args={1}'.format(method, args))
        ret = self.client.invoke(method, args)
        result['type'] = ret.types
        result['msg'] = ret.msg
        result['value'] = ret.value
        return json.dumps(result, ensure_ascii=False)
