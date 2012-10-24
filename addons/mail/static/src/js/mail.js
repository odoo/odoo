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
                    'default_res_id', 'default_content_subtype', 'active_id', 'lang',
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

        /**
         *Get an image in /web/binary/image?... */
        get_image: function(session, model, field, id) {
            return session.prefix + '/web/binary/image?session_id=' + session.session_id + '&model=' + model + '&field=' + field + '&id=' + (id || '');
        },

        /**
         *Get the url of an attachment {'id': id} */
        get_attachment_url: function (session, attachment) {
            return session.origin + '/web/binary/saveas?session_id=' + session.session_id + '&model=ir.attachment&field=datas&filename_field=datas_fname&id=' + attachment['id'];
        },

        /**
         *Replaces some expressions
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
        },

        /**
         * return the complete domain with "&"
         */
        expend_domain: function (domain) {
            var new_domain = [];
            var nb_and = -1;
            
            for ( var k = domain.length-1; k >= 0 ; k-- ) {
                if ( typeof domain[k] != 'array' && typeof domain[k] != 'object' ) {
                    nb_and -= 2;
                    continue;
                }
                nb_and += 1;
            }

            for (var k = 0; k < nb_and ; k++){
                domain.unshift('&');
            }

            return domain;
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
            this.options = options.options;

            this.show_compact_message = this.options.show_compact_message || false;

            // data of this compose message
            this.attachment_ids = [];
            this.id = datasets.id;
            this.model = datasets.model;
            this.res_model = datasets.res_model;
            this.is_private = datasets.is_private || false;
            this.partner_ids = datasets.partner_ids || [];
            this.avatar = mail.ChatterUtils.get_image(this.session, 'res.users', 'image_small', this.session.uid);
            this.parent_thread= parent.messages!= undefined ? parent : false;

            this.ds_attachment = new session.web.DataSetSearch(this, 'ir.attachment');
            this.show_delete_attachment = true;

            this.fileupload_id = _.uniqueId('oe_fileupload_temp');
            $(window).on(self.fileupload_id, self.on_attachment_loaded);

            this.$render_expandable = false;
            this.$render_compact = false;
        },

        start: function(){
            this.$render_compact = this.$el;

            if( this.options.show_compact_message ) {
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
                this.$render_expandable.find('.oe_msg_attachment_list').replaceWith( render );
            } else {
                this.list_attachment.replaceWith( render );
            }
            this.list_attachment = this.$render_expandable.find(".oe_msg_attachments");

            // event: delete an attachment
            this.$render_expandable.on('click', '.oe_mail_attachment_delete', self.on_attachment_delete);
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
                this.$render_expandable.find('form.oe_form_binary_form').submit();

                this.$render_expandable.find(".oe_attachment_file").hide();

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
        
        /* when the file is uploaded 
        */
        on_attachment_loaded: function (event, result) {
            for(var i in this.attachment_ids){
                if(this.attachment_ids[i].filename == result.filename && this.attachment_ids[i].upload) {
                    this.attachment_ids[i]={
                        'id': result.id,
                        'name': result.name,
                        'filename': result.filename,
                        'url': mail.ChatterUtils.get_attachment_url(this.session, result)
                    };
                }
            }
            this.display_attachments();

            var $input = this.$render_expandable.find('input.oe_form_binary_file');
            $input.after($input.clone(true)).remove();
            this.$render_expandable.find(".oe_attachment_file").show();
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

        bind_events: function() {
            var self = this;

            this.$render_compact.find('textarea').unbind().on('focus', self.on_compose_expandable);

            if(this.$render_expandable){
                // set the function called when attachments are added
                this.$render_expandable.on('change', 'input.oe_form_binary_file', self.on_attachment_change );

                this.$render_expandable.on('click', '.oe_cancel', self.on_cancel );
                this.$render_expandable.on('click', '.oe_post', function(){self.on_message_post()} );
                this.$render_expandable.on('click', '.oe_full', function(){self.on_compose_fullmail()} );

                // auto close
                this.$render_expandable.on('blur', 'textarea', this.on_compose_expandable);

                /* stack for don't close the compose form if the user click on a button */
                this.$render_expandable.on('focus, mouseup', 'textarea', function () { self.stay_open = false; });
                this.$render_expandable.on('mousedown', function () { self.stay_open = true; });
            }
        },

        on_compose_fullmail: function(){
            /* TDE note: I think this is not necessary, because
             * 1/ post on a document: followers added server-side in _notify
             * 2/ reply to a message: mail.compose.message should add the previous partners
             */
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
                    'default_model': this.context.default_model,
                    'default_res_model': this.context.default_model,
                    'default_res_id': this.context.default_res_id,
                    'default_content_subtype': 'html',
                    'default_parent_id': this.id,
                    'default_body': mail.ChatterUtils.get_text2html(this.$render_expandable ? (this.$render_expandable.find('textarea').val() || '') : ''),
                    'default_attachment_ids': this.attachment_ids,
                    'default_partner_ids': partner_ids
                },
            };
            this.do_action(action);

            if(this.$render_expandable) {
                this.on_cancel();
            }
        },

        on_cancel: function(event){
            if(event) event.stopPropagation();
            this.$render_expandable.find('textarea').val("");
            this.$render_expandable.find('input[data-id]').remove();

            this.attachment_ids=[];
            this.display_attachments();

            this.stay_open = false;
            this.on_compose_expandable();
        },

        /*post a message and fetch the message*/
        on_message_post: function (body) {
            var self = this;

            if (! body) {
                var comment_node =  this.$render_expandable.find('textarea');
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
                //session.web.blockUI();
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
                        self.on_cancel();
                        //session.web.unblockUI();
                    });
                return true;
            }
        },

        /* create the compose on expandable form
        */
        instantiate_expandable: function() {
            if(!this.$render_expandable) {
                this.$render_expandable = $(session.web.qweb.render('mail.compose_message', {'widget': this}));
                this.$render_expandable.hide();

                this.$render_expandable.insertAfter( this.$render_compact );
                this.display_attachments();

                this.bind_events();
            }
        },

        /* convert the compact mode into the compose message
        */
        on_compose_expandable: function(event){
            if(event) event.stopPropagation();

            var self = this;

            this.instantiate_expandable();

            if(this.$render_expandable.is(':hidden')){

                this.$render_expandable.show();
                this.$render_compact.hide();
                this.$render_expandable.find('textarea').focus();

            } else if(!this.stay_open){

                // do not close the box if there are some text
                if(!this.$render_expandable.find('textarea').val().match(/\S+/)){
                    this.$render_expandable.hide();
                    if(this.options.show_compact_message && this.show_compact_message) {
                        this.$render_compact.show();
                    } else {
                        this.$render_compact.hide();
                    }
                }

            }
            return true;
        },

        do_hide_compact: function() {
            this.$render_compact.hide();
            this.show_compact_message = false;
        },

        do_show_compact: function() {
            if(this.options.show_compact_message && (!this.$render_expandable || this.$render_expandable.is(':hidden'))) {
                this.$render_compact.show();
            }
            this.show_compact_message = true;
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

            // data of this expandable message
            this.id = datasets.id || -1,
            this.model = datasets.model || false,
            this.ancestor_id = datasets.ancestor_id || false,
            this.nb_messages = datasets.nb_messages || 0,
            this.thread_level = datasets.thread_level || 0,
            this.type = 'expandable',
            this.max_limit = this.id < 0 || false,
            this.flag_used = false,
            this.parent_thread= parent.messages!= undefined ? parent : options.options._parents[0];
        },

        
        start: function() {
            this._super.apply(this, arguments);
            this.bind_events();
        },

        reinit: function () {
            var $render = $(session.web.qweb.render('mail.thread.expandable', {'widget': this}));
            this.$el.replaceWith( $render );
            this.$el = $render;
            this.bind_events();
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            this.$el.on('click', 'a.oe_msg_fetch_more', this.on_expandable);
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
            if(this.flag_used) {
                return false
            }
            this.flag_used = true;

            this.animated_destroy({'fadeTime':300});
            this.parent_thread.message_fetch(this.domain, this.context);
            return false;
        },

        /**
         * call on_message_delete on his parent thread
        */
        destroy: function() {

            this._super();
            this.parent_thread.on_message_detroy(this);

        }
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
     * - - sub message (ancestor_id = root message)
     * - - - sub thread
     * - - - - sub sub message (parent id = sub thread)
     * - - sub message (ancestor_id = root message)
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
         *          @param {Number} [truncate_limit=250] number of character to
         *              display before having a "show more" link; note that the text
         *              will not be truncated if it does not have 110% of the parameter
         *          @param {Boolean} [show_record_name]
         *...  @param {int} [show_reply_button] number thread level to display the reply button
         *...  @param {int} [show_read_unread_button] number thread level to display the read/unread button
         */
        init: function(parent, datasets, options) {
            this._super(parent);

            // data of this message
            this.id = datasets.id ||  -1,
            this.model = datasets.model ||  false,
            this.ancestor_id = datasets.ancestor_id ||  false,
            this.res_id = datasets.res_id ||  false,
            this.type = datasets.type ||  false,
            this.is_author = datasets.is_author ||  false,
            this.is_private = datasets.is_private ||  false,
            this.subject = datasets.subject ||  false,
            this.name = datasets.name ||  false,
            this.record_name = datasets.record_name ||  false,
            this.body = datasets.body ||  false,
            this.vote_nb = datasets.vote_nb || 0,
            this.has_voted = datasets.has_voted ||  false,
            this.is_favorite = datasets.is_favorite ||  false,
            this.thread_level = datasets.thread_level ||  0,
            this.to_read = datasets.to_read || false,
            this.author_id = datasets.author_id ||  [],
            this.attachment_ids = datasets.attachment_ids ||  [],
            this._date = datasets.date;

            // record domain and context
            this.domain = options.domain || [];
            this.context = _.extend({
                default_model: 'mail.thread',
                default_res_id: 0,
                default_parent_id: false }, options.context || {});

            // record options
            this.options = options.options;

            this.show_reply_button = this.options.show_compose_message && this.options.show_reply_button > this.thread_level;
            this.show_read_unread_button = this.options.show_read_unread_button > this.thread_level;

            // record options and data
            this.parent_thread= parent.messages!= undefined ? parent : options.options._parents[0];
            this.thread = false;

            if( this.id > 0 ) {
                this.formating_data();
            }

            this.ds_notification = new session.web.DataSetSearch(this, 'mail.notification');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
            this.ds_follow = new session.web.DataSetSearch(this, 'mail.followers');
        },

        /**
         *Convert date, timerelative and avatar in displayable data.
        */
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

                if((attach.filename || attach.name).match(/[.](jpg|jpg|gif|png|tif|svg)$/i)) {
                    attach.is_image = true;

                }
                if((attach.filename || attach.name).match(/[.](pdf|doc|docx|xls|xlsx|ppt|pptx|psd|tiff|dxf|svg)$/i)) {
                    attach.is_document = true;
                    attach.url_escape = encodeURIComponent(attach.url);
                }
            }

        },
        
        start: function() {
            this._super.apply(this, arguments);
            this.expender();
            this.$el.hide().fadeIn(750);
            this.resize_img();
            this.bind_events();
            this.create_thread();
        },

        resize_img: function() {
            this.$("img").load(function() {
                var h = $(this).height();
                var w = $(this).width();
                if( h > 100 || w >100 ) {
                    var ratio = 100 / (h > w ? h : w);
                    $(this).attr("width", parseInt( w*ratio )).attr("height", parseInt( h*ratio ));
                }
            });
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
            this.$el.on('click', '.oe_read', this.on_message_read_unread);
            // event: click on icone 'UnRead' in header
            this.$el.on('click', '.oe_unread', this.on_message_read_unread);
            // event: click on 'Delete' in msg side menu
            this.$el.on('click', '.oe_msg_delete', this.on_message_delete);

            // event: click on 'Reply' in msg
            this.$el.on('click', '.oe_reply', this.on_message_reply);
            // event: click on 'Vote' button
            this.$el.on('click', '.oe_msg_vote', this.on_vote);
            // event: click on 'starred/favorite' button
            this.$el.on('click', '.oe_star', this.on_star);
        },

        /**
         * call the on_compose_message on the thread of this message.
         */
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

        /**
         * instantiate the thread object of this message.
         * Each message have only one thread.
         */
        create_thread: function(){
            if(this.thread){
                return false;
            }
            /*create thread*/
            this.thread = new mail.Thread(this, this, {
                    'domain': this.domain,
                    'context':{
                        'default_model': this.model,
                        'default_res_id': this.res_id,
                        'default_parent_id': this.id
                    },
                    'options': this.options
                }
            );
            /*insert thread in parent message*/
            this.thread.insertAfter(this.$el);
        },
        
        /**
         * Fade out the message and his child thread.
         * Then this object is destroyed.
         */
        animated_destroy: function(options) {
            var self=this;
            //graphic effects  
            if(options && options.fadeTime) {
                self.$el.fadeOut(options.fadeTime, function(){
                    self.parent_thread.message_to_expandable(self);
                });
                self.thread.$el.fadeOut(options.fadeTime);
            } else {
                self.parent_thread.message_to_expandable(self);
            }
        },

        /**
         * Wait a confirmation for delete the message on the DB.
         * Make an animate destroy
         */
        on_message_delete: function (event) {
            event.stopPropagation();
            if (! confirm(_t("Do you really want to delete this message?"))) { return false; }
            
            this.animated_destroy({fadeTime:250});
            // delete this message and his childs
            var ids = [this.id].concat( this.get_child_ids() );
            this.ds_message.unlink(ids);
            return false;
        },

        /*The selected thread and all childs (messages/thread) became read
        * @param {object} mouse envent
        */
        on_message_read_unread: function (event) {
            event.stopPropagation();
            var self=this;

            if( (this.to_read && this.options.typeof_thread == 'inbox') ||
                (!this.to_read && this.options.typeof_thread == 'archives')) {
                this.animated_destroy({fadeTime:250});
            }

            // if this message is read, all childs message display is read
            this.ds_notification.call('set_message_read', [ [this.id].concat( this.get_child_ids() ) , this.to_read, this.context]).pipe(function(){
                self.$el.removeClass(self.to_read ? 'oe_msg_unread':'oe_msg_read').addClass(self.to_read ? 'oe_msg_read':'oe_msg_unread');
                self.to_read = !self.to_read;
            });
            return false;
        },

        /**
         * search a message in all thread and child thread.
         * This method return an object message.
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

        /* get all child message id linked.
         * @return array of id
        */
        get_child_ids: function(){
            var res=[]
            if(arguments[0]) res.push(this.id);
            if(this.thread){
                res = res.concat( this.thread.get_child_ids(true) );
            }
            return res;
        },

        /**
         * add or remove a vote for a message and display the result
        */
        on_vote: function (event) {
            event.stopPropagation();
            var self=this;
            return this.ds_message.call('vote_toggle', [[self.id]]).pipe(function(vote){
                self.has_voted = vote;
                self.vote_nb += self.has_voted ? 1 : -1;
                self.display_vote();
            });
            return false;
        },

        /**
         * Display the render of this message's vote
        */
        display_vote: function () {
            var self = this;
            var vote_element = session.web.qweb.render('mail.thread.message.vote', {'widget': self});
            self.$(".oe_msg_vote:first").remove();
            self.$(".oe_mail_vote_count:first").replaceWith(vote_element);
        },

        /**
         * add or remove a favorite (or starred) for a message and change class on the DOM
        */
        on_star: function (event) {
            event.stopPropagation();
            var self=this;
            var button = self.$('.oe_star:first');
            return this.ds_message.call('favorite_toggle', [[self.id]]).pipe(function(star){
                self.is_favorite=star;
                if(self.is_favorite){
                    button.addClass('oe_starred');
                } else {
                    button.removeClass('oe_starred');
                    if( self.options.typeof_thread == 'stared' ) {
                        self.animated_destroy({fadeTime:250});
                    }
                }
            });
            return false;
        },

        /**
         * call on_message_delete on his parent thread
        */
        destroy: function() {

            this._super();
            this.parent_thread.on_message_detroy(this);

        }

    });

    /**
         * ------------------------------------------------------------
     * Thread Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of a thread of messages. The
     * thread view:
     * - root thread
     * - - sub message (ancestor_id = root message)
     * - - - sub thread
     * - - - - sub sub message (parent id = sub thread)
     * - - sub message (ancestor_id = root message)
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

            this.options = options.options;
            this.options._parents = (options.options._parents != undefined ? options.options._parents : []).concat( [this] );

            // record options and data
            this.parent_message= parent.thread!= undefined ? parent : false ;

            // data of this thread
            this.id =  datasets.id || false,
            this.model =  datasets.model || false,
            this.ancestor_id =  datasets.ancestor_id || false,
            this.is_private =  datasets.is_private || false,
            this.author_id =  datasets.author_id || false,
            this.thread_level =  (datasets.thread_level+1) || 0,
            this.partner_ids =  _.filter(datasets.partner_ids, function(partner){ return partner[0]!=datasets.author_id[0]; } ) 
            this.messages = [];
            this.show_compose_message = this.options.show_compose_message && (this.options.show_reply_button > this.thread_level || !this.thread_level);

            // object compose message
            this.ComposeMessage = false;

            this.ds_thread = new session.web.DataSetSearch(this, this.context.default_model || 'mail.thread');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
        },
        
        start: function() {
            this._super.apply(this, arguments);
            if(this.show_compose_message){
                this.instantiate_ComposeMessage();
            }
            this.bind_events();
        },

        /* instantiate the compose message object and insert this on the DOM.
        * The compose message is display in compact form.
        */
        instantiate_ComposeMessage: function(){
            // add message composition form view
            this.ComposeMessage = new mail.ThreadComposeMessage(this, this, {
                'context': this.context,
                'options': this.options,
            });

            if(this.thread_level){
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
            this.$('.oe_msg_expandable:last');

            var message = this.messages[this.messages.length-1];
            if(message && message.type=="expandable" && message.max_limit) {
                var pos = message.$el.position();
                if(pos.top){
                    /* bottom of the screen */
                    var bottom = $(window).scrollTop()+$(window).height()+200;
                    if(bottom > pos.top){
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

        /**
         *show all the partner list of this parent message
        */
        on_show_recipients: function(){
            var p=$(this).parent(); 
            p.find('.oe_more_hidden, .oe_hidden').show(); 
            p.find('.oe_more').hide(); 
        },

        /**
         *hide a part of the partner list of this parent message
        */
        on_hide_recipients: function(){
            var p=$(this).parent(); 
            p.find('.oe_more_hidden, .oe_hidden').hide(); 
            p.find('.oe_more').show(); 
        },

        /* get all child message/thread id linked.
         * @return array of id
        */
        get_child_ids: function(){
            var res=[];
            _(this.get_childs()).each(function (val, key) { res.push(val.id); });
            return res;
        },

        /* get all child message/thread linked.
         * @param {int} nb_thread_level, number of traversed thread level for this search
         * @return array of thread object
        */
        get_childs: function(nb_thread_level){
            var res=[];
            if(arguments[1]) res.push(this);
            if(isNaN(nb_thread_level) || nb_thread_level>0){
                _(this.messages).each(function (val, key) {
                    if(val.thread) {
                        res = res.concat( val.thread.get_childs((isNaN(nb_thread_level) ? undefined : nb_thread_level-1), true) );
                    }
                });
            }
            return res;
        },

        /**
         *search a thread in all thread and child thread.
         * This method return an object thread.
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

            if(this.id==options.id){
                return this;
            }

            if(options.id){
                for(var i in this.messages){
                    if(this.messages[i].thread){
                        var res=this.messages[i].thread.browse_thread({'id':options.id, '_go_thread_wall':true});
                        if(res) return res;
                    }
                }
            }

            //if option default_return_top_thread, return the top if no found thread
            if(options.default_return_top_thread){
                return this;
            }

            return false;
        },

        /**
         *search a message in all thread and child thread.
         * This method return an object message.
         * @param {object}{int} option.id
         * @param {object}{string} option.model
         * @param {object}{boolean} option._go_thread_wall
         *      private for check the top thread
         * @return message object
         */
        browse_message: function(options){
            if(this.options._parents[0].messages[0])
                return this.options._parents[0].messages[0].browse_message(options);
        },

        /**
         *If ComposeMessage doesn't exist, instantiate the compose message.
        * Call the on_compose_expandable method to allow the user to write his message.
        * (Is call when a user click on "Reply" button)
        */
        on_compose_message: function(){
            if(!this.ComposeMessage){
                this.instantiate_ComposeMessage();
                this.ComposeMessage.do_hide_compact();
            }

            this.ComposeMessage.on_compose_expandable();
        },

        /**
         *display the message "there are no message" on the thread
        */
        no_message: function(){
            $(session.web.qweb.render('mail.wall_no_message', {})).appendTo(this.$el);
        },

        /**
         *make a request to read the message (calling RPC to "message_read").
         * The result of this method is send to the switch message for sending ach message to
         * his parented object thread.
         * @param {Array} replace_domain: added to this.domain
         * @param {Object} replace_context: added to this.context
         * @param {Array} ids read (if the are some ids, the method don't use the domain)
         */
        message_fetch: function (replace_domain, replace_context, ids) {
            var self = this;

            // domain and context: options + additional
            fetch_domain = replace_domain ? replace_domain : this.domain;
            fetch_context = replace_context ? replace_context : this.context;
            var message_loaded_ids = this.id ? [this.id].concat( self.get_child_ids() ) : self.get_child_ids();

            // CHM note : option for sending in flat mode by server
            var nb_indented_thread = this.options.display_indented_thread > this.thread_level ? this.options.display_indented_thread - this.thread_level : 0;

            return this.ds_message.call('message_read', [ids, fetch_domain, message_loaded_ids, nb_indented_thread, fetch_context, this.context.default_parent_id || undefined]
                ).then(this.proxy('switch_new_message'));
        },

        /**
         *create the message object and attached on this thread.
         * When the message object is create, this method call insert_message for,
         * displaying this message on the DOM.
         * @param : {object} data from calling RPC to "message_read"
         */
        create_message_object: function (data) {
            var self = this;

            if(data.type=='expandable'){
                var message = new mail.ThreadExpandable(self, data, {
                    'domain': data.domain,
                    'context': {
                        'default_model': data.model || self.context.default_model,
                        'default_res_id': data.res_id || self.context.default_res_id,
                        'default_parent_id': self.id },
                });
            } else {
                var message = new mail.ThreadMessage(self, _.extend(data, {'thread_level': data.thread_level ? data.thread_level : self.thread_level}), {
                    'domain': data.domain,
                    'context': {
                        'default_model': data.model,
                        'default_res_id': data.res_id,
                        'default_parent_id': data.id },
                    'options': _.extend(self.options, data.options)
                });
            }

            // insert the message on dom
            self.insert_message( message );

            // check if the message is already create
            for(var i in self.messages){
                if(self.messages[i] && self.messages[i].id == message.id){
                    self.messages[i].destroy();
                }
            }
            self.messages.push( message );
        },

        /**
         *insert the message on the DOM.
         * All message (and expandable message) are sorted. The method get the
         * older and newer message to insert the message (before, after).
         * If there are no older or newer, the message is prepend or append to
         * the thread (parent object or on root thread for flat view).
         * The sort is define by the thread_level (O for newer on top).
         * @param : {object} ThreadMessage object
         */
        insert_message: function (message) {
            var self=this;

            if(this.show_compose_message /*&& 
                this.options.display_indented_thread >= self.thread_level*/){
                this.ComposeMessage.do_show_compact();
            }

            this.$('.oe_wall_no_message').remove();

            // check older and newer message for insertion
            var parent_newer = false;
            var parent_older = false;
            if(message.id > 0){
                for(var i in self.messages){
                    if(self.messages[i].id > message.id){
                        if(!parent_newer || parent_newer.id > self.messages[i].id) {
                            parent_newer = self.messages[i];
                        }
                    } else if(self.messages[i].id > 0 && self.messages[i].id < message.id) {
                        if(!parent_older || parent_older.id < self.messages[i].id) {
                            parent_older = self.messages[i];
                        }
                    }
                }
            }

            var sort = (!!self.thread_level || message.id<0);


            if (sort) {
                if (parent_older) {

                    //warning : insert after the thread of the message !
                    message.insertAfter(parent_older.thread ? parent_older.thread.$el : parent_older.$el);

                } else if(parent_newer) {

                    message.insertBefore(parent_newer.$el);

                } else if(message.id < 0) {

                    message.appendTo(self.$el);

                } else {

                    message.prependTo(self.$el);
                }
            } else {
                if (parent_older) {

                    message.insertBefore(parent_older.$el);

                } else if(parent_newer) {

                    //warning : insert after the thread of the message !
                    message.insertAfter(parent_newer.thread ? parent_newer.thread.$el : parent_newer.$el);

                } else if(message.id < 0) {

                    message.prependTo(self.$el);

                } else {

                    message.appendTo(self.$el);

                }
            }

            return message
        },
        
        /**
         *get the parent thread of the messages.
         * Each message is send to his parent object (or parent thread flat mode) for creating the object message.
         * @param : {Array} datas from calling RPC to "message_read"
         */
        switch_new_message: function(records) {
            var self=this;
            _(records).each(function(record){
                var thread = self.browse_thread({
                    'id': record.ancestor_id, 
                    'default_return_top_thread':true
                });
                thread.create_message_object( record );
            });
        },

        /**
         * this method is call when the widget of a message or an expandable message is destroy
         * in this thread. The this.messages array is filter to remove this message
         */
        on_message_detroy: function (message) {

            this.messages = _.filter(this.messages, function (val) { return !val.isDestroyed(); });

        },

        /**
         * Convert a destroyed message into a expandable message
         */
        message_to_expandable: function (message) {

            if(!this.thread_level || message.isDestroyed()) {
                message.destroy();
                return false;
            }

            var messages = _.sortBy( this.messages, function (val) { return val.id; });
            var it = _.indexOf( messages, message );

            var msg_up = messages[it-1];
            var msg_down = messages[it+1];

            var message_dom = [ ["id", "=", message.id] ];

            if ( msg_up && msg_up.type == "expandable" && msg_down && msg_down.type == "expandable") {
                // concat two expandable message and add this message to this dom
                msg_up.domain = mail.ChatterUtils.expend_domain( msg_up.domain );
                msg_down.domain = mail.ChatterUtils.expend_domain( msg_down.domain );

                msg_down.domain = ['|','|'].concat( msg_up.domain ).concat( message_dom ).concat( msg_down.domain );

                if( !msg_down.max_limit ){
                    msg_down.nb_messages += 1 + msg_up.nb_messages;
                }

                msg_up.$el.remove();
                msg_up.destroy();

                msg_down.reinit();

            } else if ( msg_up && msg_up.type == "expandable") {
                // concat preview expandable message and this message to this dom
                msg_up.domain = mail.ChatterUtils.expend_domain( msg_up.domain );
                msg_up.domain = ['|'].concat( msg_up.domain ).concat( message_dom );
                
                msg_up.nb_messages++;

                msg_up.reinit();

            } else if ( msg_down && msg_down.type == "expandable") {
                // concat next expandable message and this message to this dom
                msg_down.domain = mail.ChatterUtils.expend_domain( msg_down.domain );
                msg_down.domain = ['|'].concat( msg_down.domain ).concat( message_dom );
                
                // it's maybe a message expandable for the max limit read message
                if( !msg_down.max_limit ){
                    msg_down.nb_messages++;
                }
                
                msg_down.reinit();

            } else {
                // create a expandable message
                var expandable = new mail.ThreadExpandable(this, {
                    'id': message.id,
                    'model': message.model,
                    'ancestor_id': message.ancestor_id,
                    'nb_messages': 1,
                    'thread_level': message.thread_level,
                    'ancestor_id': message.ancestor_id
                    }, {
                    'domain': message_dom,
                    'context': {
                        'default_model': message.model || this.context.default_model,
                        'default_res_id': message.res_id || this.context.default_res_id,
                        'default_parent_id': this.id },
                });

                // add object on array and DOM
                this.messages.push(expandable);
                expandable.insertAfter(message.$el);
            }

            // destroy message
            message.destroy();

            return true;
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
         *...  @param {Boolean} [show_compose_message] allow to display the composer
         *...  @param {Boolean} [show_compact_message] display the compact message on the thread
         *      when the user clic on this compact mode, the composer is open
         *...  @param {Array} [message_ids] List of ids to fetch by the root thread.
         *      When you use this option, the domain is not used for the fetch root.
         */
        init: function (parent, options) {
            this._super(parent);
            this.domain = options.domain || [];
            this.context = options.context || {};
            this.search_results = {'domain': [], 'context': {}, 'groupby': {}};

            this.options = _.extend({
                'typeof_thread' : 'inbox',
                'display_indented_thread' : -1,
                'show_reply_button' : -1,
                'show_read_unread_button' : -1,
                'truncate_limit' : 250,
                'show_record_name' : false,
                'show_compose_message' : false,
                'show_compact_message' : false,
                'message_ids': []
            }, options);

            if(this.display_indented_thread === false) {
                this.display_indented_thread = -1;
            }
            if(this.show_reply_button === false) {
                this.show_reply_button = -1;
            }
            if(this.show_read_unread_button === false) {
                this.show_read_unread_button = -1;
            }
            
        },

        start: function (options) {
            this._super.apply(this, arguments);
            this.message_render();
            this.bind_events();
        },

        
        /**
         *Create the root thread and display this object in the DOM.
         * Call the no_message method then c all the message_fetch method 
         * of this root thread to display the messages.
         */
        message_render: function (search) {

            this.thread = new mail.Thread(this, {}, {
                'domain' : this.domain,
                'context' : this.context,
                'options': this.options,
            });

            this.thread.appendTo( this.$el );
            this.thread.no_message();
            this.thread.message_fetch(null, null, this.options.message_ids);

            if(this.options.show_compose_message) {
                if(this.options.show_compact_message) {
                    this.thread.ComposeMessage.do_show_compact();
                } else {
                    this.thread.ComposeMessage.do_hide_compact();
                }
            }
        },

        bind_events: function(){
            if(this.context['typeof_thread']!='other'){
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
            var self = this;
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

            var show_compose_message = this.view.is_action_enabled('edit') ||
                (this.getParent().fields.message_is_follower && this.getParent().fields.message_is_follower.get_value());

            var message_ids = this.getParent().fields.message_ids && this.getParent().fields.message_ids.get_value();

            if(this.root){
                this.root.destroy();
            }
            // create and render Thread widget
            this.root = new mail.Widget(this, {
                'domain' : domain,
                'context' : this.options.context,
                'typeof_thread': this.options.context['typeof_thread'] || 'other',
                'display_indented_thread': -1,
                'show_reply_button': 0,
                'show_read_unread_button': -1,
                'show_compose_message': show_compose_message,
                'message_ids': message_ids,
                'show_compact_message': true,
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
         *Create the root thread widget and display this object in the DOM
          */
        message_render: function (search) {
            var domain = this.options.domain.concat(this.search_results['domain']);
            var context = _.extend(this.options.context, search&&search.search_results['context'] ? search.search_results['context'] : {});
            this.root = new mail.Widget(this, {
                'domain' : domain,
                'context' : context,
                'typeof_thread': context['typeof_thread'] || 'other',
                'display_indented_thread': 1,
                'show_reply_button': 10,
                'show_read_unread_button': 11,
                'show_compose_message': true,
                'show_compact_message': true,
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
                context: _.extend(this.options.context, {
                    'default_model': this.context.default_model,
                    'default_res_id': this.context.default_res_id,
                    'default_content_subtype': 'html',
                }),
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
