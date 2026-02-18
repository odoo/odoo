import { Countdown } from "./countdown";
import { registry } from "@web/core/registry";

const CountdownEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...super.dynamicContent,
            ".countdown_metrics": {
                // focus is needed here so we can listen to keydown events
                "t-on-click": (ev) => {
                    ev.currentTarget.focus();
                },
                "t-on-keydown": (ev) => {
                    ev.preventDefault();
                    ev.stopPropagation();
                },
            },
        };
        setup() {
            this.websiteEditService = this.services.website_edit;
            super.setup();
            this.websiteEditService.callShared("builderOverlay", "refreshOverlays");
            // stop rerendering in the edit mode so we can edit the countdown
            // using the toolbar, otherwise editing becomes cumbersome and
            // messes up history
            clearInterval(this.setInterval);
        }
        get shouldHideCountdown() {
            return false;
        }
        handleEndCountdownAction() {}
    };

registry.category("public.interactions.edit").add("website.countdown", {
    Interaction: Countdown,
    mixin: CountdownEdit,
});
