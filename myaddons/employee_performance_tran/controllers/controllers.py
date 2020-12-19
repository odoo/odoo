# -*- coding: utf-8 -*-
# from odoo import http


# class EmployeePerformanceTran(http.Controller):
#     @http.route('/employee_performance_tran/employee_performance_tran/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/employee_performance_tran/employee_performance_tran/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('employee_performance_tran.listing', {
#             'root': '/employee_performance_tran/employee_performance_tran',
#             'objects': http.request.env['employee_performance_tran.employee_performance_tran'].search([]),
#         })

#     @http.route('/employee_performance_tran/employee_performance_tran/objects/<model("employee_performance_tran.employee_performance_tran"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('employee_performance_tran.object', {
#             'object': obj
#         })
