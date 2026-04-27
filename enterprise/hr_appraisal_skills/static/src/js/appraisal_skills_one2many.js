/** @odoo-module */

import {
    SkillsListRenderer,
    SkillsX2ManyField,
    skillsX2ManyField,
} from "@hr_skills/fields/skills_one2many/skills_one2many";

import { registry } from "@web/core/registry";

export class AppraisalSkillsListRenderer extends SkillsListRenderer {
    static template = "hr_appraisal_skills.AppraisalSkillsListRenderer";
    static rowsTemplate = "hr_appraisal_skills.AppraisalSkillsListRenderer.Rows";
    static props = [...AppraisalSkillsListRenderer.props, "showSampleData"];

    get showTable() {
        return this.props.showSampleData || super.showTable;
    }

    get sampleRecords() {
        return [{
            'skill': '80px',
            'level': '25px',
            'progress': '120px',
            'justification': '190px'
        }, {
            'skill': '70px',
            'level': '40px',
            'progress': '100px',
            'justification': '130px'
        }, {
            'skill': '40px',
            'level': '80px',
            'progress': '30px',
            'justification': '210px'
        }, {
            'skill': '90px',
            'level': '47px',
            'progress': '70px',
            'justification': '100px'
        }];
    }

    get fields() {
        const fields = this.props.list.fields;

        Object.values(fields).forEach((k) => {
            if (k.sortable) {
                k.sortable = false;
            }
        });
        return fields;
    }
}

export class AppraisalSkillsX2ManyField extends SkillsX2ManyField {
    static components = {
        ...SkillsX2ManyField.components,
        ListRenderer: AppraisalSkillsListRenderer,
    };

    get rendererProps() {
        const props = super.rendererProps;
        props.showSampleData = this.props.record.data.state == 'new';
        return props;
    }
}

export const appraisalSkillsX2ManyField = {
    ...skillsX2ManyField,
    component: AppraisalSkillsX2ManyField,
};

registry.category("fields").add("appraisal_skills_one2many", appraisalSkillsX2ManyField);
