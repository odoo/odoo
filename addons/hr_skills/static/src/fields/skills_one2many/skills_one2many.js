import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useX2ManyCrud, useOpenX2ManyRecord } from "@web/views/fields/relational_utils";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { CommonSkillsListRenderer } from "../../views/skills_list_renderer";
import { useService } from '@web/core/utils/hooks';
import { onWillStart } from "@odoo/owl";


export class SkillsListRenderer extends CommonSkillsListRenderer {
    static template = "hr_skills.SkillsListRenderer";
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService("action");

        onWillStart(async () => {
            const companyId = user.activeCompany.id;
            const skillTypes = await this.orm.searchRead(
                'hr.skill.type',
                ['|', ['company_id', '=', false], ['company_id', '=', companyId]],
                [],
                { limit: 1 },
            );
            this.anySkills = skillTypes.length > 0;
            this.defaultSkillType = this.anySkills ? skillTypes[0] : null;

            [this.user] = await this.orm.read("res.users", [user.userId], ["employee_ids"]);
            this.IsHrUser = await user.hasGroup("hr.group_hr_user");
            this.userSubordinates = (await this.orm.searchRead(
                "hr.employee",
                [["id", "child_of", this.user.employee_ids]],
                ["id"]
            )).map((record) => record["id"]);
        });
    }

    get groupBy() {
        return 'skill_type_id';
    }

    async skillTypesAction() {
        return this.actionService.doAction("hr_skills.hr_skill_type_action");
    }

    async openSkillsReport() {
        // fetch id through employee or public.employee
        const id = this.env.model.root.data.id || this.env.model.root.data.employee_id.id;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Skills Report"),
            res_model: "hr.employee.skill.history.report",
            view_mode: "graph,list",
            views: [[false, "graph"]],
            context: {
                'fill_temporal': false,
            },
            target: "current",
            domain: [['employee_id', '=', id]],
        });
    }

    get showTimeline() {
        return this.SkillsRight && !this.props.list.context.no_timeline;
    }

    get SkillsRight() {
        let isSubordinate = false;
        if (this.env.model.root.data.employee_id) {
            isSubordinate = this.userSubordinates.includes(this.env.model.root.data.employee_id.id);
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
        this.orm = useService('orm');
        this.actionService = useService('action');

        const { saveRecord, updateRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: saveRecord,
            updateRecord: updateRecord,
            withParentId: this.props.widget !== "many2many",
        });

        this._openRecord = (params) => {
            params.title = this.getWizardTitleName();
            openRecord({...params});
        };
    }

    getWizardTitleName() {
        return _t("Update Skills")
    }

    async onAdd({ context, editable } = {}) {
        const employeeId = this.props.record.resModel === "res.users" ? this.props.record.data.employee_id.id : this.props.record.resId;
        return super.onAdd({
            editable,
            context: {
                ...context,
                default_employee_id: employeeId,
            }
        });
    }
}

export const skillsX2ManyField = {
    ...x2ManyField,
    component: SkillsX2ManyField,
};

registry.category("fields").add("skills_one2many", skillsX2ManyField);
