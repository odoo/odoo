openerp.web_tip = function(session) {
    session.mail.Thread.include({
        message_fetch: function() {
            return this._super.apply(this, arguments).done(function() {
                openerp.web.bus.trigger('chatter_messages_fetched');
            });
        }
    });
};
