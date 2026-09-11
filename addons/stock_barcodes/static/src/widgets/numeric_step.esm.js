/** @odoo-module */
/* Copyright 2022 Tecnativa - Alexandre D. Díaz
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import {NumericStep} from "@web_widget_numeric_step/numeric_step.esm";
import {isAllowedBarcodeModel} from "../utils/barcodes_models_utils.esm";
import {patch} from "@web/core/utils/patch";

patch(NumericStep.prototype, "Adds barcode event handling and focus", {
    _onFocus() {
        if (isAllowedBarcodeModel(this.props.record.resModel)) {
            // Auto select all content when user enters into fields with this
            // widget.
            this.inputRef.el.select();
        }
    },

    _onKeyDown(ev) {
        if (isAllowedBarcodeModel(this.props.record.resModel) && ev.keyCode === 13) {
            const action_confirm = document.querySelector(
                "button[name='action_confirm']"
            );

            if (action_confirm) {
                action_confirm.click();
                return;
            }

            const action_confirm_force = document.querySelector(
                "button[name='action_force_done']"
            );

            if (action_confirm_force) {
                action_confirm_force.click();
                return;
            }
        }
        this._super(...arguments);
    },
});
