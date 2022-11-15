/** @odoo-module **/

import { ActivityMarkAsDone } from "@mail/new/activity/activity_markasdone_popover";

import { auto_str_to_date } from "web.time";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";

import { Component, useState } from "@odoo/owl";

export class ActivityListPopoverItem extends Component {
    setup() {
        this.user = useService("user");
        this.state = useState({ hasMarkDoneView: false });
        this.closeMarkAsDone = this.closeMarkAsDone.bind(this);
    }

    closeMarkAsDone() {
        this.state.hasMarkDoneView = false;
    }

    get delayLabel() {
        // TODO recompute every minute
        const today = moment().startOf("day");
        const momentDeadlineDate = moment(auto_str_to_date(this.props.activity.date_deadline));
        // true means no rounding
        const diff = momentDeadlineDate.diff(today, "days", true);
        if (diff === 0) {
            return this.env._t("Today");
        } else if (diff === -1) {
            return this.env._t("Yesterday");
        } else if (diff < 0) {
            return sprintf(this.env._t("%s days overdue"), Math.round(Math.abs(diff)));
        } else if (diff === 1) {
            return this.env._t("Tomorrow");
        } else {
            return sprintf(this.env._t("Due in %s days"), Math.round(Math.abs(diff)));
        }
    }

    get hasEditButton() {
        return this.props.activity.chaining_type === "suggest" && this.props.activity.can_write;
    }

    get hasFileUploader() {
        return this.props.activity.activity_category === "upload_file";
    }

    get hasMarkDoneButton() {
        return !this.hasFileUploader;
    }

    onClickEditActivityButton() {
        this.props.onClickEditActivityButton();
        this.env.services["mail.activity"]
            .scheduleActivity(
                this.props.activity.res_model,
                this.props.activity.res_id,
                this.props.activity.id
            )
            .then(() => this.props.onActivityChanged());
    }

    onClickMarkAsDone() {
        this.state.hasMarkDoneView = !this.state.hasMarkDoneView;
    }

    onClickUploadDocument() {
        // todo open file uploader
    }
}

Object.assign(ActivityListPopoverItem, {
    components: { ActivityMarkAsDone },
    props: [
        "activity",
        "onActivityChanged",
        "onClickDoneAndScheduleNext?",
        "onClickEditActivityButton",
    ],
    template: "mail.ActivityListPopoverItem",
});
