import { registry } from "@web/core/registry";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";

import { SkillsTagList } from "../hr_skills_tags_list/hr_skills_tags_list";


// DONE
class SkillsMany2ManyTags extends Many2ManyTagsField {
    static components = { ...Many2ManyTagsField.components, TagsList: SkillsTagList };
    getTagProps(record) {
        return { ...super.getTagProps(record), defaultLevel: record.data.default_level };
    }
}

export const skillsMany2ManyTags = {
    ...many2ManyTagsField,
    component: SkillsMany2ManyTags,
    relatedFields: (fieldInfo) => {
        return [
            ...many2ManyTagsField.relatedFields(fieldInfo),
            { name: "default_level", type: "boolean"},
        ];
    },
};

registry.category("fields").add("many2many_tags_skills", skillsMany2ManyTags);
