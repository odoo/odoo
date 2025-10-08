import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class Timeline extends Interaction {
    static selector = ".s_timeline";

    start() {
        this.observeMutations();
    }

    removeEmptyRows() {
        const rows = this.el
            .closest(".s_timeline")
            .querySelectorAll(
                ".s_timeline_row:not(:has(.s_timeline_content .s_timeline_card))"
            );
        rows.forEach((row) => row.remove());
    }

    observeMutations() {
        this._observer = new MutationObserver(() => {
            this.removeEmptyRows();
        });

        this._observer.observe(this.el, {
            childList: true,
            subtree: true,
        });
    }

    destroy() {
        if (this._observer) {
            this._observer.disconnect();
        }
    }
}

registry.category("public.interactions.edit").add("website.timeline", {
    Interaction: Timeline,
});
