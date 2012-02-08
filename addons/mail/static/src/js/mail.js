openerp.mail = function(session) {
    
    var mail = session.mail = {};

    /* Add ThreadView widget to registry */
    session.web.form.widgets.add(
        'ThreadView', 'openerp.mail.ThreadView');
    session.web.page.readonly.add(
        'ThreadView', 'openerp.mail.ThreadView');

    /* ThreadView widget: thread of comments */
    mail.ThreadView = session.web.form.Field.extend({
        // QWeb template to use when rendering the object
        template: 'ThreadView',
        
        init: function() {
//             this.timeout;
            this.follow_state = 0;
            this._super.apply(this, arguments);
            /* DataSets */
            this.ds = new session.web.DataSet(this, this.view.model);
            this.ds_sub = new session.web.DataSet(this, 'mail.subscription');
//             this.ds_msg = new session.web.DataSet(this, 'mail.message');
        },
        
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            /* bind follow and unfollow buttons */
            self.$element.find('button.oe_mail_action_follow').bind('click', function () { self.do_follow(); });
            self.$element.find('button.oe_mail_action_follow').hide();
            self.$element.find('button.oe_mail_action_unfollow').bind('click', function () { self.do_unfollow(); });
            self.$element.find('button.oe_mail_action_unfollow').hide();
            self.$element.find('button.oe_mail_action_comment').bind('click', function () { self.do_comment(); });
            /* find wich (un)follow buttons to show */
            var call_res = this.ds.call('message_is_subscriber', [[this.session.uid]]).then(function (records) {
                if (records == true) { self.follow_state = 1; self.$element.find('button.oe_mail_action_unfollow').show(); }
                else { self.follow_state = 0; self.$element.find('button.oe_mail_action_follow').show(); }
                });
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
            this.$element.find('div.oe_mail_comments').empty();
            var self = this;
            _(records).each(function (record) {
                var template = 'ThreadMsgView';
                var render_res = session.web.qweb.render(template, {
                    'record': record,
                    });
                $('<div class="oe_mail_msg">').html(render_res).appendTo(self.$element.find('div.oe_mail_comments'));
            });
//             this.timeout = setTimeout(this.proxy('fetch_messages'), 5000);
        },
        
        do_follow: function () {
            this.$element.find('button.oe_mail_action_unfollow').show();
            this.$element.find('button.oe_mail_action_follow').hide();
            return this.ds_sub.create({'res_model': this.view.model, 'user_id': this.session.uid, 'res_id': this.view.datarecord.id}).then();
        },
        
        do_unfollow: function () {
            this.$element.find('button.oe_mail_action_follow').show();
            this.$element.find('button.oe_mail_action_unfollow').hide();
            return this.ds.call('message_unsubscribe', [[this.view.datarecord.id]]).then();
        },
        
        do_comment: function () {
            var body_text = this.$element.find('textarea').val();
            return this.ds.call('message_append_note', [[this.view.datarecord.id], 'Reply comment', body_text, type='comment']).then(
                this.proxy('fetch_messages'));
        },
    });
    
    /* Add WallView widget to registry */
    session.web.client_actions.add('mail.all_feeds', 'session.mail.WallView');
    
    /* WallView widget: a wall of messages */
    mail.WallView = session.web.Widget.extend({
        // QWeb template to use when rendering the object
        template: 'WallView',

        init: function() {
            this._super.apply(this, arguments);
            alert('Cacaboudin !!');
        },
    });
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
