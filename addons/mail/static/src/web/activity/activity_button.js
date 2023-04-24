/* @odoo-module */

import { ActivityListPopover } from "@mail/web/activity/activity_list_popover";

import { _t } from "@web/core/l10n/translation";

import { usePopover } from "@web/core/popover/popover_hook";

import { Component, useRef } from "@odoo/owl";

export class ActivityButton extends Component {
    static props = ["record"];
    static template = "mail.ActivityButton";

    setup() {
        this.popover = usePopover(ActivityListPopover, { position: "bottom-start" });
        this.buttonRef = useRef("button");
    }

    get buttonClass() {
        const classes = [];
        switch (this.props.record.data.activity_state) {
            case "overdue":
                classes.push("text-danger");
                break;
            case "today":
                classes.push("text-warning");
                break;
            case "planned":
                classes.push("text-success");
                break;
            default:
                classes.push("text-muted");
                break;
        }
        switch (this.props.record.data.activity_exception_decoration) {
            case "warning":
                classes.push("text-warning");
                classes.push(this.props.record.data.activity_exception_icon);
                break;
            case "danger":
                classes.push("text-danger");
                classes.push(this.props.record.data.activity_exception_icon);
                break;
            default:
                if (this.props.record.data.activity_type_icon) {
                    classes.push(this.props.record.data.activity_type_icon);
                    break;
                }
                classes.push("fa-clock-o");
                break;
        }
        return classes.join(" ");
    }

    get title() {
        if (this.props.record.data.activity_exception_decoration) {
            return _t("Warning");
        }
        if (this.props.record.data.activity_summary) {
            return this.props.record.data.activity_summary;
        }
        if (this.props.record.data.activity_type_id) {
            return this.props.record.data.activity_type_id[1 /* display_name */];
        }
        return _t("Show activities");
    }

    onClick() {
        if (this.popover.isOpen) {
            this.popover.close();
        } else {
            this.popover.open(this.buttonRef.el, {
                activityIds: this.props.record.data.activity_ids.currentIds,
                onActivityChanged: () => {
                    this.props.record.model.load({ resId: this.props.record.resId });
                },
                resId: this.props.record.resId,
                resModel: this.props.record.resModel,
            });
        }
    }
}
