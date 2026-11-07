import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";

export class TurnstileFormOption extends BaseOptionComponent {
    static id = "turnstile_form_option";
    static template = "website_cf_turnstile.TurnstileFormOption";
    static dependencies = ["turnstileFormOption"];

    setup() {
        super.setup();
        this.hasTurnstileKey = this.dependencies.turnstileFormOption.hasTurnstileKey;
    }
}

registry.category("website-options").add(TurnstileFormOption.id, TurnstileFormOption);
