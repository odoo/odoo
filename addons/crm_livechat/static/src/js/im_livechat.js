odoo.define('crm_livechat.im_livechat', function (require) {
"use strict";

var AbstractThreadWindow = require('mail.AbstractThreadWindow');
var core = require('web.core');
var Dialog = require('web.Dialog');
var LiveChat = require('im_livechat.im_livechat');

var _t = core._t;
var QWeb = core.qweb;

LiveChat.LivechatButton.include({
    /**
    * create lead for visitor when operator is not available
    *
    * @private
    * @param {Object} Thread
    * @param {string} channnel unique id
     */
    _createLead: function (threadwindow, channel_uuid) {
        var self = this;
        var content = QWeb.render('crm_livechat.create_lead', {channel_uuid: channel_uuid});
        threadwindow.$('.o_mail_thread_content, .o_thread_composer').addClass('o_hidden');
        threadwindow.$('.o_mail_thread').append($(content));
        threadwindow.$('#lead-form input[name="name"]').focus();
        var form = document.getElementById('lead-form');
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            return self._rpc({
                route: event.target.action,
                params: $.deparam($(event.target).serialize()),
            }).then(function (res_id) {
                if (channel_uuid) {
                    self.lead_id = res_id;
                    threadwindow.$('.o_mail_thread_content, .o_thread_composer').removeClass('o_hidden');
                    threadwindow.$('#lead_create_form').remove();
                } else {
                    threadwindow.$('#lead_create_form div').html(_t('Thanks for connecting with us. we will contact you soon'));
                }
           });
        });

    },
    /**
    * create lead for visitor when operator is not available
     */
    createLead: function () {
        var self = this;
        if (this._livechat) {
            this._createLead(this._chatWindow, this._livechat._uuid);
        } else {
            var threadwindow = new AbstractThreadWindow(this, null);
            threadwindow = _.extend({}, threadwindow, {
                close: function() {this.destroy();},
                getTitle: function() {return _t('Visitor');}
            })
            threadwindow.appendTo($('body')).then(function () {
                self.do_hide();
                var cssProps = {bottom: 0};
                cssProps[_t.database.parameters.direction === 'rtl' ? 'left' : 'right'] = 0;
                threadwindow.$el.css(cssProps);
                self._createLead(threadwindow);
            });
        }
    },
    /**
     * @private
     * @override
     */
    _handleNotification: function  (notification) {
        if (this._livechat && (notification[0] === this._livechat.getUUID())) {
            if (notification[1].type == 'operator_unavailable') {
                if (!this.is_lead) {
                    this.createLead();
                }
            } else {
                this._super.apply(this, arguments);
            }
        }
    },
    /**
     * @override
     * @private
     */
    _notifyNoOperator: function (livechatData) {
        this.createLead(livechatData);
    },
    /**
     * @override
     * @private
     */
    _onPostMessageChatWindow: function (ev) {
        this._super.apply(this, arguments);
        if (this.lead_id) {
            this._rpc({
                route: '/lead/update_description',
                params: {lead_id: this.lead_id, content: ev.data.messageData.content, channel_uuid: this._livechat._uuid},
            });
        }
    },

});
});
