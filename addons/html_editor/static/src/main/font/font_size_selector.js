import { useLayoutEffect } from "@web/owl2/utils";
import { Component, onMounted, proxy, signal } from "@odoo/owl";
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

    fontSizeSelectorRef = signal(null);
    iframeContentRef = signal(null);

    setup() {
        this.items = this.props.getItems();
        this.state = proxy(this.props.getDisplay());
        this.dropdown = useDropdownState();
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        this.debouncedCustomFontSizeInput = useDebounced(this.onCustomFontSizeInput, 200);
        useToolbarDropdownFocus(this.dropdown, this.fontSizeSelectorRef);

        onMounted(() => {
            const iframeEl = this.iframeContentRef();

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
                    }
                });
                this.fontSizeInput.addEventListener("input", this.debouncedCustomFontSizeInput);
                this.fontSizeInput.addEventListener(
                    "keydown",
                    this.onKeyDownFontSizeInput.bind(this)
                );
                // On mobile, opening the bottom sheet moves the iframe in the DOM,
                // which reloads it and recreates the input. The dropdown-open layout
                // effect may already have run `select()` on the previous input, so
                // re-select the freshly created input to keep it focused for keyboard
                // navigation while the menu is open.
                if (this.dropdown.isOpen) {
                    this.fontSizeInput.select();
                }
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
                        this.iframeContentRef()?.contains(this.props.document.activeElement)
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
