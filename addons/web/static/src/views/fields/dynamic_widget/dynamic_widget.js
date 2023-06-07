/** @odoo-module */

import { CharField, charField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";

import { DynamicModelFieldSelector }  from "./dynamic_model_field_selector";


export class DynamicDomainWithChar extends CharField {
    static components = {
        ...CharField.components,
        DynamicModelFieldSelector
    };

    static props = {
        ...CharField.props,
        resModel : { type: String, optional: true },
    }

    /**
     * Update record
     *
     * @param {string} value
     * @private
     */
    async _onRecordUpdate(value) {
        await this.props.record.update({[this.props.name]: value});
        await this.props.record.save();
        await this.props.record.load();
    }

    //---- Getters ----
    get getSelectorProps() {
        return {
            path: this.props.record.data[this.props.name],
            resModel: this.getResModel(),
            readonly: this.props.readonly,
            record: this.props.record,
            recordProps: this.props,
            update: this._onRecordUpdate.bind(this),
            isDebugMode: !!this.env.debug,
        };
    }

    getResModel(props = this.props) {
        let resModel = props.record.data[props.resModel];
        if (!resModel) { 
            resModel = props.record.resModel;
        }
        return resModel;
    }
}

DynamicDomainWithChar.template = "web.DynamicDomainWithChar";

export const dynamicDomainWithChar = {
    ...charField,
    component: DynamicDomainWithChar,
    extractProps({ options }, dynamicInfo) {
        return {
            resModel: options.model,
        };
    },
};

registry.category("fields").add("dynamic_domain", dynamicDomainWithChar);
