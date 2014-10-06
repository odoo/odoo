(function() {
    var instance = openerp;
    instance.web_tip = function(session) {
        session.mail.Thread.include({
            message_fetch: function() {
                return this._super.apply(this, arguments).done(function() {
                    instance.web.bus.trigger('chatter_messages_fetched');
                });
            }
        });
    };
})();
