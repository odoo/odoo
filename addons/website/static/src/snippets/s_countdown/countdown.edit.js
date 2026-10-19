import { closestElement } from "@html_editor/utils/dom_traversal";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { registry } from "@web/core/registry";
import { Countdown } from "./countdown";

const DELETION_HOTKEYS = new Set([
    "control+backspace",
    "control+delete",
    "control+shift+backspace",
    "control+shift+delete",
]);

const COUNTDOWN_READONLY_SELECTOR = ".o_count_item_nbs, .o_count_separator";

const CountdownEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            _root: {
                // Users should be able to change the countdown values only with
                // the toolbar, no other changes are allowed.
                "t-on-keydown": (ev) => {
                    // We want to allow "Ctrl" actions and arrow keys.
                    const hotkey = getActiveHotkey(ev);
                    if (
                        DELETION_HOTKEYS.has(hotkey) ||
                        !(hotkey.startsWith("control") || hotkey.startsWith("arrow"))
                    ) {
                        this.preventEvent(ev);
                    }
                },
                "t-on-paste": this.preventEvent,
                "t-on-cut": this.preventEvent,
                "t-on-dragstart": this.preventEvent,
            },
        };

        setup() {
            super.setup();
            this.websiteEditService = this.services.website_edit;
            this.websiteEditService.callShared("builderOverlay", "refreshOverlays");
        }

        get shouldHideCountdown() {
            return false;
        }

        handleEndCountdownAction() {}

        shouldUpdateValue(el) {
            // Don't update while it is selected, otherwise rewriting it would
            // conflict with the toolbar.
            const targetedNodes =
                this.websiteEditService?.callShared("selection", "getTargetedNodes") || [];
            return !targetedNodes.some((node) => el.contains(node));
        }

        getConfigurationSnapshot() {
            let snapshot = super.getConfigurationSnapshot();
            // should restart the interaction if the color has changed
            // so canvas' text color is updated
            if (this.el.querySelector(".o_template_circle")) {
                snapshot = JSON.parse(snapshot) || {};
                snapshot.style = { ...snapshot.style, color: this.textColor };
                snapshot = JSON.stringify(snapshot);
            }
            return snapshot;
        }

        preventEvent(ev) {
            const targetedNodes = this.websiteEditService.callShared(
                "selection",
                "getTargetedNodes"
            );
            if (targetedNodes.some((node) => closestElement(node, COUNTDOWN_READONLY_SELECTOR))) {
                ev.preventDefault();
                ev.stopPropagation();
            }
        }
    };

registry.category("public.interactions.edit").add("website.countdown", {
    Interaction: Countdown,
    mixin: CountdownEdit,
});

registry.category("public.interactions.preview").add("website.countdown", {
    Interaction: Countdown,
});
