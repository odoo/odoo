import { SaleOrderLineProductField } from "@sale/js/sale_product_field";
import { x2ManyCommands } from "@web/core/orm_service";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";


patch(SaleOrderLineProductField.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
    },
    get isEventBooth() {
        return this.props.record.data.service_tracking === "event_booth";
    },
    get hasConfigurationButton() {
        return super.hasConfigurationButton || this.isEventBooth;
    },
    onEditConfiguration() {
        if (this.isEventBooth) {
            this._openEventBoothConfigurator(true);
        } else {
            super.onEditConfiguration();
        }
    },
    _onProductUpdate() {
        if (this.isEventBooth) {
            this._openEventBoothConfigurator(false);
        } else {
            super._onProductUpdate();
        }
    },
    async _openEventBoothConfigurator(edit) {
        const actionContext = {
            default_product_id: this.props.record.data.product_id.id,
        };
        if (edit) {
            const recordData = this.props.record.data;
            if (recordData.event_id) {
                actionContext.default_event_id = recordData.event_id.id;
            }
            if (recordData.event_booth_category_id) {
                actionContext.default_event_booth_category_id = recordData.event_booth_category_id.id;
            }
            if (recordData.event_booth_pending_ids) {
                actionContext.default_event_booth_ids = recordData.event_booth_pending_ids.currentIds.map(
                    (resId) => [4, resId]
                );
            }
        }
        this.action.doAction(
            'event_booth_sale.event_booth_configurator_action',
            {
                additionalContext: actionContext,
                onClose: async (closeInfo) => {
                    if (!closeInfo?.eventBoothConfiguration || closeInfo.special || closeInfo.dismiss) {
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
