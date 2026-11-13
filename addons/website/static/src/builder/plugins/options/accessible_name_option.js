import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { getDefaultAccessibleName } from "@website/js/utils";

export class AccessibleNameOption extends BaseOptionComponent {
    static id = "accessible_name_option";
    static template = "website.AccessibleNameOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            defaultName: getDefaultAccessibleName(editingElement),
        }));
    }
}

registry.category("website-options").add(AccessibleNameOption.id, AccessibleNameOption);
