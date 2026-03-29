/** @odoo-module */
import { registry} from '@web/core/registry';
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
const { Component, useState } = owl
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
    var currency=0;
export class PharmacyOrderLines extends Component {
    setup() {
        super.setup(...arguments);
        this.orm = useService('orm')
        this.user = user;
        this.actionService = useService("action");
        this.state = useState({
              product_lst :[],
              medicines :[],
              units :[],
              medicine :[],
              table_row: [{}]
        });
        this.lineState = useState({
            product: this.props.line.product || false,
            qty: this.props.line.qty || 1,
            uom: this.props.line.uom || false,
            price: this.props.line.price || 0,
            sub_total: this.props.line.sub_total || 0,
        })
        this.fetch_product();
        this.fetch_uom();
        this.fetch_tax();
    }

    // method to get selected medicine name
    getSelectedMedicineName() {
        if (!this.lineState.product || !this.state.medicines || this.state.medicines.length === 0) {
            return "Select Medicine";
        }
        const medicine = this.state.medicines.find(med => med.id === this.lineState.product);
        return medicine ? medicine.name : "Select Medicine";
    }

    //  Fetch product details
    async fetch_product() {
        try {
            const domain = [['medicine_ok', '=', true]];
            const result = await this.orm.call('product.template', 'search_read', [domain]);
            this.product_lst = result;
            this.state.medicines = result;
            this.create_order();
        } catch (error) {
            console.error('Error fetching products:', error);
        }
    }

    //   Fetch UOM of selected product
    async fetch_uom (){
        var uom_lst= [];
        var result= await this.orm.call( 'uom.uom','search_read',)
        this.uom_lst=result
    }

    //  Fetch tax amount of product.
    async fetch_tax(){
        var tax_lst= [];
        var result= await this.orm.call( 'account.tax','search_read',)
        this.tax_lst=result
    }

    //  Method for creating sale order
    async create_order() {
        await this.orm.call('hospital.pharmacy','company_currency',
        ).then(function (result){
            const symbolElements = document.querySelectorAll('[id^="symbol"]');
            symbolElements.forEach(el => {
                el.textContent = result || '';
            });
            const classSymbolElements = document.querySelectorAll('.symbol');
            classSymbolElements.forEach(el => {
                el.textContent = result || '';
            });
        })
        this.state.medicines = await this.product_lst;
        this.state.units = await this.uom_lst;
    }
    calculateSubtotal(qty, price) {
        return qty *price
    }

    //  Method on changing the product in the sale order
    async _onChange_prod_price(med_id) {
        if (!med_id) return;
        this.lineState.product = med_id;
        const medicine = this.state.medicines.find(med => med.id === med_id);
        if (medicine) {
            this.lineState.price = medicine.list_price || 0;
            this.lineState.sub_total = this.calculateSubtotal(this.lineState.qty, this.lineState.price);
            this.props.updateOrderLine(this.lineState, this.props.id);
        }
    }

    //  Calculation of sub total based on product quantity
    async _onChange_prod_qty () {
        var self = this;
        this.lineState.sub_total = this.calculateSubtotal(this.lineState.qty, this.lineState.price)
        this.props.updateOrderLine(this.lineState, this.props.id)
    }

    //  To remove the added line
    async remove_line () {
        this.props.removeLine(this.props.id)
    }
}
PharmacyOrderLines.template = "PharmacyOrderLines"
PharmacyOrderLines.components = { Dropdown, DropdownItem }
