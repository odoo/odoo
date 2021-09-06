odoo.define('point_of_sale.RefillMedicineScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const { useState } = owl.hooks;
    var rpc = require('web.rpc');

    class RefillMedicineScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.filter = null;
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            useListener('ViewMedicineOrder', this.ViewMedicineOrder);
            this.state = useState({ 'ViewRefillMedicineOrder': false, 'MedicineOrderData': false});
            this.searchDetails = {};
            this._initializeSearchFieldConstants();
        }
        async orderLines() {
            var lines = await rpc.query({
                model: 'pos.recurrent.prod.line',
                method: 'search_read',
                domain: [['id', 'in', event.detail.line.product_line]],
            }, {async: false}).then(function(res){
                return res
            });
            return lines
        }
        async ViewMedicineOrder(event){
            event.detail.line['order_lines'] = await this.orderLines(event)
            this.state.ViewRefillMedicineOrder = true
            this.state.MedicineOrderData = event.detail.line
        }
        _onFilterSelected(event) {
            this.filter = event.detail.filter;
            this.render();
        }
        get SerialsList() {
            return this.env.pos.recurrent_order_list;
        }
        _onSearch(event) {
            const searchDetails = event.detail;
            Object.assign(this.searchDetails, searchDetails);
            this.render();
        }
        get filteredRefillList() {
            const { fieldValue, searchTerm } = this.searchDetails;
            const fieldAccessor = this._searchFields[fieldValue];
            const searchCheck = (order) => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(order);
                if (fieldValue === null) return true;
                if (!searchTerm) return true;
                return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (order) => {
                return searchCheck(order);
            };
            return this.SerialsList.filter(predicate);
        }
        get searchBarConfig() {
            return {
                searchFields: this.constants.searchFieldNames,
                filter: { show: true, options: this.filterOptions },
            };
        }
        get filterOptions() {
            return ['All'];
        }
        get _searchFields() {
            var fields = {}
            fields = {
                'Name': (line) => line.partner_id[1],
                'Next Execution Date': (line) => line.next_exe_date,
            };
            return fields;
        }
        _initializeSearchFieldConstants() {
            this.constants = {};
            Object.assign(this.constants, {
                searchFieldNames: Object.keys(this._searchFields),
            });
        }
        _closeRefillMedicineScreen(){
            this.showScreen('ProductScreen');
        }
        _closeRefillMedicineOrderScreen(){
            this.state.ViewRefillMedicineOrder = false
            this.state.MedicineOrderData = false
        }
        async reloadRefillMedicine(){
            var self = this;
            var params = {
                model: 'pos.recurrent.order',
                method: 'search_read',
                domain: [],
            }
            await self.rpc(params).then(function(result){
                self.env.pos.recurrent_order_list = result;
                self.render();
            });
        }
        async CreateRefillMedicine(){
            this.showScreen('RefillProductDetailScreen');
        }
    }
    RefillMedicineScreen.template = 'RefillMedicineScreen';

    Registries.Component.add(RefillMedicineScreen);

    return RefillMedicineScreen;
});
