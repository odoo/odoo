/** @odoo-module **/
import { uniqueId } from "@web/core/utils/functions";

/**
 * Used to communicate to the iot devices.
 */
export class DeviceController {
    /**
     * @param {Object} iotLongpolling
     * @param {{ iot_ip: string?, identifier: string?, manual_measurement: boolean? }} deviceInfo - Representation of an iot device
     */
    constructor(iotLongpolling, deviceInfo = { iot_ip: null, identifier: null, manual_measurement: null }) {
        this.id = uniqueId('listener-');
        this.iotIp = deviceInfo.iot_ip;
        this.identifier = deviceInfo.identifier;
        this.manualMeasurement = deviceInfo.manual_measurement;
        this.iotLongpolling = iotLongpolling;
    }

    /**
     * Send an action to the device.
     * @param data - action to send to the device
     * @param fallback - if true, no `IoTConnectionErrorDialog` popup will be displayed on fail
     */
    action(data, fallback = false) {
        return this.iotLongpolling.action(this.iotIp, this.identifier, data, fallback);
    }

    /**
     * Add a listener to the device.
     * @param callback - function to call when the listener is triggered
     * @param fallback - if true, no `IoTConnectionErrorDialog` popup will be displayed on fail
     */
    addListener(callback, fallback = false) {
        return this.iotLongpolling.addListener(this.iotIp, [this.identifier], this.id, callback, fallback);
    }
    removeListener() {
        return this.iotLongpolling.removeListener(this.iotIp, this.identifier, this.id);
    }
}
