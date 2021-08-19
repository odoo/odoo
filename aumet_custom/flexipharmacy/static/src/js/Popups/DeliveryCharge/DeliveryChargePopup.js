odoo.define('flexipharmacy.DeliveryChargePopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class DeliveryChargePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            var self = this;
            this.selectedUserName
            if(this.props.data.DeliveryUser){
                _.each(this.env.pos.users,function(users){
                    if(users.id == self.props.data.DeliveryUser){
                        self.selectedUserName = users.name 
                    }
                });
            }
            this.state = useState({
                IsDeliveryCharge: true, 
                DeliveryDate: this.props.data.DeliveryDate || '', 
                DeliveryTime: this.props.data.DeliveryTime || '00:00', 
                CustomerAddress: this.props.address || '', 
                DeliveryUser: this.selectedUserName || '',
                Msg:'',
                DeliveryDateBlank: false, 
                CustomerAddressBlank: false, 
                DeliveryUserBlank: false,
                DeliveryTimeBlanke: false,
                Today: moment().format('YYYY-MM-DD'),
            });
        }
        getPayload() {
            this.state.DeliveryUser = $('option[value="'+$('#delivery_user').val()+'"]').attr('id')
            return {
                IsDeliveryCharge: this.state.IsDeliveryCharge, 
                DeliveryDate: this.state.DeliveryDate, 
                DeliveryTime: this.state.DeliveryTime, 
                CustomerAddress: this.state.CustomerAddress, 
                DeliveryUser: Number(this.state.DeliveryUser),
            };
        }
        async confirm() {
            if (this.state.DeliveryDate == ""){
                this.state.DeliveryDateBlanke = true
            }else{
                this.state.DeliveryDateBlanke = false
            }
            if (this.state.DeliveryTime == ""){
                this.state.DeliveryTimeBlanke = true
            }else{
                this.state.DeliveryTimeBlanke = false
            }

            if (this.state.Today > this.state.DeliveryDate){
                this.state.Msg = "Date should not be before today date !"
                this.state.DeliveryDateBlanke = true
                return
            }else{
                this.state.DeliveryDateBlanke = false
            }
            if (this.state.CustomerAddress == ""){
                this.state.CustomerAddressBlank = true
            }else{
                this.state.CustomerAddressBlank = false
            }
            if (this.state.DeliveryUser == ""){
                this.state.DeliveryUserBlank = true
            }else{
                this.state.DeliveryUserBlank = false
            }
            if (this.state.DeliveryUserBlank || this.state.CustomerAddressBlank || this.state.DeliveryDateBlanke || this.state.DeliveryTimeBlanke){
                return
            }else{
                this.props.resolve({ confirmed: true, payload: await this.getPayload() });
                this.trigger('close-popup');
            }
        }
    }
    DeliveryChargePopup.template = 'DeliveryChargePopup';
    DeliveryChargePopup.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(DeliveryChargePopup);

    return DeliveryChargePopup;
});
