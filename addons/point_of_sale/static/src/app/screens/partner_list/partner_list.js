/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { fuzzyLookup } from "@point_of_sale/utils";
import { Dialog } from "@web/core/dialog/dialog";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { PartnerEditor } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { Component, useState } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { unaccent } from "@web/core/utils/strings";

export class PartnerList extends Component {
    static components = { PartnerEditor, PartnerLine, Dialog, Input };
    static template = "point_of_sale.PartnerList";
    static props = {
        partner: {
            optional: true,
            type: [{ value: null }, Object],
        },
        missingFields: { type: Array, optional: true, element: String },
        getPayload: { type: Function },
        close: { type: Function },
    };
    static defaultProps = {
        missingFields: [],
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

    goToOrders() {
        this.back(true);
        const partner = this.state.editModeProps.partner;
        const partnerHasActiveOrders = this.pos
            .get_order_list()
            .some((order) => order.partner?.id === partner.id);
        const ui = {
            searchDetails: {
                fieldName: "PARTNER",
                searchTerm: partner.name,
            },
            filter: partnerHasActiveOrders ? "" : "SYNCED",
        };
        this.pos.showScreen("TicketScreen", { ui });
    }

    confirm() {
        this.props.resolve({ confirmed: true, payload: this.state.selectedPartner });
        this.pos.closeTempScreen();
    }
    // Getters

    get_partners_sorted(max_count) {
        const partners = [];
        const resPartner = this.pos.models["res.partner"].getAll();
        max_count = max_count ? Math.min(resPartner.length, max_count) : resPartner.length;

        for (var i = 0; i < max_count; i++) {
            partners.push(this.pos.models["res.partner"].get(resPartner[i].id));
        }

        return partners;
    }

    get_partners_searched() {
        const searchWord = unaccent(this.state.query.trim(), false);
        const partners = this.pos.models["res.partner"].getAll();
        const exactMatches = partners.filter((product) => product.exactMatch(searchWord));

        if (exactMatches.length > 0) {
            return exactMatches;
        }

        return fuzzyLookup(searchWord, partners, (partner) =>
            unaccent(partner.searchString, false)
        );
    }

    get currentOrder() {
        return this.pos.get_order();
    }
    get partners() {
        let res;
        if (this.state.query && this.state.query.trim() !== "") {
            res = this.get_partners_searched();
        } else {
            res = this.get_partners_sorted(1000);
            res.sort(function (a, b) {
                return (a.name || "").localeCompare(b.name || "");
            });
        }
        // the selected partner (if any) is displayed at the top of the list
        if (this.props.partner) {
            const indexOfSelectedPartner = res.findIndex(
                (partner) => partner.id === this.props.partner?.id
            );
            if (indexOfSelectedPartner !== -1) {
                res.splice(indexOfSelectedPartner, 1);
            }
            res.unshift(this.props.partner);
        }
        return res;
    }
    get isBalanceDisplayed() {
        return false;
    }
    clickPartner(partner) {
        this.props.getPayload(partner);
        this.props.close();
    }
    editPartner(partner) {
        this.dialog.add(PartnerEditor, {
            partner: partner || this.props.partner,
            closePartnerList: () => this.props.close(),
        });
    }
    createPartner() {
        // initialize the edit screen with default details about country, state, and lang
        this.editPartner(this.newPartnerDefaults());
    }
    newPartnerDefaults() {
        const { country_id, state_id } = this.pos.company;
        return {
            country_id,
            state_id,
            lang: user.lang,
        };
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
            const search_fields = [
                "name",
                "parent_name",
                "phone_mobile_search",
                "email",
                "barcode",
                "street",
                "zip",
                "city",
                "state_id",
                "country_id",
                "vat",
            ];
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
