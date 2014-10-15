

openerp.crm_wardialing = function(instance) {
    
    
    
    var _t = openerp._t;
    var _lt = openerp._lt;
    var QWeb = openerp.qweb;
    var CALLS_LIMIT = 20;
    var crm_wardialing = openerp.crm_wardialing = {};
    
    
    crm_wardialing.PhonecallWidget = openerp.Widget.extend({
        "template": "crm_wardialing.PhonecallWidget",
        events: {
            "click": "select_call",
        },
        init: function(parent, phonecall, image_small, email) {
            this._super(parent);
            this.set("id", phonecall.id);
            if(phonecall.partner_id){
                this.set("partner", phonecall.partner_id[1]);
            }else{
                this.set("partner", "There is no contact linked");
            }

            if(phonecall.description){
                this.set("description", phonecall.description);
            }else{
                this.set("description", "There is no description");
            }
            
            if(phonecall.opportunity_id){
                this.set("opportunity", phonecall.opportunity_id[1]);
                this.set("opportunity_id", phonecall.opportunity_id[0]);
            }else{
                this.set("opportunity", "No opportunity linked");
            }
            this.set("image_small", image_small);
            this.set("email", email);
            if(phonecall.opportunity_id[1].length < 24){
                this.set("opportunity", phonecall.opportunity_id[1]);
            }else{
                var opportunity = phonecall.opportunity_id[1].substring(0,23) + '...';
                this.set("opportunity", opportunity);
            }
            
                       
        },
        start: function() {
            this.$el.data("phonecall", {id:this.get("id"), partner:this.get("partner")});
            this.$el.draggable({helper: "clone"});
        },

        //select the clicked call, show options and put some highlight on it
        select_call: function(){
            this.trigger("select_call", this)
        },
    });
    

    crm_wardialing.DialingPanel = openerp.Widget.extend({
        template: "crm_wardialing.DialingPanel",
        events: {
            "keydown .oe_dial_searchbox": "input_change",
            "keyup .oe_dial_searchbox": "input_change",
            "change .oe_dial_searchbox": "input_change",
        },
        init: function(parent) {
            
            this._super(parent);
            this.shown = false;
            this.set("current_search", "");
            this.phonecalls = {};
            this.widgets = {};
            this.formatCurrency;
        },
        start: function() {
            var self = this;
            
            //To get the formatCurrency function from the server
            new instance.web.Model("res.currency")
                .call("get_format_currencies_js_function")
                .then(function(data) {
                    self.formatCurrency = new Function("amount, currency_id", data);
                    //update of the pannel's list
                    self.on("change:current_search", self, self.search_phonecalls_status);
                    self.search_phonecalls_status();
                });
            this.$el.css("bottom", -this.$el.outerHeight());
            $(window).scroll(_.bind(this.calc_box, this));
            $(window).resize(_.bind(this.calc_box, this));
            this.calc_box();
            
            
            this.$el.find(".oe_dial_callbutton").click(function() {
                self.call_button();
            });
            this.$el.find(".oe_dial_changelog").click(function() {
                self.change_log();
            });
            this.$el.find(".oe_dial_email").click(function() {
                self.send_email();
            });
            this.$el.find(".oe_dial_to_client").click(function() {
                self.to_client();
            });
            this.$el.find(".oe_dial_to_lead").click(function() {
                self.to_lead();
            });

            
            return;
        },
        calc_box: function() {
            var $topbar = window.$('#oe_main_menu_navbar'); // .oe_topbar is replaced with .navbar of bootstrap3
            var top = $topbar.offset().top + $topbar.height();
            top = Math.max(top - $(window).scrollTop(), 0);
            this.$el.css("left",0)
            
        },
        input_change: function() {
            this.set("current_search", this.$(".oe_dial_searchbox").val());
        },

        //Get the phonecalls and create the widget to put inside the panel
        search_phonecalls_status: function() {
            var phonecall_model = new openerp.web.Model("crm.phonecall");

            this.$el.find(".oe_dial_phonecalls").css('height','280px');

            var self = this;

            return phonecall_model.query(['id', 'partner_id', 'to_call', 'description', 'opportunity_id'])
                .filter([['to_call','=',true],['partner_id', 'ilike', this.get("current_search")]])
                .limit(CALLS_LIMIT)
                .all().then(function(result) {
                    self.$(".oe_dial_input").val("");
                    var old_widgets = self.widgets;                   
                    self.widgets = {};
                    self.phonecalls = {};
                    _.each(result, function(phonecall) {
                        new openerp.web.Model("res.partner").query(["name","image_small","email", "title", "phone", "mobile"])
                            .filter([["id","=",phonecall.partner_id[0]]])
                            .first().then(function(partner){
                                    var opportunity = new openerp.web.Model("crm.lead").query(["name","priority","planned_revenue","title_action","company_currency","probability"])
                                        .filter([["id","=",phonecall.opportunity_id[0]]])
                                        .first().then(function(opportunity){
                                            var widget = new openerp.crm_wardialing.PhonecallWidget(self, phonecall,partner.image_small, partner.email);
                                            widget.appendTo(self.$(".oe_dial_phonecalls"));
                                            widget.on("select_call", self, self.select_call);
                                            self.widgets[phonecall.id] = widget;
                                            if(! phonecall.description){
                                                phonecall.description = "There is no description";
                                            }
                                            if(! partner.title){
                                                var partner_name = partner.name;
                                            }else{
                                                var partner_name = partner.title[1] + ' ' + partner.name;
                                            }
                                            var empty_star = 4 - parseInt(opportunity.priority);
                                            $("[rel='popover']").popover({
                                                placement : 'right', // top, bottom, left or right
                                                title : QWeb.render("crm_wardialing_Tooltip_title", {
                                                    opportunity: phonecall.opportunity_id[1], priority: parseInt(opportunity.priority), empty_star:empty_star}), 
                                                html: 'true', 
                                                content :  QWeb.render("crm_wardialing_Tooltip",{
                                                    partner_name: partner_name,
                                                    phone: partner.phone,
                                                    mobile: partner.mobile,
                                                    email: partner.email,
                                                    title_action: opportunity.title_action,
                                                    planned_revenue: self.formatCurrency(opportunity.planned_revenue, opportunity.company_currency[0]),
                                                    probability: opportunity.probability
                                                }),
                                            });
                                            self.phonecalls[phonecall.id] = phonecall;

                                            

                                    });
                            });
                    });

                    _.each(old_widgets, function(w) {
                        w.destroy();
                    });
                });
        },

        //function that will display the panel
        switch_display: function() {
            this.calc_box();
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
            var id = this.$el.find(".oe_dial_selected_phonecall").find(".phonecall_id").text();
            var phonecall = this.phonecalls[id];
            //Call of the function xmlid_to_res_model_res_id to get the id of the opportunity's form view and not the lead's form view
            new instance.web.Model("ir.model.data").call("xmlid_to_res_model_res_id",["crm.crm_case_form_view_oppor"]).then(function(data){
                openerp.client.action_manager.do_action({
                    type: 'ir.actions.act_window',
                    res_model: "crm.lead",
                    res_id: phonecall.opportunity_id[0],
                    views: [[data[1], 'form']],
                    target: 'current',
                    context: {},
                });
            })
            
        },

        //action to change the main view to go to the client's view
        to_client: function() {
            var id = this.$el.find(".oe_dial_selected_phonecall").find(".phonecall_id").text();
            var phonecall = this.phonecalls[id];
            
            openerp.client.action_manager.do_action({
                type: 'ir.actions.act_window',
                res_model: "res.partner",
                res_id: phonecall.partner_id[0],
                views: [[false, 'form']],
                target: 'current',
                context: {},
            });
        },

        //action to select a call and display the specific actions
        select_call: function(phonecall_widget){
            var classes = phonecall_widget.$()[0].className.split(" ");
            
            
            self.$(".oe_dial_selected_phonecall").removeClass("oe_dial_selected_phonecall");
            if(classes.indexOf("oe_dial_selected_phonecall") == -1){
                phonecall_widget.$()[0].className += " oe_dial_selected_phonecall";
                this.$el.find(".oe_dial_phonecalls").animate({'height' : '225px'});   
                this.$el.find(".oe_dial_email").css("display","none");
                if(phonecall_widget.get('email')){
                    this.$el.find(".oe_dial_email").css("display","inline");
                    this.$el.find(".oe_dial_changelog").css("width", "45%");
                }else{
                    this.$el.find(".oe_dial_changelog").css("width", "90%");
                }
            }else{
                this.$el.find(".oe_dial_phonecalls").animate({'height' : '280px'}); 
            }
            
        },

        //action done when the button "call" is clicked
        call_button: function(){
            var phonecall_model = new openerp.web.Model("crm.phonecall");
            
            if(this.$el.find(".oe_dial_selected_phonecall").find(".phonecall_id").text() != ''){
                var phonecall_id = this.$el.find(".oe_dial_selected_phonecall").find(".phonecall_id").text();
                console.log(phonecall_id);
                phonecall_model.call("call_partner", [this.phonecalls[phonecall_id].id]).then(function(phonecall){
                    console.log("after the call")
                });  
            }else{
                var phonecall_id = this.$el.find(".oe_dial_phonecalls > div:first-child").find(".phonecall_id").text();
                console.log(phonecall_id);
                phonecall_model.call("call_partner", [this.phonecalls[phonecall_id].id]).then(function(phonecall){
                    console.log("after the call")
                });
            }
            
            
            
        },

        //action done when the button "Call Log" is clicked
        change_log: function(){
            var id = this.$el.find(".oe_dial_selected_phonecall").find(".phonecall_id").text();
            console.log(this.phonecalls[id]);
            openerp.client.action_manager.do_action({
                type: 'ir.actions.act_window',
                key2: 'client_action_multi',
                src_model: "crm.phonecall",
                res_model: "crm.phonecall.log.wizard",
                multi: "True",
                target: 'new',
                context: {'phonecall_id': id, 'phonecall' : this.phonecalls[id]},
                views: [[false, 'form']],
            });
        },

        //action done when the button "Send Email" is clicked
        send_email: function(){
            console.log("EMAIL");
            var id = this.$el.find(".oe_dial_selected_phonecall").find(".phonecall_id").text();
            var widget = this.widgets[this.phonecalls[id].id];

            console.log(widget.get('email'));
            openerp.client.action_manager.do_action({
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                src_model: 'crm.phonecall',
                multi: "True",
                target: 'new',
                key2: 'client_action_multi',
                context: {
                            'default_composition_mode': 'comment',
                            'default_email_to': widget.get('email'),
                            'default_model': 'crm.lead',
                            'default_res_id': this.phonecalls[id].opportunity_id[0],
                            'default_partner_ids': [this.phonecalls[id].partner_id[0]],
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
                        var dial = new openerp.crm_wardialing.DialingPanel(self);
                        openerp.crm_wardialing.single = dial;
                        dial.appendTo(openerp.client.$el);
                        $('.oe_topbar_dialbutton_icon').parent().on("click", dial, _.bind(dial.switch_display, dial));
                        
                        //bind the action to retrieve the panel with the button in the header of the panel
                        $('.oe_dial_header_dialbutton_icon').parent().on("click", dial, _.bind(dial.switch_display, dial));

                        //bind the action to refresh the panel information
                        $('.oe_dial_search_icon').parent().on("click", dial, _.bind(dial.search_phonecalls_status, dial));
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
    }

    
    //Action of the button added in the Kanban view of the opportunities
    instance.web_kanban.KanbanRecord.include({
        
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            if (this.view.dataset.model === 'crm.lead') {              
                this.$el.find(".oe_dial_link_icon").click(function(e) {
                    e.stopPropagation();

                    self.$el.find(".oe_dial_lead_to_call_center_button").replaceWith('<i class="oe_dial_lead_to_call_center_button text-muted fa fa-phone"></i>');

                    var lead_model = new openerp.web.Model("crm.lead");
                    lead_model.call("create_call_center_call", [self.id]);
                });
            }

            this.$el.find(".oe_kanban_draghandle").mouseenter(
                function(){
                    self.$el.find(".oe_dial_hidden_button").css("visibility","visible");
            });
            this.$el.find(".oe_kanban_draghandle").mouseleave(
                function(){
                    self.$el.find(".oe_dial_hidden_button").css("visibility","hidden");
            });
        },
    });
    



    
    return crm_wardialing;


};

