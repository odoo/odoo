import { Component, onMounted, proxy, signal, useProps, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import {
    Numpad,
    BACKSPACE,
    ZERO,
    EMPTY,
    getButtons,
} from "@point_of_sale/app/components/numpad/numpad";
import { _t } from "@web/core/l10n/translation";

export const UNIQUE_CODE_LENGTH = 5;

export class UniqueCodePopup extends Component {
    static template = "pos_unique_code.UniqueCodePopup";
    static components = { Dialog, Numpad };
    props = useProps({
        // Async, resolves to { success, message } as returned by pos.unique.code.consume_code
        consume: t.function(),
        allowForce: t.boolean().optional(false),
        getPayload: t.function(),
        close: t.function(),
    });

    // A real input holds the focus, so the code can be typed on a keyboard. It also keeps the
    // keystrokes away from the barcode reader and from the number buffer of the screen behind,
    // both of which ignore events coming from an <input>.
    inputRef = signal.ref();

    setup() {
        this.state = proxy({
            code: "",
            loading: false,
            error: "",
            shake: false,
        });
        onMounted(() => this.focusInput());
    }

    get title() {
        return _t("Enter your order code");
    }

    get buttons() {
        return getButtons([{ ...EMPTY, disabled: true }, ZERO, BACKSPACE]);
    }

    get isComplete() {
        return this.state.code.length === UNIQUE_CODE_LENGTH;
    }

    // The code is displayed as one box per digit, empty boxes included.
    get digits() {
        return Array.from({ length: UNIQUE_CODE_LENGTH }, (_, i) => this.state.code[i] || "");
    }

    focusInput() {
        this.inputRef()?.focus();
    }

    setCode(code) {
        this.state.code = code;
        const input = this.inputRef();
        if (input && input.value !== code) {
            input.value = code;
        }
    }

    onInput(ev) {
        const typed = ev.target.value.replace(/\D/g, "");
        // A rejected code stays on screen in red: the next keystroke starts a fresh one.
        const code = this.state.error ? typed.slice(-1) : typed;
        this.state.error = "";
        this.setCode(code.slice(0, UNIQUE_CODE_LENGTH));
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.confirm();
        }
    }

    onNumpadClick(value) {
        if (this.state.loading) {
            return;
        }
        const current = this.state.error ? "" : this.state.code;
        this.state.error = "";
        if (value === "Backspace") {
            this.setCode(current.slice(0, -1));
        } else if (current.length < UNIQUE_CODE_LENGTH) {
            this.setCode(current + value);
        }
        this.focusInput();
    }

    reject(message) {
        this.state.error = message;
        this.state.shake = true;
        this.focusInput();
    }

    async confirm() {
        if (!this.isComplete || this.state.loading) {
            return;
        }
        this.state.loading = true;
        let result;
        try {
            result = await this.props.consume(this.state.code);
        } finally {
            this.state.loading = false;
        }

        if (!result?.success) {
            this.reject(result?.message || _t("This code can't be used. Please try another one."));
            return;
        }
        this.props.getPayload({ forced: false, code: this.state.code });
        this.props.close();
    }

    // Escape hatch for the cashier when a customer has no working code.
    forceValidate() {
        this.props.getPayload({ forced: true, code: "" });
        this.props.close();
    }
}
