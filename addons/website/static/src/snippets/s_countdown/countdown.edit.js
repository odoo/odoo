import { Countdown } from "./countdown";
import { registry } from "@web/core/registry";

const CountdownEdit = (I) => class extends I {
    get shouldHideCountdown() {
        return false;
    }
    handleEndCountdownAction() { }
};

registry
    .category("public.interactions.edit")
    .add("website.countdown", {
        Interaction: Countdown,
        mixin: CountdownEdit,
    });
