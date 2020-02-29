odoo.define('pos_restaurant.splitbill', function (require) {
"use strict";

var gui = require('point_of_sale.gui');
var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var core = require('web.core');

var QWeb = core.qweb;

var SplitbillScreenWidget = screens.ScreenWidget.extend({
    template: 'SplitbillScreenWidget',

    previous_screen: 'products',

    renderElement: function(){
        var self = this;
        var linewidget;

        this._super();
        var order = this.pos.get_order();
        if(!order){
            return;
        }
        var orderlines = order.get_orderlines();
        for(var i = 0; i < orderlines.length; i++){
            var line = orderlines[i];
            linewidget = $(QWeb.render('SplitOrderline',{ 
                widget:this, 
                line:line, 
                selected: false,
                quantity: 0,
                id: line.id,
            }));
            linewidget.data('id',line.id);
            this.$('.orderlines').append(linewidget);
        }
        this.$('.back').click(function(){
            self.gui.show_screen(self.previous_screen);
        });
    },

    split_quantity: function(split, line, splitlines) {
        if( !line.get_unit().is_pos_groupable ){
            if( split.quantity !== line.get_quantity()){
                split.quantity = line.get_quantity();
            }else{
                split.quantity = 0;
            }
        }else{
            if( split.quantity < line.get_quantity()){
                split.quantity += line.get_unit().is_pos_groupable ? 1 : line.get_unit().rounding;
                if(split.quantity > line.get_quantity()){
                    split.quantity = line.get_quantity();
                }
            }else{
                split.quantity = 0;
            }
        }
    },

    set_line_on_order: function(neworder, split, line) {
        if( split.quantity ){
            if ( !split.line ){
                split.line = line.clone();
                neworder.add_orderline(split.line);
            }
            split.line.set_quantity(split.quantity, 'do not recompute unit price');
        }else if( split.line ) {
            neworder.remove_orderline(split.line);
            split.line = null;
        }
    },

    lineselect: function($el,order,neworder,splitlines,line_id){
        var split = splitlines[line_id] || {'quantity': 0, line: null};
        var line  = order.get_orderline(line_id);

        this.split_quantity(split, line, null);

        this.set_line_on_order(neworder, split, line);

        splitlines[line_id] = split;
        $el.replaceWith($(QWeb.render('SplitOrderline',{
            widget: this,
            line: line,
            selected: split.quantity !== 0,
            quantity: split.quantity,
            id: line_id,
        })));
        this.$('.order-info .subtotal').text(this.format_currency(neworder.get_subtotal()));
    },

    check_full_pay_order: function (order, splitlines) {
        return _.every(order.get_orderlines(), function(orderLine) {
            var split = splitlines[orderLine.id];
            return split && split.quantity === orderLine.get_quantity();
        });
    },

    set_quantity_on_order: function(splitlines, order) {
        for(var id in splitlines){
            var split = splitlines[id];
            var line  = order.get_orderline(parseInt(id));
            line.set_quantity(line.get_quantity() - split.quantity, 'do not recompute unit price');
            if(Math.abs(line.get_quantity()) < 0.00001){
                order.remove_orderline(line);
            }
            delete splitlines[id];
        }
    },

    pay: function(order,neworder,splitlines){
        if(_.isEmpty(splitlines))    // Splitlines is empty
            return;

        delete neworder.temporary;

        if(this.check_full_pay_order(order, splitlines)){
            this.gui.show_screen('payment');
        }else{
            this.set_quantity_on_order(splitlines, order);

            neworder.set_screen_data('screen','payment');

            // for the kitchen printer we assume that everything
            // has already been sent to the kitchen before splitting
            // the bill. So we save all changes both for the old
            // order and for the new one. This is not entirely correct
            // but avoids flooding the kitchen with unnecessary orders.
            // Not sure what to do in this case.

            if ( neworder.saveChanges ) {
                order.saveChanges();
                neworder.saveChanges();
            }

            neworder.set_customer_count(1);
            order.set_customer_count(order.get_customer_count() - 1);
            order.set_screen_data('screen','products');

            this.pos.get('orders').add(neworder);
            this.pos.set('selectedOrder',neworder);
        }
    },
    show: function(){
        var self = this;
        this._super();
        this.renderElement();

        var order = this.pos.get_order();
        var neworder = new models.Order({},{
            pos: this.pos,
            temporary: true,
        });
        neworder.set('client',order.get('client'));

        var splitlines = {};

        this.$('.orderlines').on('click','.orderline',function(){
            var id = parseInt($(this).data('id'));
            var $el = $(this);
            self.lineselect($el,order,neworder,splitlines,id);
        });

        this.$('.paymentmethods .button').click(function(){
            self.pay(order,neworder,splitlines);
        });
    },
});

gui.define_screen({
    'name': 'splitbill',
    'widget': SplitbillScreenWidget,
    'condition': function(){
        return this.pos.config.iface_splitbill;
    },
});

var SplitbillButton = screens.ActionButtonWidget.extend({
    template: 'SplitbillButton',
    button_click: function(){
        if(this.pos.get_order().get_orderlines().length > 0){
            this.gui.show_screen('splitbill');
        }
    },
});

screens.define_action_button({
    'name': 'splitbill',
    'widget': SplitbillButton,
    'condition': function(){
        return this.pos.config.iface_splitbill;
    },
});

return {
    SplitbillButton: SplitbillButton,
    SplitbillScreenWidget: SplitbillScreenWidget,
}

});

