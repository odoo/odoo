import { BaseOptionComponent } from "@html_builder/core/utils";

export class RecaptchaSubscribeOption extends BaseOptionComponent {
    static template = "website_mass_mailing.RecaptchaSubscribeOption";

    setup(){
        super.setup();
        this.hasRecaptcha = this.dependencies.newsletterSubscribeCommonOption.hasRecaptcha;
    }
}
