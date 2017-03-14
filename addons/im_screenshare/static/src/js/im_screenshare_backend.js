(function(){

    var instance = openerp;

    // add the button in the webclient menu bar
    /* FP don't this for now
    instance.web.UserMenu.include({
        do_update: function(){
            var self = this;
            this.update_promise.then(function() {
                var button = new instance.im_screenshare.RecordButton(this);
                button.appendTo(openerp.webclient.$el.find('.oe_systray'));
            });
            return this._super.apply(this, arguments);
        },
    });
    */

    // add the button to the header of the conversation
    instance.im_chat.Conversation.include({
        start: function() {
            this._super();
            var b = new instance.im_screenshare.ShareButton(this);
            b.prependTo(this.$('.oe_im_chatview_right'));
        },
        /* TODO : make it work with im_livechat (for saas6)
        add_options: function(){
            this._super();
            this._add_option('Screensharing', 'im_chat_option_screenshare', 'fa fa-desktop');
        }
        */
    });

})();