openerp.mail = function (session) {
    var _t = session.web._t,
       _lt = session.web._lt;

    var mail = session.mail = {};

    openerp_mail_followers(session, mail);        // import mail_followers.js
    openerp_FieldMany2ManyTagsEmail(session);      // import manyy2many_tags_email.js

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

        /** parse text to find email: Tagada <address@mail.fr> -> [Tagada, address@mail.fr] or False */
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

        /* Get an image in /web/binary/image?... */
        get_image: function (session, model, field, id, resize) {
            var r = resize ? encodeURIComponent(resize) : '';
            id = id || '';
            return session.url('/web/binary/image', {model: model, field: field, id: id, resize: r});
        },

        /* Get the url of an attachment {'id': id} */
        get_attachment_url: function (session, message_id, attachment_id) {
            return session.url('/mail/download_attachment', {
                'model': 'mail.message',
                'id': message_id,
                'method': 'download_attachment',
                'attachment_id': attachment_id
            });
        },

        /**
         * Replaces some expressions
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

        /**
         * Replaces textarea text into html text (add <p>, <a>)
         * TDE note : should be done server-side, in Python -> use mail.compose.message ?
         */
        get_text2html: function (text) {
            return text
                .replace(/[\n\r]/g,'<br/>')
                .replace(/((?:https?|ftp):\/\/[\S]+)/g,'<a href="$1">$1</a> ')
        },

        /* Returns the complete domain with "&" 
         * TDE note: please add some comments to explain how/why
         */
        expand_domain: function (domain) {
            var new_domain = [];
            var nb_and = -1;
            // TDE note: smarted code maybe ?
            for ( var k = domain.length-1; k >= 0 ; k-- ) {
                if ( typeof domain[k] != 'array' && typeof domain[k] != 'object' ) {
                    nb_and -= 2;
                    continue;
                }
                nb_and += 1;
            }

            for (var k = 0; k < nb_and ; k++) {
                domain.unshift('&');
            }

            return domain;
        },

        // inserts zero width space between each letter of a string so that
        // the word will correctly wrap in html boxes smaller than the text
        breakword: function(str){
            var out = '';
            if (!str) {
                return str;
            }
            for(var i = 0, len = str.length; i < len; i++){
                out += _.str.escapeHTML(str[i]) + '&#8203;';
            }
            return out;
        },

        // returns the file type of a file based on its extension 
        // As it only looks at the extension it is quite approximative. 
        filetype: function(url){
            var url = url && url.filename || url;
            var tokens = typeof url == 'string' ? url.split('.') : [];
            if(tokens.length <= 1){
                return 'unknown';
            }
            var extension = tokens[tokens.length -1];
            if(extension.length === 0){
                return 'unknown';
            }else{
                extension = extension.toLowerCase();
            }
            var filetypes = {
                'webimage':     ['png','jpg','jpeg','jpe','gif'], // those have browser preview
                'image':        ['tif','tiff','tga',
                                 'bmp','xcf','psd','ppm','pbm','pgm','pnm','mng',
                                 'xbm','ico','icon','exr','webp','psp','pgf','xcf',
                                 'jp2','jpx','dng','djvu','dds'],
                'vector':       ['ai','svg','eps','vml','cdr','xar','cgm','odg','sxd'],
                'print':        ['dvi','pdf','ps'],
                'document':     ['doc','docx','odm','odt'],
                'presentation': ['key','keynote','odp','pps','ppt'],
                'font':         ['otf','ttf','woff','eot'],
                'archive':      ['zip','7z','ace','apk','bzip2','cab','deb','dmg','gzip','jar',
                                 'rar','tar','gz','pak','pk3','pk4','lzip','lz','rpm'],
                'certificate':  ['cer','key','pfx','p12','pem','crl','der','crt','csr'],
                'audio':        ['aiff','wav','mp3','ogg','flac','wma','mp2','aac',
                                 'm4a','ra','mid','midi'],
                'video':        ['asf','avi','flv','mkv','m4v','mpeg','mpg','mpe','wmv','mp4','ogm'],
                'text':         ['txt','rtf','ass'],
                'html':         ['html','xhtml','xml','htm','css'],
                'disk':         ['iso','nrg','img','ccd','sub','cdi','cue','mds','mdx'],
                'script':       ['py','js','c','cc','cpp','cs','h','java','bat','sh',
                                 'd','rb','pl','as','cmd','coffee','m','r','vbs','lisp'],
                'spreadsheet':  ['123','csv','ods','numbers','sxc','xls','vc','xlsx'],
                'binary':       ['exe','com','bin','app'],
            };
            for(filetype in filetypes){
                var ext_list = filetypes[filetype];
                for(var i = 0, len = ext_list.length; i < len; i++){
                    if(extension === ext_list[i]){
                        return filetype;
                    }
                }
            }
            return 'unknown';
        },

    };


    /**
     * ------------------------------------------------------------
     * MessageCommon
     * ------------------------------------------------------------
     * 
     * Common base for expandables, chatter messages and composer. It manages
     * the various variables common to those models.
     */

    mail.MessageCommon = session.web.Widget.extend({

    /**
     * ------------------------------------------------------------
     * FIXME: this comment was moved as is from the ThreadMessage Init as
     * part of a refactoring. Check that it is still correct
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
        
        init: function (parent, datasets, options) {
            this._super(parent, options);

            // record options
            this.options = datasets.options || options || {};
            // record domain and context
            this.domain = datasets.domain || options.domain || [];
            this.context = _.extend({
                default_model: false,
                default_res_id: 0,
                default_parent_id: false }, options.context || {});

            // data of this message
            this.id = datasets.id ||  false,
            this.last_id = this.id,
            this.model = datasets.model || this.context.default_model || false,
            this.res_id = datasets.res_id || this.context.default_res_id ||  false,
            this.parent_id = datasets.parent_id ||  false,
            this.type = datasets.type ||  false,
            this.subtype = datasets.subtype ||  false,
            this.is_author = datasets.is_author ||  false,
            this.is_private = datasets.is_private ||  false,
            this.subject = datasets.subject ||  false,
            this.name = datasets.name ||  false,
            this.record_name = datasets.record_name ||  false,
            this.body = datasets.body || '',
            this.vote_nb = datasets.vote_nb || 0,
            this.has_voted = datasets.has_voted ||  false,
            this.is_favorite = datasets.is_favorite ||  false,
            this.thread_level = datasets.thread_level ||  0,
            this.to_read = datasets.to_read || false,
            this.author_id = datasets.author_id || false,
            this.attachment_ids = datasets.attachment_ids ||  [],
            this.partner_ids = datasets.partner_ids || [];
            this.date = datasets.date;

            this.format_data();

            // record options and data
            this.show_record_name = this.options.show_record_name && this.record_name && !this.thread_level && this.model != 'res.partner';
            this.options.show_read = false;
            this.options.show_unread = false;
            if (this.options.show_read_unread_button) {
                if (this.options.read_action == 'read') this.options.show_read = true;
                else if (this.options.read_action == 'unread') this.options.show_unread = true;
                else {
                    this.options.show_read = this.to_read;
                    this.options.show_unread = !this.to_read;
                }
                this.options.rerender = true;
                this.options.toggle_read = true;
            }
            this.parent_thread = typeof parent.on_message_detroy == 'function' ? parent : this.options.root_thread;
            this.thread = false;
        },

        /* Convert date, timerelative and avatar in displayable data. */
        format_data: function () {
            //formating and add some fields for render
            this.date = this.date ? session.web.str_to_datetime(this.date) : false;
            if (this.date && new Date().getTime()-this.date.getTime() < 7*24*60*60*1000) {
                this.timerelative = $.timeago(this.date);
            } 
            if (this.type == 'email' && (!this.author_id || !this.author_id[0])) {
                this.avatar = ('/mail/static/src/img/email_icon.png');
            } else if (this.author_id && this.template != 'mail.compose_message') {
                this.avatar = mail.ChatterUtils.get_image(this.session, 'res.partner', 'image_small', this.author_id[0]);
            } else {
                this.avatar = mail.ChatterUtils.get_image(this.session, 'res.users', 'image_small', this.session.uid);
            }
            if (this.author_id && this.author_id[1]) {
                var parsed_email = mail.ChatterUtils.parse_email(this.author_id[1]);
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


        /* upload the file on the server, add in the attachments list and reload display
         */
        display_attachments: function () {
            for (var l in this.attachment_ids) {
                var attach = this.attachment_ids[l];
                if (!attach.formating) {
                    attach.url = mail.ChatterUtils.get_attachment_url(this.session, this.id, attach.id);
                    attach.filetype = mail.ChatterUtils.filetype(attach.filename || attach.name);
                    attach.name = mail.ChatterUtils.breakword(attach.name || attach.filename);
                    attach.formating = true;
                }
            }
            this.$(".oe_msg_attachment_list").html( session.web.qweb.render('mail.thread.message.attachments', {'widget': this}) );
        },

        /* return the link to resized image
         */
        attachments_resize_image: function (id, resize) {
            return mail.ChatterUtils.get_image(this.session, 'ir.attachment', 'datas', id, resize);
        },

        /* get all child message id linked.
         * @return array of id
        */
        get_child_ids: function () {
            return _.map(this.get_childs(), function (val) { return val.id; });
        },

        /* get all child message linked.
         * @return array of message object
        */
        get_childs: function (nb_thread_level) {
            var res=[];
            if (arguments[1] && this.id) res.push(this);
            if ((isNaN(nb_thread_level) || nb_thread_level>0) && this.thread) {
                _(this.thread.messages).each(function (val, key) {
                    res = res.concat( val.get_childs((isNaN(nb_thread_level) ? undefined : nb_thread_level-1), true) );
                });
            }
            return res;
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
        browse_message: function (options) {
            // goto the wall thread for launch browse
            if (!options._go_thread_wall) {
                options._go_thread_wall = true;
                for (var i in this.options.root_thread.messages) {
                    var res=this.options.root_thread.messages[i].browse_message(options);
                    if (res) return res;
                }
            }

            if (this.id==options.id)
                return this;

            for (var i in this.thread.messages) {
                if (this.thread.messages[i].thread) {
                    var res=this.thread.messages[i].browse_message(options);
                    if (res) return res;
                }
            }

            return false;
        },

        /**
         * call on_message_delete on his parent thread
        */
        destroy: function () {

            this._super();
            this.parent_thread.on_message_detroy(this);

        }

    });

    /**
     * ------------------------------------------------------------
     * ComposeMessage widget
     * ------------------------------------------------------------
     * 
     * This widget handles the display of a form to compose a new message.
     * This form is a mail.compose.message form_view.
     * On first time : display a compact textarea that is not the compose form.
     * When the user focuses the textarea, the compose message is instantiated.
     */
    
    mail.ThreadComposeMessage = mail.MessageCommon.extend({
        template: 'mail.compose_message',

        /**
         * @param {Object} parent parent
         * @param {Object} [options]
         *      @param {Object} [context] context passed to the
         *          mail.compose.message DataSetSearch. Please refer to this model
         *          for more details about fields and default values.
         * @param {Object} recipients = [
                        {
                            'email_address': [str],
                            'partner_id': False/[int],
                            'name': [str],
                            'full_name': name<email_address>,
                        },
                        { ... },
                    ]
         */

        init: function (parent, datasets, options) {
            this._super(parent, datasets, options);
            this.show_compact_message = false;
            this.show_delete_attachment = true;
            this.is_log = false;
            this.recipients = [];
            this.recipient_ids = [];
        },

        start: function () {
            this._super.apply(this, arguments);

            this.ds_attachment = new session.web.DataSetSearch(this, 'ir.attachment');
            this.fileupload_id = _.uniqueId('oe_fileupload_temp');
            $(window).on(this.fileupload_id, this.on_attachment_loaded);

            this.display_attachments();
            this.bind_events();
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
                for (var i in this.attachment_ids) {
                    if ((this.attachment_ids[i].filename || this.attachment_ids[i].name) == filename) {
                        if (this.attachment_ids[i].upload) {
                            return false;
                        }
                        this.ds_attachment.unlink([this.attachment_ids[i].id]);
                    } else {
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
        
        /* when the file is uploaded 
        */
        on_attachment_loaded: function (event, result) {

            if (result.erorr || !result.id ) {
                this.do_warn( session.web.qweb.render('mail.error_upload'), result.error);
                this.attachment_ids = _.filter(this.attachment_ids, function (val) { return !val.upload; });
            } else {
                for (var i in this.attachment_ids) {
                    if (this.attachment_ids[i].filename == result.filename && this.attachment_ids[i].upload) {
                        this.attachment_ids[i]={
                            'id': result.id,
                            'name': result.name,
                            'filename': result.filename,
                            'url': mail.ChatterUtils.get_attachment_url(this.session, this.id, result.id)
                        };
                    }
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
                for (var i in this.attachment_ids) {
                    if (attachment_id!=this.attachment_ids[i].id) {
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

        bind_events: function () {
            var self = this;
            this.$('.oe_compact_inbox').on('click', self.on_toggle_quick_composer);
            this.$('.oe_compose_post').on('click', self.on_toggle_quick_composer);
            this.$('.oe_compose_log').on('click', self.on_toggle_quick_composer);
            this.$('input.oe_form_binary_file').on('change', _.bind( this.on_attachment_change, this));
            this.$('.oe_cancel').on('click', _.bind( this.on_cancel, this));
            this.$('.oe_post').on('click', self.on_message_post);
            this.$('.oe_full').on('click', _.bind( this.on_compose_fullmail, this, this.id ? 'reply' : 'comment'));
            /* stack for don't close the compose form if the user click on a button */
            this.$('.oe_msg_left, .oe_msg_center').on('mousedown', _.bind( function () { this.stay_open = true; }, this));
            this.$('.oe_msg_left, .oe_msg_content').on('mouseup', _.bind( function () { this.$('textarea').focus(); }, this));
            var ev_stay = {};
            ev_stay.mouseup = ev_stay.keydown = ev_stay.focus = function () { self.stay_open = false; };
            this.$('textarea').on(ev_stay);
            this.$('textarea').autosize();

            // auto close
            this.$('textarea').on('blur', self.on_toggle_quick_composer);

            // event: delete child attachments off the oe_msg_attachment_list box
            this.$(".oe_msg_attachment_list").on('click', '.oe_delete', this.on_attachment_delete);

            this.$(".oe_recipients").on('change', 'input', this.on_checked_recipient);
        },

        on_compose_fullmail: function (default_composition_mode) {
            var self = this;
            if(!this.do_check_attachment_upload()) {
                return false;
            }
            var recipient_done = $.Deferred();
            if (this.is_log) {
                recipient_done.resolve([]);
            }
            else {
                recipient_done = this.check_recipient_partners();
            }
            $.when(recipient_done).done(function (partner_ids) {
                var context = {
                    'default_composition_mode': default_composition_mode,
                    'default_parent_id': self.id,
                    'default_body': mail.ChatterUtils.get_text2html(self.$el ? (self.$el.find('textarea:not(.oe_compact)').val() || '') : ''),
                    'default_attachment_ids': self.attachment_ids,
                    'default_partner_ids': partner_ids,
                    'mail_post_autofollow': true,
                    'mail_post_autofollow_partner_ids': partner_ids,
                };
                if (self.is_log) {
                    _.extend(context, {'mail_compose_log': true});
                }
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

        reinit: function() {
            var $render = $( session.web.qweb.render('mail.compose_message', {'widget': this}) );

            $render.insertAfter(this.$el.last());
            this.$el.remove();
            this.$el = $render;

            this.display_attachments();
            this.bind_events();
        },

        on_cancel: function (event) {
            if (event) event.stopPropagation();
            this.attachment_ids=[];
            this.stay_open = false;
            this.show_composer = false;
            this.reinit();
        },

        /* return true if all file are complete else return false and make an alert */
        do_check_attachment_upload: function () {
            if (_.find(this.attachment_ids, function (file) {return file.upload;})) {
                this.do_warn(session.web.qweb.render('mail.error_upload'), session.web.qweb.render('mail.error_upload_please_wait'));
                return false;
            } else {
                return true;
            }
        },

        check_recipient_partners: function () {
            var self = this;
            var check_done = $.Deferred();
            var recipients = _.filter(this.recipients, function (recipient) { return recipient.checked });
            var recipients_to_find = _.filter(recipients, function (recipient) { return (! recipient.partner_id) });
            var names_to_find = _.pluck(recipients_to_find, 'full_name');
            var recipients_to_check = _.filter(recipients, function (recipient) { return (recipient.partner_id && ! recipient.email_address) });
            var recipient_ids = _.pluck(_.filter(recipients, function (recipient) { return recipient.partner_id && recipient.email_address }), 'partner_id');
            var names_to_remove = [];
            var recipient_ids_to_remove = [];

            // have unknown names -> call message_get_partner_info_from_emails to try to find partner_id
            var find_done = $.Deferred();
            if (names_to_find.length > 0) {
                var values = {
                    'res_id': this.context.default_res_id,
                }
                find_done = self.parent_thread.ds_thread._model.call('message_get_partner_info_from_emails', [names_to_find], values);
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
                        var values = {
                            'link_mail': true,
                            'res_id': self.context.default_res_id,
                        }
                        find_done = self.parent_thread.ds_thread._model.call('message_get_partner_info_from_emails', [new_names_to_find], values);
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

        on_message_post: function (event) {
            var self = this;
            if (self.flag_post) {
                return;
            }
            self.flag_post = true;
            if (this.do_check_attachment_upload() && (this.attachment_ids.length || this.$('textarea').val().match(/\S+/))) {
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

        /* do post a message and fetch the message */
        do_send_message_post: function (partner_ids, log) {
            var self = this;
            var values = {
                'body': this.$('textarea').val(),
                'subject': false,
                'parent_id': this.context.default_parent_id,
                'attachment_ids': _.map(this.attachment_ids, function (file) {return file.id;}),
                'partner_ids': partner_ids,
                'context': _.extend(this.parent_thread.context, {
                    'mail_post_autofollow': true,
                    'mail_post_autofollow_partner_ids': partner_ids,
                }),
                'type': 'comment',
                'content_subtype': 'plaintext',
            };
            if (log) {
                values['subtype'] = false;
            }
            else {
                values['subtype'] = 'mail.mt_comment';   
            }
            this.parent_thread.ds_thread._model.call('message_post', [this.context.default_res_id], values).done(function (message_id) {
                var thread = self.parent_thread;
                var root = thread == self.options.root_thread;
                if (self.options.display_indented_thread < self.thread_level && thread.parent_message) {
                    var thread = thread.parent_message.parent_thread;
                }
                // create object and attach to the thread object
                thread.message_fetch([["id", "=", message_id]], false, [message_id], function (arg, data) {
                    var message = thread.create_message_object( data[0] );
                    // insert the message on dom
                    thread.insert_message( message, root ? undefined : self.$el, root );
                });
                self.on_cancel();
                self.flag_post = false;
            });
        },

        /* Quick composer: toggle minimal / expanded mode
         * - toggle minimal (one-liner) / expanded (textarea, buttons) mode
         * - when going into expanded mode:
         *  - call `message_get_suggested_recipients` to have a list of partners to add
         *  - compute email_from list (list of unknown email_from to propose to create partners)
         */
        on_toggle_quick_composer: function (event) {
            var self = this;
            var $input = $(event.target);
            this.compute_emails_from();
            var email_addresses = _.pluck(this.recipients, 'email_address');
            var suggested_partners = $.Deferred();

            // if clicked: call for suggested recipients
            if (event.type == 'click') {
                this.is_log = $input.hasClass('oe_compose_log');
                suggested_partners = this.parent_thread.ds_thread.call('message_get_suggested_recipients', [[this.context.default_res_id]]).done(function (additional_recipients) {
                    var thread_recipients = additional_recipients[self.context.default_res_id];
                    _.each(thread_recipients, function (recipient) {
                        var parsed_email = mail.ChatterUtils.parse_email(recipient[1]);
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
                if ((!self.stay_open || (event && event.type == 'click')) && (!self.show_composer || !self.$('textarea:not(.oe_compact)').val().match(/\S+/) && !self.attachment_ids.length)) {
                    self.show_composer = !self.show_composer || self.stay_open;
                    self.reinit();
                }
                if (!self.stay_open && self.show_composer && (!event || event.type != 'blur')) {
                    self.$('textarea:not(.oe_compact):first').focus();
                }
            });

            return suggested_partners;
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

        /** Compute the list of unknown email_from the the given thread
         * TDE FIXME: seems odd to delegate to the composer
         * TDE TODO: please de-obfuscate and comment your code */
        compute_emails_from: function () {
            var self = this;
            var messages = [];

            if (this.parent_thread.parent_message) {
                // go to the parented message
                var message = this.parent_thread.parent_message;
                var parent_message = message.parent_id ? message.parent_thread.parent_message : message;
                var messages = [parent_message].concat(parent_message.get_childs());
            } else if (this.options.emails_from_on_composer) {
                // get all wall messages if is not a mail.Wall
                _.each(this.options.root_thread.messages, function (msg) {messages.push(msg); messages.concat(msg.get_childs());});
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

        on_checked_recipient: function (event) {
            var $input = $(event.target);
            var email = $input.attr("data");
            _.each(this.recipients, function (recipient) {
                if (recipient.email_address == email) {
                    recipient.checked = $input.is(":checked");
                }
            });
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
    mail.ThreadExpandable = mail.MessageCommon.extend({
        template: 'mail.thread.expandable',

        init: function (parent, datasets, options) {
            this._super(parent, datasets, options);
            this.type = 'expandable';
            this.max_limit = datasets.max_limit;
            this.nb_messages = datasets.nb_messages;
            this.flag_used = false;
        },
        
        start: function () {
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
        bind_events: function () {
            this.$('.oe_msg_more_message').on('click', this.on_expandable);
        },

        animated_destroy: function (fadeTime) {
            var self=this;
            this.$el.fadeOut(fadeTime, function () {
                self.destroy();
            });
        },

        /*The selected thread and all childs (messages/thread) became read
        * @param {object} mouse envent
        */
        on_expandable: function (event) {
            if (event)event.stopPropagation();
            if (this.flag_used) {
                return false
            }
            this.flag_used = true;

            var self = this;

            // read messages
            self.parent_thread.message_fetch(this.domain, this.context, false, function (arg, data) {
                self.id = false;
                // insert the message on dom after this message
                self.parent_thread.switch_new_message( data, self.$el );
                self.animated_destroy(200);
            });

            return false;
        },

    });

    mail.ThreadMessage = mail.MessageCommon.extend({
        template: 'mail.thread.message',
        
        start: function () {
            this._super.apply(this, arguments);
            this.expender();
            this.bind_events();
            if(this.thread_level < this.options.display_indented_thread) {
                this.create_thread();
            }
            this.display_attachments();

            this.ds_notification = new session.web.DataSetSearch(this, 'mail.notification');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function () {
            var self = this;
            // header icons bindings
            this.$('.oe_read').on('click', this.on_message_read);
            this.$('.oe_unread').on('click', this.on_message_unread);
            this.$('.oe_msg_delete').on('click', this.on_message_delete);
            this.$('.oe_reply').on('click', this.on_message_reply);
            this.$('.oe_star').on('click', this.on_star);
            this.$('.oe_msg_vote').on('click', this.on_vote);
        },

        /* Call the on_compose_message on the thread of this message. */
        on_message_reply:function (event) {
            event.stopPropagation();
            this.create_thread();
            this.thread.on_compose_message(event);
            return false;
        },

        expender: function () {
            this.$('.oe_msg_body:first').expander({
                slicePoint: this.options.truncate_limit,
                expandText: 'read more',
                userCollapseText: 'read less',
                detailClass: 'oe_msg_tail',
                moreClass: 'oe_mail_expand',
                lessClass: 'oe_mail_reduce',
                });
        },

        /**
         * Instantiate the thread object of this message.
         * Each message have only one thread.
         */
        create_thread: function () {
            if (this.thread) {
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
            if (! confirm(_t("Do you really want to delete this message?"))) { return false; }
            
            this.animated_destroy(150);
            // delete this message and his childs
            var ids = [this.id].concat( this.get_child_ids() );
            this.ds_message.unlink(ids);
            return false;
        },

        /* Check if the message must be destroy and detroy it or check for re render widget
        * @param {callback} apply function
        */
        check_for_rerender: function () {
            var self = this;

            var messages = [this].concat(this.get_childs());
            var message_ids = _.map(messages, function (msg) { return msg.id;});
            var domain = mail.ChatterUtils.expand_domain( this.options.root_thread.domain )
                .concat([["id", "in", message_ids ]]);

            return this.parent_thread.ds_message.call('message_read', [undefined, domain, [], !!this.parent_thread.options.display_indented_thread, this.context, this.parent_thread.id])
                .then( function (records) {
                    // remove message not loaded
                    _.map(messages, function (msg) {
                        if(!_.find(records, function (record) { return record.id == msg.id; })) {
                            msg.animated_destroy(150);
                        } else {
                            msg.renderElement();
                            msg.start();
                        }
                        if( self.options.root_thread.__parentedParent.__parentedParent.do_reload_menu_emails ) {
                            self.options.root_thread.__parentedParent.__parentedParent.do_reload_menu_emails();
                        }
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
         * add or remove a vote for a message and display the result
        */
        on_vote: function (event) {
            event.stopPropagation();
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
         * Display the render of this message's vote
        */
        display_vote: function () {
            var vote_element = session.web.qweb.render('mail.thread.message.vote', {'widget': this});
            this.$(".oe_msg_footer:first .oe_mail_vote_count").remove();
            this.$(".oe_msg_footer:first .oe_msg_vote").replaceWith(vote_element);
            this.$('.oe_msg_vote').on('click', this.on_vote);
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
                    } else {
                        button.removeClass('oe_starred');
                    }

                    if (self.options.view_inbox && self.is_favorite) {
                        self.on_message_read_unread(true);
                    } else {
                        self.check_for_rerender();
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
         *          @param {int} [display_indented_thread] number thread level to indented threads.
         *              other are on flat mode
         *          @param {Array} [parents] liked with the parents thread
         *              use with browse, fetch... [O]= top parent
         */
        init: function (parent, datasets, options) {
            var self = this;
            this._super(parent, options);
            this.domain = options.domain || [];
            this.context = _.extend(options.context || {});

            this.options = options.options;
            this.options.root_thread = (options.options.root_thread != undefined ? options.options.root_thread : this);
            this.options.show_compose_message = this.options.show_compose_message && !this.thread_level;
            
            // record options and data
            this.parent_message= parent.thread!= undefined ? parent : false ;

            // data of this thread
            this.id = datasets.id || false;
            this.last_id = datasets.last_id || false;
            this.parent_id = datasets.parent_id || false;
            this.is_private = datasets.is_private || false;
            this.author_id = datasets.author_id || false;
            this.thread_level = (datasets.thread_level+1) || 0;
            datasets.partner_ids = datasets.partner_ids || [];
            if (datasets.author_id && !_.contains(_.flatten(datasets.partner_ids),datasets.author_id[0]) && datasets.author_id[0]) {
                datasets.partner_ids.push(datasets.author_id);
            }
            this.partner_ids = datasets.partner_ids;
            this.messages = [];

            this.options.flat_mode = (this.options.display_indented_thread - this.thread_level > 0);

            // object compose message
            this.compose_message = false;

            this.ds_thread = new session.web.DataSetSearch(this, this.context.default_model || 'mail.thread');
            this.ds_message = new session.web.DataSetSearch(this, 'mail.message');
            this.render_mutex = new $.Mutex();
        },
        
        start: function () {
            this._super.apply(this, arguments);
            this.bind_events();
        },

        /* instantiate the compose message object and insert this on the DOM.
        * The compose message is display in compact form.
        */
        instantiate_compose_message: function () {
            // add message composition form view
            if (!this.compose_message) {
                this.compose_message = new mail.ThreadComposeMessage(this, this, {
                    'context': this.options.compose_as_todo && !this.thread_level ? _.extend(this.context, { 'default_starred': true }) : this.context,
                    'options': this.options,
                });
                if (!this.thread_level || this.thread_level > this.options.display_indented_thread) {
                    this.compose_message.insertBefore(this.$el);
                } else {
                    this.compose_message.prependTo(this.$el);
                }
            }
        },

        /* When the expandable object is visible on screen (with scrolling)
         * then the on_expandable function is launch
        */
        on_scroll: function () {
            var expandables = 
            _.each( _.filter(this.messages, function (val) {return val.max_limit && !val.parent_id;}), function (val) {
                var pos = val.$el.position();
                if (pos.top) {
                    /* bottom of the screen */
                    var bottom = $(window).scrollTop()+$(window).height()+200;
                    if (bottom > pos.top) {
                        val.on_expandable();
                    }
                }
            });
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function () {
            var self = this;
            self.$('.oe_mail_list_recipients .oe_more').on('click', self.on_show_recipients);
            self.$('.oe_mail_compose_textarea .oe_more_hidden').on('click', self.on_hide_recipients);
        },

        /**
         *show all the partner list of this parent message
        */
        on_show_recipients: function () {
            var p=$(this).parent(); 
            p.find('.oe_more_hidden, .oe_hidden').show(); 
            p.find('.oe_more').hide(); 
            return false;
        },

        /**
         *hide a part of the partner list of this parent message
        */
        on_hide_recipients: function () {
            var p=$(this).parent(); 
            p.find('.oe_more_hidden, .oe_hidden').hide(); 
            p.find('.oe_more').show(); 
            return false;
        },

        /* get all child message/thread id linked.
         * @return array of id
        */
        get_child_ids: function () {
            return _.map(this.get_childs(), function (val) { return val.id; });
        },

        /* get all child message/thread linked.
         * @param {int} nb_thread_level, number of traversed thread level for this search
         * @return array of thread object
        */
        get_childs: function (nb_thread_level) {
            var res=[];
            if (arguments[1]) res.push(this);
            if (isNaN(nb_thread_level) || nb_thread_level>0) {
                _(this.messages).each(function (val, key) {
                    if (val.thread) {
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
        browse_thread: function (options) {
            // goto the wall thread for launch browse
            if (!options._go_thread_wall) {
                options._go_thread_wall = true;
                return this.options.root_thread.browse_thread(options);
            }

            if (this.id == options.id) {
                return this;
            }

            if (options.id) {
                for (var i in this.messages) {
                    if (this.messages[i].thread) {
                        var res = this.messages[i].thread.browse_thread({'id':options.id, '_go_thread_wall':true});
                        if (res) return res;
                    }
                }
            }

            //if option default_return_top_thread, return the top if no found thread
            if (options.default_return_top_thread) {
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
        browse_message: function (options) {
            if (this.options.root_thread.messages[0])
                return this.options.root_thread.messages[0].browse_message(options);
        },

        /**
         *If compose_message doesn't exist, instantiate the compose message.
        * Call the on_toggle_quick_composer method to allow the user to write his message.
        * (Is call when a user click on "Reply" button)
        */
        on_compose_message: function (event) {
            this.instantiate_compose_message();
            this.compose_message.on_toggle_quick_composer(event);
            return false;
        },

        /**
         *display the message "there are no message" on the thread
        */
        no_message: function () {
            var no_message = $(session.web.qweb.render('mail.wall_no_message', {}));
            if (this.options.help) {
                no_message.html(this.options.help);
            }
            if (!this.$el.find(".oe_view_nocontent").length)
            {
                no_message.appendTo(this.$el);
            }
        },

        /**
         *make a request to read the message (calling RPC to "message_read").
         * The result of this method is send to the switch message for sending ach message to
         * his parented object thread.
         * @param {Array} replace_domain: added to this.domain
         * @param {Object} replace_context: added to this.context
         * @param {Array} ids read (if the are some ids, the method don't use the domain)
         */
        message_fetch: function (replace_domain, replace_context, ids, callback) {
            return this.ds_message.call('message_read', [
                    // ids force to read
                    ids == false ? undefined : ids, 
                    // domain + additional
                    (replace_domain ? replace_domain : this.domain), 
                    // ids allready loaded
                    (this.id ? [this.id].concat( this.get_child_ids() ) : this.get_child_ids()), 
                    // option for sending in flat mode by server
                    this.options.flat_mode, 
                    // context + additional
                    (replace_context ? replace_context : this.context), 
                    // parent_id
                    this.context.default_parent_id || undefined
                ]).done(callback ? _.bind(callback, this, arguments) : this.proxy('switch_new_message')
                ).done(this.proxy('message_fetch_set_read'));
        },

        message_fetch_set_read: function (message_list) {
            if (! this.context.mail_read_set_read) return;
            this.render_mutex.exec(_.bind(function() {
                msg_ids = _.pluck(message_list, 'id');
                return this.ds_message.call('set_message_read', [
                        msg_ids, true, false, this.context]);
             }, this));
        },

        /**
         *create the message object and attached on this thread.
         * When the message object is create, this method call insert_message for,
         * displaying this message on the DOM.
         * @param : {object} data from calling RPC to "message_read"
         */
        create_message_object: function (data) {
            var self = this;

            data.thread_level = self.thread_level || 0;
            data.options = _.extend(data.options || {}, self.options);

            if (data.type=='expandable') {
                var message = new mail.ThreadExpandable(self, data, {'context':{
                    'default_model': data.model || self.context.default_model,
                    'default_res_id': data.res_id || self.context.default_res_id,
                    'default_parent_id': self.id,
                }});
            } else {
                data.record_name= (data.record_name != '' && data.record_name) || (self.parent_message && self.parent_message.record_name);
                var message = new mail.ThreadMessage(self, data, {'context':{
                    'default_model': data.model,
                    'default_res_id': data.res_id,
                    'default_parent_id': data.id,
                }});
            }

            // check if the message is already create
            for (var i in self.messages) {
                if (message.id && self.messages[i] && self.messages[i].id == message.id) {
                    self.messages[i].destroy();
                }
            }
            self.messages.push( message );

            return message;
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
        insert_message: function (message, dom_insert_after, prepend) {
            var self=this;
            if (this.options.show_compact_message > this.thread_level) {
                this.instantiate_compose_message();
                this.compose_message.do_show_compact();
            }

            this.$('.oe_view_nocontent').remove();
            if (dom_insert_after && dom_insert_after.parent()[0] == self.$el[0]) {
                message.insertAfter(dom_insert_after);
            } else if (prepend) {
                message.prependTo(self.$el);
            } else {
                message.appendTo(self.$el);
            }
            message.$el.hide().fadeIn(500);

            return message
        },
        
        /**
         *get the parent thread of the messages.
         * Each message is send to his parent object (or parent thread flat mode) for creating the object message.
         * @param : {Array} datas from calling RPC to "message_read"
         */
        switch_new_message: function (records, dom_insert_after) {
            var self=this;
            var dom_insert_after = typeof dom_insert_after == 'object' ? dom_insert_after : false;
            _(records).each(function (record) {
                var thread = self.browse_thread({
                    'id': record.parent_id, 
                    'default_return_top_thread':true
                });
                // create object and attach to the thread object
                var message = thread.create_message_object( record );
                // insert the message on dom
                thread.insert_message( message, dom_insert_after);
            });
            if (!records.length && this.options.root_thread == this) {
                this.no_message();
            }
        },

        /**
         * this method is call when the widget of a message or an expandable message is destroy
         * in this thread. The this.messages array is filter to remove this message
         */
        on_message_detroy: function (message) {

            this.messages = _.filter(this.messages, function (val) { return !val.isDestroyed(); });
            if (this.options.root_thread == this && !this.messages.length) {
                this.no_message();
            }
            return false;

        },

        /**
         * Convert a destroyed message into a expandable message
         */
        message_to_expandable: function (message) {

            if (!this.thread_level || message.isDestroyed()) {
                message.destroy();
                return false;
            }

            var messages = _.sortBy( this.messages, function (val) { return val.id; });
            var it = _.indexOf( messages, message );

            var msg_up = message.$el.prev('.oe_msg');
            var msg_down = message.$el.next('.oe_msg');
            var msg_up = msg_up.hasClass('oe_msg_expandable') ? _.find( this.messages, function (val) { return val.$el[0] == msg_up[0]; }) : false;
            var msg_down = msg_down.hasClass('oe_msg_expandable') ? _.find( this.messages, function (val) { return val.$el[0] == msg_down[0]; }) : false;

            var message_dom = [ ["id", "=", message.id] ];

            if ( msg_up && msg_up.type == "expandable" && msg_down && msg_down.type == "expandable") {
                // concat two expandable message and add this message to this dom
                msg_up.domain = mail.ChatterUtils.expand_domain( msg_up.domain );
                msg_down.domain = mail.ChatterUtils.expand_domain( msg_down.domain );

                msg_down.domain = ['|','|'].concat( msg_up.domain ).concat( message_dom ).concat( msg_down.domain );

                if ( !msg_down.max_limit ) {
                    msg_down.nb_messages += 1 + msg_up.nb_messages;
                }

                msg_up.$el.remove();
                msg_up.destroy();

                msg_down.reinit();

            } else if ( msg_up && msg_up.type == "expandable") {
                // concat preview expandable message and this message to this dom
                msg_up.domain = mail.ChatterUtils.expand_domain( msg_up.domain );
                msg_up.domain = ['|'].concat( msg_up.domain ).concat( message_dom );
                
                msg_up.nb_messages++;

                msg_up.reinit();

            } else if ( msg_down && msg_down.type == "expandable") {
                // concat next expandable message and this message to this dom
                msg_down.domain = mail.ChatterUtils.expand_domain( msg_down.domain );
                msg_down.domain = ['|'].concat( msg_down.domain ).concat( message_dom );
                
                // it's maybe a message expandable for the max limit read message
                if ( !msg_down.max_limit ) {
                    msg_down.nb_messages++;
                }
                
                msg_down.reinit();

            } else {
                // create a expandable message
                var expandable = new mail.ThreadExpandable(this, {
                    'model': message.model,
                    'parent_id': message.parent_id,
                    'nb_messages': 1,
                    'thread_level': message.thread_level,
                    'parent_id': message.parent_id,
                    'domain': message_dom,
                    'options': message.options,
                    }, {
                    'context':{
                        'default_model': message.model || this.context.default_model,
                        'default_res_id': message.res_id || this.context.default_res_id,
                        'default_parent_id': this.id,
                    }
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
        template: 'mail.Root',

        /**
         * @param {Object} parent parent
         * @param {Array} [domain]
         * @param {Object} [context] context of the thread. It should
         *   contain at least default_model, default_res_id. Please refer to
         *   the compose_message widget for more information about it.
         * @param {Object} [options]
         *...  @param {Number} [truncate_limit=250] number of character to
         *      display before having a "show more" link; note that the text
         *      will not be truncated if it does not have 110% of the parameter
         *...  @param {Boolean} [show_record_name] display the name and link for do action
         *...  @param {boolean} [show_reply_button] display the reply button
         *...  @param {boolean} [show_read_unread_button] display the read/unread button
         *...  @param {int} [display_indented_thread] number thread level to indented threads.
         *      other are on flat mode
         *...  @param {Boolean} [show_compose_message] allow to display the composer
         *...  @param {Boolean} [show_compact_message] display the compact message on the thread
         *      when the user clic on this compact mode, the composer is open
         *...  @param {Array} [message_ids] List of ids to fetch by the root thread.
         *      When you use this option, the domain is not used for the fetch root.
         *     @param {String} [no_message] Message to display when there are no message
         *     @param {Boolean} [show_link] Display partner (authors, followers...) on link or not
         *     @param {Boolean} [compose_as_todo] The root composer mark automatically the message as todo
         *     @param {Boolean} [readonly] Read only mode, hide all action buttons and composer
         */
        init: function (parent, action) {
            this._super(parent, action);
            var self = this;
            this.action = _.clone(action);
            this.domain = this.action.domain || this.action.params.domain || [];
            this.context = this.action.context || this.action.params.context || {};

            this.action.params = _.extend({
                'display_indented_thread' : -1,
                'show_reply_button' : false,
                'show_read_unread_button' : false,
                'truncate_limit' : 250,
                'show_record_name' : false,
                'show_compose_message' : false,
                'show_compact_message' : false,
                'compose_placeholder': false,
                'show_link': true,
                'view_inbox': false,
                'message_ids': undefined,
                'compose_as_todo' : false,
                'readonly' : false,
                'emails_from_on_composer': true,
            }, this.action.params);

            this.action.params.help = this.action.help || false;
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
                'options': this.action.params,
            });

            this.thread.appendTo( this.$el );

            if (this.action.params.show_compose_message) {
                this.thread.instantiate_compose_message();
                this.thread.compose_message.do_show_compact();
            }

            this.thread.message_fetch(null, null, this.action.params.message_ids);

        },

        bind_events: function () {
            $(document).scroll( _.bind(this.thread.on_scroll, this.thread) );
            $(window).resize( _.bind(this.thread.on_scroll, this.thread) );
            this.$el.resize( _.bind(this.thread.on_scroll, this.thread) );
            window.setTimeout( _.bind(this.thread.on_scroll, this.thread), 500 );
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
     * Use Help on the field to display a custom "no message loaded"
     */
    session.web.form.widgets.add('mail_thread', 'openerp.mail.RecordThread');
    mail.RecordThread = session.web.form.AbstractField.extend({
        template: 'mail.record_thread',

        init: function (parent, node) {
            this._super.apply(this, arguments);
            this.node = _.clone(node);
            this.node.params = _.extend({
                'display_indented_thread': -1,
                'show_reply_button': false,
                'show_read_unread_button': true,
                'read_action': 'unread',
                'show_record_name': false,
                'show_compact_message': 1,
            }, this.node.params);

            if (this.node.attrs.placeholder) {
                this.node.params.compose_placeholder = this.node.attrs.placeholder;
            }
            if (this.node.attrs.readonly) {
                this.node.params.readonly = this.node.attrs.readonly;
            }

            this.domain = this.node.params && this.node.params.domain || [];

            if (!this.__parentedParent.is_action_enabled('edit')) {
                this.node.params.show_link = false;
            }
        },

        start: function () {
            this._super.apply(this, arguments);
            // NB: check the actual_mode property on view to know if the view is in create mode anymore
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
        },

        _check_visibility: function () {
            this.$el.toggle(this.view.get("actual_mode") !== "create");
        },

        render_value: function () {
            var self = this;

            if (! this.view.datarecord.id || session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$('oe_mail_thread').hide();
                return;
            }

            this.node.params = _.extend(this.node.params, {
                'message_ids': this.get_value(),
                'show_compose_message': this.view.is_action_enabled('edit'),
            });
            this.node.context = {
                'mail_read_set_read': true,  // set messages as read in Chatter
                'default_res_id': this.view.datarecord.id || false,
                'default_model': this.view.model || false,
            };

            if (this.root) {
                $('<span class="oe_mail-placeholder"/>').insertAfter(this.root.$el);
                this.root.destroy();
            }
            // create and render Thread widget
            this.root = new mail.Widget(this, _.extend(this.node, {
                'domain' : (this.domain || []).concat([['model', '=', this.view.model], ['res_id', '=', this.view.datarecord.id]]),
            }));

            return this.root.replace(this.$('.oe_mail-placeholder'));
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
         */
        init: function (parent, action) {
            this._super(parent, action);

            this.action = _.clone(action);
            this.domain = this.action.params.domain || this.action.domain || [];
            this.context = _.extend(this.action.params.context || {}, this.action.context || {});

            this.defaults = {};
            for (var key in this.context) {
                if (key.match(/^search_default_/)) {
                    this.defaults[key.replace(/^search_default_/, '')] = this.context[key];
                }
            }
            this.action.params = _.extend({
                'display_indented_thread': 1,
                'show_reply_button': true,
                'show_read_unread_button': true,
                'show_compose_message': true,
                'show_record_name': true,
                'show_compact_message': this.action.params.view_mailbox ? false : 1,
                'view_inbox': false,
                'emails_from_on_composer': false,
            }, this.action.params);
        },

        start: function () {
            this._super.apply(this);
            this.bind_events();
            var searchview_loaded = this.load_searchview(this.defaults);
            if (! this.searchview.has_defaults) {
                this.message_render();
            }
        },

        /**
        * crete an object "related_menu"
        * contain the menu widget and the the sub menu related of this wall
        */
        do_reload_menu_emails: function () {
            var menu = this.__parentedParent.__parentedParent.menu;
            // return this.rpc("/web/menu/load", {'menu_id': 100}).done(function(r) {
            //     _.each(menu.data.data.children, function (val) {
            //         if (val.id == 100) {
            //             val.children = _.find(r.data.children, function (r_val) {return r_val.id == 100;}).children;
            //         }
            //     });
            //     var r = menu.data;
            // window.setTimeout(function(){menu.do_reload();}, 0);
            // });
        },

        /**
         * Load the mail.message search view
         * @param {Object} defaults ??
         */
        load_searchview: function (defaults) {
            var self = this;
            var ds_msg = new session.web.DataSetSearch(this, 'mail.message');
            this.searchview = new session.web.SearchView(this, ds_msg, false, defaults || {}, false);
            this.searchview.appendTo(this.$('.oe_view_manager_view_search'))
                .then(function () { self.searchview.on('search_data', self, self.do_searchview_search); });
            if (this.searchview.has_defaults) {
                this.searchview.ready.then(this.searchview.do_search);
            }
            return this.searchview
        },

        /**
         * Get the domains, contexts and groupbys in parameter from search
         * view, then render the filtered threads.
         * @param {Array} domains
         * @param {Array} contexts
         * @param {Array} groupbys
         */
        do_searchview_search: function (domains, contexts, groupbys) {
            var self = this;
            session.web.pyeval.eval_domains_and_contexts({
                domains: domains || [],
                contexts: contexts || [],
                group_by_seq: groupbys || []
            }).then(function (results) {
                if(self.root) {
                    $('<span class="oe_mail-placeholder"/>').insertAfter(self.root.$el);
                    self.root.destroy();
                }
                return self.message_render(results);
            });
        },

        /**
         * Create the root thread widget and display this object in the DOM
         */
        message_render: function (search) {
            var domain = this.domain.concat(search && search['domain'] ? search['domain'] : []);
            var context = _.extend(this.context, search && search['context'] ? search['context'] : {});

            this.root = new mail.Widget(this, _.extend(this.action, {
                'domain' : domain,
                'context' : context,
            }));
            return this.root.replace(this.$('.oe_mail-placeholder'));
        },

        bind_events: function () {
            var self=this;
            this.$(".oe_write_full").click(function (event) {
                event.stopPropagation();
                var action = {
                    type: 'ir.actions.act_window',
                    res_model: 'mail.compose.message',
                    view_mode: 'form',
                    view_type: 'form',
                    action_from: 'mail.ThreadComposeMessage',
                    views: [[false, 'form']],
                    target: 'new',
                    context: {
                    },
                };
                session.client.action_manager.do_action(action);
            });
            this.$(".oe_write_onwall").click(function (event) { self.root.thread.on_compose_message(event); });
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
        template:'mail.ComposeMessageTopButton',

        start: function () {
            this.$('button').on('click', this.on_compose_message );
            this._super();
        },

        on_compose_message: function (event) {
            event.stopPropagation();
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

    session.web.UserMenu.include({
        do_update: function(){
            var self = this;
            this._super.apply(this, arguments);
            this.update_promise.then(function() {
                var mail_button = new session.web.ComposeMessageTopButton();
                mail_button.appendTo(session.webclient.$el.find('.oe_systray'));
            });
        },
    });
};
