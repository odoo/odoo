openerp.mail = function(session) {
    var _t = session.web._t,
       _lt = session.web._lt;

    var mail = session.mail = {};

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
            if (action.res_model == 'mail.compose.message' && this.fields && this.fields.message_ids && this.fields.message_ids.view.get("actual_mode") != 'create') {
                var record_thread = this.fields.message_ids;
                var thread = record_thread.thread;
                thread.instantiate_composition_form('comment', true, false, 0, action.context);
                return false;
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
     * This class holds a few tools method that will be used by
     * the various Chatter widgets.
     */

    mail.ChatterUtils = {

        /**
        * mail_int_mapping: structure to keep a trace of internal links mapping
        *      mail_int_mapping['model'] = {
        *          'name_get': [[id,label], [id,label], ...]
        *          'fetch_ids': [id, id, ...] } */
        //var mail_int_mapping = {};
        
        /**
        * mail_msg_struct: structure to orrganize chatter messages
        */
        //var mail_msg_struct = {}; // TODO: USE IT OR NOT :)

        /* generic chatter events binding */
        bind_events: function(widget) {
            // event: click on an internal link to a document: model, login
            widget.$element.delegate('a.oe_mail_internal_link', 'click', function (event) {
                event.preventDefault();
                // lazy implementation: fetch data and try to redirect
                if (! event.srcElement.dataset.resModel) return false;
                else var res_model = event.srcElement.dataset.resModel;
                var res_login = event.srcElement.dataset.resLogin;
                if (! res_login) return false;
                var ds = new session.web.DataSet(widget, res_model);
                var defer = ds.call('search', [[['login', '=', res_login]]]).pipe(function (records) {
                    if (records[0]) {
                        widget.do_action({ type: 'ir.actions.act_window', res_model: res_model, res_id: parseInt(records[0]), views: [[false, 'form']]});
                    }
                    else return false;
                });
            });
        },

        /** get an image in /web/binary/image?... */
        get_image: function(session_prefix, session_id, model, field, id) {
            return session_prefix + '/web/binary/image?session_id=' + session_id + '&model=' + model + '&field=' + field + '&id=' + (id || '');
        },

        /** checks if tue current user is the message author */
        is_author: function (widget, message_user_id) {
            return (widget.session && widget.session.uid != 0 && widget.session.uid == message_user_id);
        },

        /**
        * Add records to comments_structure array
        * @param {Array} records records from mail.message sorted by date desc
        * @returns {Object} cs comments_structure: dict
        *       cs.model_to_root_ids = {model: [root_ids], }
        *       cs.new_root_ids = [new_root_ids]
        *       cs.root_ids = [root_ids]
        *       cs.msgs = {record.id: record,}
        *       cs.tree_struct = {record.id: {
        *           'level': record_level in hierarchy, 0 is root,
        *           'msg_nbr': number of childs,
        *           'direct_childs': [msg_ids],
        *           'all_childs': [msg_ids],
        *           'for_thread_msgs': [records],
        *           'ancestors': [msg_ids], } }
        */
        records_struct_add_records: function(cs, records, parent_id) {
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
        },

        /* copy cs.new_root_ids into cs.root_ids */
        records_struct_update_after_display: function(cs) {
            // update TODO
            cs['root_ids'] = _.union(cs['root_ids'], cs['new_root_ids']);
            cs['new_root_ids'] = [];
            return cs;
        },

        /**
         *    CONTENT MANIPULATION
         * 
         * Regular expressions
         * - (^|\s)@((\w|@|\.)*): @login@log.log, supports inner '@' for
         *   logins that are emails
         *      1. '(void)'
         *      2. login@log.log
         * - (^|\s)\[(\w+).(\w+),(\d)\|*((\w|[@ .,])*)\]: [ir.attachment,3|My Label],
         *   for internal links to model ir.attachment, id=3, and with
         *   optional label 'My Label'. Note that having a '|Label' is not
         *   mandatory, because the regex should still be correct.
         *      1. '(void)'
         *      2. 'ir'
         *      3. 'attachment'
         *      4. '3'
         *      5. 'My Label'
         */

        /** Removes html tags, except b, em, br, ul, li */
        do_text_remove_html_tags: function (string) {
            var html = $('<div/>').text(string.replace(/\s+/g, ' ')).html().replace(new RegExp('&lt;(/)?(b|em|br|br /|ul|li|div)\\s*&gt;', 'gi'), '<$1$2>');
            return html;
        },
        
        /** Replaces line breaks by html line breaks (br) */
        do_text_nl2br: function (str, is_xhtml) {   
            var break_tag = (is_xhtml || typeof is_xhtml === 'undefined') ? '<br />' : '<br>';    
            return (str + '').replace(/([^>\r\n]?)(\r\n|\n\r|\r|\n)/g, '$1'+ break_tag +'$2');
        },

        /* Add a prefix before each new line of the original string */
        do_text_quote: function (str, prefix) {
            return str.replace(/([^>\r\n]?)(\r\n|\n\r|\r|\n)/g, '$1'+ break_tag +'$2' + prefix || '> ');
        },

        /**
         * Replaces some expressions
         * - @login - shorcut to link to a res.user, given its login
         * - [ir.attachment,3|My Label] - shortcut to an internal
         *   document
         * - :name - shortcut to an image
         */
        do_replace_expressions: function (string) {
            var self = this;
            var icon_list = ['al', 'pinky']
            /* shortcut to user: @login */
            var regex_login = new RegExp(/(^|\s)@((\w|@|\.)*)/g);
            var regex_res = regex_login.exec(string);
            while (regex_res != null) {
                var login = regex_res[2];
                string = string.replace(regex_res[0], regex_res[1] + '<a href="#" class="oe_mail_internal_link" data-res-model="res.users" data-res-login = ' + login + '>@' + login + '</a>');
                regex_res = regex_login.exec(string);
            }
            /* shortcut for internal document */
            var regex_login = new RegExp(/(^|\s)\[(\w+).(\w+),(\d)\|*((\w|[@ .,])*)\]/g);
            var regex_res = regex_login.exec(string);
            while (regex_res != null) {
                var res_model = regex_res[2] + '.' + regex_res[3];
                var res_id = regex_res[4];
                if (! regex_res[5]) {
                    var label = res_model + ':' + res_id }
                else {
                    var label = regex_res[5];
                }
                string = string.replace(regex_res[0], regex_res[1] + '<a href="#model=' + res_model + '&id=' + res_id + '>' + label + '</a>');
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
         * Checks a string to find an expression that will be replaced
         * by an internal link and requiring a name_get to replace
         * the expression.
         * :param mapping: structure to keep a trace of internal links mapping
         *                  mapping['model'] = {
         *                      name_get': [[id,label], [id,label], ...]
         *                      'to_fetch_ids': [id, id, ...]
         *                  }
         * CURRENTLY NOT IMPLEMENTED */
        do_check_for_name_get_mapping: function(string, mapping) {
            /* shortcut to user: @login */
            //var regex_login = new RegExp(/(^|\s)@((\w|@|\.)*)/g);
            //var regex_res = regex_login.exec(string);
            //while (regex_res != null) {
                //var login = regex_res[2];
                //if (! ('res.users' in this.map_hash)) { this.map_hash['res.users']['name'] = []; }
                //this.map_hash['res.users']['login'].push(login);
                //regex_res = regex_login.exec(string);
            //}
            /* document link with name_get: [res.model,name] */
            /* internal link with id: [res.model,id], or [res.model,id|display_name] */
            //var regex_intlink = new RegExp(/(^|\s)#(\w*[a-zA-Z_]+\w*)\.(\w+[a-zA-Z_]+\w*),(\w+)/g);
            //regex_res = regex_intlink.exec(string);
            //while (regex_res != null) {
                //var res_model = regex_res[2] + '.' + regex_res[3];
                //var res_name = regex_res[4];
                //if (! (res_model in this.map_hash)) { this.map_hash[res_model]['name'] = []; }
                //this.map_hash[res_model]['name'].push(res_name);
                //regex_res = regex_intlink.exec(string);
            //}
        },
        
        /**
         * Updates the mapping; check for to_fetch_ids for each recorded
         * model, and perform a name_get to update the mapping.
         * CURRENTLY NOT IMPLEMENTED */
        do_update_name_get_mapping: function(mapping) {
        },
    };


    /**
     * ------------------------------------------------------------
     * ComposeMessage widget
     * ------------------------------------------------------------
     * 
     * This widget handles the display of a form to compose a new message.
     * This form is an OpenERP form_view, build on a mail.compose.message
     * wizard.
     */

    mail.ComposeMessage = session.web.Widget.extend({
        template: 'mail.compose_message',
        
        /**
         * @param {Object} parent parent
         * @param {Object} [params]
         * @param {String} [params.res_model] res_model of document [REQUIRED]
         * @param {Number} [params.res_id] res_id of record [REQUIRED]
         * @param {Number} [params.email_mode] true/false, tells whether
         *      we are in email sending mode
         * @param {Number} [params.formatting] true/false, tells whether
         *      we are in advance formatting mode
         * @param {String} [params.model] mail.compose.message.mode (see
         *      composition wizard)
         * @param {Number} [params.msg_id] id of a message in case we are in
         *      reply mode
         */
        init: function(parent, params) {
            var self = this;
            this._super(parent);
            // options
            this.params = params || {};
            this.params.context = params.context || {};
            this.params.email_mode = params.email_mode || false;
            this.params.formatting = params.formatting || false;
            this.params.mode = params.mode || 'comment';
            this.params.form_xml_id = params.form_xml_id || 'email_compose_message_wizard_form_chatter';
            this.params.form_view_id = false;
            if (this.params.mode == 'reply') {
                this.params.active_id = this.params.msg_id;
            } else {
                this.params.active_id = this.params.res_id;
            }
            this.email_mode = false;
            this.formatting = false;
        },

        /**
         * Reinitialize the widget field values to the default values. The
         * purpose is to avoid to destroy and re-build a form view. Default
         * values are therefore given as for an onchange. */
        reinit: function() {
            var self = this;
            if (! this.form_view) return;
            var call_defer = this.ds_compose.call('default_get', [['subject', 'body_text', 'body_html', 'dest_partner_ids'], this.ds_compose.get_context()]).then(
                function (result) {
                    self.form_view.on_processed_onchange({'value': result}, []);
                });
            return call_defer;
        },

        /**
         * Override-hack of do_action: clean the form */
        do_action: function(action, on_close) {
            // this.init_comments();
            return this._super(action, on_close);
        },

        /**
         * Widget start function
         * - builds and initializes the form view */
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            // customize display: add avatar, clean previous content
            var user_avatar = mail.ChatterUtils.get_image(this.session.prefix,
                this.session.session_id, 'res.users', 'image_small', this.session.uid);
            this.$element.find('img.oe_mail_icon').attr('src', user_avatar);
            this.$element.find('div.oe_mail_msg_content').empty();
            // create a context for the default_get of the compose form
            var widget_context = {
                'active_model': this.params.res_model,
                'active_id': this.params.active_id,
                'mail.compose.message.mode': this.params.mode,
            };
            var context = _.extend({}, this.params.context, widget_context);
            this.ds_compose = new session.web.DataSetSearch(this, 'mail.compose.message', context);
            // find the id of the view to display in the chatter form
            var data_ds = new session.web.DataSetSearch(this, 'ir.model.data');
            var deferred_form_id =data_ds.call('get_object_reference', ['mail', this.params.form_xml_id]).then( function (result) {
                if (result) {
                    self.params.form_view_id = result[1];
                }
            }).pipe(this.proxy('create_form_view'));
            return deferred_form_id;
        },

        /**
         * Create a FormView, then append it to the to widget DOM. */
        create_form_view: function () {
            var self = this;
            // destroy previous form_view if any
            if (this.form_view) { this.form_view.destroy(); }
            // create the FormView
            this.form_view = new session.web.FormView(this, this.ds_compose, this.params.form_view_id, {
                action_buttons: false,
                pager: false,
                initial_mode: 'edit',
                disable_autofocus: true,
            });
            // add the form, bind events, activate the form
            var msg_node = this.$element.find('div.oe_mail_msg_content');
            return $.when(this.form_view.appendTo(msg_node)).pipe(function() {
                self.bind_events();
                self.form_view.do_show();
                if (self.params.email_mode) { self.toggle_email_mode(); }
                if (self.params.formatting) { self.toggle_formatting_mode(); }
            });
        },

        destroy: function() {
            this._super.apply(this, arguments);
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            this.$element.find('button.oe_form_button').click(function (event) {
                event.preventDefault();
            });
            // event: click on 'Send an Email' link that toggles the form for
            // sending an email (partner_ids)
            this.$element.find('a.oe_mail_compose_message_email').click(function (event) {
                event.preventDefault();
                self.toggle_email_mode();
            });
            // event: click on 'Formatting' icon-link that toggles the advanced
            // formatting options for writing a message (subject, body_html)
            this.$element.find('a.oe_mail_compose_message_formatting').click(function (event) {
                event.preventDefault();
                self.toggle_formatting_mode();
            });
            // event: click on 'Attachment' icon-link that opens the dialog to
            // add an attachment.
            this.$element.find('a.oe_mail_compose_message_attachment').click(function (event) {
                event.preventDefault();
                // not yet implemented
                self.set_body_value('attachment', 'attachment');
            });
            // event: click on 'Checklist' icon-link that toggles the options
            // for adding checklist.
            this.$element.find('a.oe_mail_compose_message_checklist').click(function (event) {
                event.preventDefault();
                // not yet implemented
                self.set_body_value('checklist', 'checklist');
            });
        },

        /**
         * Toggle the formatting mode. */
        toggle_formatting_mode: function() {
            var self = this;
            this.formatting = ! this.formatting;
            // calls onchange
            var call_defer = this.ds_compose.call('onchange_formatting', [[], this.formatting, this.params.res_model, this.params.res_id]).then(
                function (result) {
                    self.form_view.on_processed_onchange(result, []);
                });
            // update context of datasetsearch
            this.ds_compose.context.formatting = this.formatting;
            // toggle display
            this.$element.find('span.oe_mail_compose_message_subject').toggleClass('oe_mail_compose_message_invisible');
            this.$element.find('div.oe_mail_compose_message_body_text').toggleClass('oe_mail_compose_message_invisible');
            this.$element.find('div.oe_mail_compose_message_body_html').toggleClass('oe_mail_compose_message_invisible');
        },

        /**
         * Toggle the email mode. */
        toggle_email_mode: function() {
            var self = this;
            this.email_mode = ! this.email_mode;
            // calls onchange
            var call_defer = this.ds_compose.call('onchange_email_mode', [[], this.email_mode, this.params.res_model, this.params.res_id]).then(
                function (result) {
                    self.form_view.on_processed_onchange(result, []);
                });
            // update context of datasetsearch
            this.ds_compose.context.email_mode = this.email_mode;
            // update 'Post' button -> 'Send'
            // update 'Send an Email' link -> 'Post a comment'
            if (this.email_mode) {
                this.$element.find('button.oe_mail_compose_message_button_send').html('<span>Send</span>');
                this.$element.find('a.oe_mail_compose_message_email').html('Comment');
            } else {
                this.$element.find('button.oe_mail_compose_message_button_send').html('<span>Post</span>');
                this.$element.find('a.oe_mail_compose_message_email').html('Send an Email');
            }
            // toggle display
            this.$element.find('div.oe_mail_compose_message_partner_ids').toggleClass('oe_mail_compose_message_invisible');
        },

        /**
         * Update the values of the composition form; with possible different
         * values for body_text and body_html. */
        set_body_value: function(body_text, body_html) {
            this.form_view.fields.body_text.set_value(body_text);
            this.form_view.fields.body_html.set_value(body_html);
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
     * This widget has 2 ways of initialization, either you give records
     * to be rendered, either it will fetch [limit] messages related to
     * [res_model]:[res_id].
     */

    mail.Thread = session.web.Widget.extend({
        template: 'mail.thread',

        /**
         * @param {Object} parent parent
         * @param {Object} [params]
         * @param {String} [params.res_model] res_model of document [REQUIRED]
         * @param {Number} [params.res_id] res_id of record [REQUIRED]
         * @param {Number} [params.uid] user id [REQUIRED]
         * @param {Bool}   [params.parent_id=false] parent_id of message
         * @param {Number} [params.thread_level=0] number of levels in the thread
         *      (only 0 or 1 currently)
         * @param {Bool}   [params.is_wall=false] thread is displayed in the wall
         * @param {Number} [params.msg_more_limit=150] number of character to
         *      display before having a "show more" link; note that the text
         *      will not be truncated if it does not have 110% of the parameter
         *      (ex: 110 characters needed to be truncated and be displayed as
         *      a 100-characters message)
         * @param {Number} [params.limit=100] maximum number of messages to fetch
         * @param {Number} [params.offset=0] offset for fetching messages
         * @param {Number} [params.records=null] records to show instead of fetching messages
         */
        init: function(parent, params) {
            this._super(parent);
            // options
            this.params = params;
            this.params.parent_id = this.params.parent_id || false;
            this.params.thread_level = this.params.thread_level || 0;
            this.params.is_wall = this.params.is_wall || (this.params.records != undefined) || false;
            this.params.msg_more_limit = this.params.msg_more_limit || 250;
            this.params.limit = this.params.limit || 100;
            // this.params.limit = 3; // tmp for testing
            this.params.offset = this.params.offset || 0;
            this.params.records = this.params.records || null;
            // datasets and internal vars
            this.ds = new session.web.DataSetSearch(this, this.params.res_model);
            this.ds_users = new session.web.DataSetSearch(this, 'res.users');
            this.ds_msg = new session.web.DataSetSearch(this, 'mail.message');
            this.comments_structure = {'root_ids': [], 'new_root_ids': [], 'msgs': {}, 'tree_struct': {}, 'model_to_root_ids': {}};
            // display customization vars
            this.display = {};
            this.display.show_post_comment = this.params.show_post_comment || false;
            this.display.show_reply = (this.params.thread_level > 0 && this.params.is_wall);
            this.display.show_delete = ! this.params.is_wall;
            this.display.show_hide = this.params.is_wall;
            this.display.show_reply_by_email = ! this.params.is_wall;
            this.display.show_more = (this.params.thread_level == 0);
        },
        
        start: function() {
            this._super.apply(this, arguments);
            // add events
            this.bind_events();
            // display user, fetch comments
            this.display_current_user();
            if (this.params.records) var display_done = this.display_comments_from_parameters(this.params.records);
            else var display_done = this.init_comments();
            // customize display
            $.when(display_done).then(this.proxy('do_customize_display'));            
            // add message composition form view
            if (this.display.show_post_comment) {
                var compose_done = this.instantiate_composition_form();
            }
            return display_done && compose_done;
        },

        //Mail vote Functionality...
        add_vote_event: function(element){
            self = this;
            vote_img = element.find('.oe_mail_msg_vote_like');
            if (vote_img)
                vote_img.click(function(){
                    self.subscribe_vote($(this).attr('data-id'));
                });
            return
        },
        
        find_parent_element: function(name, message_id){
            parent_element = false;
            _.each($(name), function(element){
                if ($(element).attr("data-id") == message_id){
                    parent_element = element;
                }
            });
            return parent_element;
         },

        render_vote: function(message_id){
            var self = this;
            var mail_vote = new session.web.DataSetSearch(self, 'mail.vote', self.session.context, [['msg_id','=',parseInt(message_id)]]);
            mail_vote.read_slice(['user_id']).then(function(result){
                vote_count = result.length;
                is_vote_liked = false;
                _.each(result, function(vote){
                    if (self.session.uid == vote.user_id[0]){
                        is_vote_liked = true;
                    }
                });
                parent_element = self.find_parent_element(".oe_mail_msg_vote", message_id);
                vote_element = session.web.qweb.render('VoteDisplay', {'msg_id': message_id, 'vote_count': vote_count, 'is_vote_liked': is_vote_liked});
                $(parent_element).html(vote_element);
                self.add_vote_event($(parent_element));
            });
        },
        
        subscribe_vote: function(message_id){
            var self = this;
            this.mail_message = new session.web.DataSet(this, 'mail.message');
            return this.mail_message.call('vote_toggle', [[parseInt(message_id)]]).then(function(result){
                self.render_vote(message_id);
            });
        },
         
        /**
         * Override-hack of do_action: automatically reload the chatter.
         * Normally it should be called only when clicking on 'Post/Send'
         * in the composition form. */
        do_action: function(action, on_close) {
            this.init_comments();
            if (this.compose_message_widget) {
                this.compose_message_widget.reinit(); }
            return this._super(action, on_close);
        },

        instantiate_composition_form: function(mode, email_mode, formatting, msg_id, context) {
            if (this.compose_message_widget) {
                this.compose_message_widget.destroy();
            }
            this.compose_message_widget = new mail.ComposeMessage(this, {
                'extended_mode': false, 'uid': this.params.uid, 'res_model': this.params.res_model,
                'res_id': this.params.res_id, 'mode': mode || 'comment', 'msg_id': msg_id,
                'email_mode': email_mode || false, 'formatting': formatting || false,
                'context': context || false } );
            var composition_node = this.$element.find('div.oe_mail_thread_action');
            composition_node.empty();
            var compose_done = this.compose_message_widget.appendTo(composition_node);
            return compose_done;
        },

        do_customize_display: function() {
            if (this.display.show_post_comment) { this.$element.find('div.oe_mail_thread_action').eq(0).show(); }
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function() {
            var self = this;
            // generic events from Chatter Mixin
            mail.ChatterUtils.bind_events(this);
            // event: click on 'more' at bottom of thread
            this.$element.find('button.oe_mail_button_more').click(function () {
                self.do_more();
            });
            // event: writing in basic textarea of composition form (quick reply)
            this.$element.find('textarea.oe_mail_compose_textarea').keyup(function (event) {
                var charCode = (event.which) ? event.which : window.event.keyCode;
                if (event.shiftKey && charCode == 13) { this.value = this.value+"\n"; }
                else if (charCode == 13) { return self.do_comment(); }
            });
            // event: click on 'Reply' in msg
            this.$element.find('div.oe_mail_thread_display').delegate('a.oe_mail_msg_reply', 'click', function (event) {
                var act_dom = $(this).parents('div.oe_mail_thread_display').find('div.oe_mail_thread_action:first');
                act_dom.toggle();
                event.preventDefault();
            });
            // event: click on 'attachment(s)' in msg
            this.$element.delegate('a.oe_mail_msg_view_attachments', 'click', function (event) {
                var act_dom = $(this).parent().parent().parent().find('.oe_mail_msg_attachments');
                act_dom.toggle();
                event.preventDefault();
            });
            // event: click on 'Delete' in msg side menu
            this.$element.find('div.oe_mail_thread_display').delegate('a.oe_mail_msg_delete', 'click', function (event) {
                if (! confirm(_t("Do you really want to delete this message?"))) { return false; }
                var msg_id = event.srcElement.dataset.id;
                if (! msg_id) return false;
                var call_defer = self.ds_msg.unlink([parseInt(msg_id)]);
                $(event.srcElement).parents('li.oe_mail_thread_msg').eq(0).hide();
                if (self.params.thread_level > 0) {
                    $(event.srcElement).parents('.oe_mail_thread').eq(0).hide();
                }
                event.preventDefault();
                return call_defer;
            });
            // event: click on 'Hide' in msg side menu
            this.$element.find('div.oe_mail_thread_display').delegate('a.oe_mail_msg_hide', 'click', function (event) {
                if (! confirm(_t("Do you really want to hide this thread ?"))) { return false; }
                var msg_id = event.srcElement.dataset.id;
                if (! msg_id) return false;
                var call_defer = self.ds.call('message_remove_pushed_notifications', [[self.params.res_id], [parseInt(msg_id)], true]);
                $(event.srcElement).parents('li.oe_mail_thread_msg').eq(0).hide();
                if (self.params.thread_level > 0) {
                    $(event.srcElement).parents('.oe_mail_thread').eq(0).hide();
                }
                event.preventDefault();
                return call_defer;
            });
            // event: click on "Reply" in msg side menu (email style)
            this.$element.find('div.oe_mail_thread_display').delegate('a.oe_mail_msg_reply_by_email', 'click', function (event) {
                var msg_id = event.srcElement.dataset.msg_id;
                var email_mode = (event.srcElement.dataset.type == 'email');
                var formatting = (event.srcElement.dataset.formatting == 'html');
                if (! msg_id) return false;
                self.instantiate_composition_form('reply', email_mode, formatting, msg_id);
                event.preventDefault();
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
            var defer = this.ds.call('message_read', [[this.params.res_id], (this.params.thread_level > 0), (this.comments_structure['root_ids']),
                                    (limit+1) || (this.params.limit+1), offset||this.params.offset, domain||undefined ]).then(function (records) {
                if (records.length <= self.params.limit) self.display.show_more = false;
                // else { self.display.show_more = true; records.pop(); }
                // else { self.display.show_more = true; records.splice(0, 1); }
                else { self.display.show_more = true; }
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
            // sort the records
            mail.ChatterUtils.records_struct_add_records(this.comments_structure, records, this.params.parent_id);
            //build attachments download urls and compute time-relative from dates
            for (var k in records) {
                records[k].timerelative = $.timeago(records[k].date);
                if (records[k].attachments) {
                    for (var l in records[k].attachments) {
                        var url = self.session.origin + '/web/binary/saveas?session_id=' + self.session.session_id + '&model=ir.attachment&field=datas&filename_field=datas_fname&id='+records[k].attachments[l].id;
                        records[k].attachments[l].url = url;
                    }
                }
            }
            _(records).each(function (record) {
                //Render Votes.
                 self.render_vote(record.id);
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
            mail.ChatterUtils.records_struct_update_after_display(this.comments_structure);
            // update offset for "More" buttons
            if (this.params.thread_level == 0) this.params.offset += records.length;
        },

        /** Displays a record, performs text/link formatting */
        display_comment: function (record) {
            record.body = mail.ChatterUtils.do_text_nl2br($.trim(record.body), true);
            // if (record.type == 'email' && record.state == 'received') {
            if (record.type == 'email') {
                record.mini_url = ('/mail/static/src/img/email_icon.png');
            } else {
                record.mini_url = mail.ChatterUtils.get_image(this.session.prefix, this.session.session_id, 'res.users', 'image_small', record.user_id[0]);
            }
            // body text manipulation
            if (record.subtype == 'plain') {
                record.body = mail.ChatterUtils.do_text_remove_html_tags(record.body);
            }
            record.body = mail.ChatterUtils.do_replace_expressions(record.body);
            // format date according to the user timezone
            record.date = session.web.format_value(record.date, {type:"datetime"});
            // is the user the author ?
            record.is_author = mail.ChatterUtils.is_author(this, record.user_id[0]);
            // render
            var rendered = session.web.qweb.render('mail.thread.message', {'record': record, 'thread': this, 'params': this.params, 'display': this.display});
            // expand feature
            $(rendered).appendTo(this.$element.children('div.oe_mail_thread_display:first'));
            this.$element.find('div.oe_mail_msg_record_body').expander({
                slicePoint: this.params.msg_more_limit,
                expandText: 'read more',
                userCollapseText: '[^]',
                detailClass: 'oe_mail_msg_tail',
                moreClass: 'oe_mail_expand',
                lessClass: 'oe_mail_reduce',
                });
        },

        display_current_user: function () {
            var avatar = mail.ChatterUtils.get_image(this.session.prefix, this.session.session_id, 'res.users', 'image_small', this.params.uid);
            return this.$element.find('img.oe_mail_icon').attr('src', avatar);
        },
        
        do_comment: function () {
            var comment_node = this.$element.find('textarea');
            var body_text = comment_node.val();
            comment_node.val('');
            return this.ds.call('message_append_note', [[this.params.res_id], '', body_text, this.params.parent_id, 'comment', 'plain']).then(
                this.proxy('init_comments'));
        },
        
        /**
         * Create a domain to fetch new comments according to
         * comment already present in comments_structure
         * @param {Object} comments_structure (see chatter utils)
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
    });


    /** 
     * ------------------------------------------------------------
     * mail_thread Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of the Chatter on documents.
     */

    /* Add mail_thread widget to registry */
    session.web.form.widgets.add('mail_thread', 'openerp.mail.RecordThread');

    /** mail_thread widget: thread of comments */
    mail.RecordThread = session.web.form.AbstractField.extend({
        // QWeb template to use when rendering the object
        template: 'mail.record_thread',

       init: function() {
            this._super.apply(this, arguments);
            this.params = this.get_definition_options();
            this.params.thread_level = this.params.thread_level || 0;
            this.params.see_subscribers = true;
            this.params.see_subscribers_options = this.params.see_subscribers_options || false;
            this.thread = null;
            this.ds = new session.web.DataSet(this, this.view.model);
            this.ds_users = new session.web.DataSet(this, 'res.users');
        },
        
        start: function() {
            var self = this;
            
            // NB: all the widget should be modified to check the actual_mode property on view, not use
            // any other method to know if the view is in create mode anymore
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
            
            mail.ChatterUtils.bind_events(this);
            this.$element.find('button.oe_mail_button_followers').click(function () { self.do_toggle_followers(); });
            if (! this.params.see_subscribers_options) {
                this.$element.find('button.oe_mail_button_followers').hide(); }
            this.$element.find('button.oe_mail_button_follow').click(function () { self.do_follow(); })
                .mouseover(function () { $(this).html('Follow').removeClass('oe_mail_button_mouseout').addClass('oe_mail_button_mouseover'); })
                .mouseleave(function () { $(this).html('Not following').removeClass('oe_mail_button_mouseover').addClass('oe_mail_button_mouseout'); });
            this.$element.find('button.oe_mail_button_unfollow').click(function () { self.do_unfollow(); })
                .mouseover(function () { $(this).html('Unfollow').removeClass('oe_mail_button_mouseout').addClass('oe_mail_button_mouseover'); })
                .mouseleave(function () { $(this).html('Following').removeClass('oe_mail_button_mouseover').addClass('oe_mail_button_mouseout'); });
            this.reinit();
        },
        
        _check_visibility: function() {
            this.$element.toggle(this.view.get("actual_mode") !== "create");
        },
        
        destroy: function () {
            this._super.apply(this, arguments);
        },
        
        reinit: function() {
            this.params.see_subscribers = true;
            this.params.see_subscribers_options = this.params.see_subscribers_options || false;
            this.$element.find('button.oe_mail_button_followers').html('Hide followers')
            this.$element.find('button.oe_mail_button_follow').hide();
            this.$element.find('button.oe_mail_button_unfollow').hide();
        },
        
        set_value: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.reinit();
            if (! this.view.datarecord.id ||
                session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$element.find('.oe_mail_thread').hide();
                return;
            }
            // fetch followers
            var fetch_sub_done = this.fetch_subscribers();
            // create and render Thread widget
            this.$element.find('div.oe_mail_recthread_main').empty();
            if (this.thread) this.thread.destroy();
            this.thread = new mail.Thread(this, {'res_model': this.view.model, 'res_id': this.view.datarecord.id, 'uid': this.session.uid,
                                                'thread_level': this.params.thread_level, 'show_post_comment': true, 'limit': 15});
            var thread_done = this.thread.appendTo(this.$element.find('div.oe_mail_recthread_main'));
            return fetch_sub_done && thread_done;
        },
        
        fetch_subscribers: function () {
            return this.ds.call('message_read_subscribers', [[this.view.datarecord.id]]).then(this.proxy('display_subscribers'));
        },
        
        display_subscribers: function (records) {
            var self = this;
            this.is_subscriber = false;
            var user_list = this.$element.find('ul.oe_mail_followers_display').empty();
            this.$element.find('div.oe_mail_recthread_followers h4').html('Followers (' + records.length + ')');
            _(records).each(function (record) {
                if (record.id == self.session.uid) { self.is_subscriber = true; }
                record.avatar_url = mail.ChatterUtils.get_image(self.session.prefix, self.session.session_id, 'res.users', 'image_small', record.id);
                $(session.web.qweb.render('mail.record_thread.subscriber', {'record': record})).appendTo(user_list);
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
            this.params.see_subscribers = ! this.params.see_subscribers;
            if (this.params.see_subscribers) { this.$element.find('button.oe_mail_button_followers').html('Hide followers'); }
            else { this.$element.find('button.oe_mail_button_followers').html('Show followers'); }
            this.$element.find('div.oe_mail_recthread_followers').toggle();
        },
    });


    /** 
     * ------------------------------------------------------------
     * WallView Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of the Chatter on the Wall.
     */

    /* Add WallView widget to registry */
    session.web.client_actions.add('mail.wall', 'session.mail.Wall');

    /* WallView widget: a wall of messages */
    mail.Wall = session.web.Widget.extend({
        template: 'mail.wall',

        /**
         * @param {Object} parent parent
         * @param {Object} [params]
         * @param {Number} [params.limit=20] number of messages to show and fetch
         * @param {Number} [params.search_view_id=false] search view id for messages
         * @var {Array} comments_structure (see chatter utils)
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
            this.display_current_user();
            // add events
            this.add_event_handlers();
            // load mail.message search view
            var search_view_ready = this.load_search_view(this.params.search_view_id, {}, false);
            // load composition form
            var compose_done = this.instantiate_composition_form();
            // fetch first threads
            var comments_ready = this.init_and_fetch_comments(this.params.limit, 0);
            return (search_view_ready && comments_ready && compose_done);
        },

        /**
         * Override-hack of do_action: automatically reload the chatter.
         * Normally it should be called only when clicking on 'Post/Send'
         * in the composition form. */
        do_action: function(action, on_close) {
            this.init_and_fetch_comments();
            if (this.compose_message_widget) {
                this.compose_message_widget.reinit(); }
            return this._super(action, on_close);
        },

        destroy: function () {
            this._super.apply(this, arguments);
        },

        instantiate_composition_form: function(mode, msg_id) {
            if (this.compose_message_widget) {
                this.compose_message_widget.destroy();
            }
            this.compose_message_widget = new mail.ComposeMessage(this, {
                'extended_mode': false, 'uid': this.session.uid, 'res_model': 'res.users',
                'res_id': this.session.uid, 'mode': mode || 'comment', 'msg_id': msg_id });
            var composition_node = this.$element.find('div.oe_mail_wall_action');
            composition_node.empty();
            var compose_done = this.compose_message_widget.appendTo(composition_node);
            return compose_done;
        },

        /** Add events */
        add_event_handlers: function () {
            var self = this;
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

        display_current_user: function () {
            //return this.$element.find('img.oe_mail_msg_image').attr('src', this.thread_get_avatar('res.users', 'avatar', this.session.uid));
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
            this.$element.find('ul.oe_mail_wall_threads').empty();
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
            return this.ds_thread.call('message_get_pushed_messages', 
                [[this.session.uid], true, [], (limit || 0), (offset || 0), fetch_domain, fetch_context]).then(this.proxy('display_comments'));
        },

        /**
         * @param {Array} records records to show in threads
         */
        display_comments: function (records) {
            var self = this;
            this.do_update_show_more(records.length >= self.params.limit);
            mail.ChatterUtils.records_struct_add_records(this.comments_structure, records, false);
            _(this.comments_structure['new_root_ids']).each(function (root_id) {
                var records = self.comments_structure.tree_struct[root_id]['for_thread_msgs'];
                var model_name = self.comments_structure.msgs[root_id]['model'];
                var res_id = self.comments_structure.msgs[root_id]['res_id'];
                var render_res = session.web.qweb.render('mail.Wall_thread_container', {});
                $('<li class="oe_mail_wall_thread">').html(render_res).appendTo(self.$element.find('ul.oe_mail_wall_threads'));
                var thread = new mail.Thread(self, {
                    'res_model': model_name, 'res_id': res_id, 'uid': self.session.uid, 'records': records,
                    'parent_id': false, 'thread_level': self.params.thread_level, 'show_hide': true, 'is_wall': true}
                    );
                self.thread_list.push(thread);
                return thread.appendTo(self.$element.find('li.oe_mail_wall_thread:last'));
            });
            // update TODO
            this.comments_structure['root_ids'] = _.union(this.comments_structure['root_ids'], this.comments_structure['new_root_ids']);
            this.comments_structure['new_root_ids'] = [];
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
    });
};
