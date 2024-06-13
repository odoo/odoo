/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { FormRenderer } from '@web/views/form/form_renderer';
import { useRef, useEffect } from "@odoo/owl";

export class FormRendererWithHtmlExpander extends FormRenderer {
    setup() {
        super.setup();
        this.ui = useService('ui');
        const ref = useRef('compiled_view_root');
        useEffect(
            (el, size) => {
                if (el && size === 6) {
                    const descriptionField = el.querySelector(this.htmlFieldQuerySelector);
                    if (descriptionField) {
                        const editor = descriptionField.querySelector('.note-editable');
                        const elementToResize = editor || descriptionField;
                        const { bottom, height } = elementToResize.getBoundingClientRect();
                        const minHeight = document.documentElement.clientHeight - bottom - height;
                        elementToResize.style.minHeight = `${minHeight}px`;
                    }
                }
            },
            () => [ref.el, this.ui.size, this.props.record.mode],
        );
    }

    get htmlFieldQuerySelector() {
        return '.oe_form_field.oe_form_field_html';
    }
}
