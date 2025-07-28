import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import {
    NoteButton,
    InternalNoteButton,
} from "@point_of_sale/app/screens/product_screen/control_buttons/orderline_note_button/orderline_note_button";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";

export class ControlButtons extends Component {
    static template = "point_of_sale.ControlButtons";
    static components = {
        NoteButton,
        SelectPartnerButton,
        InternalNoteButton,
    };
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
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    }
    get partner() {
        return this.pos.getOrder()?.getPartner();
    }
    get currentOrder() {
        return this.pos.getOrder();
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
        for (const fiscalPos of this.pos.models["pos.config"].getFirst().fiscal_position_ids) {
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
            title: _t("Please register the voucher number"),
        });

        if (!selectedFiscalPosition) {
            return;
        }

        if (selectedFiscalPosition === "none") {
            this.currentOrder.fiscal_position_id = false;
            return;
        }

        this.currentOrder.fiscal_position_id = selectedFiscalPosition
            ? selectedFiscalPosition
            : false;
    }
    /**
     * Create the list to be passed to the SelectionPopup on the `click` function.
     * Pricelist object is passed as item in the list because it
     * is the object that will be returned when the popup is confirmed.
     * @returns {Array}
     */
    getPricelistList() {
        const selectionList = this.pos.models["product.pricelist"].map((pricelist) => ({
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
        const order = this.pos.getOrder();
        const partner = order.getPartner();
        const searchDetails = partner ? { fieldName: "PARTNER", searchTerm: partner.name } : {};
        this.pos.navigate("TicketScreen", {
            stateOverride: {
                filter: "SYNCED",
                search: searchDetails,
                destinationOrder: order,
            },
        });
    }

    get buttonClass() {
        return this.props.showRemainingButtons
            ? this.ui.isSmall
                ? "btn bg-100 btn-md py-2 text-start"
                : "btn btn-secondary btn-lg py-5"
            : "btn btn-secondary btn-lg lh-lg";
    }

    displayProductInfoBtn() {
        const selectedOrderLine = this.currentOrder?.getSelectedOrderline();
        return (
            selectedOrderLine &&
            selectedOrderLine.product_id.product_tmpl_id &&
            !this.pos
                .getExcludedProductIds()
                .includes(selectedOrderLine.product_id.product_tmpl_id.id)
        );
    }
}

export class ControlButtonsPopup extends Component {
    static components = { Dialog, ControlButtons };
    static template = "point_of_sale.ControlButtonsPopup";
    static props = {
        close: Function,
    };
}
