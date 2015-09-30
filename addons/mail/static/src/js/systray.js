odoo.define('mail.systray', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var web_client = require('web.web_client');
var Widget = require('web.Widget');

var internal_bus = core.bus;

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
        init: function () {
            this._super.apply(this, arguments);
            this.set('counter', 0);
        },
        willStart: function () {
            var self = this;
            var ir_model = new Model("ir.model.data");
            var def1 = ir_model.call("xmlid_to_res_id", ["mail.mail_channel_menu_root_chat"]);
            var def2 = ir_model.call("xmlid_to_res_id", ["mail.mail_channel_action_client_chat"]);
            var def3 = session.rpc('/mail/needaction');
            var def4 = this._super();
            return $.when(def1, def2, def3, def4).then(function (menu_id, action_id, needaction_count) {
                self.discuss_menu_id = menu_id;
                self.client_action_id = action_id;
                self.set('counter', needaction_count);
            });
        },
        start: function () {
            this.on("change:counter", this, this.on_change_counter);
            // events
            internal_bus.on('mail_needaction_new', this, this.counter_increment);
            internal_bus.on('mail_needaction_done', this, this.counter_decrement);
            return this._super();
        },
        counter_increment: function (inc) {
            this.set('counter', this.get('counter')+inc);
        },
        counter_decrement: function (dec) {
            this.set('counter', this.get('counter')-dec);
        },
        on_change_counter: function () {
            this.$('.fa-comment').html(this.get('counter') || '');
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
