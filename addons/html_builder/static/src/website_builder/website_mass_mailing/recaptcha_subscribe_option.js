import { Component } from "@odoo/owl";
import { useBuilderComponents } from "@html_builder/core/utils";

export class RecaptchaSubscribeOption extends Component {
    static template = "html_builder.RecaptchaSubscribeOption";
    static props = {
        hasRecaptcha: Function,
    };

    setup() {
        useBuilderComponents();
    }
}
