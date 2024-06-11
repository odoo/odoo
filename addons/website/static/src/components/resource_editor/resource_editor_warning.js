/** @odoo-module **/

import { EditHeadBodyDialog } from "../edit_head_body_dialog/edit_head_body_dialog";
import { Component, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

/**
 * Represents the warning overlay that appears when the user opens the ResourceEditor
 * It provides options to hide the warning, inject code, and not show the warning again.
 */
export class ResourceEditorWarningOverlay extends Component {
    static template = "website.ResourceEditorWarningOverlay";

    /**
     * Initializes the component by setting up the necessary services and state.
     */
    setup() {
        this.website = useService("website");
        this.dialog = useService("dialog");

        const localStorageValue = browser.localStorage.getItem("website.ace.doNotShowWarning");
        this.state = useState({
            visible: !localStorageValue || localStorageValue === "false",
        });
    }

    /**
     * Closes the Ace editor and updates the website context to hide it.
     */
    onCloseEditor() {
        this.website.context.showResourceEditor = false;
    }

    /**
     * Hides the warning overlay.
     */
    onHideWarning() {
        this.state.visible = false;
    }

    /**
     * Sets a flag in the local storage to prevent the warning overlay from
     * showing again and hides the overlay.
     */
    onStopAsking() {
        browser.localStorage.setItem("website.ace.doNotShowWarning", "true");
        this.onHideWarning();
    }

    /**
     * Opens a dialog to edit the head and body of the website and closes the
     * Ace editor.
     */
    onInjectCode() {
        this.dialog.add(EditHeadBodyDialog);
        this.onCloseEditor();
    }
}
