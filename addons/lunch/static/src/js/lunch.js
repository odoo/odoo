(function() {
    "use strict";

    var QWeb = openerp.web.qweb,
        lunch = openerp.lunch = {};

    lunch.previousorder = openerp.web.form.AbstractField.extend(openerp.web.form.ReinitializeWidgetMixin,{
        template : 'lunch.PreviousOrder',
        events: {
        'click span.add_button': 'set_order_line',
        },
        init: function(){
            this.lunch_data = {};
            this.feilds_to_read = ['product_id', 'supplier', 'note', 'price', 'category_id','currency_id'];
            return this._super.apply(this, arguments);
        },
        set_value: function(value_) {
            value_ = value_ || [];
            this._super((value_.length >= 1 && value_[0] instanceof Array)?value_[0][2]:value_);
        },
        set_lunchbox_value: function(data){
            var self = this;
            _.each(data, function(datum){
                datum['product_id'] = datum['product_id'][0];
                datum['supplier'] = datum['supplier'][0];
                self.lunch_data[datum['id']] = datum;
            });
        },
        fetch_value: function(){
            var self = this;
            return new openerp.web.Model("lunch.order.line").call('read',[this.get_value(), this.feilds_to_read])
                .done(function(data){ self.set_lunchbox_value(data);});
        },
        set_order_line: function(event){
            var records = this.field_manager.get_field_value('order_line_ids');
            records.push([0, 0, this.lunch_data[parseInt($(event.currentTarget).attr('id'))]]);
            this.field_manager.set_values({order_line_ids: records});
            this.getParent().do_notify_change();
        },
        render_value: function() {
            var self = this;
            return this.fetch_value().done(function(data) {
                if (_.isEmpty(data)) {
                    return self.$el.html(QWeb.render("lunch.no_preference_ids"));
                }
                self.$el.html(QWeb.render("lunch.PreviousOrderLine", {'categories': _.groupBy(data,function(data1){return data1['category_id'][1];})}));
             });
        },
    });
    openerp.web.form.widgets.add('previous_order', 'openerp.lunch.previousorder');
})();