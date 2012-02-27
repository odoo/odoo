openerp.mail = function(session) {
    
    var mail = session.mail = {};

    /* Add ThreadDisplay widget to registry */
    session.web.form.widgets.add(
        'ThreadDisplay', 'openerp.mail.ThreadDisplay');
    session.web.page.readonly.add(
        'ThreadDisplay', 'openerp.mail.ThreadDisplay');

    /* ThreadDisplay widget: display a thread of comments */
    mail.ThreadDisplay = session.web.Widget.extend({
        // QWeb template to use when rendering the object
        template: 'ThreadDisplay',
        
        init: function(parent, params) {
            this._super(parent);
            this.res_model = params['res_model'];
            this.res_id = params['res_id'];
            this.uid = params['uid'];
            this.limit = params['limit'] || 10;
            this.offset = params['offset'] || 0;
            this.cur_limit = this.limit;
            this.records = params['records'] || false;
            // tmp
            this.map_hash = {'res.users': []};
            /* DataSets */
            this.ds = new session.web.DataSet(this, this.res_model);
            this.ds_users = new session.web.DataSet(this, 'res.users');
        },
        
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            /* bind buttons */
            this.$element.find('button.oe_mail_button_comment').bind('click', function () { self.do_comment(); });
            /* delegate links */
            self.$element.find('div.oe_mail_thread_display').delegate('a', 'click', function (event) {
                var res_model = event.srcElement.dataset.resModel;
                var res_id = event.srcElement.dataset.resId;
                self.do_action({
                    type: 'ir.actions.act_window',
                    res_model: res_model,
                    res_id: parseInt(res_id),
                    views: [[false, 'form']]
                });
            });
            /* display user, fetch comments */
            this.display_current_user();
            if (this.records == false) return this.fetch_comments();
            else return this.display_comments(this.records);
        },
        
        stop: function () {
            this._super.apply(this, arguments);
        },
        
        fetch_comments: function () {
            return this.ds.call('message_load', [[this.res_id]]).then(this.proxy('display_comments'));
        },
        
        display_comments: function (records) {
            var self = this;
            this.$element.find('div.oe_mail_thread_display').empty();
            /* WIP: map matched regexp -> records to browse with name */
            _(records).each(function (record) {
                self.check_internal_links(record.body_text);
            });
            //console.log(this.map_hash);
            _(records).each(function (record) {
                if (record.type == 'email') { record.mini_url = ('/mail/static/src/img/email_icon.png'); }
                else { record.mini_url = self.thread_get_avatar_mini('res.users', 'avatar_mini', record.user_id[0]); }
                record.body_text = self.do_replace_internal_links(record.body_text);
                var render_res = session.web.qweb.render('ThreadMsg', {
                    'record': record,
                    });
                $(render_res).appendTo(self.$element.find('div.oe_mail_thread_display'));
            });
            // add and bind "more button"
            $(session.web.qweb.render('MoreButton', {})).appendTo(self.$element.find('div.oe_mail_thread_display'));
            this.$element.find('button.oe_mail_button_more').bind('click', function () { self.do_more(); });
        },
        
        display_current_user: function () {
            $('<div>').html(
                '<img src="' + this.thread_get_avatar_mini('res.users', 'avatar_mini', this.uid) + '"/>'
                ).appendTo(this.$element.find('div.oe_mail_msg_image'));
        },
        
        do_comment: function () {
            var body_text = this.$element.find('textarea').val();
            return this.ds.call('message_append_note', [[this.res_id], 'Reply comment', body_text, type='comment']).then(
                this.proxy('fetch_comments'));
        },
        
        do_more: function () {
            console.log('do more !');
        },
        
        do_replace_internal_links: function (string) {
            var self = this;
            /* internal links: @sale.order,32 */
            var regex_intlink = new RegExp(/(^|\s)@(\w*[a-zA-Z_]+\w*)\.(\w+[a-zA-Z_]+\w*),(\d+)/g);
            var regex_res = regex_intlink.exec(string);
            while (regex_res != null) {
                var res_model = regex_res[2] + '.' + regex_res[3];
                var res_id = regex_res[4];
                string = string.replace(regex_res[0], '' + regex_res[1] + '<a href="#" data-res-model = ' + res_model + ' data-res-id = ' + res_id + '>'
                    + res_model + '(' + res_id + ')</a>');
                regex_res = regex_intlink.exec(string);
            }
            /* shortcut to user: @login */
            //var regex_login = new RegExp(/(^|\s)@(\w*[a-zA-Z_.]+\w*)/g);
            //var regex_res = regex_login.exec(string);
            //while (regex_res != null) {
                //var res_model = regex_res[2] + '.' + regex_res[3];
                //var res_id = regex_res[4];
                //string = string.replace(regex_res[0], '' + regex_res[1] + '<a href="#" data-res-model = ' + res_model + ' data-res-id = ' + res_id + '>'
                    //+ res_model + '(' + res_id + ')</a>');
                //regex_res = regex_intlink.exec(string);
            //}
            return string;
        },
        
        /* check for internal links, and map them to limitate number of queries -- WIP, probably not useful */
        check_internal_links: function(string) {
            /* shortcut to user: @login */
            var regex_login = new RegExp(/(^|\s)@(\w*[a-zA-Z_.]+\w*\s)/g);
            var regex_res = regex_login.exec(string);
            while (regex_res != null) {
                var login = regex_res[2];
                this.map_hash['res.users'].push(login);
                regex_res = regex_login.exec(string);
            }
            /* internal links: @res.model,name */
            var regex_intlink = new RegExp(/(^|\s)@(\w*[a-zA-Z_]+\w*)\.(\w+[a-zA-Z_]+\w*),(\w+)/g);
            regex_res = regex_intlink.exec(string);
            while (regex_res != null) {
                var res_model = regex_res[2] + '.' + regex_res[3];
                var res_name = regex_res[4];
                if (! (res_model in this.map_hash)) { this.map_hash[res_model] = []; }
                this.map_hash[res_model].push(res_name);
                regex_res = regex_intlink.exec(string);
            }
        },
        
        thread_get_avatar_mini: function(model, field, id) {
            return this.session.prefix + '/web/binary/image?session_id=' + this.session.session_id + '&model=' + model + '&field=' + field + '&id=' + (id || '');
        },
    });


    /* Add ThreadView widget to registry */
    session.web.form.widgets.add(
        'ThreadView', 'openerp.mail.ThreadView');
    session.web.page.readonly.add(
        'ThreadView', 'openerp.mail.ThreadView');

    /* ThreadView widget: thread of comments */
    mail.ThreadView = session.web.form.Field.extend({
        // QWeb template to use when rendering the object
        form_template: 'Thread',

        init: function() {
            this.is_sub = 0;
            this.see_sub = 0;
            this._super.apply(this, arguments);
            this.thread_display = null;
            /* DataSets */
            this.ds = new session.web.DataSet(this, this.view.model);
            this.ds_users = new session.web.DataSet(this, 'res.users');
        },

        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            /* bind and hide buttons */
            self.$element.find('button.oe_mail_button_followers').bind('click', function () { self.do_toggle_followers(); });
            self.$element.find('button.oe_mail_button_follow').bind('click', function () { self.do_follow(); }).hide();
            self.$element.find('button.oe_mail_button_unfollow').bind('click', function () { self.do_unfollow(); }).hide();
        },

        stop: function () {
            this._super.apply(this, arguments);
        },
        
        set_value: function() {
            var self = this;
            this._super.apply(this, arguments);
            /* hide follow/unfollow/see followers buttons */
            self.$element.find('button.oe_mail_button_follow').hide();
            self.$element.find('button.oe_mail_button_unfollow').hide();
            if (! this.view.datarecord.id) { return; }
            /* find wich (un)follow buttons to show */
            var call_res = this.ds.call('message_is_subscriber', [[this.view.datarecord.id]]).then(function (records) {
                if (records == true) { self.is_sub = 1; self.$element.find('button.oe_mail_button_unfollow').show(); }
                else { self.is_sub = 0; self.$element.find('button.oe_mail_button_follow').show(); }
                });
            /* fetch subscribers */
            this.fetch_subscribers();
            /* create ThreadDisplay widget and render it */
            this.$element.find('div.oe_mail_thread_left').empty();
            this.thread_display = new mail.ThreadDisplay(this, {'res_model': this.view.model, 'res_id': this.view.datarecord.id, 'uid': this.session.uid});
            this.thread_display.appendTo(this.$element.find('div.oe_mail_thread_left'));
        },
        
        fetch_subscribers: function () {
            var follow_res = this.ds.call('message_get_subscribers', [[this.view.datarecord.id]]).then(
                this.proxy('display_subscribers'));
            this.$element.find('div.oe_mail_followers_display').hide();
            return follow_res;
        },
        
        display_subscribers: function (records) {
            this.$element.find('div.oe_mail_followers_display').empty();
            var self = this;
            _(records).each(function (record) {
                $('<div class="oe_mail_followers_vignette">').html(
                    '<img src="' + self.thread_get_avatar_mini('res.users', 'avatar_mini', record.id) + '" title="' + record.name + '" alt="' + record.name + '"/>'
                    ).appendTo(self.$element.find('div.oe_mail_followers_display'));
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
        
        do_toggle_follow: function () {
            this.is_sub = 1 - this.is_sub;
            this.$element.find('button.oe_mail_button_unfollow').toggle();
            this.$element.find('button.oe_mail_button_follow').toggle();
        },
        
        do_toggle_followers: function () {
            this.see_sub = 1 - this.see_sub;
            if (this.see_sub == 1) { this.$element.find('button.oe_mail_button_followers').html('Hide followers'); }
            else { this.$element.find('button.oe_mail_button_followers').html('Display followers'); }
            this.$element.find('div.oe_mail_followers_display').toggle();
        },
        
        thread_get_avatar_mini: function(model, field, id) {
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
        template: 'Wall',

        init: function (parent, params) {
            this._super(parent);
            this.filter_search = params['filter_search'];
            this.search = {}
            /* DataSets */
            this.ds_msg = new session.web.DataSet(this, 'mail.message');
            this.ds_thread = new session.web.DataSet(this, 'mail.thread');
            this.ds_users = new session.web.DataSet(this, 'res.users');
        },

        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.$element.find('button.oe_mail_button_comment').bind('click', function () { self.do_comment(); });   
            /* load mail.message search view */
            var search_view_loaded = this.load_search_view();
            var search_view_ready = $.when(search_view_loaded).then(function () {
                self.searchview.on_search.add(self.do_searchview_search);
            });
            /* fetch comments */
            var comments_ready = this.fetch_comments();
            return (search_view_ready && comments_ready);
        },
        
        stop: function () {
            this._super.apply(this, arguments);
        },
        
        load_search_view: function (view_id, defaults, hidden) {
            this.searchview = new session.web.SearchView(this, this.ds_msg, view_id || false, defaults || {}, hidden || false);
            return this.searchview.appendTo(this.$element.find('div.oe_mail_wall_search'));
        },
        
        do_searchview_search: function(domains, contexts, groupbys) {
            var self = this;
            this.rpc('/web/session/eval_domain_and_context', {
                domains: domains || [],
                contexts: contexts || [],
                group_by_seq: groupbys || []
            }, function (results) {
                self.search['context'] = results.context;
                self.search['domain'] = results.domain;
                self.search['groupby'] = results.group_by;
                self.fetch_comments(self.search['domain'], self.search['context']);
            });
        },
        
        fetch_comments: function (domain, context, offset, limit) {
            var load_res = this.ds_thread.call('get_pushed_messages',
                [[this.session.uid], limit = (limit || 100), offset = (offset || 0), domain = (domain || null), context = (context || null) ]).then(
                    this.proxy('display_comments'));
            return load_res;
        },
        
        display_comments: function (records) {
            this.$element.find('div.oe_mail_wall_threads').empty();
            sorted_records = this.sort_comments(records);
            var self = this;
            _(sorted_records).each(function (rec_models, model) { // each model
                _(rec_models).each(function (record_id, id) { // each record
                    var template = 'WallThreadContainer';
                    var render_res = session.web.qweb.render(template, {
                        'record_model': model,
                        'record_id': id,
                    });
                    $('<div class="oe_mail_wall_thread">').html(render_res).appendTo(self.$element.find('div.oe_mail_wall_threads'));
                    self.thread_display = new mail.ThreadDisplay(self,
                        {'res_model': model, 'res_id': parseInt(id), 'uid': self.session.uid, 'records': record_id}
                        );
                    self.thread_display.appendTo(self.$element.find('div.oe_mail_wall_thread_content:last'));
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
