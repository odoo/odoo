import { Component, onWillStart, useState } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { useRecordObserver } from "@web/model/relational_model/utils";

import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AccrualLevels extends Component {
    static template = "hr_holidays.AccrualLevels";
    static props = {
        ...standardFieldProps
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.state = useState({});

        useRecordObserver(async (record) => {
            this.state.carryOverDate = this.getCarryOverDate(record);
            this.state.data = await this.orm.read("hr.leave.accrual.level", record.data[this.props.name]._currentIds);
            if (!this.state.newMilestoneIds.some(id => record.data[this.props.name]._currentIds.includes(id))) {
                this.state.newMilestoneIds = record.data[this.props.name]._currentIds;
            }
        });

        onWillStart(async () => {
            this.state.newMilestoneIds = this.props.record.data[this.props.name]._currentIds;
        });
    }

    get milestones() {
        return this.props.record.data[this.props.name].records.map((record) => ({
            id: record.id,
            resId: record.evalContext.id,
            data: this.state.data.filter((r) => r.id === record.evalContext.id)[0],
            onDelete: () => this.deleteMilestone(record.id),
        }));
    }

    getFullDay(day) {
        return luxon.DateTime.fromFormat(day, "c", {
            locale: this.env.model.config.context.lang.replace("_","-")}).toLocaleString({ weekday: "long" });
    }

    getFullMonth(month) {
        return luxon.DateTime.fromFormat(month, "M", {
            locale: this.env.model.config.context.lang.replace("_","-")}).toLocaleString({ month: "long" });
    }

    getNewMilestoneClass(id){
        return this.state.newMilestoneIds.includes(id) ? "" : "new";
    }

    getCarryOverDate(planRecord) {
        switch (planRecord._values.carryover_date) {
            case "year_start":
                return _t("start of the year");
            case "allocation":
                return _t("allocation date");
            default:
                return luxon.DateTime.fromFormat(
                    `${planRecord._values.carryover_day} ${planRecord._values.carryover_month} 2020`,
                    "d M y",
                    {locale: this.env.model.config.context.lang.replace("_","-")})
                    .toLocaleString({ day:"numeric", month: "long" });
        }
    }

    async openMilestone(id) {
        let action;
        if (id) {
            action = await this.orm.call("hr.leave.accrual.plan", "action_open_accrual_plan_level",
                [this.props.record.evalContext.id], { level_id: id });
        } else {
            action = await this.orm.call("hr.leave.accrual.plan", "action_create_accrual_plan_level",
                [this.props.record.evalContext.id]);
        }
        this.action.doAction(action, {
            additionalContext: {
                active_id: this.props.record.evalContext.id,
            },
            onClose: () => this.env.model.root.load(),
        });
    }

    deleteMilestone(id) {
        const milestoneRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === id
        );
        this.props.record.data[this.props.name].delete(milestoneRecord);
    }

    async editMilestone(id){
        if (this.props.record.dirty) {
            this.dialog.add(ConfirmationDialog, {
                body: id ?
                    _t("Do you want to save the changes made to the accrual plan before editing this milestone?") :
                    _t("Do you want to save the changes made to the accrual plan before creating a new milestone?"),
                confirmLabel: _t("Yes, save changes"),
                cancelLabel: _t("No, keep the old version"),
                cancel: async () => await this.openMilestone(id),
                confirm: async () => {
                    await this.props.record.save({ reload: false });
                    await this.openMilestone(id);
                },
            });
        } else {
            await this.openMilestone(id);
        }
    }
}

export const accrualLevels = {
    component: AccrualLevels,
    fieldDependencies: [
        { name: "carryover_day", type: "integer" }
    ],
    relatedFields: () => [{ name: "id", type: "integer" }],
};

registry.category("fields").add("accrual_levels", accrualLevels);
