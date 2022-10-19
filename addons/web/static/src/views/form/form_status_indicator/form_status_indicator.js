/** @odoo-module **/

import { Component } from "@odoo/owl";

export class FormStatusIndicator extends Component {
    get displayButtons() {
        return this.indicatorMode !== "saved";
    }

    get indicatorMode() {
        if (this.props.model.root.isVirtual) {
            return this.props.model.root.isValid ? "dirty" : "invalid";
        } else if (!this.props.model.root.isValid) {
            return "invalid";
        } else if (this.props.model.root.isDirty) {
            return "dirty";
        } else {
            return "saved";
        }
    }

    async discard() {
        await this.props.discard();
    }
    async save() {
        await this.props.save();
    }
}
FormStatusIndicator.template = "web.FormStatusIndicator";
FormStatusIndicator.props = {
    model: Object,
    save: Function,
    discard: Function,
    isDisabled: Boolean,
};
