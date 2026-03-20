import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { Component, useState, useRef } from "@odoo/owl";

/**
 * @typedef {import('./google_map_option_plugin.js').ApiKeyValidation} ApiKeyValidation
 */

export class GoogleMapsApiKeyDialog extends Component {
    static template = "website.GoogleMapsApiKeyDialog";
    static components = { Dialog };
    static props = {
        originalApiKey: String,
        onSave: Function,
        close: Function,
    };

    setup() {
        this.modalRef = useChildRef();
        /** @type {{ apiKey?: string, apiKeyValidation: ApiKeyValidation }} */
        this.state = useState({
            apiKey: this.props.originalApiKey,
            apiKeyValidation: { isValid: false },
        });
        this.apiKeyInput = useRef("apiKeyInput");
        // @TODO mysterious-egg: the `google_map service` is a duplicate of the
        // `website_map_service`, but without the dependency on public
        // interactions. These are used only to restart the interactions once
        // the API is loaded. We do this in the plugin instead. Once
        // `html_builder` replaces `website`, we should be able to remove
        // `website_map_service` since only google_map service will be used.
        this.googleMapsService = useService("google_maps");
    }

    async onClickSave() {
        if (this.state.apiKey) {
            /** @type {NodeList} */
            const buttons = this.modalRef.el.querySelectorAll("button");
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
