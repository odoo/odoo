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

        dbname = state.get('d')
        url_return = state.get('from')
        
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        with registry.cursor() as cr:
            #TODO CHECK IF REQUEST OK
            registry.get('google.calendar').set_all_tokens(cr,request.session.uid,kw['code'])
            #registry.get('google.calendar').set_primary_id(cr,request.session.uid)
            
        return werkzeug.utils.redirect(url_return)        

    @http.route('/web_calendar_sync/sync_calendar/sync_data', type='json', auth='user')
    def sync_data(self, arch, fields, model,**kw):
       
                    
        if model == 'crm.meeting':
            gs_obj = request.registry.get('google.service')
            gc_obj = request.registry.get('google.calendar')
            
            #We check that admin has already configure api for google synchronization !
            client_id = gs_obj.get_client_id(request.cr, request.uid,'calendar',context=kw.get('LocalContext'))

            if not client_id or client_id == '':
                return {
                        "status" :  "NeedConfigFromAdmin",
                        "url" : '' 
                        }
                        
            #We check that user has already accepted openerp to access his calendar !
            if gc_obj.need_authorize(request.cr, request.uid,context=kw.get('LocalContext')):
                url =  gc_obj.authorize_google_uri(request.cr, request.uid, from_url=kw.get('fromurl'),context=kw.get('LocalContext'))
                return {
                        "status" :  "NeedAuth",
                        "url" : url 
                        }
            
            #We launch the synchronization
            result = gc_obj.synchronize_events(request.cr, request.uid, [], kw.get('LocalContext'))
            return result
        else:            
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
            
            print "@@@@@@@@@@@@@@@@@  Is still used !!!!"
            import ipdb; ipdb.set_trace()
            gc_obj.synchronize_calendar(request.cr, request.uid, calendar_info, kw.get('LocalContext'))
        
        
        return { "status" : "SUCCESS" }
























    @http.route('/gmail/delete_all', type='http', auth='user')
    def delete_all(self, **kw):
        gs_obj = request.registry.get('google.service')
        gc_obj = request.registry.get('google.calendar')
        
        #We check that admin has already configure api for google synchronization !
        client_id = gs_obj.get_client_id(request.cr, request.uid,'calendar',context=kw.get('LocalContext'))

        if not client_id or client_id == '':
            return {
                    "status" :  "NeedConfigFromAdmin",
                    "url" : '' 
                    }
                    
        #We check that user has already accepted openerp to access his calendar !
        if gc_obj.need_authorize(request.cr, request.uid,context=kw.get('LocalContext')):
            url =  gc_obj.authorize_google_uri(request.cr, request.uid, from_url=kw.get('fromurl'),context=kw.get('LocalContext'))
            return {
                    "status" :  "NeedAuth",
                    "url" : url 
                    }
        
        #We launch the synchronization
        gc_obj.delete_all(request.cr, request.uid, kw.get('LocalContext'))



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
        
