// @ts-check
/** @odoo-module native */

import { Component, onWillUnmount, useRef } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { faIconClass } from "@web/core/utils/icons";
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

    /** @type {import("@odoo/owl").Ref<HTMLButtonElement>} */
    button;
    /** @type {any} */
    popover;

    /** @type {number | undefined} */
    tooltipCloseTimer;

    get iconClass() {
        return faIconClass(this.props.icon || "fa-clipboard");
    }

    setup() {
        /** @type {import("@odoo/owl").Ref<HTMLButtonElement>} */
        this.button = useRef("button");
        this.popover = usePopover(Tooltip);
        onWillUnmount(() => browser.clearTimeout(this.tooltipCloseTimer));
    }

    showTooltip() {
        const target = this.button.el;
        if (!target) {
            return;
        }
        this.popover.open(target, {
            tooltip: this.props.successText,
        });
        browser.clearTimeout(this.tooltipCloseTimer);
        this.tooltipCloseTimer = browser.setTimeout(this.popover.close, 800);
    }

    async onClick() {
        let write, content;
        if (typeof this.props.content === "function") {
            content = await this.props.content();
        } else {
            content = this.props.content;
        }
        if (content === undefined || content === null) {
            return;
        }
        if (typeof content === "string" || content instanceof String) {
            write = (/** @type {string} */ value) =>
                browser.navigator.clipboard.writeText(value);
        } else {
            write = (/** @type {ClipboardItems} */ value) =>
                browser.navigator.clipboard.write(value);
        }
        try {
            await write(content);
        } catch (error) {
            return browser.console.warn(error);
        }
        this.showTooltip();
    }
}
