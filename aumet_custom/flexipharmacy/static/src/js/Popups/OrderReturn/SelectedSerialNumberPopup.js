odoo.define('flexipharmacy.SelectedSerialNumberPopup', function (require) {
    'use strict';

    const { useState } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class SelectedSerialNumberPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ selectItem: [], selectedLotid: [], SelectAll: false});
            this.selectedLot = []
            this.selectedLotid = []
        }
        SelectAll() {
            var self = this;
            if (this.state.SelectAll){
                this.state.selectItem = []
                this.state.selectedLotid = []
                this.state.SelectAll = false
            }else{
                this.state.selectItem = this.props.numberlist
                _.each(this.props.numberlist, function(value,key) {
                    self.state.selectedLotid.push(key)    
                });
                this.state.SelectAll = true
            }
        }
        selectItem(itemId) {
            if(this.selectedLot.length > 0){
                if (this.selectedLot.includes(itemId)){
                    this.selectedLot = _.without(this.selectedLot, itemId)
                    this.state.selectedLotid = _.without(this.state.selectedLotid, itemId.id)
                    if (this.state.selectedLotid.length == 0){
                        this.state.SelectAll = false
                    }
                }else{
                    this.selectedLot.unshift(itemId)
                    this.state.selectedLotid.unshift(itemId.id)
                    if (this.props.numberlist.length == this.state.selectedLotid.length){
                        this.state.SelectAll = true
                    }
                }
            }else{
                this.selectedLot.push(itemId)
                this.state.selectedLotid.push(itemId.id)
                if (this.props.numberlist.length == this.state.selectedLotid.length){
                    this.state.SelectAll = true
                }
            }
            this.state.selectItem = this.selectedLot
        }
        getPayload() {
            return this.selectedLot;
        }
    }
    SelectedSerialNumberPopup.template = 'SelectedSerialNumberPopup';
    SelectedSerialNumberPopup.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Select',
        body: '',
        list: [],
    };

    Registries.Component.add(SelectedSerialNumberPopup);

    return SelectedSerialNumberPopup;
});
