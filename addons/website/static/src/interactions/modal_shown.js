import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ModalShown extends Interaction {
    static selector = ".modal";
    dynamicContent = {
        _root: {
            "t-on-shown.bs.modal": () => this.el.classList.add("modal_shown"),
        },
    };
}

registry.category("public.interactions").add("website.modal_shown", ModalShown);
registry.category("public.interactions.edit").add("website.modal_shown", {
    Interaction: ModalShown,
});
