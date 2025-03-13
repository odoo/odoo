import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../../core/default_builder_components";

export class RecaptchaSubscribeOption extends Component {
    static template = "html_builder.RecaptchaSubscribeOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        hasRecaptcha: Function,
    };
}
