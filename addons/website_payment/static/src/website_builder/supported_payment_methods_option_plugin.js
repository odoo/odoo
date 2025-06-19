import { BuilderAction } from "@html_builder/core/builder_action";
import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";


class SupportedPaymentMethodsOption extends Plugin {
    static id = "supportedPaymentMethodsOption";
    static shared = ["renderSnippetOn"];

    resources = {
        so_content_addition_selector: [".s_supported_payment_methods"],
        builder_options: [
            withSequence(SNIPPET_SPECIFIC, {
                template: "website_payment.SupportedPaymentMethodsOption",
                selector: ".s_supported_payment_methods",
            }),
        ],
        builder_actions: {
            SupportedPaymentMethodsLimit,
            SupportedPaymentMethodsHeight,
        },
        get_options_container_top_buttons: withSequence(
            0,
            this.getOptionButtons.bind(this)
        ),
        get_overlay_buttons: withSequence(0, {
            getButtons: this.getOptionButtons.bind(this),
        }),
        on_snippet_dragged_handlers: ({ snippetEl }) => this.renderSnippetOn(snippetEl),
    };

    /**
     * Add a reload button at the top in case the user made some changes to the available payment
     * methods list.
     */
    getOptionButtons(editingElement) {
        if (editingElement.dataset.snippet !== "s_supported_payment_methods") {
            return [];
        }
        return [{
            class: "fa fa-fw fa-rotate-right btn btn-outline-info",
            title: _t("Refresh the payment methods."),
            handler: this.renderSnippetOn.bind(this, editingElement, true),
        }];
    }

    async getPaymentMethods(limit, force = false) {
        if (force) {
            this.payment_methods = undefined;
        }

        if (this.payment_methods === undefined) {
            this.payment_methods = await rpc(
                "/website_payment/snippet/supported_payment_methods",
            ).catch(() => []); // TODO: find a way to show the error (if its necessary)
        }
        return this.payment_methods.slice(0, limit);
    }

    async renderSnippetOn(editingElement, force = false) {
        const payment_methods = await this.getPaymentMethods(getLimit(editingElement), force);
        if (payment_methods.length) {
            editingElement.replaceChildren(renderToElement(
                "website_payment.s_supported_payment_methods.icons",
                { payment_methods, height: getHeight(editingElement) },
            ));
            delete editingElement.dataset.empty;
        } else {
            // Triggers an interaction to render a message that will not be saved by the editor
            editingElement.dataset.empty = true;
        }
    }
}


class SupportedPaymentMethodsLimit extends BuilderAction {
    static id = "supportedPaymentMethodsLimit";
    static dependencies = ["supportedPaymentMethodsOption"];

    getValue({ editingElement }) {
        return getLimit(editingElement);
    }

    async apply({ editingElement, value: limit }) {
        editingElement.dataset.limit = limit;
        await this.dependencies.supportedPaymentMethodsOption.renderSnippetOn(editingElement);
    }
}


class SupportedPaymentMethodsHeight extends BuilderAction {
    static id = "supportedPaymentMethodsHeight";
    static dependencies = ["supportedPaymentMethodsOption"];

    getValue({ editingElement }) {
        return getHeight(editingElement);
    }

    async apply({ editingElement, value: height }) {
        editingElement.dataset.height = height;
        await this.dependencies.supportedPaymentMethodsOption.renderSnippetOn(editingElement);
    }
}


function getLimit(editingElement) {
    return parseInt(editingElement.dataset.limit);
}


function getHeight(editingElement) {
    return parseInt(editingElement.dataset.height);
}


registry
    .category("website-plugins")
    .add(SupportedPaymentMethodsOption.id, SupportedPaymentMethodsOption);
