import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class HeaderTop extends Interaction {
    static selector = "header#top";
    dynamicContent = {
        "#top_menu_collapse, #top_menu_collapse_mobile": {
            "t-on-show.bs.offcanvas": () => (this.showCollapse = true),
            "t-on-hidden.bs.offcanvas": () =>
                (this.showCollapse &&= this.mobileNavbarEl.matches(".show, .showing")),
            "t-att-class": () => ({
                o_top_menu_collapse_shown: this.showCollapse,
            }),
        },
    };

    setup() {
        this.showCollapse = false;
        this.mobileNavbarEl = this.el.querySelector("#top_menu_collapse_mobile");
    }
}

registry.category("public.interactions").add("website.header_top", HeaderTop);

registry.category("public.interactions.edit").add("website.header_top", {
    Interaction: HeaderTop,
});
