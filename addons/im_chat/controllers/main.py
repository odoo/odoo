# -*- coding: utf-8 -*
import base64
import openerp

from openerp import SUPERUSER_ID
from openerp.http import request


class ChatController(openerp.addons.bus.controllers.main.BusController):

    def _default_request_uid(self):
        """ For Anonymous people, they receive the access right of SUPERUSER_ID since they have NO access (auth=none)
            !!! Each time a method from this controller is call, there is a check if the user (who can be anonymous and Sudo access)
            can access to the ressource, thanks to 'is_in_session', (for instance).
        """
        return request.session.uid and request.session.uid or SUPERUSER_ID

    # --------------------------
    # Extends BUS Controller Poll
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            request.env['im_chat.presence'].update(options.get('im_presence'))
            # channel to receive message
            channels.append((request.db, 'im_chat.session', request.session.uid))
            ## For performance issue, the real time status notification is disabled. This means a change of status are still braoadcasted
            ## but not received by anyone. Otherwise, all listening user restart their longpolling at the same time and cause a 'ConnectionPool Full Error'
            ## since there is not enought cursors for everyone. Now, when a user open his list of users, an RPC call is made to update his user status list.
            ##channels.append((request.db,'im_chat.presence'))
        return super(ChatController, self)._poll(dbname, channels, last, options)

    # --------------------------
    # Anonymous routes (Common Methods)
    # --------------------------
    @openerp.http.route('/im_chat/post', type="json", auth="none")
    def post(self, uuid, message_content, message_type):
        request_uid = self._default_request_uid()
        return request.env["im_chat.message"].sudo(request_uid).send_message(request.session.uid, uuid, message_content, message_type)

    @openerp.http.route(['/im_chat/image/<string:uuid>/<int:user_id>', '/im_chat/image/<string:uuid>/<string:user_id>'], type='http', auth="none")
    def image(self, uuid, user_id):
        request_uid = self._default_request_uid()
        # anonymous will have a user_id = False, interpreted by string
        if isinstance(user_id, (basestring, unicode)):
            user_id = False
        # get image for the people in the channel
        image_b64 = request.env['im_chat.session'].sudo(request_uid).session_user_image(uuid, user_id)
        image_data = base64.b64decode(image_b64)
        headers = [('Content-Type', 'image/png')]
        headers.append(('Content-Length', len(image_data)))
        return request.make_response(image_data, headers)

    @openerp.http.route(['/im_chat/history'], type="json", auth="none")
    def history(self, uuid, last_id=False, limit=20):
        request_uid = self._default_request_uid()
        return request.env["im_chat.message"].sudo(request_uid).fetch_message(uuid, last_id, limit)

    # --------------------------
    # User routes (Only Logged User Methods)
    # --------------------------
    @openerp.http.route('/im_chat/init', type="json", auth="user")
    def init(self):
        return request.env['im_chat.message'].get_init_notifications()
