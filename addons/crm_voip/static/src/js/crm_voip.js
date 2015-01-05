openerp.crm_voip = function(instance) {

    var _t = openerp._t;
    var _lt = openerp._lt;
    var QWeb = openerp.qweb;
    var crm_voip = openerp.crm_voip = {};  
    
    crm_voip.PhonecallWidget = openerp.Widget.extend({
        "template": "crm_voip.PhonecallWidget",
        events: {
            "click": "select_call",
            "click .oe_dial_remove_phonecall": "remove_phonecall"
        },
        init: function(parent, phonecall, in_call) {
            this._super(parent);
            this.set("id", phonecall.id);
            if(phonecall.partner_name){
                this.set("partner",_.str.truncate(phonecall.partner_name,19));
            }else{
                this.set("partner", _t("Unknown"));
            }
            this.set("state",phonecall.state);
            this.set("image_small", phonecall.partner_image_small);
            this.set("in_call", in_call); 
            this.set("email",phonecall.partner_email);
            this.set("name",_.str.truncate(phonecall.name,23));
        },

        //select the clicked call, show options and put some highlight on it
        select_call: function(){
            this.trigger("select_call", this.get('id'));
        },

        remove_phonecall: function(e){
            e.stopPropagation();
            this.trigger("remove_phonecall",this);
        },
    });
    
    crm_voip.Panel_UI = openerp.Widget.extend({

        init: function(parent){
            this._super(parent);
            this.shown = false;
            this.panel = this.__parentedParent;
            this.buttonAnimated = false;
            this.buttonUp = false;
        },

        start_ringing: function(id){
            this.panel.$('.oe_dial_big_callbutton').html(_t("Calling..."));
            this.panel.$('.oe_dial_hangupbutton').removeAttr('disabled');
            if(this.panel.$('.oe_dial_icon_inCall').length === 0){
                this.panel.$(".oe_dial_phonecall_partner_name").filter(function(){return $(this).data('id') == id;})
                .after("<i style='margin-left:5px;' class='fa fa-microphone oe_dial_icon_inCall'></i>");
            }
        },

        remove_mic: function(){
            this.panel.$(".oe_dial_icon_inCall").remove();
        },

        hangup: function(){
            this.panel.$('.oe_dial_big_callbutton').html(_t("Call"));
            this.panel.$(".oe_dial_transferbutton, .oe_dial_hangupbutton").attr('disabled','disabled');
        },

        start_auto_call: function(){
            this.panel.$(".oe_dial_split_callbutton").hide();
            this.panel.$(".oe_dial_stop_autocall_button").show();
        },

        stop_auto_call: function(){
            this.panel.$(".oe_dial_split_callbutton").show();
            this.panel.$(".oe_dial_stop_autocall_button").hide();
        },

        reset_display_panel: function(phonecall_displayed){
            if(this.panel.$(".oe_dial_icon_inCall").length === 0){
                this.panel.$(".oe_dial_transferbutton, .oe_dial_hangupbutton").attr('disabled','disabled');
            }
            this.panel.$(".oe_dial_content").animate({
                bottom: 0,
            });
            if(!phonecall_displayed){
                this.panel.$(".oe_dial_callbutton, .oe_call_dropdown").attr('disabled','disabled');
            }else{
                this.panel.$(".oe_dial_callbutton, .oe_call_dropdown").removeAttr('disabled');
            }
        },

        switch_display: function(){
            if (this.shown) {
                this.panel.$el.animate({
                    bottom: -this.panel.$el.outerHeight(),
                });
            } else {
                // update the list of user status when show the dialer panel
                this.panel.search_phonecalls_status();

                this.panel.$el.animate({
                    bottom: 0,
                });
            }
            this.shown = ! this.shown;
        },

        select_call: function(selected_phonecall){
            if(!this.buttonAnimated){
                var self = this;
                var selected = selected_phonecall.$el.hasClass("oe_dial_selected_phonecall");
                this.panel.$(".oe_dial_selected_phonecall").removeClass("oe_dial_selected_phonecall");
                if(!selected){
                    selected_phonecall.$el.addClass("oe_dial_selected_phonecall");
                    if(!this.buttonUp){
                        this.buttonAnimated = true;
                        this.panel.$(".oe_dial_phonecalls").animate({
                            height: (this.panel.$(".oe_dial_phonecalls").height() - this.panel.$(".oe_dial_optionalbuttons").outerHeight()),
                        }, 300,function(){
                            self.buttonAnimated = false;
                            self.buttonUp = true;
                        });
                    }
                    this.panel.$(".oe_dial_email").hide();
                    if(selected_phonecall.get('email')){
                        this.panel.$(".oe_dial_email").show();
                        this.panel.$(".oe_dial_schedule_call").removeClass("oe_dial_schedule_full_width");
                    }else{
                        this.panel.$(".oe_dial_schedule_call").addClass("oe_dial_schedule_full_width");
                    }
                }else{
                    selected_phonecall = false;
                    this.buttonAnimated = true;
                    this.panel.$(".oe_dial_phonecalls").animate({
                        height: (this.panel.$(".oe_dial_phonecalls").height() + this.panel.$(".oe_dial_optionalbuttons").outerHeight()),
                    }, 300,function(){
                        self.buttonAnimated = false;
                        self.buttonUp = false;
                    });
                }
            }
            return selected_phonecall;
        },

        //Hide the optional buttons when the panel is reloaded
        hide_buttons: function(){
            var self = this;
            if(this.buttonUp && !this.buttonAnimated){
                this.buttonAnimated = true;
                this.panel.$(".oe_dial_phonecalls").animate({
                    height: (this.panel.$(".oe_dial_phonecalls").height() + this.panel.$(".oe_dial_optionalbuttons").outerHeight()),
                }, 300,function(){
                    self.buttonUp = false;
                    self.buttonAnimated = false;
                });
            }
        },
    });

    crm_voip.DialingPanel = openerp.Widget.extend({
        template: "crm_voip.DialingPanel",
        events: {
            "keyup .oe_dial_searchbox": "input_change",
            "click .oe_dial_callbutton": "call_button",
            "click .oe_dial_hangupbutton": "hangup_button",
            "click .oe_dial_schedule_call": "schedule_call",
            "click .oe_dial_email": "send_email",
            "click .oe_dial_to_client": "to_client",
            "click .oe_dial_to_lead": "to_lead",
            "click .oe_dial_transferbutton": "transfer_button",
            "click .oe_dial_auto_callbutton": "auto_call_button",
            "click .oe_dial_stop_autocall_button": "stop_auto_call_button",
        },

        init: function(parent) {    
            this._super(parent);
            this.phonecalls = {};
            this.widgets = {};
            this.on_call = false;
            this.in_automatic_mode = false;
        },

        start: function() {
            var self = this;
            this.sip_js = new openerp.voip.user_agent();
            this.sip_js.on('sip_ringing',this,this.sip_ringing);
            this.sip_js.on('sip_accepted',this,this.sip_accepted);
            this.sip_js.on('sip_cancel',this,this.sip_cancel);
            this.sip_js.on('sip_rejected',this,this.sip_rejected);
            this.sip_js.on('sip_bye',this,this.sip_bye);
            this.sip_js.on('sip_error',this,this.sip_error);
            
            this.UI = new openerp.crm_voip.Panel_UI(this);
            //To get the formatCurrency function from the server
            new instance.web.Model("res.currency")
                .call("get_format_currencies_js_function")
                .then(function(data) {
                    self.formatCurrency = new Function("amount, currency_id", data);
                    //update of the panel's list
                    self.search_phonecalls_status();
                });
            this.$el.css("bottom", -this.$el.outerHeight());
            //bind the bus trigger with the functions
            openerp.web.bus.on('reload_panel', this, this.search_phonecalls_status);
            openerp.web.bus.on('transfer_call',this,this.transfer_call);
            openerp.web.bus.on('select_call',this,this.select_call);
            openerp.web.bus.on('next_call',this,this.next_call);
            return;
        },

        sip_ringing: function(){
            var id = this.current_phonecall.id;
            this.UI.start_ringing(id);
            //Select the current call if not already selected
            if(!this.selected_phonecall || this.selected_phonecall.get('id') !== id ){
                this.select_call(id);
            }
        },

        sip_accepted: function(){
            new openerp.web.Model("crm.phonecall").call("init_call", [this.current_phonecall.id]);
            $('.oe_dial_transferbutton').removeAttr('disabled');
        },

        sip_cancel: function(){
            this.on_call = false;
            var id = this.current_phonecall.id;
            this.UI.remove_mic();
            //TODO if the sale cancel one call, continue the automatic call or not ? 
            this.stop_automatic_call();
        },

        sip_rejected: function(){
            this.on_call = false;
            var id = this.current_phonecall.id;
            new openerp.web.Model("crm.phonecall").call("rejected_call",[id]);
            this.UI.remove_mic();
            if(this.in_automatic_mode){
                this.next_call();
            }else{
                this.stop_automatic_call();
            }
        },

        sip_bye: function(){
            var self = this;
            this.on_call = false;
            var id = this.current_phonecall.id;
            new openerp.web.Model("crm.phonecall").call("hangup_call", [id]).then(_.bind(self.hangup_call,self));
        },

        hangup_call: function(result){
            var duration = parseFloat(result.duration).toFixed(2);
            this.log_call(duration);
            this.UI.remove_mic();
            if(!this.in_automatic_mode){
               this.stop_automatic_call();
            }
        },

        sip_error: function(){
            this.on_call = false;
            this.UI.hangup();
            new openerp.web.Model("crm.phonecall").call("error_config");
        },

        log_call: function(duration){
            var self = this;
            var value = duration;
            var pattern = '%02d:%02d';
            if (value < 0) {
                value = Math.abs(value);
                pattern = '-' + pattern;
            }
            var min = Math.floor(value);
            var sec = Math.round((value % 1) * 60);
            if (sec == 60){
                sec = 0;
                min = min + 1;
            }
            this.current_phonecall.duration = _.str.sprintf(pattern, min, sec);
            openerp.client.action_manager.do_action({
                    name: 'Log a call',
                    type: 'ir.actions.act_window',
                    key2: 'client_action_multi',
                    src_model: "crm.phonecall",
                    res_model: "crm.phonecall.log.wizard",
                    multi: "True",
                    target: 'new',
                    context: {'phonecall_id': self.current_phonecall.id,
                    'default_opportunity_id': self.current_phonecall.opportunity_id,
                    'default_name': self.current_phonecall.name,
                    'default_duration': self.current_phonecall.duration,
                    'default_description' : self.current_phonecall.description,
                    'default_opportunity_name' : self.current_phonecall.opportunity_name,
                    'default_opportunity_planned_revenue' : self.current_phonecall.opportunity_planned_revenue,
                    'default_opportunity_title_action' : self.current_phonecall.opportunity_title_action,
                    'default_opportunity_date_action' : self.current_phonecall.opportunity_date_action,
                    'default_opportunity_probability' : self.current_phonecall.opportunity_probability,
                    'default_partner_id': self.current_phonecall.partner_id,
                    'default_partner_name' : self.current_phonecall.partner_name,
                    'default_partner_phone' : self.current_phonecall.partner_phone,
                    'default_partner_email' : self.current_phonecall.partner_email,
                    'default_partner_image_small' : self.current_phonecall.partner_image_small,
                    'default_in_automatic_mode': self.in_automatic_mode,},
                    views: [[false, 'form']],
                    flags: {
                        'headless': true,
                    },
                });
        },

        make_call: function(phonecall_id){
            this.current_phonecall = this.phonecalls[phonecall_id];
            var number;
            if(this.current_phonecall.partner_phone){
                number = this.current_phonecall.partner_phone;
            } else if (this.current_phonecall.partner_mobile){
                number = this.current_phonecall.partner_mobile;
            }else{
                //TODO what to do when no number?
                return {};
            }
            this.on_call = true;
            this.sip_js.make_call(number);
        },

        automatic_call: function(){
            if(!this.on_call){
                this.in_automatic_mode = true;
                this.phonecalls_ids = [];
                for (var id in this.phonecalls){
                    if(this.phonecalls[id].state != "done"){
                        this.phonecalls_ids.push(id);
                    }
                }
                if(this.phonecalls_ids.length){
                    this.make_call(this.phonecalls_ids.shift());
                }else{
                    this.stop_automatic_call();
                }
            }
        },

        next_call: function(){
            if(this.phonecalls_ids.length){
                if(!this.on_call){
                    this.make_call(this.phonecalls_ids.shift());
                }
            }else{
                this.stop_automatic_call();
            }
        },

        stop_automatic_call: function(){
            this.in_automatic_mode = false;
            this.UI.stop_auto_call();
            if(!this.on_call){
                this.UI.hangup();
            }else{
                $('.oe_dial_big_callbutton').html(_t("Calling..."));
            }
        },

        //Modify the phonecalls list when the search input changes
        input_change: function() {
            var search = this.$(".oe_dial_searchbox").val().toLowerCase();
            //for each phonecall, check if the search is in phonecall name or the partner name
            _.each(this.phonecalls,function(phonecall){
                var flag = phonecall.partner_name.toLowerCase().indexOf(search) == -1 && 
                    phonecall.name.toLowerCase().indexOf(search) == -1;
                this.$(".oe_dial_phonecall").filter(function(){return $(this).data('id') == phonecall.id;}).toggle(!flag);
            });
        },

        //Get the phonecalls and create the widget to put inside the panel
        search_phonecalls_status: function(refresh_by_user) {
            var self = this;
            this.UI.hide_buttons();
            //get the phonecalls' information and populate the queue
            new openerp.web.Model("crm.phonecall").call("get_list").then(_.bind(self.parse_phonecall,self,refresh_by_user));
        },

        parse_phonecall: function(refresh_by_user,result){
            var self = this;
            var old_widgets = self.widgets;                   
            self.widgets = {};
            self.phonecalls = {};
            
            var phonecall_displayed = false;
            //for each phonecall display it only if the date is lower than the current one
            //if the refresh is done by the user, retrieve the phonecalls set as "done"
            _.each(result.phonecalls, function(phonecall){
                date = new Date(phonecall.date.split(" ")[0]);
                date_now = new Date(Date.now());
                if(date.getDate() <= date_now.getDate() && date.getMonth() <= date_now.getMonth() && date.getFullYear() <= date_now.getFullYear()){
                    phonecall_displayed = true;
                    if(refresh_by_user){
                        if(phonecall.state != "done"){
                            self.display_in_queue(phonecall);
                        }else{
                            new openerp.web.Model("crm.phonecall").call("remove_from_queue",[phonecall.id]);
                        }
                    }else{
                        self.display_in_queue(phonecall);
                    }
                }
            });
            self.UI.reset_display_panel(phonecall_displayed);
            _.each(old_widgets, function(w) {
                w.destroy();
            });
        },

        //function which will add the phonecall in the queue and create the tooltip
        display_in_queue: function(phonecall){
            var in_call = false;
            //Check if the current phonecall is currently done to add the microphone icon
            if(this.on_call && phonecall.id == this.current_phonecall.id){
                in_call = true;
            }
            var widget = new openerp.crm_voip.PhonecallWidget(this, phonecall, in_call);
            widget.appendTo(this.$(".oe_dial_phonecalls"));
            widget.on("select_call", this, this.select_call);
            widget.on("remove_phonecall",this,this.remove_phonecall);
            this.widgets[phonecall.id] = widget;
            phonecall.opportunity_planned_revenue = this.formatCurrency(phonecall.opportunity_planned_revenue, phonecall.opportunity_company_currency);
            var partner_name;
            if(phonecall.partner_name){
                if(! phonecall.partner_title){
                    partner_name = phonecall.partner_name;
                }else{
                    partner_name = phonecall.partner_title + ' ' + phonecall.partner_name;
                }
            }else{
                partner_name = "Unknown";
            }
            display_opp_name = true;
            if(!phonecall.opportunity_name){
                phonecall.opportunity_name = _t("No opportunity linked");
            }else if(phonecall.opportunity_name == phonecall.name){
                display_opp_name = false;
            }
            var empty_star = parseInt(phonecall.max_priority) - parseInt(phonecall.opportunity_priority);
            //creation of the tooltip
            $("[rel='popover']").popover({
                placement : 'right', // top, bottom, left or right
                title : QWeb.render("crm_voip_Tooltip_title", {
                    name: phonecall.name, priority: parseInt(phonecall.opportunity_priority), empty_star:empty_star}), 
                html: 'true', 
                content :  QWeb.render("crm_voip_Tooltip",{
                    display_opp_name: display_opp_name,
                    opportunity: phonecall.opportunity_name,
                    partner_name: partner_name,
                    phone: phonecall.partner_phone,
                    description: phonecall.description,
                    email: phonecall.partner_email,
                    title_action: phonecall.opportunity_title_action,
                    planned_revenue: phonecall.opportunity_planned_revenue,
                    probability: phonecall.opportunity_probability,
                    date: phonecall.date,
                }),
            });
            this.phonecalls[phonecall.id] = phonecall;
        },

        //function that will display the panel
        switch_display: function() {
            this.UI.switch_display();
        },

        //action to change the main view to go to the opportunity's view
        to_lead: function() {
            var id = this.selected_phonecall.get('id');
            var phonecall = this.phonecalls[id];
            if(phonecall.opportunity_id){
                //Call of the function xmlid_to_res_model_res_id to get the id of the opportunity's form view and not the lead's form view
                new instance.web.Model("ir.model.data").call("xmlid_to_res_model_res_id",["crm.crm_case_form_view_oppor"]).then(function(data){
                    openerp.client.action_manager.do_action({
                        type: 'ir.actions.act_window',
                        res_model: "crm.lead",
                        res_id: phonecall.opportunity_id,
                        views: [[data[1], 'form']],
                        target: 'current',
                        context: {},
                        flags: {initial_mode: "edit",},
                    });
                });
            }else{
                var phonecall_model = new openerp.web.Model("crm.phonecall");
                phonecall_model.call("action_button_convert2opportunity", [[phonecall.id]]).then(function(result){
                    result.flags= {initial_mode: "edit",};
                    openerp.client.action_manager.do_action(result);
                });
            }
        },

        //action to change the main view to go to the client's view
        to_client: function() {
            var id = this.selected_phonecall.get('id');
            var phonecall = this.phonecalls[id];
            openerp.client.action_manager.do_action({
                type: 'ir.actions.act_window',
                res_model: "res.partner",
                res_id: phonecall.partner_id,
                views: [[false, 'form']],
                target: 'current',
                context: {},
                flags: {initial_mode: "edit",},
            });
        },

        //action to select a call and display the specific actions
        select_call: function(phonecall_id){
            this.selected_phonecall = this.UI.select_call(this.widgets[phonecall_id]);
        },

        //remove the phonecall from the queue
        remove_phonecall: function(phonecall_widget){
            var phonecall_model = new openerp.web.Model("crm.phonecall");
            var phonecall_id = phonecall_widget.$(".oe_dial_phonecall_partner_name").data().id;
            var self = this;
            phonecall_model.call("remove_from_queue", [this.phonecalls[phonecall_id].id]).then(function(action){
                openerp.client.action_manager.do_action(action);
                self.$(".popover").remove();
            });
        },

        //action done when the button "call" is clicked
        call_button: function(){
            var self = this;
            if(this.selected_phonecall){
                this.make_call(this.selected_phonecall.get('id'));
            }else{
                this.$(".oe_dial_phonecalls > .oe_dial_phonecall")
                    .each(function(key,phonecall){
                        if($(phonecall).data('state') != 'done'){
                            self.make_call($(phonecall).data('id'));
                            return false;
                        }
                    });
            }
        },

        auto_call_button: function(){
            this.UI.start_auto_call();
            this.automatic_call();
        },

        stop_auto_call_button: function(){
            this.sip_js.stop_automatic_call();
        },

        //action done when the button "Hang Up" is clicked
        hangup_button: function(){
            this.sip_js.hangup();
            self.$(".popover").remove();
        },

        //action done when the button "Transfer" is clicked
        transfer_button: function(){
            //Launch the transfer wizard
            openerp.client.action_manager.do_action({
                type: 'ir.actions.act_window',
                key2: 'client_action_multi',
                src_model: "crm.phonecall",
                res_model: "crm.phonecall.transfer.wizard",
                multi: "True",
                target: 'new',
                context: {},
                views: [[false, 'form']],
                flags: {
                    'headless': true,
                },
            });
        },

        //action done when the transfer_call action is triggered
        transfer_call: function(number){
            this.sip_js.transfer(number);
        },

        //action done when the button "Reschedule Call" is clicked
        schedule_call: function(){
            var id = this.selected_phonecall.get('id');
            var self = this;
            openerp.client.action_manager.do_action({
                name: 'Schedule Other Call',
                type: 'ir.actions.act_window',
                key2: 'client_action_multi',
                src_model: "crm.phonecall",
                res_model: "crm.phonecall2phonecall",
                multi: "True",
                target: 'new',
                context: {'active_id': this.phonecalls[id].id, 'active_ids': [this.phonecalls[id].id]},
                views: [[false, 'form']],
                flags: {
                    'headless': true,
                }
            });
        },

        //action done when the button "Send Email" is clicked
        send_email: function(){
            var id = this.selected_phonecall.get('id');
            var self = this;
            if(this.phonecalls[id].opportunity_id){
                openerp.client.action_manager.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'mail.compose.message',
                    src_model: 'crm.phonecall',
                    multi: "True",
                    target: 'new',
                    key2: 'client_action_multi',
                    context: {
                                'default_composition_mode': 'mass_mail',
                                'active_ids': [this.phonecalls[id].opportunity_id],
                                'default_model': 'crm.lead',
                                'default_partner_ids': [this.phonecalls[id].partner_id],
                                'default_use_template': true,
                            },
                    views: [[false, 'form']],
                });
            }else if(this.phonecalls[id].partner_id){
                openerp.client.action_manager.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'mail.compose.message',
                    src_model: 'crm.phonecall',
                    multi: "True",
                    target: 'new',
                    key2: 'client_action_multi',
                    context: {
                                'default_composition_mode': 'mass_mail',
                                'active_ids': [this.phonecalls[id].partner_id],
                                'default_model': 'res.partner',
                                'default_partner_ids': [this.phonecalls[id].partner_id],
                                'default_use_template': true,
                            },
                    views: [[false, 'form']],
                });
            }
            
        },
    });

    //Creation of the panel and binding of the display with the button in the top bar
    if(openerp.web && openerp.web.UserMenu) {
        openerp.web.UserMenu.include({
            do_update: function(){
                var self = this;
                if($('.oe_systray .oe_topbar_dialbutton_icon')){
                    self.update_promise.then(function() {
                        var dial = new openerp.crm_voip.DialingPanel(self);
                        dial.appendTo(openerp.client.$el);
                        $('.oe_topbar_dialbutton_icon').parent().on("click", dial, _.bind(dial.switch_display, dial));
                        
                        //bind the action to retrieve the panel with the button in the header of the panel
                        $('.oe_dial_close_icon').parent().on("click", dial, _.bind(dial.switch_display, dial));

                        //bind the action to refresh the panel information
                        $('.oe_dial_search_icon').on("click", dial, _.bind(dial.search_phonecalls_status, dial));

                        //bind the action to refresh the panel information
                        refresh_by_user = true;
                        $('.oe_dial_refresh_icon').parent().on("click", dial, _.bind(dial.search_phonecalls_status, dial,refresh_by_user));
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
    }
    
    //Trigger "reload_panel" that will be catch by the widget to reload the panel
    openerp.crm_voip.reload_panel = function (parent, action) {
        var params = action.params || {};
        if(params.go_to_opp){
            //Call of the function xmlid_to_res_model_res_id to get the id of the opportunity's form view and not the lead's form view
            new instance.web.Model("ir.model.data").call("xmlid_to_res_model_res_id",["crm.crm_case_form_view_oppor"]).then(function(data){
                openerp.client.action_manager.do_action({
                    type: 'ir.actions.act_window',
                    res_model: "crm.lead",
                    res_id: params.opportunity_id,
                    views: [[data[1], 'form']],
                    target: 'current',
                    context: {},
                    flags: {initial_mode: "edit",},
                });
            });
        }
        if(params.in_automatic_mode){
            openerp.web.bus.trigger('next_call');
        }
        openerp.web.bus.trigger('reload_panel');
        //Return an action to close the wizard after the reload of the panel
        return { type: 'ir.actions.act_window_close' };
    };

    openerp.crm_voip.transfer_call = function(parent, action){
        var params = action.params || {};
        openerp.web.bus.trigger('transfer_call', params.number);
        return { type: 'ir.actions.act_window_close' };
    };

    instance.web.client_actions.add("reload_panel", "openerp.crm_voip.reload_panel");
    instance.web.client_actions.add("transfer_call","openerp.crm_voip.transfer_call");
    return crm_voip;
};