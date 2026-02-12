import { delay } from "@web/core/utils/concurrency";
import { ScaleInterface } from "@point_of_sale/app/utils/scale/scale_interface";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const SERIAL_PORT_SETTINGS = {
    baudRate: 9600,
    dataBits: 7,
    parity: "even",
};

const READ_TIMEOUT_MS = 1000;
const COMMAND_DELAY_MS = 100;

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

export class WebSerialScale extends ScaleInterface {
    /**
     * @param {import("@point_of_sale/app/services/pos_store").PosStore} pos
     * @param {SerialPort} [serialPort]  If provided, this serial port is used otherwise the first compatible port is used.
     */
    setup(pos, serialPort) {
        super.setup(...arguments);

        this._encoder = new TextEncoder();
        this._decoder = new TextDecoder();
        this.status = Object.fromEntries(
            Object.values(STATUS_BITS).map((status) => [status, false])
        );
        this.isListening = false;

        if (serialPort) {
            this.serialPort = serialPort;
        }
    }

    async connectToScale() {
        if (!navigator.serial) {
            return false;
        }

        const allowedPorts = await navigator.serial.getPorts();
        const connectedPorts = allowedPorts.filter((port) => port.connected);
        for (const port of connectedPorts) {
            this.serialPort = port;
            if (await this.isScaleSupported(port)) {
                break;
            }
            this.serialPort = null;
        }

        if (this.serialPort) {
            this.listenForWeightChanges();
        }

        return Boolean(this.serialPort);
    }

    async listenForWeightChanges() {
        this.isListening = true;
        while (this.serialPort.writable) {
            await this.requestWeightAndUpdateStatus();
            await delay(COMMAND_DELAY_MS);
        }

        await this.serialPort.close();
        this.isListening = false;
    }

    async requestWeightAndUpdateStatus() {
        await this.write("W");
        const response = await this.readUntil("\r");

        const weightMatch = response.match(WEIGHT_REGEX);
        if (weightMatch) {
            this._setWeight(parseFloat(weightMatch[1]));
            const isNetWeight = weightMatch[2] === "N";
            this.hardwareTare = isNetWeight;
            this.updateStatusFromStatusByte(0);
        }

        const statusMatch = response.match(STATUS_REGEX);
        if (statusMatch) {
            const statusByte = statusMatch[1].charCodeAt(0);
            this.updateStatusFromStatusByte(statusByte);
            if (!this.hardwareTare && this.status.NET_WEIGHT) {
                this._setWeight(0);
            }
            this.hardwareTare = this.status.NET_WEIGHT;
        }
    }

    async onWeighingStart() {
        if (!this.isListening) {
            const connected = await this.connectToScale();
            if (!connected) {
                this.onScaleDisconnected();
            }
        }
    }

    /** @param {number} statusByte */
    updateStatusFromStatusByte(statusByte) {
        for (const bitNum in STATUS_BITS) {
            const bitMask = 1 << bitNum;
            this.status[STATUS_BITS[bitNum]] = Boolean(bitMask & statusByte);
        }
    }

    /** @param {string} message */
    async write(message) {
        const writer = this.serialPort.writable.getWriter();
        await writer.write(this._encoder.encode(message));
        writer.releaseLock();
    }

    /** @param {string} terminator */
    async readUntil(terminator) {
        if (!this.serialPort.readable) {
            this.onScaleDisconnected();
        }

        const reader = this.serialPort.readable.getReader();
        let result = "";
        try {
            setTimeout(() => reader.releaseLock(), READ_TIMEOUT_MS);
            while (!result.includes(terminator)) {
                const { value, done } = await reader.read();
                if (done) {
                    break;
                }
                result += this._decoder.decode(value);
            }
        } catch {
            this.onScaleDisconnected();
        }

        reader.releaseLock();
        return result;
    }

    async isScaleSupported() {
        try {
            await this.serialPort.open(SERIAL_PORT_SETTINGS);
        } catch {
            return false;
        }

        await this.write("Ehello");
        const response = await this.readUntil("hello");
        const supported = response === "\x02E\rhello";

        if (supported) {
            await this.write("F");
            await this.readUntil("F");
        } else {
            await this.serialPort.close();
        }

        return supported;
    }

    onScaleDisconnected() {
        this.onError(_t("The scale has been disconnected."));
    }

    get warningMessage() {
        if (this.status.OVER_CAPACITY) {
            return _t("Scale is over capacity");
        }
        if (this.status.UNDER_ZERO) {
            return _t("Scale is under zero");
        }
        return "";
    }

    get isWeightValid() {
        return super.isWeightValid && !this.status.SCALE_IN_MOTION && !this.warningMessage;
    }
}

registry.category("electronic_scales").add("web_serial", WebSerialScale, { sequence: 100 });
