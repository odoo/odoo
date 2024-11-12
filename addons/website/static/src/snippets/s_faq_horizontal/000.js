import { Interaction } from "@website/core/interaction";
import { registry } from "@web/core/registry";

//import { extraMenuUpdateCallbacks } from "@website/js/content/menu";

class FaqHorizontal extends Interaction {

    static selector = ".s_faq_horizontal";

    setup() {
        this.titles = this.el.getElementsByClassName('s_faq_horizontal_entry_title');
        this.updateTitlesPosition();
        this.updateTitlesPositionBound = this.updateTitlesPosition.bind(this);
        //extraMenuUpdateCallbacks.push(this.updateTitlesPositionBound);
    }

    destroy() {
        // const indexCallback = extraMenuUpdateCallbacks.indexOf(this._updateTitlesPositionBound);
        // if (indexCallback >= 0) {
        //     extraMenuUpdateCallbacks.splice(indexCallback, 1);
        // }
    }

    updateTitlesPosition() {
        console.log("updateTitlesPosition");
        let position = 16; // Add 1rem equivalent in px to provide a visual gap by default
        const fixedElements = document.getElementsByClassName('o_top_fixed_element');

        Array.from(fixedElements).forEach((el) => position += el.offsetHeight);

        Array.from(this.titles).forEach((title) => {
            title.style.top = `${position}px`;
            title.style.maxHeight = `calc(100vh - ${position + 40}px)`;
        });
    }

}

registry.category("website.active_elements").add("website.faq_horizontal", FaqHorizontal);
