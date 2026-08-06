import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class Love extends Interaction {
    static selector = ".s_love";

    setup() {
        this.trackEls = [...this.el.querySelectorAll(".s_love_source .s_love_track")];
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
                cloneEl.classList.add("o_not_editable", "s_love_clone");
                cloneEl.setAttribute("contenteditable", "false");
                cloneEl.setAttribute("aria-hidden", "true");
                trackEl.appendChild(cloneEl);
            }
        }
    }

    clearTracks() {
        for (const cloneEl of this.el.querySelectorAll(".s_love_clone")) {
            cloneEl.remove();
        }
    }
}

registry.category("public.interactions").add("website.love", Love);
