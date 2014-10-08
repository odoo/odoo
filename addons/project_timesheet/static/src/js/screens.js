function odoo_project_timesheet_screens(project_timesheet) {

    var QWeb = openerp.qweb,
    _t = openerp._t;

    //Move it in lib code, may be in openerpframework.js
    $.fn.openerpClass = function(additionalClass) {
        // This plugin should be applied on top level elements
        additionalClass = additionalClass || '';
        if (!!$.browser.msie) {
            additionalClass += ' openerp_ie';
        }
        return this.each(function() {
            $(this).addClass('openerp ' + additionalClass);
        });
    };

    var opened_modal = [];
    project_timesheet.Dialog = openerp.Widget.extend({
        //template: "ProjectTimesheetDialog",
        init: function(parent, options, content) {
            this._super();
            this.content_to_set = content;
            this.dialog_options = {
                destroy_on_close: true,
                size: 'large', //'medium', 'small'
                buttons: null,
            };
            if (options) {
                _.extend(this.dialog_options, options);
            }
            this.on("closing", this, this._closing);
            this.$buttons = $('<div class="modal-footer"><span class="oe_dialog_custom_buttons"/></div>');
        },
        renderElement: function() {
            if (this.content_to_set) {
                this.setElement(this.content_to_set);
            } else if (this.template) {
                this._super();
            }
        },
        /**
            Opens the popup. Inits the dialog if it is not already inited.
    
            @return this
        */
        open: function() {
            if (!this.dialog_inited) {
                this.init_dialog();
            }
            this.$buttons.insertAfter(this.$dialog_box.find(".modal-body"));
            $('.tooltip').remove(); //remove open tooltip if any to prevent them staying when modal is opened
            //add to list of currently opened modal
            opened_modal.push(this.$dialog_box);
            return this;
        },
        _add_buttons: function(buttons) {
            var self = this;
            var $customButons = this.$buttons.find('.oe_dialog_custom_buttons').empty();
            _.each(buttons, function(fn, text) {
                // buttons can be object or array
                var pre_text  = fn.pre_text || "";
                var post_text = fn.post_text || "";
                var oe_link_class = fn.oe_link_class;
                if (!_.isFunction(fn)) {
                    text = fn.text;
                    fn = fn.click;
                }
                var $but = $(QWeb.render('WidgetButton', { widget : { pre_text: pre_text, post_text: post_text, string: text, node: { attrs: {'class': oe_link_class} }}}));
                $customButons.append($but);
                $but.filter('button').on('click', function(ev) {
                    fn.call(self.$el, ev);
                });
            });
        },
        /**
            Initializes the popup.
    
            @return The result returned by start().
        */
        init_dialog: function() {
            var self = this;
            var options = _.extend({}, this.dialog_options);
            options.title = options.title || this.dialog_title;
            if (options.buttons) {
                this._add_buttons(options.buttons);
                delete(options.buttons);
            }
            this.renderElement();
            this.$dialog_box = $(QWeb.render('ProjectTimesheetDialog', options)).appendTo("body");
            this.$el.modal({
                'backdrop': false,
                'keyboard': true,
            });
            if (options.size !== 'large'){
                var dialog_class_size = this.$dialog_box.find('.modal-lg').removeClass('modal-lg');
                if (options.size === 'small'){
                    dialog_class_size.addClass('modal-sm');
                }
            }
    
            this.$el.appendTo(this.$dialog_box.find(".modal-body"));
            var $dialog_content = this.$dialog_box.find('.modal-content');
            if (options.dialogClass){
                $dialog_content.find(".modal-body").addClass(options.dialogClass);
            }
            $dialog_content.openerpClass();
    
            this.$dialog_box.on('hidden.bs.modal', this, function() {
                self.close();
            });
            this.$dialog_box.modal('show');
    
            this.dialog_inited = true;
            var res = this.start();
            return res;
        },
        /**
            Closes (hide) the popup, if destroy_on_close was passed to the constructor, it will be destroyed instead.
        */
        close: function(reason) {
            if (this.dialog_inited && !this.__tmp_dialog_hiding) {
                $('.tooltip').remove(); //remove open tooltip if any to prevent them staying when modal has disappeared
                if (this.$el.is(":data(bs.modal)")) {     // may have been destroyed by closing signal
                    this.__tmp_dialog_hiding = true;
                    this.$dialog_box.modal('hide');
                    this.__tmp_dialog_hiding = undefined;
                }
                this.trigger("closing", reason);
            }
        },
        _closing: function() {
            if (this.__tmp_dialog_destroying)
                return;
            if (this.dialog_options.destroy_on_close) {
                this.__tmp_dialog_closing = true;
                this.destroy();
                this.__tmp_dialog_closing = undefined;
            }
        },
        /**
            Destroys the popup, also closes it.
        */
        destroy: function (reason) {
            this.$buttons.remove();
            var self = this;
            _.each(this.getChildren(), function(el) {
                el.destroy();
            });
            if (! this.__tmp_dialog_closing) {
                this.__tmp_dialog_destroying = true;
                this.close(reason);
                this.__tmp_dialog_destroying = undefined;
            }
            if (this.dialog_inited && !this.isDestroyed() && this.$el.is(":data(bs.modal)")) {
                //we need this to put the instruction to remove modal from DOM at the end
                //of the queue, otherwise it might already have been removed before the modal-backdrop
                //is removed when pressing escape key
                var $element = this.$dialog_box;
                setTimeout(function () {
                    //remove modal from list of opened modal since we just destroy it
                    var modal_list_index = $.inArray($element, opened_modal);
                    if (modal_list_index > -1){
                        opened_modal.splice(modal_list_index,1)[0].remove();
                    }
                    if (opened_modal.length > 0){
                        //we still have other opened modal so we should focus it
                        opened_modal[opened_modal.length-1].focus();
                        //keep class modal-open (deleted by bootstrap hide fnct) on body 
                        //to allow scrolling inside the modal
                        $('body').addClass('modal-open');
                    }
                },0);
            }
            this._super();
        }
    });

    project_timesheet.ScreenSelector = openerp.Class.extend({
        init: function(options){
            this.project_timesheet_model = options.project_timesheet_model;

            this.screen_set = options.screen_set || {};

            this.default_screen = options.default_screen;

            this.current_screen = null; 

            for(screen_name in this.screen_set){
                this.screen_set[screen_name].hide();
            }

        },
        add_screen: function(screen_name, screen){
            screen.hide();
            this.screen_set[screen_name] = screen;
            return this;
        },
        set_current_screen: function(screen_name, screen_data_set, params, refresh, re_render) {
            var screen = this.screen_set[screen_name];
            if(re_render) {
                screen.renderElement();
            }
            if(!screen){
                console.error("ERROR: set_current_screen("+screen_name+") : screen not found");
            }

            var old_screen_name = this.project_timesheet_model.get_screen_data('screen');

            this.project_timesheet_model.set_screen_data('screen', screen_name);

            if(params){
                this.project_timesheet_model.set_screen_data('params', params);
            }

            if( screen_name !== old_screen_name ){
                this.project_timesheet_model.set_screen_data('previous-screen',old_screen_name);
            }

            if ( refresh || screen !== this.current_screen){
                if(this.current_screen){
                    this.current_screen.close();
                    this.current_screen.hide();
                }
                this.current_screen = screen;
                this.current_screen.show();
                if(screen_data_set && this.current_screen.set_screen_values) {
                    this.current_screen.set_screen_values(screen_data_set);
                }
            }
        },
        get_current_screen: function(){
            //return this.pos.get('selectedOrder').get_screen_data('screen') || this.default_screen;
            return this.project_timesheet_model.get_screen_data('screen') || this.default_screen;
        },
        back: function(){
            var previous = this.project_timesheet_model.get_screen_data('previous-screen');
            if(previous){
                this.set_current_screen(previous);
            }
        },
        get_current_screen_param: function(param){
            var params = this.project_timesheet_model.get_screen_data('params');
            return params ? params[param] : undefined;
        },
        set_screen_values: function() {
            //void method, child will implement if needed
        },
        set_default_screen: function(){
            this.set_current_screen(this.default_screen);
        },
    });

    project_timesheet.ScreenWidget = openerp.Widget.extend({ //Make sure we need to extend project_timesheet_widget or openerp.widget
        init: function(parent,options){
            this._super(parent,options);
            this.hidden = false;
            this.project_timesheet_model = project_timesheet.project_timesheet_model;
            this.project_timesheet_db = this.project_timesheet_model.project_timesheet_db;
        },
        // this method shows the screen and sets up all the widget related to this screen. Extend this method
        // if you want to alter the behavior of the screen.
        show: function(){
            var self = this;

            this.hidden = false;
            if(this.$el){
                this.$el.removeClass('o_hidden');
            }
        },

        // this method is called when the screen is closed to make place for a new screen. this is a good place
        // to put your cleanup stuff as it is guaranteed that for each show() there is one and only one close()
        close: function(){
            //TO Implement
        },

        // this methods hides the screen. It's not a good place to put your cleanup stuff as it is called on the
        // POS initialization.
        hide: function(){
            this.hidden = true;
            if(this.$el){
                this.$el.addClass('o_hidden');
            }
        },

        // we need this because some screens re-render themselves when they are hidden
        // (due to some events, or magic, or both...)  we must make sure they remain hidden.
        // the good solution would probably be to make them not re-render themselves when they
        // are hidden. 
        renderElement: function(){
            this._super();
            if(this.hidden){
                if(this.$el){
                    this.$el.addClass('o_hidden');
                }
            }
        },
        rpc_error: function(error) {
            if (error.data.exception_type === "except_osv" || error.data.exception_type === "warning" || error.data.exception_type === "access_error") {
                this.show_warning(error);
            } else {
                this.show_error(error);
            }
        },
        show_warning: function(error) {
            var self = this;
            if (error.data.exception_type === "except_osv") {
                error = _.extend({}, error, {data: _.extend({}, error.data, {message: error.data.arguments[0] + "\n\n" + error.data.arguments[1]})});
            }
            new project_timesheet.Dialog(this, {
                size: 'medium',
                title: "Odoo " + (_.str.capitalize(error.type) || "Warning"),
                buttons: [
                    {text: _t("Ok"), click: function() { $("body").find('.modal').modal('hide'); }}
                ],
            }, $('<div>' + QWeb.render('ProjectTimesheet.warning', {error: error}) + '</div>')).open();
        },
        show_error: function(error) {
            var self = this;
            var buttons = {};
            buttons[_t("Ok")] = function() {
                console.log("$(body).find('.modal') is ::: ",$("body").find('.modal'));
                $("body").find('.modal').modal('hide');
            };
            new project_timesheet.Dialog(this, {
                title: "Odoo " + _.str.capitalize(error.type),
                buttons: buttons
            }, QWeb.render('ProjectTimesheet.error', {widget: this, error: error})).open();
        },
    });

    project_timesheet.ActivityScreen = project_timesheet.ScreenWidget.extend({
        template: "ActivityScreen",
        init: function(project_timesheet_widget, options) {
            this._super.apply(this, arguments);
            this.project_timesheet_widget = project_timesheet_widget;
            this.activities = [];
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
        },
        show: function() {
            var self = this;
            this._super();
            this.activity_list = new project_timesheet.ActivityListView();
            this.activity_list.appendTo(this.$el.find(".pt_activity_body"));

            this.pad_table_to(11);
            //Add, Add Activity row prior to activities listview
            var $row = $("<tr><td><span class='pt_add_activity'>+ Add Activity</span></td></tr>");
            if(!this.$el.find(".pt_add_activity").length) {
                $row.prependTo(this.$el.find(".activity_row:first").parent());
            }

            //When Cancel is clicked it should move user to Activity List screen
            $(".pt_btn_cancel").on("click", function() {
                self.project_timesheet_widget.screen_selector.set_current_screen("activity");
            });
            this.$el.find(".pt_timer_button").on("click", this.on_button_timer);
            this.$el.find(".pt_add_activity").on("click", function() {
                self.project_timesheet_widget.screen_selector.set_current_screen("add_activity");
            });
            this.$el.find(".pt_stat").on("click", function() {
                self.project_timesheet_widget.screen_selector.set_current_screen("stat");
            });
            this.$el.find(".pt_sync").on("click", function() {
                self.project_timesheet_widget.screen_selector.set_current_screen("sync");
            });
            this.$el.find(".activity_row").on("click", this.on_row_click);
        },
        hide: function() {
            if(this.activity_list) {
                this.activity_list.destroy();
            }
            this._super();
        },
        pad_table_to: function(count) {
            if (this.activity_list.activities.length >= count) {
                return;
            }
            var row = '<tr class="activity_row"><td></td></tr>';
            $rows = $(new Array(count - this.activity_list.activities.length + 1).join(row));
            if (!this.$el.find(".activity_row").length) {
                $rows.appendTo(this.$el.find(".pt_activity_body > table > tbody").parent());
            } else {
                $rows.appendTo(this.$el.find(".activity_row:last").parent());
            }
        },
        on_row_click: function(event) {
            var activity_id = $(event.currentTarget).data("activity_id");
            if(activity_id) {
                var activity = this.project_timesheet_db.get_activity_by_id(activity_id);
                //TODO: Better to develop modify screen, instead of putting static logic and putting static logic
                this.project_timesheet_widget.screen_selector.set_current_screen("add_activity", activity);
            }
        },
        on_button_timer: function() {
            //TO Implement
        },
    });

    project_timesheet.AddActivityScreen = project_timesheet.ScreenWidget.extend({
        template: "AddActivityScreen",
        init: function(project_timesheet_widget, options) {
            this._super.apply(this, arguments);
            this.mode = options.mode || 'create';
            this.current_id = null;
            this.project_timesheet_widget = project_timesheet_widget;
            this._drop_shown = false;
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.$el.find(".pt_btn_add_activity").on("click", this.on_activity_add);
            this.$el.find(".pt_btn_edit_activity").on("click", this.on_activity_edit);
            this.$el.find(".pt_btn_remove_activity").on("click", this.on_activity_remove);
            
        },
        get_from_data: function() {
            var project_activity_data = {};
            $form_data = this.$el.find("input,textarea").filter(function() {return $(this).val() != "";});
            //TODO: Simplify this
            _.each($form_data, function(input) {
                var $input = $(input);
                switch(input.id) {
                    case "project_id":
                        project_activity_data['project_id'] = [$input.data("id"), $input.val()];
                        break;
                    case "task_id":
                        project_activity_data['task_id'] = [$input.data("id"), $input.val()];
                        break;
                    case "hours":
                        project_activity_data['hours'] = (project_activity_data['hours'] || 0) + parseInt($input.val());
                        break;
                    case "minutes":
                        project_activity_data['hours'] = (project_activity_data['hours'] || 0) + (((parseInt($input.val()) * 100) / 60))/100;
                        break;
                    case "name":
                        project_activity_data['name'] = $input.val();
                        break;
                }
            });
            return project_activity_data;
        },
        on_activity_add: function() {
            //TO Implement, get project_input value, if id is virtual prefix then also call project create else project write
            //Simply generate value such that project model can accept it, we will then call add project, now project will have logic
            //which finds project model based project_id from project's collection and for that model call add_task....
            if (!this.is_valid_data()) {
                return;
            }
            var project_activity_data = this.get_from_data();
            var momObj = new moment();
            var date = project_timesheet.datetime_to_str(momObj._d);
            project_activity_data['date'] = date; //Current date in accepted format
            project_activity_data['id'] = _.uniqueId(this.project_timesheet_db.virtual_id_prefix); //Activity New ID
            this.project_timesheet_model.add_project(project_activity_data);
            this.project_timesheet_widget.screen_selector.set_current_screen("activity", {}, {}, false, true);
        },
        on_activity_edit: function() {
            if (!this.is_valid_data()) {
                return;
            }
            var project_activity_data = this.get_from_data();
            project_activity_data['id'] = this.current_id; //Activity Existing ID
            this.project_timesheet_model.add_project(project_activity_data);
            this.project_timesheet_widget.screen_selector.set_current_screen("activity", {}, {}, false, true);
        },
        on_activity_remove: function() {
            //This method will set activity command to 2, so while synchronize we will set that activty as a to_delete
            var project_activity_data = this.get_from_data();
            project_activity_data['id'] = this.current_id; //Activity Existing ID
            var projects_collection = this.project_timesheet_model.get("projects");
            if(projects_collection.get(project_activity_data.project_id[0])) {
                var project_model = projects_collection.get(project_activity_data.project_id[0]);
                var task_collection = project_model.get('tasks');
                if (task_collection.get(project_activity_data.task_id[0])) {
                    var task_model = task_collection.get(project_activity_data.task_id[0]);
                    var task_activity_collection = task_model.get("task_activities");
                    var task_activity = task_activity_collection.get(this.current_id);
                    if (this.current_id.toString().match(this.project_timesheet_db.virtual_id_regex)) {
                        task_activity_collection.remove(task_activity);
                        this.project_timesheet_db.remove_activity(task_activity);
                        //Remove activity from db also
                    } else {
                        console.log("Inside set command for existing record in database.");
                        task_activity.set({command: 2});
                    }
                }
            }
            this.project_timesheet_widget.screen_selector.set_current_screen("activity", {}, {}, false, true);
        },
        show: function() {
            var self = this;
            $form_data = this.$el.find("input,textarea").filter(function() {return $(this).val() != "";});
            $form_data.val('');
            this.$el.find(".pt_activity_body h2").removeClass("o_hidden");
            this.$el.find(".pt_btn_add_activity").removeClass("o_hidden");
            self.$el.find(".pt_btn_remove_activity").addClass("o_hidden");
            if(!this.$el.find(".pt_btn_edit_activity").hasClass("o_hidden")) {
                this.$el.find(".pt_btn_edit_activity").addClass("o_hidden");
            }
            $form_data.removeData();
            this.activity_list = new project_timesheet.ActivityListView();
            this.activity_list.appendTo(this.$el.find(".pt_activity_body"));
            this.activity_list.$el.find(".activity_row").on('click', this.on_click_row);
            this._super();
            //Need to create instance of many2one in show method, because when autocomplete input is hidden, and show again it throws event binding error, we need to develop destroy_content in many2one widget and need to call when screen is hidden, need to bind events of many2one in show screen
            this.project_m2o = new project_timesheet.FieldMany2One(this, {model: this.project_timesheet_model , classname: "pt_input_project pt_required", label: "Project", id_for_input: "project_id"});
            this.project_m2o.on("change:value", this, this.set_project_model);
            this.project_m2o.appendTo(this.$el.find(".project_m2o"));
            this.task_m2o = new project_timesheet.FieldMany2One(this, {model: false, classname: "pt_input_task pt_required", label: "Task", id_for_input: "task_id"});
            this.task_m2o.appendTo(this.$el.find(".task_m2o"));
        },
        hide: function() {
            if(this.activity_list) {
                this.activity_list.destroy();
            }
            if(this.project_m2o) {
                this.project_m2o.destroy();
            }
            if(this.task_m2o) {
                this.task_m2o.destroy();
            }
            this._super();
        },
        on_click_row: function(event) {
            var activity_id = $(event.currentTarget).data("activity_id");
            var activity = this.project_timesheet_db.get_activity_by_id(activity_id);
            var activity_clone = _.clone(activity);
            activity_clone.id = _.uniqueId(this.project_timesheet_db.virtual_id_prefix); //Activity New ID
            this.project_timesheet_model.add_project(activity_clone);
            this.project_timesheet_widget.screen_selector.set_current_screen("activity", {}, {}, false, true);

        },
        is_valid_data: function() {
            var validity = true;
            var $required_inputs = this.$el.find("input.pt_required,textarea.pt_required").filter(function() {return $(this).val() == "";});
            _.each($required_inputs, function(input) {
                $(input).addClass("pt_invalid");
                validity = false;
            });
            var $duration_field = this.$el.find(".pt_duration input");
            _.each($duration_field, function(input) {
                if(!$(input).val() || (typeof parseInt($(input).val()) !== 'number' || isNaN(parseInt($(input).val())))) {
                    $(input).addClass("pt_invalid");
                    validity = false;
                }
            });
            return validity;
        },
        set_project_model: function() {
            var project_id = this.project_m2o.get('value');
            var projects_collection = this.project_timesheet_model.get('projects');
            var project_model = projects_collection.get(project_id);
            console.log("project_model is ::: ", projects_collection, project_model);
            this.task_m2o.model = project_model;
        },
        format_duration: function(field_val) {
            var data = field_val.toString().split(".");
            if (data[1]) {
                data[1] = Math.round((data[1]*60*10)/100).toString();
            }
            return data;
        },
        set_screen_values: function(screen_data) {
            //This method is called when its edit mode(i.e. when row is clicked from Activity Listview)
            var self = this;
            this.mode = "edit";
            this.current_id = screen_data['id'];
            this.$el.find(".pt_activity_body table").remove();
            this.$el.find(".pt_activity_body h2").addClass("o_hidden");
            self.$el.find(".pt_btn_remove_activity").removeClass("o_hidden");
            self.$el.find(".pt_btn_edit_activity").toggleClass("o_hidden");
            self.$el.find(".pt_btn_add_activity").toggleClass("o_hidden");
            _.each(screen_data, function(field_val, field_key) {
                switch(field_key) {
                    case "project_id":
                        self.project_m2o.set({value: field_val[0]});
                        self.$el.find("#project_id").val(field_val[1]);
                        self.$el.find("#project_id").data("id", field_val[0]);
                        break;
                    case "task_id":
                        self.$el.find("#task_id").val(field_val[1]);
                        self.$el.find("#task_id").data("id", field_val[0]);
                        break;
                    case "hours":
                        var formatted = self.format_duration(field_val);
                        self.$el.find("#hours").val(formatted[0]);
                        self.$el.find("#minutes").val(formatted[1]);
                        break;
                    case "name":
                        self.$el.find("#"+field_key).val(field_val);
                        break;
                }
            });
        },
    });

    //TODO: We can override show method, when user document's cookie is already set with session_id then do not ask for server name, db, username, and password, directy give Synchronize button
    //When Sync screen is displayed check session first whether session_id exist then call reload session and do not display db, username, password elements
    //May be give message in template that you are already logged in, login with other user ?
    project_timesheet.SyncScreen = project_timesheet.ScreenWidget.extend({
        template: "SyncScreen",
        init: function(project_timesheet_widget, options) {
            this._super.apply(this, arguments);
            this.project_timesheet_widget = project_timesheet_widget;
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.$el.find(".pt_select_protocol").on("click", function() {
                self.$el.find(".pt_button_protocol span:first").text($(this).text());
            });
            this.$el.find("#pt_new_user,#pt_existing_user").on("click", function() {
                self.$el.find(".o_new_account").toggleClass("o_active");
                self.$el.find(".o_existing_account").toggleClass("o_active");
            });
            /*
            this.$el.find("#pt_new_user,#pt_existing_user").on("click", function() {
                self.$el.find(".o_existing_account").toggleClass("o_active")
            });
            */
            this.$el.find(".pt_btn_synchronize").on("click", this.on_authenticate_and_sync)
        },
        on_authenticate_and_sync: function() {
            var self = this;
            var def = $.Deferred();
            var protocol = self.$el.find(".pt_button_protocol span:first").text();
            var origin = protocol + this.$el.find(".pt_input_server_address").val(); //May be store origin in localstorage to keep session persistent for that origin
            var db = this.$el.find(".pt_input_db").val();
            var username = this.$el.find(".pt_input_username").val();
            var password = this.$el.find(".pt_input_password").val();
            if(!_.all([origin, db, username, password])) {
                this.set_required();
                return;
            }
            var session = new openerp.Session(undefined, origin);
            project_timesheet.session = session;
            //if (!openerp.get_cookie("session_id")) { //use check_session_id
                def = session.session_authenticate(db, username, password).done(function() {
                    //TODO: Create generic method set_cookie
                    document.cookie = ["session_id="+session.session_id,'path='+origin,
                        'max-age=' + (24*60*60*365),
                        'expires=' + new Date(new Date().getTime() + 300*1000).toGMTString()].join(';')

                        //Store session object in local storage, we need it, so that user don't have to enter login detail each time while sync
                        //Note that, session_id is created new each time for cross domain policy
                        self.project_timesheet_db.save("session", session);
                }).fail(function(error, event) {
                    if (error) {
                        self.rpc_error(error);
                    } else {
                        alert("Something went wrong, please check your username or password");
                    }
                });
            //} else {
            //    def.resolve();
            //}
            $.when(def).done(function() {
                console.log("You can go ahead to sync data and retrieve data");
                //Get Model data and sync with Server and then Retrieve data and store in localstorage
            });
        },
        set_required: function() {
            var origin = this.$el.find(".pt_input_server_address"); //May be store origin in localstorage to keep session persistent for that origin
            var db = this.$el.find(".pt_input_db");
            var username = this.$el.find(".pt_input_username");
            var password = this.$el.find(".pt_input_password");
            var first_elem = _.find([origin, db, username, password], function(ele) {return !ele.val();});
            first_elem.focus();
            _([origin, db, username, password]).each(function($element) {
                $element.removeClass('oe_form_required');
                if (!$element.val()) {
                    $element.addClass('pt_invalid');
                }
            });
            
        },
    });

    project_timesheet.StatisticScreen = project_timesheet.ScreenWidget.extend({
        template: "StatisticScreen",
        init: function(project_timesheet_widget, options) {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
        }
    });
}