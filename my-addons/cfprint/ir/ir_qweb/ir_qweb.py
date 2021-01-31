# -*- coding: utf-8 -*-
# 康虎软件工作室
# http://www.khcloud.net
# QQ: 360026606
# wechat: 360026606
#--------------------------

from __future__ import print_function
import ast

import re
import logging
import json

from odoo import api, models, tools, _

_logger = logging.getLogger(__name__)

"""
HTML处理工具类
"""
class HTMLHelper:
    @staticmethod
    def filter_tags_re(htmlstr):
        """
        过滤HTML中的标签， 将HTML中标签等信息去掉
        使用示例：
        if __name__=='__main__':
            s=file('Google.htm').read()
            news=filter_tags(s)
            print news

        @param htmlstr HTML字符串.
        :return:
        """
        if not isinstance (htmlstr, str):
            return htmlstr;

        # 先过滤CDATA
        re_cdata = re.compile('//<!\[CDATA\[[^>]*//\]\]>', re.I)  # 匹配CDATA
        re_script = re.compile('<\s*script[^>]*>[^<]*<\s*/\s*script\s*>', re.I)  # Script
        re_style = re.compile('<\s*style[^>]*>[^<]*<\s*/\s*style\s*>', re.I)  # style
        re_br = re.compile('<br\s*?/?>')  # 处理换行
        re_h = re.compile('</?\w+[^>]*>')  # HTML标签
        re_comment = re.compile('<!--[^>]*-->')  # HTML注释
        s = re_cdata.sub('', htmlstr)  # 去掉CDATA
        s = re_script.sub('', s)  # 去掉SCRIPT
        s = re_style.sub('', s)  # 去掉style
        s = re_br.sub('\n', s)  # 将br转换为换行
        s = re_h.sub('', s)  # 去掉HTML 标签
        s = re_comment.sub('', s)  # 去掉HTML注释
        s = s.strip();
        s = HTMLHelper.replaceCharEntity(s)  # 替换实体
        return s

    @staticmethod
    def replaceCharEntity(htmlstr):
        """
        替换常用HTML字符实体.
        使用正常的字符替换HTML中特殊的字符实体.
        你可以添加新的实体字符到CHAR_ENTITIES中,处理更多HTML字符实体.
        @param htmlstr HTML字符串.

        :return:
        """
        CHAR_ENTITIES = {'nbsp': ' ', '160': ' ',
                         'lt': '<', '60': '<',
                         'gt': '>', '62': '>',
                         'amp': '&', '38': '&',
                         'quot': '"', '34': '"',}

        re_charEntity = re.compile(r'&#?(?P<name>\w+);')
        sz = re_charEntity.search(htmlstr)
        while sz:
            entity = sz.group()  # entity全称，如&gt;
            key = sz.group('name')  # 去除&;后entity,如&gt;为gt
            try:
                htmlstr = re_charEntity.sub(CHAR_ENTITIES[key], htmlstr, 1)
                sz = re_charEntity.search(htmlstr)
            except KeyError:
                # 以空串代替
                htmlstr = re_charEntity.sub('', htmlstr, 1)
                sz = re_charEntity.search(htmlstr)
        return htmlstr

    @staticmethod
    def repalce(s, re_exp, repl_string):
        return re_exp.sub(repl_string, s)

    @staticmethod
    def strip_tags_parser(self, html):
        """
        去除文本中的HTML标签.用到了HTMLParser
        使用示例：
        str_text=strip_tags("<font color=red>hello</font>")

        :return: String
        """
        from html.parser import HTMLParser
        html = html.strip('\n')
        html = html.strip('\t')
        html = html.strip(' ')
        html = html.strip()

        result = []
        parser = HTMLParser()
        parser.handle_data = result.append
        parser.feed(html)
        parser.close()
        return '$'.join(result)

    @staticmethod
    def strip_tags_simple(self, html):
        """
        用正则表达式去除HTML
        :param html:
        :return:
        """
        TAG_RE = re.compile(r'(<[^>]+>)|[\r\n]')
        return TAG_RE.sub('', html).strip()

class CFIrQWeb(models.AbstractModel):
    """ 继承IrQWeb对象，以实现删除字段值中的HTML标签和前后空格
    """
    _inherit = 'ir.qweb'

    def _get_field(self, record, field_name, expression, tagName, field_options, options, values):
        """
        判断是否指定了data_type=raw，如果已经指定则移除字段值中的HTML标签、换行和前后空格
        """
        data = super(CFIrQWeb, self)._get_field(record, field_name, expression, tagName, field_options, options, values)

        attributes = data[0]
        content = data[1]

        data_type = field_options.get("data_type", False)
        if data_type and isinstance(data_type, str) and data_type.lower() == "raw":
            content = HTMLHelper.filter_tags_re(content)

        return attributes, content, data[2]

    def __is_show_html(self, el, options):
        """
        根据data_type判断是否要显示HTML
        """
        show_tag = True  # 是否显示HTML标签
        data_type = None

        if el.nsmap and "data_type" in el.nsmap:
            data_type = el.nsmap['data_type'].lower()
        # if not data_type and options.has_key('data_type'):
        if not data_type and "data_type" in options:
            data_type = options['data_type'].lower()

        if data_type == "raw" or data_type == "json":
            show_tag = False  # 如果指定数据类型是raw或json，则不显示HTML标签

        return show_tag

    def _compile_tag(self, el, content, options, attr_already_created=False):
        """
        继承base/ir/ir_qweb/qweb.py中_compile_tag方法，根据条件判断是否要移除HTML
        """

        if not self.__is_show_html(el, options):
            body = []
            body.extend(content)
            return body
        else:
            body = super(CFIrQWeb, self)._compile_tag(el, content, options, attr_already_created)
            return body

    # for backward compatibility to remove after v10
    def _get_widget_options(self, el, directive_type):
        """
        仿照 base/ir/ir_qweb/ir_qweb.py中_compile_widget_options方法，
        从el.attrib中获取“t-options”和“t-widget名称-options”的值，但不从el.attrib移除，
        以便于odoo其他代码还能正常执行。
        """
        # 依照base/ir/ir_qweb/qweb.py中的_compile_widget_options方法从el.attrib取t-options值，取出但不移除
        field_options = None
        if hasattr(el.attrib, 't-options'):
            field_options = el.attrib['t-options']

        # 仿照 base/ir/ir_qweb/ir_qweb.py中_compile_widget_options方法从从el.attrib中取“t-widget名称-options”值,
        # 取出但不移除
        if ('t-%s-options' % directive_type) in el.attrib:
            if tools.config['dev_mode']:
                _logger.warning("Use new syntax t-options instead of t-%s-options" % directive_type)
            if not field_options:
                field_options = el.attrib['t-%s-options' % directive_type]

        return field_options
    # end backward


    def _compile_directive_field(self, el, options):
        """
        继承base/ir/ir_qweb/qweb/py中_compile_directive_field方法，用以获取t-options或t-field-options属性，
        并塞进options以便于_compile_tag中根据这些属性进行相应处理（典型的就是输出不带HTML的内容）
        """
        field_options = self._get_widget_options(el, 'field')
        if field_options:
            for k, v in json.loads(field_options).items():
                options[k] = v

        return super(CFIrQWeb, self)._compile_directive_field(el, options)
