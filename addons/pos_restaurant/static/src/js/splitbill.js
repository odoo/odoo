function openerp_restaurant_splitbill(instance, module){
    var QWeb = instance.web.qweb;
	var _t = instance.web._t;

    module.SplitbillScreenWidget = module.ScreenWidget.extend({
        template: 'SplitbillScreenWidget',

        show_leftpane:   false,
        previous_screen: 'products',

        renderElement: function(){
            var self = this;
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
                self.pos_widget.screen_selector.set_current_screen(self.previous_screen);
            });
        },

        lineselect: function($el,order,neworder,splitlines,line_id){
            var split = splitlines[line_id] || {'quantity': 0, line: null};
            var line  = order.get_orderline(line_id);
            
            if( !line.get_unit().groupable ){
                if( split.quantity !== line.get_quantity()){
                    split.quantity = line.get_quantity();
                }else{
                    split.quantity = 0;
                }
            }else{
                if( split.quantity < line.get_quantity()){
                    split.quantity += line.get_unit().rounding;
                    if(split.quantity > line.get_quantity()){
                        split.quantity = line.get_quantity();
                    }
                }else{
                    split.quantity = 0;
                }
            }

            if( split.quantity ){
                if ( !split.line ){
                    split.line = line.clone();
                    neworder.add_orderline(split.line);
                }
                split.line.set_quantity(split.quantity);
            }else if( split.line ) {
                neworder.remove_orderline(split.line);
                split.line = null;
            }
     
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

        pay: function(order,neworder,splitlines){
            var orderlines = order.get_orderlines();
            var empty = true;
            var full  = true;

            for(var i = 0; i < orderlines.length; i++){
                var id = orderlines[i].id;
                var split = splitlines[id];
                if(!split){
                    full = false;
                }else{
                    if(split.quantity){
                        empty = false;
                        if(split.quantity !== orderlines[i].get_quantity()){
                            full = false;
                        }
                    }
                }
            }
            
            if(empty){
                return;
            }


            if(full){
                this.pos_widget.screen_selector.set_current_screen('payment');
            }else{
                for(var id in splitlines){
                    var split = splitlines[id];
                    var line  = order.get_orderline(parseInt(id));
                    line.set_quantity(line.get_quantity() - split.quantity);
                    if(Math.abs(line.get_quantity()) < 0.00001){
                        order.remove_orderline(line);
                    }
                    delete splitlines[id];
                }
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

                this.pos.get('orders').add(neworder);
                this.pos.set('selectedOrder',neworder);
            }
        },
        show: function(){
            var self = this;
            this._super();
            this.renderElement();

            var order = this.pos.get_order();
            var neworder = new module.Order({},{
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

    module.PosWidget.include({
        build_widgets: function(){
            var self = this;
            this._super();

            if(this.pos.config.iface_splitbill){
                this.splitbill_screen = new module.SplitbillScreenWidget(this,{});
                this.splitbill_screen.appendTo(this.$('.screens'));
                this.screen_selector.add_screen('splitbill',this.splitbill_screen);

                var splitbill = $(QWeb.render('SplitbillButton'));

                splitbill.click(function(){
                    if(self.pos.get_order().get_orderlines().length > 0){
                        self.pos_widget.screen_selector.set_current_screen('splitbill');
                    }
                });
                
                splitbill.appendTo(this.$('.control-buttons'));
                this.$('.control-buttons').removeClass('oe_hidden');
            }
        },
    });
}
