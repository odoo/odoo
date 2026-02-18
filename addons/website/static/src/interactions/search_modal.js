import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class SearchModal extends Interaction {
    static selector = ".modal[id^='o_search_modal']";
    dynamicContent = {
        _root: {
            "t-on-shown.bs.modal": this.onModalShown,
        },
    };
    destroy() {
        Modal.getInstance(this.el)?.hide();
    }
    onModalShown() {
        this.el.classList.remove("o_keyboard_navigation");
        this.el.querySelector(".search-query").focus();
    }
}

registry.category("public.interactions").add("website.search_modal", SearchModal);
