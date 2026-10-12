import { registry } from "@web/core/registry";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Component, t, useProps } from "@odoo/owl";
import { BadgeTag } from "@web/core/tags_list/badge_tag";

class SkillsTag extends Component {
    static template = "hr_skills.SkillsTag";
    static components = { BadgeTag };

    props = useProps({
        color: t.any().optional(),
        defaultLevel: t.any(),
        onClick: t.function(),
        onDelete: t.function().optional(),
        text: t.string().optional(),
        tooltip: t.string().optional(),
    });
}

class SkillsMany2ManyTags extends Many2ManyTagsField {
    static components = { ...Many2ManyTagsField.components, Tag: SkillsTag };
    getTagProps(record) {
        return { ...super.getTagProps(record), defaultLevel: record.data.default_level };
    }
}

export const skillsMany2ManyTags = {
    ...many2ManyTagsField,
    component: SkillsMany2ManyTags,
    relatedFields: (fieldInfo) => [
        ...many2ManyTagsField.relatedFields(fieldInfo),
        { name: "default_level", type: "boolean" },
    ],
};

registry.category("fields").add("many2many_tags_skills", skillsMany2ManyTags);
