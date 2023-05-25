/** @odoo-module */

import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import {
    useX2ManyCrud,
    useOpenX2ManyRecord,
} from "@web/views/fields/relational_utils";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CommonSkillsListRenderer } from "../../views/skills_list_renderer";
import { useService } from '@web/core/utils/hooks';
import { onWillStart } from "@odoo/owl";


export class SkillsListRenderer extends CommonSkillsListRenderer {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.action = useService("action");

        onWillStart(async () => {
            const res = await this.orm.searchCount('hr.skill', []);
            this.anySkills = res > 0;
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
        const id = this.env.model.root.data.id || this.env.model.root.data.employee_id[0];
-        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Skills Report"),
            res_model: "hr.employee.skill.log",
            view_mode: "graph,tree",
            views: [[false, "graph"], [false, "tree"]],
            context: {
                'fill_temporal': 0,
            },
            target: "current",
            domain: [['employee_id', '=', id]],
        });
    }

    calculateColumnWidth(column) {
        if (column.name != 'skill_level_id') {
            return {
                type: 'absolute',
                value: '90px',
            }
        }

        return super.calculateColumnWidth(column);
    }
}
SkillsListRenderer.template = 'hr_skills.SkillsListRenderer';

export class SkillsX2ManyField extends X2ManyField {
    setup() {
        super.setup()
        const { saveRecord, updateRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: async (record) => {
                await saveRecord(record);
                await this.props.record.save();
            },
            updateRecord: updateRecord,
            withParentId: this.props.widget !== "many2many",
        });

        this._openRecord = (params) => {
            params.title = _t("Select Skills");
            openRecord({...params});
        };
    }

    async onAdd({ context, editable } = {}) {
        const employeeId = this.props.record.resId;
        return super.onAdd({
            editable,
            context: {
                ...context,
                default_employee_id: employeeId,
            }
        });
    }
}

SkillsX2ManyField.components = {
    ...X2ManyField.components,
    ListRenderer: SkillsListRenderer,
};

export const skillsX2ManyField = {
    ...x2ManyField,
    component: SkillsX2ManyField,
};

registry.category("fields").add("skills_one2many", skillsX2ManyField);
