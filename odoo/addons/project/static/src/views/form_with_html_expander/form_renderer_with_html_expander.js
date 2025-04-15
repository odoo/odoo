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
                        const containerEL = descriptionField.closest(
                            this.getHTMLFieldContainerQuerySelector
                        );
                        const editor = descriptionField.querySelector('.note-editable');
                        const elementToResize = editor || descriptionField;
                        const { top, bottom } = elementToResize.getBoundingClientRect();
                        const { bottom: containerBottom } = containerEL.getBoundingClientRect();
                        const { paddingTop, paddingBottom } = window.getComputedStyle(containerEL);
                        const nonEditableHeight =
                            containerBottom -
                            bottom +
                            parseInt(paddingTop) +
                            parseInt(paddingBottom);
                        const minHeight =
                            document.documentElement.clientHeight - top - nonEditableHeight;
                        elementToResize.style.minHeight = `${minHeight}px`;
                    }
                }
            },
            () => [ref.el, this.ui.size, this.props.record.resId]
        );
    }

    get htmlFieldQuerySelector() {
        return '.oe_form_field.oe_form_field_html';
    }

    get getHTMLFieldContainerQuerySelector() {
        return ".o_form_sheet";
    }
}
