import { useService } from "@web/core/utils/hooks";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useRef, useEffect } from "@odoo/owl";

export class FormRendererWithHtmlExpander extends FormRenderer {
    static props = {
        ...FormRenderer.props,
        reloadHtmlFieldHeight: { type: Boolean, optional: true },
        notifyHtmlExpander: { type: Function, optional: true },
    };
    static defaultProps = {
        ...FormRenderer.defaultProps,
        reloadHtmlFieldHeight: true,
        notifyHtmlExpander: () => {},
    };

    setup() {
        super.setup();
        if (!this.uiService) {
            // Should be defined in FormRenderer
            this.uiService = useService("ui");
        }
        const ref = useRef("compiled_view_root");
        useEffect(
            (el, size) => {
                if (el && this._canExpandHTMLField(size)) {
                    const descriptionField = el.querySelector(this.htmlFieldQuerySelector);
                    if (descriptionField) {
                        const containerEL = descriptionField.closest(
                            this.getHTMLFieldContainerQuerySelector
                        );
                        const editor = descriptionField.querySelector(".note-editable");
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
                this.props.notifyHtmlExpander();
            },
            () => [ref.el, this.uiService.size, this.props.reloadHtmlFieldHeight]
        );
    }

    get htmlFieldQuerySelector() {
        return ".o_field_html[name=description]";
    }

    get getHTMLFieldContainerQuerySelector() {
        return ".o_form_sheet";
    }

    _canExpandHTMLField(size) {
        return size === 6;
    }
}
