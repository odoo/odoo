/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";

Model({
    name: "ActivityButtonView",
    template: "mail.ActivityButtonView",
    identifyingMode: "xor",
    recordMethods: {
        onClick(ev) {
            if (!this.exists()) {
                return;
            }
            if (this.listFieldActivityViewOwner) {
                ev.stopPropagation(); // prevents list view click that opens form view. TODO use special_click instead?
            }
            this.update({ activityListPopoverView: this.activityListPopoverView ? clear() : {} });
        },
    },
    fields: {
        activityListPopoverView: one("PopoverView", {
            inverse: "activityButtonViewOwnerAsActivityList",
        }),
        buttonClass: attr({
            compute() {
                if (!this.thread) {
                    return clear();
                }
                const classes = [];
                switch (this.webRecord.data.activity_state) {
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
                switch (this.webRecord.data.activity_exception_decoration) {
                    case "warning":
                        classes.push("text-warning");
                        classes.push(this.webRecord.data.activity_exception_icon);
                        break;
                    case "danger":
                        classes.push("text-danger");
                        classes.push(this.webRecord.data.activity_exception_icon);
                        break;
                    default:
                        if (this.webRecord.data.activity_type_icon) {
                            classes.push(this.webRecord.data.activity_type_icon);
                            break;
                        }
                        classes.push("fa-clock-o");
                        break;
                }
                return classes.join(" ");
            },
        }),
        buttonRef: attr({ ref: "button" }),
        kanbanFieldActivityViewOwner: one("KanbanFieldActivityView", {
            identifying: true,
            inverse: "activityButtonView",
        }),
        listFieldActivityViewOwner: one("ListFieldActivityView", {
            identifying: true,
            inverse: "activityButtonView",
        }),
        thread: one("Thread", {
            required: true,
            compute() {
                if (this.kanbanFieldActivityViewOwner) {
                    return this.kanbanFieldActivityViewOwner.thread;
                }
                if (this.listFieldActivityViewOwner) {
                    return this.listFieldActivityViewOwner.thread;
                }
                return clear();
            },
        }),
        webRecord: attr({
            required: true,
            compute() {
                if (this.kanbanFieldActivityViewOwner) {
                    return this.kanbanFieldActivityViewOwner.webRecord;
                }
                if (this.listFieldActivityViewOwner) {
                    return this.listFieldActivityViewOwner.webRecord;
                }
                return clear();
            },
        }),
    },
});
