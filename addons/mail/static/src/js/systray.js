odoo.define('mail.systray', function (require) {
"use strict";

var core = require('web.core');
var SystrayMenu = require('web.SystrayMenu');
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
        start: function () {
            chat_manager.bus.on("update_needaction", this, this.update_counter);
            this.update_counter(chat_manager.get_needaction_counter());
            return this._super();
        },
        update_counter: function (counter) {
            this.$('.o_notification_counter').html(counter);
        },
        on_click: function (event) {
            event.preventDefault();
            this.discuss_redirect();
        },
        discuss_redirect: _.debounce(function () {
            var discuss_ids = chat_manager.get_discuss_ids();
            this.do_action(discuss_ids.action_id, {clear_breadcrumbs: true}).then(function () {
                core.bus.trigger('change_menu_section', discuss_ids.menu_id);
            });
        }, 1000, true),
});

SystrayMenu.Items.push(NotificationTopButton);

});
