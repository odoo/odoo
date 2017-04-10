odoo.define('mail.TypingNotifier', function (require) {

"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var _t = core._t;

/**
 * This widget manage the typing part. To make it work, the widget parent need to have :
 *  - an input item (input, textarea, ...) with the class 'o_mail_typing_input'.
 *  - a div with 'o_mail_typing_people' class, in which who is typing will be displayed.
 **/
var TypingNotifier = Widget.extend({
    init: function(parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
            typing_timeout: 1000,
            display_name_limit: 3,
        });

        // ui parts
        this.$input = parent.$el.find('.o_mail_typing_input').first();
        this.$output = parent.$el.find('.o_mail_typing_people').first();
        // actions and events
        this.bind_typing_event();
        this.set('typing_people', []); // list of user profile, like {'partner_id':3, 'name': 'Administrator'}
        this.on('change:typing_people', this, this.on_change_typing_people);
    },
    bind_typing_event: function(){
        var self = this;
        this.$input.on('keypress', _.bind(this._start_typing, this));
        this.$input.on('keydown', function(event){
            if(_.contains([8, 46, 13], event.keyCode)){ // BACKSPACE, DELETE, ENTER keys (avoid requiring jquery ui for external livechat)
                self._start_typing();
            }
        });
        this.$input.on('keyup', function(event){
            self._stop_typing();
        });
        this.$input.on('blur', function(event){
            self._stop_typing(1);
        });
        this.$input.on('paste cut', function(){
            self.is_typing = true;
            self._stop_typing(500);
        });
    },
    _start_typing: function(){
        if (!this.is_typing) {
            this.is_typing = true;
            this.notify_typing('start');
        }
    },
    _stop_typing: function(delay) {
        var self = this;
        if (this.is_typing) {
            clearTimeout(this.delayedCallback);
            this.delayedCallback = setTimeout(function() {
                self.is_typing = false;
                self.notify_typing('stop');
            }, delay || this.options.typing_timeout);
        }
    },
    // send typing notification
    notify_typing: function(status) {
        this.trigger("notify_typing", status);
    },
    apply_typing: function(notif){
        var new_typing_list = _.clone(this.get('typing_people'));
        var typing_list_ids = _.pluck(this.get('typing_people'), 'partner_id');
        if (notif.typing_status === 'start') {
            if(!_.contains(typing_list_ids, notif.partner_id)){
                new_typing_list.push({
                    'partner_id': notif.partner_id,
                    'name': notif.name
                });
            }
        } else {
            new_typing_list = _.filter(new_typing_list, function(item){
                return item.partner_id != notif.partner_id;
            });
        }
        this.set('typing_people', new_typing_list);
    },
    on_change_typing_people: function(){
        var message_str = '';
        var selection = this.get('typing_people').slice(0, this.options.display_name_limit);
        var people_names = _.pluck(selection, 'name');
        if(people_names.length > 0){
            if(people_names.length == 1){
                message_str = _t('%s is typing...');
            }else{
                if(people_names.length > this.options.display_name_limit){
                    message_str = _t('%s and others are typing...');
                }else{
                    message_str = _t('%s are typing...');
                }
            }
            people_names = _.map(people_names, function(item){return '<b>'+item+'</b>'}); // make bold
            message_str = '<span>' + _.str.sprintf(message_str, people_names.join(', ')) + '</span>';
        }
        this.$output.html(message_str);
    },
});

return TypingNotifier;

});
