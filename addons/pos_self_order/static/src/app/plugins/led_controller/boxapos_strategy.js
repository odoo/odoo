import {
    compareVersion,
    getCalibratedLedColor,
    SUCCESS_COLOR,
    ERROR_COLOR,
    TIMEOUT_MS,
} from "./utils";

const PRESETS = {
    SUCCESS: {
        id: 1,
        color: getCalibratedLedColor(SUCCESS_COLOR),
        brightness: 255,
        reverse: false,
        speed: 40,
        animation: 3,
        play: false,
    },
    ERROR: {
        id: 2,
        color: getCalibratedLedColor(ERROR_COLOR),
        brightness: 255,
        reverse: false,
        speed: 15,
        animation: 2,
        play: false,
    },
};

export class BoxaPosStrategy {
    static IP = "127.0.0.1";
    static PORT = "8080";
    static REQUIRED_VERSION = "260.812.1";
    static REQUIRED_METHODS = ["setColor", "setPreset", "getPresets", "applyPreset"];

    constructor() {
        this.baseUrl = `http://${BoxaPosStrategy.IP}:${BoxaPosStrategy.PORT}`;
    }

    /**
     * Attempts to detect a compatible BoxaPos device on the network.
     *
     * @returns {Promise<BoxaPosStrategy|boolean>} A new strategy instance if detected, false otherwise.
     */
    static async detect() {
        try {
            const response = await fetch(`http://${this.IP}:${this.PORT}/status`, {
                signal: AbortSignal.timeout(TIMEOUT_MS),
            });

            if (!response.ok) {
                return false;
            }

            const data = await response.json();
            const availableCapabilities = new Set(data.capabilities || []);
            const versionComparison = compareVersion(this.REQUIRED_VERSION, data.version);

            const isCompatible =
                data.name === "Kiosk" &&
                data.platform === "android" &&
                versionComparison !== false &&
                versionComparison >= 0 &&
                this.REQUIRED_METHODS.every((method) => availableCapabilities.has(method)) &&
                data.ledController?.connected;

            if (isCompatible) {
                return new BoxaPosStrategy();
            }
        } catch (error) {
            error;
        }
        return false;
    }

    /**
     * Sends a command to the BoxaPos API.
     *
     * @param {string} action - The action to perform.
     * @param {any} [value=null] - Optional payload for the action.
     * @returns {Promise<any|boolean>} The API response, or false if it fails.
     */
    async sendCommand(action, value = null) {
        try {
            const body = value !== null ? { action, value } : { action };

            const response = await fetch(`${this.baseUrl}/request`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
                signal: AbortSignal.timeout(TIMEOUT_MS),
            });

            if (!response.ok) {
                return false;
            }

            return await response.json();
        } catch (error) {
            error;
            return false;
        }
    }

    /**
     * Initializes the device by setting up required presets.
     *
     * @returns {Promise<boolean>} True if startup configuration succeeds.
     */
    async onStartup() {
        return !!(
            (await this.sendCommand("setPreset", PRESETS.SUCCESS)) &&
            (await this.sendCommand("setPreset", PRESETS.ERROR))
        );
    }

    /**
     * Applies a specific preset by its ID.
     *
     * @param {number} [presetId=1] - The ID of the preset to apply.
     * @returns {Promise<boolean>}
     */
    async applyPreset(presetId = 1) {
        return !!this.sendCommand("applyPreset", presetId);
    }

    /**
     * Retrieves all configured presets from the device.
     *
     * @returns {Promise<any>}
     */
    async getPresets() {
        return this.sendCommand("getPresets");
    }

    /**
     * Triggers the success visual state on the device.
     *
     * @returns {Promise<boolean>}
     */
    async setSuccessState() {
        return await this.applyPreset(PRESETS.SUCCESS.id);
    }

    /**
     * Triggers the error visual state on the device.
     *
     * @returns {Promise<boolean>}
     */
    async setErrorState() {
        return await this.applyPreset(PRESETS.ERROR.id);
    }

    /**
     * Sets the device color.
     *
     * @param {string} idleColor - The RGB color string to apply.
     * @returns {Promise<boolean>}
     */
    async setIdleState(idleColor) {
        return !!(await this.sendCommand("setColor", `${getCalibratedLedColor(idleColor)},255`));
    }
}
