/** @odoo-module */
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef, useService } from "@web/core/utils/hooks";

import { Component, useExternalListener } from "@odoo/owl";

export class PromoteStudioDialog extends Component {
    static template = "web_enterprise.PromoteStudioDialog";
    static components = { Dialog };
    static props = {
        title: String,
        close: Function,
    };

    setup() {
        this.ormService = useService("orm");
        this.uiService = useService("ui");

        this.modalRef = useChildRef();

        useExternalListener(window, "mousedown", this.onWindowMouseDown);
    }

    async onClickInstallStudio() {
        this.disableClick = true;
        this.uiService.block();
        const modules = await this.ormService.searchRead(
            "ir.module.module",
            [["name", "=", "web_studio"]],
            ["id"]
        );
        await this.ormService.call("ir.module.module", "button_immediate_install", [
            [modules[0].id],
        ]);
        // on rpc call return, the framework unblocks the page
        // make sure to keep the page blocked until the reload ends.
        this.uiService.unblock();
        browser.localStorage.setItem("openStudioOnReload", "main");
        browser.location.reload();
    }

    /**
     * Close the dialog on outside click.
     */
    onWindowMouseDown(ev) {
        const dialogContent = this.modalRef.el.querySelector(".modal-content");
        if (!this.disableClick && !dialogContent.contains(ev.target)) {
            this.props.close();
        }
    }
}

export class PromoteStudioAutomationDialog extends PromoteStudioDialog {
    static template = "web_enterprise.PromoteStudioAutomationDialog";
}
