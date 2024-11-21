import { onWillDestroy, useComponent } from "@odoo/owl";
import { registry } from "@web/core/registry";

const isFloat = (n) => n % 1 !== 0;
const { DateTime } = luxon;
const symbolMap = {
    "+": (a, b) => a + b,
    "-": (a, b) => a - b,
    "*": (a, b) => a * b,
    "/": (a, b) => a / b,
};

class BufferService {
    static serviceDependencies = ["localization", "barcode_reader"];

    constructor(args) {
        this.setup(args);
    }

    setup({ localization, barcode_reader }) {
        this.decimalPoint = localization.decimalPoint;
        this.callback = null;
        this.barcode = null;
        this.barcodeReader = barcode_reader;
        this.barcodeTimout = this.barcodeReader.maxTimeBetweenKeysInMs;
        this.timeout = {
            barcode: null,
            callback: null,
        };

        this.state = {
            stack: [],
            keypressTs: DateTime.now().toMillis(),
            isNegative: false,
            // use to handle if we are after float and the gap of 0 in case of .00X
            float: {
                status: false,
                gap: 0,
            },
            // Start value in case of use of +XX buttons, value is the current value
            buffer: {
                value: 0,
                symbolStart: 0,
            },
        };

        window.addEventListener("keyup", this.handleKeyboardEvent.bind(this));
    }

    get isReset() {
        return this.state.buffer.value === 0;
    }

    get buffer() {
        return this.state.buffer.value;
    }

    get holder() {
        return this.state.stack[this.state.stack.length - 1];
    }

    // Call the barcode scan method if keypress interval is less than 50ms
    handleCallback() {
        const currentTime = new Date().getTime();
        const timeout = this.useBarcode ? this.barcodeTimout : 0;

        if (this.state.lastKeypressTime && currentTime - this.state.lastKeypressTime < 50) {
            clearTimeout(this.timeout.barcode);
            clearTimeout(this.timeout.callback);

            this.timeout.barcode = setTimeout(() => {
                this.barcodeReader.scan(this.state.buffer.value.toString());
                this.reset();
            }, timeout);
        } else {
            clearTimeout(this.timeout.callback);

            this.timeout.callback = setTimeout(() => {
                this.callback && this.callback(this.state.buffer.value);
            }, timeout);
        }

        this.state.lastKeypressTime = currentTime;
    }

    set({ value = 0, symbolStart = 0 }) {
        this.state.buffer.value = !isNaN(parseFloat(value)) ? parseFloat(value) : 0;
        this.state.buffer.symbolStart = !isNaN(parseFloat(symbolStart))
            ? parseFloat(symbolStart)
            : 0;
    }

    reset() {
        this.state.float = { status: false, gap: 0 };
        this.state.isNegative = false;
        this.state.buffer.value = 0;
        this.state.buffer.symbolStart = 0;
        this.state.keypressTs = DateTime.now().toMillis();
    }

    use(config) {
        const currentComponent = useComponent();
        this.state.stack.push({
            component: currentComponent,
            buffer: Object.assign({ value: 0, symbolStart: 0 }, config.buffer || {}),
            callback: config.callback || null,
            useBarcode: config.useBarcode || false,
        });
        this.changeHolder();

        onWillDestroy(() => {
            const currentComponentName = currentComponent.constructor.name;
            const indexComponent = this.state.stack.findIndex(
                (stack) => stack.component.constructor.name === currentComponentName
            );
            this.state.stack.splice(indexComponent, 1);
            this.changeHolder();
        });
    }

    changeHolder() {
        const holder = this.holder;

        if (!holder) {
            return;
        }

        this.useBarcode = holder.useBarcode || false;
        this.callback = holder.callback || null;
        this.state.buffer = Object.assign({ value: 0, symbolStart: 0 }, holder.buffer || {});
        this.state.float.value = isFloat(this.state.buffer.value);
        this.state.isNegative = this.state.buffer.value < 0;
    }

    handleKeyboardEvent(event) {
        if (["INPUT", "TEXTAREA"].includes(event.target.tagName)) {
            return;
        }

        if (isNaN(parseInt(event.key, 10)) && !["Backspace", "Delete"].includes(event.key)) {
            return;
        }

        this.handleMethodInput({ key: event.key, value: event.key });
    }

    handleMethodInput(options = { key: null, value: 0, symbol: null }) {
        const { key, value, symbol } = options;
        const buffer = this.state.buffer;
        const state = this.state;

        if (key === "Backspace") {
            buffer.value = parseFloat(buffer.value.toString().slice(0, -1)) || 0;
            state.float.status = isFloat(buffer.value);
            this.handleCallback();
            return;
        }

        if (key === "-") {
            state.isNegative = !state.isNegative;
            buffer.value *= -1;
            buffer.value !== 0 && this.handleCallback();
            return;
        }

        if (key === this.decimalPoint) {
            state.float.status = true;
            buffer.value !== 0 && this.handleCallback();
            return;
        }

        if (key === "Delete") {
            this.reset();
            this.handleCallback();
            return;
        }

        if (symbol in symbolMap) {
            const initValue = buffer.value !== 0 ? buffer.value : buffer.symbolStart;
            buffer.value = symbolMap[symbol](parseFloat(initValue), parseFloat(value));
            this.handleCallback();
            return;
        }

        if (!symbol && !isNaN(value)) {
            if (state.float.status && value === "0") {
                state.float.gap++;
                return;
            } else if (state.float.status && value !== "0") {
                buffer.value = parseFloat(
                    buffer.value + this.decimalPoint + "0".repeat(state.float.gap) + value
                );
                state.float.gap = 0;
                state.float.status = false;
            } else {
                buffer.value = parseFloat(buffer.value.toString() + value);
            }

            if (state.isNegative && buffer.value > 0) {
                buffer.value *= -1;
            }

            this.handleCallback();
            return;
        }
    }
}

export const bufferService = {
    dependencies: BufferService.serviceDependencies,
    start(env, deps) {
        return new BufferService(deps);
    },
};

registry.category("services").add("buffer_service", bufferService);
