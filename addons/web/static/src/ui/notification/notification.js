// @ts-check

/** @module @web/ui/notification/notification - Individual notification toast with auto-close progress bar and action buttons */

import { Component, onMounted, useRef } from "@odoo/owl";

const AUTOCLOSE_DELAY = 4000;

/**
 * Individual notification toast with auto-close progress bar.
 *
 * Supports warning/danger/success/info types, sticky mode,
 * configurable autoclose delay, and action buttons.
 */
export class Notification extends Component {
    static template = "web.NotificationWowl";
    static props = {
        message: {
            validate: (m) =>
                typeof m === "string" ||
                (typeof m === "object" && typeof m.toString === "function"),
        },
        type: {
            type: String,
            optional: true,
            validate: (t) => ["warning", "danger", "success", "info"].includes(t),
        },
        title: {
            type: [String, Boolean, { toString: Function }],
            optional: true,
        },
        className: { type: String, optional: true },
        buttons: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    name: { type: String },
                    icon: { type: String, optional: true },
                    primary: { type: Boolean, optional: true },
                    onClick: Function,
                },
            },
            optional: true,
        },
        sticky: { type: Boolean, optional: true },
        autocloseDelay: { type: Number, optional: true },
        close: { type: Function },
    };
    static defaultProps = {
        buttons: [],
        className: "",
        type: "warning",
        autocloseDelay: AUTOCLOSE_DELAY,
    };
    setup() {
        this.autocloseProgress = useRef("autoclose_progress_bar");
        onMounted(() => this.startNotificationTimer());
    }

    /** Pause the auto-close timer (e.g. on mouse hover). */
    freeze() {
        this.startedTimestamp = false;
        this.autocloseProgress.el.style.width = "0";
    }

    /** Restart the auto-close timer from the beginning. */
    refresh() {
        this.startNotificationTimer();
    }

    close() {
        this.props.close();
    }

    startNotificationTimer() {
        if (this.props.sticky) {
            return;
        }
        this.startedTimestamp = luxon.DateTime.now().toMillis();

        const cb = () => {
            if (this.startedTimestamp) {
                const currentProgress =
                    (luxon.DateTime.now().toMillis() -
                        /** @type {number} */ (this.startedTimestamp)) /
                    this.props.autocloseDelay;
                if (currentProgress > 1) {
                    this.close();
                    return;
                }
                if (this.autocloseProgress.el) {
                    this.autocloseProgress.el.style.width = `${(1 - currentProgress) * 100}%`;
                }
                requestAnimationFrame(cb);
            }
        };
        cb();
    }
}
