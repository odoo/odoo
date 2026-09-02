import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { CLICKABLE_LINK_SELECTOR } from "./clickable_element_option_plugin";

export class ClickableElementOption extends BaseOptionComponent {
    static id = "clickable_element_option";
    static template = "website.ClickableElementOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            hasHref: editingElement.querySelector(CLICKABLE_LINK_SELECTOR)?.hasAttribute("href"),
        }));
    }
}

registry.category("builder-options").add(ClickableElementOption.id, ClickableElementOption);
