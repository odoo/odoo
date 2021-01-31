# -*- coding: utf-8 -*-
# 康虎软件工作室
# http://www.khcloud.net
# QQ: 360026606
# wechat: 360026606
#--------------------------


from odoo import http

# class CfReportDesigner(http.Controller):
#     @http.route('/cf_report_designer/cf_report_designer/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cf_report_designer/cf_report_designer/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cf_report_designer.listing', {
#             'root': '/cf_report_designer/cf_report_designer',
#             'objects': http.request.env['cf_report_designer.cf_report_designer'].search([]),
#         })

#     @http.route('/cf_report_designer/cf_report_designer/objects/<model("cf_report_designer.cf_report_designer"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cf_report_designer.object', {
#             'object': obj
#         })