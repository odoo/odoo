import simplejson
import urllib
import openerp
import openerp.addons.web.http as http
from openerp.addons.web.http import request
import openerp.addons.web.controllers.main as webmain
from openerp.addons.web.http import SessionExpiredException
from werkzeug.exceptions import BadRequest
import werkzeug.utils

class google_calendar_controller(http.Controller):
    
    @http.route('/google_calendar/sync_data', type='json', auth='user')
    def sync_data(self, arch, fields, model,**kw):
        """ 
            This route/function is called when we want to synchronize openERP calendar with Google Calendar
            
            Function return a dictionary with the status :  NeedConfigFromAdmin, NeedAuth, NeedRefresh, NoNewEventFromGoogle, SUCCESS if not crm meeting
            The dictionary may contains an url, to allow OpenERP Client to redirect user on this URL for authorization for example 
                    
        """
                            
        if model == 'crm.meeting':
            gs_obj = request.registry.get('google.service')
            gc_obj = request.registry.get('google.calendar')
            
            # Checking that admin have already configured Google API for google synchronization !
            client_id = gs_obj.get_client_id(request.cr, request.uid,'calendar',context=kw.get('LocalContext'))

            if not client_id or client_id == '':
                action = ''
                if gc_obj.can_authorize_google(request.cr,request.uid):
                    dummy, action = request.registry.get('ir.model.data').get_object_reference(request.cr, request.uid, 'google_calendar', 'action_config_settings_google_calendar')
                
                return {
                        "status" :  "NeedConfigFromAdmin",
                        "url" : '',
                        "action" : action
                        }
                        
            # Checking that user have already  accepted OpenERP to access his calendar !
            if gc_obj.need_authorize(request.cr, request.uid,context=kw.get('LocalContext')):
                url =  gc_obj.authorize_google_uri(request.cr, request.uid, from_url=kw.get('fromurl'),context=kw.get('LocalContext'))
                return {
                        "status" :  "NeedAuth",
                        "url" : url 
                        }
            
            # If App authorized, and user access accepted, We launch the synchronization
            return gc_obj.synchronize_events(request.cr, request.uid, [], kw.get('LocalContext'))
                      
        return { "status" : "SUCCESS" }
    
