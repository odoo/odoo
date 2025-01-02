import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";
import { Thread } from "./thread_model";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 * @property {string} size
 * @property {string} className
 * @extends {Component<Props, Env>}
 */
export class ThreadIcon extends Component {
    static template = "mail.ThreadIcon";
    static props = {
        thread: { type: Thread },
        size: { optional: true, validate: (size) => ["small", "medium", "large"].includes(size) },
        className: { type: String, optional: true },
    };
    static defaultProps = {
        size: "medium",
        className: "",
    };

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }

    get correspondent() {
        return this.props.thread.correspondent;
    }

    get defaultChatIcon() {
        return {
            class: "fa fa-question-circle",
            title: _t("No IM status available"),
        };
    }
}
