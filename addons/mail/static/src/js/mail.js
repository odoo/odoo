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
            this.is_sub = 0;
            this.see_sub = 1;
            this._super.apply(this, arguments);
            /* DataSets */
            this.ds = new session.web.DataSet(this, this.view.model);
            this.ds_users = new session.web.DataSet(this, 'res.users');
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
                if (records == true) { self.is_sub = 1; self.$element.find('button.oe_mail_button_unfollow').show(); }
                else { self.is_sub = 0; self.$element.find('button.oe_mail_button_follow').show(); }
                });
            console.log(this);
            /* fetch comments and subscribers */
            this.fetch_current_user();
            this.fetch_subscribers();
            return this.fetch_comments();
        },
        
        fetch_current_user: function ()  {
            return this.ds_users.read_ids([this.session.uid], ['id', 'name', 'avatar_mini']).then(
                this.proxy('display_current_user'));
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
        
        display_current_user: function (records) {
            $('<div>').html(
                    '<img src="' + this.thread_get_mini('res.users', 'avatar_mini', records[0].id) + '" title="' + records[0].name + '" alt="' + records[0].name + '"/>'
                    ).appendTo(this.$element.find('div.oe_mail_msg_image'));
        },
        
        display_comments: function (records) {
            this.$element.find('div.oe_mail_msg').empty();
            var self = this;
            _(records).each(function (record) {
                record.mini_url = self.thread_get_mini('res.users', 'avatar_mini', record.user_id[0]);
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
                $('<div class="oe_mail_followers_vignette">').html(
                    '<img src="' + self.thread_get_mini('res.users', 'avatar_mini', record.id) + '" title="' + record.name + '" alt="' + record.name + '"/>'
                    ).appendTo(self.$element.find('div.oe_mail_followers'));
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
            this.is_sub = 1 - this.is_sub;
            this.$element.find('button.oe_mail_button_unfollow').toggle();
            this.$element.find('button.oe_mail_button_follow').toggle();
        },
        
        do_toggle_followers: function () {
            this.see_sub = 1 - this.see_sub;
            if (this.see_sub == 1) { this.$element.find('button.oe_mail_button_followers').html('Hide followers'); }
            else { this.$element.find('button.oe_mail_button_followers').html('Display followers'); }
            this.$element.find('div.oe_mail_followers').toggle();
        },

        thread_get_mini: function(model, field, id) {
            id = id || '';
            var url = this.session.prefix + '/web/binary/image?session_id=' + this.session.session_id + '&model=' + model + '&field=' + field + '&id=' + id;
            return url;
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
            this.ds_users = new session.web.DataSet(this, 'res.users');
        },

        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            self.$element.find('button.oe_mail_button_comment').bind('click', function () { self.do_comment(); });
            return this.fetch_comments();
        },
        
        stop: function () {
            this._super();
        },

        fetch_comments: function () {
            var load_res = this.ds_msg.call('get_pushed_messages', [[this.session.uid]]).then(
                this.proxy('display_comments'));
            return load_res;
        },
        
        display_comments: function (records) {
            this.$element.find('div.oe_mail_msg').empty();
            sorted_records = this.sort_comments(records);
            var self = this;
            _(sorted_records).each(function (rec_models, model) { // each model
                _(rec_models).each(function (record_id, id) { // each record
                    var template = 'WallThreadView';
                    var render_res = session.web.qweb.render(template, {
                        'record_model': model,
                        'record_id': id,
                    });
                    $('<div class="oe_mail_thread">').html(render_res).appendTo(self.$element.find('div.oe_mail_msg'));
                    _(record_id).each(function (record) { // each record
                        record.mini_url = self.thread_get_mini('res.users', 'avatar_mini', record.user_id[0]);
                        var template = 'ThreadMsgView';
                        var render_res = session.web.qweb.render(template, {
                            'record': record,
                            });
                        $('<div class="oe_mail_comment">').html(render_res).appendTo(self.$element.find('div.oe_mail_thread_content:last'));
                    });
                });
            });
        },

        sort_comments: function (records) {
            sorted_comments = {};
            _(records).each(function (record) {
                if (! (record.model in sorted_comments)) { sorted_comments[record.model] = {}; }
                if (! (record.res_id in sorted_comments[record.model])) {
                    sorted_comments[record.model][record.res_id] = []; }
                sorted_comments[record.model][record.res_id].push(record);
            });
            return sorted_comments;
        },

        do_comment: function () {
            var body_text = this.$element.find('textarea').val();
            return this.ds_users.call('message_append_note', [[this.session.uid], 'Tweet', body_text, type='comment']).then(
                this.proxy('fetch_comments'));
        },

        thread_get_mini: function(model, field, id) {
            id = id || '';
            var url = this.session.prefix + '/web/binary/image?session_id=' + this.session.session_id + '&model=' + model + '&field=' + field + '&id=' + id;
            return url;
        },
    });
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
