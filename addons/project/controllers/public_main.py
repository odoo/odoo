# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .public_project import PublicProject
from odoo import api, http
from odoo.addons.web.controllers.main import Action, DataSet
from odoo.addons.mail.controllers.main import MailController
from odoo.http import request


class PublicAction(Action, PublicProject):

    @http.route('/embed/project/action/load', type='json', auth="public")
    def public_load_action(self, **kwargs):
        return self._check_and_perform('load_action', access_info=kwargs.pop('access_info', None), **kwargs)


class PublicDataSet(DataSet, PublicProject):

    @http.route('/embed/project/dataset/call', type='json', auth="public")
    def public_call(self, **kwargs):
        """After checking permissions, call call() in order to call a given method
        of a given model.

        call() is a shorthand for call_kw without keyword arguments: it passes
        an empty dict to _call_kw().

        Use within a project:
        - Read a template (only used by colorpicker)

        :param kwargs: Contains the method, the model and any other keyword
                       arguments required by the call() method of DataSet.
        :return: (any) The result of Dataset.call
        """
        return self._check_and_perform('call', access_info=kwargs.pop('access_info', None), **kwargs)

    @http.route('/embed/project/dataset/call_button', type='json', auth="public")
    def public_call_button(self, **kwargs):
        """After checking permissions, call call_button() in order to call a given method of a given model.
        call_button() is a shorthand for call but for actions: it passes an empty dict to _call_kw() then
        "cleans" the response with action info.

        Use within a project:
        - None found

        :param kwargs: Contains the method, the model and any other keyword
                       arguments required by the call_button() method of
                       DataSet.
        :return: (any) The result of Dataset.call_button
        """
        return self._check_and_perform('call_button', access_info=kwargs.pop('access_info', None), **kwargs)

    @http.route(['/embed/project/dataset/call_kw',
                 '/embed/project/dataset/call_kw/<path:path>'], type='json', auth="public")
    def public_call_kw(self, **kwargs):
        """After checking permissions, call call_kw() in order to call a given method of a given model.
        Most dataset CRUD operations go through this route.

        Unexhaustive use within a project:
            (- K = on project view (kanban)
             - F = on task view (form)
             - C = on click create task
             - S = on click save)
        - KF    read: Read fields of a record
        - KF    search_read: Get the recordsets data
        - F     name_get: Get the (id, repr) of task types/users
        - F     message_format: Get the chatter messages/emails (from their ids) / Rest of info comes from /mail route ]
        - KF    default_view: Get the id of the kanban view (in order to instantiate it)
        - C     default_get: Return default values for the fields in ``fields_list``
        - KFC   load_views: Get the fields definitions
        - KC    read_group: Get the list of records in list view grouped by the given ``groupby`` fields
        - KC    read_progress_bar: Get the data needed for all the kanban column progressbars. Fetched alongside read_group operation.
        - C     onchange
        - S     create: Create a record in project.task

        :param kwargs: Contains the method, the model and any other keyword
                       arguments required by the call_kw() method of
                       DataSet.
        :return: (any) The result of Dataset.call_kw
        """
        return self._check_and_perform('call_kw',
                                       submethod=kwargs['method'],
                                       access_info=kwargs.pop('access_info', {}),
                                       **kwargs)

    @http.route('/embed/project/dataset/load', type='json', auth="public")
    def public_load(self, **kwargs):
        """After checking permissions, call load() in order to perform a read() using
        the provided model, id and fields.

        Use within a project:
        - None found

        :param kwargs: Contains the model, id, fields and any other keyword
                       arguments required by the load() method of DataSet.
        :return: (any) The result of Dataset.load
        """
        return self._check_and_perform('load', access_info=kwargs.pop('access_info', None), **kwargs)

    @http.route('/embed/project/dataset/resequence', type='json', auth="public")
    def public_resequence(self, **kwargs):
        """After checking permissions, call resequence() in order to re-sequence
        a number of records in the model, by their ids.

        Use within a project:
        - Changing the order of tasks or stages

        :param kwargs: Contains the ids and any other keyword arguments
                       required by the call_button() method of DataSet.
        :return: (any) The result of Dataset.resequence
        """
        return self._check_and_perform('resequence', access_info=kwargs.pop('access_info', None), **kwargs)

    @http.route('/embed/project/dataset/search_read', type='json', auth="public")
    def public_search_read(self, **kwargs):
        """After checking permissions, call search_read() in order to perform a search()
        followed by a read() (if needed) using the provided search criteria.

        Use within a project:
        - Get the recordsets data

        :param kwargs: Contains the search criteria and any other keyword arguments required
                       by the search_read() method of DataSet.
        :return: (any) The result of Dataset.search_read
        """
        return self._check_and_perform('search_read', access_info=kwargs.pop('access_info', None), **kwargs)


class PublicMailController(MailController, PublicProject):

    @http.route('/embed/project/mail/init_messaging', type='json', auth='public')
    def public_mail_init_messaging(self, **kwargs):
            """After checking permissions, call mail_init_messaging() in order to retrieve
            values required for the chatter initialization.

            :param kwargs: (dict) contains access_info: access token and document information (project_id, task_id)
                                           and potentially a context key
            :return: (dict) The result of MailController.mail_init_messaging
            """
            return self._check_and_perform('mail_init_messaging', access_info=kwargs.pop('access_info', None), **kwargs)
