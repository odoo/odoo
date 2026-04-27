/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

export class SendcloudFunctionalitiesField extends Component {
    static template = "delivery_sendcloud.functionalities";
    static props = {
        "*": true,
    };
    setup() {
        const { data } = this.props.record;
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.resId = data.id;
        this.sendcloudProductId = data.sendcloud_shipping_id[0];
        this.filterableFunc = useState({});
        this.currentFilters = {...data.sendcloud_product_functionalities};
        onWillStart(this._fetchFunctionalities);
        onWillUpdateProps((nextProps) => this._onWillUpdateProps(nextProps));
    }

    async _fetchFunctionalities(){
        const res = await this.orm.read(
            "sendcloud.shipping.product",
            [this.sendcloudProductId],
            ['functionalities']
        );
        const productFunctionalities = res[0].functionalities.customizable;
        this.filterableFunc = {...productFunctionalities};
        for (const func in this.filterableFunc){
            for (let i = 0; i < this.filterableFunc[func].length; i++){
                if (this.filterableFunc[func][i] === null){
                    this.filterableFunc[func][i] = "None";
                }
            }
        }
    }

    async _onWillUpdateProps(nextProps){
        const { data } = nextProps.record;
        if (typeof data.sendcloud_shipping_id === "undefined"){
            return false;
        }
        const newProductId = data.sendcloud_shipping_id[0];
        if (newProductId === this.sendcloudProductId ){
            return false;
        }
        this.sendcloudProductId = newProductId;
        await this._fetchFunctionalities();
        this.currentFilters = data.sendcloud_product_functionalities;
    }

    _humanizeFunctionality(technicalName){
        technicalName = new String(technicalName);
        return technicalName.substring(0, 1).toUpperCase().concat(technicalName.substring(1).replaceAll("_", " ")).toString();
    }

    _isChecked(func, option){
        return this.currentFilters[func]?.includes(option);
    }

    _onChecked(func, option){
        if (!this.currentFilters){
            this.currentFilters = {};
        }
        if (func in this.currentFilters){
            const i = this.currentFilters[func].indexOf(option);
            if (i >= 0){
                this.currentFilters[func].splice(i,1);
                if (this.currentFilters[func].length == 0){
                    delete this.currentFilters[func];
                }
            }
            else{
                this.currentFilters[func].push(option);
            }
        }else{
            this.currentFilters[func] = [option];
        }
        this.props.record.update({['sendcloud_product_functionalities']: this.currentFilters});
    }

}

export const sendcloudFunctionalitiesField = {
    component: SendcloudFunctionalitiesField,
};

registry.category("fields").add("sendcloud_functionalities", sendcloudFunctionalitiesField);
