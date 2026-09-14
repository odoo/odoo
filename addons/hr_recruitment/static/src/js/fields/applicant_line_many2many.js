/** @odoo-module native */

import { registry } from "@web/core/registry";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/fields/relational/many2many_tags";

export class ApplicantLineMany2Many extends Many2ManyTagsField {
    getTagProps(record) {
        const applicantName = record.data.display_name;
        const jobName = record.data.job_id?.display_name;
        return {
            ...super.getTagProps(record),
            text: jobName ? `${jobName} - ${applicantName}` : applicantName,
        };
    }
}

export const applicantLineMany2Many = {
    ...many2ManyTagsField,
    component: ApplicantLineMany2Many,
    relatedFields: (fieldInfo) => {
        return [
            ...many2ManyTagsField.relatedFields(fieldInfo),
            { name: "job_id", type: "many2one" },
        ];
    },
};

registry.category("fields").add("applicant_line_many2many", applicantLineMany2Many);
