odoo.define('pos_l10n_fr_split_bill.splitbill', function (require) {
"use strict";

    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var utils = require('web.utils');
    var SplitbillScreenWidget = require('pos_restaurant.splitbill').SplitbillScreenWidget;

    var _t = core._t;
    var round_di = utils.round_decimals;
    var QWeb = core.qweb;

    SplitbillScreenWidget.include({
        set_line_on_order: function(neworder, split, line) {
            if( split.quantity && this.pos.is_french_country()){
                if ( !split.line ){
                    split.line = line.clone();
                    neworder.add_orderline(split.line);
                }

                if(!this.pos.is_french_country())
                    split.line.set_quantity(split.quantity, 'do not recompute unit price');
                else
                    split.line.set_quantity(split.quantity);

            }else if( split.line && this.pos.is_french_country()) {
                neworder.remove_orderline(split.line);
                split.line = null;
            } else {
                this._super(neworder, split, line);
            }
        },

        set_quantity_on_order: function(splitlines, order) {
            if(this.pos.is_french_country()) {
                for(var id in splitlines){
                    var split = splitlines[id];
                    var line  = order.get_orderline(parseInt(id));

                    if(!this.pos.is_french_country()) {
                        line.set_quantity(line.get_quantity() - split.quantity);
                        if(Math.abs(line.get_quantity()) < 0.00001){
                            order.remove_orderline(line);
                        }
                    } else {
                        var decrease_line = line.clone();
                        decrease_line.order = order;
                        decrease_line.set_quantity(-split.quantity);
                        order.add_orderline(decrease_line);
                    }
                    delete splitlines[id];
                }
            } else {
                 this._super(splitlines, order);
            }
        },

        check_full_pay_order:function(order, splitlines) {
            // Because of the lines added with negative quantity when we remove product,
            // we have to check if the sum of the negative and positive lines are equals to the split.
            if(this.pos.is_french_country()) {
                var full = true;
                order.get_orderlines().forEach(function(orderLine) {
                    var split = splitlines[orderLine.id];
                    if(orderLine.get_quantity() > 0) {
                        if(!split) {
                            full = false
                        } else {
                            if(split.quantity >= 0) {
                                var qty = 0;
                                var total_quantity = 0;
                                var lines = order.get_orderlines();
                                for(var i = 0; i < lines.length; i++){
                                    if(lines[i].get_product().id === orderLine.get_product().id) {
                                        total_quantity += lines[i].get_quantity();
                                        qty += (splitlines[lines[i].id]? splitlines[lines[i].id].quantity : 0)
                                    }
                                }

                                if(qty !== total_quantity)
                                    full = false;
                            }
                        }
                    }
                });
                return full;
            } else {
                this._super(order, splitlines);
            }
        },

        lineselect: function($el,order,neworder,splitlines,line_id){
            var split = splitlines[line_id] || {'quantity': 0, line: null};
            var line  = order.get_orderline(line_id);

            if(this.pos.is_french_country())
                this.split_quantity(split, line, order, splitlines);
            else
                this.split_quantity(split, line);

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

        split_quantity: function(split, line, order, splitlines) {
            if(this.pos.is_french_country()) {
                var total_quantity = 0;
                var splitted = 0;

                order.get_orderlines().forEach(function(orderLine) {
                    if(orderLine.get_product().id === line.product.id){
                        total_quantity += orderLine.get_quantity();
                        splitted += splitlines[orderLine.id]? splitlines[orderLine.id].quantity: 0;
                    }
                });

                if(line.get_quantity() > 0) {
                    if( !line.get_unit().is_pos_groupable ){
                        if( split.quantity !== total_quantity){
                            split.quantity = total_quantity;
                        }else{
                            split.quantity = 0;
                        }
                    }else{
                        if( splitted < total_quantity && split.quantity < line.get_quantity()){
                            split.quantity += line.get_unit().is_pos_groupable ? 1 : line.get_unit().rounding;
                            if(splitted > total_quantity){
                                split.quantity = line.get_quantity();
                            }
                        }else{
                            split.quantity = 0;
                        }
                    }
                }
            } else {
                this._super(split, line);
            }
        },
    });
});
