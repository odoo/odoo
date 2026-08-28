import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, proxy, signal, useProps, t } from "@odoo/owl";

/**
 * @typedef {import('./google_map_option_plugin.js').ApiKeyValidation} ApiKeyValidation
 */

export class GoogleMapsApiKeyDialog extends Component {
    static template = "website.GoogleMapsApiKeyDialog";
    static components = { Dialog };
    props = useProps({
        title: t.string().optional(),
        originalApiKey: t.string(),
        onSave: t.function(),
        close: t.function(),
    });

    setup() {
        this.modalRef = signal.ref();
        /** @type {{ apiKey?: string, apiKeyValidation: ApiKeyValidation }} */
        this.state = proxy({
            apiKey: this.props.originalApiKey,
            apiKeyValidation: { isValid: false },
        });
        this.googleMapsService = useService("google_maps");
    }

    async onClickSave() {
        if (this.state.apiKey) {
            /** @type {NodeList} */
            const buttons = this.modalRef().querySelectorAll("button");
            buttons.forEach((button) => button.setAttribute("disabled", true));
            /** @type {ApiKeyValidation} */
            const apiKeyValidation = await this.googleMapsService.validateGMapsApiKey(
                this.state.apiKey
            );
            this.state.apiKeyValidation = apiKeyValidation;
            if (apiKeyValidation.isValid) {
                await this.props.onSave(this.state.apiKey);
                this.props.close();
            }
            buttons.forEach((button) => button.removeAttribute("disabled"));
        } else {
            this.state.apiKeyValidation = {
                isValid: false,
                message: _t("Enter an API Key"),
            };
        }
    }
}
