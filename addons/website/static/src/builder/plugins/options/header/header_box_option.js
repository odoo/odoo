import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
export class HeaderBoxOption extends BaseOptionComponent {
    static id = "header_box_option";
    static template = "website.HeaderBoxOption";

    setup() {
        super.setup();
        this.domState = useDomState((editingElement) => ({
            withRoundCorner: !editingElement.classList.contains("o_header_force_no_radius"),
        }));
    }
}

registry.category("builder-options").add(HeaderBoxOption.id, HeaderBoxOption);
