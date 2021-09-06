odoo.define('flexipharmacy.db', function (require) {
    "use strict";

    var DB = require('point_of_sale.DB');
    var core = require('web.core');
    var rpc = require('web.rpc');

    var _t = core._t;
    
    DB.include({
        init: function(options){
            this._super.apply(this, arguments);
            this.card_by_id = {};
            this.card_sorted = [];
            this.picking_type_by_id = {};
            this.order_write_date = null;
            this.order_sorted = [];
            this.orders_list = [];
            this.draft_orders_list = [];
            this.orders_list_by_id = {};
            this.order_search_string = "";
        },
        add_orders : function(orders){
            var updated_count = 0;
            var new_write_date = '';
            this.orders_list = orders
            for(var i = 0, len = orders.length; i < len; i++){
                var order = orders[i];
                let localTime =  moment.utc(order['date_order']).toDate();
                order['date_order'] =   moment(localTime).format('YYYY-MM-DD hh:mm:ss')
                if (    this.order_write_date &&
                        this.orders_list_by_id[order.id] &&
                        new Date(this.order_write_date).getTime() + 1000 >=
                        new Date(order.write_date).getTime() ) {
                    continue;
                } else if ( new_write_date < order.write_date ) {
                    new_write_date  = order.write_date;
                }
                if (!this.orders_list_by_id[order.id]) {
                    this.order_sorted.push(order.id);
                }
                this.orders_list_by_id[order.id] = order;
                updated_count += 1;
            }
            this.order_write_date = new_write_date || this.order_write_date;
            if (updated_count){
                this.order_search_string = "";
                for (var id in this.orders_list_by_id) {
                    var order = this.orders_list_by_id[id];
                    this.order_search_string += this._order_search_string(order);
                }
            }
            return updated_count;
        },
        get_orders_list_by_id: function(id){
            return this.orders_list_by_id[id];
        },
        get_orders_list: function(){
            return this.orders_list;
        },
        add_draft_orders:function(draft_orders){
            this.draft_orders_list = draft_orders;
        },
        get_draft_orders_list: function(){
            return this.draft_orders_list;
        },
        _order_search_string: function(order){
            var str =  order.name;
            if(order.pos_reference){
                str += '|' + order.pos_reference;
            }
            if(order.partner_id.length > 0){
                str += '|' + order.partner_id[1];
            }
            if(order.salesman_id && order.salesman_id.length > 0){
                str += '|' + order.salesman_id[1];
            }
            str = '' + order.id + ':' + str.replace(':','') + '\n';
            return str;
        },

        search_orders: function(query){
            try {
                query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g,'.');
                query = query.replace(' ','.+');
                var re = RegExp("([0-9]+):.*?"+query,"gi");
            }catch(e){
                return [];
            }
            var results = [];
            var r;
            for(var i = 0; i < this.limit; i++){
                r = re.exec(this.order_search_string);
                if(r){
                    var id = Number(r[1]);
                    results.push(this.get_orders_list_by_id(id));
                }else{
                    break;
                }
            }
            return results;
        },
        add_picking_types: function(stock_pick_typ){
            var self = this;
            stock_pick_typ.map(function(type){
                self.picking_type_by_id[type.id] = type;
            });
        },
        get_picking_type_by_id: function(id){
            return this.picking_type_by_id[id]
        },
        notification: function(type, message){
            var types = ['success','warning','info', 'danger'];
            if($.inArray(type.toLowerCase(),types) != -1){
                $('div.span4').remove();
                var newMessage = '';
                message = _t(message);
                switch(type){
                case 'success' :
                    newMessage = '<i class="fa fa-check" aria-hidden="true"></i> '+message;
                    break;
                case 'warning' :
                    newMessage = '<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> '+message;
                    break;
                case 'info' :
                    newMessage = '<i class="fa fa-info" aria-hidden="true"></i> '+message;
                    break;
                case 'danger' :
                    newMessage = '<i class="fa fa-ban" aria-hidden="true"></i> '+message;
                    break;
                }
                $('body').append('<div class="span4 pull-right">' +
                        '<div class="alert alert-'+type+' fade">' +
                        newMessage+
                       '</div>'+
                     '</div>');
                $(".alert").removeClass("in").show();
                $(".alert").delay(200).addClass("in").fadeOut(5000);
            }
        },
        get_card_by_id: function(id){
            return this.card_by_id[id];
        },
        _card_search_string: function(gift_card){
            var str =  gift_card.card_no;
            if(gift_card.customer_id){
                str += '|' + gift_card.customer_id[1];
            }
            str = '' + gift_card.id + ':' + str.replace(':','') + '\n';
            return str;
        },
        search_gift_card: function(query){
            try {
                query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g,'.');
                query = query.replace(' ','.+');
                var re = RegExp("([0-9]+):.*?"+query,"gi");
            }catch(e){
                return [];
            }
            var results = [];
            var r;
            for(var i = 0; i < this.limit; i++){
                r = re.exec(this.card_search_string);
                if(r){
                    var id = Number(r[1]);
                    results.push(this.get_card_by_id(id));
                }else{
                    break;
                }
            }
            return results;
        },
        add_giftcard: function(gift_cards){
            var updated_count = 0;
            var new_write_date = '';
            for(var i = 0, len = gift_cards.length; i < len; i++){
                var gift_card = gift_cards[i];
                if (this.card_write_date && this.card_by_id[gift_card.id] && new Date(this.card_write_date).getTime() + 1000 >= new Date(gift_card.write_date).getTime() ) {
                    continue;
                } else if ( new_write_date < gift_card.write_date ) { 
                    new_write_date  = gift_card.write_date;
                }
                if (!this.card_by_id[gift_card.id]) {
                    this.card_sorted.push(gift_card.id);
                }
                this.card_by_id[gift_card.id] = gift_card;
                updated_count += 1;
            }
            this.card_write_date = new_write_date || this.card_write_date;
            if (updated_count) {
                // If there were updates, we need to completely 
                this.card_search_string = "";
                for (var id in this.card_by_id) {
                    var gift_card = this.card_by_id[id];
                    this.card_search_string += this._card_search_string(gift_card);
                }
            }
            return updated_count;
        },
    });
});