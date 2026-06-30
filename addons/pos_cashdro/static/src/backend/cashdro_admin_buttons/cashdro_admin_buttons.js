import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { downloadFile } from "@web/core/network/download";
import { Logger } from "@bus/workers/bus_worker_utils";

export class CashdroAdminButtons extends Component {
    static template = `pos_cashdro.CashdroAdminButtons`;
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.logger = new Logger("pos_cashdro");
    }

    async downloadLogs() {
        const logs = await this.logger.getLogs();
        const blob = new Blob([logs.join("\n")], {
            type: "text/plain",
        });
        const filename = `cashdro_logs_${luxon.DateTime.now().toFormat("yyyy-LL-dd-HH-mm-ss")}.txt`;
        downloadFile(blob, filename);
    }

    openDiagnosticsPage() {
        const cashdroIp = this.props.record.data.cashdro_ip;
        if (!cashdroIp) {
            this.notification.add(
                _t("Please configure the IP address before opening the diagnostics page"),
                {
                    type: "warning",
                }
            );
            return;
        }
        const protocol = this.props.record.data.cashdro_use_lna
            ? "http:"
            : window.location.protocol;
        browser.open(`${protocol}//${cashdroIp}/Cashdro3Web/#/diagnosis/false`);
    }
}

export const CashdroAdminButtonsWidget = {
    component: CashdroAdminButtons,
};
registry.category("view_widgets").add("pos_cashdro_admin_buttons", CashdroAdminButtonsWidget);
