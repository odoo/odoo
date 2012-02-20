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
        form_template: 'ThreadView',
        
        init: function() {
            this.follow_state = 0;
            this._super.apply(this, arguments);
            /* DataSets */
            this.ds = new session.web.DataSet(this, this.view.model);
        },
        
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            /* bind buttons */
            self.$element.find('button.oe_mail_button_comment').bind('click', function () { self.do_comment(); });
            self.$element.find('button.oe_mail_button_followers').bind('click', function () { self.do_toggle_followers(); });
            self.$element.find('button.oe_mail_button_follow').bind('click', function () { self.do_follow(); });
            self.$element.find('button.oe_mail_button_unfollow').bind('click', function () { self.do_unfollow(); });
            /* hide follow/unfollow buttons */
            self.$element.find('button.oe_mail_button_follow').hide();
            self.$element.find('button.oe_mail_button_unfollow').hide();
        },
        
        stop: function () {
            console.log('stop');
            this._super.apply(this, arguments);
        },
        
        set_value: function() {
            var self = this;
            this._super.apply(this, arguments);
            /* hide follow/unfollow buttons */
            self.$element.find('button.oe_mail_button_follow').hide();
            self.$element.find('button.oe_mail_button_unfollow').hide();
            if (! this.view.datarecord.id) { return; }
            /* find wich (un)follow buttons to show */
            var call_res = this.ds.call('message_is_subscriber', [[this.view.datarecord.id]]).then(function (records) {
                if (records == true) { self.follow_state = 1; self.$element.find('button.oe_mail_button_unfollow').show(); }
                else { self.follow_state = 0; self.$element.find('button.oe_mail_button_follow').show(); }
                });
            /* fetch comments and subscribers */
            this.fetch_subscribers();
            return this.fetch_comments();
        },
        
        fetch_comments: function () {
            var load_res = this.ds.call('message_load', [[this.view.datarecord.id]]).then(
                this.proxy('display_comments'));
            return load_res;
        },
        
        fetch_subscribers: function () {
            var follow_res = this.ds.call('message_get_subscribers', [[this.view.datarecord.id]]).then(
                this.proxy('display_followers'));
            return follow_res;
        },
        
        display_comments: function (records) {
            this.$element.find('div.oe_mail_msg').empty();
            var self = this;
            _(records).each(function (record) {
                var template = 'ThreadMsgView';
                var render_res = session.web.qweb.render(template, {
                    'record': record,
                    });
                $('<div class="oe_mail_comment">').html(render_res).appendTo(self.$element.find('div.oe_mail_msg'));
            });
        },
        
        display_followers: function (records) {
            this.$element.find('div.oe_mail_followers').empty();
            var self = this;
            _(records).each(function (record) {
//                 <div class="oe_mail_followers_vignette" title="Raoul Grobedon"><img src="people.png"/></div>
                //$('<div class="oe_mail_followers_vignette">').text(record.user_id[1]).appendTo(self.$element.find('div.oe_mail_followers'));
                $('<div class="oe_mail_followers_vignette">').text(record.name).appendTo(self.$element.find('div.oe_mail_followers'));
            });
        },
        
        do_follow: function () {
            this.do_toggle_follow();
            return this.ds.call('message_subscribe', [[this.view.datarecord.id]]).then();
        },
        
        do_unfollow: function () {
            this.do_toggle_follow();
            return this.ds.call('message_unsubscribe', [[this.view.datarecord.id]]).then();
        },
        
        do_comment: function () {
            var body_text = this.$element.find('textarea').val();
            return this.ds.call('message_append_note', [[this.view.datarecord.id], 'Reply comment', body_text, type='comment']).then(
                this.proxy('fetch_comments'));
        },
        
        do_toggle_follow: function () {
            this.follow_state = 1 - this.follow_state;
            this.$element.find('button.oe_mail_button_unfollow').toggle();
            this.$element.find('button.oe_mail_button_follow').toggle();
        },
        
        do_toggle_followers: function () {
            this.$element.find('div.oe_mail_followers').toggle();
        },
    });
    
    /* Add WallView widget to registry */
    session.web.client_actions.add('mail.all_feeds', 'session.mail.WallView');
    
    /* WallView widget: a wall of messages */
    mail.WallView = session.web.Widget.extend({
        // QWeb template to use when rendering the object
        template: 'WallView',

        init: function (parent, params) {
            this._super(parent);
            this.filter_search = params['filter_search'];
            /* DataSets */
            this.ds_msg = new session.web.DataSet(this, 'mail.message');
        },

        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            console.log(this);
            self.$element.find('button.oe_mail_action_comment').bind('click', function () { self.do_comment(); });
            this.ds_msg.call('get_pushed_messages', [[], self.filter_search]).then(
                this.proxy('display_records'));
        },
        
        stop: function () {
            this._super();
        },

        fetch_messages: function () {
            console.log('debug--fetch_messages');
            return this.ds_msg.call('get_pushed_messages', []).then(
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

        do_comment: function () {
            var body_text = this.$element.find('textarea').val();
            return this.ds.call('message_append_note', [[this.view.datarecord.id], 'Reply comment', body_text, type='comment']).then(
                this.proxy('fetch_messages'));
        },
    });
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
