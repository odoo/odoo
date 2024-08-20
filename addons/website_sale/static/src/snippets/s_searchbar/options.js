import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const websiteSearchBar = registry.category("snippet_options").get("SearchBar");
patch(websiteSearchBar.Class.prototype, {
    /**
     * @override
     */
    _constructor() {
        super._constructor(...arguments);
        this.orm = this.env.services.orm;
    },
    /**
     * @override
     */
    async _getRenderContext() {
        return {
            ...(await super._getRenderContext()),
            productSorts: await this.orm.call("website", "get_product_sort_mapping"),
        };
    },
});
