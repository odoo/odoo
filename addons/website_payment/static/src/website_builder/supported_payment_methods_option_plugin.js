import { BuilderAction } from '@html_builder/core/builder_action';
import { BaseOptionComponent } from '@html_builder/core/utils';
import { SNIPPET_SPECIFIC } from '@html_builder/utils/option_sequence';
import { Plugin } from '@html_editor/plugin';
import { withSequence } from '@html_editor/utils/resource';
import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';


export class SupportedPaymentMethodsOption extends BaseOptionComponent {
    static template = 'website_payment.SupportedPaymentMethodsOption';
    static selector = '.s_supported_payment_methods';
}

class SupportedPaymentMethodsOptionPlugin extends Plugin {
    static id = 'supportedPaymentMethodsOption';
    static dependencies = ['edit_interaction'];
    resources = {
        so_content_addition_selector: ['.s_supported_payment_methods'],
        builder_options: [
            withSequence(SNIPPET_SPECIFIC, SupportedPaymentMethodsOption),
        ],
        builder_actions: { SupportedPaymentMethodsLimit, SupportedPaymentMethodsHeight },
        get_options_container_top_buttons: withSequence(0, this.getOptionButtons.bind(this)),
        get_overlay_buttons: withSequence(0, { getButtons: this.getOptionButtons.bind(this) }),
    };

    /**
     * Add a reload button at the top in case the user made some changes to the supported payment
     * methods. This only reloads the snippet element and not the entire editor page.
     */
    getOptionButtons(editingElement) {
        if (editingElement.dataset.snippet !== 's_supported_payment_methods') {
            return [];
        }
        return [{
            class: 'fa fa-fw fa-rotate-right btn btn-outline-info',
            title: _t("Reload the payment methods"),
            // Force the interaction to call the server again in case the user made backend changes.
            handler: () => this.dependencies.edit_interaction.restartInteractions(editingElement),
        }];
    }
}


class SupportedPaymentMethodsLimit extends BuilderAction {
    static id = 'supportedPaymentMethodsLimit';

    getValue({ editingElement }) {
        return editingElement.dataset.limit;
    }

    apply({ editingElement, value }) {
        editingElement.dataset.limit = value;
    }
}


class SupportedPaymentMethodsHeight extends BuilderAction {
    static id = 'supportedPaymentMethodsHeight';

    getValue({ editingElement }) {
        return editingElement.dataset.height;
    }

    apply({ editingElement, value }) {
        editingElement.dataset.height = value;
    }
}


registry
    .category('website-plugins')
    .add(SupportedPaymentMethodsOptionPlugin.id, SupportedPaymentMethodsOptionPlugin);
