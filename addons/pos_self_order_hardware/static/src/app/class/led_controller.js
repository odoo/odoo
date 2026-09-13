/**
 * These methods must be overridden by the various hardware providers.
 *
 * Available providers:
 * - pos_hardware/static/src/common/class/providers/led_controller_boxapos.js
 **/

export default class LedController {
    constructor(config) {
        this.config = config;
        this.setup();
    }
    setup() {}
    setColor(r, g, b, luminance) {}
    setDanger(intensity = 255) {}
    setWarning(intensity = 255) {}
    setSuccess(intensity = 255) {}
    setDefault(intensity = 255) {}
    off() {}
}
