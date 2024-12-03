import { Interaction } from "@website/core/interaction";
import { registry } from "@web/core/registry";

class SearchModal extends Interaction {
    static selector = "#o_search_modal_block #o_search_modal";
    dynamicContent = {
        _root: {
            "t-on-show.bs.modal": this.onSearchModalShow,
            "t-on-shown.bs.modal": this.onSearchModalShown,
        },
    }

    /**
     * @param {Event} ev
     */
    onSearchModalShow(ev) {
        // TODO
        // if (!this.editableMode) {
        //     return;
        // }
        // ev.preventDefault();
    }

    onSearchModalShown() {
        this.el.querySelector(".search-query").focus();
    }
}

registry
    .category("website.active_elements")
    .add("website.search_modal", SearchModal);
