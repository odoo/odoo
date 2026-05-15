import { Plugin } from "@mail/convert_inline/plugin";
import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";

export class ConditionalVisibilityPlugin extends Plugin {
    static id = "conditionalVisibility";
    resources = {
        on_will_load_reference_content_handlers: this.preprocessFilterDomains.bind(this),
    };

    /**
     * Processes the data-filter-domain to be converted to a t-if that will be interpreted on send
     * by QWeb.
     */
    preprocessFilterDomains() {
        for (const el of this.config.reference.querySelectorAll("[data-filter-domain]")) {
            let domain;
            try {
                domain = new Domain(JSON.parse(el.dataset.filterDomain));
            } catch {
                el.setAttribute("t-if", "false");
                return;
            }
            el.setAttribute("t-if", `object.filtered_domain(${domain.toString()})`);
        }
    }
}

registry
    .category("mass-mailing-html-conversion-plugins")
    .add(ConditionalVisibilityPlugin.id, ConditionalVisibilityPlugin);
