# -*- coding: utf-8 -*
import base64
import openerp
import simplejson

from openerp import SUPERUSER_ID
from openerp.http import request

#----------------------------------------------------------
# Controllers
#----------------------------------------------------------
class Controller(openerp.addons.bus.controllers.main.BusController):
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            registry, cr, uid, context = request.registry, request.cr, request.session.uid, request.context
            registry.get('im_chat.presence').update(cr, uid, options.get('im_presence', False), context=context)
            ## For performance issue, the real time status notification is disabled. This means a change of status are still braoadcasted
            ## but not received by anyone. Otherwise, all listening user restart their longpolling at the same time and cause a 'ConnectionPool Full Error'
            ## since there is not enought cursors for everyone. Now, when a user open his list of users, an RPC call is made to update his user status list.
            ##channels.append((request.db,'im_chat.presence'))
            # channel to receive message
            channels.append((request.db,'im_chat.session', request.uid))
        return super(Controller, self)._poll(dbname, channels, last, options)

    @openerp.http.route('/im_chat/init', type="json", auth="none")
    def init(self):
        registry, cr, uid, context = request.registry, request.cr, request.session.uid, request.context
        notifications = registry['im_chat.message'].init_messages(cr, uid, context=context)
        return notifications

    @openerp.http.route('/im_chat/post', type="json", auth="none")
    def post(self, uuid, message_type, message_content):
        registry, cr, uid, context = request.registry, request.cr, request.session.uid, request.context
        # execute the post method as SUPERUSER_ID
        message_id = registry["im_chat.message"].post(cr, openerp.SUPERUSER_ID, uid, uuid, message_type, message_content, context=context)
        return message_id

    @openerp.http.route(['/im_chat/image/<string:uuid>/<string:user_id>'], type='http', auth="none")
    def image(self, uuid, user_id):
        registry, cr, context, uid = request.registry, request.cr, request.context, request.session.uid
        # get the image
        Session = registry.get("im_chat.session")
        image_b64 = Session.get_image(cr, openerp.SUPERUSER_ID, uuid, simplejson.loads(user_id), context)
        # built the response
        image_data = base64.b64decode(image_b64)
        headers = [('Content-Type', 'image/png')]
        headers.append(('Content-Length', len(image_data)))
        return request.make_response(image_data, headers)

    @openerp.http.route(['/im_chat/history'], type="json", auth="none")
    def history(self, uuid, last_id=False, limit=20):
        registry, cr, uid, context = request.registry, request.cr, request.session.uid or openerp.SUPERUSER_ID, request.context
        return registry["im_chat.message"].get_messages(cr, uid, uuid, last_id, limit, context=context)
