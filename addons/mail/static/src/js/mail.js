openerp.mail = function(session) {
    
    var mail = session.mail = {};
    
    session.web.form.widgets.add(
        'ThreadView', 'openerp.mail.ThreadView');

    /* ThreadView Widget: thread of comments */
    mail.ThreadView = session.web.form.Field.extend({
        // QWeb template to use when rendering the object
        template: 'ThreadView',
        
        init: function() {
            console.log('Entering init');
//             this.timeout;
            this.follow_state = 0;
            this._super.apply(this, arguments);
            this.ds = new session.web.DataSet(this, this.view.model);
            this.ds_sub = new session.web.DataSet(this, 'mail.subscription');
            console.log('Leaving init');
        },
        
        start: function() {
            console.log('Entering start');
            var self = this;
            this._super.apply(this, arguments);
            /* bind follow and unfollow buttons */
            self.$element.find('button.oe_mail_action_follow').bind('click', function () { self.do_follow(); });
            self.$element.find('button.oe_mail_action_follow').hide();
            self.$element.find('button.oe_mail_action_unfollow').bind('click', function () { self.do_unfollow(); });
            self.$element.find('button.oe_mail_action_unfollow').hide();
            /* find wich (un)follow buttons to show */
            var call_res = this.ds.call('message_is_subscriber', [[this.session.uid]]).then(function (records) {
                console.log('Pouet');
                console.log(records);
                console.log('Pouet2');
                if (records == true) { self.follow_state = 1; console.log('brout!'); self.$element.find('button.oe_mail_action_unfollow').show(); }
                else { self.follow_state = 0; console.log('proutch!');  self.$element.find('button.oe_mail_action_follow').show(); }
                });
            console.log(call_res);
            console.log('Leaving start');
        },
        
        render: function() {
            console.log('Entering render');
//             this._super.apply(this, arguments);
            var template = this.template;
            var render_res = session.web.qweb.render(template, {
                'tmp': 'comment',
                });
            console.log('Leaving render');
            return render_res;
        },
        
        stop: function () {
//             clearTimeout(this.timeout);
            console.log('Entering stop');
            this._super();
            console.log('Leaving stop');
        },
        
        set_value: function() {
            console.log('Entering set_value');
            this._super.apply(this, arguments);
            if (! this.view.datarecord.id) { return; }
            var fetch_res = this.fetch_messages();
            console.log('Leaving set_value');
            return fetch_res
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
            console.log('Follow');
            console.log(this);
            this.$element.find('button.oe_mail_action_unfollow').show();
            this.$element.find('button.oe_mail_action_follow').hide();
            return this.ds_sub.create({'res_model': this.view.model, 'user_id': this.session.uid, 'res_id': this.view.datarecord.id}).then(
                console.log('Subscription done'));
        },
        
        do_unfollow: function () {
            console.log('Unfollow');
            this.$element.find('button.oe_mail_action_follow').show();
            this.$element.find('button.oe_mail_action_unfollow').hide();
            return this.ds.call('message_unsubscribe', [[this.view.datarecord.id]]).then(
                console.log('Unfollowing'));
        }
    });
    
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
