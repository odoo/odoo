import { delay } from "@web/core/utils/concurrency";
import { WebSerialDevice } from "./web_serial_device";

// eslint-disable-next-line no-control-regex
const WEIGHT_REGEX = /\x02([0-9.]+)(N?)\r/;
// eslint-disable-next-line no-control-regex
const STATUS_REGEX = /\x02\?(.)\r/;

const STATUS_BITS = {
    0: "SCALE_IN_MOTION",
    1: "OVER_CAPACITY",
    2: "UNDER_ZERO",
    3: "OUTSIDE_ZERO_RANGE",
    4: "CENTER_OF_ZERO",
    5: "NET_WEIGHT",
};

export class WebSerialScale extends WebSerialDevice {
    constructor() {
        super(...arguments);
        this.tareEnabled = false;
        this.status = Object.fromEntries(
            Object.values(STATUS_BITS).map((status) => [status, false])
        );
    }

    /** @returns {import("./web_serial_device").SerialPortOptions} */
    get serialPortOptions() {
        return { baudRate: 9600, stopBits: 1, parity: "even" };
    }

    async supported() {
        await this.write("Ehello");
        const response = await this.readUntil("hello");
        const supported = response === "\x02E\rhello";

        if (supported) {
            await this.write("F");
            await this.readUntil("F");
        }

        return supported;
    }

    /** @returns {Promise<number | null>} the new weight or null if it didn't change */
    async readWeight() {
        await this.write("W");
        const response = await this.readUntil("\r");

        const weightMatch = response.match(WEIGHT_REGEX);
        if (weightMatch) {
            this.tareEnabled = weightMatch[2] === "N";
            this.updateStatusFromStatusByte(0);
            return parseFloat(weightMatch[1]);
        }

        const statusMatch = response.match(STATUS_REGEX);
        if (statusMatch) {
            const statusByte = statusMatch[1].charCodeAt(0);
            this.updateStatusFromStatusByte(statusByte);
            if (!this.tareEnabled && this.status.NET_WEIGHT) {
                this.tareEnabled = true;
                return 0;
            }
            this.tareEnabled = this.status.NET_WEIGHT;
            if (this.status.SCALE_IN_MOTION) {
                // If the scale is in motion, we wait and try to read again
                await delay(100);
                return this.readWeight();
            }
        }

        return null;
    }

    /** @param {number} statusByte */
    updateStatusFromStatusByte(statusByte) {
        for (const bitNum in STATUS_BITS) {
            const bitMask = 1 << bitNum;
            this.status[STATUS_BITS[bitNum]] = Boolean(bitMask & statusByte);
        }
    }
}
