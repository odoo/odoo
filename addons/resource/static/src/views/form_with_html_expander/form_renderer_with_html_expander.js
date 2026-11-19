import { t, untrack, useProps } from "@odoo/owl";
import { SIZES } from "@web/core/ui/ui_utils";
import { useService } from "@web/core/utils/hooks";
import { useLayoutEffect } from "@web/owl2/utils";
import { FormRenderer, formRendererProps } from "@web/views/form/form_renderer";

export class FormRendererWithHtmlExpander extends FormRenderer {
    props = useProps({
        ...formRendererProps,
        reloadHtmlFieldHeight: t.boolean().optional(true),
        notifyHtmlExpander: t.function().optional(() => () => {}),
    });

    setup() {
        super.setup();
        if (!this.uiService) {
            // Should be defined in FormRenderer
            this.uiService = useService("ui");
        }
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
            () => [
                untrack(this.rootRef),
                this.uiService.size,
                this.props.reloadHtmlFieldHeight,
            ]
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
