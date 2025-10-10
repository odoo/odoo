import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useDebounced } from "@web/core/utils/timing";
import { cookie } from "@web/core/browser/cookie";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { useDropdownAutoVisibility } from "@html_editor/dropdown_autovisibility_hook";
import { useChildRef } from "@web/core/utils/hooks";

const MAX_FONT_SIZE = 144;

export class FontSizeSelector extends Component {
    static template = "html_editor.FontSizeSelector";
    static props = {
        getItems: Function,
        getDisplay: Function,
        onFontSizeInput: Function,
        onSelected: Function,
        onBlur: { type: Function, optional: true },
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
        ...toolbarButtonProps,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.items = this.props.getItems();
        this.state = useState(this.props.getDisplay());
        this.dropdown = useDropdownState();
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        this.iframeContentRef = useRef("iframeContent");
        this.debouncedCustomFontSizeInput = useDebounced(this.onCustomFontSizeInput, 200);

        onMounted(() => {
            const iframeEl = this.iframeContentRef.el;

            const initFontSizeInput = () => {
                const iframeDoc = iframeEl.contentWindow.document;

                // Skip if already initialized.
                if (this.fontSizeInput || !iframeDoc.body) {
                    return;
                }

                this.fontSizeInput = iframeDoc.createElement("input");
                const isDarkMode = cookie.get("color_scheme") === "dark";
                const htmlStyle = getHtmlStyle(document);
                const backgroundColor = getCSSVariableValue(
                    isDarkMode ? "gray-200" : "white",
                    htmlStyle
                );
                const color = getCSSVariableValue("black", htmlStyle);
                const fontFamily = getCSSVariableValue("o-system-fonts", htmlStyle);
                Object.assign(iframeDoc.body.style, {
                    padding: "0",
                    margin: "0",
                });
                Object.assign(this.fontSizeInput.style, {
                    width: "100%",
                    height: "100%",
                    border: "none",
                    outline: "none",
                    textAlign: "center",
                    backgroundColor: backgroundColor,
                    color: color,
                    fontFamily: fontFamily,
                });
                this.fontSizeInput.type = "text";
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
            };
            if (iframeEl.contentDocument.readyState === "complete") {
                initFontSizeInput();
            } else {
                // in firefox, iframe is not immediately available. we need to wait
                // for it to be ready before mounting.
                iframeEl.addEventListener(
                    "load",
                    () => {
                        initFontSizeInput();
                    },
                    { once: true }
                );
            }
        });
        useEffect(
            () => {
                if (this.fontSizeInput) {
                    // Update `fontSizeInputValue` whenever the font size changes.
                    this.fontSizeInput.value = this.state.displayName;
                }
            },
            () => [this.state.displayName]
        );
        useEffect(
            () => {
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
            fontSize = Math.min(fontSize, MAX_FONT_SIZE);
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
        if (["Enter", "Tab"].includes(ev.key) && this.dropdown.isOpen) {
            this.dropdown.close();
        } else if (["ArrowUp", "ArrowDown"].includes(ev.key)) {
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
