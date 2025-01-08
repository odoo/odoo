import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class SearchModal extends Interaction {
    static selector = "#o_search_modal_block #o_search_modal";
    dynamicContent = {
        _root: {
            "t-on-shown.bs.modal": () => this.el.querySelector(".search-query").focus(),
        },
    };
}

registry
    .category("public.interactions")
    .add("website.search_modal", SearchModal);
