(function() {

    "use strict";

    var QWeb = openerp.web.qweb,
        lunch = openerp.lunch = {};

    lunch.previousorder = openerp.web.form.FormWidget.extend(openerp.web.form.ReinitializeWidgetMixin,{
        template : 'lunch.PreviousOrder',
        update_lines: function (pref_id, records) {
            var self = this;
            new openerp.web.Model("lunch.order.line").call('read', [parseInt(pref_id), ['product_id', 'supplier', 'note', 'price']])
                .then(function(res){
                    if (res.id == parseInt(pref_id)) {
                        if(res.note == 'false') { res.note = ''; }
                        records.push([0, 0, {'product_id': res.product_id[0], 'note': res.note, 'supplier': res.supplier[0], 'price': res.price}]);
                        self.field_manager.set_values({order_line_ids: records});
                    }
            });
        },
        initialize_content: function() {
            this.render_value();
        },
        render_value: function() {
            var self = this;
            new openerp.web.Model("lunch.order").call("get_previous_lunch_order_details")
                .then(function(data) {
                if (_.isEmpty(data)) {
                    self.$el.html(QWeb.render("lunch.no_preference_ids"));
                } else {
                    self.$el.html(QWeb.render("lunch.PreviousOrderLine", {'categories': data.categories, 'currency': data.currency}));
                    self.$el.find('span.add_button').click( function(event) {
                        var pref_id = $(event.currentTarget).attr('id');
                        var records = self.field_manager.get_field_value('order_line_ids');
                        self.update_lines(pref_id, records);
                    });
                }
            });
        },
    });

    openerp.web.form.custom_widgets.add('lunch_previous_order_widget', 'openerp.lunch.previousorder');
})();
