import { BaseOptionComponent } from "@html_builder/core/base_option_component";

export class TurnstileSubscribeOption extends BaseOptionComponent {
    static template = "website_mass_mailing.TurnstileSubscribeOption";
    static dependencies = ["turnstileSubscribeOption"];

    setup() {
        super.setup();
        this.hasTurnstile = this.dependencies.turnstileSubscribeOption.hasTurnstile;
    }
}
