/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';


patch(SaleOrderLineProductField.prototype, 'event_booth_sale', {

    _configureBoothProduct() {
        const configureProduct = this._super(...arguments);
        if (!configureProduct && this.props.record.data.product_type === 'event_booth') {
            return this._openEventBoothConfigurator(false);
        }
    },

    _editLineConfiguration() {
        this._super(...arguments);
        if (this.props.record.data.product_type === 'event_booth') {
            const configurator = this._openEventBoothConfigurator(true);
            configurator();
        }
    },

    get isConfigurableLine() {
        return this._super(...arguments) || Boolean(this.props.record.data.product_type == 'event_booth');
    },

    _openEventBoothConfigurator(edit) {
        return async() => {
            let actionContext = {
                'default_product_id': this.props.record.data.product_id[0],
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
                            return [4, record.data.id];
                        }
                    );
                }
            }

            await new Promise((resolve, reject) => {
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
                                        event_id: undefined,
                                    });
                                }
                            } else {
                                const eventBoothConfiguration = closeInfo.eventBoothConfiguration;
                                this.props.record.update({
                                    event_id: eventBoothConfiguration.event_id,
                                    event_booth_category_id: eventBoothConfiguration.event_booth_category_id,
                                    event_booth_pending_ids: eventBoothConfiguration.event_booth_pending_ids,
                                });
                            }
                            resolve();
                        }
                    }
                );
            });
        }
    },
});
