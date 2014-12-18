function openerp_restaurant_notes(instance,module){
    "use strict";

    var QWeb = instance.web.qweb;
    var _t   = instance.web._t;

    var _super_orderline = module.Orderline.prototype;

    module.Orderline = module.Orderline.extend({
        initialize: function(attr, options) {
            _super_orderline.initialize.call(this,attr,options);
            this.note = this.note || "";
        },
        set_note: function(note){
            this.note = note;
            this.trigger('change',this);
        },
        get_note: function(note){
            return this.note;
        },
        can_be_merged_with: function(orderline) {
            if (orderline.get_note() !== this.get_note()) {
                return false;
            } else {
                return _super_orderline.can_be_merged_with.call(this,orderline);
            }
        },
        clone: function(){
            var orderline = _super_orderline.clone.call(this);
            orderline.note = this.note;
            return orderline;
        },
        export_as_JSON: function(){
            var json = _super_orderline.export_as_JSON.call(this);
            json.note = this.note;
            return json;
        },
        init_from_JSON: function(json){
            _super_orderline.init_from_JSON.apply(this,arguments);
            this.note = json.note;
        },
    });

    module.PosWidget.include({
        orderline_note_click: function(){
            var self = this;
            var line = this.pos.get_order().get_selected_orderline();

            if (line) {
                this.screen_selector.show_popup('textarea',{
                    message: _t('Orderline Note'),
                    value:   line.get_note(),
                    confirm: function(note) {
                        line.set_note(note);
                    },
                });
            }
        },
        build_widgets: function(){
            var self = this;
            this._super();

            if (this.pos.config.iface_orderline_notes) {
                var button = $(QWeb.render('OrderlineNoteButton'));
                button.click(function(){ self.orderline_note_click(); });
                button.appendTo(this.$('.control-buttons'));
                this.$('.control-buttons').removeClass('oe_hidden');
            }
        },
    });
}
