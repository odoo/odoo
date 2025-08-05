import { TagsList } from "@web/core/tags_list/tags_list";


// DONE
export class SkillsTagList extends TagsList {
    static template = "hr_skills.SkillsTagsList";

    getTextStyle(tag) {
        return tag.defaultLevel
    }
}
