import simplejson
import urllib
import openerp
import openerp.addons.web.http as http
from openerp.addons.web.http import request
import openerp.addons.web.controllers.main as webmain
import json
from openerp.addons.web.http import SessionExpiredException
from werkzeug.exceptions import BadRequest
import werkzeug.utils

class google_auth(http.Controller):
    
    @http.route('/googleauth/oauth2callback', type='http', auth="none")
    def oauth2callback(self, **kw):
        
        state = simplejson.loads(kw['state'])

        #action = state.get('a')
        #menu = state.get('m')
        dbname = state.get('d')
        #service = state.get('s')
        url_return = state.get('from')
        
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        with registry.cursor() as cr:
            #TODO CHECK IF REQUEST OK
            registry.get('google.calendar').set_all_tokens(cr,request.session.uid,kw['code'])
            registry.get('google.calendar').set_primary_id(cr,request.session.uid)
            
        return werkzeug.utils.redirect(url_return)        

    #@openerp.addons.web.http.route('/web_calendar_sync/sync_calendar/sync_data', type='json', auth='user')
    @http.route('/web_calendar_sync/sync_calendar/sync_data', type='json', auth='user')
    def sync_data(self, arch, fields, model,**kw):
        calendar_info = {
            'field_data':{},
            'date_start':arch['attrs'].get('date_start'),
            'date_stop':arch['attrs'].get('date_stop'),
            'calendar_string':arch['attrs'].get('string'),
            'model':model
        }
        for field, data in fields.items():
            calendar_info['field_data'][field] = {
                 'type': data.get('type'),
                 'string': data.get('string')
                 }
                    
        if model == 'crm.meeting':
            model_obj = request.registry.get('crm.meeting.synchronize')
            gc_obj = request.registry.get('google.calendar')
             
            #We check that user has already accepted openerp to acces his calendar !
            if not gc_obj.get_refresh_token(request.cr, request.uid,context=kw.get('LocalContext')):
                url =  gc_obj.authorize_google_uri(request.cr, request.uid, from_url=kw.get('fromurl'),context=kw.get('LocalContext'))
                return {
                        "status" :  "NeedAuth",
                        "url" : url 
                        }
            
            #We lunch th synchronization    
            print "ORI COONTEXT = ",kw.get('LocalContext')
            model_obj.synchronize_events(request.cr, request.uid, [], kw.get('LocalContext'))
        else:
            model_obj = request.registry.get('google.calendar')
            model_obj.synchronize_calendar(request.cr, request.uid, calendar_info, kw.get('LocalContext'))
        
        
        return { "status" : "SUCCESS" }


























    @http.route('/googleauth/AuthorizeMe', type='http', auth="none")
    def authorize_app(self,**val):
        if val.get('done'):
             return;
        registry = openerp.modules.registry.RegistryManager.get(request.session.get('db'))
        gs_pool = registry.get('google.service')
        with registry.cursor() as cr:
            url = gs_pool._get_authorize_uri(cr,request.session.uid,service='calendar',from_url='')
        return werkzeug.utils.redirect(url) ##REDIRECT WHERE THE USER WAS BEFORE (with state)
    
    
    @http.route('/googleauth/GiveMeAToken', type='http', auth="none")
    def authorize_me(self,**val):
        registry = openerp.modules.registry.RegistryManager.get(request.session.get('db'))
        gs_pool = registry.get('google.service')
        with registry.cursor() as cr:
            token = gs_pool._get_google_token_json(cr, request.session.uid, 'api_code')
            
            print '#####################################'
            print '## YOUR TOKEN : ',token,      "    ##"
            print '#####################################'     
        #return werkzeug.utils.redirect(url)
        return                
        
