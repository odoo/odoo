/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ScaleScreen } from "@point_of_sale/app/screens/scale_screen/scale_screen";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ErrorTracebackPopup } from "@point_of_sale/app/errors/popups/error_traceback_popup";
import { useService, useBus } from "@web/core/utils/hooks";

patch(ScaleScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.popup = useService("popup");
        useBus(this.hardwareProxy, "change_status", this.onProxyStatusChange);
    },
    async onProxyStatusChange({ detail: newStatus }) {
        if (this.iot_box.connected && newStatus.drivers.scale?.status === "connected") {
            this._error = false;
        } else {
            if (!this._error) {
                this._error = true;
                this.popup.add(ErrorPopup, {
                    title: _t("Could not connect to IoT scale"),
                    body: _t("The IoT scale is not responding. You should check your connection."),
                });
            }
        }
    },
    get scale() {
        return this.hardwareProxy.deviceControllers.scale;
    },
    get isManualMeasurement() {
        return this.scale?.manual_measurement;
    },
    /**
     * @override
     */
    onMounted() {
        this.iot_box = this.hardwareProxy.iotBoxes.find((box) => box.ip === this.scale._iot_ip);
        this._error = false;
        if (!this.isManualMeasurement) {
            this.scale.action({ action: "start_reading" });
        }
        super.onMounted(...arguments);
    },
    /**
     * @override
     */
    onWillUnmount() {
        super.onWillUnmount(...arguments);
        // FIXME POSREF shouldn't the stop_reading action be awaited before removing the listener?
        this.scale.action({ action: "stop_reading" });
        this.scale.removeListener();
    },
    measureWeight() {
        this.scale.action({ action: "read_once" });
    },
    /**
     * @override
     * Completely replace how the original _readScale works.
     */
    async _readScale() {
        await this.scale.addListener(this._onValueChange.bind(this));
        await this.scale.action({ action: "read_once" });
    },
    async _onValueChange(data) {
        if (data.status.status === "error") {
            await this.popup.add(ErrorTracebackPopup, {
                title: data.status.message_title,
                body: data.status.message_body,
            });
        } else {
            this.state.weight = data.value;
        }
    },
});
