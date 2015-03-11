/*---------------------------------------------------------
 * OpenERP web_timeline
 *---------------------------------------------------------*/

openerp.web_timeline = function (session) {
    "use strict";

    var _t = session.web._t,
        _lt = session.web._lt;
    var QWeb = openerp.web.qweb;
    var mail = session.mail;


    openerp.web_timeline.followers(session, mail);          // import timeline_followers.js

    /**
     * ChatterUtils
     * This class holds a few tools method for Chatter.
     * Some regular expressions not used anymore, kept because I want to
     * - (^|\s)@((\w|@|\.)*): @login@log.log
     * - (^|\s)\[(\w+).(\w+),(\d)\|*((\w|[@ .,])*)\]: [ir.attachment,3|My Label],
     *   for internal links
     */
    openerp.web_timeline.ChatterUtils = {

        /** 
         * Parse text to find email: Tagada <address@mail.fr> -> [Tagada, address@mail.fr] or False 
         */
        parse_email: function (text) {
            var result = text.match(/(.*)<(.*@.*)>/);
            if (result) {
                return [_.str.trim(result[1]), _.str.trim(result[2])];
            }
            result = text.match(/(.*@.*)/);
            if (result) {
                return [_.str.trim(result[1]), _.str.trim(result[1])];
            }
            return [text, false];
        },

        /**
         * Get an image in /web/binary/image?... 
         */
        get_image: function (session, model, field, id, resize) {
            var r = resize ? encodeURIComponent(resize) : '';
            id = id || '';
            return session.url('/web/binary/image', {model: model, field: field, id: id, resize: r});
        },
 
        /** 
         * Get the url of an attachment {'id': id} 
         */
        get_attachment_url: function (session, message_id, attachment_id) {
            return session.url('/mail/download_attachment', {
                'model': 'mail.message',
                'id': message_id,
                'method': 'download_attachment',
                'attachment_id': attachment_id,
            });
        },

        /**
         * Replaces textarea text into html text (add <p>, <a>)
         */
        get_text2html: function (text) {
            return text
                .replace(/((?:https?|ftp):\/\/[\S]+)/g,'<a href="$1">$1</a> ')
                .replace(/[\n\r]/g,'<br/>');              
        },

        /** 
         * Returns the complete domain with "&" 
         */
        expand_domain: function (domain) {
            var new_domain = [];
            var nb_and = -1;
            
            for (var k = domain.length-1; k >= 0; k--) {
                if (typeof domain[k] != 'array' && typeof domain[k] != 'object') {
                    nb_and -= 2;
                    continue;
                }
                nb_and += 1;
            }

            for (var k = 0; k < nb_and; k++)
                domain.unshift('&');

            return domain;
        },

        /**
         * Inserts zero width space between each letter of a string so that
         * the word will correctly wrap in html boxes smaller than the text
         */
        breakword: function (str) {
            var out = '';
            if (!str) return str;
            
            for(var i = 0, len = str.length; i < len; i++)
                out += _.str.escapeHTML(str[i]) + '&#8203;';
            
            return out;
        },

        bindTooltipTo: function ($el, value, position) {
            $el.tooltip({
                'title': value,
                'placement': position,
                'html': true,
                'trigger': 'manual',
                'animation': false,
            }).on("mouseleave", function () {
                setTimeout(function () {
                    if (!$(".tooltip:hover").length) {
                        $el.tooltip("hide");
                    }
                }, 100);
            });
        },
    };

    openerp.web_timeline.TimelineRecordThread = session.web.form.AbstractField.extend ({
        className: 'oe_timeline_record_thread',

        init: function (parent, node) {
            this._super.apply(this, arguments);

            this.parent = parent;
            this.dataset = new session.web.DataSet(this, 'mail.message', this.view.dataset.context);
            this.domain = (this.node.params && this.node.params.domain) || (this.field && this.field.domain) || [];

            this.opts = _.extend({
                'show_reply_button': false,
                'show_read_unread_button': true,
                'read_action': 'unread',
                'show_record_name': false,
                'show_compact_message': true,
                'compose_as_todo' : false,
                'view_inbox': false,
                'emails_from_on_composer': true,
                'fetch_limit': 15,
                'readonly': this.node.attrs.readonly || false,
                'compose_placeholder' : this.node.attrs.placeholder || false,
                'display_log_button' : this.options.display_log_button || true,
                'show_compose_message': this.view.is_action_enabled('edit') || false,
                'show_link': this.parent.is_action_enabled('edit') || true,
            }, this.node.params);
        },

        start: function () {
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
           
            this.timeline_view = new session.web_timeline.TimelineView(this, this.dataset, false, this.opts);
            this._super.apply(this, arguments);

            return this.timeline_view.appendTo(this.$el);
        },

        _check_visibility: function () {
            this.$el.toggle(this.view.get("actual_mode") !== "create");
        },
 
        render_value: function () {
            if (! this.view.datarecord.id || 
                session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                    return;
            }

            this.timeline_view.set_message_ids(this.get_value());
            
            var domain = (this.domain || []).concat([['model', '=', this.view.model], 
                                                     ['res_id', '=', this.view.datarecord.id]]);

            var context = {
                'mail_read_set_read': true,
                'default_res_id': this.view.datarecord.id || false,
                'default_model': this.view.model || false,
            };
            
            return this.timeline_view.do_search(domain, context);
        }
    });

    session.web_timeline.TimelineView = session.web.View.extend ({
        display_name: _lt('Timeline'),
        view_type: 'timeline',
        template: 'TimelineWall',

        init: function (parent, dataset, view_id, options) {
            this._super(parent, dataset, view_id, options);

            this.model = dataset.model;
            this.domain = dataset.domain || [];
            this.context = dataset.context || {};

            var opt = _.clone(this.context.options);
            this.options = options || {};
            this.options = _.extend(this.options, (opt || {}));
            this.options = _.extend({
                'show_link': true,
                'show_reply_button': true,
                'show_read_unread_button': true,
                'fetch_limit': 15,
                'fetch_child_limit': 5,
                }, this.options);

            this.fields_view = {};
            this.fields_keys = [];

            this.qweb = new QWeb2.Engine();
            this.has_been_loaded = $.Deferred();
        },

        view_loading: function (fields_view_get) {
            return this.load_timeline(fields_view_get);
        },

        load_timeline: function (fields_view_get) {
            var self = this;

            this.fields_view = fields_view_get;
            this.fields_keys = _.keys(this.fields_view.fields);
    
            this.add_qweb_template(); 

            if (this.options.$buttons) {
                this.$buttons = $(QWeb.render("TimelineView.buttons", {'widget': this}));
                this.$buttons.appendTo(this.options.$buttons);
                this.$buttons
                    .on('click', 'button.oe_timeline_button_new', this.on_compose_message)
                    .on('click', '.oe_timeline_share', function(event) {
                        self.write_to_followers(event, self);
                    });
            } 

            this.has_been_loaded.resolve();
        },

        do_show: function () {
            this.do_push_state({});
            return this._super();
        },

        do_search: function (dom, cxt, group_by) {
            var self = this;

            var domain = this.domain.concat(dom || []);
            var context = _.clone(this.context);
                context = _.extend(context, (cxt || {}));
            var ds = {
                "domain" : domain, 
                "context" : context,
            };
            var opts = _.clone(this.options);

            return this.has_been_loaded.then(function() {
                if (self.thread) {
                    $('<span class="oe_timeline-placeholder"/>').insertAfter(self.thread.$el);
                    self.thread.destroy();
                }
                self.thread = new openerp.web_timeline.MailThread(self, ds, opts);
                self.thread.message_fetch(null, null, self.options.message_ids, self.options.view_inbox ? 'inbox' : 'default');

                return self.thread.replace(self.$('.oe_timeline-placeholder'));
            });
        },

        do_reload_menu_emails: function () {
            var menu = session.webclient.menu;
            if (!menu || !menu.current_menu) {
                return $.when();
            }
            return menu.rpc("/web/menu/load_needaction", {'menu_ids': [menu.current_menu]})
                .done(function(r) {
                    menu.on_needaction_loaded(r);
                }).then(function () {
                    menu.trigger("need_action_reloaded");
                });
        },

        add_qweb_template: function () {
            for (var i = 0; i < this.fields_view.arch.children.length; i++) {
                var child = this.fields_view.arch.children[i];
                if (child.tag === 'templates') {
                    this.transform_qweb_template(child);
                    this.qweb.add_template(session.web.json_node_to_xml(child));
                    break;
                }
            }
        },

        transform_qweb_template: function (node) {
            switch (node.tag) {
                case 'field':
                    node.tag = QWeb.prefix;
                    switch (node.attrs['name']) {
                        case 'res_id':
                            node.attrs[QWeb.prefix + '-raw'] = 'widget.record_name';
                            break;
                        case 'model':
                            node.attrs[QWeb.prefix + '-raw'] = 'widget.model_desc';
                            break;
                        case 'author_id':
                            node.attrs[QWeb.prefix + '-raw'] = 'thread.format_author(widget.author_id)[2]';
                            break;
                        case 'subtype_id':
                            node.attrs[QWeb.prefix + '-raw'] = 'widget.subtype';
                            break;
                        case 'date':
                            node.attrs[QWeb.prefix + '-raw'] = 'thread.format_date(widget.date)';
                            break;
                        default:
                            node.attrs[QWeb.prefix + '-raw'] = 'widget.' + node.attrs.name;
                            break;
                    }
                break;

                case 'a':
                    break;
            }
            
            if (node.children) {
                for (var i = 0; i < node.children.length; i++) {
                    this.transform_qweb_template(node.children[i]);
                }
            }
        },

        on_compose_message: function (event) {
            event.preventDefault();
            var action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {},
            };
            session.client.action_manager.do_action(action);
        },

        write_to_followers: function (event, view) {
            view.thread.instantiate_write_to_followers(event);
        },

        set_message_ids: function (val) {
            this.options.message_ids = val;
        },
    });

    openerp.web_timeline.Common = session.web.Widget.extend ({
        format_attachments: function (attachments) {
            for (var l in attachments) {
                var attach = attachments[l];
                if (!attach.formating) {
                    attach.url = openerp.web_timeline.ChatterUtils
                                    .get_attachment_url(this.session, this.id, attach.id);
                    attach.name = openerp.web_timeline.ChatterUtils
                                    .breakword(attach.name || attach.filename);
                    attach.formating = true;
                }
            }
            return attachments;
        },

        display_attachments: function (message) {
            return session.web.qweb.render('ThreadMessageAttachments', {'widget': message, 'thread': this});
        },

        /**
         * Return the link to resized image
         */
        attachments_resize_image: function (id, resize) {
            return openerp.web_timeline.ChatterUtils.get_image(
                        this.session, 'ir.attachment', 'datas', id, resize);
        },
    });

    openerp.web_timeline.MailThread = openerp.web_timeline.Common.extend ({
        template: 'MailThread',

        events: {
            'click .oe_tl_msg .oe_read':'on_message_read',
            'click .oe_tl_msg .oe_unread':'on_message_unread',
            'click .oe_tl_msg .oe_star':'on_star',
            'click .oe_tl_parent_message .oe_reply':'on_message_reply',
            'click .oe_tl_parent_message .oe_read':'on_thread_read',
            'click .oe_tl_msg_vote':'on_vote',
            'mouseenter .oe_timeline_vote_count':'on_hover',
            'click .oe_timeline_action_author':'on_record_author_clicked',
            'click .oe_tl_msg_expandable':'on_message_expandable',
            'click .oe_tl_parent_expandable':'on_thread_expandable',
            'click .oe_tl_parent_subject':'on_parent_message',
            'click .oe_tl_go_to_doc':'on_record_clicked',
            'mouseenter .oe_follwrs':'on_display_followers',
        },

        init: function (parent, dataset, options) {
            this._super(parent, dataset, options);
            var self = this;

            this.domain = dataset.domain || [];
            this.context = _.clone(dataset.context) || {};
            this.options = _.clone(options);
            
            this.root = parent instanceof openerp.web_timeline.TimelineView ? parent : false;
            this.view = parent instanceof openerp.web_timeline.TimelineView ? parent : parent.view;

            this.is_ready = $.Deferred();
            this.messages = dataset.messages ? dataset.messages[1] || [dataset.messages] : [];
            this.parent_message = this.messages.length ? this.messages[this.messages.length - 1] : false;
            this.type = dataset.messages ? dataset.messages.type || 'parent' : false;
            
            this.id = this.parent_message.id || false;
            this.parent_id = this.parent_message.id || false;
            this.author_id = this.parent_message.author_id || false;
            this.user_pid = this.parent_message.user_pid || false;
            this.is_private = this.parent_message.is_private || false;
            this.partner_ids = this.parent_message.partner_ids || [];
            if (this.parent_message.author_id 
                && !_.contains(_.flatten(this.parent_message.partner_ids),this.parent_message.author_id[0]) 
                && this.parent_message.author_id[0]) {
                this.partner_ids.push(this.parent_message.author_id);
            }

            if (!this.root) {
                this.context = _.extend(this.context, {
                    'default_model': this.parent_message.model,
                    'default_res_id': this.parent_message.res_id,
                });
            }

            this.options.root_thread = this.options.root_thread != undefined ? this.options.root_thread : this;
            this.options.show_compose_message = this.root ? false : this.options.root_thread.view.options.show_compose_message;
            this.options.is_folded = this.options.view_inbox ? true : false;
            this.options.rerender = true;
            this.options.toggle_read = true;
            
            _.each(this.messages, function (msg) {
                msg = self.format_message(msg);
            });

            this.record_name = this.parent_message.record_name || false;
            this.subject = this.parent_message.subject || false;

            if (this.options.view_inbox && this.messages.length) {
                this.format_thread().then(function () {
                        self.is_ready.resolve();
                    });
            }
            else {
                self.is_ready.resolve();
            }

            this.compose_message = false;

            this.ds_thread = new session.web.DataSetSearch(this, this.context.default_model || 'mail.thread');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
        },

        start: function () {
            var self = this;
            return this.is_ready.then(function () {
                var $el = $(session.web.qweb.render('MailThread', {'widget': self}));
                self.replaceElement($el);

                if (self.options.show_compose_message) {
                    self.instantiate_compose_message();
                    self.compose_message.do_show_compact();
                }
            });
        },

        /**
         * instantiate the compose message object and insert this on the DOM.
         * The compose message is display in compact form.
         */
        instantiate_compose_message: function (option) {
            if (!this.compose_message) {
                this.context = this.options.compose_as_todo ? 
                    _.extend({'default_starred': true}, this.context) : this.context;
                this.compose_message = new openerp.web_timeline.ThreadComposeMessage(this, this, this.options);

                if (this.options.view_inbox && option == 'reply') {
                    this.compose_message.insertAfter(this.$('.oe_tl_thread_content'));
                }
                else if (this.options.view_inbox && option == 'write_to_followers') {
                    this.compose_message.prependTo(this.$el);
                }
                else {
                    this.compose_message.insertBefore(this.$el);
                }
            }
        },

        on_compose_message: function (event, option) {
            if (this.compose_message) {
                this.compose_message.destroy();
            }
            this.compose_message = false;

            this.instantiate_compose_message(option);
            return this.compose_message.on_toggle_quick_composer(event);
        },

        instantiate_write_to_followers: function (event) {
            var self = this;
            return this.on_compose_message(event, 'write_to_followers')
                .then(function () {
                    self.$('.oe_tl_msg_composer').addClass('oe_tl_write_to_followers');
                });
        },

        /**
         * make a request to read the message (calling RPC to "message_read").
         * @param {Array} replace_domain: added to this.domain
         * @param {Object} replace_context: added to this.context
         * @param {Array} ids read (if the are some ids, the method don't use the domain)
         */
        message_fetch: function (replace_domain, replace_context, ids, mode, callback) {
            var self = this;
            return this.ds_message.call('message_read', [
                    // ids force to read
                    ids === false ? undefined : ids && ids.slice(0, this.options.fetch_limit),
                    // domain + additional
                    (replace_domain ? replace_domain : this.domain), 
                    // context + additional
                    (replace_context ? replace_context : this.context), 
                    // mode
                    mode,
                    // parent_id
                    this.context.default_parent_id || undefined,
                    // limits
                    this.options.fetch_limit,
                    this.options.fetch_child_limit
                 ]).done(callback ? _.bind(callback, this, arguments) : this.proxy('treat_threads')
                  ).done(function (records) {
                        if (records.nb_read) {
                            self.options.root_thread.view.do_reload_menu_emails();
                        }
                  });
        },

        treat_threads: function (records) {
            var self = this;
            
            _.each(records.threads, function (record) {
                self.create_thread(record);
            });

            if (!records.threads.length) {
                this.create_thread();
            }
        },

        create_thread: function (record) {
            var thread = new openerp.web_timeline.MailThread(this, _.extend(_.clone(this), {
                    'messages': record, 
                    }), this.options);

            thread.appendTo(this.$el);
            return thread;
        },

        on_message_read: function (event) {
            var msg_id = $(event.target).data('msg_id');
            var msg = _.findWhere(this.messages, {id: msg_id});
            event.stopPropagation();
            this.on_message_read_unread([msg], true);
        },

        on_message_unread: function (event) {
            var msg_id = $(event.target).data('msg_id');
            var msg = _.findWhere(this.messages, {id: msg_id});
            event.stopPropagation();
            this.on_message_read_unread([msg], false);
        },

        on_thread_read: function (event) {
            event.stopPropagation();
            this.on_message_read_unread(
                _.filter(this.messages, function (val) {return val.type != 'expandable'}), true);
        },

        /** 
         * Set the selected thread and all childs as read or unread, based on
         * read parameter.
         * @param {boolean} read_value
         * @param {messages} array of messages
         */
        on_message_read_unread: function (messages, read_value) {
            var self = this; 

            // inside the inbox, when the user mark a message as read/done, don't apply this value
            // for the stared/favorite message
            if (this.options.view_inbox && read_value) {
                messages = _.filter(messages, function (val) {return !val.is_favorite && val.id;});
                if (!messages.length) {
                    this.check_for_rerender();
                    return false;
                }
            }
            var message_ids = _.map(messages, function (val) {return val.id;});

            this.ds_message.call('set_message_read', [message_ids, read_value, true, this.context])
                .then(function (nb_read) {
                    // apply modification
                    _.each(messages, function (msg) {
                        msg.to_read = !read_value;
                        if (self.options.toggle_read) {
                            msg.options.show_read = msg.to_read;
                            msg.options.show_unread = !msg.to_read;
                        }
                    });
                
                    self.check_for_rerender();
                });

            return false;
        },

        /**
         * add or remove a favorite (or starred) for a message and change class on the DOM
         */
        on_star: function (event) {
            var self = this;
            var msg_id = $(event.target).data('msg_id');
            var msg = _.findWhere(this.messages, {id: msg_id});
            var button = self.$('.oe_star:first');
            event.stopPropagation();
            
            this.ds_message.call('set_message_starred', [[msg_id], !msg.is_favorite, true])
                .then(function (star) {
                    msg.is_favorite = star;
                    if (msg.is_favorite) {
                        button.addClass('oe_starred');
                    } 
                    else {
                        button.removeClass('oe_starred');
                    }

                    if (self.options.view_inbox && msg.is_favorite) {
                        self.on_message_read_unread([msg], true);
                    } 
                    else {
                        self.check_for_rerender();
                    }
                });
            return false;
        },

        on_message_reply:function (event) {
            event.stopPropagation();
            this.on_compose_message(event, 'reply');
            return false;
        },

        /**
         * Add or remove a vote for a message and display the result
         */
        on_vote: function (event) {
            var self = this;
            var msg_id = $(event.target).data('msg_id');
            var msg = _.findWhere(this.messages, {id: msg_id});
            event.stopPropagation();

            this.ds_message.call('vote_toggle', [[msg_id]])
                .then(_.bind(function (vote) {
                      msg.has_voted = vote;
                      msg.vote_nb += msg.has_voted ? 1 : -1;
                      self.check_for_rerender();
                    }, self));

            return false;
        },

        on_hover : function (event) {
            var voter = "";
            var limit = 10;
            var msg_id = $(event.target).data('msg_id');
            event.stopPropagation();

            var $target = $(event.target).hasClass("fa-thumbs-o-up") ? $(event.target).parent() : $(event.target);
            // Note: We can set data-content attr on target element once we fetch data so that 
            // next time when one moves mouse on element it saves call
            // But if there is new like comes then we'll not have new likes in popover in that case
            if ($target.data('liker-list'))
            {
                voter = $target.data('liker-list');
                openerp.web_timeline.ChatterUtils.bindTooltipTo($target, voter, 'top');
                $target.tooltip('hide').tooltip('show');
                $(".tooltip").on("mouseleave", function () {
                    $(this).remove();
                });
            }
            else {
                this.ds_message.call('get_likers_list', [msg_id, limit])
                .done(function (data) {
                    _.each(data, function(people, index) {
                        voter = voter + people.substring(0,1).toUpperCase() + people.substring(1);
                        if (index != data.length-1) {
                            voter = voter + "<br/>";
                        }
                    });
                    $target.data('liker-list', voter);
                    openerp.web_timeline.ChatterUtils.bindTooltipTo($target, voter, 'top');
                    $target.tooltip('hide').tooltip('show');
                    $(".tooltip").on("mouseleave", function () {
                        $(this).remove();
                    });
                });
            }

            return true;
        },

        on_record_author_clicked: function (event) {
            event.preventDefault();
            var partner_id = $(event.target).data('partner');
            var record_name = $(event.target).data('record');
            var state = {
                'model': 'res.partner',
                'id': partner_id,
                'title': record_name
            };

            session.webclient.action_manager.do_push_state(state);
            var action = {
                type:'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: 'res.partner',
                views: [[false, 'form']],
                res_id: partner_id,
            }
            this.do_action(action);
        },

        on_record_clicked: function (event) {
            event.preventDefault();
            event.stopPropagation();

            var self = this;
            var state = {
                'model': this.context.default_model,
                'id': this.context.default_res_id,
                'title': this.record_name,
            };

            session.webclient.action_manager.do_push_state(state);

            this.context.params = {
                model: this.context.default_model,
                res_id: this.context.default_res_id,
            };

            this.ds_thread.call("message_redirect_action", {context: this.context})
                .then(function(action){
                    self.do_action(action); 
                });
        },

        on_message_expandable: function (event) {
            event.stopPropagation();

            var self = this;
            if (this.options.view_inbox) {
                var parent_message = this.messages.pop();
            }
            var msg = this.messages.pop();

            this.message_fetch(msg.domain, this.context, false, 'default', function (arg, data) {
                var messages = data.threads[0][1];
                _.each(messages, function (message) {
                    self.add_message(message, true);
                });
                if (this.options.view_inbox) {
                    this.messages.push(parent_message);
                }
                self.check_for_rerender();
            });
        },

        on_thread_expandable: function (event) {
            event.stopPropagation();
            var self = this;
            var msg = this.messages.pop();

            this.options.root_thread.message_fetch(msg.domain, this.context, false, 'inbox')
                .then(function () {
                    self.$el.remove();
                    self.destroy();
                });
        },

        on_parent_message: function (event) {
            event.stopPropagation();
            this.options.is_folded = !this.options.is_folded;
            this.check_for_rerender();
        },

        on_display_followers: function (event) {
            var self = this;
            var $target = $(event.target);
            event.stopPropagation();

            if (this.followers_data) {
                openerp.web_timeline.ChatterUtils.bindTooltipTo($target, this.followers_data, 'right');
                $target.tooltip('hide').tooltip('show');
                $(".tooltip").on("mouseleave", function () {
                    $(this).remove();
                });
            }
            else {
                var ds_model = new session.web.DataSetSearch(this, this.model, this.context);
                ds_model.call('read_followers_data', [this.follower_ids.slice(0, this.options.followers_limit)])
                .then(function (records) {
                    self.followers_data = [];
                    _.each(records, function(f) {
                        self.followers_data.push(f[1] + '</br>');
                    });
                    if (self.nb_followers - self.followers_limit > 0) {
                        self.followers_data.push('and ' + self.nb_followers - self.followers_limit + 'more ... </br>');  
                    } 
                    openerp.web_timeline.ChatterUtils.bindTooltipTo($target, self.followers_data, 'right');
                    $target.tooltip('hide').tooltip('show');
                    $(".tooltip").on("mouseleave", function () {
                        $(this).remove();
                    });
                });
            }
        }, 

        check_for_rerender: function () {
            var self = this; 

            _.each(this.messages, function (msg) {
                var qweb_context = {
                    session: session,
                    widget: msg,
                    thread: self,
                    options: msg.options,
                };
                msg.content = self.view.qweb.render("message_content", qweb_context);
            });

            if (this.options.view_inbox && this.messages.length) {
                this.is_ready = $.Deferred();
                this.format_thread().then(function () {
                    self.is_ready.resolve();
                });
            }

            this.is_ready.then(function () {
                var $el = $(session.web.qweb.render('MailThread', {'widget': self}));
                self.replaceElement($el);
                self.options.root_thread.view.do_reload_menu_emails();
            });
        },

        add_message: function (message, to_end) {
            message = this.format_message(message);
            if (to_end) {
                this.messages.push(message);
            }
            else {
                this.messages.unshift(message);
            }
        },

        insert_message: function (message) {
            this.$('.oe_view_nocontent').remove();
            if (this.options.view_inbox && !this.root) {
                $(message.content).appendTo(this.$('.oe_tl_thread_content'));
            }
            else if (this.options.view_inbox && this.root) {
                $(message.content).appendTo(this.$('.oe_tl_thread_parent:first'));
            }
            else {
                $(message.content).prependTo(this.$el);
            } 
        },

        format_thread: function () {
            var self = this;

            this.model = this.context.default_model;
            this.res_id = this.context.default_res_id;

            this.followers_loaded = $.Deferred();

            if ((! this.nb_followers || !this.follower_ids)
                && (this.model && this.res_id)) {
                this.nb_followers = 0;
                this.follower_ids = [];

                this.ds_res = new session.web.DataSetSearch(this, this.model, this.context, [['id', '=', this.res_id]]);
                this.ds_res.read_slice().then(function (data) {
                    self.follower_ids = data[0].message_follower_ids;
                    self.nb_followers = data[0].message_follower_ids.length;
                    self.followers_loaded.resolve();
                });
            }
            else {    
                this.followers_loaded.resolve();
            }

            return this.followers_loaded.then(function () {
                var qweb_context = {
                    widget: self.messages[0],
                    thread: self,
                    options: self.options,
                };
                self.content = self.view.qweb.render("thread_content", qweb_context);
            });
        },

        format_message: function (msg) {
            msg.tracking_values = msg.tracking_value_ids ? (msg.tracking_value_ids.length > 0) : false;
            msg.partners = msg.partner_ids ? (msg.partner_ids.length > 0) : false;
            msg.attachments = msg.attachment_ids ? (msg.attachment_ids.length > 0) : false;
            msg.parent_id = msg.parent_id || false;

            if (msg.model == 'res.partner') {
                msg.record_name = 'Partner Profile of ' + msg.record_name;
            }
            else if (msg.model == 'hr.employee') {
                msg.record_name = 'News from ' + msg.record_name;
            }

            if (msg.attachments) msg.attachments_content = this.display_attachments(msg);

            msg.parent_thread = this;

            msg.options = _.clone(this.options);
            msg.options.show_read = false;
            msg.options.show_unread = false;

            if (this.options.show_read_unread_button) {
                if (this.options.read_action == 'read') {
                    msg.options.show_read = true;
                }
                else if (this.options.read_action == 'unread') {
                    msg.options.show_unread = true;
                }
                else {
                    msg.options.show_read = msg.to_read;
                    msg.options.show_unread = !msg.to_read;
                }
            }

            var qweb_context = {
                widget: msg,
                thread: this,
                options: msg.options,
            };
            msg.content = this.view.qweb.render("message_content", qweb_context);

            return msg;
        },

        format_date: function (date) {
            var d = date ? session.web.str_to_datetime(date) : false;
            if (d) {
                var display_date = moment(new Date(d).toISOString()).format('ddd MMM DD YYYY LT');
                date = display_date;
                if (new Date().getTime()-d.getTime() < 7*24*60*60*1000) {
                    var timerelative = $.timeago(d);
                    date = timerelative;
                }
            }

            return date;
        },

        format_avatar: function (avatar, author, type) {
            var avt = false;
            if (avatar) {
                avt = "data:image/png;base64," + avatar;
            }
            else if (type == 'email' && (!author || !author[0])) {
                avt = ('/mail/static/src/img/email_icon.png');
            } 
            else if (author) {
                avt  = openerp.web_timeline.ChatterUtils.get_image(
                    this.session, 'res.partner', 'image_small', author[0]);
            } 
            else {
                avt = openerp.web_timeline.ChatterUtils.get_image(
                    this.session, 'res.users', 'image_small', this.session.uid);
            }
            return avt;
        },

        format_author: function (author) {
            if (author && author[1]) {
                var parsed_email = openerp.web_timeline.ChatterUtils.parse_email(author[1]);
                author.push(parsed_email[0], parsed_email[1]);
            }
            return author;
        }, 

        format_partners_nb: function (partners) {
            return partners.length - 3;
        },

        format_partners_str: function (partners) {
            if (partners && partners.length > 3) {
                var extra_partners_nbr = this.format_partners_nb(partners);
                var extra_partners_str = ''
                var extra_partners = partners.slice(3);

                for (var key in extra_partners) {
                    extra_partners_str += extra_partners[key][1];
                }

                return extra_partners_str;
            }
        },
    });

    openerp.web_timeline.ThreadComposeMessage = openerp.web_timeline.Common.extend ({
        template: 'ComposeMessage',

        events: {
            'click .oe_tl_compose_post':'on_toggle_quick_composer',
            'click .oe_tl_compose_log':'on_toggle_quick_composer',
            'click .oe_post':'on_message_post',
            'click .oe_full':'on_full',
            'click .oe_tl_msg_attachment_list .oe_delete': 'on_attachment_delete',
            'change input.oe_form_binary_file': 'on_attachment_change',
            'blur textarea':'on_toggle_quick_composer',
            'mousedown .oe_tl_msg_center':function (event) {
                this.stay_open = true;
            },
            'mouseup .oe_tl_msg_content':function (event) {
                this.$('textarea').focus();
            },
            'change .oe_recipients input':'on_checked_recipient',
        },

        init: function (parent, dataset, options) {
            this._super(parent, dataset, options);

            this.domain = dataset.domain || [];
            this.context = _.clone(dataset.context) || {};
            this.options = _.clone(options);

            this.show_compact_message = false;
            this.show_delete_attachment = true;
            this.is_log = false;

            this.id = dataset.id || false;
            this.user_pid = dataset.user_pid || false;
            this.parent_id = dataset.parent_id || false;
            this.is_private = dataset.is_private || false;
            this.partner_ids = dataset.partner_ids || [];
            this.recipients = [];
            this.recipient_ids = [];
            this.attachment_ids = [];

            this.parent_thread = parent;
            this.view = parent.view;

            session.web.bus.on('clear_uncommitted_changes', this, function (e) {
                if (this.show_composer && !e.isDefaultPrevented()) {
                    if (!confirm(_t("You are currently composing a message, your message will be discarded.\n\nAre you sure you want to leave this page ?"))) {
                        e.preventDefault();
                    }
                    else {
                        this.on_cancel();
                    }
                }
            });
        },

        start: function () {
            this.ds_attachment = new session.web.DataSetSearch(this, 'ir.attachment');
            this.fileupload_id = _.uniqueId('oe_fileupload_temp');
            $(window).on(this.fileupload_id, this.on_attachment_loaded);
            this.$(".oe_tl_msg_attachment_list").html(this.display_attachments(this));
            this.bind_events();

            return this._super.apply(this, arguments);
        },

        reinit: function () {
            var $render = $(session.web.qweb.render('ComposeMessage', {'widget': this}));
            this.replaceElement($render);

            this.$(".oe_tl_msg_attachment_list").html(this.display_attachments(this));
            this.bind_events();
        },

        bind_events: function () {
            var self = this;   
            var ev_stay = {};
            ev_stay.mouseup = ev_stay.keydown = ev_stay.focus = function () { self.stay_open = false; };
            this.$('textarea').on(ev_stay);
            this.$('textarea').autosize();
        },

        on_cancel: function (event) {
            if (event) event.stopPropagation();
            this.attachment_ids = [];
            this.stay_open = false;
            this.show_composer = false;
            this.reinit();
        },

        compute_emails_from: function () {
            var self = this;
            var messages = this.parent_thread.messages;

            _.each(messages, function (thread) {
                if (thread.author_id && !thread.author_id[0] &&
                    !_.find(self.recipients, function (recipient) {return recipient.email_address == thread.author_id[3];})) {
                    self.recipients.push({'full_name': thread.author_id[1],
                                          'name': thread.author_id[2],
                                          'email_address': thread.author_id[3],
                                          'partner_id': false,
                                          'checked': true,
                                          'reason': 'Incoming email author'
                                        });
                }
            });

            return self.recipients;
        },

        on_toggle_quick_composer: function (event) {
            var self = this;
            var $input = $(event.target);

            this.compute_emails_from();
            var email_addresses = _.pluck(this.recipients, 'email_address');

            var suggested_partners = $.Deferred();

            // if clicked: call for suggested recipients
            if (event.type == 'click') {
                this.is_log = $input.hasClass('oe_tl_compose_log');
                suggested_partners = this.parent_thread.ds_thread.call(
                    'message_get_suggested_recipients', [[this.context.default_res_id], this.context])
                    .done(function (additional_recipients) {
                        var thread_recipients = additional_recipients[self.context.default_res_id];

                        _.each(thread_recipients, function (recipient) {
                            var parsed_email = openerp.web_timeline.ChatterUtils.parse_email(recipient[1]);
                            if (_.indexOf(email_addresses, parsed_email[1]) == -1) {
                                self.recipients.push({
                                    'checked': true,
                                    'partner_id': recipient[0],
                                    'full_name': recipient[1],
                                    'name': parsed_email[0],
                                    'email_address': parsed_email[1],
                                    'reason': recipient[2],
                                })
                            }
                        });
                    });
            }
            else {
                suggested_partners.resolve({});
            }

            // when call for suggested partners finished: re-render the widget
            $.when(suggested_partners).pipe(function (additional_recipients) {
                if ((!self.stay_open || (event && event.type == 'click')) 
                     && (!self.show_composer || !self.$('textarea:not(.oe_tl_compact)').val().match(/\S+/) 
                     && !self.attachment_ids.length)) {
                        self.show_composer = !self.show_composer || self.stay_open;
                        self.reinit();
                }
                if (!self.stay_open && self.show_composer && (!event || event.type != 'blur')) {
                    self.$('textarea:not(.oe_tl_compact):first').focus();
                }
            });

            return suggested_partners;
        },

        on_message_post: function (event) {
            if (this.flag_post) return;
            
            var self = this;
            this.flag_post = true;
            if (this.do_check_attachment_upload() && 
               (this.attachment_ids.length || this.$('textarea').val().match(/\S+/))) {
                if (this.is_log) {
                    this.do_send_message_post([], this.is_log);
                }
                else {
                    this.check_recipient_partners().done(function (partner_ids) {
                        self.do_send_message_post(partner_ids, self.is_log);
                    });
                }
            }
        },

        do_send_message_post: function (partner_ids, log) {
            var self = this;

            var values = {
                'body': this.$('textarea').val(),
                'subject': false,
                'parent_id': this.parent_id || this.id,
                'partner_ids': partner_ids,
                'attachment_ids': _.map(this.attachment_ids, function (file) {return file.id;}),
                'context': _.extend(this.parent_thread.context, {
                    'mail_post_autofollow': true,
                    'mail_post_autofollow_partner_ids': partner_ids,
                }),
                'type': 'comment',
                'content_subtype': 'plaintext',
            };

            if (log) 
                values['subtype'] = false;
            else 
                values['subtype'] = 'mail.mt_comment';   
            
            this.parent_thread.ds_thread._model.call('message_post', [this.context.default_res_id], values)
                .done(function (message_id) {
                    var thread = self.parent_thread;

                    // attach message to the thread object
                    thread.message_fetch([["id", "=", message_id]], false, [message_id], 'default', function (arg, data) {
                        var message = data.threads[0][1][0];
                        thread.add_message(message, false);
                        thread.insert_message(message);
                    });

                    self.on_cancel();
                    self.flag_post = false;
            });
        },

        check_recipient_partners: function () {
            var self = this;
            var check_done = $.Deferred();

            var recipients = _.filter(this.recipients, function (recipient) {return recipient.checked});
            var recipients_to_find = _.filter(recipients, function (recipient) {return (! recipient.partner_id)});

            var names_to_find = _.pluck(recipients_to_find, 'full_name');
            var recipients_to_check = _.filter(recipients, function (recipient) { 
                return (recipient.partner_id && ! recipient.email_address) });
            var recipient_ids = _.pluck(_.filter(recipients, function (recipient) { 
                return recipient.partner_id && recipient.email_address }), 'partner_id');

            var names_to_remove = [];
            var recipient_ids_to_remove = [];

            // have unknown names -> call message_get_partner_info_from_emails to try to find partner_id
            var find_done = $.Deferred();
            if (names_to_find.length > 0) {
                find_done = self.parent_thread.ds_thread._model.call(
                'message_partner_info_from_emails', [this.context.default_res_id, names_to_find]);
            }
            else {
                find_done.resolve([]);
            }

            // for unknown names + incomplete partners -> open popup - cancel = remove from recipients
            $.when(find_done).pipe(function (result) {
                var emails_deferred = [];
                var recipient_popups = result.concat(recipients_to_check);

                _.each(recipient_popups, function (partner_info) {
                    var deferred = $.Deferred()
                    emails_deferred.push(deferred);

                    var partner_name = partner_info.full_name;
                    var partner_id = partner_info.partner_id;
                    var parsed_email = mail.ChatterUtils.parse_email(partner_name);

                    var pop = new session.web.form.FormOpenPopup(this);                    
                    pop.show_element(
                        'res.partner',
                        partner_id,
                        {   'force_email': true,
                            'ref': "compound_context",
                            'default_name': parsed_email[0],
                            'default_email': parsed_email[1],
                        }, {
                            title: _t("Please complete partner's informations"),
                        }
                    );
                    pop.on('closed', self, function () {
                        deferred.resolve();
                    });
                    pop.view_form.on('on_button_cancel', self, function () {
                        names_to_remove.push(partner_name);
                        if (partner_id) {
                            recipient_ids_to_remove.push(partner_id);
                        }
                    });
                });

                $.when.apply($, emails_deferred).then(function () {
                    var new_names_to_find = _.difference(names_to_find, names_to_remove);
                    find_done = $.Deferred();

                    if (new_names_to_find.length > 0) {
                        find_done = self.parent_thread.ds_thread._model.call(
                            'message_partner_info_from_emails', [self.context.default_res_id, new_names_to_find, true]);
                    }
                    else {
                        find_done.resolve([]);
                    }

                    $.when(find_done).pipe(function (result) {
                        var recipient_popups = result.concat(recipients_to_check);
                        _.each(recipient_popups, function (partner_info) {
                            if (partner_info.partner_id && _.indexOf(partner_info.partner_id, recipient_ids_to_remove) == -1) {
                                recipient_ids.push(partner_info.partner_id);
                            }
                        });
                    }).pipe(function () {
                        check_done.resolve(recipient_ids);
                    });
                });
            });
            
            return check_done;
        },

        on_full: function () {
            return this.on_compose_fullmail(this.id ? 'reply' : 'comment');
        },

        on_compose_fullmail: function (default_composition_mode) {
            if (!this.do_check_attachment_upload()) 
                return false;

            var self = this;
            var recipient_done = $.Deferred();

            if (this.is_log) 
                recipient_done.resolve([]);
            else 
                recipient_done = this.check_recipient_partners();

            $.when(recipient_done).done(function (partner_ids) {
                console.log("fullmail partners", partner_ids);
                var context = {
                    'default_parent_id': self.id,
                    'default_body': openerp.web_timeline.ChatterUtils.get_text2html(
                                        self.$el ? (self.$el.find('textarea:not(.oe_tl_compact)').val() || '') : ''),
                    'default_partner_ids': partner_ids,
                    'default_is_log': self.is_log,
                    'mail_post_autofollow': true,
                    'mail_post_autofollow_partner_ids': partner_ids,
                    'is_private': self.is_private,
                    'default_attachment_ids': _.map(self.attachment_ids, function (file) { return file.id; }),
                };

                if (default_composition_mode != 'reply' && self.context.default_model && self.context.default_res_id) {
                    context.default_model = self.context.default_model;
                    context.default_res_id = self.context.default_res_id;
                }
                console.log("fullmail context", context);

                var action = {
                    type: 'ir.actions.act_window',
                    res_model: 'mail.compose.message',
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    context: context,
                };

                self.do_action(action);
                self.on_cancel();
            });
        },

        on_checked_recipient: function (event) {
            var $input = $(event.target);
            var full_name = $input.attr("data");
            _.each(this.recipients, function (recipient) {
                if (recipient.full_name == full_name) {
                    recipient.checked = $input.is(":checked");
                }
            });
        },

        /**
         * when a user click on the upload button, send file read on_attachment_loaded
         */
        on_attachment_change: function (event) {
            event.stopPropagation();
            var $target = $(event.target);

            if ($target.val() !== '') {
                var filename = $target.val().replace(/.*[\\\/]/,'');

                // if the files exits for this answer, delete the file before upload
                var attachments = [];
                for (var i in this.attachment_ids) {
                    if ((this.attachment_ids[i].filename || this.attachment_ids[i].name) == filename) {
                        if (this.attachment_ids[i].upload) {
                            return false;
                        }
                        this.ds_attachment.unlink([this.attachment_ids[i].id]);
                    } 
                    else {
                        attachments.push(this.attachment_ids[i]);
                    }
                }

                this.attachment_ids = attachments;

                // submit file
                this.$('form.oe_form_binary_form').submit();
                this.$(".oe_attachment_file").hide();

                this.attachment_ids.push({
                    'id': 0,
                    'name': filename,
                    'filename': filename,
                    'url': '',
                    'upload': true
                });

                this.$(".oe_tl_msg_attachment_list").html(this.display_attachments(this));
            }
        },
        
        /**
         * When the file is uploaded 
         */
        on_attachment_loaded: function (event, result) {
            if (result.erorr || !result.id ) {
                this.do_warn( session.web.qweb.render('mail.error_upload'), result.error);
                this.attachment_ids = _.filter(this.attachment_ids, function (val) { return !val.upload; });
            } 
            else {
                for (var i in this.attachment_ids) {
                    if (this.attachment_ids[i].filename == result.filename && this.attachment_ids[i].upload) {
                        this.attachment_ids[i] = {
                            'id': result.id,
                            'name': result.name,
                            'filename': result.filename,
                            'url': openerp.web_timeline.ChatterUtils.get_attachment_url(
                                        this.session, this.id, result.id)
                        };
                    }
                }
            }

            this.$(".oe_tl_msg_attachment_list").html(this.display_attachments(this));

            var $input = this.$('input.oe_form_binary_file');
            $input.after($input.clone(true)).remove();
            this.$(".oe_attachment_file").show();
        },

        /**
         * Unlink the file on the server and reload display
         */
        on_attachment_delete: function (event) {
            event.stopPropagation();
            var attachment_id = $(event.target).data("id");

            if (attachment_id) {
                var attachments = [];
                for (var i in this.attachment_ids) {
                    if (attachment_id != this.attachment_ids[i].id) {
                        attachments.push(this.attachment_ids[i]);
                    }
                    else {
                        this.ds_attachment.unlink([attachment_id]);
                    }
                }
                this.attachment_ids = attachments;
                this.$(".oe_tl_msg_attachment_list").html(this.display_attachments(this));
            }
        },

        /**
         * Return true if all file are complete else return false and make an alert 
         */
        do_check_attachment_upload: function () {
            if (_.find(this.attachment_ids, function (file) {return file.upload;})) {
                this.do_warn(session.web.qweb.render('mail.error_upload'), 
                             session.web.qweb.render('mail.error_upload_please_wait'));
                return false;
            } 
            else 
                return true;
        },

        do_show_compact: function () {
            this.show_compact_message = true;
            if (!this.show_composer) {
                this.reinit();
            }
        },
    });
    
    /**
     * UserMenu
     * Add a link on the top user bar for write a full mail
     */
    session.web.ComposeMessageTopButton = session.web.Widget.extend ({
        template:'ComposeMessageTopButton',

        events: {
            "click": "on_compose_message",
        },

        on_compose_message: function (ev) {
            ev.preventDefault();
            var action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {},
            };
            session.client.action_manager.do_action(action);
        },
    });

    session.web.SystrayItems.push(session.web.ComposeMessageTopButton);
    session.web.views.add('timeline', 'session.web_timeline.TimelineView');
    session.web.form.widgets.add('mail_thread', 'openerp.web_timeline.TimelineRecordThread');
};