odoo.define('mail.systray', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var SystrayMenu = require('web.SystrayMenu');
var web_client = require('web.web_client');
var Widget = require('web.Widget');

var chat_manager = require('mail.chat_manager');

/**
 * Widget Top Menu Notification Counter
 *
 * Counter of notification in the Systray Menu. Need to know if InstantMessagingView is displayed to
 * increment (or not) the counter. On click, should redirect to the client action.
 **/
var NotificationTopButton = Widget.extend({
        template:'mail.chat.NotificationTopButton',
        events: {
            "click": "on_click",
        },
        willStart: function () {
            var self = this;
            var ir_model = new Model("ir.model.data");
            var def1 = ir_model.call("xmlid_to_res_id", ["mail.mail_channel_menu_root_chat"]);
            var def2 = ir_model.call("xmlid_to_res_id", ["mail.mail_channel_action_client_chat"]);
            return $.when(def1, def2, this._super()).then(function (menu_id, action_id) {
                self.discuss_menu_id = menu_id;
                self.client_action_id = action_id;
            });
        },
        start: function () {
            chat_manager.bus.on("update_needaction", this, this.update_counter);
            this.update_counter(chat_manager.get_needaction_counter());
            return this._super();
        },
        update_counter: function (counter) {
            this.$('.o_notification_counter').html(counter);
        },
        on_click: function (event) {
            var self = this;
            event.preventDefault();
            this.do_action(this.client_action_id, {clear_breadcrumbs: true}).then(function () {
                core.bus.trigger('change_menu_section', self.discuss_menu_id);
            });
        },
});

SystrayMenu.Items.push(NotificationTopButton);



/**
 *  * Global ComposeMessage Top Button
 *   *
 *    * Add a link on the top user bar to write a full mail. It opens the form view
 *     * of the mail.compose.message (in a modal).
 *      */
var ComposeMessageTopButton = Widget.extend({
    template:'mail.ComposeMessageTopButton',
    events: {
        "click": "on_compose_message",
    },
    on_compose_message: function (ev) {
        ev.preventDefault();
        web_client.action_manager.do_action({
            type: 'ir.actions.act_window',
            res_model: 'mail.compose.message',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
        });
    },
});

// Put the ComposeMessageTopButton widget in the systray menu
SystrayMenu.Items.push(ComposeMessageTopButton);

});
