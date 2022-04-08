/** @odoo-module **/

import ControlPanelX2Many from 'web.ControlPanelX2Many';
import { FieldOne2Many } from 'web.relational_fields';
import fieldRegistry from 'web.field_registry';

export class LoyaltyControlPanelX2Many extends ControlPanelX2Many {
}

LoyaltyControlPanelX2Many.props = Object.assign({}, ControlPanelX2Many.props, {
    label: String,
});
LoyaltyControlPanelX2Many.template = 'LoyaltyControlPanelX2Many';

export const LoyaltyFieldOne2Many = FieldOne2Many.extend({
    /**
     * @override
     * @private
     */
    _getControlPanelComponent: function () {
        return LoyaltyControlPanelX2Many;
    },
    /**
     * @override
     * @private
     */
     _getControlPanelContext: function () {
        const context = this._super.apply(this);
        Object.assign(context, {
            label: this.string,
        });
        return context;
     }
});

fieldRegistry.add('loyalty_one2many', LoyaltyFieldOne2Many);
