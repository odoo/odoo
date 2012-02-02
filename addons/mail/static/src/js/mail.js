openerp.mail = function(session) {
    
    var mail = session.mail = {};
    
    mail.Wall = session.web.Widget.extend({
        init: function(parent) {
        },
        start: function() {
//             this.$element
        },
    });
    
    mail.ThreadView = session.web.Widget.extend({
        template: 'MailTest',
        
        init: function(parent) {
        },
        
        start: function() {
//             this.$element
        },
    });
    
    mail.MessgageInput = session.web.Widget.extend({
    });
    
    
    var tv = new mail.ThreadView(this);
//     tv.appendTo($("div.wall"));
//     tv.appendTo($("body"));
    
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
