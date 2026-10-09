/** @odoo-module */
/* Copyright 2018-2019 Sergio Teruel <sergio.teruel@tecnativa.com>.
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import {BooleanToggleField} from "@web/views/fields/boolean_toggle/boolean_toggle_field";
import {registry} from "@web/core/registry";

class BarcodeBooleanToggleField extends BooleanToggleField {
    /*
    This is needed because, whenever we click the checkbox to enter data
    manually, the checkbox will be focused causing that when we scan the
    barcode afterwards, it will not perform the python on_barcode_scanned
    function.
    */
    onChange(newValue) {
        super.onChange(newValue);
        // We can't blur an element on its onchange event
        // we need to wait for the event to finish (thus
        // requestIdleCallback)
        requestIdleCallback(() => {
            document.activeElement.blur();
        });
    }
}

registry.category("fields").add("barcode_boolean_toggle", BarcodeBooleanToggleField);
