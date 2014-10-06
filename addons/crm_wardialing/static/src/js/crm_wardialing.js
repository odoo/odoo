

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
                       
        },
        start: function() {
            this.$el.data("phonecall", {id:this.get("id"), partner:this.get("partner")});
            this.$el.draggable({helper: "clone"});
        },

        //Action when we click on a phonecall to be redirect to the linked opportunity
        to_leads: function() {
            if(this.get("opportunity_id")){
                this.trigger("to_leads", this.get("opportunity_id"));
            }
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
        },
        start: function() {
            var self = this;
            
            this.$el.css("bottom", -this.$el.outerHeight());
            $(window).scroll(_.bind(this.calc_box, this));
            $(window).resize(_.bind(this.calc_box, this));
            this.calc_box();
            
            this.on("change:current_search", this, this.search_phonecalls_status);
            this.search_phonecalls_status();
            this.$el.find(".oe_dial_callbutton").click(function() {
                self.call_button();
            });
            this.$el.find(".oe_dial_changelog").click(function() {
                self.change_log();
            });
            this.$el.find(".oe_dial_email").click(function() {
                self.send_email();
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

            //hide the option to edit the logs
            this.$el.find(".oe_dial_changelog").css("display","none");
            this.$el.find(".oe_dial_email").css("display","none");

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
                        new openerp.web.Model("res.partner").query(["name","image_small","email"])
                            .filter([["id","=",phonecall.partner_id[0]]])
                            .first().then(function(partner){
                                    var widget = new openerp.crm_wardialing.PhonecallWidget(self, phonecall,partner.image_small, partner.email);
                                    widget.appendTo(self.$(".oe_dial_phonecalls"));
                                    widget.on("select_call", self, self.select_call);
                                    self.widgets[phonecall.id] = widget;
                                    if(! phonecall.description){
                                        phonecall.description = "There is no description";
                                    }
                                    $("[rel='popover']").popover({
                                        placement : 'right', // top, bottom, left or right
                                        title : 'Opportunity: ' + phonecall.opportunity_id[1], 
                                        html: 'true', 
                                        content : '<img src="data:image/jpg;base64,'+partner.image_small+'"</img><div id="popOverBox">' + phonecall.description +'</div>'
                                    });
                                    self.phonecalls[phonecall.id] = phonecall;
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

        //action to change the main view to go to the opportunity view
        to_leads: function(opportunity_id) {
            openerp.client.action_manager.do_action({
                type: 'ir.actions.act_window',
                res_model: "crm.lead",
                res_id: opportunity_id,
                views: [[false, 'form']],
                target: 'current',
                context: {},
            });
        },

        select_call: function(phonecall_widget){
            self.$(".oe_dial_selected_phonecall").removeClass("oe_dial_selected_phonecall");
            phonecall_widget.$()[0].className += " oe_dial_selected_phonecall";

            this.$el.find(".oe_dial_changelog").css("display","inline");
            this.$el.find(".oe_dial_email").css("display","none");
            if(phonecall_widget.get('email')){
                this.$el.find(".oe_dial_email").css("display","inline");
            }
        },

        //action done when the button "call" is clicked
        call_button: function(){
            console.log(this.phonecalls[0]);
            var phonecall_model = new openerp.web.Model("crm.phonecall");
            phonecall_model.call("call_partner", [this.phonecalls[0].id]).then(function(phonecall){
                console.log("after the call")
            });
            
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
                            'default_composition_mode': 'mass_mail',
                            'default_email_to': widget.get('email'),
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
                        $('.oe_dial_header_refresh_icon').parent().on("click", dial, _.bind(dial.search_phonecalls_status, dial));
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
                this.$el.find(".oe_dial_lead_to_call_center_button_icon").parent().click(function() {
                    var lead_model = new openerp.web.Model("crm.lead");
                    lead_model.call("create_call_center_call", [self.id]);
                    
                });
            }

        },
    });
    



    
    return crm_wardialing;


};

