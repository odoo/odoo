import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class Confidence extends Interaction {
    static selector = ".s_confidence";

    setup() {
        this.trackEls = [...this.el.querySelectorAll(".s_confidence_source .s_confidence_track")];
    }

    start() {
        this.buildTracks();
    }

    destroy() {
        this.clearTracks();
    }

    buildTracks() {
        for (const trackEl of this.trackEls) {
            for (const childEl of [...trackEl.children]) {
                const cloneEl = childEl.cloneNode(true);
                cloneEl.classList.add("o_not_editable", "s_confidence_clone");
                cloneEl.setAttribute("contenteditable", "false");
                cloneEl.setAttribute("aria-hidden", "true");
                trackEl.appendChild(cloneEl);
            }
        }
    }

    clearTracks() {
        for (const cloneEl of this.el.querySelectorAll(".s_confidence_clone")) {
            cloneEl.remove();
        }
    }
}

registry.category("public.interactions").add("website.confidence", Confidence);
