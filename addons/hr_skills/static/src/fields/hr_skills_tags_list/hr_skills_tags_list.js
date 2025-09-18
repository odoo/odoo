import { TagsList } from "@web/components/tags_list/tags_list";


export class SkillsTagList extends TagsList {
    static template = "hr_skills.SkillsTagsList";

    getTextStyle(tag) {
        return tag.defaultLevel
    }
}
