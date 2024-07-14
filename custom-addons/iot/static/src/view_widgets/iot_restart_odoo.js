/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { IoTConnectionErrorDialog } from "../iot_connection_error_dialog";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";

let restarting = false;

export class IoTRestartOdooOrReboot extends Component {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.http = useService("http");
        this.notification = useService("notification");
        this.rpc = useService("rpc");
    }

    get ip_url() {
        return this.props.record.data.ip_url;
    }

    async onClick() {
        this.dialog.add(ConfirmationDialog, {
            body:
                this.props.action == "restart_odoo"
                    ? _t("Are you sure you want to restart Odoo on the IoT box?")
                    : _t("Are you sure you want to reboot the IoT box?"),
            confirm: () => this.restartOdooOrReboot(),
            cancel: () => {},
        });
    }

    showMsgAndClearInterval(interval, message, title, message_type) {
        /// Displays the specified message through the notifications
        /// and stops the interval sending requests to the server
        if (interval) {
            restarting = false;
            clearInterval(interval);
        }
        this.notification.add(message, {
            title: title,
            type: message_type,
        });
    }

    async callRestartMethodOnServer() {
        /// Call "restart_odoo_or_reboot" method from "hw_posbox_homepage" controller
        let restartResponse;
        try {
            this.showMsgAndClearInterval(
                null,
                _t("Please wait"),
                _t("Restarting"),
                "warning"
            );
            restartResponse = await this.rpc(this.ip_url + "/iot_restart_odoo_or_reboot", {
                action: this.props.action,
            });
        } catch (error) {
            restartResponse = `${error.name} ${error.message}`;
            this.doWarnFail(this.ip_url);
        }
        return restartResponse;
    }

    pingServerUntilItFinishedRestarting() {
        /// Every 4 seconds check if the server responds
        /// Stop checking when it does
        restarting = true;
        const responseInterval = setInterval(async () => {
            let server_response;
            try {
                server_response = await this.http.get(this.ip_url + "/hw_proxy/hello", "text");
                if (server_response == "ping" && restarting) {
                    this.showMsgAndClearInterval(
                        responseInterval,
                        _t("Restart finished"),
                        _t("Success"),
                        "success"
                    );
                }
            } catch (error) {
                // During the restart, the http request will always throw a "TypeError"
                // We can ignore it and only catch other errors
                if (!(error instanceof TypeError)) {
                    this.showMsgAndClearInterval(
                        responseInterval,
                        `${error.name} ${error.message}`,
                        _t("Restart Failed"),
                        "danger"
                    );
                }
            }
        }, 4000);
        // If the IoT box is still unreachable after 10 minutes, it's a timeout
        setTimeout(() => {
            if (restarting) {
                this.showMsgAndClearInterval(
                    responseInterval,
                    _t("Timed out"),
                    _t("Restart Failed"),
                    "danger"
                );
                this.doWarnFail(this.ip_url);
            }
        }, 600000);
    }

    async restartOdooOrReboot() {
        /// Call restart method on server, then ping it until restarting is finished
        /// Only restart if there are no other restart processes active
        /// If an error is encountered, display it and stop
        let restartResponse;
        if (!restarting) {
            restartResponse = await this.callRestartMethodOnServer();
            if (restartResponse == "success") {
                this.pingServerUntilItFinishedRestarting();
            } else {
                // If the python code triggerred an exception, display its message and stop
                this.showMsgAndClearInterval(
                    null,
                    restartResponse,
                    _t("Restart Failed"),
                    "danger"
                );
            }
        } else {
            this.showMsgAndClearInterval(
                null,
                _t("Last restarting process hasn't finished yet"),
                _t("Please wait"),
                "danger"
            );
        }
    }

    doWarnFail(url) {
        this.dialog.add(IoTConnectionErrorDialog, { href: url });
    }
}

IoTRestartOdooOrReboot.template = `iot.IoTRestartOdooOrReboot`;

IoTRestartOdooOrReboot.props = {
    ...standardWidgetProps,
    btn_name: { type: String },
    action: { type: String },
};

export const ioTRestartOdooOrReboot = {
    component: IoTRestartOdooOrReboot,
    extractProps: ({ attrs }) => {
        return {
            btn_name: attrs.btn_name,
            action: attrs.action,
        };
    },
};
registry.category("view_widgets").add("iot_restart_odoo_or_reboot", ioTRestartOdooOrReboot);
