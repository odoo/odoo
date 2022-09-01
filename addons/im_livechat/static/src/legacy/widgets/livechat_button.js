/** @odoo-module **/

import time from 'web.time';
import utils from 'web.utils';
import Widget from 'web.Widget';

const LivechatButton = Widget.extend({
    className: 'openerp o_livechat_button d-print-none',
    events: {
        'click': '_onClick'
    },
    init(parent, messaging) {
        this._super(parent);
        this.messaging = messaging;
    },
    start() {
        this.messaging.publicLivechatGlobal.livechatButtonView.start();
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Will try to get a previous operator for this visitor.
     * If the visitor already had visitor A, it's better for his user experience
     * to get operator A again.
     *
     * The information is stored in the 'im_livechat_previous_operator_pid' cookie.
     *
     * @private
     * @return {integer} operator_id.partner_id.id if the cookie is set
     */
     _get_previous_operator_id() {
        const cookie = utils.get_cookie('im_livechat_previous_operator_pid');
        if (cookie) {
            return cookie;
        }

        return null;
    },
    /**
     * @private
     */
    _prepareGetSessionParameters() {
        return {
            channel_id: this.messaging.publicLivechatGlobal.channelId,
            anonymous_name: this.messaging.publicLivechatGlobal.livechatButtonView.defaultUsername,
            previous_operator_id: this._get_previous_operator_id(),
        };
    },
    /**
     * @private
     */
    _sendWelcomeMessage() {
        if (this.messaging.publicLivechatGlobal.livechatButtonView.defaultMessage) {
            this.messaging.publicLivechatGlobal.livechatButtonView.addMessage({
                id: '_welcome',
                author: {
                    id: this.messaging.publicLivechatGlobal.publicLivechat.operator.id,
                    name: this.messaging.publicLivechatGlobal.publicLivechat.operator.name,
                },
                body: this.messaging.publicLivechatGlobal.livechatButtonView.defaultMessage,
                date: time.datetime_to_str(new Date()),
                model: "mail.channel",
                res_id: this.messaging.publicLivechatGlobal.publicLivechat.id,
            }, { prepend: true });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick() {
        this.messaging.publicLivechatGlobal.livechatButtonView.openChat();
    },
});

export default LivechatButton;
