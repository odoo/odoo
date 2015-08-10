odoo.define('im_livechat.chat_backend', function (require) {
"use strict";

var mail_chat_backend = require('mail.chat_backend');


/**
 * Patch for the client action to integrate Livechat Mail Channel in a particular slot
 */
mail_chat_backend.ChatMailThread.include({
    init: function(parent, action){
        this._super.apply(this, arguments);
        this.set('channel_livechat', []);
    },
    start: function(){
        var self = this;
        this.on("change:channel_livechat", this, function(){
            self.channel_render('channel_livechat');
        });
        return this._super.apply(this, arguments).then(function(){
            self.$el.on('click', '.o_mail_chat_channel_unpin', _.bind(self.on_click_channel_unpin, self));
        });
    },
    on_click_channel_unpin: function(event){
        var self = this;
        var channel_id = this.$(event.currentTarget).data('channel-id');
        var channel = this.channels[channel_id];
        return this.channel_pin(channel.uuid, false).then(function(){
            self.channel_remove(channel_id);
            // if unpin current channel, switch to inbox
            if(self.get('current_channel_id') === channel_id){
                self.set('current_channel_id', 'channel_inbox');
            }
        });
    },
    channel_change: function(){
        // update the default username
        var current_channel = this.channels[this.get('current_channel_id')];
        if(current_channel){
            this.options.default_username = current_channel.anonymous_name || this.options.default_username
        }
        return this._super.apply(this, arguments);
    },
    // utils function
    get_channel_slot: function(channel){
        if(channel.channel_type === 'livechat'){
            return 'channel_livechat';
        }
        return this._super.apply(this, arguments);
    },
});

});
