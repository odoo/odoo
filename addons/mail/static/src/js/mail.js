openerp.mail = function(session) {
    var _t = session.web._t,
       _lt = session.web._lt;
    
    var mail = session.mail = {};

    /** 
     * Thread widget: this widget handles the display of a thread of
     * messages. The [thread_level] parameter sets the thread level number:
     * - root message
     * - - sub message (parent_id = root message)
     * - - - sub sub message (parent id = sub message)
     * - - sub message (parent_id = root message)
     * This widget has 2 ways of initialization, either you give records to be rendered,
     * either it will fetch [limit] messages related to [res_model]:[res_id].
     */

    /* Add ThreadDisplay widget to registry */
    session.web.form.widgets.add( 'Thread', 'openerp.mail.Thread');

    /* Thread is an extension of a Widget */
    mail.Thread = session.web.Widget.extend({
        template: 'Thread',

        /**
         * @param {Object} parent parent
         * @param {Object} [params]
         * @param {String} [params.res_model] res_model of document [REQUIRED]
         * @param {Number} [params.res_id] res_id of record [REQUIRED]
         * @param {Number} [params.uid] user id [REQUIRED]
         * @param {Bool}   [params.parent_id=false] parent_id of message
         * @param {Number} [params.thread_level=0] number of levels in the thread (only 0 or 1 currently)
         * @param {Bool}   [params.wall=false] thread is displayed in the wall
         * @param {Number} [params.msg_more_limit=150] number of character to display before having a "show more" link;
         *                                             note that the text will not be truncated if it does not have 110% of
         *                                             the parameter (ex: 110 characters needed to be truncated and be displayed
         *                                             as a 100-characters message)
         * @param {Number} [params.limit=100] maximum number of messages to fetch
         * @param {Number} [params.offset=0] offset for fetching messages
         * @param {Number} [params.records=null] records to show instead of fetching messages
         */
        init: function(parent, params) {
            this._super(parent);
            this.params = params;
            this.params.parent_id = this.params.parent_id || false;
            this.params.thread_level = this.params.thread_level || 0;
            this.params.is_wall = this.params.is_wall || this.params.records || false;
            this.params.msg_more_limit = this.params.msg_more_limit || 150;
            this.params.limit = this.params.limit || 100;
            this.params.offset = this.params.offset || 0;
            this.params.records = this.params.records || null;
            // datasets and internal vars
            this.ds = new session.web.DataSet(this, this.params.res_model);
            this.ds_users = new session.web.DataSet(this, 'res.users');
            this.ds_msg = new session.web.DataSet(this, 'mail.message');
            this.comments_structure = {'root_ids': [], 'new_root_ids': [], 'msgs': {}, 'tree_struct': {}, 'model_to_root_ids': {}};
            // display customization vars
            this.display = {};
            this.display.show_post_comment = this.params.show_post_comment || false;
            this.display.show_msg_menu = this.params.is_wall;
            this.display.show_reply = (this.params.thread_level > 0 && this.params.is_wall);
            this.display.show_delete = ! this.params.is_wall;
            this.display.show_hide = this.params.is_wall;
            this.display.show_reply_by_email = ! this.params.is_wall;
            this.display.show_more = (this.params.thread_level == 0);
            // internal links mapping
            this.intlinks_mapping = {};
        },
        
        start: function() {
            this._super.apply(this, arguments);
            // add events
            this.add_events();
            // display user, fetch comments
            this.display_current_user();
            if (this.params.records) var display_done = this.display_comments_from_parameters(this.params.records);
            else var display_done = this.init_comments();
            // customize display
            $.when(display_done).then(this.proxy('do_customize_display'));
            return display_done
        },
        
        do_customize_display: function() {
            if (this.display.show_post_comment) { this.$element.find('div.oe_mail_thread_act').eq(0).show(); }
            if (this.display.show_reply_by_email) { this.$element.find('a.oe_mail_compose').show(); }
            if (! this.display.show_msg_menu) { this.$element.find('img.oe_mail_msg_menu_icon').hide(); }
        },
        
        add_events: function() {
            var self = this;
            // event: click on 'more' at bottom of thread
            this.$element.find('button.oe_mail_button_more').click(function () {
                self.do_more();
            });
            // event: writing in textarea
            this.$element.find('textarea.oe_mail_action_textarea').keyup(function (event) {
                var charCode = (event.which) ? event.which : window.event.keyCode;
                if (event.shiftKey && charCode == 13) { this.value = this.value+"\n"; }
                else if (charCode == 13) { return self.do_comment(); }
            });
            // event: click on 'reply' in msg
            this.$element.find('div.oe_mail_thread_display').delegate('a.oe_mail_msg_reply', 'click', function (event) {
                var act_dom = $(this).parents('div.oe_mail_thread_display').find('div.oe_mail_thread_act:first');
                act_dom.toggle();
                event.preventDefault();
            });
            // event: click on 'delete' in msg
            this.$element.find('div.oe_mail_thread_display').delegate('a.oe_mail_msg_delete', 'click', function (event) {
                if (! confirm(_t("Do you really want to delete this message?"))) { return false; }
                var msg_id = event.srcElement.dataset.id;
                if (! msg_id) return false;
                var call_defer = self.ds_msg.unlink([parseInt(msg_id)]);
                $(event.srcElement).parents('li.oe_mail_thread_msg').eq(0).hide();
                if (self.params.thread_level > 0) {
                    $(event.srcElement).parents('ul.oe_mail_thread').eq(0).hide();
                }
                return false;
            });
            // event: click on 'hide' in msg
            this.$element.find('div.oe_mail_thread_display').delegate('a.oe_mail_msg_hide', 'click', function (event) {
                if (! confirm(_t("Do you really want to hide this thread ?"))) { return false; }
                var msg_id = event.srcElement.dataset.id;
                if (! msg_id) return false;
                var call_defer = self.ds.call('message_remove_pushed_notifications', [[self.params.res_id], [parseInt(msg_id)], true]);
                $(event.srcElement).parents('li.oe_mail_thread_msg').eq(0).hide();
                if (self.params.thread_level > 0) {
                    $(event.srcElement).parents('ul.oe_mail_thread').eq(0).hide();
                }
                return false;
            });
            // event: click on "reply by email" in msg
            this.$element.find('div.oe_mail_thread_display').delegate('a.oe_mail_msg_reply_by_email', 'click', function (event) {
                var msg_id = event.srcElement.dataset.id;
                if (! msg_id) return false;
                self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'mail.compose.message',
                        views: [[false, 'form']],
                        view_type: 'form',
                        view_mode: 'form',
                        target: 'new',
                        context: {'active_model': self.params.res_model, 'active_id': self.params.res_id, 'message_id': msg_id, 'mail.compose.message.mode': 'reply'},
                        key2: 'client_action_multi',
                });
                return false;
            });
            // event: click on 'hide this type' in wheel_menu
            this.$element.find('div.oe_mail_thread_display').delegate('a.oe_mail_msg_hide_type', 'click', function (event) {
                if (! confirm(_t("Do you really want to hide this type of thread ?"))) { return false; }
                var subtype = event.srcElement.dataset.subtype;
                if (! subtype) return false;
                console.log(subtype);
                var call_defer = self.ds.call('message_subscription_hide', [[self.params.res_id], subtype]);
                $(event.srcElement).parents('li.oe_mail_thread_msg').eq(0).hide();
                if (self.params.thread_level > 0) {
                    $(event.srcElement).parents('ul.oe_mail_thread').eq(0).hide();
                }
                return false;
            });
            // event: click on an internal link
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
            // event: click on "send an email"
            this.$element.find('div.oe_mail_thread_act').delegate('a.oe_mail_compose', 'click', function (event) {
                self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'mail.compose.message',
                        views: [[false, 'form']],
                        view_type: 'form',
                        view_mode: 'form',
                        target: 'new',
                        context: {'active_model': self.params.res_model, 'active_id': self.params.res_id, 'mail.compose.message.mode': 'document'},
                        key2: 'client_action_multi',
                });
                return false;
            });
        },
        
        destroy: function () {
            this._super.apply(this, arguments);
        },
        
        init_comments: function() {
            var self = this;
            this.params.offset = 0;
            this.comments_structure = {'root_ids': [], 'new_root_ids': [], 'msgs': {}, 'tree_struct': {}, 'model_to_root_ids': {}};
            this.$element.find('div.oe_mail_thread_display').empty();
            var domain = this.get_fetch_domain(this.comments_structure);
            return this.fetch_comments(this.params.limit, this.params.offset, domain).then();
        },
        
        fetch_comments: function (limit, offset, domain) {
            var self = this;
            var defer = this.ds.call('message_load', [[this.params.res_id], (this.params.thread_level > 0), (this.comments_structure['root_ids']),
                                    (limit+1) || (this.params.limit+1), offset||this.params.offset, domain||undefined ]).then(function (records) {
                if (records.length <= self.params.limit) self.display.show_more = false;
                else { self.display.show_more = true; records.pop(); }
                self.display_comments(records);
                // TODO: move to customize display
                if (self.display.show_more == true) self.$element.find('div.oe_mail_thread_more:last').show();
                else  self.$element.find('div.oe_mail_thread_more:last').hide();
                });
            return defer;
        },

        display_comments_from_parameters: function (records) {
            if (records.length > 0 && records.length < (records[0].child_ids.length+1) ) this.display.show_more = true;
            else this.display.show_more = false;
            var defer = this.display_comments(records);
            // TODO: move to customize display
            if (this.display.show_more == true) $('div.oe_mail_thread_more').eq(-2).show();
            else $('div.oe_mail_thread_more').eq(-2).hide();
            return defer;
        },
        
        display_comments: function (records) {
            var self = this;
            tools_sort_comments(this.comments_structure, records, this.params.parent_id);
            
            /* WIP: map matched regexp -> records to browse with name */
            //_(records).each(function (record) {
                //self.do_check_internal_links(record.body_text);
            //});
            
            _(records).each(function (record) {
                var sub_msgs = [];
                if ((record.parent_id == false || record.parent_id[0] == self.params.parent_id) && self.params.thread_level > 0 ) {
                    var sub_list = self.comments_structure['tree_struct'][record.id]['direct_childs'];
                    _(records).each(function (record) {
                        //if (record.parent_id == false || record.parent_id[0] == self.params.parent_id) return;
                        if (_.indexOf(sub_list, record.id) != -1) {
                            sub_msgs.push(record);
                        }
                    });
                    self.display_comment(record);
                    self.thread = new mail.Thread(self, {'res_model': self.params.res_model, 'res_id': self.params.res_id, 'uid': self.params.uid,
                                                            'records': sub_msgs, 'thread_level': (self.params.thread_level-1), 'parent_id': record.id,
                                                            'is_wall': self.params.is_wall});
                    self.$element.find('li.oe_mail_thread_msg:last').append('<div class="oe_mail_thread_subthread"/>');
                    self.thread.appendTo(self.$element.find('div.oe_mail_thread_subthread:last'));
                }
                else if (self.params.thread_level == 0) {
                    self.display_comment(record);
                }
            });
            // update offset for "More" buttons
            if (this.params.thread_level == 0) this.params.offset += records.length;
        },

        /**
         * Display a record
         */
        display_comment: function (record) {
            record.body = this.do_text_nl2br(record.body, true);
            if (record.type == 'email') { record.mini_url = ('/mail/static/src/img/email_icon.png'); }
            else { record.mini_url = tools_get_image(this.session.prefix, this.session.session_id, 'res.users', 'avatar', record.user_id[0]); }    
            // body text manipulation
            record.body = this.do_clean_text(record.body);
            record.body = this.do_replace_internal_links(record.body);
            // format date according to the user timezone
            record.date = session.web.format_value(record.date, {type:"datetime"});
            // render
            $(session.web.qweb.render('ThreadMsg', {'record': record, 'thread': this, 'params': this.params, 'display': this.display})
                    ).appendTo(this.$element.children('div.oe_mail_thread_display:first'));
            // expand feature
            this.$element.find('span.oe_mail_msg_body:last').expander({slicePoint: this.params.msg_more_limit, moreClass: 'oe_mail_expand', lesClass: 'oe_mail_reduce'});
        },
        
        display_current_user: function () {
            return this.$element.find('img.oe_mail_msg_image').attr('src', tools_get_image(this.session.prefix, this.session.session_id, 'res.users', 'avatar', this.params.uid));
        },
        
        do_comment: function () {
            var comment_node = this.$element.find('textarea');
            var body_text = comment_node.val();
            comment_node.val('');
            return this.ds.call('message_append_note', [[this.params.res_id], 'Reply', body_text, this.params.parent_id, 'comment', 'html', 'comment']).then(
                this.proxy('init_comments'));
        },
        
        /**
         * Create a domain to fetch new comments according to
         * comment already present in comments_structure
         * @param {Object} comments_structure (see tools_sort_comments)
         * @returns {Array} fetch_domain (OpenERP domain style)
         */
        get_fetch_domain: function (comments_structure) {
            var domain = [];
            var ids = comments_structure.root_ids.slice();
            var ids2 = [];
            // must be child of current parent
            if (this.params.parent_id) { domain.push(['id', 'child_of', this.params.parent_id]); }
            _(comments_structure.root_ids).each(function (id) { // each record
                ids.push(id);
                ids2.push(id);
            });
            if (this.params.parent_id != false) {
                ids2.push(this.params.parent_id);
            }
            // must not be children of already fetched messages
            if (ids.length > 0) {
                domain.push('&');
                domain.push('!');
                domain.push(['id', 'child_of', ids]);
            }
            if (ids2.length > 0) {
                domain.push(['id', 'not in', ids2]);
            }
            return domain;
        },
        
        do_more: function () {
            domain = this.get_fetch_domain(this.comments_structure);
            return this.fetch_comments(this.params.limit, this.params.offset, domain);
        },


        /**
         *    CONTENT MANIPULATION
         */
        
        /**
         * var regex_login = new RegExp(/(^|\s)@((\w|@|\.)*)/g);
         * var regex_intlink = new RegExp(/(^|\s)#(\w*[a-zA-Z_]+\w*)\.(\w+[a-zA-Z_]+\w*),(\w+)/g);
         */
        do_replace_internal_links: function (string) {
            var self = this;
            var icon_list = ['al', 'pinky']
            /* shortcut to user: @login */
            var regex_login = new RegExp(/(^|\s)@((\w|@|\.)*)/g);
            var regex_res = regex_login.exec(string);
            while (regex_res != null) {
                var login = regex_res[2];
                string = string.replace(regex_res[0], regex_res[1] + '<a href="#" class="intlink oe_mail_oe_intlink" data-res-model="res.users" data-res-login = ' + login + '>@' + login + '</a>');
                regex_res = regex_login.exec(string);
            }
            /* special shortcut: :name, try to find an icon if in list */
            var regex_login = new RegExp(/(^|\s):((\w)*)/g);
            var regex_res = regex_login.exec(string);
            while (regex_res != null) {
                var icon_name = regex_res[2];
                if (_.include(icon_list, icon_name))
                    string = string.replace(regex_res[0], regex_res[1] + '<img src="/mail/static/src/img/_' + icon_name + '.png" width="22px" height="22px" alt="' + icon_name + '"/>');
                regex_res = regex_login.exec(string);
            }
            return string;
        },
        
        /**
         * var regex_login = new RegExp(/(^|\s)@((\w|@|\.)*)/g);
         * var regex_intlink = new RegExp(/(^|\s)#(\w*[a-zA-Z_]+\w*)\.(\w+[a-zA-Z_]+\w*),(\w+)/g);
         */
        do_check_for_internal_links: function(string) {
            /* shortcut to user: @login */
            var regex_login = new RegExp(/(^|\s)@((\w|@|\.)*)/g);
            var regex_res = regex_login.exec(string);
            while (regex_res != null) {
                var login = regex_res[2];
                if (! ('res.users' in this.map_hash)) { this.map_hash['res.users']['name'] = []; }
                this.map_hash['res.users']['login'].push(login);
                regex_res = regex_login.exec(string);
            }
            /* document link with name_get: [res.model,name] */
            /* internal link with id: [res.model,id], or [res.model,id|display_name] */
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
        
        do_clean_text: function (string) {
            var html = $('<div/>').text(string.replace(/\s+/g, ' ')).html().replace(new RegExp('&lt;(/)?(b|em|br|br /)\\s*&gt;', 'gi'), '<$1$2>');
            return html;
        },
        
        do_text_nl2br: function (str, is_xhtml) {   
            var break_tag = (is_xhtml || typeof is_xhtml === 'undefined') ? '<br />' : '<br>';    
            return (str + '').replace(/([^>\r\n]?)(\r\n|\n\r|\r|\n)/g, '$1'+ break_tag +'$2');
        },


        /**
         *    MISC TOOLS METHODS
         */
        
        /** checks if tue current user is the message author */
        _is_author: function (id) {
            return (this.session.uid == id);
        },

    });


    /* Add ThreadView widget to registry */
    session.web.form.widgets.add( 'ThreadView', 'openerp.mail.RecordThread');
//    session.web.page.readonly.add( 'ThreadView', 'openerp.mail.RecordThread');

    /* ThreadView widget: thread of comments */
    mail.RecordThread = session.web.form.AbstractField.extend({
        // QWeb template to use when rendering the object
        template: 'RecordThread',

       init: function() {
            this._super.apply(this, arguments);
            this.see_subscribers = true;
            this.thread = null;
            this.params = this.get_definition_options();
            this.params.thread_level = this.params.thread_level || 0;
            // datasets
            this.ds = new session.web.DataSet(this, this.view.model);
            this.ds_users = new session.web.DataSet(this, 'res.users');
        },

        start: function() {
            this._super.apply(this, arguments);
            var self = this;
            // bind buttons
            this.$element.find('button.oe_mail_button_followers').click(function () { self.do_toggle_followers(); }).hide();
            this.$element.find('button.oe_mail_button_follow').click(function () { self.do_follow(); })
                .mouseover(function () { $(this).html('Follow').removeClass('oe_mail_button_mouseout').addClass('oe_mail_button_mouseover'); })
                .mouseleave(function () { $(this).html('Not following').removeClass('oe_mail_button_mouseover').addClass('oe_mail_button_mouseout'); });
            this.$element.find('button.oe_mail_button_unfollow').click(function () { self.do_unfollow(); })
                .mouseover(function () { $(this).html('Unfollow').removeClass('oe_mail_button_mouseout').addClass('oe_mail_button_mouseover'); })
                .mouseleave(function () { $(this).html('Following').removeClass('oe_mail_button_mouseover').addClass('oe_mail_button_mouseout'); });
            this.reinit();
        },

        destroy: function () {
            this._super.apply(this, arguments);
        },
        
        reinit: function() {
            this.see_subscribers = true;
            this.$element.find('button.oe_mail_button_followers').html('Hide followers')
            this.$element.find('button.oe_mail_button_follow').hide();
            this.$element.find('button.oe_mail_button_unfollow').hide();
        },
        
        set_value: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.reinit();
            if (! this.view.datarecord.id) { this.$element.find('ul.oe_mail_thread').hide(); return; }
            // fetch followers
            var fetch_sub_done = this.fetch_subscribers();
            // create and render Thread widget
            this.$element.find('div.oe_mail_recthread_left').empty();
            if (this.thread) this.thread.destroy();
            this.thread = new mail.Thread(this, {'res_model': this.view.model, 'res_id': this.view.datarecord.id, 'uid': this.session.uid,
                                                    'thread_level': this.params.thread_level, 'show_post_comment': true, 'limit': 15});
            var thread_done = this.thread.appendTo(this.$element.find('div.oe_mail_recthread_left'));
            return fetch_sub_done && thread_done;
        },
        
        fetch_subscribers: function () {
            return this.ds.call('message_get_subscribers', [[this.view.datarecord.id]]).then(this.proxy('display_subscribers'));
        },
        
        display_subscribers: function (records) {
            var self = this;
            this.is_subscriber = false;
            var sub_node = this.$element.find('div.oe_mail_recthread_followers')
            sub_node.empty();
            $('<h4/>').html('Followers (' + records.length + ')').appendTo(sub_node);
            _(records).each(function (record) {
                if (record.id == self.session.uid) { self.is_subscriber = true; }
                var mini_url = tools_get_image(self.session.prefix, self.session.session_id, 'res.users', 'avatar', record.id);
                $('<img class="oe_mail_oe_left oe_mail_msg_image" src="' + mini_url + '" title="' + record.name + '" alt="' + record.name + '"/>').appendTo(sub_node);
            });
            if (self.is_subscriber) {
                self.$element.find('button.oe_mail_button_follow').hide();
                self.$element.find('button.oe_mail_button_unfollow').show(); }
            else {
                self.$element.find('button.oe_mail_button_follow').show();
                self.$element.find('button.oe_mail_button_unfollow').hide(); }
        },
        
        do_follow: function () {
            return this.ds.call('message_subscribe', [[this.view.datarecord.id]]).pipe(this.proxy('fetch_subscribers'));
        },
        
        do_unfollow: function () {
            var self = this;
            return this.ds.call('message_unsubscribe', [[this.view.datarecord.id]]).then(function (record) {
                if (record == false) self.do_notify("Impossible to unsubscribe", "You are automatically subscribed to this record. You cannot unsubscribe.");
                }).pipe(this.proxy('fetch_subscribers'));
        },
        
        do_toggle_followers: function () {
            this.see_subscribers = ! this.see_subscribers;
            if (this.see_subscribers) { this.$element.find('button.oe_mail_button_followers').html('Hide followers'); }
            else { this.$element.find('button.oe_mail_button_followers').html('Display followers'); }
            this.$element.find('div.oe_mail_recthread_followers').toggle();
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
         * @var {Array} comments_structure see tools_sort_comments
         */
        init: function (parent, params) {
            this._super(parent);
            this.params = {};
            this.params.limit = params.limit || 25;
            this.params.domain = params.domain || [];
            this.params.context = params.context || {};
            this.params.search_view_id = params.search_view_id || false;
            this.params.thread_level = params.thread_level || 1;
            this.comments_structure = {'root_ids': [], 'new_root_ids': [], 'msgs': {}, 'tree_struct': {}, 'model_to_root_ids': {}};
            this.display_show_more = true;
            this.thread_list = [];
            this.search = {'domain': [], 'context': {}, 'groupby': {}}
            this.search_results = {'domain': [], 'context': {}, 'groupby': {}}
            // datasets
            this.ds_msg = new session.web.DataSet(this, 'mail.message');
            this.ds_thread = new session.web.DataSet(this, 'mail.thread');
            this.ds_users = new session.web.DataSet(this, 'res.users');
        },

        start: function () {
            this._super.apply(this, arguments);
            var self = this;
            // add events
            this.add_event_handlers();
            // load mail.message search view
            var search_view_ready = this.load_search_view(this.params.search_view_id, {}, false);
            // fetch first threads
            var comments_ready = this.init_and_fetch_comments(this.params.limit, 0);
            return (search_view_ready && comments_ready);
        },
        
        stop: function () {
            this._super.apply(this, arguments);
        },
        
        /** Add events */
        add_event_handlers: function () {
            var self = this;
            // post a comment
            this.$element.find('button.oe_mail_wall_button_comment').click(function () { return self.do_comment(); });
            // display more threads
            this.$element.find('button.oe_mail_wall_button_more').click(function () { return self.do_more(); });
        },

        /**
         * Loads the mail.message search view
         * @param {Number} view_id id of the search view to load
         * @param {Object} defaults ??
         * @param {Boolean} hidden some kind of trick we do not care here
         */
        load_search_view: function (view_id, defaults, hidden) {
            var self = this;
            this.searchview = new session.web.SearchView(this, this.ds_msg, view_id || false, defaults || {}, hidden || false);
            var search_view_loaded = this.searchview.appendTo(this.$element.find('.oe_view_manager_view_search'));
            return $.when(search_view_loaded).then(function () {
                self.searchview.on_search.add(self.do_searchview_search);
            });
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
                self.search_results['context'] = results.context;
                self.search_results['domain'] = results.domain;
                self.search_results['groupby'] = results.group_by;
                return self.init_and_fetch_comments();
            });
        },

        /**
         * Initializes the wall and calls fetch_comments
         * @param {Number} limit: number of notifications to fetch
         * @param {Number} offset: offset in notifications search
         * @param {Array} domain
         * @param {Array} context
         */
        init_and_fetch_comments: function() {
            this.search['domain'] = _.union(this.params.domain, this.search_results.domain);
            this.search['context'] = _.extend(this.params.context, this.search_results.context);
            this.display_show_more = true;
            this.comments_structure = {'root_ids': [], 'new_root_ids': [], 'msgs': {}, 'tree_struct': {}, 'model_to_root_ids': {}};
            this.$element.find('div.oe_mail_wall_threads').empty();
            return this.fetch_comments(this.params.limit, 0);
        },

        /**
         * Fetches wall messages
         * @param {Number} limit: number of notifications to fetch
         * @param {Number} offset: offset in notifications search
         * @param {Array} domain
         * @param {Array} context
         */
        fetch_comments: function (limit, offset, additional_domain, additional_context) {
            var self = this;
            if (additional_domain) var fetch_domain = this.search['domain'].concat(additional_domain);
            else var fetch_domain = this.search['domain'];
            if (additional_context) var fetch_context = _.extend(this.search['context'], additional_context);
            else var fetch_context = this.search['context'];
            return this.ds_thread.call('get_pushed_messages', 
                [[this.session.uid], true, [], (limit || 0), (offset || 0), fetch_domain, fetch_context]).then(this.proxy('display_comments'));
        },

        /**
         * @param {Array} records records to show in threads
         */
        display_comments: function (records) {
            var self = this;
            this.do_update_show_more(records.length >= self.params.limit);
            this.sort_comments(records);
            _(this.comments_structure['new_root_ids']).each(function (root_id) {
                var records = self.comments_structure.tree_struct[root_id]['for_thread_msgs'];
                var model_name = self.comments_structure.msgs[root_id]['model'];
                var res_id = self.comments_structure.msgs[root_id]['res_id'];
                var render_res = session.web.qweb.render('WallThreadContainer', {});
                $('<div class="oe_mail_wall_thread">').html(render_res).appendTo(self.$element.find('div.oe_mail_wall_threads'));
                var thread = new mail.Thread(self, {
                    'res_model': model_name, 'res_id': res_id, 'uid': self.session.uid, 'records': records,
                    'parent_id': false, 'thread_level': self.params.thread_level, 'show_hide': true, 'is_wall': true}
                    );
                self.thread_list.push(thread);
                return thread.appendTo(self.$element.find('div.oe_mail_wall_thread:last'));
            });
            // update TODO
            this.comments_structure['root_ids'] = _.union(this.comments_structure['root_ids'], this.comments_structure['new_root_ids']);
            this.comments_structure['new_root_ids'] = [];
        },

        /**
         * Add records to comments_structure object: see function for details
         */
        sort_comments: function(records) {
            tools_sort_comments(this.comments_structure, records, false);
        },

        /**
         * Create a domain to fetch new comments according to
         * comments already present in comments_structure
         * - for each model:
         * -- should not be child of already displayed ids
         * @returns {Array} fetch_domain (OpenERP domain style)
         */
        get_fetch_domain: function () {
            var self = this;
            var model_to_root = {};
            var fetch_domain = [];
            _(this.comments_structure['model_to_root_ids']).each(function (sc_model, model_name) {
                fetch_domain.push('|', ['model', '!=', model_name], '!', ['id', 'child_of', sc_model]);
            });
            return fetch_domain;
        },
        
        /** Display update: show more button */
        do_update_show_more: function (new_value) {
            if (new_value != undefined) this.display_show_more = new_value;
            if (this.display_show_more) this.$element.find('div.oe_mail_wall_more:last').show();
            else this.$element.find('div.oe_mail_wall_more:last').hide();
        },
        
        /** Action: Shows more discussions */
        do_more: function () {
            var domain = this.get_fetch_domain();
            return this.fetch_comments(this.params.limit, 0, domain);
        },
        
        /** Action: Posts a comment */
        do_comment: function () {
            var comment_node = this.$element.find('textarea.oe_mail_wall_action_textarea');
            var body_text = comment_node.val();
            comment_node.val('');
            var call_done = this.ds_users.call('message_append_note', [[this.session.uid], 'Tweet', body_text, false, 'comment', 'html', 'tweet']).then(this.proxy('init_and_fetch_comments'));
        },
    });
    

    /**
     *    TOOLS
     */

    /**
    * Add records to comments_structure array
    * @param {Array} records records from mail.message sorted by date desc
    * @returns {Object} cs comments_structure: dict
    *                      cs.model_to_root_ids = {model: [root_ids], }
    *                      cs.new_root_ids = [new_root_ids]
    *                      cs.root_ids = [root_ids]
    *                      cs.msgs = {record.id: record,}
    *                      cs.tree_struct = {record.id: {
    *                          'level': record_level in hierarchy, 0 is root,
    *                          'msg_nbr': number of childs,
    *                          'direct_childs': [msg_ids],
    *                          'all_childs': [msg_ids],
    *                          'for_thread_msgs': [records],
    *                          'ancestors': [msg_ids], } }
    */
    function tools_sort_comments(cs, records, parent_id) {
        var cur_iter = 0; var max_iter = 10; var modif = true;
        while ( modif && (cur_iter++) < max_iter) {
            modif = false;
            _(records).each(function (record) {
                // root and not yet recorded
                if ( (record.parent_id == false || record.parent_id[0] == parent_id) && ! cs['msgs'][record.id]) {
                    // add to model -> root_list ids
                    if (! cs['model_to_root_ids'][record.model]) cs['model_to_root_ids'][record.model] = [record.id];
                    else cs['model_to_root_ids'][record.model].push(record.id);
                    // add root data
                    cs['new_root_ids'].push(record.id);
                    // add record
                    cs['tree_struct'][record.id] = {'level': 0, 'direct_childs': [], 'all_childs': [], 'for_thread_msgs': [record], 'msg_nbr': -1, 'ancestors': []};
                    cs['msgs'][record.id] = record;
                    modif = true;
                }
                // not yet recorded, but parent is recorded
                else if (! cs['msgs'][record.id] && cs['msgs'][record.parent_id[0]]) {
                    var parent_level = cs['tree_struct'][record.parent_id[0]]['level'];
                    // update parent structure
                    cs['tree_struct'][record.parent_id[0]]['direct_childs'].push(record.id);
                    cs['tree_struct'][record.parent_id[0]]['for_thread_msgs'].push(record);
                    // update ancestors structure
                    for (ancestor_id in cs['tree_struct'][record.parent_id[0]]['ancestors']) {
                        cs['tree_struct'][ancestor_id]['all_childs'].push(record.id);
                    }
                    // add record
                    cs['tree_struct'][record.id] = {'level': parent_level+1, 'direct_childs': [], 'all_childs': [], 'for_thread_msgs': [], 'msg_nbr': -1, 'ancestors': []};
                    cs['msgs'][record.id] = record;
                    modif = true;
                }
            });
        }
        return cs;
    }

    /** get an image in /web/binary/image?... */
    function tools_get_image(session_prefix, session_id, model, field, id) {
        return session_prefix + '/web/binary/image?session_id=' + session_id + '&model=' + model + '&field=' + field + '&id=' + (id || '');
    }
        
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
