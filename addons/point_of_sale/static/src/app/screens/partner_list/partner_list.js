/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@point_of_sale/utils";
import { Dialog } from "@web/core/dialog/dialog";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { Component, useState } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { unaccent } from "@web/core/utils/strings";

export class PartnerList extends Component {
    static components = { PartnerLine, Dialog, Input };
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
    async onEnter() {
        if (!this.state.query) {
            return;
        }
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
            .get_order_list()
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
    getPartners() {
        const partners = this.state.query?.trim?.()?.length
            ? fuzzyLookup(
                  unaccent(this.state.query.trim(), false),
                  this.pos.models["res.partner"].getAll(),
                  (partner) => unaccent(partner.searchString, false)
              )
            : this.pos.models["res.partner"].getAll().slice(0, 1000);
        return partners.toSorted((a, b) =>
            this.props.partner?.id === a.id ? -1 : a.name.localeCompare(b.name)
        );
    }
    get isBalanceDisplayed() {
        return false;
    }
    clickPartner(partner) {
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
    async getNewPartners() {
        let domain = [];
        const limit = 30;
        if (this.state.query) {
            const search_fields = ["name", "parent_name", "phone_mobile_search", "email"];
            domain = [
                ...Array(search_fields.length - 1).fill("|"),
                ...search_fields.map((field) => [field, "ilike", this.state.query + "%"]),
            ];
        }

        const result = await this.pos.data.searchRead("res.partner", domain, [], {
            limit: limit,
            offset: this.state.currentOffset,
        });

        return result;
    }
}
