(function() {
    "use strict";

    var QWeb = openerp.web.qweb,
        lunch = openerp.lunch = {};

    lunch.previousorder = openerp.web.form.AbstractField.extend(openerp.web.form.ReinitializeWidgetMixin,{
        template : 'lunch.PreviousOrder',
        set_value: function(value_) {
            value_ = value_ || [];
            if(value_.length >= 1 && value_[0] instanceof Array) {
                value_ = value_[0][2];
            }
            this._super(value_);
        },
        render_value: function() {
            var self = this;
            var category = {};
            new openerp.web.Model("lunch.order.line").call('read',[self.get_value(),['product_id', 'supplier', 'note', 'price', 'category_id','currency_id']])
            .then(function(data) {
                if (_.isEmpty(data)) {
                    self.$el.html(QWeb.render("lunch.no_preference_ids"));
                } else {
                    var product_line = {};
                    _.each(data, function(data){
                        product_line[data['id']] = data;
                    });
                    category = _.groupBy(data,function(data1){return data1['category_id'][1];});
                    self.$el.html(QWeb.render("lunch.PreviousOrderLine", {'categories': category, 'currency': data[0]['currency_id'][1]}));
                    self.$el.find('span.add_button').click( function(event) {
                        var pref_id = $(event.currentTarget).attr('id');
                        var records = self.field_manager.get_field_value('order_line_ids');
                        records.push([0, 0, {'product_id': product_line[pref_id]['product_id'][0], 'note': product_line[pref_id]['note'], 'supplier': product_line[pref_id]['supplier'][0], 'price': product_line[pref_id]['price']}]);
                        self.field_manager.set_values({order_line_ids: records});
                    });
                 }
             });
        },
    });
    openerp.web.form.widgets.add('previous_order', 'openerp.lunch.previousorder');
})();