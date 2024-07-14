/** @odoo-module */

import {
    SkillsListRenderer,
    SkillsX2ManyField,
    skillsX2ManyField,
} from "@hr_skills/fields/skills_one2many/skills_one2many";

import { registry } from "@web/core/registry";

export class AppraisalSkillsListRenderer extends SkillsListRenderer {
    calculateColumnWidth(column) {
        const columnSizes = {
            justification: '600px',
            level_progress: '150px',
            skill_level_id: '130px',
            skill_id: '150px',
        };

        if (column.name in columnSizes) {
            return { type: "absolute", value: columnSizes[column.name] };
        }

        return super.calculateColumnWidth(column);
    }

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
AppraisalSkillsListRenderer.template = 'hr_appraisal_skills.AppraisalSkillsListRenderer';
AppraisalSkillsListRenderer.rowsTemplate = "hr_appraisal_skills.AppraisalSkillsListRenderer.Rows";
AppraisalSkillsListRenderer.props = [
    ...AppraisalSkillsListRenderer.props,
    'showSampleData'
];

export class AppraisalSkillsX2ManyField extends SkillsX2ManyField {
    get rendererProps() {
        const props = super.rendererProps;
        props.showSampleData = this.props.record.data.state == 'new';
        return props;
    }
}
AppraisalSkillsX2ManyField.components = {
    ...SkillsX2ManyField.components,
    ListRenderer: AppraisalSkillsListRenderer,
};

export const appraisalSkillsX2ManyField = {
    ...skillsX2ManyField,
    component: AppraisalSkillsX2ManyField,
};

registry.category("fields").add("appraisal_skills_one2many", appraisalSkillsX2ManyField);
