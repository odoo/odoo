/*---------------------------------------------------------
 * OpenERP web_timeline
 *---------------------------------------------------------*/

openerp.web_timeline = function (session) {
    "use strict";

    var _t = session.web._t,
        _lt = session.web._lt;
    var QWeb = openerp.web.qweb;
    var mail = session.mail;

    openerp_timeline_followers(session, mail);          // import timeline_followers.js

    session.web_timeline = {};

    session.web_timeline.TimelineView = session.web.View.extend ({
        display_name: _lt('Timeline'),
        view_type: 'timeline',
        template: 'timeline_wall',

        init: function (parent, dataset, view_id, options) {
            this._super(parent, dataset, view_id, options);

            this.dataset = dataset;
            this.model = dataset.model;
            this.domain = dataset.domain || [];
            this.context = dataset.context || {};

            this.fields_view = {};
            this.fields_keys = [];

            if (!dataset.params) {
                this.dataset.params = {};
                this.dataset.params = {
                    'show_record_name': true,
                    'show_reply_button': true,
                    'show_compose_message': false,
                    'show_compact_message': false, 
                    'view_inbox': false,
                    'fetch_limit': 1000, 
                };
            }

            this.qweb = new QWeb2.Engine();
            this.has_been_loaded = $.Deferred();
        },

        start: function () {
            //this.do_push_state({});
            return this._super.apply(this, arguments);
        },

        view_loading: function (fields_view_get) {
            return this.load_timeline(fields_view_get);           
        },

        load_timeline: function (fields_view_get) {
            this.fields_view = fields_view_get;
            this.fields_keys = _.keys(this.fields_view.fields);
    
            this.add_qweb_template();

            this.has_been_loaded.resolve();
        },

        do_search: function (dom, cxt, group_by) {
            var self = this;
            //this.do_push_state({}); // ???

            var domain = (this.domain).concat(dom || []);
            var context = _.clone(this.context);
                context = _.extend(context, (cxt || {}));
            var node = {};
                node.params = _.clone(this.dataset.params);
                node = _.extend(node, {"domain" : domain, 
                                       "context" : context});

            if (this.root) {
                $('<span class="oe_timeline-placeholder"/>').insertAfter(this.root.$el);
                this.root.destroy();
            }
       
            return this.has_been_loaded.then(function() {
                self.root = new openerp.web_timeline.MailRoot(self, node);
                return self.root.replace(self.$('.oe_timeline-placeholder'));
            });
        },

        add_qweb_template: function () {
            for (var i = 0; i < this.fields_view.arch.children.length; i++) {
                var child = this.fields_view.arch.children[i];
                if (child.tag === "templates") {
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
                            node.attrs[QWeb.prefix + '-raw'] = 'widget.' + 'record_name';
                            break;
                        case 'model':
                            node.attrs[QWeb.prefix + '-raw'] = 'widget.' + 'model_desc';
                            break;
                        case 'author_id':
                            node.attrs[QWeb.prefix + '-raw'] = 'widget.' + 'author_id[2]';
                            break;
                        case 'subtype_id':
                            node.attrs[QWeb.prefix + '-raw'] = 'widget.' + 'subtype';
                            break;
                        default:
                            node.attrs[QWeb.prefix + '-raw'] = 'widget.' + node.attrs['name'];
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
    });

    openerp.web_timeline.TimelineRecordThread = session.web.form.AbstractField.extend({
        template: 'timeline_record_thread',

        init: function (parent, node) {
            this._super.apply(this, arguments);

            this.node = _.clone(node);        
            this.parent = parent;   
            this.dataset = new session.web.DataSet(this, 'mail.message', this.view.dataset.context);
            this.domain = (this.node.params && this.node.params.domain) || (this.field && this.field.domain) || [];
            this.opt = {};

            this.node.params = _.extend({
                'show_reply_button': false,
                'show_read_unread_button': true,
                'read_action': 'unread',
                'show_record_name': false,
                'show_compact_message': true,
                'display_log_button' : true,
                'show_compose_message': this.view.is_action_enabled('edit'),
            }, this.node.params);

            if (this.node.attrs.placeholder) {
                this.node.params.compose_placeholder = this.node.attrs.placeholder;
            }
            if (this.node.attrs.readonly) {
                this.node.params.readonly = this.node.attrs.readonly;
            }
            if ('display_log_button' in this.options) {
                this.node.params.display_log_button = this.options.display_log_button;
            }

            if (!this.parent.is_action_enabled('edit')) {
                this.node.params.show_link = false;
            }

            this.dataset.params = this.node.params;
        },

        start: function () {
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
           
            this.timeline_view = new session.web_timeline.TimelineView(this, this.dataset, false, this.opt);
            this.timeline_view.appendTo(this.$el);

            return this._super.apply(this, arguments);
        },

        _check_visibility: function () {
            this.$el.toggle(this.view.get("actual_mode") !== "create");
        },
 
        render_value: function () {
            if (! this.view.datarecord.id || 
                session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                    this.$('oe_timeline_thread').hide();
                    return;
            }
            
            this.timeline_view.dataset.params = _.extend(this.timeline_view.dataset.params, {
                'message_ids': this.get_value(),
            });
            
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

    /**
     * ------------------------------------------------------------
     * ChatterUtils
     * ------------------------------------------------------------
     * 
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
                'attachment_id': attachment_id
            });
        },

        /**
         * Replaces textarea text into html text (add <p>, <a>)
         * TDE note : should be done server-side, in Python -> use mail.compose.message ?
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
            if (!str) 
                return str;
            
            for(var i = 0, len = str.length; i < len; i++)
                out += _.str.escapeHTML(str[i]) + '&#8203;';
            
            return out;
        },
    };

    openerp.web_timeline.MessageCommon = session.web.Widget.extend({

        init: function (parent, dataset, options) {
            this._super(parent, options);

            // record options
            this.options = dataset.options || options || {};

            // record domain and context
            this.domain = dataset.domain || options.domain || [];
            this.context = _.extend({
                default_model: false,
                default_res_id: 0,
                default_parent_id: false}, options.context || {});

            // data of this message
            this.id = dataset.id ||  false,
            this.last_id = this.id,
            this.model = dataset.model || this.context.default_model || false,
            this.model_desc = dataset.model_desc || false,
            this.res_id = dataset.res_id || this.context.default_res_id ||  false,
            this.parent_id = dataset.parent_id ||  false,
            this.type = dataset.type ||  false,
            this.subtype = dataset.subtype ||  false,
            this.is_author = dataset.is_author ||  false,
            this.author_avatar = dataset.author_avatar || false,
            this.is_private = dataset.is_private ||  false,
            this.subject = dataset.subject ||  false,
            this.name = dataset.name ||  false,
            this.record_name = dataset.record_name ||  false,
            this.body = dataset.body || '',
            this.vote_nb = dataset.vote_nb || 0,
            this.has_voted = dataset.has_voted ||  false,
            this.is_favorite = dataset.is_favorite ||  false,
            this.to_read = dataset.to_read || false,
            this.author_id = dataset.author_id || false,
            this.attachment_ids = dataset.attachment_ids ||  [],
            this.tracking_value_ids = dataset.tracking_value_ids || [],
            this.partner_ids = dataset.partner_ids || [],
            this.date = dataset.date,
            this.user_pid = dataset.user_pid || false;

            this.format_data();

            // update record_name: Partner profile
            if (this.model == 'res.partner') {
                this.record_name = 'Partner Profile of ' + this.record_name;
            }
            else if (this.model == 'hr.employee') {
                this.record_name = 'News from ' + this.record_name;
            }

            // record options and data
            this.options.show_read = false;
            this.options.show_unread = false;

            if (this.options.show_read_unread_button) {
                if (this.options.read_action == 'read')
                    this.options.show_read = true;
                else if (this.options.read_action == 'unread') 
                    this.options.show_unread = true;
                else {
                    this.options.show_read = this.to_read;
                    this.options.show_unread = !this.to_read;
                }
                this.options.rerender = true;
                this.options.toggle_read = true;
            }

            this.view = parent.view;
            this.parent_thread = parent;
            this.thread = false;

            this.tracking_values = (this.tracking_value_ids.length > 0);
            this.partners = (this.partner_ids.length > 0);
            this.attachents = (this.attachment_ids.length > 0);
        },

        /** 
         * Convert date, timerelative and avatar in displayable data. 
         */
        format_data: function () {
            //formating and add some fields for render
            var date = this.date ? session.web.str_to_datetime(this.date) : false;
            if (date) {
                this.display_date = moment(new Date(date).toISOString()).format('ddd MMM DD YYYY LT');
                this.date = this.display_date;
                if (new Date().getTime()-date.getTime() < 7*24*60*60*1000) {
                    this.timerelative = $.timeago(date);
                    this.date = this.timerelative;
                }
            }

            if (this.author_avatar) {
                this.avatar = "data:image/png;base64," + this.author_avatar;
            }
            else if (this.type == 'email' && (!this.author_id || !this.author_id[0])) {
                this.avatar = ('/mail/static/src/img/email_icon.png');
            } 
            else if (this.author_id && this.template != 'mail.compose_message') {
                this.avatar = openerp.web_timeline.ChatterUtils.get_image(
                    this.session, 'res.partner', 'image_small', this.author_id[0]);
            } 
            else {
                this.avatar = openerp.web_timeline.ChatterUtils.get_image(
                    this.session, 'res.users', 'image_small', this.session.uid);
            }

            if (this.author_id && this.author_id[1]) {
                var parsed_email = openerp.web_timeline.ChatterUtils.parse_email(this.author_id[1]);
                this.author_id.push(parsed_email[0], parsed_email[1]);
            }

            if (this.partner_ids && this.partner_ids.length > 3) {
                this.extra_partners_nbr = this.partner_ids.length - 3;
                this.extra_partners_str = ''
                var extra_partners = this.partner_ids.slice(3);

                for (var key in extra_partners) {
                    this.extra_partners_str += extra_partners[key][1];
                }
            }
        },

        /** 
         * Upload the file on the server, add in the attachments list and reload display
         */
        display_attachments: function () {
            for (var l in this.attachment_ids) {
                var attach = this.attachment_ids[l];
                if (!attach.formating) {
                    attach.url = openerp.web_timeline.ChatterUtils
                                    .get_attachment_url(this.session, this.id, attach.id);
                    attach.name = openerp.web_timeline.ChatterUtils
                                    .breakword(attach.name || attach.filename);
                    attach.formating = true;
                }
            }
            this.$(".oe_tl_msg_attachment_list").html( 
                    session.web.qweb.render('timeline_thread_message_attachments', {'widget': this}));
        },

        /**
         * Return the link to resized image
         */
        attachments_resize_image: function (id, resize) {
            return openerp.web_timeline.ChatterUtils.get_image(
                        this.session, 'ir.attachment', 'datas', id, resize);
        },

        /**
         * Get all child message id linked.
         * @return array of id
         */
        get_child_ids: function () {
			return _.map(this.get_childs(), function (val) { return val.id; });
        },    
    
        /** 
         * Get all child message linked.
         * @return array of message object
         */
        get_childs: function (nb_thread_level) {
            var res = [];
            if (arguments[1] && this.id) res.push(this);
            if ((isNaN(nb_thread_level) || nb_thread_level > 0) && this.thread) {
                _(this.thread.messages).each(function (val, key) {
                    res = res.concat( val.get_childs((isNaN(nb_thread_level) ? undefined : nb_thread_level-1), true) );
                });
            }
            return res;
        },

        /**
         * Call on_message_destroy on his parent thread
         */
        destroy: function () {
            this._super();
            this.parent_thread.on_message_destroy(this);
        },
    });

    openerp.web_timeline.ThreadComposeMessage = openerp.web_timeline.MessageCommon.extend({
        template: 'timeline_compose_message',

        init: function (parent, datasets, options) {
            this._super(parent, datasets, options);
            this.show_compact_message = false;
            this.show_delete_attachment = true;
            this.is_log = false;
            this.recipients = [];
            this.recipient_ids = [];
        },

        start: function () {
            this.ds_attachment = new session.web.DataSetSearch(this, 'ir.attachment');
            this.fileupload_id = _.uniqueId('oe_fileupload_temp');
            $(window).on(this.fileupload_id, this.on_attachment_loaded);
            this.display_attachments();
            this.bind_events();

            return this._super.apply(this, arguments);
        },

        bind_events: function () {
            var self = this;            

            this.$('.oe_tl_compact_inbox').on('click', self.on_toggle_quick_composer);
            this.$('.oe_tl_compose_post').on('click', self.on_toggle_quick_composer);
            this.$('.oe_tl_compose_log').on('click', self.on_toggle_quick_composer);
            this.$('.oe_cancel').on('click', _.bind( this.on_cancel, this));
            this.$('.oe_post').on('click', self.on_message_post);
            this.$('.oe_full').on('click', _.bind( this.on_compose_fullmail, this, this.id ? 'reply' : 'comment'));

            this.$('input.oe_form_binary_file').on('change', _.bind( this.on_attachment_change, this));

            // event: delete child attachments off the oe_msg_attachment_list box
            this.$(".oe_tl_msg_attachment_list").on('click', '.oe_delete', this.on_attachment_delete);

            // stack for don't close the compose form if the user click on a button
            this.$('.oe_tl_msg_left, .oe_tl_msg_center').on('mousedown', 
                        _.bind( function () { this.stay_open = true; }, this));
            this.$('.oe_tl_msg_left, .oe_tl_msg_content').on('mouseup', 
                        _.bind( function () { this.$('textarea').focus(); }, this));

            var ev_stay = {};
            ev_stay.mouseup = ev_stay.keydown = ev_stay.focus = function () { self.stay_open = false; };
            this.$('textarea').on(ev_stay);
            this.$('textarea').autosize();

            // auto close
            this.$('textarea').on('blur', self.on_toggle_quick_composer);

            this.$(".oe_recipients").on('change', 'input', this.on_checked_recipient);
        },

        /**
         * when a user click on the upload button, send file read on_attachment_loaded
         */
        on_attachment_change: function (event) {
            var self = this;
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

                this.display_attachments();
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

            this.display_attachments();

            var $input = this.$('input.oe_form_binary_file');
            $input.after($input.clone(true)).remove();
            this.$(".oe_attachment_file").show();
        },

        /**
         * Unlink the file on the server and reload display
         */
        on_attachment_delete: function (event) {
            event.stopPropagation();
            var attachment_id=$(event.target).data("id");

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
                this.display_attachments();
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

        reinit: function() {
            var $render = $(session.web.qweb.render('timeline_compose_message', {'widget': this}));

            $render.insertAfter(this.$el.last());
            this.$el.remove();
            this.$el = $render;

            this.display_attachments();
            this.bind_events();
        },

        on_cancel: function (event) {
            if (event) event.stopPropagation();
            this.attachment_ids = [];
            this.stay_open = false;
            this.show_composer = false;
            this.reinit();
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

        on_message_post: function (event) {
            var self = this;

            if (self.flag_post) 
                return;
            
            self.flag_post = true;
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

        on_checked_recipient: function (event) {
            var $input = $(event.target);
            var full_name = $input.attr("data");
            _.each(this.recipients, function (recipient) {
                if (recipient.full_name == full_name) {
                    recipient.checked = $input.is(":checked");
                }
            });
        },
 
        check_recipient_partners: function () {
            var self = this;
            var check_done = $.Deferred();

            var recipients = _.filter(this.recipients, function (recipient) { return recipient.checked });
            var recipients_to_find = _.filter(recipients, function (recipient) { return (! recipient.partner_id) });

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

        do_send_message_post: function (partner_ids, log) {
            var self = this;

            var values = {
                'body': this.$('textarea').val(),
                'subject': false,
                'parent_id': this.context.default_parent_id,
                'partner_ids': partner_ids,
                'attachment_ids': _.map(this.attachment_ids, function (file) { return file.id; }),
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
            
            this.parent_thread.ds_thread._model.call(
                'message_post', [this.context.default_res_id], values).done(function (message_id) {
                    var thread = self.parent_thread;
                    var root = thread == self.options.root_thread;

                    // create object and attach to the thread object
                    thread.message_fetch([["id", "=", message_id]], false, [message_id], function (arg, data) {
                        var message = thread.create_message_object( data.slice(-1)[0] );
                        // insert the message on dom
                        thread.insert_message( message, root ? undefined : self.$el, root );
                    });

                    self.on_cancel();
                    self.flag_post = false;
            });
       },

       compute_emails_from: function () {
            var self = this;
            var messages = [];

            if (this.parent_thread.parent_message) {
                // go to the parented message
                var message = this.parent_thread.parent_message;
                var parent_message = message.parent_id ? message.parent_thread.parent_message : message;
                if (parent_message) {
                    var messages = [parent_message].concat(parent_message.get_childs());
                }
            } 
            else if (this.options.emails_from_on_composer) {
                // get all wall messages if is not a mail.Wall
                _.each(this.options.root_thread.messages, function (msg) {
                    messages.push(msg); messages.concat(msg.get_childs());});
            }

            _.each(messages, function (thread) {
                if (thread.author_id && !thread.author_id[0] &&
                    !_.find(self.recipients, function (recipient) {return recipient.email_address == thread.author_id[3];})) {
                    self.recipients.push({  'full_name': thread.author_id[1],
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

        do_hide_compact: function () {
            this.show_compact_message = false;
            if (!this.show_composer) {
                this.reinit();
            }
        },

        do_show_compact: function () {
            this.show_compact_message = true;
            if (!this.show_composer) {
                this.reinit();
            }
        },      
    });

    openerp.web_timeline.ThreadMessage = openerp.web_timeline.MessageCommon.extend({
        template: 'timeline_thread_message',

        start: function () {
            var qweb_context = {
                session: session,
                widget: this,
                options: this.options,
            };
            
            this.$el.append(QWeb.render(this.template, {
                'widget': this, 
                'content' : this.view.qweb.render("message_content", qweb_context)
            }));

            this.display_tracking_values();
            this.display_votes();
            this.display_attachments();
            this.display_partners_recipients();
    
            this.bind_events();
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');

            return this._super.apply(this, arguments);
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. 
         */
        bind_events: function () {
            var self = this;
            // header icons bindings
            this.$('.oe_read').on('click', this.on_message_read);
            this.$('.oe_unread').on('click', this.on_message_unread);
            this.$('.oe_msg_delete').on('click', this.on_message_delete);
            this.$('.oe_reply').on('click', this.on_message_reply);
            this.$('.oe_star').on('click', this.on_star);
            this.$('.oe_tl_msg_vote').on('click', this.on_vote);
            this.$('.oe_timeline_vote_count').on('mouseenter', this.on_hover);
            this.$('.oe_timeline_action_author').on('click', this.on_record_author_clicked);
        },

        on_hover : function (event) {
            var self = this;
            var voter = "";
            var limit = 10;
            event.stopPropagation();

            var $target = $(event.target).hasClass("fa-thumbs-o-up") ? $(event.target).parent() : $(event.target);
            // Note: We can set data-content attr on target element once we fetch data so that 
            // next time when one moves mouse on element it saves call
            // But if there is new like comes then we'll not have new likes in popover in that case
            if ($target.data('liker-list'))
            {
                voter = $target.data('liker-list');
                self.bindTooltipTo($target, voter);
                $target.tooltip('hide').tooltip('show');
                $(".tooltip").on("mouseleave", function () {
                    $(this).remove();
                });
            }
            else {
                this.ds_message.call('get_likers_list', [this.id, limit])
                .done(function (data) {
                    _.each(data, function(people, index) {
                        voter = voter + people.substring(0,1).toUpperCase() + people.substring(1);
                        if (index != data.length-1) {
                            voter = voter + "<br/>";
                        }
                    });
                    $target.data('liker-list', voter);
                    self.bindTooltipTo($target, voter);
                    $target.tooltip('hide').tooltip('show');
                    $(".tooltip").on("mouseleave", function () {
                        $(this).remove();
                    });
                });
            }
            return true;
        },

        bindTooltipTo: function ($el, value) {
            $el.tooltip({
                'title': value,
                'placement': 'top',
                'container': this.el,
                'html': true,
                'trigger': 'manual',
                'animation': false
             }).on("mouseleave", function () {
                setTimeout(function () {
                    if (!$(".tooltip:hover").length) {
                        $el.tooltip("hide");
                    }
                },100);
            });
        },

        on_record_author_clicked: function (event) {
            event.preventDefault();
            var partner_id = $(event.target).data('partner');
            var state = {
                'model': 'res.partner',
                'id': partner_id,
                'title': this.record_name
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

        on_message_reply: function (event) {
            event.stopPropagation();
            this.create_thread();
            this.thread.on_compose_message(event);
            return false;
        },

        /**
         * Add or remove a vote for a message and display the result
         */
        on_vote: function (event) {
            event.stopPropagation();
            console.log("on_vote");
            this.ds_message.call('vote_toggle', [[this.id]])
                .then(
                    _.bind(function (vote) {
                        this.has_voted = vote;
                        this.vote_nb += this.has_voted ? 1 : -1;
                        this.display_vote();
                    }, this));
            return false;
        },
    
        /**
         * Instantiate the thread object of this message.
         * Each message have only one thread.
         */
        create_thread: function () {
            if (this.thread) return false;
           
            // create thread
            this.thread = new openerp.web_timeline.MailThread(this, this, {
                    'domain': this.domain,
                    'context': {
                        'default_model': this.model,
                        'default_res_id': this.res_id,
                        'default_parent_id': this.id
                    },
                    'params': this.options
                });

            // insert thread in parent message
            this.thread.insertAfter(this.$el);
        },

        /**
         * Display the render of this message's vote
         */
        display_vote: function () {
            var vote_element = session.web.qweb.render('timeline_thread_message_vote', {'widget': this});

            this.$(".oe_tl_header:first .oe_timeline_vote_count").remove();
            this.$(".oe_tl_header:first .oe_tl_msg_vote").replaceWith(vote_element);
            this.$('.oe_tl_msg_vote').on('click', this.on_vote);
            this.$('.oe_timeline_vote_count').on('mouseenter', this.on_hover);
        },
        
        /**
         * Fade out the message and his child thread.
         * Then this object is destroyed.
         */
        animated_destroy: function (fadeTime) {
            var self=this;
            this.$el.fadeOut(fadeTime, function () {
                self.parent_thread.message_to_expandable(self);
            });
            if (this.thread) {
                this.thread.$el.fadeOut(fadeTime);
            }
        },

        /**
         * Wait a confirmation for delete the message on the DB.
         * Make an animate destroy
         */
        on_message_delete: function (event) {
            event.stopPropagation();
            if (! confirm(_t("Do you really want to delete this message?"))) {
                return false; 
            }
            
            this.animated_destroy(150);
            // delete this message and his childs
            var ids = [this.id].concat( this.get_child_ids() );
            this.ds_message.unlink(ids);
            return false;
        },

        /**
         * Check if the message must be destroy and detroy it or check for re render widget
         * @param {callback} apply function
         */
        check_for_rerender: function () {
            var self = this;

            var messages = [this].concat(this.get_childs());
            var message_ids = _.map(messages, function (msg) { return msg.id;});
            var domain = openerp.web_timeline.ChatterUtils.expand_domain(this.options.root_thread.domain)
                .concat([["id", "in", message_ids ]]);
                
            return this.parent_thread.ds_message.call('message_read', 
                [undefined, domain, [], 0, this.context, this.parent_thread.id])
                .then( function (records) {
                    // remove message not loaded
                    _.map(messages, function (msg) {
                        if (!_.find(records, function (record) { return record.id == msg.id; })) {
                            msg.animated_destroy(150);
                        } 
                        else {
                            msg.renderElement();
                            msg.start();
                        }
                        self.options.root_thread.MailRoot.do_reload_menu_emails();
                    });

                });
        },

        on_message_read: function (event) {
            event.stopPropagation();
            this.on_message_read_unread(true);
            return false;
        },

        on_message_unread: function (event) {
            event.stopPropagation();
            this.on_message_read_unread(false);
            return false;
        },

        /* Set the selected thread and all childs as read or unread, based on
         * read parameter.
         * @param {boolean} read_value
         */
        on_message_read_unread: function (read_value) {
            var self = this;
            var messages = [this].concat(this.get_childs());

            // inside the inbox, when the user mark a message as read/done, don't apply this value
            // for the stared/favorite message
            if (this.options.view_inbox && read_value) {
                var messages = _.filter(messages, function (val) { return !val.is_favorite && val.id; });
                if (!messages.length) {
                    this.check_for_rerender();
                    return false;
                }
            }
            var message_ids = _.map(messages, function (val) { return val.id; });

            this.ds_message.call('set_message_read', [message_ids, read_value, true, this.context])
                .then(function () {
                    // apply modification
                    _.each(messages, function (msg) {
                        msg.to_read = !read_value;
                        if (msg.options.toggle_read) {
                            msg.options.show_read = msg.to_read;
                            msg.options.show_unread = !msg.to_read;
                        }
                    });
                    // check if the message must be display, destroy or rerender
                    self.check_for_rerender();
                });

            return false;
        },

        /**
         * add or remove a favorite (or starred) for a message and change class on the DOM
         */
        on_star: function (event) {
            event.stopPropagation();
            var self=this;
            var button = self.$('.oe_star:first');

            this.ds_message.call('set_message_starred', [[self.id], !self.is_favorite, true])
                .then(function (star) {
                    self.is_favorite=star;
                    if (self.is_favorite) {
                        button.addClass('oe_starred');
                    } 
                    else {
                        button.removeClass('oe_starred');
                    }

                    if (self.options.view_inbox && self.is_favorite) {
                        self.on_message_read_unread(true);
                    } 
                    else {
                        self.check_for_rerender();
                    }
                });
            return false;
        },

        display_votes: function () {
           this.$(".oe_tl_vote")
               .replaceWith(session.web.qweb.render('timeline_thread_message_vote', 
                                            {'widget': this}));
        },
        
        display_tracking_values: function () {
           this.$(".oe_timeline_tracking_value_list")
               .html(session.web.qweb.render('timeline_thread_message.tracking_values', 
                                            {'widget': this}));
        },

        display_partners_recipients: function () {
           this.$(".oe_tl_partners_list")
               .html(session.web.qweb.render('timeline_thread_partners_list', 
                                            {'widget': this}));
        },
    });

    openerp.web_timeline.MailThread = session.web.Widget.extend({
        template: 'timeline_mail_thread',

        init: function (parent, msg_data, dataset) {
            this._super(parent, dataset);

            this.MailRoot = parent instanceof openerp.web_timeline.MailRoot ? parent : false;
            this.domain = dataset.domain || [];
            this.context = _.extend(dataset.context || {});

            this.id = msg_data.id || false;
            this.last_id = msg_data.last_id || false;
            this.parent_id = msg_data.parent_id || false;
            this.is_private = msg_data.is_private || false;
            this.author_id = msg_data.author_id || false;
            this.user_pid = msg_data.user_pid || false;
            
            msg_data.partner_ids = msg_data.partner_ids || [];
            if (msg_data.author_id 
                && !_.contains(_.flatten(msg_data.partner_ids), msg_data.author_id[0]) 
                && msg_data.author_id[0]) {
                    msg_data.partner_ids.push(msg_data.author_id);
            }
            this.partner_ids = msg_data.partner_ids;

            this.options = dataset.params;
            this.options.root_thread = (this.options.root_thread != undefined ? this.options.root_thread : this);

            this.messages = [];
            this.compose_message = false;
            this.parent_message = parent.thread != undefined ? parent : false ;
            this.view = parent.view;

            this.ds_thread = new session.web.DataSetSearch(this, this.context.default_model || 'mail.thread');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
            this.render_mutex = new $.Mutex();
        },

        start: function () {
            this._super.apply(this, arguments);
            return $.when();
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. 
         */
        bind_events: function () {
            var self = this;
            this.$('.oe_timeline_list_recipients .oe_more').on('click', self.on_show_recipients);
            this.$('.oe_timeline_compose_textarea .oe_more_hidden').on('click', self.on_hide_recipients);
        },

        /**
         * Show all the partner list of this parent message
         */
        on_show_recipients: function () {
            var p = $(this).parent(); 
            p.find('.oe_more_hidden, .oe_hidden').show(); 
            p.find('.oe_more').hide(); 
            return false;
        },

        /**
         * Hide a part of the partner list of this parent message
         */
        on_hide_recipients: function () {
            var p = $(this).parent(); 
            p.find('.oe_more_hidden, .oe_hidden').hide(); 
            p.find('.oe_more').show(); 
            return false;
        },

        /**
         * instantiate the compose message object and insert this on the DOM.
         * The compose message is display in compact form.
         */
        instantiate_compose_message: function () {
            // add message composition form view
            if (!this.compose_message) {
                this.compose_message = new openerp.web_timeline.ThreadComposeMessage(this, this, {
                    'context': this.options.compose_as_todo ? 
                                   _.extend(this.context, { 'default_starred': true }) : this.context,
                    'options': this.options,
                });

                this.compose_message.insertBefore(this.$el);
            }
        },
 
        /**
         * If compose_message doesn't exist, instantiate the compose message.
         * Call the on_toggle_quick_composer method to allow the user to write his message.
         * (Is call when a user click on "Reply" button)
         */
        on_compose_message: function (event) {
            this.instantiate_compose_message();
            this.compose_message.on_toggle_quick_composer(event);
            return false;
        },

        /**
         * make a request to read the message (calling RPC to "message_read").
         * The result of this method is send to the switch message for sending ach message to
         * his parented object thread.
         * @param {Array} replace_domain: added to this.domain
         * @param {Object} replace_context: added to this.context
         * @param {Array} ids read (if the are some ids, the method don't use the domain)
         */
        message_fetch: function (replace_domain, replace_context, ids, callback) {
            return this.ds_message.call('message_read', [
                    // ids force to read
                    ids === false ? undefined : ids && ids.slice(0, this.options.fetch_limit),
                    // domain + additional
                    (replace_domain ? replace_domain : this.domain), 
                    // ids allready loaded
                    (this.id ? [this.id].concat( this.get_child_ids() ) : this.get_child_ids()), 
                    // thread level
                    0,
                    // context + additional
                    (replace_context ? replace_context : this.context), 
                    // parent_id
                    this.context.default_parent_id || undefined,
                    this.options.fetch_limit,
                 ]).done(callback ? _.bind(callback, this, arguments) : this.proxy('switch_new_message')
                  ).done(this.proxy('message_fetch_set_read'));
        },

         /**
         * get the parent thread of the messages.
         * Each message is send to his parent object (or parent thread flat mode) for creating the object message.
         * @param : {Array} datas from calling RPC to "message_read"
         */
         switch_new_message: function (records, dom_insert_after) {
            console.log("records", records);

            var self = this;
            var dom_insert_after = typeof dom_insert_after == 'object' ? dom_insert_after : false;

            _(records).each(function (record) {
                // create object and attach to the thread object
                var message = self.create_message_object(record);
                // insert the message on dom
                self.insert_message(message, dom_insert_after);
            });

            if (!records.length && this.options.root_thread == this) {
                this.no_message();
            }
        },

        message_fetch_set_read: function (message_list) {
            if (! this.context.mail_read_set_read) return;
            
            var self = this;
            this.render_mutex.exec(function() {
                var msg_ids = _.pluck(message_list, 'id');
                return self.ds_message.call('set_message_read', [msg_ids, true, false, self.context])
                    .then(function (nb_read) {
                        if (nb_read) {
                            self.options.root_thread.MailRoot.do_reload_menu_emails(); 
                        }
                    });
             });
        },

        /**
         * get all child message/thread id linked.
         * @return array of id
         */
        get_child_ids: function () {
			return _.map(this.get_childs(), function (val) { return val.id; });
        },

        /** 
         * get all child message/thread linked.
         * @param {int} nb_thread_level, number of traversed thread level for this search
         * @return array of thread object
         */
        get_childs: function (nb_thread_level) {
            var res = [];
            if (arguments[1]) res.push(this);
            if (isNaN(nb_thread_level) || nb_thread_level > 0) {
                _(this.messages).each(function (val, key) {
                    if (val.thread) {
                        res = res.concat(val.thread.get_childs(
                                         (isNaN(nb_thread_level) ? undefined : nb_thread_level-1), 
                                         true));
                    }
                });
            }
            return res;
        },

        /**
         * create the message object and attached on this thread.
         * When the message object is create, this method call insert_message for,
         * displaying this message on the DOM.
         * @param : {object} data from calling RPC to "message_read"
         */
        create_message_object: function (data) {
            var self = this;

            data.options = _.extend(data.options || {}, self.options);
            data.record_name = (data.record_name != '' && data.record_name) || 
                               (self.parent_message && self.parent_message.record_name);

            var message = new openerp.web_timeline.ThreadMessage(self, data, {'context': {
                'default_model': data.model,
                'default_res_id': data.res_id,
                'default_parent_id': data.id,
            }});

            // check if the message is already create
            for (var i in self.messages) {
                if (message.id && self.messages[i] && self.messages[i].id == message.id) {
                    self.messages[i].destroy();
                }
            }
            self.messages.push(message);

            return message;
        },

        /**
         * insert the message on the DOM.
         * All message are sorted. The method get the
         * older and newer message to insert the message (before, after).
         * If there are no older or newer, the message is prepend or append to
         * the thread (parent object or on root thread for flat view).
         * The sort is define by the thread_level (O for newer on top).
         * @param : {object} ThreadMessage object
         */
        insert_message: function (message, dom_insert_after, prepend) {
            var self = this;

            if (this.options.show_compact_message) {
                this.instantiate_compose_message();
                this.compose_message.do_show_compact();
            }

            this.$('.oe_view_nocontent').remove();
            if (dom_insert_after && dom_insert_after.parent()[0] == self.$el[0]) {
                message.insertAfter(dom_insert_after);
            } 
            else if (prepend) {
                message.prependTo(self.$el);
            } 
            else {
                message.appendTo(self.$el);
            }

            return message
        },

        /**
         * display the message "there are no message" on the thread
         */
        no_message: function () {           
            var no_message = $(session.web.qweb.render('timeline_no_message', {}));

            if (this.options.help) {
                no_message.html(this.options.help);
            }
            if (!this.$el.find(".oe_view_nocontent").length) {
                no_message.appendTo(this.$el);
            }
        },

        /**
         * this method is call when the widget of a message or an expandable message is destroy
         * in this thread. The this.messages array is filter to remove this message
         */
        on_message_destroy: function (message) {
            this.messages = _.filter(this.messages, function (val) {return !val.isDestroyed();});
            if (this.options.root_thread == this && !this.messages.length) {
                this.no_message();
            }
            return false;
        },
    });

    openerp.web_timeline.MailRoot = session.web.Widget.extend({
        template: 'timeline_mail_root',

        init: function (parent, dataset) {
            this._super(parent, dataset);

            this.dataset = _.clone(dataset);
            this.domain = this.dataset.domain || this.dataset.params.domain || [];
            this.context = this.dataset.context || this.dataset.params.context || {}; 

            this.dataset.params = _.extend({
                'show_reply_button' : false,
                'show_read_unread_button' : false,
                'show_record_name' : false,
                'show_compose_message' : false,
                'show_compact_message' : false,
                'compose_placeholder': false,
                'compose_as_todo' : false,
                'show_link': true,
                'view_inbox': false,
                'message_ids': undefined,
                'readonly' : false,
                'emails_from_on_composer': true,
                'fetch_limit': 30,
            }, this.dataset.params);

            this.view = parent;
            this.dataset.params.help = this.dataset.help || false;
        },

        start: function () {
            this.message_render();
            return this._super.apply(this, arguments);
        },

        /**
         * create an object "related_menu"
         * contains the menu widget and the sub menu related of this wall
         */
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

        message_render: function (search) {
            this.thread = new openerp.web_timeline.MailThread(this, {}, {
                'domain' : this.domain,
                'context' : this.context,
                'params' : this.dataset.params,
            });

            this.thread.appendTo(this.$el);
            
            if (this.dataset.params.show_compose_message) {
                this.thread.instantiate_compose_message();
                this.thread.compose_message.do_show_compact();
            }

            this.thread.message_fetch(null, null, this.dataset.params.message_ids);
        },

    });

    session.web.views.add('timeline', 'session.web_timeline.TimelineView');
    session.web.form.widgets.add('mail_thread', 'openerp.web_timeline.TimelineRecordThread');
}

