import { _t } from "@web/core/l10n/translation";

const READ_TIMEOUT_MS = 1000;

/**
 * @typedef {{
 *   open(options: SerialPortOptions): Promise<void>;
 *   close(): Promise<void>;
 *   readable: ReadableStream<Uint8Array>;
 *   writable: WritableStream<Uint8Array>;
 * }} SerialPort
 */

/**
 * @typedef {{
 *   baudRate: number;
 *   dataBits?: 7 | 8;
 *   parity?: "none" | "even" | "odd";
 *   stopBits?: 1 | 2;
 * }} SerialPortOptions
 */

export class WebSerialDevice {
    /**
     * @param {SerialPort} serialPort
     */
    constructor(serialPort) {
        this._encoder = new TextEncoder();
        this._decoder = new TextDecoder();
        this._serialPort = serialPort;
    }

    /**
     * @abstract
     * @returns {SerialPortOptions}
     */
    get serialPortOptions() {
        throw Error("Not implemented");
    }

    async open() {
        await this._serialPort.open(this.serialPortOptions);
        if (await this.supported()) {
            return true;
        }
        await this._serialPort.close();
        return false;
    }

    async close() {
        await this._serialPort.close();
    }

    async supported() {
        return false;
    }

    /** @param {string} message */
    async write(message) {
        if (!this._serialPort.writable) {
            throw new Error(_t("The device has been disconnected"));
        }
        const writer = this._serialPort.writable.getWriter();
        await writer.write(this._encoder.encode(message));
        writer.releaseLock();
    }

    /** @param {string} terminator */
    async readUntil(terminator) {
        if (!this._serialPort.readable) {
            throw new Error(_t("The device has been disconnected"));
        }

        const reader = this._serialPort.readable.getReader();
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
            throw new Error(_t("The device has been disconnected"));
        } finally {
            reader.releaseLock();
        }

        return result;
    }
}

/**
 * @template {typeof WebSerialDevice} T
 * @param {T} deviceClass
 * @returns {Promise<InstanceType<T> | null>}
 */
export const openWebSerialDevice = async (deviceClass) => {
    if (!navigator.serial) {
        return null;
    }

    const allowedPorts = await navigator.serial.getPorts();
    const connectedPorts = allowedPorts.filter((port) => port.connected);
    for (const port of connectedPorts) {
        const device = new deviceClass(port);
        if (await device.open()) {
            return device;
        }
    }

    return null;
};
