import openerp.addons.web.http as http
from openerp.addons.web.http import request


class google_calendar_controller(http.Controller):

    @http.route('/google_calendar/sync_data', type='json', auth='user')
    def sync_data(self, arch, fields, model, **kw):
        """
            This route/function is called when we want to synchronize openERP calendar with Google Calendar
            Function return a dictionary with the status :  need_config_from_admin, need_auth, need_refresh, success if not calendar_event
            The dictionary may contains an url, to allow OpenERP Client to redirect user on this URL for authorization for example
        """

        if model == 'calendar.event':
            gs_obj = request.registry['google.service']
            gc_obj = request.registry['google.calendar']

            # Checking that admin have already configured Google API for google synchronization !
            client_id = gs_obj.get_client_id(request.cr, request.uid, 'calendar', context=kw.get('local_context'))

            if not client_id or client_id == '':
                action = ''
                if gc_obj.can_authorize_google(request.cr, request.uid):
                    dummy, action = request.registry.get('ir.model.data').get_object_reference(request.cr, request.uid,
                                                                                               'google_calendar', 'action_config_settings_google_calendar')

                return {
                    "status": "need_config_from_admin",
                    "url": '',
                    "action": action
                }

            # Checking that user have already accepted OpenERP to access his calendar !
            if gc_obj.need_authorize(request.cr, request.uid, context=kw.get('local_context')):
                url = gc_obj.authorize_google_uri(request.cr, request.uid, from_url=kw.get('fromurl'), context=kw.get('local_context'))
                return {
                    "status": "need_auth",
                    "url": url
                }

            # If App authorized, and user access accepted, We launch the synchronization
            return gc_obj.synchronize_events(request.cr, request.uid, [], context=kw.get('local_context'))

        return {"status": "success"}

    @http.route('/google_calendar/remove_references', type='json', auth='user')
    def remove_references(self, model, **kw):
        """
            This route/function is called when we want to remove all the references between one calendar OpenERP and one Google Calendar
        """
        status = "NOP"
        if model == 'calendar.event':
            gc_obj = request.registry['google.calendar']
            # Checking that user have already accepted OpenERP to access his calendar !
            if gc_obj.remove_references(request.cr, request.uid, context=kw.get('local_context')):
                status = "OK"
            else:
                status = "KO"
        return {"status": status}
