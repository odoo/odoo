import { patch } from "@web/core/utils/patch";
import LedController from "../led_controller";

// The default color codes do not exactly match the colors that can be found on a screen.
const ODOO_COLOR = { r: 255, g: 1, b: 188 };
const SUCCESS_COLOR = { r: 61, g: 255, b: 0 };
const WARNING_COLOR = { r: 255, g: 58, b: 0 };
const DANGER_COLOR = { r: 255, g: 0, b: 0 };

patch(LedController.prototype, {
    setup() {
        super.setup();
        this.isBoxapos = Boolean(window.Kiosk) && this.config.module_pos_hardware;
    },
    _setBoxaposColor(r, g, b, luminance) {
        try {
            window.Kiosk.postMessage(
                JSON.stringify({
                    action: "setColor",
                    value: `${r} ${g} ${b} ${luminance}`,
                })
            );
        } catch {
            console.warn("Failed to set color, the provider is not available");
        }
    },
    setDanger(intensity = 255) {
        if (!this.isBoxapos) {
            return super.setDanger(intensity);
        }

        this._setBoxaposColor(DANGER_COLOR.r, DANGER_COLOR.g, DANGER_COLOR.b, intensity);
    },
    setWarning(intensity = 255) {
        if (!this.isBoxapos) {
            return super.setWarning(intensity);
        }

        this._setBoxaposColor(WARNING_COLOR.r, WARNING_COLOR.g, WARNING_COLOR.b, intensity);
    },
    setSuccess(intensity = 255) {
        if (!this.isBoxapos) {
            return super.setSuccess(intensity);
        }

        this._setBoxaposColor(SUCCESS_COLOR.r, SUCCESS_COLOR.g, SUCCESS_COLOR.b, intensity);
    },
    setDefault(intensity = 255) {
        if (!this.isBoxapos) {
            return super.setDefault(intensity);
        }

        this._setBoxaposColor(ODOO_COLOR.r, ODOO_COLOR.g, ODOO_COLOR.b, intensity);
    },
    off() {
        if (!this.isBoxapos) {
            return super.off();
        }

        this._setBoxaposColor(ODOO_COLOR.r, ODOO_COLOR.g, ODOO_COLOR.b, 0);
    },
});
