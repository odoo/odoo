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
            [[this.resId || this.env.model.record.id]],
            { context: { barcode_trigger: true } }
        );
        if (typeof res === 'object' && res !== null) {
            return this.action.doAction(res, {
                onClose: async () => {
                    await this._onRefreshState({ recordId: this.resId });
                    // update lines demand just split to their quantity done to mark them
                    // validated
                    for (const line of this.env.model.pageLines) {
                        if (['pass', 'fail'].includes(line.check_state)) {
                            line.reserved_uom_qty = line.quantity;
                        }
                    }
                    this.env.model.groupLines();
                    this.env.model.trigger("update");
                },
            });
        } else {
            this.notification.add(_t("All the quality checks have been done"));
        }
    },

    async onDemandQualityCheck() {
        await this.env.model.save();
        const res = await this.orm.call(this.resModel, "action_open_on_demand_quality_check",
            [[this.resId]]
        );
        if (typeof res === 'object' && res !== null) {
            return this.action.doAction(res, {
                onClose: this._onRefreshState.bind(this, { recordId: this.resId }),
            });
        }
    }
});
