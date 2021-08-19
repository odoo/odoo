    odoo.define('point_of_sale.OrderReturnProductList', function(require) {
    'use strict';

    const { useState } = owl.hooks;
    const { useAutofocus, useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const OrderFetcher = require('point_of_sale.OrderFetcher');
    const contexts = require('point_of_sale.PosContext');


    const VALID_SEARCH_TAGS = new Set(['order']);
    const FIELD_MAP = {
        name: 'pos_reference',
        order: 'pos_reference',
    };
    const SEARCH_FIELDS = ['pos_reference'];

    function getDomainForSingleCondition(fields, toSearch) {
        const orSymbols = Array(fields.length - 1).fill('|');
        return orSymbols.concat(fields.map((field) => [field, 'ilike', `%${toSearch}%`]));
    }

    class OrderReturnProductList extends PosComponent {
        constructor() {
            super(...arguments);
            this.product = this.env.pos.db.get_product_by_id(this.props.line.product_id) 
            var serialProduct = false
            if (this.props.line.pack_lot_ids.length > 0 && !this.product.isAllowOnlyOneLot()){
                serialProduct = true
            }
            this.state = useState({ProductQty: 0, LotProduct: this.product.isAllowOnlyOneLot(), serialProduct: serialProduct})
        }

        QuantityValidation(e) {
            var prevent = false
            if(e.key == '!' || e.key == '@' || e.key == '#' || e.key == '$' || e.key == '%' || e.key == '^' || e.key == '&' || e.key == '*' || e.key == '(' || e.key == ')') {
                prevent = true;
            }else if (e.which == 46 || e.which == 8 || !(e.which < 96 || e.which > 105) || !(e.which < 48 || e.which > 57) || !(e.which < 37 || e.which > 40)){
                prevent = false;
            }else{
                prevent = true;

            }
            if (prevent){
                e.preventDefault();
            }
        }
        get imageUrl() {
            const lines = this.env.pos.db.get_product_by_id(this.props.line.product_id);
            return `/web/image?model=product.product&field=image_128&id=${lines.id}&write_date=${lines.write_date}&unique=1`;
        }
        get Orderqty() {
            if (this.props.ReturnProduct){
                return this.props.line.order_return_qty
            }else{
                return this.state.ProductQty
            }
        }
        addQty(event){
            if (!this.props.ReturnProduct){
                if (this.props.line.return_qty >= this.props.line.order_return_qty){
                    this.props.line.return_qty = this.props.line.order_return_qty
                }else{
                    this.props.line.return_qty += 1
                }
            }
        }
        removeQty(){
            if (!this.props.ReturnProduct){
                if (this.props.line.return_qty <= 0){
                    this.props.line.return_qty = 0
                }else{
                    this.props.line.return_qty -= 1
                }
            }
        }
    }
    OrderReturnProductList.template = 'OrderReturnProductList';

    Registries.Component.add(OrderReturnProductList);

    return OrderReturnProductList;
});
