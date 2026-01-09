import { DiscussCategory } from "@mail/discuss/core/common/discuss_category_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussCategory} */
const discussCategoryPatch = {
    setup() {
        super.setup(...arguments);
        this.appCategory = fields.One("DiscussAppCategory", {
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
    },
    delete() {
        this.appCategory?.delete();
        super.delete();
    },
};
patch(DiscussCategory.prototype, discussCategoryPatch);
