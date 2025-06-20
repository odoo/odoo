import { Component, useRef } from "@odoo/owl";
import { browser } from "../browser/browser";

const AUTOCLOSE_DELAY = 4000;

export class Notification extends Component {
    static template = "web.NotificationWowl";
    static props = {
        message: {
            validate: (m) => {
                return (
                    typeof m === "string" ||
                    (typeof m === "object" && typeof m.toString === "function")
                );
            },
        },
        title: { type: [String, Boolean, { toString: Function }], optional: true },
        type: {
            type: String,
            optional: true,
            validate: (t) => ["warning", "danger", "success", "info"].includes(t),
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
        this.startNotificationTimer();
    }

    freeze () {
        browser.clearTimeout(this.timeout);
        browser.clearInterval(this.intervalId);
        this.autocloseProgress.el.style.width = 0;
    }

    refresh() {
        this.startNotificationTimer();
    }

    close() {
        browser.clearTimeout(this.timeout);
        browser.clearInterval(this.intervalId);
        this.props.close();
    }

    startNotificationTimer() {
        if (this.props.autocloseDelay === 0) {
            return
        }

        this.autocloseDelay = this.props.autocloseDelay;
        this.intervalId = browser.setInterval(() => {
            this.autocloseDelay -= 11;
            if (this.autocloseProgress.el) {
                this.autocloseProgress.el.style.width = `${(this.autocloseDelay / this.props.autocloseDelay) * 100}%`;
            }
        }, 10)
        this.timeout = browser.setTimeout(() => {
            this.close();
        }, this.props.autocloseDelay);
    }
}
