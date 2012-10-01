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
            this.$('img.oe_mail_icon').attr('src', user_avatar);
            this.$('div.oe_mail_msg_content').empty();
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
            var msg_node = this.$('div.oe_mail_msg_content');
            return $.when(this.form_view.appendTo(msg_node)).pipe(this.proxy('postprocess_create_form_view'));
        },

        postprocess_create_form_view: function () {
            // handle attachment button
            this.fileupload_id = _.uniqueId('oe_fileupload');
            var button_attach = this.$('button.oe_mail_compose_message_attachment');
            var rendered = session.web.qweb.render('mail.compose_message.add_attachment', {'widget': this});
            $(rendered).insertBefore(button_attach);
            // move the button inside div.oe_hidden_input_file
            var input_node = this.$('input[name=ufile]');
            button_attach.detach().insertAfter(input_node);
            // set the function called when attachments are added
            this.$('input.oe_form_binary_file').change(this.on_attachment_change);
            this.bind_events();
            this.form_view.do_show();
        },

        on_attachment_change: function (event) {
            var $target = $(event.target);
            if ($target.val() !== '') {
                this.$('form.oe_form_binary_form').submit();
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
            var attach_node = this.$('div.oe_mail_compose_message_attachments');
            var rendered = session.web.qweb.render('mail.thread.message.attachments', {'record': this});
            attach_node.empty();
            $(rendered).appendTo(attach_node);
            this.$('.oe_mail_msg_attachments').show();
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
     * Thread Message Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of a messages in a thread. The
     * [thread_level] parameter sets the thread level number:
     * - root thread
     * - - sub message (parent_id = root message)
     * - - - sub thread
     * - - - - sub sub message (parent id = sub thread)
     * - - sub message (parent_id = root message)
     * - - - sub thread
     */

    mail.ThreadMessage = session.web.Widget.extend({
        template: 'mail.thread.message',

        /**
         * @param {Object} parent parent
         * @param {Array} [domain]
         * @param {Object} [context] context of the thread. It should
            contain at least default_model, default_res_id. Please refer to
            the ComposeMessage widget for more information about it.
         * @param {Object} [options]
         *      @param {Object} [thread] read obout mail.Thread object
         *      @param {Object} [message]
         *          @param {Number} [message_ids=null] ids for message_fetch
         *          @param {Number} [message_data=null] already formatted message data, 
         *              for subthreads getting data from their parent
         *          @param {Number} [truncate_limit=250] number of character to
         *              display before having a "show more" link; note that the text
         *              will not be truncated if it does not have 110% of the parameter
         *          @param {Boolean} [show_record_name]
         *          @param {Boolean} [show_reply]
         *          @param {Boolean} [show_reply_by_email]
         *          @param {Boolean} [show_dd_reply_by_email]
         *          @param {Boolean} [show_dd_delete]
         *          @param {Boolean} [show_dd_hide]
         */
        init: function(parent, options) {
            this._super(parent);
            this.domain = options.domain || [];
            this.context = _.extend({
                default_model: 'mail.thread',
                default_res_id:  0,
                default_parent_id: false }, options.context || {});

            // options
            this.options={
                'thread' : options.options.thread,
                'message' : {
                    'message_ids':            options.options.message.message_ids || null,
                    'message_data':           options.options.message.message_data || null,
                    'show_record_name':       options.options.message.show_record_name != undefined ? options.options.message.show_record_name: true,
                    'show_reply':             options.options.message.show_reply || false,
                    'show_reply_by_email':    options.options.message.show_reply_by_email || false,
                    'show_dd_reply_by_email': options.options.message.show_dd_reply_by_email != undefined ? options.options.message.show_dd_reply_by_email: true,
                    'show_dd_delete':         options.options.message.show_dd_delete || false,
                    'show_dd_hide':           options.options.message.show_dd_hide || false,
                    'truncate_limit':         options.options.message.truncate_limit || 250,
                }
            };
            // record options and data
            this.parent_thread= parent.messages!= undefined ? parent : options.options.thread._parents[0] ;

            var param =         options.parameters;
            // child messages
            this.child_ids=     param.child_ids;
            // record parameters
            this.id =           param.id || -1;
            this.model =        param.model || false;
            this.parent_id=     param.parent_id || false;
            this.res_id =       param.res_id || false;
            this.type =         param.type || false;
            this.is_author =    param.is_author || false;
            this.subject =      param.subject || false;
            this.name =         param.name || false;
            this.record_name =  param.record_name || false;
            this.body =         param.body || false;
            this.vote_user_ids =param.vote_user_ids || [];
            this.has_voted =     param.has_voted || false;

            this.vote_user_ids = param.vote_user_ids || [];

            this.unread =       param.unread || false;
            this._date =        param.date;
            this.author_id =    param.author_id || [];
            this.attachment_ids = param.attachment_ids || [];

            this.thread = false;

            if( param.id > 0 ) {
                this.formating_data();
            }

            this.ds_notification = new session.web.DataSetSearch(this, 'mail.notification');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
        },

        formating_data: function(){

            //formating and add some fields for render
            this.timestamp = Date.parse(this._date).getTime();
            this.date = session.web.format_value(this._date, {type:"datetime"});
            this.timerelative = $.timeago(this.date);
            if (this.type == 'email') {
                this.avatar = ('/mail/static/src/img/email_icon.png');
            } else {
                this.avatar = mail.ChatterUtils.get_image(this.session, 'res.partner', 'image_small', this.author_id[0]);
            }
            for (var l in this.attachment_ids) {
                var attach = this.attachment_ids[l];
                attach['url'] = mail.ChatterUtils.get_attachment_url(this.session, attach);
            }
        },
        
        start: function() {
            this._super.apply(this, arguments);
            this.expender();
            this.$el.hide().fadeIn(750);
            this.bind_events();
            this.create_thread();

            this.parent_thread.on_insert_message();
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            this.$('*').unbind('click');

            // event: click on 'Reply' in msg
            this.$el.on('click', 'a.oe_reply', function (event) {
                var act_dom = $(this).parents('li.oe_mail_thread_msg').eq(0).find('div.oe_mail_thread_action:first');
                act_dom.toggle();
            });
            // event: click on 'Attachment(s)' in msg
            this.$el.on('click', 'a.oe_mail_msg_view_attachments', function (event) {
                var act_dom = $(this).parent().parent().parent().find('.oe_mail_msg_attachments');
                act_dom.toggle();
            });
            // event: click on icone 'Read' in header
            this.$el.on('click', 'a.oe_read', this.on_message_read_unread);
            // event: click on icone 'UnRead' in header
            this.$el.on('click', 'a.oe_unread', this.on_message_read_unread);
            // event: click on 'Delete' in msg side menu
            this.$el.on('click', 'a.oe_mail_msg_delete', this.on_message_delete);
            // event: click on 'Reply by email' in msg side menu
            this.$el.on('click', 'a.oe_reply_by_email', function (event) {
                if (! self.compose_message_widget) return true;
                evt = event.target || event.srcElement;
                var msg_id = evt.dataset.msg_id;
                if (! msg_id) return false;
                self.compose_message_widget.refresh({
                    'default_composition_mode': 'reply',
                    'default_parent_id': parseInt(msg_id),
                    'default_content_subtype': 'html'} );
            });
            // event: click on 'Vote' button
            this.$el.on('click', 'button.oe_mail_msg_vote', this.on_vote);
        },

        expender: function(){
            this.$('div.oe_mail_msg_body:first').expander({
                slicePoint: this.options.truncate_limit,
                expandText: 'read more',
                userCollapseText: '[^]',
                detailClass: 'oe_mail_msg_tail',
                moreClass: 'oe_mail_expand',
                lessClass: 'oe_mail_reduce',
                });
        },

        create_thread: function(){
            var self=this;
            if(this.thread){
                return false;
            }
            /*create thread*/
            self.thread = new mail.Thread(self, {
                    'domain': self.domain,
                    'context':{
                        'default_model': self.model,
                        'default_res_id': self.res_id,
                        'default_parent_id': self.id
                    },
                    'options': {
                        'thread' :  self.options.thread,
                        'message' : self.options.message
                    },
                    'parameters':{
                        'model': self.model,
                        'id': self.id,
                        'child_ids': self.child_ids,
                        'parent_id': self.id
                    }
                }
            );
            /*insert thread in parent message*/
            self.thread.appendTo(self.$el.find('div.oe_thread_placeholder'));
        },
        
        animated_destroy: function(options) {
            var self=this;
            //graphic effects  
            if(options.fadeTime) {
                self.$el.fadeOut(options.fadeTime, function(){
                    self.destroy();
                    self.parent_thread.on_message_destroy();
                });
            } else {
                self.destroy();
                self.parent_thread.on_message_destroy();
            }

            for(var i in this.thread.messages){
                this.thread.messages[i].animated_destroy({fadeTime:0});
            }
        },

        on_message_delete: function (event) {
            if (! confirm(_t("Do you really want to delete this message?"))) { return false; }

            var source = $(event.srcElement).parents('[data-msg_id]:first');
            var msg_id = source.data("msg_id");
            var msg_model = source.data("msg_model");
            if (!msg_id || !msg_model) return false;

            var thread=this.browse_message({'id':msg_id, 'model':msg_model});
            if(thread){
                thread.animated_destroy({fadeTime:250});
                // delete this thread and his childs
                var ids = [thread.id].concat( thread.get_child_ids() );
                this.ds_message.unlink(ids);
            }
        },

        /*The selected thread and all childs (messages/thread) became read
        * @param {object} mouse envent
        */
        on_message_read_unread: function (event) {
            var thread=this.get_thread_of_bind_event(event);

            if(thread){
                thread.animated_destroy({fadeTime:250});
                // if this thread is read, all childs thread display is read
                var ids = [thread.id].concat( thread.get_child_ids() );
                thread.ds_notification.call('set_message_read', [ids,$(event.srcElement).hasClass("oe_read")]);
            }
        },

        /** browse message
         * @param {object}{int} option.id
         * @param {object}{string} option.model
         * @param {object}{boolean} option._go_thread_wall
         *      private for check the top thread
         * @return thread object
         */
        browse_message: function(options){
            // goto the wall thread for launch browse
            if(!options._go_thread_wall) {
                options._go_thread_wall = true;

                var top_thread = this.options.thread._parents[0];

                for(var i in top_thread.messages){
                    var res=top_thread.messages[i].browse_message(options);
                    if(res) return res;
                }
            }

            if(options.id && options.model){
                if(this.id==options.id && this.model==options.model)
                    return this;

                for(var i in this.thread.messages){
                    var res=this.thread.messages[i].browse_message(options);
                    if(res) return res;
                }
            }

            return false;
        },

        /* get all child message/thread id linked
        */
        get_child_ids: function(){
            var res=[]
            if(arguments[0]) res.push(this.id);
            if(this.thread){
                res = res.concat( this.thread.get_child_ids(true) );
            }
            return res;
        },


        on_vote: function (event) {
            var self=this;
            var thread=this.get_thread_of_bind_event(event);
            return this.ds_message.call('vote_toggle', [[thread.id]]).pipe(function(vote){

                    self.has_voted=vote;
                    if (!self.has_voted) {
                        var votes=[];
                        for(var i in self.vote_user_ids){
                            if(self.vote_user_ids[i][0]!=self.session.uid)
                                vote.push(self.vote_user_ids[i]);
                        }
                        self.vote_user_ids=votes;
                    }
                    else {
                        self.vote_user_ids.push([self.session.uid, 'You']);
                    }
                    self.display_vote();

                });
        },

        // Render vote Display template.
        display_vote: function () {
            var self = this;
            var vote_element = session.web.qweb.render('mail.thread.message.vote', {'widget': self});
            self.$(".placeholder-mail-vote").empty();
            self.$(".placeholder-mail-vote").html(vote_element);
        },

        get_thread_of_bind_event: function(event){
            var source = $(event.srcElement).parents('[data-msg_id]:first');
            var msg_id = source.data("msg_id");
            var msg_model = source.data("msg_model");
            if (!msg_id || !msg_model) return false;
            return this.browse_message({'id':msg_id, 'model':msg_model});
        }
    });

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
         *      @param {Object} [message] read about mail.ThreadMessage object
         *      @param {Object} [thread]
         *          @param {Number} [thread_level=0] number of thread levels
         *          @param {Boolean} [use_composer] use the advanced composer, or
         *              the default basic textarea if not set
         *          @param {Number} [expandable_number=5] number message show
         *              for each click on "show more message"
         *          @param {Number} [expandable_default_number=5] number message show
         *              on begin before the first click on "show more message"
         *          @param {Boolean} [display_on_flat] display all thread
         *              on the wall thread level (no hierarchy)
         *          @param {Array} [parents] liked with the parents thread
         *              use with browse, fletch... [O]= top parent
         */
        init: function(parent, options) {
            this._super(parent);
            this.domain = options.domain || [];
            this.context = _.extend({
                default_model: 'mail.thread',
                default_res_id:  0,
                default_parent_id: false }, options.context || {});

            // options
            this.options={
                'thread' : {
                    'thread_level':         options.options.thread.thread_level || 0,
                    'show_header_compose':  (options.options.thread.show_header_compose != undefined ? options.options.thread.show_header_compose: false),
                    'use_composer':         options.options.thread.use_composer || false,
                    'expandable_number':    options.options.thread.expandable_number || 5,
                    'expandable_default_number': options.options.thread.expandable_default_number || 5,
                    '_expandable_max':      options.options.thread.expandable_default_number || 5,
                    'display_on_flat':      options.options.thread.display_on_flat || false,
                    '_parents':             (options.options.thread._parents != undefined ? options.options.thread._parents : []).concat( [this] )
                },
                'message' : options.options.message
            };

            // record options and data
            this.parent_linked_message= parent.thread!= undefined ? parent : false ;

            var param = options.parameters
            // child messages
            this.child_ids=param.child_ids || [];
            // datasets and internal vars
            this.id=            param.id || false;
            this.model=         param.model || false;
            this.parent_id=     param.parent_id || false;

            this.messages = [];

            this.ds_thread = new session.web.DataSetSearch(this, this.context.default_model);
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
        },
        
        start: function() {
            // TDE TODO: check for deferred, not sure it is correct
            this._super.apply(this, arguments);

            this.list_ul=this.$('ul.oe_mail_thread_display:first');
            this.more_msg=this.$(">.oe_mail_msg_more_message:first");

            this.display_user_avatar();
            this.display_expandable();
            var display_done = compose_done = false;

            if(this.options.thread._parents[0]==this){
                this.on_first_thread();
            }
            
            // add message composition form view
            compose_done = this.instantiate_composition_form();

            this.bind_events();

            this.switch_new_message(this.child_ids);

            return display_done && compose_done;
        },

        /**
        * Override-hack of do_action: automatically load message on the chatter.
        * Normally it should be called only when clicking on 'Post/Send'
        * in the composition form. */
        do_action: function(action, on_close) {
            //TDE: TODO: instead of reloading, push the message ?
            console.log("do_action");
            this.message_fetch();
            if (this.compose_message_widget) {
                this.compose_message_widget.refresh({
                    'default_parent_id': this.context.default_parent_id,
                    'default_content_subtype': 'plain'} );
            }
            return this._super(action, on_close);
        },

        /* this method is runing for first parent thread
        */
        on_first_thread: function(){
            // fetch and display message, using message_ids if set
            display_done = this.message_fetch(true, [], {});
            //show the first write message
            this.$(">.oe_mail_thread_action").show();
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            // event: click on 'More' at bottom of thread
            this.$el.on('click', 'a.oe_mail_fetch_more', this.do_message_fetch_more);
            // event: writing in basic textarea of composition form (quick reply)
            // event: onblur for hide 'Reply'
            this.$('textarea.oe_mail_compose_textarea:first')
                .keyup(function (event) {
                    var charCode = (event.which) ? event.which : window.event.keyCode;
                    if (event.shiftKey && charCode == 13) { this.value = this.value+"\n"; }
                    else if (charCode == 13) { return self.message_post(); }
                })
                .blur(function (event) {
                    $(this).parents('.oe_mail_thread_action:first').hide();
                });
        },

        /* get all child message/thread id linked
        */
        get_child_ids: function(){
            var res=[];
            for(var i in this.messages){
                res = res.concat( this.messages[i].get_child_ids(true) );
            }
            return res;
        },

        /* this method is call when we insert a message in the thread
        *  and object is create and started
        */
        on_insert_message: function(){
            this.display_expandable();
        },

        /* this method is call when we destroy a message of the thread
        */
        on_message_destroy: function(){
            this.display_expandable();
        },

        /** browse thread
         * @param {object}{int} option.id
         * @param {object}{string} option.model
         * @param {object}{boolean} option._go_thread_wall
         *      private for check the top thread
         * @param {object}{boolean} option.top_thread
         *      return the top thread (wall) if no thread found
         * @return thread object
         */
        browse_thread: function(options){
            // goto the wall thread for launch browse
            if(!options._go_thread_wall) {
                options._go_thread_wall = true;
                return this.options.thread._parents[0].browse_thread(options);
            }
            if(options.id && options.model){
                if(this.id==options.id && this.model==options.model)
                    return this;

                for(var i in this.messages){
                    var res=this.messages[i].thread.browse_thread(options);
                    if(res) return res;
                }
            }

            //if option top_thread, return the top if no found thread
            if(options.top_thread){
                return this;
            }

            return false;
        },

        /** browse message
         * @param {object}{int} option.id
         * @param {object}{string} option.model
         * @param {object}{boolean} option._go_thread_wall
         *      private for check the top thread
         * @return thread object
         */
        browse_message: function(options){
            if(this.options.thread._parents[0].messages[0])
                return this.options.thread._parents[0].messages[0].browse_message(options);
        },

        /** Instantiate the composition form, with every parameters in context
            or in the widget context. */
        instantiate_composition_form: function(context) {
            // add message composition form view
            if (!this.options.thread.show_header_compose || !this.options.thread.use_composer ||
                (this.options.thread.thread_level < this.options.thread._parents.length && this.options.thread._parents[0]!=this)) {
                return false;
            }

            var self=this;
            if (this.compose_message_widget) {
                this.compose_message_widget.destroy();
            }
            this.compose_message_widget = new mail.ComposeMessage(this, {
                'context': _.extend(context || {}, this.context),
            });
            var composition_node = this.$('div.oe_mail_thread_action');
            composition_node.empty();
            var compose_done = this.compose_message_widget.appendTo(composition_node)
                .then(function(){ self.message_post_composition_form(); });
            return compose_done;
        },

        refresh_composition_form: function (context) {
            if (! this.compose_message_widget) return;
            return this.compose_message_widget.refresh(context);
        },

        /*post a message and fletch the message with wizard form*/
        message_post_composition_form: function () {
            var self=this;
            self.$("button.oe_mail_compose_message_button_send").mouseup(function(){
                window.setTimeout(function(){
                    self.$('.oe_mail_msg_content textarea').val("");
                    self.browse_thread({'top_thread':1}).message_fetch();
                },250);
                console.log("todo : load after write on wizard !");
            });
        },

        /*post a message and fletch the message*/
        message_post: function (body) {
            var self = this;
            if (! body) {
                var comment_node = this.$('textarea');
                var body = comment_node.val();
                comment_node.val('');
            }
            if(body.match(/\S+/)) {
                //this.$("textarea:first").blur();
                return this.ds_thread.call('message_post_api', [
                    [this.context.default_res_id], body, false, 'comment', false, this.context.default_parent_id, undefined])
                    .then(this.proxy('switch_new_message'));
            }
            else {
                return false;
            }
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

            // initial mode: try to use message_data or message_ids
            if (initial_mode && this.options.thread.message_data) {
                return this.create_message_object(this.options.message_data);
            }
            // domain and context: options + additional
            fetch_domain = _.flatten([this.domain, additional_domain || []], true);
            fetch_context = _.extend({}, this.context, additional_context || {});
            fetch_context.message_loaded= [this.id].concat( self.options.thread._parents[0].get_child_ids() );
            // select message_ids (optional)
            message_ids = this.options.thread.message_ids && this.options.thread.message_ids[0] ? this.options.thread.message_ids : false;

            return this.ds_message.call('message_read', [message_ids, fetch_domain, (this.options.thread.thread_level+1), fetch_context, this.context.default_parent_id || undefined]
                ).then(this.proxy('switch_new_message'));
        },

        /* create record object and linked him
         */
        create_message_object: function (record) {
            var self = this;

            if(record.id < 0){
                return false;
            }

            // chck if the message is already read
            for(var i in this.messages){
                if(this.messages[i].id==record.id && this.messages[i].model==record.model)
                    return false;
            }

            // delete child no read
            var child_ids=[];
            for(var i in this.child_ids){
                if(this.child_ids[i]!=record.id)
                    child_ids.push( this.child_ids[i] );
            }
            this.child_ids=child_ids;

            /*create message*/
            var message = new mail.ThreadMessage(self, {
                'domain': record.domain,
                'context': {
                    'default_model':        record.model,
                    'default_res_id':       record.res_id,
                    'default_parent_id':    record.id },
                'options':{
                    'thread': self.options.thread,
                    'message': self.options.message
                },
                'parameters': record
            });
            
            self.insert_message(message);
            self.messages.push(message);
        },

        /** Displays a record and performs some formatting on the record :
         * - record.date: formatting according to the user timezone
         * - record.timerelative: relative time givein by timeago lib
         * - record.avatar: image url
         * - record.attachment_ids[].url: url of each attachment */
        insert_message: function (message) {
            var self=this;
            // check older and newer message for insert
            var parent_newer = false;
            var parent_older = false;
            for(var i in this.messages){
                if(this.messages[i].timestamp > message.timestamp){
                    if(!parent_newer || parent_newer.timestamp>this.messages[i].timestamp)
                        parent_newer = this.messages[i];
                } else if(this.messages[i].timestamp>0 && this.messages[i].timestamp < message.timestamp) {
                    if(!parent_older || parent_older.timestamp<this.messages[i].timestamp)
                        parent_older = this.messages[i];
                }
            }

            if(parent_newer)
                message.insertAfter(parent_newer.$el);
            else if(parent_older)
                message.insertBefore(parent_older.$el);
            else
                message.prependTo(this.list_ul);
        },

        /* Hide messages if they are more message that _expandable_max
        *  display "show more messages"
        */
        display_expandable: function(){
            var self =this;
            if(self.messages.length>self.options._expandable_max){
                self.list_ul.find('>li:gt('+(self.options._expandable_max-1)+')').hide();
                self.more_msg.show();
            } else {
                self.list_ul.find('>li').show();
                self.more_msg.hide();
            }

            if(self.child_ids>0){
                self.more_msg.show();
            }
            console.log("display_expandable");
        },

        display_user_avatar: function () {
            var avatar = mail.ChatterUtils.get_image(this.session, 'res.users', 'image_small', this.session.uid);
            return this.$('img.oe_mail_icon').attr('src', avatar);
        },
        
        /*  Display the message if if the msg_id don't exists.
        *   If the record have a parent, insert parent or inside parent */
        switch_new_message: function(records) {
            var self=this;
            _(records.reverse()).each(function (record) {
                if(!self.options.thread.display_on_flat){
                    if(record.parent_id==self.id && record.model==self.model){
                        return self.create_message_object( record );
                    } else if(record.parent_id){
                        var thread=self.browse_thread({'id':record.parent_id, 'model':record.model});
                        if(thread) {
                            return thread.create_message_object( record );
                        }
                    }
                }
                var thread=self.browse_thread({'top_thread':true});
                return thread.create_message_object( record );
            });
        },

        /** Action: 'shows more' to fetch new messages */
        do_message_fetch_more: function (event) {
            event.stopPropagation();

            var source = $(event.srcElement).parents('[data-msg_id]:first');
            var msg_id = source.data("msg_id");
            var msg_model = source.data("msg_model");

            var thread=this.browse_thread({'id':msg_id, 'model':msg_model, 'top_thread': true});
            if(thread){
                thread.options._expandable_max+=thread.options.expendable_number;
                if(thread.display_expandable())
                    return thread.message_fetch(false, this.fetch_more_domain, this.fetch_more_context);
            }
        },
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
                this.$('oe_mail_thread').hide();
                return;
            }
            // update context
            _.extend(this.options.context, {
                default_res_id: this.view.datarecord.id,
                default_model: this.view.model });
            // update domain
            var domain = this.options.domain.concat([['model', '=', this.view.model], ['res_id', '=', this.view.datarecord.id]]);
            // create and render Thread widget
            var show_header_compose = this.view.is_action_enabled('edit') ||
                (this.getParent().fields.message_is_follower && this.getParent().fields.message_is_follower.get_value());

            this.thread = new mail.Thread(self, {
                    'domain': domain,
                    'context': this.options.context,
                    'options':{
                        'thread':{
                            'thread_level': this.options.thread_level,
                            'show_header_compose': show_header_compose,
                            'use_composer': show_header_compose,
                            'display_on_flat':true
                        },
                        'message':{
                            'show_dd_delete': true,
                            'show_reply_by_email': show_header_compose,
                        }
                    },
                    'parameters': {},
                }
            );

            this.$('ul.oe_mail_wall_threads').empty();
            var render_res = session.web.qweb.render('mail.wall_thread_container', {});
            $(render_res).appendTo(this.$('ul.oe_mail_wall_threads'));

            return this.thread.appendTo( this.$('li.oe_mail_wall_thread:last') );
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
            return this.searchview.appendTo(this.$('.oe_view_manager_view_search')).then(function () {
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
            var domain = this.options.domain.concat(this.search_results['domain']);

            this.thread = new mail.Thread(this, {
                    'domain' : this.options.domain,
                    'context' : this.options.context,
                    'options': {
                        'thread' :{
                            'thread_level': this.options.thread_level,
                            'use_composer': true,
                            'show_header_compose': true, 
                        },
                        'message': {
                            'show_reply': this.options.thread_level > 0,
                            'show_dd_hide': true,
                        },
                    },
                    'parameters': {},
                }
            );

            this.$('ul.oe_mail_wall_threads').empty();
            var render_res = session.web.qweb.render('mail.wall_thread_container', {});
            $(render_res).appendTo(this.$('ul.oe_mail_wall_threads'));

            return this.thread.appendTo( this.$('li.oe_mail_wall_thread:last') );
        },
    });
};
