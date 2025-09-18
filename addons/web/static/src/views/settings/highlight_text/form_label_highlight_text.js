// @ts-check

/** @module @web/views/settings/highlight_text/form_label_highlight_text - FormLabel variant with search-term highlighting and enterprise upgrade badge */

import { FormLabel } from "@web/views/form/form_label";
import { upgradeBooleanField } from "@web/views/settings/fields/upgrade_boolean_field";

import { HighlightText } from "./highlight_text";

/** FormLabel variant with search-term highlighting and enterprise upgrade badge. */
export class FormLabelHighlightText extends FormLabel {
    static template = "web.FormLabelHighlightText";
    static components = { HighlightText };
    /** Set up highlighting and detect enterprise upgrade badge requirement. */
    setup() {
        super.setup();
        /** @type {boolean} */
        const isEnterprise = odoo.info && odoo.info.isEnterprise;
        if (this.props.fieldInfo?.field === upgradeBooleanField && !isEnterprise) {
            this.upgradeEnterprise = true;
        }
    }
}
