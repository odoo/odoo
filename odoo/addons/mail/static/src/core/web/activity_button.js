/* @odoo-module */

import { ActivityListPopover } from "@mail/core/web/activity_list_popover";

import { Component, useEnv, useRef } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

export class ActivityButton extends Component {
    static props = {
        record: { type: Object },
    };
    static template = "mail.ActivityButton";

    setup() {
        this.popover = usePopover(ActivityListPopover, { position: "bottom-start" });
        this.buttonRef = useRef("button");
        this.env = useEnv();
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
            default: {
                const { activity_ids, activity_type_icon } = this.props.record.data;
                if (activity_ids.records.length) {
                    classes.push(activity_type_icon || "fa-tasks");
                    break;
                }
                classes.push("fa-clock-o btn-link text-dark");
                break;
            }
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

    async onClick() {
        if (this.popover.isOpen) {
            this.popover.close();
        } else {
            const resId = this.props.record.resId;
            const selectedRecords = this.env?.model?.root?.selection ?? [];
            const selectedIds = selectedRecords.map((r) => r.resId);
            // If the current record is not selected, ignore the selection
            const resIds =
                selectedIds.includes(resId) && selectedIds.length > 1 ? selectedIds : undefined;
            this.popover.open(this.buttonRef.el, {
                activityIds: this.props.record.data.activity_ids.currentIds,
                onActivityChanged: () => {
                    const recordToLoad = resIds ? selectedRecords : [this.props.record];
                    recordToLoad.forEach((r) => r.load());
                    this.popover.close();
                },
                resId,
                resIds,
                resModel: this.props.record.resModel,
            });
        }
    }
}
