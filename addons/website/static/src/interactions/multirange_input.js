import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import multirange from "@website/../lib/multirange/multirange_custom";

export class WebsiteMultirangeInput extends Interaction {
    static selector = "input[type=range][multiple]:not(.multirange)";

    start() {
        multirange.init(this.el);
    }
}

registry
    .category("public.interactions")
    .add("website.multirange_input", WebsiteMultirangeInput);
