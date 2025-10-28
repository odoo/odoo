import { fields, Record } from "@mail/core/common/record";

export class DiscussCategory extends Record {
    static _name = "discuss.category";
    static id = "id";

    appCategory = fields.One("DiscussAppCategory", {
        inverse: "discussCategoryAsAppCategory",
        compute() {
            return {
                canView: false,
                extraClass: "o-mail-DiscussSidebarCategory-discussCategory",
                hideWhenEmpty: true,
                icon: "fa fa-hashtag",
                id: `discuss_category_${this.id}`,
            };
        },
    });
    channel_ids = fields.Many("discuss.channel");
    /** @type {number} */
    id;
    /** @type {string} */
    name;

    delete() {
        this.appCategory?.delete();
        super.delete();
    }
}

DiscussCategory.register();
