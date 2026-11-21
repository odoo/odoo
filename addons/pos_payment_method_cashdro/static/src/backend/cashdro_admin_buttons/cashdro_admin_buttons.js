import { Component, usePlugin, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { downloadFile } from "@web/core/network/download";
import { Logger } from "@bus/workers/bus_worker_utils";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";

export class CashdroAdminButtons extends Component {
    static template = `pos_cashdro.CashdroAdminButtons`;
    props = useProps(standardWidgetProps);

    setup() {
        super.setup();
        this.notification = usePlugin(NotificationPlugin);
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
        window.open(`${protocol}//${cashdroIp}/Cashdro3Web/#/diagnosis/false`);
    }
}

export const CashdroAdminButtonsWidget = {
    component: CashdroAdminButtons,
};
registry
    .category("view_widgets")
    .add("pos_payment_method_cashdro.admin_buttons", CashdroAdminButtonsWidget);
