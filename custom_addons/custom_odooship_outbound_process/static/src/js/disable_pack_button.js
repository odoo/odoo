/** @odoo-module **/

import { FormController } from '@web/views/form/form_controller';

const { patch } = require("@web/core/utils/patch");

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.__packDisabled = false;
    },

    async _onButtonClicked(ev) {
        if (ev.detail.attrs.name === 'pack_products') {
            this.__packDisabled = true;
        }

        try {
            await super._onButtonClicked(ev);
        } catch (error) {
            // Re-enable if failure
            if (ev.detail.attrs.name === 'pack_products') {
                this.__packDisabled = false;
            }
            throw error;
        }
    }
});
