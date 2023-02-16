/** @odoo-module **/

import { FormRenderer } from "@web/views/form/form_renderer";

import { useEffect, useRef } from "@odoo/owl";

export class TodoConversionFormRenderer extends FormRenderer {
    //Override of FormRenderer to get the autofocus even if a non-virtual record is loaded
    setup() {
        super.setup();
        const { archInfo } = this.props;
        const { autofocusFieldId } = archInfo;
        if (this.shouldAutoFocus) {
            const rootRef = useRef("compiled_view_root");
            useEffect(
                (isVirtual, rootEl) => {
                    if (!rootEl) {
                        return;
                    }
                    let elementToFocus;
                    const focusableSelectors = [
                        'input[type="text"]',
                        "textarea",
                        "[contenteditable]",
                    ];
                    elementToFocus =
                        (autofocusFieldId && rootEl.querySelector(`#${autofocusFieldId}`)) ||
                        rootEl.querySelector(
                            focusableSelectors
                                .map((sel) => `.o_content .o_field_widget ${sel}`)
                                .join(", ")
                        );
                    
                    if (elementToFocus) {
                        elementToFocus.focus();
                    }
                },
                () => [this.props.record.isVirtual, rootRef.el]
            );
        }
    }
}

