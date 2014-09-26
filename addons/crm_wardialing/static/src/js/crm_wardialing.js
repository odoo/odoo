(function(){
    
    
    
    var _t = openerp._t;
    var _lt = openerp._lt;
    var QWeb = openerp.qweb;
    var CALLS_LIMIT = 20;
    var crm_wardialing = openerp.crm_wardialing = {};
    
    
    crm_wardialing.PhonecallWidget = openerp.Widget.extend({
        "template": "crm_wardialing.PhonecallWidget",
        events: {
            "click": "to_leads",
        },
        init: function(parent, phonecall, image_small) {
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


                       
        },
        start: function() {
            this.$el.data("phonecall", {id:this.get("id"), partner:this.get("partner")});
            this.$el.draggable({helper: "clone"});
        },
        to_leads: function() {
            if(this.get("opportunity_id")){
                this.trigger("to_leads", this.get("opportunity_id"));
            }
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
            this.phonecalls = [];
            this.widgets = {};
            this.phonecall_search_dm = new openerp.web.DropMisordered();
            
            
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
        search_phonecalls_status: function(e) {
            var phonecall_model = new openerp.web.Model("crm.phonecall");
            var self = this;
            return phonecall_model.query(['id', 'partner_id', 'to_call', 'description', 'opportunity_id'])
                .filter([['to_call','=',true],['partner_id', 'ilike', this.get("current_search")]])
                .limit(CALLS_LIMIT)
                .all().then(function(result) {
                    self.$(".oe_dial_input").val("");
                    var old_widgets = self.widgets;
                    self.widgets = {};
                    self.phonecalls = [];
                    _.each(result, function(phonecall) {
                        new openerp.web.Model("res.partner").query(["name","image_small"])
                            .filter([["id","=",phonecall.partner_id[0]]])
                            .all().then(function(partners){
                                _.each(partners,function(partner){

                                    var widget = new openerp.crm_wardialing.PhonecallWidget(self, phonecall,partner.image_small);
                                    widget.appendTo(self.$(".oe_dial_phonecalls"));
                                    widget.on("to_leads", self, self.to_leads);
                                    self.widgets[phonecall.id] = widget;
                                    self.phonecalls.push(phonecall);
                                    if(! phonecall.description){
                                        phonecall.description = "There is no description";
                                    }
                                    $("[rel='popover']").popover({
                                        placement : 'right', // top, bottom, left or right
                                        title : 'Opportunity: ' + phonecall.opportunity_id[1], 
                                        html: 'true', 
                                        content : '<img src="data:image/jpg;base64,'+partner.image_small+'"</img><div id="popOverBox">' + phonecall.description +'</div>'
                                    });
                                                                            
                                });
                            });
                    });
                    _.each(old_widgets, function(w) {
                        w.destroy();
                    });
                });
        },
        switch_display: function() {
            this.calc_box();
            
            if (this.shown) {
                this.$el.animate({
                    bottom: -this.$el.outerHeight(),
                });
            } else {
               
                // update the list of user status when show the IM
                this.search_phonecalls_status();
                this.$el.animate({
                    bottom: 0,
                });
            }
            this.shown = ! this.shown;
        },
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

        call_button: function(){
            console.log("CLICK CALL BUTTON")
        },
    });

    

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
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
    }

    return crm_wardialing;
})();