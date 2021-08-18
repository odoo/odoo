odoo.define('point_of_sale.PackLotLineScreen', function(require) {
    'use strict';

    const { useState } = owl.hooks;
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const IndependentToOrderScreen = require('point_of_sale.IndependentToOrderScreen');

    class PackLotLineScreen extends IndependentToOrderScreen {
        constructor() {
            super(...arguments);
            useListener('toggle-Lot', this._toggleLot);
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            useListener('toggle-button-highlight', this._toggleButtonActive);
            this.lot = useState({ isLotSelected : false,buttonActive: false});
            this.searchDetails = {};
            this.state = {
                filter: null,
                activePage: 0,
                totalPages: 0,  
            };
            this._initializeSearchFieldConstants();
            this._lineIsSelected();
        }
        _toggleButtonActive(){
            let selectedLines = this.props.serials.filter(serial => serial.isSelected == true);
            this.lot.buttonActive = true ? selectedLines.length != 0 : false;
        }
        _closePackLotScreen(){
            let serialApplied = [];
            let orderLine = this.env.pos.get_order().get_selected_orderline();
            if(this.props.orderline){
                orderLine = this.props.orderline;
            }
            _.each(orderLine.getPackLotLinesToEdit(), function(packLot){
                if(packLot.text != ''){
                    serialApplied.push(packLot.text)
                }
            });
            _.each(this.props.serials, function(serial){
                if(!serialApplied.includes(serial.name)){
                    serial.isSelected = false;
                }
            });
            this.close();
        }
        _lineIsSelected(){
            let selectedLines = this.props.serials.filter(serial => serial.isSelected == true);
            if(selectedLines.length != 0){
                this.lot.isLotSelected = true;
            }
        }
        onClickNext(){
            if((this.state.activePage + 1) != this.state.totalPages){
                this.state.activePage += 1;
                this.render();
            }
        }
        onClickPrevious(){
            if((this.state.activePage + 1) != 1){
                this.state.activePage -= 1;
                this.render();
            }
        }
        onClickFirstPage(){
            this.state.activePage = 0;
            this.render();
        }
        _updateTotalPages(pages){
            this.state.totalPages = pages == 0 ? 1 : pages;
        }
        get totalNumberOfPage(){
            const filterCheck = (order) => {
                if (this.state.filter && this.state.filter !== 'All') {
                    if(this.state.filter === 'Selected' || this.state.filter === 'Unselected'){
                        const screen = order.isSelected;
                        return this.state.filter === this.constants.screenToStatusMap[screen];
                    }
                    if(this.state.filter === 'Near To Expire'){
                        const screen = order.NearToExpire;
                        return this.state.filter === this.constants.screenToStatusMap[screen];
                    }
                }
                return true;
            };
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
                return filterCheck(order) && searchCheck(order);
            };
            var searchedResult = this.SerialsList.filter(predicate);
            var total_pages_num = Math.ceil(searchedResult.length / 10)
            var total_pages = total_pages_num == 0 ? 1 : total_pages_num
            return total_pages
        }
        async printSerials(){
            let selectedLines = this.props.serials.filter(serial => serial.NearToExpire == 'NearToExpire');
            var use_posbox = this.env.pos.config.is_posbox && (this.env.pos.config.iface_print_via_proxy);
            if (use_posbox || this.env.pos.config.other_devices) {
               const report = this.env.qweb.renderToString('PosSerialReceipt',{props: {'receiptData':selectedLines }});
               const printResult = await this.env.pos.proxy.printer.print_receipt(report);
               if (!printResult.successful) {
                   await this.showPopup('ErrorPopup', {
                       title: printResult.message.title,
                       body: printResult.message.body,
                   });
               }
            }else{
                this.showScreen('ReceiptScreen', {'check':'from-packLot-screen', 'receiptData':selectedLines});
            }
        }
        _toggleLot(){
            this.lot.isLotSelected = !this.lot.isLotSelected;
        }
        _onFilterSelected(event) {
            this.state.filter = event.detail.filter;
            this.onClickFirstPage()
            this.render();
        }
        get SerialsList() {
            return this.props.serials;
        }
        _onSearch(event) {
            const searchDetails = event.detail;
            Object.assign(this.searchDetails, searchDetails);
            this.render();
        }
        get filteredSerialList() {
            const filterCheck = (order) => {
                if (this.state.filter && this.state.filter !== 'All') {
                    if(this.state.filter === 'Selected' || this.state.filter === 'Unselected'){
                        const screen = order.isSelected;
                        return this.state.filter === this.constants.screenToStatusMap[screen];
                    }
                    if(this.state.filter === 'Near To Expire'){
                        const screen = order.NearToExpire;
                        return this.state.filter === this.constants.screenToStatusMap[screen];
                    }
                }
                return true;
            };
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
                return filterCheck(order) && searchCheck(order);
            };
            var searchedResult = this.SerialsList.filter(predicate);
            let indexOfFirstRecord = this.state.activePage * 10;
            let indexOfLastRecord =  (this.state.activePage + 1) * 10;
            this._updateTotalPages(Math.ceil(searchedResult.length / 10));
            return searchedResult.slice(indexOfFirstRecord, indexOfLastRecord);
        }
        get searchBarConfig() {
            return {
                searchFields: this.constants.searchFieldNames,
                filter: { show: true, options: this.filterOptions },
            };
        }
        get filterOptions() {
            return ['All','Selected','Unselected','Near To Expire'];
        }
        get _searchFields() {
            var fields = {}
            fields = {
                'Lot/Serial': (line) => line.name,
                'Expiry Date': (line) => line.expiration_date,
            };
            return fields;
        }
        get _screenToStatusMap() {
            return {
                true : 'Selected',
                false : 'Unselected',
                NearToExpire : 'Near To Expire'
            };
        }
        _initializeSearchFieldConstants() {
            this.constants = {};
            Object.assign(this.constants, {
                searchFieldNames: Object.keys(this._searchFields),
                screenToStatusMap: this._screenToStatusMap,
            });
        }
        applyPackLotLines(){
            let orderLine = this.env.pos.get_order().get_selected_orderline();
            if(this.props.orderline){
                orderLine = this.props.orderline;
            }
            let selectedLines = [];
            selectedLines = this.props.serials.filter(serial => serial.isSelected == true);
            if(selectedLines.length >= 1){
                let modifiedPackLotLines = {};
                if(this.props.isSingleItem){
                    if(selectedLines[0].inputQty > selectedLines[0].product_qty){
                        alert('Invalid Quantity!');
                        return;
                    }else{
                        let numberOfInputs = selectedLines[0].inputQty;
                        let newPackLotLines = selectedLines.filter(item => item.id).map(item => ({ lot_name: item.name }));
                        orderLine.setPackLotLines({ modifiedPackLotLines, newPackLotLines });
                        orderLine.set_quantity(selectedLines[0].inputQty);
                        this._closePackLotScreen();
                        return;
                    }
                }
                let newPackLotLines = selectedLines.filter(item => item.id).map(item => ({ lot_name: item.name }));
                orderLine.setPackLotLines({ modifiedPackLotLines, newPackLotLines });
                this._closePackLotScreen();
            }else{
                alert('Please assign Lot/Serial of product!')
            }
        }
    }

    PackLotLineScreen.template = 'PackLotLineScreen';

    Registries.Component.add(PackLotLineScreen);

    return PackLotLineScreen;
});
