/** @odoo-module **/

import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { x2ManyCommands } from "@web/core/orm_service";
import { patch } from "@web/core/utils/patch";


patch(SaleOrderLineProductField.prototype, {

    async _onProductUpdate() {
        super._onProductUpdate(...arguments);
        if (this.props.record.data.product_type === 'event_booth') {
            this._openEventBoothConfigurator(false);
        }
    },

    _editLineConfiguration() {
        super._editLineConfiguration(...arguments);
        if (this.props.record.data.product_type === 'event_booth') {
            this._openEventBoothConfigurator(true);
        }
    },

    get isConfigurableLine() {
        return super.isConfigurableLine || this.props.record.data.product_type === 'event_booth';
    },

    async _openEventBoothConfigurator(edit) {
        let actionContext = {
            default_product_id: this.props.record.data.product_id[0],
        };
        if (edit) {
            const recordData = this.props.record.data;
            if (recordData.event_id) {
                actionContext.default_event_id = recordData.event_id[0];
            }
            if (recordData.event_booth_category_id) {
                actionContext.default_event_booth_category_id = recordData.event_booth_category_id[0];
            }
            if (recordData.event_booth_pending_ids) {
                actionContext.default_event_booth_ids = recordData.event_booth_pending_ids.records.map(
                    record => {
                        return [4, record.resId];
                    }
                );
            }
        }
        this.action.doAction(
            'event_booth_sale.event_booth_configurator_action',
            {
                additionalContext: actionContext,
                onClose: async (closeInfo) => {
                    if (!closeInfo || closeInfo.special) {
                        // wizard popup closed or 'Cancel' button triggered
                        if (!this.props.record.data.event_ticket_id) {
                            // remove product if event configuration was cancelled.
                            this.props.record.update({
                                [this.props.name]: undefined,
                            });
                        }
                    } else {
                        const { event_id, event_booth_category_id, event_booth_pending_ids } =
                            closeInfo.eventBoothConfiguration;
                        this.props.record.update({
                            event_id,
                            event_booth_category_id,
                            event_booth_pending_ids: [x2ManyCommands.set(event_booth_pending_ids)],
                        });
                    }
                }
            }
        );
    },
});
