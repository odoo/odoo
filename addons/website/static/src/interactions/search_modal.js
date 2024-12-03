import { Interaction } from "@website/core/interaction";
import { registry } from "@web/core/registry";

class SearchModal extends Interaction {
    static selector = "#o_search_modal_block #o_search_modal";
    dynamicContent = {
        _root: {
            "t-on-shown.bs.modal": this.onSearchModalShown,
        },
    }

    onSearchModalShown() {
        this.el.querySelector(".search-query").focus();
    }
}

registry
    .category("website.active_elements")
    .add("website.search_modal", SearchModal);
