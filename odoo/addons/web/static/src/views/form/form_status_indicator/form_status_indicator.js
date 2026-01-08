/** @odoo-module **/

import { Component, useEffect, useRef, useState } from "@odoo/owl";
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
        useEffect(
            () => {
                if (!this.props.model.root.isNew && this.indicatorMode === "invalid") {
                    this.saveButton.el.setAttribute("disabled", "1");
                } else {
                    this.saveButton.el.removeAttribute("disabled");
                }
            },
            () => [this.props.model.root.isValid]
        );

        this.saveButton = useRef("save");
    }

    get displayButtons() {
        return this.indicatorMode !== "saved";
    }

    get indicatorMode() {
        if (this.props.model.root.isNew) {
            return this.props.model.root.isValid ? "dirty" : "invalid";
        } else if (!this.props.model.root.isValid) {
            return "invalid";
        } else if (this.props.model.root.dirty || this.state.fieldIsDirty) {
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
};
