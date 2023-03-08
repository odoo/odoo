/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export class FormStatusIndicator extends Component {
    setup() {
        this.state = useState({
            fieldIsDirty: false,
        });
        useBus(
            this.props.model.bus,
            "FIELD_IS_DIRTY",
            (ev) => (this.state.fieldIsDirty = ev.detail)
        );
    }

    get displayButtons() {
        return this.indicatorMode !== "saved";
    }

    get indicatorMode() {
        if (this.props.model.root.isNew) {
            return this.props.model.root.isValid ? "dirty" : "invalid";
        } else if (!this.props.model.root.isValid) {
            return "invalid";
        } else if (this.props.model.root.isDirty || this.state.fieldIsDirty) {
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
