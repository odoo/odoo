import { makeContext } from "@web/core/context";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useX2ManyCrud, useOpenX2ManyRecord } from "@web/views/fields/relational_utils";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { CommonSkillsListRenderer } from "../../views/skills_list_renderer";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

export class SkillsListRenderer extends CommonSkillsListRenderer {
    static template = "hr_skills.SkillsListRenderer";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");

        onWillStart(async () => {
            const res = await this.orm.searchCount("hr.skill.type", []);
            this.anySkills = res > 0;
            [this.user] = await this.orm.read("res.users", [user.userId], ["employee_ids"]);
            this.IsHrUser = await user.hasGroup("hr.group_hr_user");
            this.userSubordinates = (
                await this.orm.searchRead(
                    "hr.employee",
                    [["id", "child_of", this.user.employee_ids]],
                    ["id"]
                )
            ).map((record) => record["id"]);
        });
    }

    get groupBy() {
        return "skill_type_id";
    }

    async skillTypesAction() {
        return this.actionService.doAction("hr_skills.hr_skill_type_action");
    }

    async openSkillsReport() {
        // fetch id through employee or public.employee
        const id = this.env.model.root.data.id || this.env.model.root.data.employee_id[0];
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Skills Report"),
            res_model: "hr.employee.skill.log",
            view_mode: "graph,list",
            views: [
                [false, "graph"],
                [false, "list"],
            ],
            context: {
                fill_temporal: 0,
            },
            target: "current",
            domain: [["employee_id", "=", id]],
        });
    }

    get showTimeline() {
        return this.SkillsRight && !this.props.list.context.no_timeline;
    }

    get SkillsRight() {
        let isSubordinate = false;
        if (this.env.model.root.data.employee_id) {
            isSubordinate = this.userSubordinates.includes(this.env.model.root.data.employee_id[0]);
        }
        return this.IsHrUser || isSubordinate;
    }
}

export class SkillsX2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: SkillsListRenderer,
    };
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");

        const { saveRecord, updateRecord } = useX2ManyCrud(() => this.list, this.isMany2Many);

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: async (record) => {
                await saveRecord(record);
                await this.props.record.save();
            },
            updateRecord: async (record) => {
                await updateRecord(record);
                await this.props.record.save();
            },
            withParentId: this.props.widget !== "many2many",
        });

        this._openRecord = (params) => {
            // this.openSkillWizard(params);
            openRecord({ ...params });
        };
    }

    getWizardTitleName() {
        return _t("Select Skills");
    }

    async onAdd({ context, editable } = {}) {
        const employeeId =
            this.props.record.resModel === "res.users"
                ? this.props.record.data.employee_id[0]
                : this.props.record.resId;

        context = makeContext([this.props.context, context]);
        context = { ...context, default_employee_id: employeeId };
        // We remove the this.isMany2Many check to prevent the list view from being opened

        if (editable) {
            const editedRecord = this.list.editedRecord;
            if (editedRecord) {
                const proms = [];
                this.list.model.bus.trigger("NEED_LOCAL_CHANGES", { proms });
                await Promise.all([...proms, editedRecord._updatePromise]);
                await this.list.leaveEditMode({ canAbandon: false });
            }
            if (!this.list.editedRecord) {
                return this.addInLine({ context, editable });
            }
            return;
        }
        return this._openRecord({ context });
    }
}

export const skillsX2ManyField = {
    ...x2ManyField,
    component: SkillsX2ManyField,
};

registry.category("fields").add("skills_one2many", skillsX2ManyField);
