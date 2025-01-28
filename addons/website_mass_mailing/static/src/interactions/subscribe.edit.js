import { Subscribe } from "./subscribe";
import { registry } from "@web/core/registry";

const SubscribeEdit = I => class extends I {
    // Since there is an editor option to choose whether "Thanks" button
    // should be visible or not, we should not vary its visibility here.
    start() { }
};

registry
    .category("public.interactions.edit")
    .add("website_mass_mailing.subscribe", {
        Interaction: Subscribe,
        mixin: SubscribeEdit,
    });
