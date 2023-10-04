/** @odoo-module */

import { CharField, charField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { useEffect, useRef } from "@odoo/owl";

class DescriptionPageField extends CharField {
    setup() {
        super.setup();
        const inputRef = useRef("input");
        useEffect(
            (input) => {
                if (input) {
                    input.classList.add("col");
                }
            },
            () => [inputRef.el]
        );
    }
    onExternalBtnClick() {
        this.env.openRecord(this.props.record);
    }
}
DescriptionPageField.template = "survey.DescriptionPageField";

registry.category("fields").add("survey_description_page", {
    ...charField,
    component: DescriptionPageField,
});
