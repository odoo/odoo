/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';


patch(SaleOrderLineProductField.prototype, 'event_sale', {

    async _onProductUpdate() {
        this._super(...arguments);
        if (this.props.record.data.product_type === 'event') {
            this._openEventConfigurator();
        }
    },

    _editLineConfiguration() {
        this._super(...arguments);
        if (this.props.record.data.product_type === 'event') {
            this._openEventConfigurator();
        }
    },

    get isConfigurableLine() {
        return this._super(...arguments) || Boolean(this.props.record.data.event_ticket_id);
    },

    async _openEventConfigurator() {
        let actionContext = {
            'default_product_id': this.props.record.data.product_id[0],
        };
        if (this.props.record.data.event_id) {
            actionContext.default_event_id = this.props.record.data.event_id[0];
        }
        if (this.props.record.data.event_ticket_id) {
            actionContext.default_event_ticket_id = this.props.record.data.event_ticket_id[0];
        }
        this.action.doAction(
            'event_sale.event_configurator_action',
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
                        const eventConfiguration = closeInfo.eventConfiguration;
                        this.props.record.update(eventConfiguration);
                    }
                }
            }
        );
    },
});
