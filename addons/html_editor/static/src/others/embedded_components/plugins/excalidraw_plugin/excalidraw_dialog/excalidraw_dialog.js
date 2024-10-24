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
        this.state = useState({ isInsertionDisabled: true });
        this.inputRef = useAutofocus({ refName: "urlInput" });
        useExternalListener(window, "keydown", this.onKeyDown.bind(this));
    }

    onKeyDown(event) {
        this.state.hasError = false;
        if (event.key === "Enter") {
            this.saveURL();
        }
    }

    checkInput() {
        this.state.hasError = false;
        let potentialURL = this.inputRef.el.value?.trim();
        if (!potentialURL) {
            this.state.isInsertionDisabled = true;
            return false;
        }
        this.state.isInsertionDisabled = false;
        potentialURL = checkURL(potentialURL, excalidrawWebsiteDomainList);
        if (!potentialURL) {
            this.state.hasError = true;
            this.state.isInsertionDisabled = true;
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
