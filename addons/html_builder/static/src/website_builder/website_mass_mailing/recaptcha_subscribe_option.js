import { BaseOptionComponent } from "@html_builder/core/utils";

export class RecaptchaSubscribeOption extends BaseOptionComponent {
    static template = "html_builder.RecaptchaSubscribeOption";
    static props = {
        hasRecaptcha: Function,
    };
}
