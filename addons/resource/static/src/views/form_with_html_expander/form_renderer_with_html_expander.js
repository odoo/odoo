import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";
import { FormRenderer } from "@web/views/form/form_renderer";
<<<<<<< 5c6f3526e192fed5af597e447224a1c70e12328f
||||||| 639e8f5f072bb7525659e41fe19930ee5a698e7b
import { useRef, useEffect } from "@odoo/owl";
=======
import { useRef, useEffect } from "@odoo/owl";
import { SIZES } from "@web/core/ui/ui_service";
>>>>>>> cebf0ab40e9ceeca555846d224de2cf853207a0c

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
        useLayoutEffect(
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
                        if (editor) {
                            descriptionField.classList.add("o_resource_html_expander");
                            descriptionField.style.setProperty(
                                "--HtmlExpander__editable-min-height",
                                `${minHeight}px`
                            );
                        } else {
                            elementToResize.style.minHeight = `${minHeight}px`;
                        }
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
        return size === SIZES.XXL;
    }
}
