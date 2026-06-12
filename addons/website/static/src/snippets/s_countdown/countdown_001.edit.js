import { closestElement } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";
import { Countdown001 } from "./countdown_001";
import { CountdownEdit } from "./countdown.edit";

const CountdownEdit001 = (I) =>
    class extends CountdownEdit(I) {
        dynamicContent = {
            ...super.dynamicContent,
            _root: {
                // users should be able to change the countdown metrics only
                // with the toolbar, no other changes are allowed
                "t-on-keydown": this.preventEvent,
                "t-on-paste": this.preventEvent,
                "t-on-cut": this.preventEvent,
                "t-on-dragstart": this.preventEvent,
            },
        };
        setup() {
            this.renderedTimes = 0;
            super.setup();
        }
        render() {
            // first render's modifications are ignored by the history, because
            // they happened in the setup of the interaction, we need to render
            // once more so the countdown's state has been added to the history
            // so if a user undoes/redoes stuff, it won't be broken.
            super.render();
            this.renderedTimes += 1;
            if (this.renderedTimes == 2) {
                // stop the render in the edit mode, so users can modify the
                // countdown using the toolbar
                clearInterval(this.setInterval);
            }
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
            if (targetedNodes.some((node) => closestElement(node, ".countdown_metrics"))) {
                ev.preventDefault();
                ev.stopPropagation();
            }
        }
    };

registry.category("public.interactions.edit").add("website.countdown_001", {
    Interaction: Countdown001,
    mixin: CountdownEdit001,
});

registry.category("public.interactions.preview").add("website.countdown_001", {
    Interaction: Countdown001,
});
