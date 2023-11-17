/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { OrderlineNoteButton } from "@point_of_sale/app/screens/product_screen/control_buttons/customer_note_button/customer_note_button";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";

export class ControlButtons extends Component {
    static template = "point_of_sale.ControlButtons";
    static components = { OrderlineNoteButton };
    static props = {
        wrapped: { type: Boolean, optional: true },
    };
    static defaultProps = {
        wrapped: true,
    };
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
        this.notification = useService("pos_notification");
    }
    get partner() {
        return this.pos.get_order()?.get_partner();
    }
    get currentOrder() {
        return this.pos.get_order();
    }
    async clickFiscalPosition() {
        const currentFiscalPosition = this.currentOrder.fiscal_position;
        const fiscalPosList = [
            {
                id: -1,
                label: _t("None"),
                isSelected: !currentFiscalPosition,
            },
        ];
        for (const fiscalPos of this.pos.models["account.fiscal.position"].getAll()) {
            fiscalPosList.push({
                id: fiscalPos.id,
                label: fiscalPos.name,
                isSelected: currentFiscalPosition
                    ? fiscalPos.id === currentFiscalPosition.id
                    : false,
                item: fiscalPos,
            });
        }
        this.dialog.add(SelectionPopup, {
            title: _t("Select Fiscal Position"),
            list: fiscalPosList,
            getPayload: (selectedFiscalPosition) => {
                this.currentOrder.set_fiscal_position(selectedFiscalPosition);
                // IMPROVEMENT: The following is the old implementation and I believe
                // there could be a better way of doing it.
                for (const line of this.currentOrder.orderlines) {
                    line.set_quantity(line.quantity);
                }
            },
        });
    }
    async clickPricelist() {
        // Create the list to be passed to the SelectionPopup.
        // Pricelist object is passed as item in the list because it
        // is the object that will be returned when the popup is confirmed.
        const selectionList = this.pos.models["product.pricelist"].map((pricelist) => ({
            id: pricelist.id,
            label: pricelist.name,
            isSelected:
                this.currentOrder.pricelist && pricelist.id === this.currentOrder.pricelist.id,
            item: pricelist,
        }));

        if (!this.pos.default_pricelist) {
            selectionList.push({
                id: null,
                label: _t("Default Price"),
                isSelected: !this.currentOrder.pricelist,
                item: null,
            });
        }

        this.dialog.add(SelectionPopup, {
            title: _t("Select the pricelist"),
            list: selectionList,
            getPayload: (x) => this.currentOrder.set_pricelist(x),
        });
    }

    clickRefund() {
        const order = this.pos.get_order();
        const partner = order.get_partner();
        const searchDetails = partner ? { fieldName: "PARTNER", searchTerm: partner.name } : {};
        this.pos.showScreen("TicketScreen", {
            ui: { filter: "SYNCED", searchDetails },
            destinationOrder: order,
        });
    }
    onClickSave() {
        const orderline = this.pos.get_order().get_selected_orderline();
        if (!orderline) {
            this.notification.add(_t("You cannot save an empty order"), 3000);
            return;
        }
        this._selectEmptyOrder();
        this.notification.add(_t("Order saved for later"), 3000);
    }
    _selectEmptyOrder() {
        const orders = this.pos.get_order_list();
        const emptyOrders = orders.filter((order) => order.is_empty());
        if (emptyOrders.length > 0) {
            this.pos.sendDraftToServer();
            this.pos.set_order(emptyOrders[0]);
        } else {
            this.pos.add_new_order();
        }
    }
}

export class ControlButtonsPopup extends Component {
    static components = { Dialog, ControlButtons };
    static template = xml`
        <Dialog bodyClass="'d-flex flex-column'" footer="false" title="''" t-on-click="props.close">
            <ControlButtons wrapped="false"/>
        </Dialog>
    `;
}
