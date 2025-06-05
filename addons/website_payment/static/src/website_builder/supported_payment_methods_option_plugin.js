import { SupportedPaymentMethodsOption } from "./supported_payment_methods_option";
import { BuilderAction } from "@html_builder/core/builder_action";
import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";


class SupportedPaymentMethodsOptionPlugin extends Plugin {
    static id = "supportedPaymentMethodsOption";
    static shared = ["renderSnippetOn"];

    resources = {
        so_content_addition_selector: [".s_supported_payment_methods"],
        builder_options: [
            withSequence(SNIPPET_SPECIFIC, {
                OptionComponent: SupportedPaymentMethodsOption,
                props: { getMaxLimit: this.getMaxLimit.bind(this) },
                selector: ".s_supported_payment_methods",
            }),
        ],
        builder_actions: {
            SupportedPaymentMethodsLimit,
            SupportedPaymentMethodsHeight,
        },
        on_snippet_dragged_handlers: ({ snippetEl }) => this.renderSnippetOn(snippetEl),
        get_options_container_top_buttons: withSequence(
            0,
            editingElement => this.getOptionButtons(editingElement),
        ),
        get_overlay_buttons: withSequence(0, {
            getButtons: editingElement => this.getOptionButtons(editingElement),
        }),
    };

    setup() {
        this.getOptionButtons = this.selectSnippetEl(this.getOptionButtons.bind(this), []);
        this.renderSnippetOn = this.selectSnippetEl(this.renderSnippetOn.bind(this));
    }

    /**
     * Applies `fn` only to `s_supported_payment_methods` elements.
     */
    selectSnippetEl(fn, defaultVal) {
        return (editingElement, ...args) => {
            if (editingElement?.dataset?.snippet !== "s_supported_payment_methods") {
                return defaultVal;
            }
            return fn(editingElement, ...args);
        }
    }

    /**
     * Add a reload button at the top in case the user made some changes to the supported payment
     * methods list.
     */
    getOptionButtons(editingElement) {
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
            ).catch(() => []);
        }
        return this.payment_methods.slice(0, limit);
    }

    async renderSnippetOn(editingElement, force = false) {
        const limit = getLimit(editingElement);
        const payment_methods = await this.getPaymentMethods(limit, force);
        if (payment_methods.length) {
            delete editingElement.dataset.empty;
            editingElement.dataset.limit = Math.min(limit, await this.getMaxLimit());
            editingElement.replaceChildren(renderToElement(
                "website_payment.s_supported_payment_methods.icons",
                { payment_methods, height: getHeight(editingElement) },
            ));
        } else {
            // Triggers an interaction that renders a warning message instead in the snippet (the
            // warning message will be clean by the interaction and is thus not saved by the editor)
            editingElement.dataset.empty = true;
        }
    }

    async getMaxLimit() {
        return await this.getPaymentMethods().then(pms => pms.length)
    }
}


class SupportedPaymentMethodsLimit extends BuilderAction {
    static id = "supportedPaymentMethodsLimit";
    static dependencies = ["supportedPaymentMethodsOption"];

    getValue({ editingElement }) {
        if (editingElement.dataset.empty) {
            return 0; // This is only visual, the actual limit should always be positive
        }
        return getLimit(editingElement);
    }

    async apply({ editingElement, value: limit }) {
        // Should always be positive otherwise the snippet element could end up empty which would
        // make it impossbile to select it anymore.
        if (limit <= 0) {
            return;
        }
        editingElement.dataset.limit = limit;
        await this.dependencies.supportedPaymentMethodsOption.renderSnippetOn(editingElement);
    }
}


class SupportedPaymentMethodsHeight extends BuilderAction {
    static id = "supportedPaymentMethodsHeight";
    static dependencies = ["supportedPaymentMethodsOption"];

    getValue({ editingElement }) {
        return editingElement.dataset.height; // The `BuilderRange` component expects a raw string
    }

    async apply({ editingElement, value: height }) {
        editingElement.dataset.height = height;
        await this.dependencies.supportedPaymentMethodsOption.renderSnippetOn(editingElement);
    }
}


function getLimit(editingElement) {
    return parseInt(editingElement.dataset.limit) || 6;
}


function getHeight(editingElement) {
    return parseInt(editingElement.dataset.height) || 30;
}


registry
    .category("website-plugins")
    .add(SupportedPaymentMethodsOptionPlugin.id, SupportedPaymentMethodsOptionPlugin);
