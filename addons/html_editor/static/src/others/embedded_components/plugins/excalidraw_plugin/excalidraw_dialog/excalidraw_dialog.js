import { Dialog } from "@web/core/dialog/dialog";
import { useAutofocus } from "@web/core/utils/hooks";

import { Component, useExternalListener, useState } from "@odoo/owl";
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
        this.state = useState({
            hasError: false,
            isInputEmpty: true,
        });
        this.inputRef = useAutofocus({ refName: "urlInput" });
        useExternalListener(window, "keydown", this.onKeyDown.bind(this));
    }

    onKeyDown(event) {
        if (event.key === "Enter") {
            this.saveURL();
        }
    }

    checkInput() {
        this.state.hasError = false;
        this.state.isInputEmpty = false;
        let potentialURL = this.inputRef.el.value?.trim();
        if (!potentialURL) {
            this.state.isInputEmpty = true;
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
