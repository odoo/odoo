/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { copy } from "../hoot_utils";

/**
 * @typedef {{
 *  altText?: string;
 *  text: string;
 * }} HootCopyButtonProps
 */

/** @extends {Component<HootCopyButtonProps, import("../hoot").Environment>} */
export class HootCopyButton extends Component {
    static props = {
        altText: { type: String, optional: true },
        text: String,
    };

    static template = xml`
        <button
            type="button"
            class="text-gray-400 hover:text-gray-500"
            t-att-class="{ 'text-pass': state.copied }"
            title="copy to clipboard"
            t-on-click="onClick"
        >
            <i class="fa fa-clipboard" />
        </button>
    `;

    setup() {
        this.state = useState({ copied: false });
    }

    /**
     * @param {PointerEvent} ev
     */
    async onClick(ev) {
        const text = ev.altKey && this.props.altText ? this.props.altText : this.props.text;
        await copy(text);
        this.state.copied = true;
    }
}
