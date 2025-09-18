// @ts-check

/** @module @web/views/form/form_status_indicator/form_status_indicator - Save/discard indicator shown when the form record is dirty or invalid */

import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
/** Save/discard indicator shown in the form view when the record is dirty or invalid. */
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
            (ev) => (this.state.fieldIsDirty = ev.detail),
        );
        useEffect(
            () => {
                if (!this.props.model.root.isNew && this.indicatorMode === "invalid") {
                    this.saveButton.el.setAttribute("disabled", "1");
                } else {
                    this.saveButton.el.removeAttribute("disabled");
                }
            },
            () => [this.props.model.root.isValid, this.state.fieldIsDirty],
        );

        this.saveButton = useRef("save");
    }

    /** @returns {boolean} whether to show save/discard buttons */
    get displayButtons() {
        return this.indicatorMode !== "saved";
    }

    /** @returns {"dirty" | "invalid" | "saved"} current state of the form record */
    get indicatorMode() {
        const { isNew, isValid } = this.props.model.root;
        const isDirty = this.props.model.root.dirty || this.state.fieldIsDirty;
        if (isNew || isDirty) {
            return isValid ? "dirty" : "invalid";
        }
        return "saved";
    }

    /** @returns {Promise<void>} */
    async discard() {
        await this.props.discard();
    }
    /** @returns {Promise<void>} */
    async save() {
        await this.props.save();
    }
}
