import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export class FormStatusIndicator extends Component {
    static template = "web.FormStatusIndicator";
    static props = {
        model: Object,
        save: Function,
        discard: Function,
    };

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
            () => [this.props.model.root.isValid, this.state.fieldIsDirty]
        );

        this.saveButton = useRef("save");
    }

    get displayButtons() {
        return this.indicatorMode !== "saved";
    }

    get indicatorMode() {
        const { isNew, isValid } = this.props.model.root;
        const isDirty = this.props.model.root.dirty || this.state.fieldIsDirty;
        if (isNew || isDirty) {
            return isValid ? "dirty" : "invalid";
        }
        return "saved";
    }

    async discard() {
        await this.props.discard();
    }
    async save() {
        await this.props.save();
    }
}
