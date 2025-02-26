import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useDebounced } from "@web/core/utils/timing";

const MAX_FONT_SIZE = 144;

export class FontSelector extends Component {
    static template = "html_editor.FontSelector";
    static props = {
        getItems: Function,
        getDisplay: Function,
        onSelected: Function,
        onFontSizeInput: { type: Function, optional: true },
        variant: { type: String, optional: true },
        ...toolbarButtonProps,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.items = this.props.getItems();
        this.state = useState(this.props.getDisplay());
        this.dropdown = useDropdownState();
        this.iframeContentRef = useRef("iframeContent");
        this.debouncedCustomFontSizeInput = useDebounced(this.onCustomFontSizeInput, 200);

        onMounted(() => {
            const iframeEl = this.iframeContentRef?.el;
            if (iframeEl) {
                const iframeDoc = iframeEl.contentWindow.document;
                this.fontSizeInput = iframeDoc.createElement("input");
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
                });
                this.fontSizeInput.type = "text";
                this.fontSizeInput.name = "font-size-input";
                this.fontSizeInput.autocomplete = "off";
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
                    this.dropdown.isOpen ? this.fontSizeInput.select() : this.fontSizeInput.blur();
                }
            },
            () => [this.dropdown.isOpen]
        );
    }

    get isFontSizeSelector() {
        return this.props.variant === "font-size";
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
    }

    onKeyDownFontSizeInput(ev) {
        if (["Enter", "Tab"].includes(ev.key) && this.dropdown.isOpen) {
            this.dropdown.close();
        } else if (["ArrowUp", "ArrowDown"].includes(ev.key)) {
            const fontSelectorMenu = document.querySelector(".o_font_selector_menu");
            if (!fontSelectorMenu) {
                return;
            }
            ev.target.blur();
            const fontMenuItemToFocus =
                ev.key === "ArrowUp"
                    ? fontSelectorMenu.lastElementChild
                    : fontSelectorMenu.firstElementChild;
            if (fontMenuItemToFocus) {
                fontMenuItemToFocus.focus();
            }
        }
    }

    onSelected(item) {
        this.props.onSelected(item);
    }
}
