import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class MapEdit extends Interaction {
    static selector = ".s_map:not([data-map-address]), .s_map[data-map-address='']";

    start() {
        const savedWarningEl = this.el.querySelector(".missing_option_warning:not(.d-none)");
        if (savedWarningEl) {
            return;
        }
        this.renderAt(
            "website.s_map.missing_option_warning",
            {},
            this.el.querySelector(".map_container"),
            "afterbegin"
        );
    }
}

registry.category("public.interactions.edit").add("website.map_edit", {
    Interaction: MapEdit,
});
