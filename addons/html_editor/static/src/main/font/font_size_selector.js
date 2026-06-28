import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { Component, props, proxy, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useDebounced } from "@web/core/utils/timing";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useChildRef } from "@web/core/utils/hooks";
import { IframeInput } from "@html_editor/components/iframe_input/iframe_input";

export const MAX_FONT_SIZE = 144;

export class FontSizeSelector extends Component {
    static template = "html_editor.FontSizeSelector";
    props = props({
        getItems: t.function(),
        getDisplay: t.function(),
        onFontSizeInput: t.function(),
        onSelected: t.function(),
        onBlur: t.function().optional(),
        document: t.customValidator(t.any(), (p) => p.nodeType === Node.DOCUMENT_NODE),
        maxFontSize: t.number().optional(MAX_FONT_SIZE),
        // from toolbarButtonProps
        title: t.or([t.string(), t.function()]),
        getSelection: t.function(),
        isDisabled: t.boolean(),
    });
    static components = { Dropdown, DropdownItem, IframeInput };

    setup() {
        this.items = this.props.getItems();
        this.state = proxy(this.props.getDisplay());
        this.fontSizeSelector = useRef("fontSizeSelector");
        this.dropdown = useDropdownState();
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        this.iframeContentRef = useChildRef();
        this.fontSizeInputRef = useChildRef();
        this.debouncedCustomFontSizeInput = useDebounced(this.onCustomFontSizeInput, 200);
        useToolbarDropdownFocus(this.dropdown, this.fontSizeSelector);
        const htmlStyle = getHtmlStyle(document);
        this.fontFamily = getCSSVariableValue("o-system-fonts", htmlStyle);
        useLayoutEffect(
            () => {
                // blur on close
                if (this.fontSizeInput) {
                    // Focus input on dropdown open, blur on close.
                    if (this.dropdown.isOpen) {
                        this.fontSizeInput.select();
                    } else if (
                        this.iframeContentRef.el?.contains(this.props.document.activeElement)
                    ) {
                        this.fontSizeInput.blur();
                        this.props.onBlur?.();
                    }
                }
            },
            () => [this.dropdown.isOpen]
        );
    }

    get fontSizeInput() {
        return this.fontSizeInputRef.el;
    }

    onClickFontSizeInput() {
        if (!this.dropdown.isOpen) {
            this.dropdown.open();
            requestAnimationFrame(() => {
                if (this.menuRef.el?.closest(".o_bottom_sheet")) {
                    this.props.onBlur?.();
                }
            });
        }
    }

    onCustomFontSizeInput(ev) {
        let fontSize = parseInt(ev.target.value, 10);
        if (fontSize > 0) {
            fontSize = Math.min(fontSize, this.props.maxFontSize);
            if (this.state.displayName !== fontSize) {
                this.props.onFontSizeInput(`${fontSize}px`);
            } else {
                // Reset input if state.displayName does not change.
                this.fontSizeInput.value = this.state.displayName;
            }
        }
        this.fontSizeInput.focus();
    }

    onKeyDownFontSizeInput(ev) {
        if (["Enter", "Escape"].includes(ev.key) && this.dropdown.isOpen) {
            this.dropdown.close();
        } else if (["ArrowUp", "ArrowDown", "Tab"].includes(ev.key)) {
            ev.preventDefault();
            const fontSizeSelectorMenu = document.querySelector(".o_font_size_selector_menu div");
            if (!fontSizeSelectorMenu) {
                return;
            }
            ev.target.blur();
            const fontSizeMenuItemToFocus =
                ev.key === "ArrowUp"
                    ? fontSizeSelectorMenu.lastElementChild
                    : fontSizeSelectorMenu.firstElementChild;
            if (fontSizeMenuItemToFocus) {
                fontSizeMenuItemToFocus.focus();
            }
        }
    }

    onSelected(item) {
        this.props.onSelected(item);
    }
}
