import { Plugin } from "@html_editor/plugin";
import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";


class SupportedPaymentMethodsOption extends Plugin {
    static id = "supportedPaymentMethodsOption";
    static dependencies = ["edit_interaction"];
    resources = {
        so_content_addition_selector: [".s_supported_payment_methods"],
        builder_options: [
            withSequence(SNIPPET_SPECIFIC, {
                template: "website_payment.SupportedPaymentMethodsOption",
                selector: ".s_supported_payment_methods",
            }),
        ],
        get_options_container_top_buttons: withSequence(
            0,
            this.getOptionsContainerTopButtons.bind(this)
        ),
        builder_actions: {
            applyLimit: {
                getValue: this.getLimit.bind(this),
                apply: this.applyLimit.bind(this),
            },
            applyHeight: {
                getValue: this.getHeight.bind(this),
                apply: this.applyHeight.bind(this),
            },
        },
    };

    getLimit({ editingElement }) {
        return editingElement.dataset.limit;
    }

    applyLimit({ editingElement, value }) {
        editingElement.dataset.limit = value;
    }

    getHeight({ editingElement }) {
        return editingElement.dataset.height;
    }

    applyHeight({ editingElement, value }) {
        editingElement.dataset.height = value;
    }

    /**
     * Add a reload button at the top in case the user made some changes to the available payment
     * methods list.
     */
    getOptionsContainerTopButtons(editingElement) {
        if (editingElement.dataset.snippet !== "s_supported_payment_methods") {
            return [];
        }
        return [
            {
                class: "fa fa-fw fa-rotate-right btn btn-outline-info",
                title: _t("Refresh the payment methods."),
                handler: this.dependencies.edit_interaction.restartInteractions,
            },
        ];
    }
}

registry
    .category("website-plugins")
    .add(SupportedPaymentMethodsOption.id, SupportedPaymentMethodsOption);
