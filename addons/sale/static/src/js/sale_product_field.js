/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Many2OneField } from '@web/views/fields/many2one/many2one_field';

const { onWillUpdateProps } = owl;


export class SaleOrderLineProductField extends Many2OneField {

    setup() {
        super.setup();
        // TODO see with SAD for a better hook to catch field updates
        // TODO inheritance (cf event_sale)
        // TODO how to trigger updates on all lines/parent record (matrix)
        // TODO how to customize return information from wizard ?
        //      can't we have a generic way to avoid the need of custom controller/code ???

        onWillUpdateProps(async (nextProps) => {
            if (
                nextProps.record.mode === 'edit' &&
                nextProps.value && (
                    !this.props.value ||
                    this.props.value[0] != nextProps.value[0]
                )
            ) {
                // Field was updated if line was open in edit mode
                // field is not emptied
                // new value is different than existing value.
                this._onFieldUpdate(nextProps);
            }
        });
    }

    get hasConfigurationButton() {
        return this.isConfigurableLine || this.isConfigurableTemplate;
    }

    get configurationButtonHelp() {
        return this.env._t("Edit Configuration");
    }

    get ConfigurationButtonIcon() {
        return 'btn btn-secondary fa fa-pencil';
    }

    _onFieldUpdate(nextProps) {
        if (this.configuratorFeedback) {
            this.configuratorFeedback = false;
        } else if (nextProps.record.data.product_type === 'event') {
            this._openEventConfigurator(nextProps);
        }
    }

    onEditConfiguration() {
        if (this.isConfigurableLine) {
            this._editLineConfiguration();
        } else {
            this._editProductConfiguration();
        }
    }

    get isConfigurableLine() {
        // TODO TEST configuration update
        //this.props.record.data ?
        const event_sale_value = Boolean(this.props.record.data.event_ticket_id)
        return false || event_sale_value;
    }

    get isConfigurableTemplate() {
        return false;
    }

    _editLineConfiguration() {
        // event_sale, sale_renting
        if (this.isEventLine) {
            this._openEventConfigurator(this.props);
        }
    }

    _editProductConfiguration() { } // sale_product_configurator, sale_product_matrix

    // event_sale logic
    get isEventLine() {
        return Boolean(this.props.record.data.product_type === 'event');
    }

    async _openEventConfigurator(props) {
        let actionContext = {
            'default_product_id': props.record.data.product_id[0],
        };
        if (props.record.data.event_id) {
            actionContext['default_event_id'] = props.record.data.event_id[0];
        }
        if (props.record.data.event_ticket_id) {
            actionContext['default_event_ticket_id'] = props.record.data.event_ticket_id[0];
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
                        if (!props.record.data.event_ticket_id) {
                            // remove product if event configuration was cancelled.
                            this.props.record.update({
                                [props.name]: undefined,
                            });
                        }
                    } else {
                        // do not reopen the wizard because of the record update.
                        this.configuratorFeedback = true;
                        const eventConfiguration = closeInfo.eventConfiguration;
                        this.props.record.update({
                            'event_id': [eventConfiguration.event_id.id, 'dunno'],
                            'event_ticket_id': [eventConfiguration.event_ticket_id.id, 'don\'t care'],
                        });
                    }
                }
            }
        );
    }
}

SaleOrderLineProductField.template = "sale.SaleProductField";

registry.category("fields").add("sol_product_many2one", SaleOrderLineProductField);
