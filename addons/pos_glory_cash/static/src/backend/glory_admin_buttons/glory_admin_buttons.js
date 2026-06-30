import { Component, useEffect, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { downloadFile } from "@web/core/network/download";
import { Logger } from "@bus/workers/bus_worker_utils";
import { GloryService } from "@pos_glory_cash/glory_service";
import { GLORY_STATUS_STRING } from "@pos_glory_cash/utils/constants";

export class GloryAdminButtons extends Component {
    static template = `pos_glory_cash.GloryAdminButtons`;
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.logger = new Logger("pos_glory_cash");
        this.gloryService = new GloryService((newStatus) => (this.state.status = newStatus));
        this.state = useState({ status: "DISCONNECTED", resetInProgress: false });

        useEffect(
            () => {
                const { glory_websocket_address, glory_username, glory_password } =
                    this.props.record.data;
                if (glory_websocket_address) {
                    this.gloryService.connect(
                        glory_websocket_address,
                        glory_username,
                        glory_password
                    );
                }
            },
            () => [this.props.record.data]
        );
    }

    get status() {
        return GLORY_STATUS_STRING[this.state.status] ?? this.state.status;
    }

    async downloadLogs() {
        const logs = await this.logger.getLogs();
        const blob = new Blob([logs.join("\n")], {
            type: "text/plain",
        });
        const filename = `glory_logs_${luxon.DateTime.now().toFormat("yyyy-LL-dd-HH-mm-ss")}.txt`;
        downloadFile(blob, filename);
    }

    async resetCashMachine() {
        if (["DISCONNECTED", "BAD_CREDENTIALS"].includes(this.state.status)) {
            this.notification.add(_t("Cash machine is disconnected"), { type: "danger" });
            return;
        }

        this.state.resetInProgress = true;
        const clearNotification = this.notification.add(_t("Resetting cash machine..."), {
            type: "info",
            sticky: true,
        });

        await this.gloryService.reset();

        this.state.resetInProgress = false;
        clearNotification();
        this.notification.add(_t("Reset complete"), { type: "info" });
    }

    openAdminPage() {
        const gloryIp = this.props.record.data.glory_websocket_address;
        if (!gloryIp) {
            this.notification.add("Please configure the IP address before opening the admin page", {
                type: "warning",
            });
            return;
        }
        const protocol = window.location.protocol;
        const port = protocol === "http:" ? 3000 : 3001;
        browser.open(
            `${protocol}//${this.props.record.data.glory_websocket_address}:${port}/control`
        );
    }
}

export const GloryAdminButtonsWidget = {
    component: GloryAdminButtons,
};
registry.category("view_widgets").add("pos_glory_cash_admin_buttons", GloryAdminButtonsWidget);
