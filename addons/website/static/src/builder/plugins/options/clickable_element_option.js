import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";

export class ClickableCardOption extends BaseOptionComponent {
    static id = "clickable_card_option";
    static template = "website.ClickableCardOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            hasHref: editingElement
                .querySelector(":scope > a.stretched-link")
                ?.hasAttribute("href"),
        }));
    }
}

registry.category("builder-options").add(ClickableCardOption.id, ClickableCardOption);
