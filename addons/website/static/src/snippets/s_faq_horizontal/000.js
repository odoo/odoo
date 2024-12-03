import { Interaction } from "@website/core/interaction";
import { registry } from "@web/core/registry";

// TODO - Handle extraMenuUpdateCallbacks
class FaqHorizontal extends Interaction {
    static selector = ".s_faq_horizontal";

    setup() {
        this.titles = this.el.getElementsByClassName('s_faq_horizontal_entry_title');
        // this.updateTitlesPositionBound = this.updateTitlesPosition.bind(this);
        // extraMenuUpdateCallbacks.push(this.updateTitlesPositionBound);
    }

    start() {
        this.updateTitlesPosition();
    }

    destroy() {
        // const indexCallback = extraMenuUpdateCallbacks.indexOf(this._updateTitlesPositionBound);
        // if (indexCallback >= 0) {
        //     extraMenuUpdateCallbacks.splice(indexCallback, 1);
        // }
    }

    updateTitlesPosition() {
        let position = 16; // Add 1rem equivalent in px to provide a visual gap by default
        const fixedElements = document.getElementsByClassName('o_top_fixed_element');

        for (const el of fixedElements) {
            position += el.offsetHeight;
        }

        for (const title of this.titles) {
            title.style.top = `${position}px`;
            title.style.maxHeight = `calc(100vh - ${position + 40}px)`;
        }
    }
}

registry
    .category("website.active_elements")
    .add("website.faq_horizontal", FaqHorizontal);
