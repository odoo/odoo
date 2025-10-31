import { patch } from "@web/core/utils/patch";
import { SaleOrderLineProductField } from "@sale/js/sale_product_field";
import { useService } from "@web/core/utils/hooks";

patch(SaleOrderLineProductField.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
    },
    get isEvent() {
        return this.props.record.data.service_tracking === "event";
    },
    get hasConfigurationButton() {
        return super.hasConfigurationButton || this.isEvent;
    },
    onEditConfiguration() {
        if (this.isEvent) {
            this._openEventConfigurator();
        } else {
            super.onEditConfiguration();
        }
    },
    _onProductUpdate() {
        if (this.isEvent) {
            this._openEventConfigurator();
        } else {
            super._onProductUpdate();
        }
    },
    async _openEventConfigurator() {
        const actionContext = {
            default_product_id: this.props.record.data.product_id.id,
        };
        if (this.props.record.data.event_id) {
            actionContext.default_event_id = this.props.record.data.event_id.id;
        }
        if (this.props.record.data.event_slot_id) {
            actionContext.default_event_slot_id = this.props.record.data.event_slot_id[0];
        }
        if (this.props.record.data.event_ticket_id) {
            actionContext.default_event_ticket_id = this.props.record.data.event_ticket_id.id;
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
                        const eventTicketInfo = closeInfo.eventTicketInfo;
                        const soLineVirtualId = this.props.record._virtualId;
                        this.props.record.update({
                            ...eventConfiguration,
                            virtual_id: soLineVirtualId,
                        });
                        if (eventTicketInfo?.additional_product_ids) {
                            const quantity = this.props.record.data.product_uom_qty;
                            await eventTicketInfo.additional_product_ids.currentIds.map(async productId => {
                                const line = await this.props.record.model.root.data.order_line.addNewRecord({
                                    position: 'bottom'
                                });
                                await line.update({
                                    product_id: { id: productId },
                                    product_uom_qty: quantity,
                                    linked_virtual_id: soLineVirtualId,
                                });
                                this.props.record.model.root.data.order_line.leaveEditMode();
                            });
                            this.props.record.model.root.data.order_line.leaveEditMode();
                        }
                    }
                }
            }
        );
    },
});
