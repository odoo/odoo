/** @odoo-module */

import { useBus } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { ListController } from "@web/views/list/list_controller";

export class InventoryReportListController extends ListController {
    setup() {
        super.setup();
        if (this.props.context.inventory_mode || this.props.context.inventory_report_mode) {
            useBus(this.model, "record-updated", this.recordUpdated);
        }
    }

    /**
     * Handler called when the user clicked on the 'Valuation at Date' button.
     * Opens wizard to display, at choice, the products inventory or a computed
     * inventory at a given date.
     */
    async onClickInventoryAtDate() {
        const context = {
            active_model: this.props.resModel,
        };
        if (this.props.context.default_product_id) {
            context.product_id = this.props.context.default_product_id;
        } else if (this.props.context.product_tmpl_id) {
            context.product_tmpl_id = this.props.context.product_tmpl_id;
        }
        this.actionService.doAction({
            res_model: "stock.quantity.history",
            views: [[false, "form"]],
            target: "new",
            type: "ir.actions.act_window",
            context,
        });
    }

    getActionMenuItems() {
        const actionMenus = super.getActionMenuItems();
        if (this.props.resModel === "stock.quant" && (!this.props.context.inventory_mode || this.props.context.inventory_report_mode)) {
            // hack so we don't show some of the default actions when it's inappropriate to
            const {print, action, other} = actionMenus;
            return Object.assign(
                {},
                print.filter(a => a.name !== 'Count Sheet'),
                action.filter(a => a.name !== 'Set'),
                { other: other },
                );
        }
        return actionMenus;
    }

    /**
     * Handler called when a record has been created or updated.
     * We need to detect when the user added to the list a quant which already exists
     * (see stock.quant.create), either already loaded or not, to warn the user
     * the quant was updated.
     * This is done by checking :
     * - the record id against the 'lastCreatedRecordId' on model
     * - the create_date against the write_date (both are equal for newly created records).
     *
     * @param {CustomEvent<{ record: Record, relatedRecords: Record[] }>} event
     */
    async recordUpdated(event) {
        const { record, relatedRecords } = event.detail;
        const justCreated = record.id == record.model.lastCreatedRecordId;
        if (justCreated && record.data.create_date.diff(record.data.write_date) != 0) {
            this.notificationService.add(
                this.env._t(
                    "You tried to create a record that already exists. The existing record was modified instead."
                ),
                { title: this.env._t("This record already exists.") }
            );
            if (relatedRecords.length > 0) {
                /* more than 1 'resId' record loaded in view (user added an already loaded record) :
                 * - both have been updated
                 * - remove the current record (the added one)
                 */
                this.model.root.removeRecord(record);
            }
        }
    }

    /**
     * Handler called when the user clicked on the 'Apply all' button.
     */
    async onClickApplyAll() {
        const activeIds = await this.model.orm.search(this.props.resModel, this.props.domain, {
            limit: session.active_ids_limit,
            context: this.props.context,
        });
        return this.actionService.doAction("stock.action_stock_inventory_adjustement_name", {
            additionalContext: {
                active_ids: activeIds,
            },
            onClose: () => {
                this.model.load();
            },
        });
    }
}
