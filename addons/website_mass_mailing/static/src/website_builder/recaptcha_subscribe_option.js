import { BaseOptionComponent } from "@html_builder/core/utils";

export class RecaptchaSubscribeOption extends BaseOptionComponent {
    static template = "website_mass_mailing.RecaptchaSubscribeOption";
    static props = {
        hasRecaptcha: Function,
    };
}
