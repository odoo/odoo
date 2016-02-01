openerp.pos_restaurant.load_notes = function(instance,module){
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
                return _super_orderline.can_be_merged_with.apply(this,arguments);
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

    module.OrderlineNoteButton = module.ActionButtonWidget.extend({
        template: 'OrderlineNoteButton',
        button_click: function(){
            var line = this.pos.get_order().get_selected_orderline();
            if (line) {
                this.gui.show_popup('textarea',{
                    title: _t('Add Note'),
                    value:   line.get_note(),
                    confirm: function(note) {
                        line.set_note(note);
                    },
                });
            }
        },
    });

    module.define_action_button({
        'name': 'orderline_note',
        'widget': module.OrderlineNoteButton,
        'condition': function(){
            return this.pos.config.iface_orderline_notes;
        },
    });
};

