odoo.define('flexipharmacy.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var _t = core._t;
    var _ModelProto = models.Order.prototype;
    var utils = require('web.utils');
    var session = require('web.session');
    var exports = {};
    var round_pr = utils.round_precision;
    var round_di = utils.round_decimals;
    var field_utils = require('web.field_utils');
    var QWeb = core.qweb;

    models.load_fields("pos.payment.method", ['jr_use_for','allow_for_loyalty']);
    models.load_fields("res.partner", ['remaining_wallet_amount', 'remaining_points','is_doctor']);
    models.load_fields("res.users", ['image_1920', 'display_amount_during_close_session','pin', 'write_date',
                        'access_money_in_out', 'access_wallet', 'access_gift_card', 'access_default_customer',
                        'access_gift_voucher', 'access_warehouse_qty', 'access_int_trans_stock','access_multi_uom',
                        'access_select_sale_person', 'access_bag_charges', 'access_vertical_category',
                        'access_pos_lock', 'access_purchase_history', 'access_pos_return', 'access_close_session',
                        'access_signature', 'access_product_summary','access_order_summary', 'access_payment_summary',
                        'access_audit_report','access_delivery_charges','access_purchase_order','barcode',
                        'access_pos_order_note', 'is_pos_direct_login', 'access_cross_selling',
                        'access_alternative_product','access_material_monitor','access_pos_promotion']);
    models.load_fields("product.product", ['is_packaging', 'type', 'alternate_product_ids', 'suggestive_product_ids',
                    'active_ingredient_ids', 'qty_available', 'is_material_monitor', 'material_monitor_qty']);
    models.load_fields('pos.session',['is_lock_screen']);
    models.load_fields('hr.employee',['rfid_pin']);
    models.load_fields('pos.order',['note']);
    models.load_fields('pos.order.line',['line_note']);

    var _super_paymentline = models.Paymentline.prototype;
    var _super_Order = models.Order.prototype;  
    var _super_posmodel = models.PosModel;
    
    models.PosModel = models.PosModel.extend({
        load_server_data: function(){
            var self = this;
            var loaded = _super_posmodel.prototype.load_server_data.call(this);
            loaded.then(function(){
                var session_params = {
                    model: 'pos.session',
                    method: 'search_read',
                    domain: [['state','=','opened']],
                    fields: ['id','name','config_id'],
                    orderBy: [{ name: 'id', asc: true}],
                }
                rpc.query(session_params, {async: false})
                .then(function(sessions){
                    if(sessions && sessions[0]){
                        self.all_pos_session = sessions;
                    }
                });
                var stock_location_params = {
                    model: 'stock.location',
                    method: 'search_read',
                    domain: [['usage','=','internal'],['company_id','=',self.company.id]],
                    fields: ['id','name','company_id','complete_name'],
                }
                rpc.query(stock_location_params, {async: false})
                .then(function(locations){
                    if(locations && locations[0]){
                        self.all_locations = locations;
                    }
                });
                var params = {
                    model: 'res.config.settings',
                    method: 'load_loyalty_config_settings',
                }
                rpc.query(params)
                .then(function(loyalty_config){
                    if(loyalty_config && loyalty_config[0]){
                        self.loyalty_config = loyalty_config[0];
                    }
                }).catch(function(){
                    console.log("Connection lost");
                });
                var params = {
                    model: 'pos.recurrent.order',
                    method: 'search_read',
                    domain: [],
                }
                rpc.query(params)
                .then(function(result){
                       console.log('result 123',result)
                       self.recurrent_order_list = result;
                }).catch(function(){
                    console.log("Connection lost");
                });
            })
            return loaded
        },
     });
    models.PosModel.prototype.models.push({
        model:  'aspl.gift.card.type',
        fields: ['name'],
        loaded: function(self,card_type){
            self.card_type = card_type;
        },
    },{
        model: 'aspl.gift.card',
        domain: [['is_active', '=', true]],
        loaded: function(self,gift_cards){
            self.db.add_giftcard(gift_cards);
            self.set({'gift_card_order_list' : gift_cards});
        },
    },{
        model: 'aspl.gift.voucher',
        domain: [['is_active', '=', true]],
        fields: ['id', 'voucher_name', 'voucher_amount', 'minimum_purchase', 'expiry_date','redemption_order', 'redemption_customer', 'voucher_code'],
        loaded: function(self,gift_voucher){
            self.gift_vouchers = gift_voucher;
        },
    },{
        model:  'stock.picking.type',
        fields: ['default_location_src_id', 'default_location_dest_id'],
        domain: function(self){ return [['id', '=', self.config.picking_type_id[0]]]; },
        loaded: function(self,default_stock_pick_type){
            self.default_stock_pick_type = default_stock_pick_type;
        },
    },{
        model:  'stock.picking.type',
        fields: [],
        domain: [['code','=','internal']],
        loaded: function(self,stock_pick_typ){
            self.stock_pick_typ = stock_pick_typ;
        },
    },{
        model:  'stock.location',
        fields: ['complete_name', 'name'],
        domain: [['usage','=','internal']],
        loaded: function(self,stock_location){
            self.stock_location = stock_location;
        },
    },{
        model: 'active.ingredient',
        loaded: function(self,active_ingredients){
            self.active_ingredients = active_ingredients;
        },
    },{
        model:  'pos.promotion',
        fields: [],
        domain: function(self){
            var current_date = moment(new Date()).locale('en').format("YYYY-MM-DD");
            var weekday = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
            var d = new Date();
            var current_day = weekday[d.getDay()]
            return [['from_date','<=',current_date],['to_date','>=',current_date],['active','=',true],
                    ['day_of_week_ids.name','in',[current_day]]];
        },
        loaded: function(self, promotions){
            self.pos_promotions = promotions;
            self.promotions_by_id = {};
            _.each(promotions, function(promo){
                self.promotions_by_id[promo.id] = promo;
            })
        },
    },{
        model:  'pos.conditions',
        fields: [],
        loaded: function(self,pos_conditions){
            self.pos_conditions_by_id = {};
            self.pos_conditions = pos_conditions;
            _.each(pos_conditions, function(promo){
                self.pos_conditions_by_id[promo.id] = promo;
            })
        },
    },{
        model:  'get.discount',
        fields: [],
        loaded: function(self, pos_get_discount){
            self.get_discount_by_id = {};
            self.get_discount = pos_get_discount;
            _.each(pos_get_discount, function(promo){
                self.get_discount_by_id[promo.id] = promo;
            })
        },
    },{
        model:  'quantity.discount',
        fields: [],
        loaded: function(self, pos_get_qty_discount){
            self.pos_get_qty_discount = pos_get_qty_discount;
            self.get_qty_discount_by_id = {};
            for(let value of pos_get_qty_discount){
                self.get_qty_discount_by_id[value.id] = value;
            }
        },
    },{
        model:  'quantity.discount.amt',
        fields: [],
        loaded: function(self,pos_qty_discount_amt){
            self.pos_qty_discount_amt_by_id = {};
            self.pos_qty_discount_amt = pos_qty_discount_amt;
            _.each(pos_qty_discount_amt, function(promo){
                self.pos_qty_discount_amt_by_id[promo.id] = promo;
            })
        },
    },{
        model:  'discount.multi.products',
        fields: [],
        loaded: function(self,pos_discount_multi_prods){
            self.pos_discount_multi_prods = pos_discount_multi_prods;
            self.pos_discount_multi_prods_by_id = {}
            for(const disc of pos_discount_multi_prods){
                self.pos_discount_multi_prods_by_id[disc.id] = disc;
            }
        },
    },{
        model:  'discount.multi.categories',
        fields: [],
        loaded: function(self, pos_discount_multi_category){
            self.pos_discount_multi_category = pos_discount_multi_category;
            self.pos_discount_multi_category_by_id = {}
            for(const disc of pos_discount_multi_category){
                self.pos_discount_multi_category_by_id[disc.id] = disc;
            }
        },
    },{
        model:  'discount.above.price',
        fields: [],
        loaded: function(self,pos_discount_above_price){
            self.pos_discount_above_price = pos_discount_above_price;
        },
    });

    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr,options){
            _super_orderline.initialize.call(this, attr, options);
            this.uom_id = this.product.uom_id;
            this.serials = this.serials || null;
            this.ingredients = this.ingredients || null;
            this.selected_ingredients = this.selected_ingredients || null;
            this.line_note = this.line_note || "";
            this.refund_order = this.refund_order || false;
            this.refund_order_line = this.refund_order_line || false;
            /* POS Promotion Code Start */
            this.uniqueChildId = this.uniqueChildId || false;
            this.uniqueParentId = this.uniqueParentId || false;
            this.isRuleApplied = this.isRuleApplied || false;
            this.promotionRule = this.promotionRule || false;
            this.promotion = this.promotion || false;
            this.combination_id = this.combination_id || false;
            this.promotion_flag = this.promotion_flag || false;
            this.promotion_disc_parentId = this.promotion_disc_parentId || false;
            this.promotion_disc_childId = this.promotion_disc_childId || false;
            /* POS Promotion Code End */
        },
        set_product_note: function(line_note){
            this.line_note = line_note;
            this.trigger('change',this);
        },
        get_product_note: function(){
            return this.line_note;
        },
        set_refund_order_line: function(refund_order_line){
            this.refund_order_line = refund_order_line;
            this.trigger('change',this);
        },
        get_refund_order_line: function(){
            return this.refund_order_line;
        },
        can_be_merged_with: function(orderline) {
            if (orderline.get_product_note() !== this.get_product_note()) {
                return false;
            } else {
                return _super_orderline.can_be_merged_with.apply(this,arguments);
            }
        },
        clone: function(){
            var orderLine = _super_orderline.clone.call(this);
            orderLine.line_note = this.line_note;
            /* POS Promotion Code Start */
            orderLine.uniqueParentId = this.uniqueParentId;
            orderLine.uniqueChildId = this.uniqueChildId;
            orderLine.isRuleApplied = this.isRuleApplied;
            orderLine.promotion = this.promotion;
            orderLine.combination_id = this.combination_id;
            orderLine.promotion_flag = this.promotion_flag;
            orderLine.promotion_disc_parentId = this.promotion_disc_parentId;
            orderLine.promotion_disc_childId = this.promotion_disc_childId;
            /* POS Promotion Code End */
            return orderLine;
        },
        init_from_JSON: function(json){
            _super_orderline.init_from_JSON.apply(this,arguments);
            this.uom_id = json.uom_id;
            this.serials = json.serials;
            this.ingredients = json.ingredients;
            this.selected_ingredients = json.selected_ingredients;
            this.line_note = json.line_note;
            this.refund_order_line = json.refund_order_line;
            /* POS Promotion Code Start */
            this.uniqueParentId = json.uniqueParentId;
            this.uniqueChildId = json.uniqueChildId;
            this.isRuleApplied = json.isRuleApplied;
            this.promotion = json.promotion;
            this.promotion_flag = json.promotion_flag;
            this.promotion_disc_parentId = json.promotion_disc_parentId;
            this.promotion_disc_childId = json.promotion_disc_childId;
            /* POS Promotion Code End */
        },
        set_orderline_ingredients: function(ingredients){
            this.ingredients = ingredients;
            this.trigger('change',this);
        },
        get_orderline_ingredients: function(ingredients){
            return this.ingredients;
        },
        set_selected_orderline_ingredients: function(selected_ingredients){
            this.selected_ingredients = selected_ingredients;
            this.trigger('change',this);
        },
        get_selected_orderline_ingredients: function(selected_ingredients){
            return this.selected_ingredients;
        },
        set_serials: function(serials){
            this.serials = serials;
            this.trigger('change',this);
        },
        get_serials: function(){
            return this.serials;
        },
        set_custom_uom_id: function(uom_id){
            this.uom_id = uom_id;
            this.trigger('change',this);
        },
        get_custom_uom_id: function(){
            return this.uom_id;
        },
        export_as_JSON: function(){
            var json = _super_orderline.export_as_JSON.call(this);
            var active_ingredients = [];
            if(this.get_selected_orderline_ingredients()){
                _.each(this.get_selected_orderline_ingredients(),function(ingredient) {
                    active_ingredients += ingredient.name +", ";
                });
            }
            json.active_ingredients = active_ingredients.length > 0 ? active_ingredients : false;
            json.uom_id = this.uom_id;
            json.unit_id = this.uom_id;
            json.serials = this.serials;
            json.ingredients = this.ingredients;
            json.selected_ingredients = this.selected_ingredients;
            json.line_note = this.line_note;
            json.refund_order_line = this.refund_order_line;
            json.order_return_qty = this.get_quantity();
            json.return_pack_lot_ids = json.pack_lot_ids;
            /* POS Promotion Code Start */
            json.uniqueParentId = this.uniqueParentId;
            json.uniqueChildId = this.uniqueChildId;
            json.isRuleApplied = this.isRuleApplied;
            json.promotion = this.promotion;
            json.combination_id = this.combination_id;
            json.promotion_flag = this.promotion_flag;
            json.promotion_disc_parentId = this.promotion_disc_parentId;
            json.promotion_disc_childId = this.promotion_disc_childId;
            /* POS Promotion Code End */
            return json;
        },
        export_for_printing: function(){
            var orderline = _super_orderline.export_for_printing.call(this);
            var serials = "";
            if(this.pack_lot_lines && this.pack_lot_lines.models){
                _.each(this.pack_lot_lines.models,function(lot) {
                    if(lot && lot.get('lot_name')){
                        serials += lot.get('lot_name')+", ";
                    }
                });
            }
            orderline.serial_names = serials ? 'Serial No(s) :' + serials : false;
            orderline.selected_ingredients = this.get_selected_orderline_ingredients();
            orderline.line_note = this.get_product_note();
            /* POS Promotion Code Start */
            orderline.promotion_code = this.promotion ? this.promotion.promotion_code : false;
            /* POS Promotion Code End */
            return orderline;
        },
        get_unit: function(){
            var res = _super_orderline.get_unit.call(this);
            var unit_id = this.uom_id;
            if(!unit_id){
                return res;
            }
            unit_id = unit_id[0] || unit_id;
            if(!this.pos){
                return undefined;
            }
            return this.pos.units_by_id[unit_id];
        },
        apply_uom: function(){
            var self = this;
            var orderline = self.pos.get_order().get_selected_orderline();
            var uom_id = orderline.get_custom_uom_id();
            if(uom_id){
                var selected_uom = this.pos.units_by_id[uom_id];
                orderline.uom_id = [uom_id, selected_uom.name];
                var latest_price = orderline.get_latest_price(selected_uom, orderline.product);
                orderline.set_unit_price(latest_price);
                return true
            } else{
                return false
            }
        },
        get_units_by_category: function(uom_list, categ_id){
            var uom_by_categ = []
            for (var uom in uom_list){
                if(uom_list[uom].category_id[0] == categ_id[0]){
                    uom_by_categ.push(uom_list[uom]);
                }
            }
            return uom_by_categ;
        },
        find_reference_unit_price: function(product, product_uom){
            return product.lst_price;
        },
        get_latest_price: function(uom, product){
            var uom_by_category = this.get_units_by_category(this.pos.units_by_id, uom.category_id);
            var product_uom = this.pos.units_by_id[product.uom_id[0]];
            var ref_price = this.find_reference_unit_price(product, product_uom);
            var ref_unit = null;
            for (var i in uom_by_category){
                if(uom_by_category[i].uom_type == 'reference'){
                    ref_unit = uom_by_category[i];
                    break;
                }
            }
            if(ref_unit){

                if(uom.uom_type == 'bigger'){
                    return (ref_price * uom.factor_inv);

                }
                else if(uom.uom_type == 'smaller'){
                    return (ref_price / uom.factor);
                }
                else if(uom.uom_type == 'reference'){
                    return ref_price;
                }
            }
            return product.price;
        },
        set_product_lot: function(product){
            this.has_product_lot = product.tracking !== 'none';
            this.pack_lot_lines  = this.has_product_lot && new PacklotlineCollection(null, {'order_line': this});
        },
        /* POS Promotion Code Start */
        set_promotion_flag : function(flag){
            this.promotion_flag = flag;
        },
        get_promotion_flag : function(flag){
            return this.promotion_flag;
        },
        set_promotion_disc_parent_id : function(parentId){
            this.promotion_disc_parentId = parentId;
        },
        get_promotion_disc_parent_id : function(){
            return this.promotion_disc_parentId;
        },
        set_promotion_disc_child_id : function(childId){
            this.promotion_disc_childId = childId;
        },
        get_promotion_disc_child_id : function(){
            return this.promotion_disc_childId;
        },
        set_combination_id : function(combinationId){
            this.combination_id = combinationId;
        },
        get_combination_id : function(){
            return this.combination_id;
        },
        // FOR BUY X GET Y FREE PRODUCT START
        set_unique_parent_id : function(uniqueParentId){
            this.uniqueParentId = uniqueParentId;
        },
        get_unique_parent_id(){
            return this.uniqueParentId;
        },
        set_unique_child_id : function(uniqueChildId){
            this.uniqueChildId = uniqueChildId;
        },
        get_unique_child_id(){
            return this.uniqueChildId;
        },
        // FOR BUY X GET Y FREE PRODUCT END
        set_promotion : function(promotion){
            this.promotion = promotion;
        },
        get_promotion : function(promotion){
            return this.promotion;
        },
        set_is_rule_applied : function(rule){
            this.applied_rule = rule;
        },
        get_is_rule_applied : function(){
            return this.applied_rule;
        },
        set_is_promotion_applied :function(rule){
            this.is_promotion_applied = rule;
        },
        get_is_promotion_applied :function(){
            return this.is_promotion_applied;
        },
        set_buy_x_get_dis_y: function(product_ids){
            this.product_ids = product_ids;
        },
        get_buy_x_get_dis_y: function(){
            return this.product_ids;
        },
        /* POS Promotion Code End */
    });
    var PacklotlineCollection = Backbone.Collection.extend({
        model: exports.Packlotline,
        initialize: function(models, options) {
            this.order_line = options.order_line;
        },

        get_valid_lots: function(){
            return this.filter(function(model){
                return model.get('lot_name');
            });
        },

        set_quantity_by_lot: function() {
            var valid_lots_quantity = this.get_valid_lots().length;
            // if (this.order_line.quantity < 0){
            //     valid_lots_quantity = -valid_lots_quantity;
            // }
            this.order_line.set_quantity(valid_lots_quantity);
        }
    });
    models.Order = models.Order.extend({
        initialize: function(attributes,options){
            var res = _super_Order.initialize.apply(this, arguments);
            this.selected_doctor = false;
            this.set({
                change_amount_for_wallet: 0.00,
                use_wallet: false,
                used_amount_from_wallet: 0.00,
                type_for_wallet: false,
                rounding: true,
                recharge: false,
                order_user_id:false,
//                selected_doctor : false,
                refund_ref_order:false,
            });
            if (this.pos.config.enable_loyalty){
                this.set({
                    earned_points: this.earned_points || 0.0,
                    redeem_points: this.redeem_points || 0.0,
                    points_amount: this.points_amount || 0.0,
                    ref_reward: this.ref_reward || 0.0,
                    ref_customer: this.ref_customer || false,
                });
            }
            if(this.pos.config.enable_default_customer && this.pos.config.default_customer_id && !this.get_client()) {
                var default_customer = this.pos.config.default_customer_id[0];
                var set_partner = this.pos.db.get_partner_by_id(default_customer);
                if(set_partner){
                    this.set_client(set_partner);
                }
            }
            this.giftcard = [];
            this.if_gift_card = false;
            this.voucher_redeem = this.voucher_redeem || false;
            this.redeem = this.redeem || false;
            this.sign = this.sign || null;
            this.raw_sign = this.raw_sign || null;
            this.print_serial = false;
            this.order_note = this.order_note || '';
            this.delivery_charge_data = this.delivery_charge_data || {};
            this.connected = this.connected || true;
            var default_src_location = this.pos.stock_location.filter((location) => location.id === this.pos.default_stock_pick_type[0].default_location_src_id[0])
            this.product_location = default_src_location[0] || false;
            this.material_monitor_data();
            /* POS Promotion Code Start */
            this.orderPromotion = this.orderPromotion || false;
            this.orderDiscountLine = this.orderDiscountLine || false;
            /* POS Promotion Code End */
            return this;
        },
        mirror_image_data:function(neworder){
            var self = this;
            var client_name = false;
            var order_total = self.get_total_with_tax();
            var change_amount = self.get_change();
            var payment_info = [];
            var paymentlines = self.paymentlines.models;
            if(paymentlines && paymentlines[0]){
                paymentlines.map(function(paymentline){
                    payment_info.push({
                        'name':paymentline.name,
                        'amount':paymentline.amount,
                    });
                });
            }
            var orderLines = [];
            this.orderlines.each(_.bind( function(item) {
                return orderLines.push(item.export_as_JSON());
            }, this));
            if(self.get_client()){
                client_name = self.get_client().name;
            }
            const total = this.get_total_with_tax() || 0;
            const tax = total - this.get_total_without_tax() || 0;
            var vals = {
                'orderLines': orderLines,
                'total': total,
                'tax': tax,
                'client_name':client_name,
                'order_total':order_total,
                'change_amount':change_amount,
                'payment_info':payment_info,
                'enable_customer_rating':self.pos.config.enable_customer_rating,
                'set_customer':self.pos.config.set_customer,
                'order_note': self.order_note,
            }
            if(neworder){
                vals['new_order'] = true;
            }
            rpc.query({
                model: 'customer.display',
                method: 'broadcast_data',
                args: [vals],
            })
            .then(function(result) {});
        },
        init_from_JSON: function(json){
            _super_Order.init_from_JSON.apply(this,arguments);
            this.refund_order = json.refund_order;
            this.voucher_redeem = json.voucher_redeem;
            this.redeem = json.redeem;
            this.sign = json.sign;
            this.raw_sign = json.raw_sign;
            this.order_note = json.order_note;
            this.delivery_charge_data = json.delivery_charge_data;
            this.connected = json.connected;
            this.product_location = json.product_location;
            /* POS Promotion Code Start */
            this.orderPromotion = json.orderPromotion;
            this.orderDiscountLine = json.orderDiscountLine;
            /* POS Promotion Code End */
        },
        set_product_location: function(product_location) {
            this.product_location = product_location
            // this.mirror_image_data();
        },
        get_product_location: function() {
            return this.product_location;
        },
        material_monitor_data:function(neworder){
            var self = this;
            var vals = this.pos.db.product_by_id;
            rpc.query({
                model: 'product.product',
                method: 'broadcast_product_qty_data',
                args: [vals, this.pos.db.product_by_id, this.get_product_location().id],
            })
            .then(function(result) {});
        },
        set_client: function(client){
            _ModelProto.set_client.apply(this, arguments);
            if(this.pos.config.customer_display){
                this.mirror_image_data();
            }
        },
        set_delivery_charge: function(charge) {
            var dilevery_product = this.pos.db.get_product_by_id(this.pos.config.delivery_product_id[0]);
            var lines = this.get_orderlines();
            if (dilevery_product) {
                for (var i = 0; i < lines.length; i++) {
                    if (lines[i].get_product() === dilevery_product) {
                        lines[i].set_unit_price(charge);
                        lines[i].set_lst_price(charge);
                        lines[i].price_manually_set = true;
                        lines[i].order.tip_amount = charge;
                        return;
                    }
                }
                return this.add_product(dilevery_product, {
                  is_tip: true,
                  quantity: 1,
                  price: charge,
                  lst_price: charge,
                  extras: {price_manually_set: true},
                });
            }
        },
        get_delivery_charge: function() {
            var dilevery_product = this.pos.db.get_product_by_id(this.pos.config.delivery_product_id[0]);
            var lines = this.get_orderlines();
            if (!dilevery_product) {
                return 0;
            } else {
                for (var i = 0; i < lines.length; i++) {
                    if (lines[i].get_product() === dilevery_product) {
                        return {product_id: this.pos.config.delivery_product_id[0], amount: lines[i].get_unit_price()}
                    }
                }
                return 0;
            }
        },
        set_doctor: function(selected_doctor){
            this.selected_doctor = selected_doctor;
        },
        get_doctor: function(){
            return this.selected_doctor;
        },
        set_print_serial: function(val) {
            this.print_serial = val
        },
        get_print_serial: function() {
            return this.print_serial;
        },
        get_number_of_print : function(){
            return this.number_of_print;
        },
        set_number_of_print : function(number){
            this.number_of_print = number;
        },
        set_connected: function(connected) {
            this.connected = connected
        },
        get_connected: function() {
            return this.connected;
        },
        set_rating: function(rating){
            this.rating = rating;
        },
        get_rating: function(){
            return this.rating;
        },
        set_order_summary_report_mode: function(order_summary_report_mode) {
            this.order_summary_report_mode = order_summary_report_mode;
        },
        get_order_summary_report_mode: function() {
            return this.order_summary_report_mode;
        },
        set_product_summary_report :function(product_summary_report) {
            this.product_summary_report = product_summary_report;
        },
        get_product_summary_report: function() {
            return this.product_summary_report;
        },
        set_sales_summary_mode: function(sales_summary_mode) {
            this.sales_summary_mode = sales_summary_mode;
        },
        get_sales_summary_mode: function() {
            return this.sales_summary_mode;
        },
        set_sales_summary_val :function(sales_summary_val) {
            this.sales_summary_val = sales_summary_val;
        },
        get_sales_summary_val: function() {
            return this.sales_summary_val;
        },
        set_receipt: function(custom_receipt) {
            this.custom_receipt = custom_receipt;
        },
        get_receipt: function() {
            return this.custom_receipt;
        },
        set_order_list: function(order_list) {
            this.order_list = order_list;
        },
        get_order_list: function() {
            return this.order_list;
        },

        set_sign: function(sign) {
            this.sign = sign;
            this.trigger('change',this);
        },
        get_sign: function(){
            return this.sign;
        },
        set_raw_sign : function(sign){
            this.raw_sign = sign;
            this.trigger('change',this);
        },
        get_raw_sign : function(){
            return this.raw_sign;
        },
        set_refund_ref_order: function(refund_ref_order) {
            this.set('refund_ref_order', refund_ref_order);
        },
        get_refund_ref_order: function() {
            return this.get('refund_ref_order');
        },
        set_refund_order: function(refund_order){
            this.refund_order = refund_order;
            this.trigger('change',this);
        },
        get_refund_order: function(){
            return this.refund_order;
        },
        set_type_for_wallet: function(type_for_wallet) {
            this.set('type_for_wallet', type_for_wallet);
        },
        get_type_for_wallet: function() {
            return this.get('type_for_wallet');
        },
        set_is_rounding: function(rounding) {
            this.set('rounding', rounding);
        },
        get_is_rounding: function() {
            return this.get('rounding');
        },
        set_change_amount_for_wallet: function(change_amount_for_wallet) {
            this.set('change_amount_for_wallet', change_amount_for_wallet);
        },
        get_change_amount_for_wallet: function() {
            return this.get('change_amount_for_wallet');
        },

        set_used_amount_from_wallet: function(used_amount_from_wallet) {
            this.set('used_amount_from_wallet', used_amount_from_wallet);
        },
        getNetTotalTaxIncluded: function() {
            var total = this.get_total_with_tax();
            return total;
        },
        get_used_amount_from_wallet: function() {
            return this.get('used_amount_from_wallet');
        },

        // gift_card
        set_giftcard: function(giftcard) {
            this.giftcard.push(giftcard);
        },
        get_giftcard: function() {
            return this.giftcard;
        },
        set_recharge_giftcard: function(recharge) {
            this.set('recharge', recharge);
        },
        get_recharge_giftcard: function(){
            return this.get('recharge');
        },
        set_redeem_giftcard: function(redeem){
            this.redeem = redeem;
            this.trigger('change',this);
        },
        get_redeem_giftcard: function(){
            return this.redeem;
        },
        set_redeem_giftvoucher: function(voucher_redeem){
            this.voucher_redeem = voucher_redeem;
            this.trigger('change',this);
        },
        get_redeem_giftvoucher: function(){
            return this.voucher_redeem;
        },
        set_earned_reward : function(earned_points){
            this.set('earned_points', earned_points);
        },

        get_earned_reward : function(earned_points){
            return this.get('earned_points');
        },

        set_used_points_from_loyalty: function(redeem_points) {
            this.set('redeem_points', redeem_points);
        },

        get_used_points_from_loyalty: function(redeem_points) {
            return this.get('redeem_points');
        },

        set_used_points_amount: function(points_amount) {
            this.set('points_amount', points_amount);
        },
        get_used_points_amount: function(points_amount) {
            return this.get('points_amount');
        },

        set_reference_reward:function(ref_reward){
            this.set('ref_reward', ref_reward);
        },
        get_reference_reward:function(ref_reward){
            return this.get('ref_reward');
        },
        set_reference_customer:function(ref_customer){
            this.set('ref_customer', ref_customer);
        },
        get_reference_customer:function(ref_customer){
            return this.get('ref_customer');
        },
        set_ref_client: function(ref){
            this.assert_editable();
            this.set('ref',ref);
        },
        get_ref_client: function(){
            return this.get('ref');
        },

        set_referral_event_type : function(referral_event){
            this.set('referral_event', referral_event);
        },

        get_referral_event_type : function(referral_event){
            return this.get('referral_event');
            return this.referral_event;
        },
        // order_sync
        set_salesman_id: function(salesman_id){
            this.set('salesman_id',salesman_id);
        },
        get_salesman_id: function(){
            return this.get('salesman_id');
        },
        set_is_modified_order:function(flag){
            this.set('flag', flag);
        },
        get_is_modified_order:function(){
            return this.get('flag');
        },
        set_pos_reference: function(pos_reference) {
            this.set('pos_reference', pos_reference)
        },
        get_pos_reference: function() {
            return this.get('pos_reference')
        },
        set_order_id: function(order_id){
            this.set('order_id', order_id);
        },
        get_order_id: function(){
            return this.get('order_id');
        },
        set_sequence:function(sequence){
            this.set('sequence',sequence);
        },
        get_sequence:function(){
            return this.get('sequence');
        },
        set_journal: function(statement_ids) {
            this.set('paymentlines', statement_ids)
        },
        get_journal: function() {
            return this.get('paymentlines');
        },
        set_amount_return: function(amount_return) {
            this.set('amount_return', amount_return);
        },
        get_amount_return: function() {
            return this.get('amount_return');
        },
        set_date_order: function(date_order) {
            this.set('date_order', date_order);
        },
        get_date_order: function() {
            return this.get('date_order');
        },
        get_change: function(paymentLine) {
            if(this.get_order_id()){
                let change = 0.0;
                if (!paymentLine) {
                    if(this.get_total_paid() > 0){
                        change = this.get_total_paid() - this.get_total_with_tax();
                    }else{
                        change = this.get_amount_return();
                    }
                }else {
                    change = -this.get_total_with_tax();
                    var orderPaymentLines  = this.pos.get_order().get_paymentlines();
                    for (let i = 0; i < orderPaymentLines.length; i++) {
                        change += orderPaymentLines[i].get_amount();
                        if (orderPaymentLines[i] === paymentLine) {
                            break;
                        }
                    }
                }
                return round_pr(Math.max(0,change), this.pos.currency.rounding);
            } else {
                return _super_Order.get_change.call(this, orderPaymentLines);
            }
        },


        // rounding off for unuse product
        get_rounding_applied: function() {
            var rounding_applied = _super_Order.get_rounding_applied.call(this);
            var rounding = this.get_is_rounding();
            if(this.pos.config.cash_rounding && !rounding && rounding_applied != 0) {
                rounding_applied = 0
                return rounding_applied;
            }
            return rounding_applied;
        },
        has_not_valid_rounding: function() {
            var rounding_applied = _super_Order.has_not_valid_rounding.call(this);
            var rounding = this.get_is_rounding();
            var line_rounding = true;
            if(!this.pos.config.cash_rounding)
                return false;
            if (this.pos.config.cash_rounding && !rounding)
                return false;
            var lines = this.paymentlines.models;

            for(var i = 0; i < lines.length; i++) {
                var line = lines[i];
                if (line.payment_method.jr_use_for === 'gift_card' || line.payment_method.jr_use_for === 'wallet'){
                    line_rounding = false;
                    break
                }else{
                    line_rounding = true;
                }
            }
            if (!line_rounding){
                return false;
            }else{
                if(!utils.float_is_zero(line.amount - round_pr(line.amount, this.pos.cash_rounding[0].rounding), 6))
                return line;
            }
            return false;
        },
        set_sales_person_id: function(user_id){
            this.set('order_user_id',user_id);
        },
        get_sales_person_id: function(){
            return this.get('order_user_id');
        },
        set_order_note: function(order_note) {
            this.order_note = order_note;
            this.trigger('change',this);
        },
        set_delivery_charge_data: function(delivery_charge_data){
            this.delivery_charge_data = delivery_charge_data;
        },
        get_delivery_charge_data: function(){
            return this.delivery_charge_data;
        },
        get_order_note: function() {
            return this.order_note;
        },
        // send detail in backend order
        export_as_JSON: function() {
            var orders = _super_Order.export_as_JSON.call(this);
            orders.wallet_type = this.get_type_for_wallet() || false;
            orders.change_amount_for_wallet = this.get_change_amount_for_wallet() || 0.00;
            orders.used_amount_from_wallet = this.get_used_amount_from_wallet() || 0.00;
            orders.amount_paid = this.get_total_paid() - (this.get_change() - Number(this.get_change_amount_for_wallet()));
            orders.amount_return = this.get_change() - Number(this.get_change_amount_for_wallet());
            orders.amount_due = this.get_due() ? (this.get_due() + Number(this.get_change_amount_for_wallet())): 0.00;
            orders.sales_person_id = this.get_sales_person_id() || false;
            // gift card
            orders.giftcard = this.get_giftcard() || false;
            orders.recharge = this.get_recharge_giftcard() || false;
            orders.redeem = this.get_redeem_giftcard() || false;
            // gift card
            orders.voucher_redeem = this.get_redeem_giftvoucher() || false;

            orders.uom_id = this.uom_id;

            orders.order_note = this.get_order_note()

            orders.earned_points = this.get_earned_reward() || false;
            orders.redeem_points = this.get_used_points_from_loyalty() || false;
            orders.points_amount = this.get_used_points_amount() || false;
            orders.ref_reward = this.get_reference_reward() || false;
            orders.ref_customer = this.get_reference_customer() || false;
            orders.referral_event = this.get_referral_event_type() || false;
            orders.refund_order = this.refund_order || false;
            orders.refund_ref_order = this.get_refund_ref_order() || false;
            // Signature
            orders.sign = this.sign || false;
            orders.raw_sign = this.raw_sign || false;
            orders.raw_sign = this.raw_sign || false;
            // $.extend(orders, new_val);
            orders.rating = this.get_rating() || 0
            // order sync
            orders.salesman_id = this.get_salesman_id() || this.pos.user.id;
            orders.old_order_id = this.get_order_id();
            orders.sequence = this.get_sequence();
            orders.pos_reference = this.get_pos_reference();
            orders.cashier_id = this.pos.user.id;
            orders.selected_doctor = this.get_doctor() || false;
            orders.get_delivery_charge_data = this.get_delivery_charge_data() || false;
            orders.get_delivery_charge = this.get_delivery_charge() || false;
            orders.product_location = this.get_product_location() || 0;
            /* POS Promotion Code Start */
            orders.orderPromotion = this.orderPromotion || false;
            orders.orderDiscountLine = this.orderDiscountLine || false;
            /* POS Promotion Code End */
            return orders;
        },

        // send detail in report
        export_for_printing: function(){
            var orders = _super_Order.export_for_printing.call(this);
            orders.change_amount_for_wallet= this.get_change_amount_for_wallet() || false;
            orders.used_amount_from_wallet= this.get_used_amount_from_wallet() || false;
            orders.amount_paid= this.get_total_paid() - (this.get_change() - Number(this.get_change_amount_for_wallet()));
            orders.amount_return= this.get_change() - Number(this.get_change_amount_for_wallet());
            //Reservation
            orders.amount_due= this.get_due() ? (this.get_due() + Number(this.get_change_amount_for_wallet())): 0.00;
            orders.change = this.locked ? this.amount_return- Number(this.get_change_amount_for_wallet()) : this.get_change() - Number(this.get_change_amount_for_wallet());
            // gift card
            orders.giftcard = this.get_giftcard() || false;
            orders.recharge = this.get_recharge_giftcard() || false;
            orders.redeem = this.get_redeem_giftcard() || false;
            // gift card
            orders.earned_points= this.get_earned_reward() || false;
            orders.redeem_points= this.get_used_points_from_loyalty() || false;
            // $.extend(orders, new_val);
            orders.order_note = this.get_order_note();
            return orders;
        },
        /* Pos Promotion Code Start */
        set_order_total_discount_line : function(line){
            this.orderDiscountLine = line;
        },
        get_order_total_discount_line : function(){
            return this.orderDiscountLine;
        },
        get_orderline_by_unique_id: function(uniqueId){
            var orderlines = this.orderlines.models;
            for(var i = 0; i < orderlines.length; i++){
                if(orderlines[i].uniqueChildId === uniqueId){
                    return orderlines[i];
                }
            }
            return null;
        },
        set_order_total_discount : function(promotion){
            this.orderPromotion = promotion;
        },
        get_order_total_discount : function(){
            return this.orderPromotion;
        },
        apply_pos_order_discount_total : async function(){
            var filteredPromotion = _.filter(this.pos.pos_promotions, function(promotion){
                                                        return promotion.promotion_type == 'discount_total'
                                                })
            var total = this.get_total_with_tax();
            for(const promotion of filteredPromotion){
                if(!this.check_for_valid_promotion(promotion))
                    return;
                var discountProduct = this.pos.db.get_product_by_id(promotion.discount_product[0]);
                if(total >= promotion.total_amount){
                    var isDiscount = await this.remove_discount_product(promotion)
                    var createNewDiscountLine = new models.Orderline({}, {pos: this.pos,
                                                        order: this.pos.get_order(), product: discountProduct});
                    const discount = - (total * promotion.total_discount)/100;
                    createNewDiscountLine.set_quantity(1);
                    createNewDiscountLine.price_manually_set = true;
                    createNewDiscountLine.set_unit_price(discount);
                    createNewDiscountLine.set_promotion(promotion);
                    this.orderlines.add(createNewDiscountLine);
                    this.add_orderline(createNewDiscountLine);
                    this.set_order_total_discount(promotion);
                    this.set_order_total_discount_line(createNewDiscountLine);
                }
            }
        },
        remove_discount_product : function(promotion){
            for(const _line of this.get_orderlines()){
                if(_line.product.id === promotion.discount_product[0]){
                    this.remove_orderline(_line);
                    return true;
                }
            }
        },
        check_for_valid_promotion: function(promotion){
            var current_time = Number(moment(new Date().getTime()).locale('en').format("H"));
            if((Number(promotion.from_time) <= current_time && Number(promotion.to_time) > current_time) ||
                (!promotion.from_time && !promotion.to_time)){
                return true;
            } else{
                return false;
            }
        },
        add_product:function(product, options){
            var self = this;
            _ModelProto.add_product.call(this,product, options);
            if(this.pos.config.customer_display){
                self.mirror_image_data();
            }
            if(self.pos.config.enable_pos_promotion && self.pos.user.access_pos_promotion){
                this.apply_pos_promotion(product);
                this.apply_pos_order_discount_total();
            }
        },
        apply_pos_promotion: function(product){
            var current_time = Number(moment(new Date().getTime()).locale('en').format("H"));
            var selectedLine =  this.get_selected_orderline();

            for(var promotion of this.pos.pos_promotions){
                let promotion_type = promotion.promotion_type;
                let flag = false;
                switch (promotion_type) {
                    case 'buy_x_get_y':
                        this.apply_buy_x_get_y_promotion(promotion);
                        break;
                    case 'buy_x_get_dis_y':
                        this.apply_buy_x_disc_y_promotion(promotion);
                        break;
                    case 'quantity_discount':
                        this.apply_quantity_discount(promotion);
                        break;
                    case 'quantity_price':
                        this.apply_quantity_price(promotion);
                        break;
                    case 'discount_on_multi_product':
                        this.apply_discount_on_multi_product(promotion);
                        break;
                    case 'discount_on_multi_category':
                        this.apply_discount_on_multi_category(promotion, product);
                        break;
                }
            }
        },
        // BUY X GET Y FREE PROMOTION START
        update_promotion_line : function(orderLine, prom_prod_id, promotion, final_qty){
            let promo_product = this.pos.db.get_product_by_id(prom_prod_id);
            var currentOrderLine = this.get_selected_orderline();

            if(!orderLine){
                var new_line = new models.Orderline({}, {pos: this.pos, order: this.pos.get_order(), product: promo_product});
                    new_line.set_quantity(final_qty);
                    new_line.price_manually_set = true;
                    new_line.set_unit_price(0);
                    new_line.set_unique_child_id(currentOrderLine.get_unique_parent_id());
                    new_line.set_promotion(promotion);
                    this.pos.get_order().add_orderline(new_line);
            }else{
                orderLine.price_manually_set = true;
                orderLine.set_unit_price(0);
                orderLine.set_quantity(final_qty);
            }
            this.select_orderline(currentOrderLine);
        },

        apply_buy_x_get_y_promotion: async function(promotion){
            if(!this.check_for_valid_promotion(promotion))
                return;
            var selectedOrderLine = this.get_selected_orderline();
            if(selectedOrderLine && promotion.pos_condition_ids.length > 0){
                for(const _line_id of promotion.pos_condition_ids){
                    var _record = this.pos.pos_conditions_by_id[_line_id];
                    if(selectedOrderLine.product.id === _record.product_x_id[0]){

                        let prom_qty = Math.floor(selectedOrderLine.quantity / _record.quantity);
                        let final_qty = Math.floor(prom_qty * _record.quantity_y);
                        if(_record.operator === 'greater_than_or_eql' && selectedOrderLine.quantity >= _record.quantity){
                            if(selectedOrderLine && !selectedOrderLine.get_unique_parent_id()){
                                selectedOrderLine.set_unique_parent_id(Math.floor(Math.random() * 1000000000));
                            }
                            var parentId = await selectedOrderLine ? selectedOrderLine.get_unique_parent_id() : false;
                            var childOrderLine = this.get_orderline_by_unique_id(parentId ? selectedOrderLine.get_unique_parent_id() : false);
                            this.update_promotion_line(childOrderLine, _record.product_y_id[0], promotion, final_qty);
                        }
                        break;
                    }
                }
            }
        },
        // BUY X GET Y FREE PROMOTION END
        apply_buy_x_disc_y_promotion: function(promotion){
            if(!this.check_for_valid_promotion(promotion))
                return;
            var SelectedLine = this.get_selected_orderline();
            var _lineById = [];
            var orderLines = _.filter(this.get_orderlines(), function(line){
                                 if(!line.get_promotion()){
                                     return line;
                                 }
                             });
            var lineProductIds = _.pluck(_.pluck(orderLines, 'product'),  'id');
            var flag = false;
            var discountLineList = [];
            if(promotion && !promotion.parent_product_ids){
                return false;
            };
            for(var _line of orderLines){
                if(_.contains(promotion && promotion.parent_product_ids, _line.product.id)){
                    if(!_line.get_promotion_flag() && !_line.get_unique_parent_id()){
                        _lineById.push(_line);
                    }
                    for(const discId of promotion.pos_quantity_dis_ids){
                        let discountLineRecord = this.pos.get_discount_by_id[discId];
                            discountLineRecord && discountLineRecord.product_id_dis ? discountLineList.push(discountLineRecord) : '';
                    }
                    flag = true;
                    break;
                }
            }
            if(!flag){
                return;
            }
            for(var _line of orderLines){
                for(const _discount of discountLineList){
                    if(_discount.product_id_dis && _discount.product_id_dis[0] == _line.product.id){
                        var parentLine =  _.filter(_lineById, function(line){
                                     if(!line.get_promotion_disc_parent_id() && _.contains(promotion.parent_product_ids, line.product.id)){
                                         return line;
                                     }
                                 });
                        if(parentLine.length > 0 && _line.quantity >= _discount.qty){
                            if(parentLine.length > 0 && !parentLine[0].get_promotion_disc_parent_id()){
                                parentLine[0].set_promotion_disc_parent_id(Math.floor(Math.random() * 1000000000));
                                parentLine[0].set_unique_parent_id(null);
                                parentLine[0].set_promotion_flag(true);
                            }
                            _line.set_promotion(promotion);
                            _line.set_discount(_discount.discount_dis_x);
                            _line.set_promotion_disc_child_id(parentLine[0].get_promotion_disc_parent_id());
                        }
                    }
                }
            }
        },
        // APPLY PERCENTAGE DISCOUNT ON QUANTITY DONE
        apply_quantity_discount: function(promotion){
            if(!this.check_for_valid_promotion(promotion))
                return;
            var selected_line = this.get_selected_orderline();
            const {product_id_qty} = promotion;
            if(selected_line && product_id_qty && product_id_qty[0] === selected_line.product.id){
                for(const promo_id of promotion.pos_quantity_ids){
                    var line_record = this.pos.get_qty_discount_by_id[promo_id];
                    if(line_record && selected_line.quantity >= line_record.quantity_dis){
                        if(line_record.discount_dis){
                            selected_line.set_promotion(promotion);
                            selected_line.set_discount(line_record.discount_dis);
                        }
                    }
                }
            }
        },
        // APPLY PERCENTAGE DISCOUNT ON QUANTITY END
        apply_quantity_price: function(promotion){
            if(!this.check_for_valid_promotion(promotion))
                return;
            var selected_line = this.get_selected_orderline();
            if(selected_line && promotion.product_id_amt && promotion.product_id_amt[0] == selected_line.product.id){
                for(const qty_amt_id of promotion.pos_quantity_amt_ids){
                    let line_record = this.pos.pos_qty_discount_amt_by_id[qty_amt_id];
                    if(line_record && selected_line.quantity >= line_record.quantity_amt){
                        if(line_record.discount_price){
                            selected_line.set_promotion(promotion);
                            selected_line.set_unit_price(((selected_line.get_unit_price() * selected_line.get_quantity()) -
                            line_record.discount_price)/selected_line.get_quantity());
                            break;
                        }
                    }
                }
            }
        },
        // APPLY DISCOUNT ON MULTIPLE PRODUCTS
        apply_discount_on_multi_product: function(promotion){
            if(!this.check_for_valid_promotion(promotion))
                return;
            if(promotion.multi_products_discount_ids){
                for(const disc_line_id of promotion.multi_products_discount_ids){
                    var disc_line_record = this.pos.pos_discount_multi_prods_by_id[disc_line_id];
                    if(disc_line_record){
                        this.check_products_for_disc(disc_line_record, promotion);
                    }
                }
            }
        },
        // APPLY DISCOUNT ON MULTIPLE PRODUCTS METHOD - check_products_for_disc
        check_products_for_disc: function(disc_line, promotion){
            var self = this;
            var lines = _.filter(self.get_orderlines(), function(line){
                            if(!line.get_promotion()){
                                return line;
                            }
                        });
            var product_cmp_list = [];
            var orderLine_ids = [];
            var products_qty = [];
            if(disc_line.product_ids && disc_line.products_discount){
                _.each(lines, function(line){
                    if(_.contains(disc_line.product_ids, line.product.id)){
                        product_cmp_list.push(line.product.id);
                        orderLine_ids.push(line.id);
                        products_qty.push(line.get_quantity());
                    }
                });
                if(!_.contains(products_qty, 0)){
                    if(_.isEqual(_.sortBy(disc_line.product_ids), _.sortBy(product_cmp_list))){
                        const combination_id = Math.floor(Math.random() * 1000000000);
                        _.each(orderLine_ids, function(orderLineId){
                            var order_line = self.get_orderline(orderLineId);
                            if(order_line && order_line.get_quantity() > 0){
                                order_line.set_discount(disc_line.products_discount);
                                order_line.set_promotion(promotion);
                                order_line.set_combination_id(combination_id);
                            }
                        });
                    }
                }
            }
        },
        // APPLY DISCOUNT ON MULTIPLE CATEGORIES DONE
        apply_discount_on_multi_category: function(promotion, product){
            if(!this.check_for_valid_promotion(promotion))
                return;
            var selected_line = this.get_selected_orderline();
            if(!product) return;
            if(promotion.multi_category_discount_ids){
                for(const disc_id of promotion.multi_category_discount_ids){
                    let disc_obj = this.pos.pos_discount_multi_category_by_id[disc_id];
                    if(disc_obj && disc_obj.category_ids && disc_obj.category_discount, product.pos_categ_id[0]){
                        if(_.contains(disc_obj.category_ids ,  product.pos_categ_id[0])){
                            selected_line.set_discount(disc_obj.category_discount);
                            selected_line.set_promotion(promotion);
                            break;
                        }
                    }
                }
            };
        },
        /* POS Promotion Code End */
    });
    models.Paymentline = models.Paymentline.extend({
        initialize: function(attributes, options) {
           var self = this;
           _super_paymentline.initialize.apply(this, arguments);
        },
        set_giftcard_line_code: function(gift_card_code) {
            this.gift_card_code = gift_card_code;
        },
        get_giftcard_line_code: function(){
            return this.gift_card_code;
        },
    });
    exports.CustomerModel = Backbone.Model.extend({
        initialize: function(attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            var  self = this;

            this.env = this.get('env');
            this.rpc = this.get('rpc');
            this.session = this.get('session');
            this.do_action = this.get('do_action');

            // Business data; loaded from the server at launch
            this.company_logo = null;
            this.company_logo_base64 = '';
            this.currency = null;
            this.company = null;
            this.pos_session = null;
            this.config = null;
            window.posmodel = this;

            var given_config = new RegExp('[\?&]config_id=([^&#]*)').exec(window.location.href);
            this.config_id = odoo.config_id || false;

            this.ready = this.load_server_data().then(function(){
                return;
            });
        },
        after_load_server_data: function(){
            this.load_orders();
            return Promise.resolve();
        },
        // releases ressources holds by the model at the end of life of the posmodel
        destroy: function(){
            // FIXME, should wait for flushing, return a deferred to indicate successfull destruction
            // this.flush();
            this.proxy.disconnect();
            this.barcode_reader.disconnect_from_proxy();
        },
        models: [
        {
            model:  'res.company',
            fields: [ 'currency_id', 'email', 'website', 'company_registry', 'vat', 'name', 'phone', 'partner_id' , 'country_id', 'state_id', 'tax_calculation_rounding_method'],
            ids:    function(self){ return [self.session.user_context.allowed_company_ids[0]]; },
            loaded: function(self,companies){ self.company = companies[0]; },
        },{
            model: 'pos.config',
            fields: [],
            domain: function(self){ return [['id','=', self.config_id]]; },
            loaded: function(self,configs){
                self.config = configs[0];
           },
        },{
            model: 'customer.display',
            fields: [],
            domain: function(self){ return [['config_id','=', self.config_id]]; },
            loaded: function(self,configs){
                self.ad_data = configs;
           },
        },{
            model: 'res.currency',
            fields: ['name','symbol','position','rounding','rate'],
            ids:    function(self){ return [self.config.currency_id[0], self.company.currency_id[0]]; },
            loaded: function(self, currencies){
                self.currency = currencies[0];
                if (self.currency.rounding > 0 && self.currency.rounding < 1) {
                    self.currency.decimals = Math.ceil(Math.log(1.0 / self.currency.rounding) / Math.log(10));
                } else {
                    self.currency.decimals = 0;
                }

                self.company_currency = currencies[1];
            },
        },{
            model:  'decimal.precision',
            fields: ['name','digits'],
            loaded: function(self,dps){
                self.dp  = {};
                for (var i = 0; i < dps.length; i++) {
                    self.dp[dps[i].name] = dps[i].digits;
                }
            },
        },{
            model:  'ad.video',
            fields: ['video_id'],
            domain: function(self){ return [['config_id','=', self.config_id]]; },
            loaded: function(self,result){
                self.ad_video_ids = [];
                for (var i = 0; i < result.length; i++) {
                    self.ad_video_ids.push(result[i].video_id)
                }
            },
        }
        ],

        load_server_data: function(){
            var self = this;
            var tmp = {};

            var loaded = new Promise(function (resolve, reject) {
                function load_model(index) {
                    if (index >= self.models.length) {
                        resolve();
                    } else {
                        var model = self.models[index];

                        var cond = typeof model.condition === 'function'  ? model.condition(self,tmp) : true;
                        if (!cond) {
                            load_model(index+1);
                            return;
                        }

                        var fields =  typeof model.fields === 'function'  ? model.fields(self,tmp)  : model.fields;
                        var domain =  typeof model.domain === 'function'  ? model.domain(self,tmp)  : model.domain;
                        var context = typeof model.context === 'function' ? model.context(self,tmp) : model.context || {};
                        var ids     = typeof model.ids === 'function'     ? model.ids(self,tmp) : model.ids;
                        var order   = typeof model.order === 'function'   ? model.order(self,tmp):    model.order;

                        if( model.model ){
                            var params = {
                                model: model.model,
                                context: _.extend(context, self.session.user_context || {}),
                            };

                            if (model.ids) {
                                params.method = 'read';
                                params.args = [ids, fields];
                            } else {
                                params.method = 'search_read';
                                params.domain = domain;
                                params.fields = fields;
                                params.orderBy = order;
                            }

                            self.rpc(params).then(function (result) {
                                try { // catching exceptions in model.loaded(...)
                                    Promise.resolve(model.loaded(self, result, tmp))
                                        .then(function () { load_model(index + 1); },
                                            function (err) { reject(err); });
                                } catch (err) {
                                    console.error(err.message, err.stack);
                                    reject(err);
                                }
                            }, function (err) {
                                reject(err);
                            });
                        } else if (model.loaded) {
                            try { // catching exceptions in model.loaded(...)
                                Promise.resolve(model.loaded(self, tmp))
                                    .then(function () { load_model(index +1); },
                                        function (err) { reject(err); });
                            } catch (err) {
                                reject(err);
                            }
                        } else {
                            load_model(index + 1);
                        }
                    }
                }

                try {
                    return load_model(0);
                } catch (err) {
                    return Promise.reject(err);
                }
            });

            return loaded;
        },
        format_currency: function(amount, precision) {
            var currency =
                this && this.currency
                    ? this.currency
                    : { symbol: '$', position: 'after', rounding: 0.01, decimals: 2 };

            amount = this.format_currency_no_symbol(amount, precision, currency);

            if (currency.position === 'after') {
                return amount + ' ' + (currency.symbol || '');
            } else {
                return (currency.symbol || '') + ' ' + amount;
            }
        },

        format_currency_no_symbol: function(amount, precision, currency) {
            if (!currency) {
                currency =
                    this && this.currency
                        ? this.currency
                        : { symbol: '$', position: 'after', rounding: 0.01, decimals: 2 };
            }
            var decimals = currency.decimals;

            if (precision && this.dp[precision] !== undefined) {
                decimals = this.dp[precision];
            }

            if (typeof amount === 'number') {
                amount = round_di(amount, decimals).toFixed(decimals);
                amount = field_utils.format.float(round_di(amount, decimals), {
                    digits: [69, decimals],
                });
            }
            return amount;
        },
    });
    return exports;

});
