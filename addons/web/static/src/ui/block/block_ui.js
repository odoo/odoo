// @ts-check

/** @module @web/ui/block/block_ui - Full-screen overlay component that blocks UI during long-running operations */

import { Component, EventBus, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
/**
 * Full-screen overlay that blocks UI interaction during long-running operations.
 *
 * Listens to BLOCK/UNBLOCK events on its bus prop. Displays progressively
 * more encouraging messages as the user waits.
 */
export class BlockUI extends Component {
    static props = {
        bus: EventBus,
    };

    static template = "web.BlockUI";

    setup() {
        this.messagesByDuration = [
            { time: 20, l1: _t("Loading...") },
            { time: 40, l1: _t("Still loading...") },
            {
                time: 60,
                l1: _t("Still loading..."),
                l2: _t("Please be patient."),
            },
            {
                time: 180,
                l1: _t("Don't leave yet,"),
                l2: _t("it's still loading..."),
            },
            {
                time: 120,
                l1: _t("You may not believe it,"),
                l2: _t("but the application is actually loading..."),
            },
            {
                time: 3180,
                l1: _t("Take a minute to get a coffee,"),
                l2: _t("because it's loading..."),
            },
            {
                time: null,
                l1: _t(
                    "Maybe you should consider reloading the application by pressing F5...",
                ),
            },
        ];
        this.BLOCK_STATES = { UNBLOCKED: 0, BLOCKED: 1, VISIBLY_BLOCKED: 2 };
        this.state = useState({
            blockState: this.BLOCK_STATES.UNBLOCKED,
            line1: "",
            line2: "",
        });

        this.props.bus.addEventListener("BLOCK", this.block.bind(this));
        this.props.bus.addEventListener("UNBLOCK", this.unblock.bind(this));
    }

    /** @param {number} index - message index in `messagesByDuration` */
    replaceMessage(index) {
        const message = this.messagesByDuration[index];
        this.state.line1 = message.l1;
        this.state.line2 = message.l2 || "";
        if (message.time !== null) {
            this.msgTimer = browser.setTimeout(() => {
                this.replaceMessage(index + 1);
            }, message.time * 1000);
        }
    }

    /** @param {{ detail?: { delay?: number, message?: string } }} ev */
    block(ev) {
        const showBlockedUI = () =>
            (this.state.blockState = this.BLOCK_STATES.VISIBLY_BLOCKED);
        const delay = ev.detail?.delay;
        if (delay) {
            this.state.blockState = this.BLOCK_STATES.BLOCKED;
            this.showBlockedUITimer = setTimeout(showBlockedUI, delay);
        } else {
            showBlockedUI();
        }

        if (ev.detail?.message) {
            this.state.line1 = ev.detail.message;
        } else {
            this.replaceMessage(0);
        }
    }

    /** Reset state and clear all pending timers. */
    unblock() {
        this.state.blockState = this.BLOCK_STATES.UNBLOCKED;
        clearTimeout(this.showBlockedUITimer);
        clearTimeout(this.msgTimer);
        this.state.line1 = "";
        this.state.line2 = "";
    }
}
