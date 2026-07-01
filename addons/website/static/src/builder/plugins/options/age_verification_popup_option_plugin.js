import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { ShowOnOption } from "../floating_snippets_plugin";

export class AgeVerificationOption extends BaseOptionComponent {
    static id = "age_verification_option";
    static template = "website.AgeVerificationOption";
    static components = { ShowOnOption };
}

class AgeVerificationOptionPlugin extends Plugin {
    static id = "AgeVerificationOption";
    resources = {
        builder_actions: {
            SetAgeConfirmationTemplateAction,
        },
        immutable_link_selectors: [".o_age_verification_btn"],
        submit_button_selectors: [".o_age_verification_btn"],
    };
}

export class SetAgeConfirmationTemplateAction extends BuilderAction {
    static id = "setAgeConfirmationTemplate";
    apply({ editingElement, params: { mainParam: confirmationType } }) {
        const confirmationBlockEl = editingElement.querySelector("#age_confirmation_block");
        const renderedEl = renderToElement(`website.age_confirmation.${confirmationType}`);
        confirmationBlockEl.replaceChildren(renderedEl);
    }
    isApplied({ editingElement, params: { mainParam: confirmationType } }) {
        const confirmationTypeSelectors = {
            yes_or_no: ".o_age_verification_yes_btn",
            birth_year: ".o_age_verification_year_btn",
            birth_date: ".o_age_verification_date_btn",
        };
        const selector = confirmationTypeSelectors[confirmationType];
        return selector ? !!editingElement.querySelector(selector) : false;
    }
}

registry
    .category("website-plugins")
    .add(AgeVerificationOptionPlugin.id, AgeVerificationOptionPlugin);

registry.category("website-options").add(AgeVerificationOption.id, AgeVerificationOption);
