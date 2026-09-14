/** @odoo-module native */
import { barcodeService } from "@barcodes/barcode_service";
import { EventBus, onWillDestroy, useComponent } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { parseFloat as oParseFloat } from "@web/core/parsers";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
const log = makeLogger("pos.number_buffer");

const INPUT_KEYS = new Set(
    ["Delete", "Backspace", "+1", "+2", "+5", "+10", "+20", "+50"].concat(
        "0123456789+-.,".split(""),
    ),
);
const CONTROL_KEYS = new Set(["Enter", "Escape", "Esc"]);
const ALLOWED_KEYS = new Set([...INPUT_KEYS, ...CONTROL_KEYS]);
const getDefaultConfig = () => ({
    decimalPoint: false,
    triggerAtEnter: false,
    triggerAtEsc: false,
    triggerAtInput: false,
    useWithBarcode: false,
});

class NumberBuffer extends EventBus {
    static serviceDependencies = ["mail.sound_effects", "localization", "overlay"];
    constructor() {
        super();
        this.setup(...arguments);
    }
    setup(services) {
        this.state = {};
        this.isReset = false;
        this.bufferHolderStack = [];
        this.sound = services["mail.sound_effects"];
        this.localization = services.localization;
        this.overlay = services.overlay;
        window.addEventListener("keyup", this._onKeyboardInput.bind(this));
    }
    /**
     * @returns {String}
     */
    get() {
        return this.state ? this.state.buffer : null;
    }
    /**
     * @param {String} val
     */
    set(val) {
        this.state.lastSet = val;
        this.state.buffer = !isNaN(parseFloat(val)) ? val : "";
        log.logic("set", () => ({
            val,
            buffer: this.state.buffer,
            holder: this.component?.constructor?.name,
        }));
        this.trigger("buffer-update", this.state.buffer);
    }
    reset() {
        this.isReset = true;
        this.state.buffer = "";
        this.trigger("buffer-update", this.state.buffer);
    }
    capture() {
        if (this.handler) {
            log.logic("capture: flushing pending keys", () => ({
                pending: this.eventsBuffer?.length,
                holder: this.component?.constructor?.name,
            }));
            clearTimeout(this._timeout);
            const handler = this.handler;
            delete this.handler;
            handler(true);
        }
    }
    /**
     * @returns {number}
     */
    getFloat() {
        return oParseFloat(this.get());
    }
    /**
     * @param {Object} config
     * @param {String|null} config.decimalPoint
     * @param {String|null} config.triggerAtEnter
     * @param {String|null} config.triggerAtEsc
     * @param {String|null} config.triggerAtInput
     * @param {Boolean} config.useWithBarcode
     */
    use(config) {
        const currentComponent = useComponent();
        config = Object.assign(getDefaultConfig(), config);
        // keys still batched for the holder about to be covered were typed for it
        this.capture();

        const holder = {
            component: currentComponent,
            state: config.state ? config.state : { buffer: "", toStartOver: false },
            config,
        };
        this.bufferHolderStack.push(holder);
        log.lifecycle("use", () => ({
            component: currentComponent.constructor.name,
            depth: this.bufferHolderStack.length,
            useWithBarcode: config.useWithBarcode,
            triggers: {
                enter: Boolean(config.triggerAtEnter),
                esc: Boolean(config.triggerAtEsc),
                input: Boolean(config.triggerAtInput),
            },
        }));
        this._setUp();
        onWillDestroy(() => {
            const indexComponent = this.bufferHolderStack.indexOf(holder);
            if (indexComponent !== -1) {
                this.bufferHolderStack.splice(indexComponent, 1);
            }
            log.lifecycle("release", () => ({
                component: currentComponent.constructor.name,
                depth: this.bufferHolderStack.length,
            }));
            this._setUp();
        });
    }
    get _currentBufferHolder() {
        return this.bufferHolderStack[this.bufferHolderStack.length - 1];
    }
    _setUp() {
        if (this.activeHolder === this._currentBufferHolder) {
            return;
        }
        log.lifecycle("active holder changed: cancel pending keys", () => ({
            pending: this.eventsBuffer?.length || 0,
        }));
        clearTimeout(this._timeout);
        delete this.handler;
        this.eventsBuffer = [];
        if (this.activeHolder) {
            this.activeHolder.isReset = this.isReset;
        }
        this.activeHolder = this._currentBufferHolder;
        this.isReset = this.activeHolder?.isReset || false;
        if (!this._currentBufferHolder) {
            this.component = null;
            this.state = {};
            this.config = null;
            return;
        }
        const { component, state, config } = this._currentBufferHolder;
        this.component = component;
        this.state = state;
        this.config = config;
        this.decimalPoint = config.decimalPoint || this.localization.decimalPoint;
        this.maxTimeBetweenKeys = this.config.useWithBarcode
            ? barcodeService.maxTimeBetweenKeysInMs
            : 0;
    }
    _onKeyboardInput(event) {
        const overlays = Object.values(this.overlay.overlays);
        if (overlays.length && !this._currentBufferHolder?.config?.captureWithOverlay) {
            log.logic("keyboard input ignored: overlay open", () => ({
                key: event.key,
                overlays: overlays.length,
            }));
            return;
        }
        return (
            this._currentBufferHolder &&
            this._bufferEvents(this._onInput((event) => event.key))(event)
        );
    }
    sendKey(key) {
        if (!this._currentBufferHolder) {
            return;
        }
        const event = new KeyboardEvent("keyup", { key });
        Object.defineProperty(event, "target", { value: {} });

        return this._bufferEvents(this._onInput((event) => event.key))(event);
    }
    _bufferEvents(handler) {
        return (event) => {
            if (
                ["INPUT", "TEXTAREA"].includes(event.target.tagName) ||
                !this.eventsBuffer
            ) {
                return;
            }
            if (event.ctrlKey || event.metaKey || event.altKey) {
                return;
            }
            clearTimeout(this._timeout);
            this.eventsBuffer.push(event);
            this._timeout = setTimeout(handler, this.maxTimeBetweenKeys);
            this.handler = handler;
        };
    }
    _onInput(keyAccessor) {
        return (manualCapture = false) => {
            const events = this.eventsBuffer;
            const holder = this._currentBufferHolder;
            this.eventsBuffer = [];
            delete this.handler;
            const process =
                manualCapture ||
                session.test_mode ||
                (!manualCapture && events.length <= 2);
            log.logic("onInput", () => ({
                keys: events.map(keyAccessor),
                manualCapture,
                process,
                treatedAsBarcode: !process,
                holder: this.component?.constructor?.name,
            }));
            if (process) {
                for (const event of events) {
                    if (!ALLOWED_KEYS.has(keyAccessor(event))) {
                        return;
                    }
                }
                for (const event of events) {
                    if (holder !== this._currentBufferHolder) {
                        break;
                    }
                    this._handleInput(keyAccessor(event));
                    event.preventDefault();
                    event.stopPropagation();
                }
            }
        };
    }
    _handleInput(key) {
        const holder = this._currentBufferHolder;
        log.logic("handleInput", () => ({
            key,
            buffer: this.state.buffer,
            holder: this.component?.constructor?.name,
        }));
        if (key === "Enter" && this.config.triggerAtEnter) {
            this.config.triggerAtEnter(this.state);
        } else if ((key === "Escape" || key === "Esc") && this.config.triggerAtEsc) {
            this.config.triggerAtEsc(this.state);
        } else if (INPUT_KEYS.has(key)) {
            this._updateBuffer(key);
            if (holder !== this._currentBufferHolder) {
                log.logic(
                    "input callback canceled: holder changed during buffer-update",
                );
                return;
            }
            if (this.config.triggerAtInput) {
                this.config.triggerAtInput({
                    buffer: this.state.buffer,
                    key,
                });
            }
        }
    }
    /**
     * @param {String} input
     */
    _updateBuffer(input) {
        const isEmpty = (val) => val === "" || val === null;
        if (input === undefined || input === null) {
            return;
        }
        const isFirstInput = isEmpty(this.state.buffer);
        if (input === "," || input === ".") {
            if (this.state.toStartOver) {
                this.state.buffer = "";
            }
            if (isFirstInput) {
                this.state.buffer = "0" + this.decimalPoint;
            } else if (!this.state.buffer.length || this.state.buffer === "-") {
                this.state.buffer += "0" + this.decimalPoint;
            } else if (this.state.buffer.indexOf(this.decimalPoint) < 0) {
                this.state.buffer = this.state.buffer + this.decimalPoint;
            }
        } else if (input === "Delete") {
            if (this.isReset) {
                this.state.buffer = "";
                this.isReset = false;
                return;
            }
            this.state.buffer = isEmpty(this.state.buffer) ? null : "";
        } else if (input === "Backspace") {
            if (this.isReset) {
                this.state.buffer = "";
                this.isReset = false;
                return;
            }
            if (this.state.toStartOver) {
                this.state.buffer = "";
            }
            const buffer = this.state.buffer;
            if (isEmpty(buffer)) {
                this.state.buffer = null;
            } else {
                this.state.buffer = buffer.substring(0, buffer.length - 1);
            }
        } else if (input === "+") {
            if (!isFirstInput && this.state.buffer[0] === "-") {
                this.state.buffer = this.state.buffer.substring(
                    1,
                    this.state.buffer.length,
                );
            }
        } else if (input === "-") {
            if (isFirstInput) {
                this.state.buffer = "-0";
            } else if (this.state.buffer[0] === "-") {
                this.state.buffer = this.state.buffer.substring(
                    1,
                    this.state.buffer.length,
                );
            } else {
                this.state.buffer = "-" + this.state.buffer;
            }
        } else if (input[0] === "+" && !isNaN(parseFloat(input))) {
            const inputValue = oParseFloat(input.slice(1));
            const currentBufferValue = this.state.buffer
                ? oParseFloat(this.state.buffer.replace(".", this.decimalPoint))
                : 0;
            this.state.buffer = (inputValue + currentBufferValue)
                .toString()
                .replace(".", this.decimalPoint);
        } else if (!isNaN(parseInt(input, 10))) {
            if (this.state.toStartOver) {
                this.state.buffer = "";
            }
            if (this.state.buffer === this.state.lastSet) {
                this.state.buffer = "";
                this.state.lastSet = false;
            }
            if (isFirstInput) {
                this.state.buffer = "" + input;
            } else if (this.state.buffer.length > 12) {
                this.sound.play("bell");
            } else {
                this.state.buffer += input;
            }
        }
        if (this.state.buffer === "-") {
            this.state.buffer = "";
        }
        this.isReset = false;
        this.state.toStartOver = false;

        this.trigger("buffer-update", this.state.buffer);
    }
}

export const numberBufferService = {
    dependencies: NumberBuffer.serviceDependencies,
    start(env, deps) {
        return new NumberBuffer(deps);
    },
};

registry.category("services").add("number_buffer", numberBufferService);
