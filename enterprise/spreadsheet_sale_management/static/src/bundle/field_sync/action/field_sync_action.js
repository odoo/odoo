import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { range } from "@web/core/utils/numbers";
import { WarningDialog } from "@web/core/errors/error_dialogs";

import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { VersionHistoryAction } from "@spreadsheet_edition/bundle/actions/version_history/version_history_action";

import { onWillUnmount, useSubEnv } from "@odoo/owl";
import {
    addSpreadsheetFieldSyncExtensionWithCleanUp,
    useSpreadsheetFieldSyncStore,
} from "../field_sync_extension_hook";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetName } from "@spreadsheet_edition/bundle/actions/control_panel/spreadsheet_name";
import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";
import { VersionHistorySidePanel } from "@spreadsheet_edition/bundle/actions/version_history/side_panel/version_history_side_panel";

class SpreadsheetComponentSync extends SpreadsheetComponent {
    setup() {
        super.setup();
        useSpreadsheetFieldSyncStore();
    }
}
export class FieldSyncVersionHistoryAction extends VersionHistoryAction {
    static components = {
        SpreadsheetComponent: SpreadsheetComponentSync,
        SpreadsheetName,
        SpreadsheetNavbar,
        VersionHistorySidePanel,
    };
    setup() {
        addSpreadsheetFieldSyncExtensionWithCleanUp(onWillUnmount);
        super.setup();
    }
}

export class SpreadsheetFieldSyncAction extends AbstractSpreadsheetAction {
    static template = "spreadsheet_sale_management.SpreadsheetFieldSyncAction";
    static path = "sale-order-spreadsheet";

    resModel = "sale.order.spreadsheet";
    threadField = "sale_order_spreadsheet_id";

    setup() {
        super.setup();
        this.notificationMessage = _t("New quote calculator created");
        useSubEnv({
            makeCopy: this.makeCopy.bind(this),
            showHistory: this.showHistory.bind(this),
        });
        addSpreadsheetFieldSyncExtensionWithCleanUp(onWillUnmount);
        useSpreadsheetFieldSyncStore();
    }

    async execInitCallbacks() {
        await super.execInitCallbacks();
        /**
         * Upon the first time we open the spreadsheet we want to resize the columns
         * of the main list to fit all the data.
         * The catch is we need to have the list data loaded to know the content and resize
         * the columns accordingly.
         */
        if (
            this.spreadsheetData.revisionId === "START_REVISION" &&
            this.stateUpdateMessages.length === 1
        ) {
            const list = this.model.getters.getMainSaleOrderLineList();
            const listDataSource = this.model.getters.getListDataSource(list.id);
            await listDataSource.load();
            this.model.dispatch("AUTORESIZE_COLUMNS", {
                sheetId: this.model.getters.getActiveSheetId(),
                cols: range(0, list.columns.length),
            });
        }
    }

    async writeToOrder() {
        const { commands, errors } = await this.model.getters.getFieldSyncX2ManyCommands();
        if (errors.length) {
            this.dialog.add(WarningDialog, {
                title: _t("Unable to save"),
                message: errors.join("\n\n"),
            });
        } else {
            await this.orm.write("sale.order", [this.orderId], {
                order_line: commands,
            });
            this.env.config.historyBack();
        }
    }

    /**
     * @override
     */
    _initializeWith(data) {
        super._initializeWith(data);
        this.orderId = data.order_id;
        const orderFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "sale.order"
        );
        if (orderFilter && this.orderId) {
            orderFilter.defaultValue = [this.orderId];
        }
    }

    showHistory() {
        this.actionService.doAction(
            {
                type: "ir.actions.act_url",
                target: "new",
                tag: "action_sale_order_spreadsheet_history",
                url: `/odoo/sale-order-spreadsheet-history?spreadsheet_id=${this.resId}&res_model=${this.resModel}`,
            },
            { newWindow: true }
        );
    }
}

registry
    .category("actions")
    .add("action_sale_order_spreadsheet", SpreadsheetFieldSyncAction, { force: true })
    .add("action_sale_order_spreadsheet_history", FieldSyncVersionHistoryAction, { force: true });
