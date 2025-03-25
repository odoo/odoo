import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef } from "@web/core/utils/hooks";
import { Component, useState, useRef } from "@odoo/owl";

/**
 * @typedef {import('./google_map_option_plugin.js').ApiKeyValidation} ApiKeyValidation
 */

export class GoogleMapsApiKeyDialog extends Component {
    static template = "website.s_google_map_modal";
    static components = { Dialog };
    static props = {
        validateGMapsApiKey: Function,
        originalApiKey: String,
        originalApiKeyValidation: Object,
        onSave: Function,
        close: Function,
    };

    setup() {
        this.modalRef = useChildRef();
        /** @type {{ apiKey?: string, apiKeyValidation: ApiKeyValidation }} */
        this.state = useState({
            apiKey: this.props.originalApiKey,
            apiKeyValidation: this.props.originalApiKeyValidation,
        });
        this.apiKeyInput = useRef("apiKeyInput");
    }

    async onClickSave() {
        if (this.state.apiKey) {
            /** @type {NodeList} */
            const buttons = this.modalRef.el.querySelectorAll("button");
            buttons.forEach((button) => button.setAttribute("disabled", true));
            /** @type {ApiKeyValidation} */
            const apiKeyValidation = await this.props.validateGMapsApiKey(this.state.apiKey);
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
