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
     * mail.compose.message. The purpose is to bind 'Send by e-mail' buttons.
     */

    session.web.FormView = session.web.FormView.extend({
        do_action: function(action) {
            if (action.res_model == 'mail.compose.message') {
                /* hack for stop context propagation of wrong value
                 * delete this hack when a global method to clean context is create
                 */
                var context_keys = ['default_template_id', 'default_composition_mode', 
                    'default_use_template', 'default_partner_ids', 'default_model',
                    'default_res_id', 'default_subtype', 'active_id', 'lang',
                    'bin_raw', 'tz', 'active_model', 'edi_web_url_view', 'active_ids']
                for (var key in action.context) {
                    if (_.indexOf(context_keys, key) == -1) {
                        action.context[key] = null;
                    }
                }
                /* end hack */
            }
            return this._super.apply(this, arguments);
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

        /* replace textarea text into html text
         * (add <p>, <a>)
         * TDE note : should not be here, but server-side I think ...
        */
        get_text2html: function(text){
            return text
                .replace(/[\n\r]/g,'<br/>')
                .replace(/((?:https?|ftp):\/\/[\S]+)/g,'<a href="$1">$1</a> ')
        }
    };


    /**
     * ------------------------------------------------------------
     * ComposeMessage widget
     * ------------------------------------------------------------
     * 
     * This widget handles the display of a form to compose a new message.
     * This form is a mail.compose.message form_view.
     * On first time : display a compact textarea but is not the compose form.
     * When the user focus this box, the compose message is intantiate and 
     * with focus on the textarea.
    */
    
    mail.ThreadComposeMessage = session.web.Widget.extend({
        template: 'mail.compose_message.compact',
                    // expandable view : 'mail.compose_message'

        /**
         * @param {Object} parent parent
         * @param {Object} [options]
         *      @param {Object} [context] context passed to the
         *          mail.compose.message DataSetSearch. Please refer to this model
         *          for more details about fields and default values.
         */

        init: function (parent, datasets, options) {
            var self = this;
            this._super(parent);
            this.context = options.context || {};

            this.datasets = {
                'attachment_ids' : [],
                'id': datasets.id,
                'model': datasets.model,
                'show_compact': true,
                'res_model': datasets.res_model,
                'is_private': datasets.is_private || false,
                'partner_ids': datasets.partner_ids || [],
                'avatar': mail.ChatterUtils.get_image(this.session, 'res.users', 'image_small', this.session.uid),
            };
            this.options={};
            this.options.display_indented_thread = options.options.display_indented_thread || -1;
            this.options.show_attachment_delete = true;

            this.parent_thread= parent.messages!= undefined ? parent : false;

            this.ds_attachment = new session.web.DataSetSearch(this, 'ir.attachment');

            this.fileupload_id = _.uniqueId('oe_fileupload_temp');
            $(window).on(self.fileupload_id, self.on_attachment_loaded);

            this.$render_expandable = false;
            this.$render_compact = false;
        },

        start: function(){
            this.$render_compact = this.$el;

            if(this.datasets.show_compact) {
                this.$render_compact.show();
            } else {
                this.$render_compact.hide();
            }

            this.bind_events();
        },

        /* upload the file on the server, add in the attachments list and reload display
         */
        display_attachments: function(){
            var self = this;
            var render = $(session.web.qweb.render('mail.thread.message.attachments', {'widget': self}));
            if(!this.list_attachment){
                this.$('.oe_msg_attachment_list').replaceWith( render );
            } else {
                this.list_attachment.replaceWith( render );
            }
            this.list_attachment = this.$(".oe_msg_attachments");

            // event: delete an attachment
            this.$el.on('click', '.oe_mail_attachment_delete', self.on_attachment_delete);
        },

        /* when a user click on the upload button, send file read on_attachment_loaded
        */
        on_attachment_change: function (event) {
            event.stopPropagation();
            var self = this;
            var $target = $(event.target);
            if ($target.val() !== '') {

                var filename = $target.val().replace(/.*[\\\/]/,'');

                // if the files exits for this answer, delete the file before upload
                var attachments=[];
                for(var i in this.datasets.attachment_ids){
                    if((this.datasets.attachment_ids[i].filename || this.datasets.attachment_ids[i].name) == filename){
                        if(this.datasets.attachment_ids[i].upload){
                            return false;
                        }
                        this.ds_attachment.unlink([this.datasets.attachment_ids[i].id]);
                    } else {
                        attachments.push(this.datasets.attachment_ids[i]);
                    }
                }
                this.datasets.attachment_ids = attachments;

                // submit file
                //session.web.blockUI();
                self.$('form.oe_form_binary_form').submit();

                this.$(".oe_attachment_file").hide();

                this.datasets.attachment_ids.push({
                    'id': 0,
                    'name': filename,
                    'filename': filename,
                    'url': '',
                    'upload': true
                });
                this.display_attachments();
            }
        },
        
        /* when the file is uploaded 
        */
        on_attachment_loaded: function (event, result) {
            //session.web.unblockUI();
            for(var i in this.datasets.attachment_ids){
                if(this.datasets.attachment_ids[i].filename == result.filename && this.datasets.attachment_ids[i].upload) {
                    this.datasets.attachment_ids[i]={
                        'id': result.id,
                        'name': result.name,
                        'filename': result.filename,
                        'url': mail.ChatterUtils.get_attachment_url(this.session, result)
                    };
                }
            }
            this.display_attachments();

            var $input = this.$('input.oe_form_binary_file');
            $input.after($input.clone(true)).remove();
            this.$(".oe_attachment_file").show();
        },

        /* unlink the file on the server and reload display
         */
        on_attachment_delete: function (event) {
            event.stopPropagation();
            var attachment_id=$(event.target).data("id");
            if (attachment_id) {
                var attachments=[];
                for(var i in this.datasets.attachment_ids){
                    if(attachment_id!=this.datasets.attachment_ids[i].id){
                        attachments.push(this.datasets.attachment_ids[i]);
                    }
                    else {
                        this.ds_attachment.unlink([attachment_id]);
                    }
                }
                this.datasets.attachment_ids = attachments;
                this.display_attachments();
            }
        },

        /* to avoid having unsorted file on the server.
            we will show the users files of the first message post
            TDE note: unnecessary call to server I think
         */
        // set_free_attachments: function(){
        //     var self=this;
        //     this.parent_thread.ds_message.call('user_free_attachment').then(function(attachments){
        //         this.attachment_ids=[];
        //         for(var i in attachments){
        //             self.attachment_ids[i]={
        //                 'id': attachments[i].id,
        //                 'name': attachments[i].name,
        //                 'filename': attachments[i].filename,
        //                 'url': mail.ChatterUtils.get_attachment_url(self.session, attachments[i])
        //             };
        //         }
        //         self.display_attachments();
        //     });
        // },

        bind_events: function() {
            var self = this;

            // set the function called when attachments are added
            this.$el.on('change', 'input.oe_form_binary_file', self.on_attachment_change );
            this.$el.on('click', 'a.oe_cancel', self.on_cancel );
            this.$el.on('click', 'button.oe_post', function(){self.on_message_post()} );
            this.$el.on('click', 'button.oe_full', function(){self.on_compose_fullmail()} );

            this.$('textarea.oe_compact').on('focus', self.on_compose_expandable);
        },

        on_compose_fullmail: function(){
            var attachments=[];
            for(var i in this.datasets.attachment_ids){
                attachments.push(this.datasets.attachment_ids[i].id);
            }
            var partner_ids=[];
            for(var i in this.datasets.partner_ids){
                partner_ids.push(this.datasets.partner_ids[i][0]);
            }

            var action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                action_from: 'mail.ThreadComposeMessage',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    'default_model': false,
                    'default_res_id': 0,
                    'default_content_subtype': 'html',
                    'default_parent_id': this.datasets.id,
                    'default_body': mail.ChatterUtils.get_text2html(this.$('textarea').val() || ''),
                    'default_attachment_ids': attachments,
                    'default_partner_ids': partner_ids
                },
            };
            this.do_action(action);
        },

        on_cancel: function(event){
            if(event) event.stopPropagation();
            this.$('textarea').val("");
            this.$('input[data-id]').remove();
            //this.attachment_ids=[];
            this.display_attachments();
            this.$el.hide();
        },

        /*post a message and fetch the message*/
        on_message_post: function (body) {
            var self = this;

            if (! body) {
                var comment_node = this.$('textarea');
                var body = comment_node.val();
                comment_node.val('');
            }

            var attachments=[];
            for(var i in this.datasets.attachment_ids){
                if(this.datasets.attachment_ids[i].upload){
                    session.web.dialog($('<div>' + session.web.qweb.render('CrashManager.warning', {message: 'Please, wait while the file is uploading.'}) + '</div>'));
                    return false;
                }
                attachments.push(this.datasets.attachment_ids[i].id);
            }

            if(body.match(/\S+/)) {
                this.parent_thread.ds_thread.call('message_post_api', [
                        this.context.default_res_id, 
                        mail.ChatterUtils.get_text2html(body), 
                        false, 
                        'comment', 
                        'mail.mt_comment',
                        this.context.default_parent_id, 
                        attachments,
                        this.parent_thread.context
                    ]).then(function(records){
                        self.parent_thread.switch_new_message(records);
                        self.datasets.attachment_ids=[];
                        self.on_cancel();
                    });
                return true;
            }
        },

        /* convert the compact mode into the compose message
        */
        on_compose_expandable: function(event){
            if(event) event.stopPropagation();

            var self = this;

            if(!this.$render_expandable) {
                this.$render_expandable = $(session.web.qweb.render('mail.compose_message', {'widget': this}));
                this.$render_expandable.hide();

                this.$render_expandable.insertAfter( this.$render_compact );
                this.display_attachments();
                
                this.$render_expandable.on('blur', 'textarea', this.on_compose_expandable);

                /* stack for don't close the compose form if the user click on a button */
                this.$render_expandable.on('focus', 'textarea', function () { self.stay_open = false; });
                this.$render_expandable.on('mousedown', function () { self.stay_open = true; });
            }
            if(this.$render_expandable.is(':hidden')){

                this.$render_expandable.show();
                this.$render_compact.hide();
                this.$render_expandable.find('textarea').focus();

            } else if(!this.stay_open){

                this.$render_expandable.hide();
                if(this.datasets.show_compact) {
                    this.$render_compact.show();
                } else {
                    this.$render_compact.hide();
                }

            }
            return true;
        },

        do_hide_compact: function() {
            this.$render_compact.hide();
            this.datasets.show_compact = false;
        },

        do_show_compact: function() {
            this.$render_compact.show();
            this.datasets.show_compact = true;
        }
    });

    /** 
     * ------------------------------------------------------------
     * Thread Message Expandable Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display the expandable message in a thread.
     * - thread
     * - - visible message
     * - - expandable
     * - - visible message
     * - - visible message
     * - - expandable
     */
    mail.ThreadExpandable = session.web.Widget.extend({
        template: 'mail.thread.expandable',

        init: function(parent, datasets, options) {
            this._super(parent);
            this.domain = options.domain || [];
            this.context = _.extend({
                default_model: 'mail.thread',
                default_res_id: 0,
                default_parent_id: false }, options.context || {});

            this.datasets = {
                'id' : datasets.id || -1,
                'model' : datasets.model || false,
                'parent_id' : datasets.parent_id || false,
                'nb_messages' : datasets.nb_messages || 0,
                'type' : 'expandable',
                'max_limit' : datasets.max_limit || false,
                'flag_used' : false,
            };

            // record options and data
            this.parent_thread= parent.messages!= undefined ? parent : options.options._parents[0] ;
        },

        
        start: function() {
            this._super.apply(this, arguments);
            this.bind_events();
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            this.$el.on('click', 'a.oe_msg_fetch_more', self.on_expandable);
        },

        animated_destroy: function(options) {
            var self=this;
            //graphic effects
            if(options && options.fadeTime) {
                self.$el.fadeOut(options.fadeTime, function(){
                    self.destroy();
                });
            } else {
                self.destroy();
            }
        },

        /*The selected thread and all childs (messages/thread) became read
        * @param {object} mouse envent
        */
        on_expandable: function (event) {
            if(event)event.stopPropagation();
            if(this.datasets.flag_used) {
                return false
            }
            this.datasets.flag_used = true;

            this.animated_destroy({'fadeTime':300});
            this.parent_thread.message_fetch(false, this.domain, this.context);
            return false;
        },
    });

    /** 
     * ------------------------------------------------------------
     * Thread Message Widget
     * ------------------------------------------------------------
     * This widget handles the display of a messages in a thread. 
     * Displays a record and performs some formatting on the record :
     * - record.date: formatting according to the user timezone
     * - record.timerelative: relative time givein by timeago lib
     * - record.avatar: image url
     * - record.attachment_ids[].url: url of each attachmentThe
     * thread view :
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
         *...  @param {int} [show_reply_button] number thread level to display the reply button
         *...  @param {int} [show_read_unread_button] number thread level to display the read/unread button
         */
        init: function(parent, datasets, options) {
            this._super(parent);

            // record datasets
            this.datasets = _.extend({
                'id' : -1,
                'model' : false,
                'parent_id': false,
                'res_id' : false,
                'type' : false,
                'is_author' : false,
                'is_private' : false,
                'subject' : false,
                'name' : false,
                'record_name' : false,
                'body' : false,
                'vote_nb' :0,
                'has_voted' : false,
                'is_favorite' : false,
                'thread_level' : 0,
                'to_read' : true,
                'author_id' : [],
                'attachment_ids' : [],
            }, datasets || {});
            this.datasets._date = datasets.date;

            // record domain and context
            this.domain = options.domain || [];
            this.context = _.extend({
                default_model: 'mail.thread',
                default_res_id: 0,
                default_parent_id: false }, options.context || {});

            // record options
            this.options = _.extend(options.options, {
                'message_ids': options.options.message_ids || null,
                'message_data': options.options.message_data || null,
                'show_record_name': options.options.show_record_name != undefined ? options.options.show_record_name: true,
                'truncate_limit': options.options.truncate_limit || 250,
                'show_reply_button': options.options.show_reply_button || -1,
                'show_read_unread_button': options.options.show_read_unread_button || -1
            });

            this.datasets.show_reply_button = this.options.show_reply_button>this.datasets.thread_level;
            this.datasets.show_read_unread_button = this.options.show_read_unread_button>this.datasets.thread_level;

            // record options and data
            this.parent_thread= parent.messages!= undefined ? parent : options.options._parents[0];
            this.thread = false;

            if( this.datasets.id > 0 ) {
                this.formating_data();
            }

            this.ds_notification = new session.web.DataSetSearch(this, 'mail.notification');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
            this.ds_follow = new session.web.DataSetSearch(this, 'mail.followers');
        },

        formating_data: function(){

            //formating and add some fields for render
            this.datasets.date = session.web.format_value(this.datasets._date, {type:"datetime"});
            this.datasets.timerelative = $.timeago(this.datasets.date);
            if (this.datasets.type == 'email') {
                this.datasets.avatar = ('/mail/static/src/img/email_icon.png');
            } else {
                this.datasets.avatar = mail.ChatterUtils.get_image(this.session, 'res.partner', 'image_small', this.datasets.author_id[0]);
            }
            for (var l in this.datasets.attachment_ids) {
                var attach = this.datasets.attachment_ids[l];
                attach['url'] = mail.ChatterUtils.get_attachment_url(this.session, attach);
            }
        },
        
        start: function() {
            this._super.apply(this, arguments);
            this.expender();
            this.$el.hide().fadeIn(750);
            this.bind_events();
            this.create_thread();
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;

            // event: click on 'Attachment(s)' in msg
            this.$('a.oe_msg_view_attachments:first').on('click', function (event) {
                self.$('.oe_msg_attachments:first').toggle();
            });
            // event: click on icone 'Read' in header
            this.$el.on('click', 'a.oe_read', this.on_message_read_unread);
            // event: click on icone 'UnRead' in header
            this.$el.on('click', 'a.oe_unread', this.on_message_read_unread);
            // event: click on 'Delete' in msg side menu
            this.$el.on('click', 'a.oe_msg_delete', this.on_message_delete);

            // event: click on 'Reply' in msg
            this.$el.on('click', 'a.oe_reply', this.on_message_reply);
            // event: click on 'Vote' button
            this.$el.on('click', 'button.oe_msg_vote', this.on_vote);
            // event: click on 'starred/favorite' button
            this.$el.on('click', 'a.oe_mail_starbox', this.on_star);
        },

        on_message_reply:function(event){
            event.stopPropagation();
            this.thread.on_compose_message();
            return false;
        },

        expender: function(){
            this.$('.oe_msg_body:first').expander({
                slicePoint: this.options.truncate_limit,
                expandText: 'read more',
                userCollapseText: '[^]',
                detailClass: 'oe_msg_tail',
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
            self.thread = new mail.Thread(self, self.datasets, {
                    'domain': self.domain,
                    'context':{
                        'default_model': self.datasets.model,
                        'default_res_id': self.datasets.res_id,
                        'default_parent_id': self.datasets.id
                    },
                    'options': self.options
                }
            );
            /*insert thread in parent message*/
            self.thread.insertAfter(self.$el);
        },
        
        animated_destroy: function(options) {
            var self=this;
            //graphic effects  
            if(options && options.fadeTime) {
                self.$el.fadeOut(options.fadeTime, function(){
                    self.destroy();
                });
            } else {
                self.destroy();
            }
        },

        on_message_delete: function (event) {
            event.stopPropagation();
            if (! confirm(_t("Do you really want to delete this message?"))) { return false; }
            
            this.animated_destroy({fadeTime:250});
            // delete this message and his childs
            var ids = [this.datasets.id].concat( this.get_child_ids() );
            this.ds_message.unlink(ids);
            this.animated_destroy();
            return false;
        },

        /*The selected thread and all childs (messages/thread) became read
        * @param {object} mouse envent
        */
        on_message_read_unread: function (event) {
            event.stopPropagation();
            // if this message is read, all childs message display is read
            var ids = [this.datasets.id].concat( this.get_child_ids() );
            var read = $(event.srcElement).hasClass("oe_read");
            this.$el.removeClass(read ? 'oe_msg_unread':'oe_msg_read').addClass(read ? 'oe_msg_read':'oe_msg_unread');

            if( (read && this.options.typeof_thread == 'inbox') ||
                (!read && this.options.typeof_thread == 'archives')) {
                this.animated_destroy({fadeTime:250});
            }

            this.ds_notification.call('set_message_read', [ids, read]);
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
            // goto the wall thread for launch browse
            if(!options._go_thread_wall) {
                options._go_thread_wall = true;
                for(var i in this.options._parents[0].messages){
                    var res=this.options._parents[0].messages[i].browse_message(options);
                    if(res) return res;
                }
            }

            if(this.datasets.id==options.id)
                return this;

            for(var i in this.thread.messages){
                if(this.thread.messages[i].thread){
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
            if(arguments[0]) res.push(this.datasets.id);
            if(this.thread){
                res = res.concat( this.thread.get_child_ids(true) );
            }
            return res;
        },

        on_vote: function (event) {
            event.stopPropagation();
            var self=this;
            return this.ds_message.call('vote_toggle', [[self.datasets.id]]).pipe(function(vote){

                self.datasets.has_voted=vote;
                self.datasets.vote_nb += self.datasets.has_voted ? 1 : -1;
                self.display_vote();
            });
            return false;
        },

        // Render vote Display template.
        display_vote: function () {
            var self = this;
            var vote_element = session.web.qweb.render('mail.thread.message.vote', {'widget': self});
            self.$(".oe_msg_vote:first").remove();
            self.$(".oe_mail_vote_count:first").replaceWith(vote_element);
        },

        // Stared/unstared + Render star.
        on_star: function (event) {
            event.stopPropagation();
            var self=this;
            var button = self.$('button.oe_mail_starbox:first');
            return this.ds_message.call('favorite_toggle', [[self.datasets.id]]).pipe(function(star){
                self.datasets.is_favorite=star;
                if(self.datasets.is_favorite){
                    button.addClass('oe_stared');
                } else {
                    button.removeClass('oe_stared');
                    if( self.options.typeof_thread == 'stared' ) {
                        self.animated_destroy({fadeTime:250});
                    }
                }
            });
            return false;
        },

    });

    /** 
     * ------------------------------------------------------------
     * Thread Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of a thread of messages. The
     * thread view:
     * - root thread
     * - - sub message (parent_id = root message)
     * - - - sub thread
     * - - - - sub sub message (parent id = sub thread)
     * - - sub message (parent_id = root message)
     * - - - sub thread
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
         *          @param {Number} [expandable_number=5] number message show
         *              for each click on "show more message"
         *          @param {Number} [expandable_default_number=5] number message show
         *              on begin before the first click on "show more message"
         *          @param {int} [display_indented_thread] number thread level to indented threads.
         *              other are on flat mode
         *          @param {Select} [typeof_thread] inbox/archives/stared/sent
         *              type of thread and option for user application like animate
         *              destroy for read/unread
         *          @param {Array} [parents] liked with the parents thread
         *              use with browse, fetch... [O]= top parent
         */
        init: function(parent, datasets, options) {
            this._super(parent);
            this.domain = options.domain || [];
            this.context = _.extend({
                default_model: 'mail.thread',
                default_res_id: 0,
                default_parent_id: false }, options.context || {});

            // options
            this.options = _.extend(options.options, {
                'expandable_number': options.options.expandable_number || 5,
                'expandable_default_number': options.options.expandable_default_number || 5,
                '_expandable_max': options.options.expandable_default_number || 5,
                'display_indented_thread': options.options.display_indented_thread || -1,
                'show_reply_button': options.options.show_reply_button || -1,
                'typeof_thread': options.options.typeof_thread || 'inbox',
                'show_header_compose': options.options.show_header_compose || false,
                '_parents': (options.options._parents != undefined ? options.options._parents : []).concat( [this] )
            });

            // record options and data
            this.parent_message= parent.thread!= undefined ? parent : false ;

            // datasets and internal vars
            this.datasets = {
                'id' : datasets.id || false,
                'model' : datasets.model || false,
                'parent_id' : datasets.parent_id || false,
                'is_private' : datasets.is_private || false,
                'author_id' : datasets.author_id || false,
                'thread_level' : (datasets.thread_level+1) || 0,
                'partner_ids' : []
            };

            this.datasets.show_composeform = this.options.show_header_compose && this.options.show_reply_button>this.datasets.thread_level;

            for(var i in datasets.partner_ids){
                if(datasets.partner_ids[i][0]!=(datasets.author_id ? datasets.author_id[0] : -1)){
                    this.datasets.partner_ids.push(datasets.partner_ids[i]);
                }
            }

            this.messages = [];
            this.ComposeMessage = false;

            this.ds_thread = new session.web.DataSetSearch(this, this.context.default_model || 'mail.thread');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
        },
        
        start: function() {
            this._super.apply(this, arguments);
            if(this.datasets.show_composeform){
                this.instantiate_ComposeMessage();
            }
            this.bind_events();
        },

        instantiate_ComposeMessage: function(){
            // add message composition form view
            this.ComposeMessage = new mail.ThreadComposeMessage(this, this.datasets, {
                'context': this.context,
                'options': this.options,
            });

            if(this.datasets.thread_level){
                this.ComposeMessage.appendTo(this.$el);
            } else {
                // root view
                this.ComposeMessage.prependTo(this.$el);
            }
            this.ComposeMessage.do_hide_compact();
        },

        /* When the expandable object is visible on screen (with scrolling)
         * then the on_expandable function is launch
        */
        on_scroll: function(event){
            if(event)event.stopPropagation();
            var message = this.messages[0];
            if(message && message.datasets.type=="expandable" && message.datasets.max_limit){
                var pos = message.$el.position();
                if(pos.top){
                    /* bottom of the screen */
                    var bottom = $(window).scrollTop()+$(window).height()+200;
                    if(bottom - pos.top > 0){
                        message.on_expandable();
                    }
                }

            }
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            self.$el.on('click', '.oe_mail_list_recipients .oe_more', self.on_show_recipients);
            self.$el.on('click', '.oe_mail_compose_textarea .oe_more_hidden', self.on_hide_recipients);
        },

        on_show_recipients: function(){
            var p=$(this).parent(); 
            p.find('.oe_more_hidden, .oe_hidden').show(); 
            p.find('.oe_more').hide(); 
        },

        on_hide_recipients: function(){
            var p=$(this).parent(); 
            p.find('.oe_more_hidden, .oe_hidden').hide(); 
            p.find('.oe_more').show(); 
        },

        /* get all child message/thread id linked
        */
        get_child_ids: function(){
            var res=[];
            _(this.get_childs()).each(function (val, key) { res.push(val.datasets.id); });
            return res;
        },

        /* get all child message/thread linked
        */
        get_childs: function(nb_thread_level){
            var res=[];
            if(arguments[1]) res.push(this);
            if(isNaN(nb_thread_level) || nb_thread_level>0){
                _(this.messages).each(function (val, key) {
                    if(val.thread){
                        res = res.concat( val.thread.get_childs((isNaN(nb_thread_level) ? null : nb_thread_level-1), true) ) 
                    }
                });
            }
            return res;
        },

        /** browse thread
         * @param {object}{int} option.id
         * @param {object}{string} option.model
         * @param {object}{boolean} option._go_thread_wall
         *      private for check the top thread
         * @param {object}{boolean} option.default_return_top_thread
         *      return the top thread (wall) if no thread found
         * @return thread object
         */
        browse_thread: function(options){
            // goto the wall thread for launch browse
            if(!options._go_thread_wall) {
                options._go_thread_wall = true;
                return this.options._parents[0].browse_thread(options);
            }

            if(this.datasets.id==options.id){
                return this;
            }

            if(options.id)
            for(var i in this.messages){
                if(this.messages[i].thread){
                    var res=this.messages[i].thread.browse_thread({'id':options.id, '_go_thread_wall':true});
                    if(res) return res;
                }
            }

            //if option default_return_top_thread, return the top if no found thread
            if(options.default_return_top_thread){
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
            if(this.options._parents[0].messages[0])
                return this.options._parents[0].messages[0].browse_message(options);
        },

        /* this function is launch when a user click on "Reply" button
        */
        on_compose_message: function(){
            this.ComposeMessage.on_compose_expandable();
        },

        /* display the no message on the thread
        */
        no_message: function(){
            $(session.web.qweb.render('mail.wall_no_message', {})).appendTo(this.$el);
        },

        /** Fetch messages
         * @param {Bool} initial_mode: initial mode: try to use message_data or
         *  message_ids, if nothing available perform a message_read; otherwise
         *  directly perform a message_read
         * @param {Array} replace_domain: added to this.domain
         * @param {Object} replace_context: added to this.context
         */
        message_fetch: function (initial_mode, replace_domain, replace_context, ids, callback) {
            var self = this;

            // initial mode: try to use message_data or message_ids
            if (initial_mode && this.options.message_data) {
                return this.create_message_object(this.options.message_data);
            }
            // domain and context: options + additional
            fetch_domain = replace_domain ? replace_domain : this.domain;
            fetch_context = replace_context ? replace_context : this.context;
            var message_loaded = [this.datasets.id||0].concat( self.options._parents[0].get_child_ids() );

            return this.ds_message.call('message_read', [ids, fetch_domain, message_loaded, fetch_context, this.context.default_parent_id || undefined]
                ).then(this.proxy('switch_new_message'));
        },

        /* create record object and linked him
         */
        create_message_object: function (data) {
            var self = this;

            if(data.type=='expandable'){
                var message = new mail.ThreadExpandable(self, data, {
                    'domain': data.domain,
                    'context': {
                        'default_model': data.model || self.context.default_model,
                        'default_res_id': data.res_id || self.context.default_res_id,
                        'default_parent_id': self.datasets.id },
                });
            } else {
                var message = new mail.ThreadMessage(self, _.extend(data, {'thread_level': self.datasets.thread_level}), {
                    'domain': data.domain,
                    'context': {
                        'default_model': data.model,
                        'default_res_id': data.res_id,
                        'default_parent_id': data.id },
                    'options': self.options
                });
            }

            // check if the message is already create
            for(var i in self.messages){
                if(self.messages[i].datasets.id == message.datasets.id){
                    self.messages[i].destroy();
                    self.messages[i] = self.insert_message(message);
                    return true;
                }
            }
            self.messages.push( self.insert_message(message) );
        },

        /** Displays a message or an expandable message  */
        insert_message: function (message) {
            var self=this;

            if(this.datasets.show_composeform){
                this.ComposeMessage.do_show_compact();
            }

            this.$('.oe_wall_no_message').remove();

            // insert on hierarchy display => insert in self child
            var thread_messages = self.messages;
            var thread = self;
            if( self.options.display_indented_thread < self.datasets.thread_level ) {
                var thread =  self.options._parents[self.options.display_indented_thread] || self.options._parents[0];
                var thread_messages = [];
                _(thread.get_childs()).each(function (val, key) { thread_messages.push(val.parent_message); });
            }

            // check older and newer message for insert
            var parent_newer = false;
            var parent_older = false;
            for(var i in thread_messages){
                if((thread_messages[i].datasets.id > message.datasets.id && message.datasets.id > 0) || 
                    thread_messages[i].datasets.id < 0){
                    if(!parent_newer || 
                        thread_messages[i].datasets.id < 0 || 
                        parent_newer.datasets.id >= thread_messages[i].datasets.id) {
                        parent_newer = thread_messages[i];
                    }
                } else if((thread_messages[i].datasets.id > 0 && thread_messages[i].datasets.id < message.datasets.id) || message.datasets.id < 0) {
                    if(!parent_older || 
                        parent_older.datasets.id < thread_messages[i].datasets.id) {
                        parent_older = thread_messages[i];
                    }
                }
            }

            var sort = self.datasets.thread_level;

            if(parent_older){
                if(sort){
                    message.insertAfter(parent_older.thread ? parent_older.thread.$el : parent_older.$el);
                } else {
                    message.insertBefore(parent_older.$el);
                }
            } else if(parent_newer){
                if(sort || parent_newer.datasets.id<0){
                    message.insertBefore(parent_newer.$el);
                } else {
                    message.insertAfter(parent_newer.thread ? parent_newer.thread.$el : parent_newer.$el);
                }
            } else {
                if(sort) {
                    message.prependTo(thread.$el);
                } else {
                    message.appendTo(thread.$el);
                }
            }

            return message
        },
        
        /*  Send the records to his parent thread */
        switch_new_message: function(records) {
            var self=this;
            _(records).each(function(record){
                self.browse_thread({
                    'id': record.parent_id, 
                    'default_return_top_thread':true
                }).create_message_object( record );
            });
        },
    });

    /** 
     * ------------------------------------------------------------
     * mail : root Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of messages with thread options. Its main
     * use is to receive a context and a domain, and to delegate the message
     * fetching and displaying to the Thread widget.
     */
    session.web.client_actions.add('mail.Widget', 'session.mail.Widget');
    mail.Widget = session.web.Widget.extend({
        template: 'mail.Widget',

        /**
         * @param {Object} parent parent
         * @param {Array} [domain]
         * @param {Object} [context] context of the thread. It should
         *   contain at least default_model, default_res_id. Please refer to
         *   the ComposeMessage widget for more information about it.
         * ... @param {Select} [typeof_thread=(mail|stared|archives|send|other)]
         *       options for destroy message when the user click on a button
         * @param {Object} [options]
         *...  @param {Number} [truncate_limit=250] number of character to
         *      display before having a "show more" link; note that the text
         *      will not be truncated if it does not have 110% of the parameter
         *...  @param {Boolean} [show_record_name] display the name and link for do action
         *...  @param {int} [show_reply_button] number thread level to display the reply button
         *...  @param {int} [show_read_unread_button] number thread level to display the read/unread button
         *...  @param {int} [display_indented_thread] number thread level to indented threads.
         *      other are on flat mode
         */
        init: function (parent, options) {
            this._super(parent);
            this.options = options || {};
            this.options.domain = options.domain || [];
            this.options.context = options.context || {};
            this.search_results = {'domain': [], 'context': {}, 'groupby': {}};
        },

        start: function (options) {
            this._super.apply(this, arguments);
            this.message_render();
            this.bind_events();
        },

        /**
         * Display the threads
          */
        message_render: function (search) {
            this.thread = new mail.Thread(this, {}, {
                'domain' : this.options.domain,
                'context' : this.options.context,
                'options': {
                    'typeof_thread': this.options.typeof_thread || 'inbox',
                    'display_indented_thread': this.options.display_indented_thread || 1,
                    'show_reply_button': this.options.show_reply_button || 1,
                    'show_read_unread_button': this.options.show_read_unread_button || 1,
                    'truncate_limit': this.options.truncate_limit || 250,
                    'show_record_name': this.options.show_record_name || false,
                    'show_header_compose': this.options.show_header_compose || false
                },
            });

            this.thread.appendTo( this.$el );
            this.thread.no_message();
            this.thread.message_fetch();
        },

        bind_events: function(){
            if(this.options.context['typeof_thread']!='other'){
                $(document).scroll( this.thread.on_scroll );
                $(window).resize( this.thread.on_scroll );
                window.setTimeout( this.thread.on_scroll, 500 );
            }
        }
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
        render_value: function() {
            if (! this.view.datarecord.id || session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$('oe_mail_thread').hide();
                return;
            }
            // update context
            _.extend(this.options.context, {
                default_res_id: this.view.datarecord.id,
                default_model: this.view.model,
                default_is_private: false });
            // update domain
            var domain = this.options.domain.concat([['model', '=', this.view.model], ['res_id', '=', this.view.datarecord.id]]);

            // TDE note: replace message_is_follower by a check in message_follower_ids, as message_is_follower is not used in views anymore
            var show_header_compose = this.view.is_action_enabled('edit') ||
                (this.getParent().fields.message_is_follower && this.getParent().fields.message_is_follower.get_value());

            if(this.root){
                this.root.destroy();
            }
            // create and render Thread widget
            this.root = new mail.Widget(this, {
                'domain' : domain,
                'context' : this.options.context,
                'typeof_thread': this.options.context['typeof_thread'] || 'other',
                'display_indented_thread': false,
                'show_reply_button': false,
                'show_read_unread_button': false,
                'show_header_compose': show_header_compose
                }
            );

            return this.root.appendTo( this.$('.oe_mail_wall_threads:first') );
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
            this.search_results = {'domain': [], 'context': {}, 'groupby': {}}
            this.ds_msg = new session.web.DataSetSearch(this, 'mail.message');
        },

        start: function () {
            this._super.apply(this, arguments);
            var searchview_ready = this.load_searchview({}, false);
            var thread_displayed = this.message_render();
            this.options.domain = this.options.domain.concat(this.search_results['domain']);
            this.bind_events();
            return $.when(searchview_ready, thread_displayed);
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
                self.searchview.on('search_data', self, self.do_searchview_search);
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
            }).then(function (results) {
                self.search_results['context'] = results.context;
                self.search_results['domain'] = results.domain;
                self.root.destroy();
                return self.message_render();
            });
        },


        /**
         * Display the threads
          */
        message_render: function (search) {
            var domain = this.options.domain.concat(this.search_results['domain']);
            var context = _.extend(this.options.context, search&&search.search_results['context'] ? search.search_results['context'] : {});
            this.root = new mail.Widget(this, {
                'domain' : domain,
                'context' : context,
                'typeof_thread': context['typeof_thread'] || 'other',
                'display_indented_thread': 2,
                'show_reply_button': 2,
                'show_read_unread_button': 3,
                'show_header_compose': true
                }
            );
            return this.root.appendTo( this.$('.oe_mail_wall_threads:first') );
        },

        bind_events: function(){
            var self=this;
            this.$("button.oe_write_full:first").click(function(){ self.root.thread.ComposeMessage.on_compose_fullmail(); });
            this.$("button.oe_write_onwall:first").click(function(){ self.root.thread.on_compose_message(); });
        }
    });


    /**
     * ------------------------------------------------------------
     * UserMenu
     * ------------------------------------------------------------
     * 
     * Add a link on the top user bar for write a full mail
     */
    session.web.ComposeMessageTopButton = session.web.Widget.extend({
        template:'mail.compose_message.button_top_bar',

        init: function (parent, options) {
            this._super.apply(this, options);
            this.options = this.options || {};
            this.options.domain = this.options.domain || [];
            this.options.context = {
                'default_model': false,
                'default_res_id': 0,
                'default_content_subtype': 'html',
            };
        },

        start: function(parent, params) {
            var self = this;
            this.$el.on('click', 'button', self.on_compose_message );
            this._super(parent, params);
        },

        on_compose_message: function(event){
            event.stopPropagation();
            var action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                action_from: 'mail.ThreadComposeMessage',
                views: [[false, 'form']],
                target: 'new',
                context: this.options.context,
            };
            session.client.action_manager.do_action(action);
        },

    });

    session.web.UserMenu = session.web.UserMenu.extend({
        start: function(parent, params) {
            var render = new session.web.ComposeMessageTopButton();
            render.insertAfter(this.$el);
            this._super(parent, params);
        }
    });

};
