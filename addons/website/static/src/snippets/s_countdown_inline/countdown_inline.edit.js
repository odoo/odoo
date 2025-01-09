import { CountdownInline } from "./countdown_inline";
import { registry } from "@web/core/registry";

const CountdownInlineEdit = (I) => class extends I {
    get shouldHideCountdown() {
        return false;
    }
    handleEndCountdownAction() { }
};

registry
    .category("public.interactions.edit")
    .add("website.countdownInline", {
        Interaction: CountdownInline,
        mixin: CountdownInlineEdit,
    });
