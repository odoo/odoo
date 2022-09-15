/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';


patch(SaleOrderLineProductField.prototype, 'event_sale', {

    _onFieldUpdate() {
        this._super(...arguments);
        if (this.props.record.data.product_type === 'event') {
            this._openEventConfigurator();
        }
    },

    _editLineConfiguration() {
        this._super(...arguments);
        if (this.isEventLine) {
            this._openEventConfigurator(this.props);
        }
    },

    get isConfigurableLine() {
        return this._super(...arguments) || Boolean(this.props.record.data.event_ticket_id)
    },

    // maybe not useful to have isEventLine prop
    get isEventLine() {
        return Boolean(this.props.record.data.product_type === 'event');
    },

    async _openEventConfigurator() {
        let actionContext = {
            'default_product_id': this.props.record.data.product_id[0],
        };
        if (this.props.record.data.event_id) {
            actionContext['default_event_id'] = this.props.record.data.event_id[0];
        }
        if (this.props.record.data.event_ticket_id) {
            actionContext['default_event_ticket_id'] = this.props.record.data.event_ticket_id[0];
        }
        this.action.doAction(
            // TODO VFE see if we can drop the action record
            // and use static values here.
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
                        // do not reopen the wizard because of the record update.
                        const eventConfiguration = closeInfo.eventConfiguration;
                        this.props.record.update({
                            'event_id': [eventConfiguration.event_id.id, 'dunno'],
                            'event_ticket_id': [eventConfiguration.event_ticket_id.id, 'don\'t care'],
                        });
                    }
                }
            }
        );
    },
});
