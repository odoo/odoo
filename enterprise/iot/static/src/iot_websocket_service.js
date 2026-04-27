/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { removeIoTReportIdFromBrowserLocalStorage } from "./client_action/delete_local_storage";

export class IotWebsocket {
    jobs = {};
    notifyUser = true; // Display jobs notifications

    constructor(bus_service, notification, orm) {
        this.notification = notification;
        this.bus_service = bus_service;
        this.orm = orm;
    }

    async getDevicesFromIds(stored_content) {
        return await this.orm.call("ir.actions.report", "get_devices_from_ids", [
            0,
            stored_content,
        ]);
    }

    async addJob(stored_content, args, notifyUser = false) {
        this.notifyUser = notifyUser;
        const [report_id, active_record_ids, report_data, uuid] = args;
        const response = await this.getDevicesFromIds(stored_content).catch((error) => {
            removeIoTReportIdFromBrowserLocalStorage(report_id);
            throw error;
        });
        this.jobs[uuid] = response;

        // For each printer device, we add a notification that the print is being sent.
        // This notification is sticky so it won't disappear until the print is done, and stored
        // in the device object, this allows us to manipulate it later on (remove it when the
        // print is done or if the connection fails)
        for (const device of this.jobs[uuid]) {
            if (this.notifyUser) {
                device._removeSendingNotification = this.notification.add(_t('Sending to printer %s...', device["display_name"]), {
                    type: "info",
                    sticky: true,
                });
            }
        }
        // The IoT is supposed to send back a confirmation request when the operation
        // is done. This request will trigger the `jobs[uuid]` to be removed
        // If the `jobs[uuid]` is still there after 10 seconds,
        // we assume the connection to the printer failed
        const iotBoxConfirmation = setTimeout(() => {
            this.jobs[uuid].forEach((device) => {
                device._removeSendingNotification?.();
                this.notification.add(_t("Check IoT Box connection. Try restarting if needed."), {
                    title: (_t("Connection to printer failed ") + device["display_name"]),
                    type: "danger",
                });
            });
            delete this.jobs[uuid];
        }, 10000);
        try {
            await this.orm.call("ir.actions.report", "render_and_send", [
                report_id,
                response,
                active_record_ids,
                report_data,
                uuid,
            ]);
        } catch (e) {
            // Send global notification instead of one per job
            clearTimeout(iotBoxConfirmation);
            if (this.notifyUser) {
                this.notification.add(_t("Check IoT Box connection. Try restarting if needed."), { type: "danger" });
            }
            throw e;
        }
    }

    onPrintConfirmation(deviceId, printId) {
        const jobIndex = this.jobs[printId].findIndex((element) => element && element["identifier"] === deviceId);
        const device = this.jobs[printId][jobIndex];

        if (!device) {
            return; // avoid traceback if multiple jobs confirmations with same `print_id`
        }

        device._removeSendingNotification?.();
        this.notification.add(_t('Printing operation completed on printer %s', device["display_name"]), {
            type: "success",
        });
        delete this.jobs[printId][jobIndex];
    }
}

export const IotWebsocketService = {
    dependencies: ["bus_service", "notification", "orm"],

    async start(env, { bus_service, notification, orm }) {
        let ws = new IotWebsocket(bus_service, notification, orm);
        const iot_channel = await orm.call("iot.channel", "get_iot_channel", [0]);

        if (iot_channel) {
            bus_service.addChannel(iot_channel);
            bus_service.subscribe("print_confirmation", ({ print_id, device_identifier }) => {
                if (ws.jobs[print_id]) {
                    ws.onPrintConfirmation(device_identifier, print_id);
                }
            });
        }
        return ws;
    },
};

registry.category("services").add("iot_websocket", IotWebsocketService);
