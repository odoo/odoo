import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { Component, useState } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { CustomListView } from "@point_of_sale/app/components/custom_list_view/custom_list_view";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class PartnerList extends Component {
    static components = { PartnerLine, Dialog, Input, CustomListView, Dropdown, DropdownItem };
    static template = "point_of_sale.PartnerList";
    static props = {
        partner: {
            optional: true,
            type: [{ value: null }, Object],
        },
        getPayload: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        this.state = useState({
            query: null,
            previousQuery: "",
            currentOffset: 0,
        });
        useHotkey("enter", () => this.onEnter());
    }
    async editPartner(p = false) {
        const partner = await this.pos.editPartner(p);
        if (partner) {
            this.clickPartner(partner);
        }
    }
    async onEnter() {
        const result = await this.searchPartner();
        if (result.length > 0) {
            this.notification.add(
                _t('%s customer(s) found for "%s".', result.length, this.state.query),
                3000
            );
        } else {
            this.notification.add(_t('No more customer found for "%s".', this.state.query));
        }
    }

    goToOrders(partner) {
        this.props.close();
        const partnerHasActiveOrders = this.pos
            .get_open_orders()
            .some((order) => order.partner?.id === partner.id);
        const stateOverride = {
            search: {
                fieldName: "PARTNER",
                searchTerm: partner.name,
            },
            filter: partnerHasActiveOrders ? "" : "SYNCED",
        };
        this.pos.showScreen("TicketScreen", { stateOverride });
    }

    confirm() {
        this.props.resolve({ confirmed: true, payload: this.state.selectedPartner });
        this.pos.closeTempScreen();
    }
    get isBalanceDisplayed() {
        return false;
    }
    clickPartner(partner) {
        if (partner && this.pos.get_order().partner_id?.id === partner.id) {
            partner = null;
        }

        this.props.getPayload(partner);
        this.props.close();
    }
    async searchPartner() {
        if (this.state.previousQuery != this.state.query) {
            this.state.currentOffset = 0;
        }
        const partner = await this.getNewPartners();

        if (this.state.previousQuery == this.state.query) {
            this.state.currentOffset += partner.length;
        } else {
            this.state.previousQuery = this.state.query;
            this.state.currentOffset = partner.length;
        }
        return partner;
    }
}
