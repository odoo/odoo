import { Dialog } from "@web/core/dialog/dialog";
import { useAutofocus } from "@web/core/utils/hooks";

import { Component, useExternalListener, useState, useRef, useEffect, onMounted } from "@odoo/owl";
import { checkURL, excalidrawWebsiteDomainList } from "@html_editor/utils/url";

/**
 * This is the dialog where the link is inputted by the user to populate the
 * behavior.
 */
export class ExcalidrawDialog extends Component {
    static template = "html_editor.ExcalidrawDialog";
    static props = {
        close: Function,
        saveLink: Function,
    };
    static components = { Dialog };

    setup() {
        super.setup();
        this.state = useState({});
        this.inputRef = useAutofocus({ refName: "urlInput" });
        this.insertButtonRef = useRef("insertButton");
        useExternalListener(window, "keydown", this.onKeyDown.bind(this));
        useEffect(
            (inputEl) => {
                if (inputEl) {
                    const onInput = () => {
                        const value = !this.inputRef.el.value || this.inputRef.el.value.trim() === "";
                        this.insertButtonRef.el.toggleAttribute("disabled", value);
                    };

                    inputEl.addEventListener("input", onInput);
                    return () => {
                        inputEl.removeEventListener("input", onInput);
                    }
                }
            },
            () => [this.inputRef.el]
        );
        onMounted(() => {
            if (this.insertButtonRef.el) {
                this.insertButtonRef.el.setAttribute("disabled", true);
            }
        });
    }

    onKeyDown(event) {
        this.state.hasError = false;
        if (event.key === "Enter") {
            this.saveURL();
        }
    }

    checkInput() {
        let potentialURL = this.inputRef.el.value;
        if (!potentialURL) {
            return false;
        }
        potentialURL = checkURL(potentialURL, excalidrawWebsiteDomainList);
        if (!potentialURL) {
            this.state.hasError = true;
        } else {
            return potentialURL;
        }
    }

    saveURL() {
        const potentialURL = this.checkInput();
        if (potentialURL) {
            this.props.saveLink(potentialURL);
            this.props.close();
        }
    }
}
