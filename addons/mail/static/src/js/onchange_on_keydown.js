import { useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { exprToBoolean } from "@web/core/utils/strings";
import { useDebounced } from "@web/core/utils/timing";
import { charField, CharField } from "@web/views/fields/char/char_field";
import { textField, TextField } from "@web/views/fields/text/text_field";

/**
 * Support a key-based onchange in text fields.
 * The triggerOnChange method is debounced to run after given debounce delay
 * (or 2 seconds by default) when typing ends.
 *
 */
const onchangeOnKeydownMixin = () => ({
    setup() {
        super.setup(...arguments);

        if (this.props.onchangeOnKeydown) {
            const input = this.input || this.textareaRef;

            const triggerOnChange = useDebounced(
                this.triggerOnChange,
                this.props.keydownDebounceDelay
            );
            useEffect(() => {
                if (input.el) {
                    input.el.addEventListener("keydown", triggerOnChange);
                    return () => {
                        input.el.removeEventListener("keydown", triggerOnChange);
                    };
                }
            });
        }
    },

    triggerOnChange() {
        const input = this.input || this.textareaRef;
        input.el.dispatchEvent(new Event("change"));
    },
});

patch(CharField.prototype, onchangeOnKeydownMixin());
patch(TextField.prototype, onchangeOnKeydownMixin());

CharField.props = {
    ...CharField.props,
    onchangeOnKeydown: { type: Boolean, optional: true },
    keydownDebounceDelay: { type: Number, optional: true },
};

TextField.props = {
    ...TextField.props,
    onchangeOnKeydown: { type: Boolean, optional: true },
    keydownDebounceDelay: { type: Number, optional: true },
};

const charExtractProps = charField.extractProps;
charField.extractProps = (fieldInfo) => {
    return Object.assign(charExtractProps(fieldInfo), {
        onchangeOnKeydown: exprToBoolean(fieldInfo.attrs.onchange_on_keydown),
        keydownDebounceDelay: fieldInfo.attrs.keydown_debounce_delay
            ? Number(fieldInfo.attrs.keydown_debounce_delay)
            : 2000,
    });
};

const textExtractProps = textField.extractProps;
textField.extractProps = (fieldInfo) => {
    return Object.assign(textExtractProps(fieldInfo), {
        onchangeOnKeydown: exprToBoolean(fieldInfo.attrs.onchange_on_keydown),
        keydownDebounceDelay: fieldInfo.attrs.keydown_debounce_delay
            ? Number(fieldInfo.attrs.keydown_debounce_delay)
            : 2000,
    });
};
