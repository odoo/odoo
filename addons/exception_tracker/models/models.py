# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import threading
from collections import deque

class NLineHandler(logging.StreamHandler):

    def __init__(self, max_size):
        logging.StreamHandler.__init__(self)
        self.max_size = max_size
        self.lines_per_threads = {}

    def emit(self, record):
        msg = self.format(record)
        current_thread_id = threading.current_thread().ident

        if current_thread_id in self.lines_per_threads:
            self.lines_per_threads[current_thread_id].append(msg)
        else:
            self.lines_per_threads[current_thread_id] = deque([msg], maxlen=self.max_size)

    def get_logs(self):
        current_thread_id = threading.current_thread().ident
        if not current_thread_id in self.lines_per_threads:
            return list()
        return list(self.lines_per_threads[current_thread_id])
        
handler = NLineHandler(10)
logger = logging.getLogger()
logger.addHandler(handler)

class Exception(models.Model):
    _name = 'exception_tracker.exception'
    _description = 'exception_tracker.exception'
    _inherit = ['mail.thread']
    
    name = fields.Char(readonly=True)
    message = fields.Text(readonly=True)
    traceback = fields.Text(readonly=True)
    user_context = fields.Text(readonly=True)
    action_context = fields.Text(readonly=True)
    logs = fields.Text(readonly=True)
    source = fields.Char(readonly=True)
    notes = fields.Html()

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val["logs"] = "\n".join(self._get_logs())
        return super(Exception, self).create(vals_list)

    def _get_logs(self):
        for h in logger.handlers:
            if isinstance(h, NLineHandler):
                return h.get_logs()
