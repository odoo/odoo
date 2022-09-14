/** @odoo-module **/

import time from 'web.time';
import {getCookie} from 'web.utils.cookies';
import Widget from 'web.Widget';

const LivechatButton = Widget.extend({
    className: 'openerp o_livechat_button d-print-none',
    events: {
        'click': '_onClick'
    },
    init(parent, messaging) {
        this._super(parent);
        this.global = messaging.global;
    },
    start() {
        this.global.PublicLivechatGlobal.livechatButtonView.start();
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
        const cookie = getCookie('im_livechat_previous_operator_pid');
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
            channel_id: this.global.PublicLivechatGlobal.channelId,
            anonymous_name: this.global.PublicLivechatGlobal.livechatButtonView.defaultUsername,
            previous_operator_id: this._get_previous_operator_id(),
        };
    },
    /**
     * @private
     */
    _sendWelcomeMessage() {
        if (this.global.PublicLivechatGlobal.livechatButtonView.defaultMessage) {
            this.global.PublicLivechatGlobal.livechatButtonView.addMessage({
                id: '_welcome',
                author: {
                    id: this.global.PublicLivechatGlobal.publicLivechat.operator.id,
                    name: this.global.PublicLivechatGlobal.publicLivechat.operator.name,
                },
                body: this.global.PublicLivechatGlobal.livechatButtonView.defaultMessage,
                date: time.datetime_to_str(new Date()),
                model: "mail.channel",
                res_id: this.global.PublicLivechatGlobal.publicLivechat.id,
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
        this.global.PublicLivechatGlobal.livechatButtonView.openChat();
    },
});

export default LivechatButton;
