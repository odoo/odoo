
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
                if(phonecall.partner_name.length < 20){
                    this.set("partner", phonecall.partner_name);
                }else{
                    var partner_name = phonecall.partner_name.substring(0,19) + '...';
                    this.set("partner", partner_name);
                } 
            }else{
                this.set("partner", "Unknown");
            }
            this.set("state",phonecall.state);
            this.set("image_small", phonecall.partner_image_small);
            this.set("inCall", inCall); 
            this.set("email",phonecall.partner_email);
            if(phonecall.name.length < 24){
                this.set("name", phonecall.name);
            }else{
                var name = phonecall.name.substring(0,23) + '...';
                this.set("name", name);
            } 
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
            this.set("current_search", "");
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
            openerp.web.bus.on('reload_panel', this, this.search_phonecalls_status);
            openerp.web.bus.on('transfer_call',this,this.transfer_call);
            openerp.web.bus.on('select_call',this,this.select_call);
            return;
        },

        //Modify the phonecalls list when the search input changes
        input_change: function() {
            var self = this;
            _.each(this.phonecalls,function(phonecall){
                if(phonecall.partner_name.toLowerCase().indexOf(this.$(".oe_dial_searchbox").val().toLowerCase()) == -1 && 
                phonecall.name.toLowerCase().indexOf(this.$(".oe_dial_searchbox").val().toLowerCase()) == -1){
                    self.$el.find(".oe_dial_phonecall_partner_name").filter(function(){return $(this)[0].dataset.id == phonecall.id;}).parent().parent().hide();
                }else{
                    self.$el.find(".oe_dial_phonecall_partner_name").filter(function(){return $(this)[0].dataset.id == phonecall.id;}).parent().parent().show();
                }
            });
        },

        //Get the phonecalls and create the widget to put inside the panel
        search_phonecalls_status: function(refresh_by_user) {
            var self = this;
            //Hide the optional buttons
            if(this.buttonUp && !this.buttonAnimated){
                this.buttonAnimated = true;
                this.$el.find(".oe_dial_phonecalls").animate({
                    height: (this.$el.find(".oe_dial_phonecalls").height() + this.$el.find(".oe_dial_optionalbuttons").outerHeight()),
                }, 300,function(){
                    self.buttonUp = false;
                    self.buttonAnimated = false;
                });
            }
            new openerp.web.Model("crm.phonecall").call("get_list",[this.get("current_search")]).then(function(result){
                var old_widgets = self.widgets;                   
                self.widgets = {};
                self.phonecalls = {};

                if(result.phonecalls.length == 0){
                    self.$el.find(".oe_dial_callbutton").attr('disabled','disabled');
                    self.$el.find(".oe_call_dropdown").attr('disabled','disabled');
                }else{
                    self.$el.find(".oe_dial_callbutton").removeAttr('disabled');
                    self.$el.find(".oe_call_dropdown").removeAttr('disabled');
                }
                if(self.$el.find(".oe_dial_icon_inCall").length == 0){
                    self.$el.find(".oe_dial_transferbutton").attr('disabled','disabled');
                    self.$el.find(".oe_dial_hangupbutton").attr('disabled','disabled');
                }
                self.$el.find(".oe_dial_content").animate({
                    bottom: 0,
                });

                _.each(result.phonecalls, function(phonecall){
                    if(Date.parse(phonecall.date).getTime() <= Date.now()){
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
                _.each(old_widgets, function(w) {
                    w.destroy();
                });
            });
            
        },

        display_in_queue: function(phonecall){
            var inCall = false;
            //Check if the current phonecall is currently done to add the microphone icon
            if(this.$el.find(".oe_dial_phonecall_partner_name").filter(function(){return $(this)[0].dataset.id == phonecall.id;}).next(".oe_dial_icon_inCall").length != 0){
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
            var id = this.$el.find(".oe_dial_selected_phonecall").find(".oe_dial_phonecall_partner_name").data().id;
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
            var id = this.$el.find(".oe_dial_selected_phonecall").find(".oe_dial_phonecall_partner_name").data().id;
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
                var classes = phonecall_widget.$()[0].className.split(" ");
                self.$(".oe_dial_selected_phonecall").removeClass("oe_dial_selected_phonecall");
                if(classes.indexOf("oe_dial_selected_phonecall") == -1){
                    phonecall_widget.$()[0].className += " oe_dial_selected_phonecall";
                    if(!self.buttonUp){
                        this.buttonAnimated = true;
                        this.$el.find(".oe_dial_phonecalls").animate({
                            height: (this.$el.find(".oe_dial_phonecalls").height() - this.$el.find(".oe_dial_optionalbuttons").outerHeight()),
                        }, 300,function(){
                            self.buttonAnimated = false;
                            self.buttonUp = true;
                        });
                    }
                    this.$el.find(".oe_dial_email").css("display","none");
                    if(phonecall_widget.get('email')){
                        this.$el.find(".oe_dial_email").css("display","inline");
                        this.$el.find(".oe_dial_schedule_call").css("width", "49%");
                    }else{
                        this.$el.find(".oe_dial_schedule_call").css("width", "100%");
                    }
                }else{
                    this.buttonAnimated = true;
                    this.$el.find(".oe_dial_phonecalls").animate({
                        height: (this.$el.find(".oe_dial_phonecalls").height() + this.$el.find(".oe_dial_optionalbuttons").outerHeight()),
                    }, 300,function(){
                        self.buttonAnimated = false;
                        self.buttonUp = false;
                    });
                }
            } 
        },

        remove_phonecall: function(phonecall_widget){
            var phonecall_model = new openerp.web.Model("crm.phonecall");
            var phonecall_id = phonecall_widget.$().find(".oe_dial_phonecall_partner_name").data().id;
            var self = this;
            phonecall_model.call("remove_from_queue", [this.phonecalls[phonecall_id].id]).then(function(action){
                openerp.client.action_manager.do_action(action);
                self.$().find(".popover").remove();
            });
        },

        //action done when the button "call" is clicked
        call_button: function(){
            var self = this;
            var phonecall_id;
            if(this.$el.find(".oe_dial_selected_phonecall").find(".oe_dial_phonecall_partner_name").data() !== null){
                phonecall_id = this.$el.find(".oe_dial_selected_phonecall").find(".oe_dial_phonecall_partner_name").data().id;
                /*
                //JS Ari lib
                this.ari_client.call(this.phonecalls[phonecall_id],function(channel){
                    console.log("after the call")
                    self.phonecall_channel = channel;
                    console.log(self.phonecall_channel);
                });
                */
                this.sip_js.call(this.phonecalls[phonecall_id]);
            }else if(phonecall_id = this.$el.find(".oe_dial_phonecalls > div:first-child").find(".oe_dial_phonecall_partner_name").data() !== null){
                //phonecall_id = this.$el.find(".oe_dial_phonecalls > div:first-child").find(".oe_dial_phonecall_partner_name").data().id;
                phonecalls = this.$el.find(".oe_dial_phonecalls > .oe_dial_phonecall");
                console.log(phonecalls);
                _.each(phonecalls, function(phonecall){
                    if(phonecall.dataset.state != 'done'){
                        console.log("IF")
                        console.log(phonecall.dataset.id)
                        self.sip_js.call(self.phonecalls[phonecall.dataset.id]);
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
            this.$el.find(".oe_dial_split_callbutton").css("display","none");
            this.$el.find(".oe_dial_stop_autocall_button").css("display","inline-block");
            this.sip_js.automatic_call(this.phonecalls);
        },

        stop_auto_call_button: function(){
            this.sip_js.stop_automatic_call();
        },

        //action done when the button "Hang Up" is clicked
        hangup_button: function(){
            this.sip_js.hangup();
            self.$().find(".popover").remove();
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
            var id = this.$el.find(".oe_dial_selected_phonecall").find(".oe_dial_phonecall_partner_name").data().id;
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
            /*
            //Launch the Log Call wizard
            openerp.client.action_manager.do_action({
                type: 'ir.actions.act_window',
                key2: 'client_action_multi',
                src_model: "crm.phonecall",
                res_model: "crm.phonecall.log.wizard",
                multi: "True",
                target: 'new',
                context: {'phonecall_id': id,
                'default_description' : this.phonecalls[id].description,
                'default_opportunity_name' : this.phonecalls[id].opportunity_name,
                'default_opportunity_planned_revenue' : this.phonecalls[id].opportunity_planned_revenue,
                'default_opportunity_title_action' : this.phonecalls[id].opportunity_title_action,
                'default_opportunity_probability' : this.phonecalls[id].opportunity_probability,
                'default_partner_name' : this.phonecalls[id].partner_name,
                'default_partner_phone' : this.phonecalls[id].partner_phone,
                'default_partner_mobile' : this.phonecalls[id].partner_mobile,
                'default_partner_email' : this.phonecalls[id].partner_email,
                'default_partner_image_small' : this.phonecalls[id].partner_image_small,},
                views: [[false, 'form']],
            });*/
        },

        //action done when the button "Send Email" is clicked
        send_email: function(){
            var id = this.$el.find(".oe_dial_selected_phonecall").find(".oe_dial_phonecall_partner_name").data().id;
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