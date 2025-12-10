import { Component, useRef } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BusLogsMenuItem extends Component {
    static components = { DropdownItem };
    static template = "bus.BusLogsMenuItem";
    static props = {};

    setup() {
        this.busLogsService = useService("bus.logs_service");
        this.downloadButton = useRef("downloadButton");
        this.dialog = useService("dialog");
    }

    onClickDownload() {
        this.dialog.add(ConfirmationDialog, {
            body: _t(
                "Bus logs contain confidential information and must only be shared with trusted recipients."
            ),
            title: _t("You're about to download the bus logs"),
            confirm: () => this.env.services.bus_service.downloadLogs(),
            cancel() {},
            confirmLabel: _t("Download"),
            cancelLabel: _t("Discard"),
        });
    }
}

registry
    .category("debug")
    .category("default")
    .add("bus.download_logs", () => ({
        Component: BusLogsMenuItem,
        sequence: 550,
        section: "tools",
        type: "component",
    }));
