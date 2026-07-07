import { useEnv } from "@web/owl2/utils";
import { ActivityListPopover } from "@mail/core/web/activity_list_popover";
import { propComputed } from "@mail/utils/common/hooks";

import { Component, signal, t } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { Record } from "@web/model/relational_model/record";

export class ActivityButton extends Component {
    static template = "mail.ActivityButton";

    buttonRef = signal.ref();

    setup() {
        super.setup();
        this.record = propComputed("record", t.instanceOf(Record));
        this.popover = usePopover(ActivityListPopover, { position: "bottom-start" });
        this.env = useEnv();
        this.defaultActivityStateClass = "text-muted";
        this.defaultActivityDecorationClass = "btn-link text-dark";
    }

    get buttonClass() {
        const classes = [];
        const { activity_ids, activity_state, activity_exception_decoration } = this.record().data;
        if (activity_ids.records.length) {
            classes.push("oi-filled");
        }
        switch (activity_state) {
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
                if (this.defaultActivityStateClass) {
                    classes.push(this.activityStateClass);
                }
                break;
        }
        switch (activity_exception_decoration) {
            case "warning":
                classes.push("text-warning");
                break;
            case "danger":
                classes.push("text-danger");
                break;
            default: {
                if (!activity_ids.records.length) {
                    classes.push(this.defaultActivityDecorationClass);
                }
                break;
            }
        }
        return classes.join(" ");
    }

    get buttonIcon() {
        const { activity_ids, activity_type_icon } = this.record().data;
        if (activity_ids.records.length) {
            return activity_type_icon || "checklist";
        } else {
            return "schedule";
        }
    }

    get title() {
        if (this.record().data.activity_exception_decoration) {
            return _t("Warning");
        }
        if (this.record().data.activity_summary) {
            return this.record().data.activity_summary;
        }
        if (this.record().data.activity_type_id) {
            return this.record().data.activity_type_id.display_name;
        }
        return _t("Show activities");
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ recordAtRender: import("@web/model/relational_model/record").Record }} param1
     */
    async onClick(ev, { recordAtRender }) {
        if (this.popover.isOpen) {
            this.popover.close();
        } else {
            const resId = recordAtRender.resId;
            const selectedRecords = this.env?.model?.root?.selection ?? [];
            const selectedIds = selectedRecords.map((r) => r.resId);
            // If the current record is not selected, ignore the selection
            const resIds =
                selectedIds.includes(resId) && selectedIds.length > 1 ? selectedIds : undefined;
            this.popover.open(this.buttonRef(), {
                activityIds: recordAtRender.data.activity_ids.currentIds,
                /** @type {ReturnType<typeof import("@mail/core/web/activity_types").onActivityChangedType>["type"]} */
                onActivityChanged: ({ thread } = {}) => {
                    const recordToLoad = resIds ? selectedRecords : [recordAtRender];
                    recordToLoad.forEach((r) => r.load());
                    this.onActivityChanged({ thread });
                    this.popover.close();
                },
                resId,
                resIds,
                resModel: recordAtRender.resModel,
            });
        }
    }

    /** @type {ReturnType<typeof import("@mail/core/web/activity_types").onActivityChangedType>["type"]} */
    onActivityChanged({ thread }) {}
}
