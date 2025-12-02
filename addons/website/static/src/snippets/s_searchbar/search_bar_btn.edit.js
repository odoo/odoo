import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class SearchBarBtnEdit extends Interaction {
    static selector = ".o_searchbar_form .oe_search_button";

    dynamicContent = {
        _root: {
            "t-on-click": this.onClick,
        },
    };

    onClick(ev) {
        ev.preventDefault();
    }
}

registry.category("public.interactions.edit").add("website.search_bar_btn", {
    Interaction: SearchBarBtnEdit,
});
