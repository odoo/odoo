/** @odoo-module */

import { Component, props, signal, types as t, xml } from "@odoo/owl";
import { copy, hasClipboard } from "../hoot_utils";

export class HootCopyButton extends Component {
    static template = xml`
        <t t-if="this.hasClipboard()">
            <button
                type="button"
                class="text-gray-400 hover:text-gray-500"
                t-att-class="{ 'text-emerald': this.copied() }"
                title="copy to clipboard"
                t-on-click.stop="this.onClick"
            >
                <i class="fa fa-clipboard" />
            </button>
        </t>
    `;

    // Props & plugins
    props = props({
        "altText?": t.string(),
        text: t.string(),
    });

    // Reactive values
    copied = signal(false, { type: t.boolean() });

    // Other members
    hasClipboard = hasClipboard;

    /**
     * @param {PointerEvent} ev
     */
    async onClick(ev) {
        const text = ev.altKey && this.props.altText ? this.props.altText : this.props.text;
        await copy(text);
        this.copied.set(true);
    }
}
