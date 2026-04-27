/** @odoo-module */
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { formatFloat } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

export class SendcloudProductSelectionWidget extends Component {
    static template = "delivery_sendcloud.SendcloudProductWidget";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        "*": true,
    };
    setup() {
        const { data } = this.props.record;
        this.isReturn = this.props.name == "return_products";
        this.products = data[this.props.name];
        if (this.isReturn || this.products.length == 0){
            this.products.unshift({name : "None", code : false});
        }
        this.activeCodeKey = this.isReturn ? "return" : "shipping";
        this.state = useState({
            'code': this.activeCode,
        });
    }

    get activeProduct(){
        let product = this.products.find(pr => pr.code == this.state.code);
        // Product may be undefined if the user removed the carrier from his sendcloud account
        if (product === undefined){
            product = this.products[0];
        }
        if (!("local_cache" in product)){
            product['local_cache'] = {};
        }
        return product;
    }

    get functionalities(){
        if(! this.activeProduct.local_cache.functionalities){
            this.activeProduct.local_cache['functionalities'] = {"bool_func" : [], "detail_func" : {}, "customizable" : {}};
            this._cleanFunctionalities();
        }
        return this.activeProduct.local_cache.functionalities;
    }

    get boolFunctionalities(){
        return this.functionalities.bool_func; //array of string
    }

    get detailFunctionalities(){
        return this.functionalities.detail_func; //dict of string
    }

    get maxHeight(){
        return this._maxDimension("height");
    }

    get maxLength(){
        return this._maxDimension("length");
    }

    get maxWidth(){
        return this._maxDimension("width");
    }

    get weightRange(){
        return this.activeProduct.weight_range['min_weight'] + " - " + this.activeProduct.weight_range['max_weight'];
    }

    get activeCode(){
        return this.props.record.data.sendcloud_products_code[this.activeCodeKey];
    }

    set activeCode(value){
        this.props.record.data.sendcloud_products_code[this.activeCodeKey] = value;
    }

    _cleanFunctionalities(){
        const product = this.activeProduct;
        const func_cache = product.local_cache.functionalities;
        const keys = Object.keys(product.available_functionalities).sort();
        for(const key of keys){
            const value = product.available_functionalities[key];
            const name = this._humanizeFunctionality(key)
            if (value.some(v => v === true)){
                func_cache.bool_func.push(name);
            }else{
                for(const v in value){
                    if (value[v] !== false && (value.length > 1 || value[v] !== null)){
                        const humanizedValue = value[v] === null ? 'None' : this._humanizeFunctionality(value[v]);
                         if (name in func_cache.detail_func){
                            func_cache.detail_func[name].push(humanizedValue);
                         }
                         else{
                            func_cache.detail_func[name] = [humanizedValue];

                         }
                    }
                }
                if (name in func_cache.detail_func){
                    func_cache.detail_func[name] = func_cache.detail_func[name].join(", ");
                }
            }
            // When multiple parameters are available for the same functionality,
            //  add the 'technical description' appart for later user-customization
            if (value.length > 1){
                func_cache.customizable[key] = value;
            }
        }
    }

    _humanizeFunctionality(technicalName){
        technicalName = new String(technicalName);
        return technicalName.substring(0, 1).toUpperCase().concat(technicalName.substring(1).replaceAll("_", " ")).toString();
    }

    _maxDimension(name){
        if (name != 'length' && name != 'width' && name != 'height'){
            return 0;
        }
        if (!("max_"+name in this.activeProduct.local_cache)){
            // Ensure normalization in cm
            // [method].properties.max_dimensions.unit is in {millimeter, centimeter, meter}
            var size = this.activeProduct.methods.map((x) => {
                let val = parseInt(x.properties.max_dimensions[name]);
                let factor = 1.0; // centimeter per default
                let unit = x.properties.max_dimensions['unit'];
                if (unit == 'millimeter'){
                    factor = 0.1;
                }else if (unit == 'meter'){
                    factor = 100;
                }
                return formatFloat(val * factor);
            });
            this.activeProduct.local_cache["max_"+name] = Math.max.apply(null, size);
        }
        return this.activeProduct.local_cache["max_"+name];
    }

    _onSelected(code){
        this.state.code = code;
        this.activeCode = code;
    }
}

export const sendcloudProductSelectionWidget = {
    component: SendcloudProductSelectionWidget,
};

registry.category("fields").add("sendcloud_product_selection", sendcloudProductSelectionWidget);

