import { uniqueId } from "@web/core/utils/functions";

/**
 * Used to communicate to the iot devices.
 */
export class DeviceController {
    /**
     * @param {import("@iot_base/network_utils/longpolling").IoTLongpolling} iotLongpolling
     * @param {{ iot_ip: string, identifier: string, iot_id: Object, manual_measurement: string }} deviceInfo - Representation of an iot device
     */
    constructor(iotLongpolling, deviceInfo) {
        this.id = uniqueId('listener-');
        this.iotIp = deviceInfo.iot_ip;
        this.identifier = deviceInfo.identifier;
        this.iotId = deviceInfo.iot_id?.id; // if class is instantiated without providing the full device record, iot_id will be undefined
        this.manual_measurement = deviceInfo.manual_measurement;
        this.iotLongpolling = iotLongpolling;
    }

    /**
     * Send an action to the device.
     * @param data - action to send to the device
     * @param fallback - if true, no notification will be displayed on fail
     */
    action(data, fallback = false) {
        return this.iotLongpolling.action(this.iotIp, this.identifier, data, fallback);
    }

    /**
     * Add a listener to the device.
     * @param callback - function to call when the listener is triggered
     * @param fallback - if true, no notification will be displayed on fail
     */
    addListener(callback, fallback = true) {
        return this.iotLongpolling.addListener(this.iotIp, [this.identifier], this.id, callback, fallback);
    }
    removeListener() {
        return this.iotLongpolling.removeListener(this.iotIp, this.identifier, this.id);
    }
}
