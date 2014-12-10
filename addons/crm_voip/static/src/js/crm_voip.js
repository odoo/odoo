
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
        init: function(parent, phonecall, inCall) {
            this._super(parent);
            this.set("id", phonecall.id);
            if(phonecall.partner_name){
                this.set("partner",_.str.truncate(phonecall.partner_name,19));
            }else{
                this.set("partner", "Unknown");
            }
            this.set("state",phonecall.state);
            this.set("image_small", phonecall.partner_image_small);
            this.set("inCall", inCall); 
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
            this.shown = false;
            this.phonecalls = {};
            this.widgets = {};
            this.buttonAnimated = false;
        },

        start: function() {
            var self = this;
            //this.ari_client = new openerp.ari_client();
            //this.ari_client.init();
            try{
                this.sip_js = new openerp.sip_js();
                this.sip_js.init();
            }catch(e){
                console.log(e);
            }
            
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
            return;
        },

        //Modify the phonecalls list when the search input changes
        input_change: function() {
            var self = this;
            var search = this.$(".oe_dial_searchbox").val().toLowerCase();
            //for each phonecall, check if the search is in phonecall name or the partner name
            _.each(this.phonecalls,function(phonecall){
                var flag = phonecall.partner_name.toLowerCase().indexOf(search) == -1 && 
                    phonecall.name.toLowerCase().indexOf(search) == -1;
                self.$(".oe_dial_phonecall").filter(function(){return $(this).data('id') == phonecall.id;}).toggle(!flag);
            });
        },

        //Get the phonecalls and create the widget to put inside the panel
        search_phonecalls_status: function(refresh_by_user) {
            var self = this;
            //Hide the optional buttons
            if(this.buttonUp && !this.buttonAnimated){
                this.buttonAnimated = true;
                this.$(".oe_dial_phonecalls").animate({
                    height: (this.$(".oe_dial_phonecalls").height() + this.$(".oe_dial_optionalbuttons").outerHeight()),
                }, 300,function(){
                    self.buttonUp = false;
                    self.buttonAnimated = false;
                });
            }
            //get the phonecalls' information and populate the queue
            new openerp.web.Model("crm.phonecall").call("get_list").then(function(result){
                var old_widgets = self.widgets;                   
                self.widgets = {};
                self.phonecalls = {};

                if(self.$(".oe_dial_icon_inCall").length === 0){
                    self.$(".oe_dial_transferbutton, .oe_dial_hangupbutton").attr('disabled','disabled');
                }
                self.$(".oe_dial_content").animate({
                    bottom: 0,
                });
                var phonecall_displayed = false;
                //for each phonecall display it only if the date is lower than the current one
                //if the refresh is done by the user, retrieve the phonecalls set as "done"
                _.each(result.phonecalls, function(phonecall){
                    if(Date.parse(phonecall.date) <= Date.now()){
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
                if(!phonecall_displayed){
                    self.$(".oe_dial_callbutton, .oe_call_dropdown").attr('disabled','disabled');
                }else{
                    self.$(".oe_dial_callbutton, .oe_call_dropdown").removeAttr('disabled');
                }
                _.each(old_widgets, function(w) {
                    w.destroy();
                });
            });
            
        },

        //function which will add the phonecall in the queue and create the tooltip
        display_in_queue: function(phonecall){
            var inCall = false;
            //Check if the current phonecall is currently done to add the microphone icon
            if(this.$(".oe_dial_phonecall_partner_name").filter(function(){return $(this).data('id') == phonecall.id;}).next(".oe_dial_icon_inCall").length != 0){
                inCall = true;
            }
            var widget = new openerp.crm_voip.PhonecallWidget(this, phonecall, inCall);
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
                phonecall.opportunity_name = "No opportunity linked";
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
            if (this.shown) {
                this.$el.animate({
                    bottom: -this.$el.outerHeight(),
                });
            } else {
                // update the list of user status when show the dialer panel
                this.search_phonecalls_status();

                this.$el.animate({
                    bottom: 0,
                });
            }
            this.shown = ! this.shown;
        },

        //action to change the main view to go to the opportunity's view
        to_lead: function() {
            var id = this.$(".oe_dial_selected_phonecall").data().id;
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
            var id = this.$(".oe_dial_selected_phonecall").data().id;
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
            var phonecall_widget = this.widgets[phonecall_id];
            if(!this.buttonAnimated){
                var self = this;
                var selected = phonecall_widget.$el.hasClass("oe_dial_selected_phonecall");
                self.$(".oe_dial_selected_phonecall").removeClass("oe_dial_selected_phonecall");
                if(!selected){
                    phonecall_widget.$el.addClass("oe_dial_selected_phonecall");
                    if(!self.buttonUp){
                        this.buttonAnimated = true;
                        this.$(".oe_dial_phonecalls").animate({
                            height: (this.$(".oe_dial_phonecalls").height() - this.$(".oe_dial_optionalbuttons").outerHeight()),
                        }, 300,function(){
                            self.buttonAnimated = false;
                            self.buttonUp = true;
                        });
                    }
                    this.$(".oe_dial_email").hide();
                    if(phonecall_widget.get('email')){
                        this.$(".oe_dial_email").show();
                        this.$(".oe_dial_schedule_call").removeClass("oe_dial_schedule_full_width");
                    }else{
                        this.$(".oe_dial_schedule_call").addClass("oe_dial_schedule_full_width");
                    }
                }else{
                    this.buttonAnimated = true;
                    this.$(".oe_dial_phonecalls").animate({
                        height: (this.$(".oe_dial_phonecalls").height() + this.$(".oe_dial_optionalbuttons").outerHeight()),
                    }, 300,function(){
                        self.buttonAnimated = false;
                        self.buttonUp = false;
                    });
                }
            } 
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
            var phonecall_id;
            if(this.$(".oe_dial_selected_phonecall").length){
                phonecall_id = this.$(".oe_dial_selected_phonecall").data('id');
                /*
                //JS Ari lib
                this.ari_client.call(this.phonecalls[phonecall_id],function(channel){
                    console.log("after the call")
                    self.phonecall_channel = channel;
                    console.log(self.phonecall_channel);
                });
                */
                this.sip_js.call(this.phonecalls[phonecall_id]);
            }else{
                this.$(".oe_dial_phonecalls > .oe_dial_phonecall")
                    .each(function(key,phonecall){
                        if($(phonecall).data('state') != 'done'){
                            self.sip_js.call(self.phonecalls[$(phonecall).data('id')]);
                            return false;
                        }
                    });
                if(phonecall_id){
                    /*
                    //JS Ari lib
                    this.ari_client.call(this.phonecalls[phonecall_id],function(channel){
                        console.log("after the call")
                        self.phonecall_channel = channel;
                    });
                    */
                    
                }
            }
        },

        auto_call_button: function(){
            this.$(".oe_dial_split_callbutton").hide();
            this.$(".oe_dial_stop_autocall_button").show();
            this.sip_js.automatic_call(this.phonecalls);
        },

        stop_auto_call_button: function(){
            this.sip_js.stop_automatic_call();
        },

        //action done when the button "Hang Up" is clicked
        hangup_button: function(){
            this.sip_js.hangup();
            self.$(".popover").remove();
            /*
            var phonecall_model = new openerp.web.Model("crm.phonecall");
            if(this.$el.find(".oe_dial_selected_phonecall").find(".phonecall_id").text() != ''){
                var phonecall_id = this.$el.find(".oe_dial_selected_phonecall").find(".phonecall_id").text();
                phonecall_model.call("hangup_call", [this.phonecalls[phonecall_id].id]).then(function(phonecall){
                    openerp.web.bus.trigger('reload_panel');
                });
                //this.ari_client.hangup(this.phonecall_channel);
                this.sip_js.hangup();
            }else if(this.$el.find(".oe_dial_phonecalls > div:first-child").find(".phonecall_id").text()){
                var phonecall_id = this.$el.find(".oe_dial_phonecalls > div:first-child").find(".phonecall_id").text();
                phonecall_model.call("hangup_call", [this.phonecalls[phonecall_id].id]).then(function(phonecall){
                    openerp.web.bus.trigger('reload_panel');
                });
                //this.ari_client.hangup(this.phonecall_channel);
                this.sip_js.hangup();
            }*/
        },

        //action done when the button "Transfer" is clicked
        transfer_button: function(){
            //this.sip_js.transfer();

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
            });
        },

        //action done when the transfer_call action is triggered
        transfer_call: function(number){
            this.sip_js.transfer(number);
        },

        //action done when the button "Reschedule Call" is clicked
        schedule_call: function(){
            var id = this.$(".oe_dial_selected_phonecall").data().id;
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
            var id = this.$(".oe_dial_selected_phonecall").data().id;
            var self = this;
            openerp.client.action_manager.do_action({
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                src_model: 'crm.phonecall',
                multi: "True",
                target: 'new',
                key2: 'client_action_multi',
                //TODO default_composition_mode? comment or mass_mail?
                //TODO Problem if comment and no opportunity linked
                //problem if mass_mail to get object information
                context: {
                            'default_composition_mode': 'comment',
                            'default_email_to': this.phonecalls[id].partner_email,
                            'default_model': 'crm.lead',
                            'default_res_id': this.phonecalls[id].opportunity_id,
                            'default_partner_ids': [this.phonecalls[id].partner_id],
                        },
                views: [[false, 'form']],
            });
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
        openerp.web.bus.trigger('reload_panel');
        //Return an action to close the wizard after the reload of the panel
        return { type: 'ir.actions.act_window_close' };
    };

    openerp.crm_voip.transfer_call = function(parent, action){
        var params = action.params || {};
        openerp.web.bus.trigger('transfer_call', params.number);
        return { type: 'ir.actions.act_window_close' };
    };

    openerp.crm_voip.select_call = function(parent, action){
        var params = action.params || {};
        openerp.web.bus.trigger('select_call', params.phonecall_id);
    };

    instance.web.client_actions.add("reload_panel", "openerp.crm_voip.reload_panel");
    instance.web.client_actions.add("transfer_call","openerp.crm_voip.transfer_call");
    instance.web.client_actions.add("select_call","openerp.crm_voip.select_call");
    return crm_voip;
};