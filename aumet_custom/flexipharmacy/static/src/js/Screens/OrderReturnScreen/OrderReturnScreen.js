    odoo.define('point_of_sale.OrderReturnScreen', function(require) {
    'use strict';

    const { useContext, useState } = owl.hooks;
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
        return orSymbols.concat(fields.map((field) => [field, '=', `Order ${toSearch}`]));
    }

    class OrderReturnScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.orderManagementContext = useContext(contexts.orderManagement);
            useListener('clear-search', this._onClearSearch);
            useListener('serialNumberPopup', this.OpenSerialNumberPopup);
            useListener('search', this._onSearch);
            useAutofocus({ selector: 'input' });
            this.ordersToShow = [];
            this.cancel_search = false;
            this.state = useState({orders:[], orderlines:[], ReturnAllProduct: false, SelectedLotSerialList: []})
            OrderFetcher.setComponent(this);
            OrderFetcher.setConfigId(this.env.pos.config_id);
        }
        async OpenSerialNumberPopup(event) {
            var LineSerialNumber = []
            var SelectedLineSerialNumber = []
            _.each(event.detail.operation_lot_name, function(value,key) {
                var lot = {'id': key, 'name': value.lot_name}
                LineSerialNumber.push(lot)
            });
            const { confirmed, payload} = await this.showPopup(
                'SelectedSerialNumberPopup',
                {
                    title: this.env._t('Select Serial Number'),
                    numberlist: LineSerialNumber,
                    // selectedno: SelectedSerialList,
                }
            );

            if (confirmed) {
                _.each(payload, function(number) {
                    var lot = {lot_name: number.name}
                    SelectedLineSerialNumber.push(lot)
                });
                event.detail.line['select_operation_lot_name'] = SelectedLineSerialNumber
                event.detail.line['return_qty'] = SelectedLineSerialNumber.length
            }

        }
        onInputKeydown(event) {
            if (event.key === 'Enter') {
                this._onSearch()
            }
        }
        ReturnAllProductQty() {
            if (this.state.ReturnAllProduct){
                for (let lines of this.state.orderlines) {
                    var product_id = this.env.pos.db.get_product_by_id(lines.product_id)
                    const isAllowOnlyOneLot = product_id.isAllowOnlyOneLot();
                    if (lines.pack_lot_ids.length > 0 && !isAllowOnlyOneLot){
                        lines['select_operation_lot_name'] = []
                        lines.return_qty = 0
                    }else if (lines.pack_lot_ids.length > 0 && isAllowOnlyOneLot){
                        this.state.SelectedLotSerialList = []
                        lines['select_operation_lot_name'] = []
                        lines.return_qty = 0
                    }else{
                        lines.return_qty = 0
                    }
                }
            }else{
                for (let lines of this.state.orderlines) {
                    var product_id = this.env.pos.db.get_product_by_id(lines.product_id)
                    const isAllowOnlyOneLot = product_id.isAllowOnlyOneLot();
                    if (lines.pack_lot_ids.length > 0 && !isAllowOnlyOneLot){
                        lines['select_operation_lot_name'] = lines.operation_lot_name
                        lines.return_qty = lines.operation_lot_name.length
                    }else if (lines.pack_lot_ids.length > 0 && isAllowOnlyOneLot){
                        this.state.SelectedLotSerialList = lines.operation_lot_name
                        lines['select_operation_lot_name'] = lines.operation_lot_name
                        lines.return_qty = lines.order_return_qty
                    }else{
                        lines.return_qty = lines.order_return_qty
                    }
                }
            }
        }
        get searchFields() {
            return SEARCH_FIELDS;
        }
        back() {
            this.showScreen('ProductScreen');
        }
        _computeDomain() {
            const input = this.orderManagementContext.searchString.trim();
            if (this.orderManagementContext.searchString) {
                this.cancel_search = true;
            }else{
                this.cancel_search = false;
            }
            if (!input) return;
            const searchConditions = this.orderManagementContext.searchString.split(/[,&]\s*/);
            if (searchConditions.length === 1) {
                let cond = searchConditions[0].split(/:\s*/);
                if (cond.length === 1) {
                    return getDomainForSingleCondition(this.searchFields, cond[0]);
                }
            }
            const domain = [];
            for (let cond of searchConditions) {
                let [tag, value] = cond.split(/:\s*/);
                if (!this.validSearchTags.has(tag)) continue;
                domain.push([this.fieldMap[tag], '=', `Order ${value}`]);
            }
            return domain;
        }
        _onClearSearch() {
            this.orderManagementContext.searchString = 'Order ';
            this.onInputKeydown({ key: 'Enter' });
            this.state.orderlines = []
            this.state.orders = []
            this.orderManagementContext.searchString = '';
            this.cancel_search = false;
        }
        setComponent(comp) {
            this.comp = comp;
            return this;
        }
        async _onSearch() {
            let limit, offset;
            offset = 0;
            limit = 1;
            var search_order_id = await this.rpc({
                model: 'pos.order',
                method: 'search_paid_order_ids',
                kwargs: { config_id: this.env.pos.config.id, domain: this._computeDomain() ? this._computeDomain() : [['pos_reference', '=', 'Order ']], limit, offset},
                context: this.env.session.user_context,
            }); 
            if (search_order_id && search_order_id.totalCount > 0){
                this.state.orders = await this.rpc({
                    model: 'pos.order',
                    method: 'export_for_ui',
                    args: search_order_id.ids,
                    context: this.env.session.user_context,
                });
                this.state.orderlines = []
                for (let lines of this.state.orders[0].lines) {
                    lines[2]['return_qty'] = 0
                    this.state.orderlines.push(lines[2]);
                }
            }else{
                this.state.orderlines = []
                this.state.orders = []
            }
            this.render();
        }
        orderIsEmpty(order) {
            var self = this;
            var currentOrderLines = order.get_orderlines();
            var lines_ids = []
            if(!order.is_empty()) {
                let lines_ids = _.pluck(order.get_orderlines(), 'id');
                _.each(lines_ids,function(id) {
                    order.remove_orderline(order.get_orderline(id));
                });
            }
        }
        createReturnOrder() {
            var self = this
            if (this.state.orderlines && this.state.orderlines.length > 0){
                var order = self.env.pos.get_order()
                var lines = order.get_orderlines();
                if(lines.length > 0){
                    self.orderIsEmpty(order);
                }
                var partner_id = this.env.pos.db.get_partner_by_id(this.state.orders[0].partner_id)
                this.env.pos.get_order().set_client(partner_id);
                _.each(this.state.orderlines, function (lines) {
                    if (lines.return_qty > 0){
                        var product_id = self.env.pos.db.get_product_by_id(lines.product_id)
                        var quantity = 0
                        if (lines.return_qty > lines.order_return_qty){
                            quantity = -lines.order_return_qty
                        }else{
                            quantity = -lines.return_qty
                        }
                        var price_unit = lines.price_unit
                        if (lines.pack_lot_ids.length > 0){
                            const isAllowOnlyOneLot = product_id.isAllowOnlyOneLot();
                            if (lines.pack_lot_ids.length > 0 && !isAllowOnlyOneLot){
                                self.state.SelectedLotSerialList = lines.select_operation_lot_name
                            }else{
                                self.state.SelectedLotSerialList = lines.operation_lot_name
                            }
                            let draftPackLotLines
                            const modifiedPackLotLines = {}
                            var newPackLotLines = self.state.SelectedLotSerialList 
                            draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
                            draftPackLotLines
                            self.env.pos.get_order().add_product(product_id, {
                                draftPackLotLines,
                                quantity: quantity, 
                                price: price_unit,
                            });
                            let orderLine = self.env.pos.get_order().get_selected_orderline();
                            orderLine.set_quantity(quantity);
                        }else{
                            self.env.pos.get_order().add_product(product_id, {
                                quantity: quantity, 
                                price: price_unit,
                            });
                        }
                    }
                });
                this.env.pos.get_order().set_refund_ref_order(this.state.orders[0])
                if (this.env.pos.get_order().get_orderlines() && this.env.pos.get_order().get_orderlines().length > 0){
                    this.env.pos.get_order().set_refund_order(true)
                }
                this._onClearSearch()
                this.showScreen('ProductScreen', {'refund_order': true, 'refund_ref_order': this.state.orders});
            }
        }
    }
    OrderReturnScreen.template = 'OrderReturnScreen';

    Registries.Component.add(OrderReturnScreen);

    return OrderReturnScreen;
});
