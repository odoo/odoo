openerp.mail = function(session) {
    
    var mail = session.mail = {};

    /* Add ThreadDisplay widget to registry */
    session.web.form.widgets.add(
        'Thread', 'openerp.mail.Thread');
    session.web.page.readonly.add(
        'Thread', 'openerp.mail.Thread');

    /** 
     * ThreadDisplay widget: this widget handles the display of a thread of messages.
     * Two displays are managed through the [thread_level] parameter that sets
     * the level number in the thread:
     * - root message
     * - - sub message (parent_id = root message)
     * - - - sub sub message (parent id = sub message)
     * - - sub message (parent_id = root message)
     * This widget has 2 ways of initialization, either you give records to be rendered,
     * either it will fetch [limit] messages related to [res_model]:[res_id].
     */
    mail.Thread = session.web.Widget.extend({
        template: 'Thread',

        /**
         *
         * @param {Object} parent parent
         * @param {Object} [params]
         * @param {String} [params.res_model] res_model of mail.thread object
         * @param {Number} [params.res_id] res_id of record
         * @param {Number} [params.parent_id=false] parent_id of message
         * @param {Number} [params.uid] user id
         * @param {Number} [params.thread_level=0] number of levels in the thread (only 0 or 1 currently)
         * @param {Number} [params.msg_more_limit=100] number of character to display before having a "show more" link;
         *                                             note that the text will not be truncated if it does not have 110% of
         *                                             the parameter (ex: 110 characters needed to be truncated and be displayed
         *                                             as a 100-characters message)
         * @param {Number} [params.limit=10] maximum number of messages to fetch
         * @param {Number} [params.offset=0] offset for fetching messages
         * @param {Number} [params.records=null] records to show instead of fetching messages
         */
        init: function(parent, params) {
            this._super(parent);
            this.params = params;
            this.params.parent_id = this.params.parent_id || false;
            this.params.thread_level = this.params.thread_level || 0;
            this.params.msg_more_limit = this.params.msg_more_limit || 100;
            this.params.limit = this.params.limit || 2;
            this.params.offset = this.params.offset || 0;
            this.params.records = this.params.records || null;
            /* DataSets and internal vars */
            this.map_hash = {};
            this.display_show_more = true;
            this.ds = new session.web.DataSet(this, this.params.res_model);
            this.ds_users = new session.web.DataSet(this, 'res.users');
        },
        
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            /* events */
            this.$element.find('p.oe_mail_p_nomore').hide();
            this.$element.find('button.oe_mail_button_comment').bind('click', function () { self.do_comment(); });
            this.$element.find('button.oe_mail_button_more').bind('click', function () { self.do_more(); });
            this.$element.find('div.oe_mail_thread_display').delegate('a.intlink', 'click', function (event) {
                // lazy implementation: fetch data and try to redirect
                if (! event.srcElement.dataset.resModel) return false;
                else var res_model = event.srcElement.dataset.resModel;
                var res_login = event.srcElement.dataset.resLogin;
                var res_id = event.srcElement.dataset.resId;
                if ((! res_login) && (! res_id)) return false;
                if (! res_id) {
                    var ds = new session.web.DataSet(self, res_model);
                    var defer = ds.call('search', [[['login', '=', res_login]]]).then(function (records) {
                        if (records[0]) {
                            self.do_action({ type: 'ir.actions.act_window', res_model: res_model, res_id: parseInt(records[0]), views: [[false, 'form']]});
                        }
                        else return false;
                    });
                }
                else self.do_action({ type: 'ir.actions.act_window', res_model: res_model, res_id: parseInt(res_id), views: [[false, 'form']]});
            });
            /* display user, fetch comments */
            this.display_current_user();
            if (this.params.records) return this.display_comments(this.params.records);
            else return this.init_comments();
        },
        
        stop: function () {
            //this._super.apply(this, arguments);
        },
        
        init_comments: function() {
            var self = this;
            this.params.offset = 0;
            this.$element.find('div.oe_mail_thread_display').empty();
            return this.fetch_comments(this.params.limit, this.params.offset).then();
        },
        
        fetch_comments: function (limit, offset) {
            var self = this;
            var defer = this.ds.call('message_load', [[this.params.res_id], limit=(limit||this.params.limit), offset=(offset||this.params.offset)]);
            $.when(defer).then(function (records) {
                if (records.length < self.params.limit) self.params.thread_show_more = false;
                self.display_comments(records);
                if (self.params.thread_show_more == true) {
                    self.$element.find('button.oe_mail_button_more').show();
                    self.$element.find('p.oe_mail_p_nomore').hide(); }
                else {
                    self.$element.find('button.oe_mail_button_more').hide();
                    self.$element.find('p.oe_mail_p_nomore').show(); }
                });
            return defer;
        },

        display_comments: function (records) {
            var self = this;
            var sorted_comments = this.sort_comments(records);
            this.sorted_comments = sorted_comments;
            
            /* WIP: map matched regexp -> records to browse with name */
            //_(records).each(function (record) {
                //self.do_check_internal_links(record.body_text);
            //});
            
            _(records).each(function (record) {
                var sub_msgs = [];
                if ((record.parent_id == false || record.parent_id[0] == self.params.parent_id) && self.params.thread_level > 0 ) {
                    var sub_list = self.sorted_comments['root_id_msg_list'][record.id];
                    _(records).each(function (record) {
                        if (record.parent_id == false || record.parent_id[0] == self.params.parent_id) return;
                        if (_.indexOf(_.pluck(sub_list, 'id'), record.id) != -1) {
                            sub_msgs.push(record);
                        }
                    });
                    self.display_comment(record);
                    self.thread = new mail.Thread(self, {'res_model': self.params.res_model, 'res_id': self.params.res_id, 'uid': self.params.uid,
                                                            'records': sub_msgs, 'thread_level': (self.params.thread_level-1), 'parent_id': record.id});
                    self.$element.find('div.oe_mail_thread_msg:last').append('<div class="oe_mail_thread_subthread"/>');
                    self.thread.appendTo(self.$element.find('div.oe_mail_thread_subthread:last'));
                }
                else if (self.params.thread_level == 0) {
                    self.display_comment(record);
                }
            });
            // update offset for "More" buttons
            this.params.offset += records.length;
        },

        /**
         * Display a record
         */
        display_comment: function (record) {
            if (record.type == 'email') { record.mini_url = ('/mail/static/src/img/email_icon.png'); }
            else { record.mini_url = this.thread_get_avatar_mini('res.users', 'avatar_mini', record.user_id[0]); }    
            // body text manipulation
            record.body_text = this.do_clean_text(record.body_text);
            record.tr_body_text = this.do_truncate_string(record.body_text, this.params.msg_more_limit);
            record.body_text = this.do_replace_internal_links(record.body_text);
            if (record.tr_body_text) record.tr_body_text = this.do_replace_internal_links(record.tr_body_text);
            // render
            $(session.web.qweb.render('ThreadMsg', {'record': record})).appendTo(this.$element.children('div.oe_mail_thread_display:first'));    
            // truncated: hide full-text, show summary, add buttons
            if (record.tr_body_text) {
                var node_body = this.$element.find('span.oe_mail_msg_body:last').append(' <a href="#" class="reduce">[ ... Show less]</a>');
                var node_body_short = this.$element.find('span.oe_mail_msg_body_short:last').append(' <a href="#" class="expand">[ ... Show more]</a>');
                node_body.hide();
                node_body.find('a:last').click(function() { node_body.hide(); node_body_short.show(); return false; });
                node_body_short.find('a:last').click(function() { node_body_short.hide(); node_body.show(); return false; });
            }
        },
       
        /**
         * Add records to sorted_comments array
         * @param {Array} records records from mail.message sorted by date desc
         * @returns {Object} sc sorted_comments: dict {
         *                          'root_id_list': list or root_ids
         *                          'root_id_msg_list': {'record_id': [ancestor_ids]}, still sorted by date desc
         *                          'id_to_root': {'root_id': [records]}, still sorted by date desc
         *                          }
         */
        sort_comments: function (records) {
            var self = this;
            sc = {'root_id_list': [], 'root_id_msg_list': {}, 'id_to_root': {}}
            var cur_iter = 0; var max_iter = 10; var modif = true;
            /* step1: get roots */
            while ( modif && (cur_iter++) < max_iter) {
                modif = false;
                _(records).each(function (record) {
                    if ( (record.parent_id == false || record.parent_id[0] == self.params.parent_id) && (_.indexOf(sc['root_id_list'], record.id) == -1)) {
                        sc['root_id_list'].push(record.id);
                        sc['root_id_msg_list'][record.id] = [];
                        modif = true;
                    } 
                    else {
                        if (_.indexOf(sc['root_id_list'], record.parent_id[0]) != -1) {
                             sc['id_to_root'][record.id] = record.parent_id[0];
                             modif = true;
                        }
                        else if ( sc['id_to_root'][record.parent_id[0]] ) {
                             sc['id_to_root'][record.id] = sc['id_to_root'][record.parent_id[0]];
                             modif = true;
                        }
                    }
                });
            }
            /* step2: add records */
            _(records).each(function (record) {
                var root_id = sc['id_to_root'][record.id];
                if (! root_id) return;
                sc['root_id_msg_list'][root_id].push(record);
            });
            return sc;
        },
        
        display_current_user: function () {
            return this.$element.find('div.oe_mail_msg_image').empty().html(
                '<img src="' + this.thread_get_avatar_mini('res.users', 'avatar_mini', this.params.uid) + '"/>');
        },
        
        do_comment: function () {
            var body_text = this.$element.find('textarea').val();
            console.log(body_text + '-' + this.params.parent_id);
            return true;
            //return this.ds.call('message_append_note', [[this.params.res_id], 'Reply comment', body_text, parent_id=this.params.parent_id, type='comment']).then(
                //this.proxy('init_comments'));
        },
        
        do_more: function () {
            return this.fetch_comments(this.params.limit, this.params.offset);
        },
        
        do_replace_internal_links: function (string) {
            var self = this;
            /* shortcut to user: @login */
            var regex_login = new RegExp(/(^|\s)@(\w*)/g);
            var regex_res = regex_login.exec(string);
            while (regex_res != null) {
                var login = regex_res[2];
                string = string.replace(regex_res[0], '<a href="#" class="intlink" data-res-model="res.users" data-res-login = ' + login + '>@' + login + '</a>');
                regex_res = regex_login.exec(string);
            }
            return string;
        },
        
        thread_get_avatar_mini: function(model, field, id) {
            return this.session.prefix + '/web/binary/image?session_id=' + this.session.session_id + '&model=' + model + '&field=' + field + '&id=' + (id || '');
        },
        
        do_truncate_string: function(string, max_length) {
            if (string.length <= (max_length * 1.2)) return false;
            else return string.slice(0, max_length);
        },
        
        do_clean_text: function (string) {
            var html = $('<div/>').text(string.replace(/\s+/g, ' ')).html().replace(new RegExp('&lt;(/)?b\\s*&gt;', 'gi'), '<$1b>');
            return html;
        },
        
        /**
         *
         * var regex_login = new RegExp(/(^|\s)@(\w*[a-zA-Z_.]+\w*\s)/g);
         * var regex_login = new RegExp(/(^|\s)@(\w*)/g);
         * var regex_intlink = new RegExp(/(^|\s)#(\w*[a-zA-Z_]+\w*)\.(\w+[a-zA-Z_]+\w*),(\w+)/g);
         */
        do_check_internal_links: function(string) {
            /* shortcut to user: @login */
            var regex_login = new RegExp(/(^|\s)@(\w*)/g);
            var regex_res = regex_login.exec(string);
            while (regex_res != null) {
                var login = regex_res[2];
                if (! ('res.users' in this.map_hash)) { this.map_hash['res.users']['name'] = []; }
                this.map_hash['res.users']['login'].push(login);
                regex_res = regex_login.exec(string);
            }
            /* internal links: #res.model,name */
            var regex_intlink = new RegExp(/(^|\s)#(\w*[a-zA-Z_]+\w*)\.(\w+[a-zA-Z_]+\w*),(\w+)/g);
            regex_res = regex_intlink.exec(string);
            while (regex_res != null) {
                var res_model = regex_res[2] + '.' + regex_res[3];
                var res_name = regex_res[4];
                if (! (res_model in this.map_hash)) { this.map_hash[res_model]['name'] = []; }
                this.map_hash[res_model]['name'].push(res_name);
                regex_res = regex_intlink.exec(string);
            }
        },

    });


    /* Add ThreadView widget to registry */
    session.web.form.widgets.add(
        'ThreadView', 'openerp.mail.RecordThread');
    session.web.page.readonly.add(
        'ThreadView', 'openerp.mail.RecordThread');

    /* ThreadView widget: thread of comments */
    mail.RecordThread = session.web.form.Field.extend({
        // QWeb template to use when rendering the object
        form_template: 'RecordThread',

        init: function() {
            this.is_sub = 0;
            this.see_sub = 0;
            this._super.apply(this, arguments);
            this.thread = null;
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
            this.see_sub = 0;
            /* hide follow/unfollow/see followers buttons */
            this.$element.find('button.oe_mail_button_followers').html('Display followers')
            this.$element.find('div.oe_mail_followers_display').hide();
            this.$element.find('button.oe_mail_button_follow').hide();
            this.$element.find('button.oe_mail_button_unfollow').hide();
            if (! this.view.datarecord.id) { return; }
            /* find wich (un)follow buttons to show */
            var fetch_fol_done = this.ds.call('message_is_subscriber', [[this.view.datarecord.id]]).then(function (records) {
                if (records == true) { self.is_sub = 1; self.$element.find('button.oe_mail_button_unfollow').show(); }
                else { self.is_sub = 0; self.$element.find('button.oe_mail_button_follow').show(); }
                });
            /* fetch subscribers */
            var fetch_sub_done = this.fetch_subscribers();
            /* create ThreadDisplay widget and render it */
            this.$element.find('div.oe_mail_recthread_left').empty();
            if (this.thread) this.thread.stop();
            this.thread = new mail.Thread(this, {'res_model': this.view.model, 'res_id': this.view.datarecord.id, 'uid': this.session.uid});
            this.thread.appendTo(this.$element.find('div.oe_mail_recthread_left'));
            return fetch_fol_done && fetch_sub_done;
        },
        
        fetch_subscribers: function () {
            return this.ds.call('message_get_subscribers', [[this.view.datarecord.id]]).then(this.proxy('display_subscribers'));
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
            return this.ds.call('message_subscribe', [[this.view.datarecord.id]]).when();
        },
        
        do_unfollow: function () {
            this.do_toggle_follow();
            return this.ds.call('message_unsubscribe', [[this.view.datarecord.id]]).when();
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
        template: 'Wall',

        /**
         * @param {Object} parent parent
         * @param {Object} [params]
         * @param {Number} [params.limit=20] number of messages to show and fetch
         * @param {Number} [params.search_view_id=false] search view id for messages
         * @var {Array} sorted_comments records sorted by res_model and res_id
         *                  records.res_model = {res_ids}
         *                  records.res_model.res_id = [records]
         */
        init: function (parent, params) {
            this._super(parent);
            this.params = params || {};
            this.params.limit = params.limit || 20;
            this.params.search_view_id = params.search_view_id || false;
            this.params.search = {};
            this.params.domain = [];
            this.sorted_comments = {};
            /* DataSets */
            this.ds_msg = new session.web.DataSet(this, 'mail.message');
            this.ds_thread = new session.web.DataSet(this, 'mail.thread');
            this.ds_users = new session.web.DataSet(this, 'res.users');
        },

        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            /* events and buttons */
            this.$element.find('button.oe_mail_button_comment').bind('click', function () { self.do_comment(); });
            this.$element.find('button.oe_mail_wall_button_more').bind('click', function () { self.do_more(); });
            this.$element.find('div.oe_mail_wall_nomore').hide();
            /* load mail.message search view */
            var search_view_loaded = this.load_search_view(this.params.search_view_id, {}, false);
            var search_view_ready = $.when(search_view_loaded).then(function () {
                self.searchview.on_search.add(self.do_searchview_search);
            });
            /* fetch comments */
            var comments_ready = this.init_comments();
            return (search_view_ready && comments_ready);
        },
        
        stop: function () {
            this._super.apply(this, arguments);
        },

        /**
         * Loads the mail.message search view
         * @param {Number} view_id id of the search view to load
         * @param {Object} defaults ??
         * @param {Boolean} hidden ??
         */
        load_search_view: function (view_id, defaults, hidden) {
            this.searchview = new session.web.SearchView(this, this.ds_msg, view_id || false, defaults || {}, hidden || false);
            return this.searchview.appendTo(this.$element.find('div.oe_mail_wall_search'));
        },

        /**
         * Aggregate the domains, contexts and groupbys in parameter
         * with those from search form, and then calls fetch_comments
         * to actually fetch comments
         * @param {Array} domains
         * @param {Array} contexts
         * @param {Array} groupbys
         */
        do_searchview_search: function(domains, contexts, groupbys) {
            var self = this;
            this.rpc('/web/session/eval_domain_and_context', {
                domains: domains || [],
                contexts: contexts || [],
                group_by_seq: groupbys || []
            }, function (results) {
                self.params.search['context'] = results.context;
                self.params.search['domain'] = results.domain;
                self.params.search['groupby'] = results.group_by;
                self.init_comments(self.params.search['domain'], self.params.search['context']);
            });
        },

        /**
         * Initializes Wall and calls fetch_comments
         * @param {Array} domains
         * @param {Array} contexts
         * @param {Array} groupbys
         * @param {Number} limit number of messages to fetch
         */
        init_comments: function(domain, context, offset, limit) {
            var self = this;
            this.params.domain = [];
            this.sorted_comments = {};
            this.$element.find('div.oe_mail_wall_threads').empty();
            return this.fetch_comments(domain, context, offset, limit);
        },

        /**
         * Fetches Wall comments (mail.thread.get_pushed_messages)
         * @param {Array} domains
         * @param {Array} contexts
         * @param {Array} groupbys
         * @param {Number} limit number of messages to fetch
         */
        fetch_comments: function (domain, context, offset, limit) {
            var load_res = this.ds_thread.call('get_pushed_messages',
                [[this.session.uid], limit = (limit || 2), offset = (offset || 0), domain = (domain || []), context = (context || null) ]).then(
                    this.proxy('display_comments'));
            return load_res;
        },

        /**
         * @param {Array} records records to show in threads
         */
        display_comments: function (records) {
            var sorted_comments = this.sort_comments(records);
            var self = this;
            _(sorted_comments.model_list).each(function (model_name) {
                _(sorted_comments.models[model_name].id_list).each(function (id) {
                    var records = sorted_comments.models[model_name].ids[id];
                    console.log('records to send');
                    console.log(records);
                    var template = 'WallThreadContainer';
                    var render_res = session.web.qweb.render(template, {
                        'record_model': model_name,
                        'record_id': id,
                    });
                    $('<div class="oe_mail_wall_thread">').html(render_res).appendTo(self.$element.find('div.oe_mail_wall_threads'));
                    var thread = new mail.Thread(self, {
                        'res_model': model_name, 'res_id': parseInt(id), 'uid': self.session.uid, 'records': records,
                        'parent_id': false, 'thread_level': 2}
                        );
                    thread.appendTo(self.$element.find('div.oe_mail_wall_thread_content:last'));
                });
            });
            $.extend(true, this.sorted_comments, sorted_comments);
        },

        /**
         * Add records to sorted_comments array
         * @param {Array} records records from mail.message sorted by date desc
         * @returns {Object} sc sorted_comments: dict
         *                      sc.model_list = [record.model names]
         *                      sc.models.model = {
         *                          'id_list': list or root_ids
         *                          'id_to_anc': {'record_id': [ancestor_ids]}, still sorted by date desc
         *                          'ids': {'root_id': [records]}, still sorted by date desc
         *                          }, for each model
         */
        sort_comments: function (records) {
            sc = {'model_list': [], 'models': {}}
            var cur_iter = 0; var max_iter = 10; var modif = true;
            /* step1: get roots */
            while ( modif && (cur_iter++) < max_iter) {
                console.log(cur_iter);
                modif = false;
                _(records).each(function (record) {
                    if ($.inArray(record.model, sc['model_list']) == -1) {
                        sc['model_list'].push(record.model);
                        sc['models'][record.model] = {'id_list': [], 'id_to_anc': {}, 'ids': {}};
                    }
                    var rmod = sc['models'][record.model];
                    if (record.parent_id == false && (_.indexOf(rmod['id_list'], record.id) == -1)) {
                        rmod['id_list'].push(record.id);
                        rmod['ids'][record.id] = [];
                        modif = true;
                    } 
                    else {
                        var test = rmod['id_to_anc'][record.parent_id[0]];
                        if (_.indexOf(rmod['id_list'], record.parent_id[0]) != -1) {
                             rmod['id_to_anc'][record.id] = record.parent_id[0];
                             modif = true;
                        }
                        else if ( test ) {
                             rmod['id_to_anc'][record.id] = test;
                             modif = true;
                        }
                    }
                });
            }
            /* step2: add records */
            _(records).each(function (record) {
                var root_id = sc['models'][record.model]['id_to_anc'][record.id];
                if (! root_id) root_id = record.id;
                sc['models'][record.model]['ids'][root_id].push(record);
            });
            console.log(sc);
            return sc;
        },

        /**
         * Create a domain to fetch new comments according to
         * comment already present in sorted_comments
         * @param {Object} sorted_comments (see sort_comments)
         * @returns {Array} fetch_domain (OpenERP domain style)
         */
        get_fetch_domain: function (sorted_comments) {
            var domain = [];
            _(sorted_comments).each(function (rec_models, model) { //each model
                var ids = [];
                _(rec_models).each(function (record_id, id) { // each record
                    ids.push(id);
                });
                //domain.push('|', ['model', '!=', model], ['res_id', 'not in', ids]);
                domain.push('|', ['model', '!=', model], '!', ['id', 'child_of', ids]);
            });
            return domain;
        },

        /**
         * Action: Posts a comment
         */
        do_comment: function () {
            var body_text = this.$element.find('textarea').val();
            return this.ds_users.call('message_append_note', [[this.session.uid], 'Tweet', body_text, type='comment']).then(
                //this.proxy('fetch_comments'));
                this.init_comments());
        },

        /**
         * Action: Shows more discussions
         */
        do_more: function () {
            var domain = this.get_fetch_domain(this.sorted_comments);
            return this.fetch_comments(domain);
        },

        /**
         * Tools: get avatar mini (TODO: should be moved in some tools ?)
         */
        thread_get_mini: function(model, field, id) {
            return this.session.prefix + '/web/binary/image?session_id=' + this.session.session_id + '&model=' + model + '&field=' + field + '&id=' + (id || '');
        },
    });
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
