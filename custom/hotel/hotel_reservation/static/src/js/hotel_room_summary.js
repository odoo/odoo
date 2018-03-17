odoo.define('hotel_reservation.hotel_room_summary', function (require) {

var core = require('web.core');
var data = require('web.data');
var ActionManager = require('web.ActionManager');
var form_common = require('web.form_common');
var time = require('web.time');
var _t = core._t;
var QWeb = core.qweb;
    
var RoomSummary = form_common.FormWidget.extend(form_common.ReinitializeWidgetMixin, {
        display_name: _t('Form'),
        view_type: "form",
        init: function() {
            this._super.apply(this, arguments);
            if(this.field_manager.model == "room.reservation.summary")
            {
                $(".oe_view_manager_buttons").hide();
                $(".oe_view_manager_header").hide();
               }
            this.set({
                date_to: false,
                date_from: false,
                summary_header: false,
                room_summary: false,
            });
            this.summary_header = [];
            this.room_summary = [];
            this.field_manager.on("field_changed:date_from", this, function() {
                this.set({"date_from": time.str_to_datetime(this.field_manager.get_field_value("date_from"))});
            });
            this.field_manager.on("field_changed:date_to", this, function() {
                this.set({"date_to": time.str_to_datetime(this.field_manager.get_field_value("date_to"))});
            });
            
            this.field_manager.on("field_changed:summary_header", this, function() {
                this.set({"summary_header": this.field_manager.get_field_value("summary_header")});
            });
            this.field_manager.on("field_changed:room_summary", this, function() {
                this.set({"room_summary":this.field_manager.get_field_value("room_summary")});
            });
        },
        
        initialize_field: function() {
            
            form_common.ReinitializeWidgetMixin.initialize_field.call(this);
            var self = this;
            self.on("change:summary_header", self, self.initialize_content);
            self.on("change:room_summary", self, self.initialize_content);
        },
        
      initialize_content: function() {
           var self = this;
           if (self.setting)
               return;
           
           if (!this.summary_header || !this.room_summary)
                  return
           // don't render anything until we have summary_header and room_summary
                  
           this.destroy_content();
           
           if (this.get("summary_header")) {
            this.summary_header = py.eval(this.get("summary_header"));
           }
           if (this.get("room_summary")) {
            this.room_summary = py.eval(this.get("room_summary"));
           }
               
           this.renderElement();
           this.view_loading();
        },
        
        view_loading: function(r) {
            return this.load_form(r);
        },
        
        load_form: function(data) {
            self.action_manager = new ActionManager(self);
            
            this.$el.find(".table_free").bind("click", function(event){
                self.action_manager.do_action({
                        type: 'ir.actions.act_window',
                        res_model: "quick.room.reservation",
                        views: [[false, 'form']],
                        target: 'new',
                        context: {"room_id": $(this).attr("data"), 'date': $(this).attr("date")},
                });
            });
        
        },
       
        renderElement: function() {
             this.destroy_content();
             this.$el.html(QWeb.render("summaryDetails", {widget: this}));
        }     
    });

core.form_custom_registry.add('Room_Reservation', RoomSummary);
});
