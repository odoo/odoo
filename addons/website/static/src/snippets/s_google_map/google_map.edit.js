import { GoogleMap } from "./google_map";
import { registry } from "@web/core/registry";

const GoogleMapEdit = I => class extends I {
    setup() {
        super.setup();
        this.canSpecifyKey = true;
    }
}

registry
    .category("public.interactions.edit")
    .add("website.google_map", {
        Interaction: GoogleMap,
        mixin: GoogleMapEdit,
    });
