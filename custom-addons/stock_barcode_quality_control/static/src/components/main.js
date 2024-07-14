/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import MainComponent from '@stock_barcode/components/main';
import { patch } from "@web/core/utils/patch";

patch(MainComponent.prototype, {
    get hasQualityChecksTodo() {
        return this.env.model.record && this.env.model.record.quality_check_todo;
    },

    async checkQuality(ev) {
        ev.stopPropagation();
        await this.env.model.save();
        const res = await this.orm.call(
            this.resModel,
            this.env.model.openQualityChecksMethod,
            [[this.resId]]
        );
        if (typeof res === 'object' && res !== null) {
            return this.action.doAction(res, {
                onClose: this._onRefreshState.bind(this, { recordId: this.resId }),
            });
        } else {
            this.notification.add(_t("All the quality checks have been done"));
        }
    },
});
