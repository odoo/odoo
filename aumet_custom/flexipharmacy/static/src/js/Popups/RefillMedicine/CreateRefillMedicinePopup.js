odoo.define('flexipharmacy.CreateRefillMedicinePopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    class CreateRefillMedicinePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            useListener('remove-line', () => this.removeLine(event));
            this._id = 0;
            this.state = useState({ 
                isDeliver: false,
                selectedCustomer: '',
                NoOfDays: 0,
                ExecutionDate: moment(new Date()).format("DD/MM/YYYY"),
                DeliveryAddress: '',
                CustomerBlank: false,
                showStaticLines: true});
        }
        async onInputKeyDownNumberVlidation(e) {
            if(e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57) && (e.which < 96 || e.which > 105) && (e.which < 37 || e.which > 40)) {
                e.preventDefault();
            }
            if(e.which == 13){
                this.state.pointsAmount = this.state.LoyaltyPoints * this.props.amount_per_point;
            }
            if(e.which == 190){
                e.preventDefault();
            }
        }
        changeCustomer(){
            if ($('#select_recurrent_customer').val() && this.state.isDeliver){
                var customer_id = $('option[value="'+$('#select_recurrent_customer').val()+'"]').attr('id')
                var customer_address = this.env.pos.db.get_partner_by_id(customer_id).address
                this.state.DeliveryAddress = customer_address
            }else{
                this.state.DeliveryAddress = ''
            }
        }
        changeExecutionDate(event){
            this.state.ExecutionDate = moment(moment(new Date())).add(event, 'days').format("DD/MM/YYYY")
        }
        DeletePurchaseLine(event){
            var SelectedProductList = _.without(this.props.SelectedProductList, _.findWhere(this.props.SelectedProductList, {id: event.id}));
            this.props.SelectedProductList = SelectedProductList
            this.render();
        }
        getPayload() {
            var line = this.RefillMedicineLineData()
            var customer = $('option[value="'+$('#select_recurrent_customer').val()+'"]').attr('id')
            return {
                partner_id: Number(customer), 
                line: line, 
                NoOfDays: Number(this.state.NoOfDays),
                isDeliver: this.state.isDeliver,
                ExecutionDate: this.state.ExecutionDate,
                DeliveryAddress: this.state.DeliveryAddress,
                pos_id: this.env.pos.config.id,
                user_id: this.env.pos.user.id,  
            };
        }
        RefillMedicineLineData() {
            var order_line = []
            for (var i=0;i<=this.props.SelectedProductList.length;i++){
                var line = {}
                if(this.props.SelectedProductList[i]){
                    var qty = $('td.product_qty').find('input#'+this.props.SelectedProductList[i].id).val()
                    var price = $('td.product_price').find('input#'+this.props.SelectedProductList[i].id).val()
                    line['product_id'] = this.props.SelectedProductList[i].id
                    line['qty'] = Number(qty)
                    line['price'] = Number(price)
                    order_line.push(line)
                }
            }
            return order_line
        }
        async confirm(){
            if (this.state.selectedCustomer == ""){
                this.state.CustomerBlank = true
            }else{
                this.state.CustomerBlank = false
            }
            if (this.state.CustomerBlank){
                return
            }else {
                this.props.resolve({ confirmed: true, payload: await this.getPayload() });
                this.trigger('close-popup');
            }
            return
        }
        cancel(){
            this.trigger('close-popup');
        }
    }
    CreateRefillMedicinePopup.template = 'CreateRefillMedicinePopup';

    CreateRefillMedicinePopup.defaultProps = {
        confirmText: 'Create',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(CreateRefillMedicinePopup);

    return CreateRefillMedicinePopup;
});
