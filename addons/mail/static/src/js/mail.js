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
            if (action.res_model == 'mail.compose.message') {

                /* hack for stop context propagation of wrong value
                 * delete this hack when a global method to clean context is create
                */
                for(var key in action.context){
                    if( key!='default_template_id' &&
                        key!='default_use_template' &&
                        key!='default_is_private' &&
                        key!='default_partner_ids' &&
                        key!='default_model' &&
                        key!='default_res_id' &&
                        key!='default_subtype' &&
                        key!='active_id' &&
                        key!='lang' &&
                        key!='bin_raw' &&
                        key!='tz' &&
                        key!='active_model' &&
                        key!='edi_web_url_view' &&
                        key!='active_ids')
                    action.context[key]=null;
                };
                /* end hack */

                $('.openerp .oe_mail_wall_threads .oe_mail_thread button.oe_mail_wall_button_fetch').click();

            }
            return this._super(action, on_close);
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
     */
    
    mail.ThreadComposeMessage = session.web.Widget.extend({
        template: 'mail.compose_message',

        /**
         * @param {Object} parent parent
         * @param {Object} [options]
         *      @param {Object} [context] context passed to the
         *          mail.compose.message DataSetSearch. Please refer to this model
         *          for more details about fields and default values.
         *      @param {Boolean} [show_attachment_delete] 
         */
        init: function (parent, options) {
            var self = this;
            this._super(parent);
            this.attachment_ids = [];

            this.context = options.context || {};

            this.id =           options.parameters.id;
            this.model =        options.parameters.model;
            this.res_id =       options.parameters.res_id;
            this.is_private =   options.parameters.is_private;
            this.partner_ids =  options.parameters.partner_ids;
            this.options={thread:{}};
            this.options.thread.show_header_compose =  options.parameters.options.thread.show_header_compose;
            this.options.thread.display_on_flat =  options.parameters.options.thread.display_on_flat;

            this.attachment_ids = [];
            this.options.thread.show_attachment_delete = true;
            this.options.thread.show_attachment_link = true;

            this.parent_thread= parent.messages!= undefined ? parent : false;

            this.ds_attachment = new session.web.DataSetSearch(this, 'ir.attachment');
            this.fileupload_id = _.uniqueId('oe_fileupload_temp');
            $(window).on(self.fileupload_id, self.on_attachment_loaded);
        },

        start: function(){
            this.display_attachments();
            this.bind_events();

            //load avatar img
            var user_avatar = mail.ChatterUtils.get_image(this.session, 'res.users', 'image_small', this.session.uid);
            this.$('img.oe_mail_icon').attr('src', user_avatar);
        },

        /* upload the file on the server, add in the attachments list and reload display
         */
        display_attachments: function(){
            var self = this;
            var render = $(session.web.qweb.render('mail.thread.message.attachments', {'widget': self}));
            if(!this.list_attachment){
                this.$('.oe_mail_compose_attachment_list').replaceWith( render );
            } else {
                this.list_attachment.replaceWith( render );
            }
            this.list_attachment = this.$("ul.oe_mail_msg_attachments");

            // event: delete an attachment
            this.$el.on('click', '.oe_mail_attachment_delete', self.on_attachment_delete);
        },
        on_attachment_change: function (event) {
            event.stopPropagation();
            var self = this;
            var $target = $(event.target);
            if ($target.val() !== '') {

                var filename = $target.val().replace(/.*[\\\/]/,'');

                // if the files exits for this answer, delete the file before upload
                var attachments=[];
                for(var i in this.attachment_ids){
                    if((this.attachment_ids[i].filename || this.attachment_ids[i].name) == filename){
                        if(this.attachment_ids[i].upload){
                            return false;
                        }
                        this.ds_attachment.unlink([this.attachment_ids[i].id]);
                    } else {
                        attachments.push(this.attachment_ids[i]);
                    }
                }
                this.attachment_ids = attachments;

                // submit file
                //session.web.blockUI();
                self.$('form.oe_form_binary_form').submit();

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
        
        on_attachment_loaded: function (event, result) {
            //session.web.unblockUI();
            for(var i in this.attachment_ids){
                if(this.attachment_ids[i].filename == result.filename && this.attachment_ids[i].upload){
                    this.attachment_ids[i]={
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
                for(var i in this.attachment_ids){
                    if(attachment_id!=this.attachment_ids[i].id){
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

        /* to avoid having unsorted file on the server.
            we will show the users files of the first message post
         */
        set_free_attachments: function(){
            var self=this;
            this.parent_thread.ds_message.call('user_free_attachment').then(function(attachments){
                this.attachment_ids=[];
                for(var i in attachments){
                    self.attachment_ids[i]={
                        'id': attachments[i].id,
                        'name': attachments[i].name,
                        'filename': attachments[i].filename,
                        'url': mail.ChatterUtils.get_attachment_url(self.session, attachments[i])
                    };
                }
                self.display_attachments();
            });
        },

        bind_events: function() {
            var self = this;

            // set the function called when attachments are added
            this.$el.on('change', 'input.oe_form_binary_file', self.on_attachment_change );
            this.$el.on('click', 'a.oe_cancel', self.on_cancel );
            this.$el.on('click', 'button.oe_post', function(){self.on_message_post()} );
            this.$el.on('click', 'button.oe_full', function(){self.on_compose_fullmail()} );
        },

        on_compose_fullmail: function(){
            var attachments=[];
            for(var i in this.attachment_ids){
                attachments.push(this.attachment_ids[i].id);
            }
            var partner_ids=[];
            for(var i in this.partner_ids){
                partner_ids.push(this.partner_ids[i][0]);
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
                    'default_res_model': this.context.default_res_model,
                    'default_res_id': this.context.default_res_id,
                    'default_content_subtype': 'html',
                    'default_is_private': this.is_private,
                    'default_parent_id': this.id,
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
            if(!this.options.thread.show_header_compose || !this.options.thread.display_on_flat){
                this.$el.hide();
            }
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
            for(var i in this.attachment_ids){
                if(this.attachment_ids[i].upload){
                    session.web.dialog($('<div>' + session.web.qweb.render('CrashManager.warning', {message: 'Please, wait while the file is uploading.'}) + '</div>'));
                    return false;
                }
                attachments.push(this.attachment_ids[i].id);
            }

            if(body.match(/\S+/)) {
                this.parent_thread.ds_thread.call('message_post_api', [
                        this.context.default_res_id, 
                        mail.ChatterUtils.get_text2html(body), 
                        false, 
                        'comment', 
                        false, 
                        this.context.default_parent_id, 
                        attachments]
                    ).then(function(records){
                        self.parent_thread.switch_new_message(records);
                        self.attachment_ids=[];
                        self.on_cancel();
                    });
                return true;
            }
        },
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

        init: function(parent, options) {
            this._super(parent);
            this.domain = options.domain || [];
            this.context = _.extend({
                default_model: 'mail.thread',
                default_res_id:  0,
                default_parent_id: false }, options.context || {});

            this.id =           options.parameters.id || -1;
            this.parent_id=     options.parameters.parent_id || false;
            this.nb_messages =  options.parameters.nb_messages || 0;
            this.type =         'expandable';

            // record options and data
            this.parent_thread= parent.messages!= undefined ? parent : options.options.thread._parents[0] ;
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
            this.$el.on('click', 'a.oe_mail_fetch_more', self.on_expandable);
        },

        /*The selected thread and all childs (messages/thread) became read
        * @param {object} mouse envent
        */
        on_expandable: function (event) {
            if(event)event.stopPropagation();
            var self = this;
            this.parent_thread.message_fetch(false, this.domain, this.context);
            this.$el.fadeOut(300, function(){
                self.destroy();
            });
            this.$('*').unbind();
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
         *          @param {Boolean} [show_dd_delete]
         *          @param {Boolean} [show_dd_hide]
         */
        init: function(parent, options) {
            this._super(parent);

            // record parameters
            var param =         options.parameters;
            for(var i in param){
                this[i] = param[i];
            }
            this.id =           param.id || -1;
            this.model =        param.model || false;
            this.parent_id=     param.parent_id || false;
            this.res_id =       param.res_id || false;
            this.type =         param.type || false;
            this.is_author =    param.is_author || false;
            this.is_private =   param.is_private || false;
            this.subject =      param.subject || false;
            this.name =         param.name || false;
            this.record_name =  param.record_name || false;
            this.body =         param.body || false;
            this.vote_user_ids =param.vote_user_ids || [];
            this.has_voted =    param.has_voted || false;
            this.has_stared =   param.has_stared || false;

            this.vote_user_ids = param.vote_user_ids || [];

            this.unread =       param.unread || false;
            this._date =        param.date;
            this.author_id =    param.author_id || [];
            this.attachment_ids = param.attachment_ids || [];

            // record domain and context
            this.domain = options.domain || [];
            this.context = _.extend({
                default_model: 'mail.thread',
                default_res_id:  0,
                default_parent_id: false }, options.context || {});

            // record options
            this.options={
                'thread' : options.options.thread,
                'message' : {
                    'message_ids':            options.options.message.message_ids || null,
                    'message_data':           options.options.message.message_data || null,
                    'show_record_name':       options.options.message.show_record_name != undefined ? options.options.message.show_record_name: true,
                    'show_dd_delete':         options.options.message.show_dd_delete || false,
                    'show_dd_hide':           options.options.message.show_dd_hide || false,
                    'truncate_limit':         options.options.message.truncate_limit || 250,
                }
            };

            // record options and data
            this.parent_thread= parent.messages!= undefined ? parent : options.options.thread._parents[0];
            this.thread = false;

            if( param.id > 0 ) {
                this.formating_data();
            }

            this.ds_notification = new session.web.DataSetSearch(this, 'mail.notification');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
        },

        formating_data: function(){

            //formating and add some fields for render
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
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;

            // event: click on 'Attachment(s)' in msg
            this.$('a.oe_mail_msg_view_attachments:first').on('click', function (event) {
                self.$('.oe_mail_msg_attachments:first').toggle();
            });
            // event: click on icone 'Read' in header
            this.$el.on('click', 'a.oe_read', this.on_message_read_unread);
            // event: click on icone 'UnRead' in header
            this.$el.on('click', 'a.oe_unread', this.on_message_read_unread);
            // event: click on 'Delete' in msg side menu
            this.$el.on('click', 'a.oe_mail_msg_delete', this.on_message_delete);

            // event: click on 'Reply' in msg
            this.$el.on('click', 'a.oe_reply', this.on_message_reply);
            // event: click on 'Vote' button
            this.$el.on('click', 'button.oe_mail_msg_vote', this.on_vote);
            // event: click on 'Star' button
            this.$el.on('click', 'button.oe_mail_starbox', this.on_star);
        },

        on_message_reply:function(event){
            event.stopPropagation();
            this.thread.on_compose_message();
            return false;
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
            var param = _.extend(self, {'parent_id': self.id});
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
                    'parameters': param
                }
            );
            /*insert thread in parent message*/
            self.thread.appendTo(self.$el.find('div.oe_thread_placeholder'));
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
            var ids = [this.id].concat( this.get_child_ids() );
            this.ds_message.unlink(ids);
            this.animated_destroy();
            return false;
        },

        /*The selected thread and all childs (messages/thread) became read
        * @param {object} mouse envent
        */
        on_message_read_unread: function (event) {
            event.stopPropagation();
            if($(event.srcElement).hasClass("oe_read")) this.animated_destroy({fadeTime:250});
            // if this message is read, all childs message display is read
            var ids = [this.id].concat( this.get_child_ids() );
            
            if($(event.srcElement).hasClass("oe_read")) {
                this.ds_notification.call('set_message_read', [ids,true]);
                this.$el.removeClass("oe_mail_unread").addClass("oe_mail_read");
            } else {
                this.ds_notification.call('set_message_read', [ids,false]);
                this.$el.removeClass("oe_mail_read").addClass("oe_mail_unread");
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
            // goto the wall thread for launch browse
            if(!options._go_thread_wall) {
                options._go_thread_wall = true;
                for(var i in this.options.thread._parents[0].messages){
                    var res=this.options.thread._parents[0].messages[i].browse_message(options);
                    if(res) return res;
                }
            }

            if(this.id==options.id)
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
            if(arguments[0]) res.push(this.id);
            if(this.thread){
                res = res.concat( this.thread.get_child_ids(true) );
            }
            return res;
        },

        on_vote: function (event) {
            event.stopPropagation();
            var self=this;
            return this.ds_message.call('vote_toggle', [[self.id]]).pipe(function(vote){

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
            return false;
        },

        // Render vote Display template.
        display_vote: function () {
            var self = this;
            var vote_element = session.web.qweb.render('mail.thread.message.vote', {'widget': self});
            self.$(".placeholder-mail-vote:first").empty();
            self.$(".placeholder-mail-vote:first").html(vote_element);
        },

        // Stared/unstared + Render star.
        on_star: function (event) {
            event.stopPropagation();
            var self=this;
            return this.ds_message.call('star_toggle', [[self.id]]).pipe(function(star){
                self.has_stared=star;
                if(self.has_stared){
                    self.$('button.oe_mail_starbox').addClass('oe_stared');
                } else {
                    self.$('button.oe_mail_starbox').removeClass('oe_stared');
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
         *          @param {Boolean} [use_composer] use the advanced composer, or
         *              the default basic textarea if not set
         *          @param {Number} [expandable_number=5] number message show
         *              for each click on "show more message"
         *          @param {Number} [expandable_default_number=5] number message show
         *              on begin before the first click on "show more message"
         *          @param {Boolean} [display_on_flat] display all thread
         *              on the wall thread level (no hierarchy)
         *          @param {Array} [parents] liked with the parents thread
         *              use with browse, fetch... [O]= top parent
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
                    'thread_level':         (options.options.thread.thread_level+1) || 0,
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
            // datasets and internal vars
            this.id=            param.id || false;
            this.model=         param.model || false;
            this.parent_id=     param.parent_id || false;
            this.is_private =   param.is_private || false;
            this.author_id =   param.author_id || false;
            this.partner_ids =  [];
            for(var i in param.partner_ids){
                if(param.partner_ids[i][0]!=(param.author_id ? param.author_id[0] : -1)){
                    this.partner_ids.push(param.partner_ids[i]);
                }
            }

            this.messages = [];

            this.ds_thread = new session.web.DataSetSearch(this, this.context.default_model || 'mail.thread');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
        },
        
        start: function() {
            // TDE TODO: check for deferred, not sure it is correct
            this._super.apply(this, arguments);

            this.list_ul=this.$('ul.oe_mail_thread_display:first');
            this.more_msg=this.$(">.oe_mail_msg_more_message:first");

            this.display_user_avatar();
            var display_done = compose_done = false;
            
            this.instantiate_ComposeMessage();

            this.bind_events();

            if(this.options.thread._parents[0]==this){
                this.on_first_thread();
            }

            return display_done && compose_done;
        },

        instantiate_ComposeMessage: function(){
            // add message composition form view
            this.ComposeMessage = new mail.ThreadComposeMessage(this,{
                'context': this.context,
                'parameters': this,
                'show_attachment_delete': true,
            });
            this.ComposeMessage.appendTo(this.$(".oe_mail_thread_action:first"));
        },

        /* this method is runing for first parent thread
        */
        on_first_thread: function(){
            var self=this;
            // fetch and display message, using message_ids if set
            this.message_fetch();

            $(document).scroll( self.on_scroll );
            window.setTimeout( self.on_scroll, 500 );

            $(session.web.qweb.render('mail.wall_no_message', {})).appendTo(this.$('ul.oe_mail_thread_display'));

            if(this.options.thread.show_header_compose){
                this.ComposeMessage.$el.show();
                //this.ComposeMessage.set_free_attachments();
            }

            var button_fetch = $('<button style="display:none;" class="oe_mail_wall_button_fetch"/>').click(function(event){
                if(event)event.stopPropagation();
                self.message_fetch();
            });
            this.$el.prepend(button_fetch);
            this.$el.addClass("oe_mail_wall_first_thread");
        },

        /* When the expandable object is visible on screen (with scrolling)
         * then the on_expandable function is launch
        */
        on_scroll: function(event){
            if(event)event.stopPropagation();
            var last=this.messages[0];
            if(last && last.type=="expandable"){
                var pos = last.$el.position();
                if(pos.top){
                    /* bottom of the screen */
                    var bottom = $(window).scrollTop()+$(window).height()+100;
                    if(bottom - pos.top > 0){
                        last.on_expandable();
                    }
                }
            }
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            self.$('.oe_mail_compose_textarea .oe_more').click(function () { var p=$(this).parent(); p.find('.oe_more_hidden, .oe_hidden').show(); p.find('.oe_more').hide(); });
            self.$('.oe_mail_compose_textarea .oe_more_hidden').click(function () { var p=$(this).parent(); p.find('.oe_more_hidden, .oe_hidden').hide(); p.find('.oe_more').show(); });
        },

        /* get all child message/thread id linked
        */
        get_child_ids: function(){
            var res=[];
            for(var i in this.messages){
                if(this.messages[i].thread){
                    res = res.concat( this.messages[i].get_child_ids(true) );
                }
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
                return this.options.thread._parents[0].browse_thread(options);
            }

            if(this.id==options.id){
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
            if(this.options.thread._parents[0].messages[0])
                return this.options.thread._parents[0].messages[0].browse_message(options);
        },

        /* this function is launch when a user click on "Reply" button
        */
        on_compose_message: function(){
            this.ComposeMessage.$el.toggle();
            return false;
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
            if (initial_mode && this.options.thread.message_data) {
                return this.create_message_object(this.options.message_data);
            }
            // domain and context: options + additional
            fetch_domain = replace_domain ? replace_domain : this.domain;
            fetch_context = replace_context ? replace_context : this.context;
            fetch_context.message_loaded= [this.id||0].concat( self.options.thread._parents[0].get_child_ids() );

            return this.ds_message.call('message_read', [ids, fetch_domain, fetch_context, 0, this.context.default_parent_id || undefined]
                ).then(function (records) { self.switch_new_message(records); });
        },

        /* create record object and linked him
         */
        create_message_object: function (message) {
            var self = this;

            // check if the message is already create
            for(var i in this.messages){
                if(this.messages[i].id==message.id){
                    this.messages[i].destroy();
                    this.messages[i]=self.insert_message(message);
                    return true;
                }
            }

            self.messages.push( self.insert_message(message) );
            
        },

        /** Displays a message or an expandable message  */
        insert_message: function (record) {
            var self=this;

            this.$("li.oe_wall_no_message").remove();

            if(record.type=='expandable'){
                var message = new mail.ThreadExpandable(self, {
                    'domain': record.domain,
                    'context': {
                        'default_model':        record.model,
                        'default_res_id':       record.res_id,
                        'default_parent_id':    record.id },
                    'parameters': record
                });
            } else {
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
            }

            var thread_messages = (self.options.thread.display_on_flat && self.options.thread.thread_level ? self.options.thread._parents[0].messages : []).concat(self.messages);
            var thread = (self.options.thread.display_on_flat && self.options.thread.thread_level ? self.options.thread._parents[0] : self);

            // check older and newer message for insert
            var parent_newer = false;
            var parent_older = false;
            if ( message.id > 0 ){
                for(var i in thread_messages){
                    if(thread_messages[i].id > message.id){
                        if(!parent_newer || parent_newer.id>=thread_messages[i].id)
                            parent_newer = thread_messages[i];
                    } else if(thread_messages[i].id>0 && thread_messages[i].id < message.id) {
                        if(!parent_older || parent_older.id<thread_messages[i].id)
                            parent_older = thread_messages[i];
                    }
                }
            }

            var sort = self.options.thread.thread_level==0 || (self.options.thread.display_on_flat && self.options.thread.thread_level<=1);

            if(parent_older){
                if(sort){
                    message.insertBefore(parent_older.$el);
                } else {
                    message.insertAfter(parent_older.$el);
                }
            }
            else if(parent_newer){
                if(sort){
                    message.insertAfter(parent_newer.$el);
                } else {
                    message.insertBefore(parent_newer.$el);
                }
            }
            else {
                if(sort && message.id > 0){
                    message.prependTo(thread.list_ul);
                } else {
                    message.appendTo(thread.list_ul);
                }
            }

            return message
        },

        display_user_avatar: function () {
            var avatar = mail.ChatterUtils.get_image(this.session, 'res.users', 'image_small', this.session.uid);
            return this.$('img.oe_mail_icon').attr('src', avatar);
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

        /**
         * Reinitialize the widget field and Display the threads
         * @param {Object} new_context: context of the refresh
          */
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
                default_model: this.view.model,
                default_is_private: false });
            // update domain
            var domain = this.options.domain.concat([['model', '=', this.view.model], ['res_id', '=', this.view.datarecord.id]]);
            // create and render Thread widget
            var show_header_compose = this.view.is_action_enabled('edit') ||
                (this.getParent().fields.message_is_follower && this.getParent().fields.message_is_follower.get_value());

            if(this.thread){
                this.thread.destroy();
            }
            this.thread = new mail.Thread(self, {
                    'domain': domain,
                    'context': this.options.context,
                    'options':{
                        'thread':{
                            'show_header_compose': show_header_compose,
                            'use_composer': show_header_compose,
                            'display_on_flat':true
                        },
                        'message':{
                            'show_dd_delete': true
                        }
                    },
                    'parameters': {},
                }
            );
            return this.thread.appendTo( this.$('.oe_mail_wall_threads:first') );
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
                self.thread.destroy();
                return self.message_render();
            });
        },


        /**
         * Display the threads
          */
        message_render: function (search) {
            this.thread = new mail.Thread(this, {
                    'domain' : this.options.domain.concat(this.search_results['domain']),
                    'context' : _.extend(this.options.context, search&&search.search_results['context'] ? search.search_results['context'] : {}),
                    'options': {
                        'thread' :{
                            'use_composer': true,
                            'show_header_compose': false,
                        },
                        'message': {
                            'show_reply': true,
                            'show_dd_hide': true,
                            'show_dd_delete': true,
                        },
                    },
                    'parameters': {},
                }
            );
            return this.thread.appendTo( this.$('.oe_mail_wall_threads:first') );

        },

        bind_events: function(){
            var self=this;
            this.$("button.oe_write_full:first").click(function(){ self.thread.ComposeMessage.on_compose_fullmail(); });
            this.$("button.oe_write_onwall:first").click(function(){ self.thread.ComposeMessage.$el.toggle(); });
        }
    });


    /**
     * ------------------------------------------------------------
     * UserMenu
     * ------------------------------------------------------------
     * 
     * add a link on the top user bar for write a full mail
     */
    session.web.ComposeMessageTopButton = session.web.Widget.extend({

        template:'mail.compose_message.button_top_bar',

        init: function (parent, options) {
            this._super.apply(this, options);
            this.options = this.options || {};
            this.options.domain = this.options.domain || [];
            this.options.context = {
                'default_res_id': 0,
                'default_model': 'mail.thread',
                'default_is_private': true, 
                'default_res_model': false,
                'default_res_id': 0,
                'default_content_subtype': 'html',
                'default_is_private': true,
                'default_parent_id': 0
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
