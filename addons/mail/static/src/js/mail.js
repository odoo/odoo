openerp.mail = function(session) {
    
    var mail = session.mail = {};
    
    session.web.form.widgets.add(
        'ThreadView', 'openerp.mail.ThreadView');

    /* ThreadView Widget: thread of comments */
    mail.ThreadView = session.web.form.Field.extend({
        // QWeb template to use when rendering the object
        template: 'MailTest',
        
        init: function() {
//             this.timeout;
            this._super.apply(this, arguments);
            this.ds = new session.web.DataSet(this, this.view.model);
        },
        
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            self.$element.find('button.oe_mail_action_follow').bind('click', function () { self.do_follow(); });
            self.$element.find('button.oe_mail_action_unfollow').bind('click', function () { self.do_unfollow(); });
        },
        
        stop: function () {
//             clearTimeout(this.timeout);
            this._super();
        },
        
        set_value: function() {
            this._super.apply(this, arguments);
            if (! this.view.datarecord.id) { return; }
            return this.fetch_messages();
        },
        
        fetch_messages: function () {
            return this.ds.call('message_load', [[this.view.datarecord.id]]).then(
                this.proxy('display_records'));
        },
        
        display_records: function (records) {
            console.log(records);
//             this.$element.empty();
            var self = this;
            _(records).each(function (record) {
                $('<div>').text(record.user_id[1]).appendTo(self.$element);
//                 $('<div>').text(record.user_id['1']).appendTo(self.$element);
//                 $('<div style="width:75%;">').text(record.body_text).appendTo(self.$element);
                $('<div>').text(record.body_text).appendTo(self.$element);
//                 $('<p>').text(record.user_id).appendTo(self.$element);
            });
//             this.timeout = setTimeout(this.proxy('fetch_messages'), 5000);
        },
        
        do_follow: function () {
            var self = this;
            console.log('Follow');
        },
        
        do_unfollow: function () {
            var self = this;
            console.log('Unfollow');
        }
    });
    
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
