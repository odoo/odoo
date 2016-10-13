odoo.define('mail.TypingNotifier', function (require) {
"use strict";
var core = require('web.core');
var Widget = require('web.Widget');

var _t = core._t;

var TypingNotifier = Widget.extend({
    init: function(parent) {
        this.composer = parent;
        this.typing = false;
        this.typing_timeout = 1000;
    },
    start: function() {
        var $input = this.composer.$('.o_composer_text_field');
        this.watch_typing($input);
    },
    watch_typing: function($input) {
        var self = this;
        var start_typing = function(e) {
            if (!this.typing) {
                this.typing = true;
                this.notify_typing({
                    'state': 'start'
                });
            }
        };
        var stop_typing = function(e, delay) {
            if (this.typing) {
                clearTimeout(this.delayedCallback);
                this.delayedCallback = setTimeout(function() {
                    this.typing = false;
                    this.notify_typing({
                        'state': $input.val() ? 'stop': 'cancel'
                    });
                }.bind(this), delay || this.typing_timeout);
            }
        };
        $input.on('keypress', start_typing.bind(this));
        $input.on('keyup', stop_typing.bind(this));
        $input.on('keydown', function(event) {
            if (_.contains([$.ui.keyCode.BACKSPACE ,$.ui.keyCode.DELETE ,$.ui.keyCode.ENTER], event.keyCode)) {
                start_typing.call(self, event);
            }
        });
        $input.on('paste cut', function (event) {
            self.typing = true;
            stop_typing.call(self, event, 50);
        });
        $input.on('blur', function(event) {
            stop_typing.call(self, event, 1);
        });
    },
    // send typing notification
    notify_typing: function(status) {
        this.composer.trigger("notify_typing", status);
    },
    // received typing notification
    notified_typing: function(channel){
        var user_name = channel.direct_partner_name || channel.name;
        var message = '';
        this.$el.empty();
        switch(channel.typing_status) {
            case 'start':
                message = _.str.sprintf(_t('<span>%s is typing...</span>'), user_name);
                this.$el.html(message);
                break;
            case 'stop':
                message = _.str.sprintf(_t('<span>%s stop typing.</span>'), user_name);
                this.$el.html(message);
                break;
            case 'cancel':
                this.$el.empty();
                break;
        }
    }
});

return TypingNotifier;
});