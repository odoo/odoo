import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

export class AgeVerificationOption extends BaseOptionComponent {
    static template = "website.AgeVerificationOption";
    static selector = ".s_popup.s_age_verification_popup";
    static applyTo = ".modal";
}

class AgeVerificationOptionPlugin extends Plugin {
    static id = "AgeVerificationOption";
    resources = {
        builder_options: [AgeVerificationOption],
        builder_actions: {
            SetAgeConfirmationTemplateAction,
        },
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
            birth_year: ".o_age_verify_year_btn",
            birth_date: ".o_age_verify_date_btn",
        };
        const selector = confirmationTypeSelectors[confirmationType];
        return selector ? !!editingElement.querySelector(selector) : false;
    }
}

registry
    .category("website-plugins")
    .add(AgeVerificationOptionPlugin.id, AgeVerificationOptionPlugin);
