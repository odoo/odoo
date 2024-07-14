/** @odoo-module **/

import MainComponent from '@stock_barcode/components/main';
import { patch } from "@web/core/utils/patch";

patch(MainComponent.prototype, {
    async recordComponents() {
        const {action, options} = await this.env.model._getActionRecordComponents();
        options.onClose = async (ev) => {
            if (ev === undefined) {
                await this._onRefreshState({ recordId: this.resId });
                this.render(true);
            }
        };
        await this.action.doAction(action, options);
    },
});
