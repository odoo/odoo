import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useDebounced } from "@web/core/utils/timing";

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
                this.fontSizeInput.value = this.state.displayName;
                this.fontSizeInput.autocomplete = "off";
                iframeDoc.body.appendChild(this.fontSizeInput);
                this.fontSizeInput.addEventListener("click", (ev) => {
                    ev.target.select();
                    this.dropdown.open();
                });
                this.fontSizeInput.addEventListener("input", this.debouncedCustomFontSizeInput);
            }
        });
        useEffect(
            () => {
                if (this.fontSizeInput) {
                    this.fontSizeInput.value = this.state.displayName;
                }
            },
            () => [this.state.displayName]
        );
    }

    get isFontSizeSelector() {
        return this.props.variant === "font-size";
    }

    onCustomFontSizeInput(ev) {
        const fontSize = parseInt(ev.target.value, 10);
        if (fontSize > 0 && this.state.displayName !== fontSize) {
            this.props.onFontSizeInput(`${fontSize}px`);
        }
    }

    onSelected(item) {
        this.props.onSelected(item);
        this.fontSizeInput?.blur();
    }
}
