
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2ManyTagsField, many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

export class ApplicantLineMany2Many extends Many2ManyTagsField {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    }

    getTagProps(record){
        let applicant_name = record.data.display_name;
        let name = applicant_name;
        let job_name = record.data.job_id[1];
        if (job_name){
            name = `${job_name} - ${applicant_name}`;
        }
        return {...super.getTagProps(record), text: name};
    }
}

export const applicantLineMany2Many = {
    ...many2ManyTagsField,
    component: ApplicantLineMany2Many,
    relatedFields: (fieldInfo) => {
        return [
            ...many2ManyTagsField.relatedFields(fieldInfo),
            { name: "job_id", type: "many2one"},
        ];
    },
};

registry.category("fields").add("applicant_line_many2many", applicantLineMany2Many);
