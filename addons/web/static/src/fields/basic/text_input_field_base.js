// @ts-check

/** @module @web/fields/basic/text_input_field_base - Abstract base class for text input fields with translation and dynamic placeholder support */

import { Component } from "@odoo/owl";

/**
 * Base class for text input fields (char, text/textarea, etc.).
 *
 * Provides shared infrastructure: isTranslatable getter, dynamic-placeholder
 * open/validate handlers using this.inputEl as the target element.
 *
 * Subclasses must implement:
 *   - get inputEl — returns the native input/textarea DOM element
 */
export class TextInputFieldBase extends Component {
    /** @abstract — override to return the native input/textarea element */
    get inputEl() {
        return null;
    }

    /** @returns {boolean} Whether this field supports translations */
    get isTranslatable() {
        return this.props.record.fields[this.props.name].translate;
    }

    async onDynamicPlaceholderOpen() {
        await /** @type {any} */ (this).dynamicPlaceholder.open({
            validateCallback: this.onDynamicPlaceholderValidate.bind(this),
        });
    }

    /**
     * @param {string} chain - Dynamic placeholder field chain (e.g. "partner_id.name")
     * @param {string} [defaultValue] - Fallback value when the placeholder resolves to empty
     */
    async onDynamicPlaceholderValidate(chain, defaultValue) {
        if (chain) {
            const el = this.inputEl;
            el.focus();
            const dynamicPlaceholder = ` {{object.${chain}${
                defaultValue?.length ? ` ||| ${defaultValue}` : ""
            }}}`;
            el.setRangeText(
                dynamicPlaceholder,
                /** @type {any} */ (this).selectionStart,
                /** @type {any} */ (this).selectionStart,
                "end",
            );
            // trigger events to make the field dirty
            el.dispatchEvent(new InputEvent("input"));
            el.dispatchEvent(new KeyboardEvent("keydown"));
            el.focus();
        }
    }
}
