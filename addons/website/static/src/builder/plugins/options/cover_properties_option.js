import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class CoverPropertiesOption extends BaseOptionComponent {
    static id = "cover_properties_option";
    static template = "website.CoverPropertiesOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            useTextAlign: editingElement.dataset.use_text_align === "True",
            useSize: editingElement.dataset.use_size === "True",
        }));
    }
}

registry.category("website-options").add(CoverPropertiesOption.id, CoverPropertiesOption);
