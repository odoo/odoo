# -*- coding: utf-8 -*-
import base64
import logging
import simplejson
import openerp

from openerp.http import request

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# Controllers
#----------------------------------------------------------
class Controller(openerp.addons.bus.bus.Controller):
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            registry, cr, uid, context = request.registry, request.cr, request.session.uid, request.context
            registry.get('im_chat.presence').update(cr, uid, ('im_presence' in options), context=context)
            # listen to connection and disconnections
            channels.append((request.db,'im_chat.presence'))
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
