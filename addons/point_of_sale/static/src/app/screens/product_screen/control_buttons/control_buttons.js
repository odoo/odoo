import { Component, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { OrderlineNoteButton } from "@point_of_sale/app/screens/product_screen/control_buttons/customer_note_button/customer_note_button";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";

export class ControlButtons extends Component {
    static template = "point_of_sale.ControlButtons";
    static components = { OrderlineNoteButton, SelectPartnerButton };
    static props = {
        showRemainingButtons: { type: Boolean, optional: true },
        onClickMore: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };
    static defaultProps = {
        showRemainingButtons: false,
    };
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    }
    get partner() {
        return this.pos.get_order()?.get_partner();
    }
    get currentOrder() {
        return this.pos.get_order();
    }
    async clickFiscalPosition() {
        const currentFiscalPosition = this.currentOrder.fiscal_position_id;
        const fiscalPosList = [
            {
                id: -1,
                label: this.pos.config.module_pos_restaurant ? _t("Dine in") : _t("Original Tax"),
                isSelected: false,
                item: "none",
            },
        ];
        for (const fiscalPos of this.pos.config.fiscal_position_ids) {
            fiscalPosList.push({
                id: fiscalPos.id,
                label: fiscalPos.name,
                isSelected: currentFiscalPosition
                    ? fiscalPos.id === currentFiscalPosition.id
                    : false,
                item: fiscalPos,
            });
        }

        const selectedFiscalPosition = await makeAwaitable(this.dialog, SelectionPopup, {
            list: fiscalPosList,
            title: _t("Choose the tax you want to apply"),
        });

        if (!selectedFiscalPosition) {
            return;
        }

        if (selectedFiscalPosition === "none") {
            this.currentOrder.update({
                fiscal_position_id: false,
            });
            return;
        }

        this.currentOrder.update({
            fiscal_position_id: selectedFiscalPosition ? selectedFiscalPosition.id : false,
        });
    }
    /**
     * Create the list to be passed to the SelectionPopup on the `click` function.
     * Pricelist object is passed as item in the list because it
     * is the object that will be returned when the popup is confirmed.
     * @returns {Array}
     */
    getPricelistList() {
        const selectionList = this.pos.config.available_pricelist_ids.map((pricelist) => ({
            id: pricelist.id,
            label: pricelist.name,
            isSelected:
                this.currentOrder.pricelist_id &&
                pricelist.id === this.currentOrder.pricelist_id.id,
            item: pricelist,
        }));

        if (!this.pos.config.pricelist_id) {
            selectionList.push({
                id: null,
                label: _t("Default Price"),
                isSelected: !this.currentOrder.pricelist_id,
                item: null,
            });
        }
        return selectionList;
    }
    async clickPricelist() {
        const selectionList = this.getPricelistList();
        const payload = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Select the pricelist"),
            list: selectionList,
        });

        if (payload) {
            this.pos.selectPricelist(payload);
        }
    }

    clickRefund() {
        const order = this.pos.get_order();
        const partner = order.get_partner();
        const searchDetails = partner ? { fieldName: "PARTNER", searchTerm: partner.name } : {};
        this.pos.showScreen("TicketScreen", {
            stateOverride: {
                filter: "SYNCED",
                search: searchDetails,
                destinationOrder: order,
            },
        });
    }
    internalNoteLabel(order) {
        if (order) {
            return _t("General Note");
        }
        return this.pos.config.module_pos_restaurant ? _t("Kitchen Note") : _t("Internal Note");
    }

    get buttonClass() {
        return this.props.showRemainingButtons
            ? "btn btn-secondary btn-lg py-5"
            : "btn btn-light btn-lg lh-lg";
    }
}

export class ControlButtonsPopup extends Component {
    static components = { Dialog, ControlButtons };
    static template = xml`
        <Dialog bodyClass="'d-flex flex-column'" footer="false" title="'Actions'" t-on-click="props.close">
            <ControlButtons showRemainingButtons="true" close="props.close"/>
        </Dialog>
    `;
    static props = {
        close: Function,
    };
}
