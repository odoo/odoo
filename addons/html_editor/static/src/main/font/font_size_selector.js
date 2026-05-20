import { useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { Component, onMounted } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useDebounced } from "@web/core/utils/timing";
import { cookie } from "@web/core/browser/cookie";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useChildRef } from "@web/core/utils/hooks";

export const MAX_FONT_SIZE = 144;

export class FontSizeSelector extends Component {
    static template = "html_editor.FontSizeSelector";
    static props = {
        getItems: Function,
        getDisplay: Function,
        onFontSizeInput: Function,
        onSelected: Function,
        onBlur: { type: Function, optional: true },
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
        maxFontSize: { type: Number, optional: true },
        ...toolbarButtonProps,
    };
    static defaultProps = {
        maxFontSize: MAX_FONT_SIZE,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.items = this.props.getItems();
        this.state = useState(this.props.getDisplay());
        this.fontSizeSelector = useRef("fontSizeSelector");
        this.dropdown = useDropdownState();
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        this.iframeContentRef = useRef("iframeContent");
        this.debouncedCustomFontSizeInput = useDebounced(this.onCustomFontSizeInput, 200);
        useToolbarDropdownFocus(this.dropdown, this.fontSizeSelector);

        onMounted(() => {
            const iframeEl = this.iframeContentRef.el;

            const initFontSizeInput = () => {
                const iframeDoc = iframeEl.contentWindow.document;

                // Skip if already/still initialized.
                if (this.fontSizeInput?.closest("body") === iframeDoc.body || !iframeDoc.body) {
                    return;
                }

                this.fontSizeInput = iframeDoc.createElement("input");
                this.fontSizeInput.addEventListener("blur", () => {
                    this.props.onBlur?.();
                });
                const isDarkMode = cookie.get("color_scheme") === "dark";
                const htmlStyle = getHtmlStyle(document);
                const backgroundColor = getCSSVariableValue(
                    isDarkMode ? "gray-200" : "white",
                    htmlStyle
                );
                const color = getCSSVariableValue("black", htmlStyle);
                const fontFamily = getCSSVariableValue("o-system-fonts", htmlStyle);

                const style = iframeDoc.createElement("style");
                style.textContent = `
                    body {
                        padding: 0;
                        margin: 0;
                    }
                    input::-webkit-outer-spin-button,
                    input::-webkit-inner-spin-button {
                        -webkit-appearance: none;
                        margin: 0;
                    }
                    input[type=number] {
                        -moz-appearance: textfield;
                        width: 100%;
                        height: 100%;
                        border: none;
                        outline: none;
                        text-align: center;
                        background-color: ${backgroundColor};
                        color: ${color};
                        font-family: ${fontFamily};
                    }
                `;
                iframeDoc.head.appendChild(style);
                this.fontSizeInput.type = "number";
                this.fontSizeInput.min = 0;
                this.fontSizeInput.name = "font-size-input";
                this.fontSizeInput.autocomplete = "off";
                this.fontSizeInput.value = this.state.displayName;
                iframeDoc.body.appendChild(this.fontSizeInput);
                this.fontSizeInput.addEventListener("click", () => {
                    if (!this.dropdown.isOpen) {
                        this.dropdown.open();
                        requestAnimationFrame(() => {
                            if (this.menuRef.el?.closest(".o_bottom_sheet")) {
                                this.props.onBlur?.();
                            }
                        });
                    }
                });
                this.fontSizeInput.addEventListener("input", this.debouncedCustomFontSizeInput);
                this.fontSizeInput.addEventListener(
                    "keydown",
                    this.onKeyDownFontSizeInput.bind(this)
                );
            };
            if (iframeEl.contentDocument.readyState === "complete") {
                initFontSizeInput();
            }
            // If iframe is moved around in DOM, it restarts from scratch and needs to be repopulated.
            iframeEl.addEventListener("load", initFontSizeInput);
        });
        useLayoutEffect(
            () => {
                if (this.fontSizeInput) {
                    // Update `fontSizeInputValue` whenever the font size changes.
                    this.fontSizeInput.value = this.state.displayName;
                }
            },
            () => [this.state.displayName]
        );
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
