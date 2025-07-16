import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ReferencesCarouselOption } from "./references_carousel_option";

class ReferencesCarouselOptionPlugin extends Plugin {
    static id = "referencesCarouselOption";
    
    get resources() {
        return {
        builder_options: [
            {
                    OptionComponent: ReferencesCarouselOption,
                    selector: ".s_references_carousel",
            },
        ],
    };
    }
}

registry.category("website-plugins").add("referencesCarouselOption", ReferencesCarouselOptionPlugin);
