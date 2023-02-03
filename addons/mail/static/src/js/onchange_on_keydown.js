/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { TextField, textField } from "@web/views/fields/text/text_field";
import { archParseBoolean } from "@web/views/utils";

const { useEffect } = owl;

/**
 * Support a key-based onchange in text fields.
 * The triggerOnChange method is debounced to run after given debounce delay
 * (or 2 seconds by default) when typing ends.
 *
 */
const onchangeOnKeydownMixin = {
    setup() {
        this._super(...arguments);

        if (this.props.onchangeOnKeydown) {
            const input = this.input || this.textareaRef;

            const triggerOnChange = debounce(this.triggerOnChange, this.props.keydownDebounceDelay);
            useEffect(() => {
                if (input.el) {
                    input.el.addEventListener("keydown", triggerOnChange.bind(this));
                }
            });
        }
    },

    triggerOnChange() {
        const input = this.input || this.textareaRef;
        input.el.dispatchEvent(new Event("change"));
    },
};

patch(CharField.prototype, "char_field_onchange_on_keydown", onchangeOnKeydownMixin);
patch(TextField.prototype, "text_field_onchange_on_keydown", onchangeOnKeydownMixin);

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
charField.extractProps = (attrs) => {
    return Object.assign(charExtractProps(attrs), {
        onchangeOnKeydown: archParseBoolean(attrs.onchange_on_keydown),
        keydownDebounceDelay: attrs.keydown_debounce_delay
            ? Number(attrs.keydown_debounce_delay)
            : 2000,
    });
};

const textExtractProps = textField.extractProps;
textField.extractProps = (params) => {
    return Object.assign(textExtractProps(params), {
        onchangeOnKeydown: archParseBoolean(params.attrs.onchange_on_keydown),
        keydownDebounceDelay: params.attrs.keydown_debounce_delay
            ? Number(params.attrs.keydown_debounce_delay)
            : 2000,
    });
};
