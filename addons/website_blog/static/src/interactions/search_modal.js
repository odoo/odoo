import { SearchModal as WebsiteSearchModal } from "@website/interactions/search_modal";
import { registry } from "@web/core/registry";

export class SearchModal extends WebsiteSearchModal {
    static selector = "#o_wblog_search_modal";
}

registry
    .category("public.interactions")
    .add("website_blog.search_modal", SearchModal);

