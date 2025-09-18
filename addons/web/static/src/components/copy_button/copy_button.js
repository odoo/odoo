// @ts-check

/** @module @web/components/copy_button/copy_button - Clipboard copy button with success tooltip feedback */

import { Component, useRef } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { usePopover } from "@web/ui/popover/popover_hook";
import { Tooltip } from "@web/ui/tooltip/tooltip";

export class CopyButton extends Component {
    static template = "web.CopyButton";
    static props = {
        className: { type: String, optional: true },
        copyText: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        successText: { type: String, optional: true },
        icon: { type: String, optional: true },
        content: { type: [String, Object, Function], optional: true },
    };

    setup() {
        /** @type {import("@odoo/owl").Ref<HTMLButtonElement>} */
        this.button = useRef("button");
        this.popover = usePopover(Tooltip);
    }

    /** Show a temporary success tooltip on the button for 800ms. */
    showTooltip() {
        this.popover.open(this.button.el, { tooltip: this.props.successText });
        browser.setTimeout(this.popover.close, 800);
    }

    /** Copy content to the clipboard, resolving function props if needed. */
    async onClick() {
        let write, content;
        if (typeof this.props.content === "function") {
            content = this.props.content();
        } else {
            content = this.props.content;
        }
        // any kind of content can be copied into the clipboard using
        // the appropriate native methods
        if (typeof content === "string" || content instanceof String) {
            write = (value) => browser.navigator.clipboard.writeText(value);
        } else {
            write = (value) => browser.navigator.clipboard.write(value);
        }
        try {
            await write(content);
        } catch (error) {
            return browser.console.warn(error);
        }
        this.showTooltip();
    }
}
