/** @odoo-module **/

import { CustomFavoriteItem } from "@web/search/custom_favorite_item/custom_favorite_item";
import { patch } from "@web/core/utils/patch";

patch(CustomFavoriteItem.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.isKnowledgeEmbeddedView()) {
            // knowledge favorites are shared for all users
            this.state.isShared = true;
        }
    },

    isKnowledgeEmbeddedView() {
        return (
            this.env.searchModel &&
            this.env.searchModel.context &&
            this.env.searchModel.context.knowledgeEmbeddedViewId
        );
    },
});
