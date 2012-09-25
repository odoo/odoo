openerp.mail = function(session) {
    var _t = session.web._t,
       _lt = session.web._lt;

    var mail = session.mail = {};

    openerp_mail_followers(session, mail);        // import mail_followers.js

    /**
     * ------------------------------------------------------------
     * FormView
     * ------------------------------------------------------------
     * 
     * Override of formview do_action method, to catch all return action about
     * mail.compose.message. The purpose is to bind 'Send by e-mail' buttons
     * and redirect them to the Chatter.
     */

    session.web.FormView = session.web.FormView.extend({
        do_action: function(action, on_close) {
            if (action.res_model == 'mail.compose.message' &&
                action.context && action.context.redirect == true &&
                this.fields && this.fields.message_ids && this.fields.message_ids.view.get("actual_mode") != 'create') {
                var thread = this.fields.message_ids.thread;
                thread.refresh_composition_form(action.context);
                return true;
            }
            else {
                return this._super(action, on_close);
            }
        },
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

    mail.ChatterUtils = {

        /** Get an image in /web/binary/image?... */
        get_image: function(session, model, field, id) {
            return session.prefix + '/web/binary/image?session_id=' + session.session_id + '&model=' + model + '&field=' + field + '&id=' + (id || '');
        },

        /** Get the url of an attachment {'id': id} */
        get_attachment_url: function (session, attachment) {
            return session.origin + '/web/binary/saveas?session_id=' + session.session_id + '&model=ir.attachment&field=datas&filename_field=datas_fname&id=' + attachment['id'];
        },

        /** Check if the current user is the message author */
        is_author: function (widget, message_user_id) {
            return (widget.session && widget.session.uid != 0 && widget.session.uid == message_user_id);
        },

        /** Replaces some expressions
         * - :name - shortcut to an image
         */
        do_replace_expressions: function (string) {
            var icon_list = ['al', 'pinky']
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
    };


    /**
     * ------------------------------------------------------------
     * ComposeMessage widget
     * ------------------------------------------------------------
     * 
     * This widget handles the display of a form to compose a new message.
     * This form is a mail.compose.message form_view.
     */

    mail.ComposeMessage = session.web.Widget.extend({
        template: 'mail.compose_message',
        
        /**
         * @param {Object} parent parent
         * @param {Object} [options]
         * @param {Object} [options.context] context passed to the
         *  mail.compose.message DataSetSearch. Please refer to this model
         *  for more details about fields and default values.
         */
        init: function (parent, options) {
            var self = this;
            this._super(parent);
            this.attachment_ids = [];
            // options
            this.options = options || {};
            this.options.context = options.context || {};
            this.options.form_xml_id = options.form_xml_id || 'email_compose_message_wizard_form_chatter';
            this.options.form_view_id = options.form_view_id || false;
            this.show_attachment_delete = true;
        },

        start: function () {
            this._super.apply(this, arguments);
            // customize display: add avatar, clean previous content
            var user_avatar = mail.ChatterUtils.get_image(this.session, 'res.users', 'image_small', this.session.uid);
            this.$el.find('img.oe_mail_icon').attr('src', user_avatar);
            this.$el.find('div.oe_mail_msg_content').empty();
            // create a context for the dataset and default_get of the wizard
            var context = _.extend({}, this.options.context);
            this.ds_compose = new session.web.DataSetSearch(this, 'mail.compose.message', context);
            // find the id of the view to display in the chatter form
            if (this.options.form_view_id) {
                return this.create_form_view();
            }
            else {
                var data_ds = new session.web.DataSetSearch(this, 'ir.model.data');
                return data_ds.call('get_object_reference', ['mail', this.options.form_xml_id]).pipe(this.proxy('create_form_view'));
            }
        },

        /** Create a FormView, then append it to the to widget DOM. */
        create_form_view: function (new_form_view_id) {
            var self = this;
            this.options.form_view_id = (new_form_view_id && new_form_view_id[1]) || this.options.form_view_id;
            // destroy previous form_view if any
            if (this.form_view) { this.form_view.destroy(); }
            // create the FormView
            this.form_view = new session.web.FormView(this, this.ds_compose, this.options.form_view_id, {
                action_buttons: false,
                pager: false,
                initial_mode: 'edit',
                disable_autofocus: true,
            });
            // add the form, bind events, activate the form
            var msg_node = this.$el.find('div.oe_mail_msg_content');
            return $.when(this.form_view.appendTo(msg_node)).pipe(this.proxy('postprocess_create_form_view'));
        },

        postprocess_create_form_view: function () {
            // handle attachment button
            this.fileupload_id = _.uniqueId('oe_fileupload');
            var button_attach = this.$el.find('button.oe_mail_compose_message_attachment');
            var rendered = session.web.qweb.render('mail.compose_message.add_attachment', {'widget': this});
            $(rendered).insertBefore(button_attach);
            // move the button inside div.oe_hidden_input_file
            var input_node = this.$el.find('input[name=ufile]');
            button_attach.detach().insertAfter(input_node);
            // set the function called when attachments are added
            this.$el.find('input.oe_form_binary_file').change(this.on_attachment_change);
            this.bind_events();
            this.form_view.do_show();
        },

        on_attachment_change: function (event) {
            var $target = $(event.target);
            if ($target.val() !== '') {
                this.$el.find('form.oe_form_binary_form').submit();
                session.web.blockUI();
            }
        },

        on_attachment_delete: function (event) {
            if (event.target.dataset && event.target.dataset.id) {
                var attachment_id = parseInt(event.target.dataset.id);
                var idx = _.pluck(this.attachment_ids, 'id').indexOf(attachment_id);
                if (idx == -1) return false;
                new session.web.DataSetSearch(this, 'ir.attachment').unlink(attachment_id);
                this.attachment_ids.splice(idx, 1);
                this.display_attachments();
            }
        },

        display_attachments: function () {
            var attach_node = this.$el.find('div.oe_mail_compose_message_attachments');
            var rendered = session.web.qweb.render('mail.thread.message.attachments', {'record': this});
            attach_node.empty();
            $(rendered).appendTo(attach_node);
            this.$el.find('.oe_mail_msg_attachments').show();
            var composer_attachment_ids = _.pluck(this.attachment_ids, 'id');
            var onchange_like = {'value': {'attachment_ids': composer_attachment_ids}}
            this.form_view.on_processed_onchange(onchange_like, []);
        },

        /**
         * Reinitialize the widget field values to the default values obtained
         * using default_get on mail.compose.message. This allows to reinitialize
         * the widget without having to rebuild a complete form view.
         * @param {Object} new_context: context of the refresh */
        refresh: function (new_context) {
            if (! this.form_view) return;
            var self = this;
            this.attachments = [];
            this.options.context = _.extend(this.options.context, new_context || {});
            this.ds_compose.context = _.extend(this.ds_compose.context, this.options.context);
            return this.ds_compose.call('default_get', [
                ['subject', 'body_text', 'body', 'partner_ids', 'composition_mode',
                    'use_template', 'template_id', 'model', 'res_id', 'parent_id', 'content_subtype'],
                this.ds_compose.get_context(),
            ]).then( function (result) {
                self.form_view.on_processed_onchange({'value': result}, []);
                self.attachment_ids = [];
                self.display_attachments();
            });
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            // event: add a new attachment
            $(window).on(this.fileupload_id, function() {
                var args = [].slice.call(arguments).slice(1);
                var attachment = args[0];
                attachment['url'] = mail.ChatterUtils.get_attachment_url(self.session, attachment);
                self.attachment_ids.push(attachment);
                self.display_attachments();
                session.web.unblockUI();
            });
            // event: delete an attachment
            this.$el.on('click', '.oe_mail_attachment_delete', self.on_attachment_delete);
        },
    }),

    /** 
     * ------------------------------------------------------------
     * Thread Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of a thread of messages. The
     * [thread_level] parameter sets the thread level number:
     * - root message
     * - - sub message (parent_id = root message)
     * - - - sub sub message (parent id = sub message)
     * - - sub message (parent_id = root message)
     */

    mail.Thread = session.web.Widget.extend({
        template: 'mail.thread',

        /**
         * @param {Object} parent parent
         * @param {Array} [domain]
         * @param {Object} [context] context of the thread. It should
            contain at least default_model, default_res_id. Please refer to
            the ComposeMessage widget for more information about it.
         * @param {Object} [options]
         * @param {Number} [options.message_ids=null] ids for message_fetch
         * @param {Number} [options.message_data=null] already formatted message
            data, for subthreads getting data from their parent
         * @param {Number} [options.thread_level=0] number of thread levels
         * @param {Boolean} [options.use_composer] use the advanced composer, or
            the default basic textarea if not set
         * @param {Number} [options.truncate_limit=250] number of character to
         *      display before having a "show more" link; note that the text
         *      will not be truncated if it does not have 110% of the parameter
         */
        init: function(parent, domain, context, options) {
            this._super(parent);
            this.domain = domain || [];
            this.context = _.extend({
                default_model: 'mail.thread',
                default_res_id:  0,
                default_parent_id: false }, context || {});
            // options
            this.options = {
                message_ids: options.message_ids || null,
                message_data: options.message_data || null,
                thread_level: options.thread_level || 0,
                use_composer: options.use_composer || false,
                show_header_compose: options.show_header_compose != undefined ? options.show_header_compose: true,
                show_record_name: options.show_record_name != undefined ? options.show_record_name: true,
                show_reply: options.show_reply || false,
                show_reply_by_email: options.show_reply_by_email || false,
                show_dd_reply_by_email:options.show_dd_reply_by_email != undefined ? options.show_dd_reply_by_email: true,
                show_dd_delete: options.show_dd_delete || false,
                show_dd_hide: options.show_dd_hide || false,
                show_more: options.show_more || false,
                truncate_limit: options.truncate_limit || 250,
            }
            // datasets and internal vars
            this.records = {};
            this.ds_thread = new session.web.DataSetSearch(this, this.context.default_model);
            this.ds_notification = new session.web.DataSetSearch(this, 'mail.notification');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
        },
        
        start: function() {
            // TDE TODO: check for deferred, not sure it is correct
            this._super.apply(this, arguments);
            this.bind_events();
            // fetch and display message, using message_ids if set
            var display_done = $.when(this.message_fetch(true, [], {})).then(this.proxy('do_customize_display'));
            // add message composition form view
            if (this.options.show_header_compose && this.options.use_composer) {
                var compose_done = this.instantiate_composition_form();
            }
            return display_done && compose_done;
        },

        /** Customize the display
         * - show_header_compose: show the composition form in the header */
        do_customize_display: function() {
            this.display_user_avatar();
            if (this.options.show_header_compose) {
                this.$el.find('div.oe_mail_thread_action').eq(0).show();
            }
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            // event: click on 'More' at bottom of thread
            this.$el.on('click', 'button.oe_mail_button_more', this.do_message_fetch_more);
            // event: writing in basic textarea of composition form (quick reply)
            this.$el.find('textarea.oe_mail_compose_textarea').keyup(function (event) {
                var charCode = (event.which) ? event.which : window.event.keyCode;
                if (event.shiftKey && charCode == 13) { this.value = this.value+"\n"; }
                else if (charCode == 13) { return self.message_post(); }
            });
            // event: click on 'Reply' in msg
            this.$el.on('click', 'a.oe_mail_msg_reply', function (event) {
                var act_dom = $(this).parents('li.oe_mail_thread_msg').eq(0).find('div.oe_mail_thread_action:first');
                act_dom.toggle();
            });
            // event: click on 'Attachment(s)' in msg
            this.$el.on('click', 'a.oe_mail_msg_view_attachments', function (event) {
                var act_dom = $(this).parent().parent().parent().find('.oe_mail_msg_attachments');
                act_dom.toggle();
            });
            // event: click on 'Delete' in msg side menu
            this.$el.on('click', 'a.oe_mail_msg_delete', this.on_message_delete);
            // event: click on 'Hide' in msg side menu
            this.$el.on('click', 'a.oe_mail_msg_hide', this.on_message_read);
            // event: click on 'Reply by email' in msg side menu
            this.$el.on('click', 'a.oe_mail_msg_reply_by_email', function (event) {
                if (! self.compose_message_widget) return true;
                var msg_id = event.target.dataset.msg_id || event.srcElement.dataset.msg_id;
                if (! msg_id) return false;
                self.compose_message_widget.refresh({
                    'default_composition_mode': 'reply',
                    'default_parent_id': parseInt(msg_id),
                    'default_content_subtype': 'html'} );
            });
            // event: click on 'Vote' button
            this.$el.on('click', 'button.oe_mail_msg_vote', this.on_vote);
        },

        on_message_delete: function (event) {
            if (! confirm(_t("Do you really want to delete this message?"))) { return false; }
            var msg_id = event.srcElement.dataset.id;
            if (! msg_id) return false;
            $(event.srcElement).parents('li.oe_mail_thread_msg').eq(0).remove();
            return this.ds_message.unlink([parseInt(msg_id)]);
        },

        on_message_read: function (event) {
            //TDE: TODO
            var msg_id = event.target.dataset.id || event.srcElement.dataset.id;
            if (! msg_id) return false;
            $(event.target || event.srcElement).parents('li.oe_mail_thread_msg').eq(0).remove();
            return this.ds_notification.call('set_message_read', [parseInt(msg_id)]);
        },

        on_vote: function (event) {
            event.stopPropagation();
            var self = this;
            var message_id = $(event.srcElement).parent().data().msg_id;
            var vote_node = $(event.srcElement).parents('li').eq(0);
            if (! message_id) { return false; }
            return this.ds_message.call('vote_toggle', [[parseInt(message_id)]]).pipe(
                self.toggle_vote(message_id, vote_node));
        },

        /**
         * Override-hack of do_action: automatically reload the chatter.
         * Normally it should be called only when clicking on 'Post/Send'
         * in the composition form. */
        do_action: function(action, on_close) {
            //TDE: TODO: instead of reloading, push the message ?
            this.message_clean();
            this.message_fetch();
            if (this.compose_message_widget) {
                this.compose_message_widget.refresh({
                    'default_composition_mode': 'comment',
                    'default_parent_id': this.context.default_parent_id,
                    'default_content_subtype': 'plain'} );
            }
            // return this._super(action, on_close);
        },

        /** Instantiate the composition form, with every parameters in context
            or in the widget context. */
        instantiate_composition_form: function(context) {
            if (this.compose_message_widget) {
                this.compose_message_widget.destroy();
            }
            this.compose_message_widget = new mail.ComposeMessage(this, {
                'context': _.extend(context || {}, this.context),
            });
            var composition_node = this.$el.find('div.oe_mail_thread_action');
            composition_node.empty();
            var compose_done = this.compose_message_widget.appendTo(composition_node);
            return compose_done;
        },

        refresh_composition_form: function (context) {
            if (! this.compose_message_widget) return;
            return this.compose_message_widget.refresh(context);
        },

        /** Clean the thread */
        message_clean: function() {
            this.$el.find('div.oe_mail_thread_display').empty();
        },

        /** Fetch messages
         * @param {Bool} initial_mode: initial mode: try to use message_data or
         *  message_ids, if nothing available perform a message_read; otherwise
         *  directly perform a message_read
         * @param {Array} additional_domain: added to this.domain
         * @param {Object} additional_context: added to this.context
         */
        message_fetch: function (initial_mode, additional_domain, additional_context) {
            var self = this;
            // domain and context: options + additional
            fetch_domain = _.flatten([this.domain, additional_domain || []], true)
            fetch_context = _.extend(this.context, additional_context || {})
            // initial mode: try to use message_data or message_ids
            if (initial_mode && this.options.message_data) {
                return this.message_display(this.options.message_data);
            }
            message_ids = initial_mode && this.options.message_ids != null && this.options.message_ids || false;
            return this.ds_message.call('message_read', [message_ids, fetch_domain, this.options.thread_level, undefined, fetch_context]
                ).then(this.proxy('message_display'));
        },

        /* Display a list of records
         * A specific case is done for 'expandable' messages that are messages
            displayed under a 'show more' button form
         */
        message_display: function (records) {
            var self = this;
            var _expendable = false;
            _(records).each(function (record) {
                if (record.type == 'expandable') {
                    _expendable = true;
                    self.update_fetch_more(true);
                    self.fetch_more_domain = record.domain;
                    self.fetch_more_context = record.context;
                }
                else {
                    self.display_record(record);
                    self.thread = new mail.Thread(self, self.domain,
                        {   'default_model': record.model,
                            'default_res_id': record.res_id,
                            'default_parent_id': record.id },
                        {   'message_data': record.child_ids,
                            'thread_level': self.options.thread_level - 1,
                            'show_header_compose': false,
                            'show_reply': self.options.show_reply && self.options.thread_level > 1,
                            'show_reply_by_email': self.options.show_reply_by_email,
                            'show_dd_hide': self.options.show_dd_hide,
                            'show_dd_delete': self.options.show_dd_delete });
                    self.$el.find('li.oe_mail_thread_msg:last').append('<div class="oe_mail_thread_subthread"/>');
                    self.thread.appendTo(self.$el.find('div.oe_mail_thread_subthread:last'));
                }
            });
            if (! _expendable) {
                this.update_fetch_more(false);
            }
        },

        /** Displays a record and performs some formatting on the record :
         * - record.date: formatting according to the user timezone
         * - record.timerelative: relative time givein by timeago lib
         * - record.avatar: image url
         * - record.attachment_ids[].url: url of each attachment
         * - record.is_author: is the current user the author of the record */
        display_record: function (record) {
            // formatting and additional fields
            record.date = session.web.format_value(record.date, {type:"datetime"});
            record.timerelative = $.timeago(record.date);
            if (record.type == 'email') {
                record.avatar = ('/mail/static/src/img/email_icon.png');
            } else {
                record.avatar = mail.ChatterUtils.get_image(this.session, 'res.partner', 'image_small', record.author_id[0]);
            }
            for (var l in record.attachment_ids) {
                var attach = record.attachment_ids[l];
                attach['url'] = mail.ChatterUtils.get_attachment_url(this.session, attach);
            }
            record.is_author = mail.ChatterUtils.is_author(this, record.author_user_id[0]);
            // add to internal storage
            this.records[record.id] = record;
            // render, add the expand feature
            var rendered = session.web.qweb.render('mail.thread.message', {'record': record, 'thread': this, 'options': this.options});
            $(rendered).appendTo(this.$el.children('div.oe_mail_thread_display:first'));
            this.$el.find('div.oe_mail_msg_body').expander({
                slicePoint: this.options.truncate_limit,
                expandText: 'read more',
                userCollapseText: '[^]',
                detailClass: 'oe_mail_msg_tail',
                moreClass: 'oe_mail_expand',
                lessClass: 'oe_mail_reduce',
                });
        },

        // Render vote Display template.
        toggle_vote: function (message_id, vote_node) {
            var self = this;
            var record = this.records[message_id];
            if (record.has_voted) {
                var idx = _.map(record.vote_user_ids, function (x) { return x[0]; }).indexOf(message_id);
                record.vote_user_ids.splice(idx, 1);
            }
            else {
                record.vote_user_ids.push([this.session.uid, 'You']);
            }
            record.has_voted = ! record.has_voted;
            var vote_element = session.web.qweb.render('mail.thread.message.vote', {'record': record});
            vote_node.empty();
            vote_node.html(vote_element);
        },

        /** Display 'show more' button */
        update_fetch_more: function (new_value) {
            if (new_value) {
                    this.$el.find('div.oe_mail_thread_more:last').show();
            } else {
                    this.$el.find('div.oe_mail_thread_more:last').hide();
            }
        },

        display_user_avatar: function () {
            var avatar = mail.ChatterUtils.get_image(this.session, 'res.users', 'image_small', this.session.uid);
            return this.$el.find('img.oe_mail_icon').attr('src', avatar);
        },
        
        message_post: function (body) {
            var self = this;
            if (! body) {
                var comment_node = this.$el.find('textarea');
                var body = comment_node.val();
                comment_node.val('');
            }
            return this.ds_thread.call('message_post', [
                [this.context.default_res_id], body, false, 'comment', this.context.default_parent_id, undefined]
                ).then(self.message_fetch());
        },

        /** Action: 'shows more' to fetch new messages */
        do_message_fetch_more: function () {
            return this.message_fetch(false, this.fetch_more_domain, this.fetch_more_context);
        },

        // TDE: keep currently because need something similar
        // /**
        //  * Create a domain to fetch new comments according to
        //  * comment already present in comments_structure
        //  * @param {Object} comments_structure (see chatter utils)
        //  * @returns {Array} fetch_domain (OpenERP domain style)
        //  */
        // get_fetch_domain: function (comments_structure) {
        //     var domain = [];
        //     var ids = comments_structure.root_ids.slice();
        //     var ids2 = [];
        //     // must be child of current parent
        //     if (this.options.parent_id) { domain.push(['id', 'child_of', this.options.parent_id]); }
        //     _(comments_structure.root_ids).each(function (id) { // each record
        //         ids.push(id);
        //         ids2.push(id);
        //     });
        //     if (this.options.parent_id != false) {
        //         ids2.push(this.options.parent_id);
        //     }
        //     // must not be children of already fetched messages
        //     if (ids.length > 0) {
        //         domain.push('&');
        //         domain.push('!');
        //         domain.push(['id', 'child_of', ids]);
        //     }
        //     if (ids2.length > 0) {
        //         domain.push(['id', 'not in', ids2]);
        //     }
        //     return domain;
        // },
    });


    /** 
     * ------------------------------------------------------------
     * mail_thread Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of messages on a document. Its main
     * use is to receive a context and a domain, and to delegate the message
     * fetching and displaying to the Thread widget.
     */
    session.web.form.widgets.add('mail_thread', 'openerp.mail.RecordThread');
    mail.RecordThread = session.web.form.AbstractField.extend({
        template: 'mail.record_thread',

        init: function() {
            this._super.apply(this, arguments);
            this.options.domain = this.options.domain || [];
            this.options.context = {'default_model': 'mail.thread', 'default_res_id': false};
            this.options.thread_level = this.options.thread_level || 0;
        },

        start: function() {
            this._super.apply(this, arguments);
            // NB: check the actual_mode property on view to know if the view is in create mode anymore
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
        },

        _check_visibility: function() {
            this.$el.toggle(this.view.get("actual_mode") !== "create");
        },

        set_value: function() {
            var self = this;
            this._super.apply(this, arguments);
            if (! this.view.datarecord.id || session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$el.find('oe_mail_thread').hide();
                return;
            }
            // update context
            _.extend(this.options.context, {
                default_res_id: this.view.datarecord.id,
                default_model: this.view.model });
            // update domain
            var domain = this.options.domain.concat([['model', '=', this.view.model], ['res_id', '=', this.view.datarecord.id]]);
            // create and render Thread widget
            this.$el.find('div.oe_mail_recthread_main').empty();
            var thread = new mail.Thread(self, domain, this.options.context,
                {   'thread_level': this.options.thread_level,
                    'use_composer': true,
                    'show_dd_delete': true,
                    'show_reply_by_email': true });
            return thread.appendTo(this.$el.find('div.oe_mail_recthread_main'));
        },
    });


    /** 
     * ------------------------------------------------------------
     * Wall Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of messages on a Wall. Its main
     * use is to receive a context and a domain, and to delegate the message
     * fetching and displaying to the Thread widget.
     */
    session.web.client_actions.add('mail.wall', 'session.mail.Wall');
    mail.Wall = session.web.Widget.extend({
        template: 'mail.wall',

        /**
         * @param {Object} parent parent
         * @param {Object} [options]
         * @param {Array} [options.domain] domain on the Wall
         * @param {Object} [options.context] context, is an object. It should
         *      contain default_model, default_res_id, to give it to the threads.
         * @param {Number} [options.thread_level] number of thread levels to display
         *      0 being flat.
         */
        init: function (parent, options) {
            this._super(parent);
            this.options = options || {};
            this.options.domain = options.domain || [];
            this.options.context = options.context || {};
            this.options.thread_level = options.thread_level || 1;
            this.search_results = {'domain': [], 'context': {}, 'groupby': {}}
            this.ds_msg = new session.web.DataSetSearch(this, 'mail.message');
        },

        start: function () {
            this._super.apply(this, arguments);
            var searchview_ready = this.load_searchview({}, false);
            var thread_displayed = this.message_render();
            return (searchview_ready && thread_displayed);
        },

        /**
         * Load the mail.message search view
         * @param {Object} defaults ??
         * @param {Boolean} hidden some kind of trick we do not care here
         */
        load_searchview: function (defaults, hidden) {
            var self = this;
            this.searchview = new session.web.SearchView(this, this.ds_msg, false, defaults || {}, hidden || false);
            return this.searchview.appendTo(this.$el.find('.oe_view_manager_view_search')).then(function () {
                self.searchview.on_search.add(self.do_searchview_search);
            });
        },

        /**
         * Get the domains, contexts and groupbys in parameter from search
         * view, then render the filtered threads.
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
                return self.message_render();
            });
        },

        /** Clean and display the threads */
        message_render: function () {
            this.$el.find('ul.oe_mail_wall_threads').empty();
            var domain = this.options.domain.concat(this.search_results['domain']);
            var render_res = session.web.qweb.render('mail.wall_thread_container', {});
            $(render_res).appendTo(this.$el.find('ul.oe_mail_wall_threads'));
            var thread = new mail.Thread(this, domain, this.options.context,
                {   'thread_level': this.options.thread_level,
                    'use_composer': true,
                    'show_reply': this.options.thread_level > 0,
                    'show_dd_hide': true,
                }
            );
            return thread.appendTo(this.$el.find('li.oe_mail_wall_thread:last'));
        },
    });
};
