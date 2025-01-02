import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { Dialog } from "@web/core/dialog/dialog";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import { Component, useEffect, useRef, useState } from "@odoo/owl";
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
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.list = useRef("partner-list");

        this.state = useState({
            initialPartners: new Set(this.pos.models["res.partner"].getAll()),
            loadedPartners: new Set(),
            query: "",
            loading: false,
        });
        useHotkey("enter", () => this.onEnter(), {
            bypassEditableProtection: true,
        });

        useEffect(
            () => {
                if (!this.list || !this.list.el) {
                    return;
                }

                const scrollMethod = this.onScroll.bind(this);
                this.list.el.addEventListener("scroll", scrollMethod);
                return () => {
                    this.list.el.removeEventListener("scroll", scrollMethod);
                };
            },
            () => [this.list]
        );
    }
    get globalState() {
        return this.pos.screenState.partnerList;
    }
    onScroll(ev) {
        const height = this.list.el.offsetHeight;
        const bottomScrollPosition = Math.ceil(this.list.el.scrollTop + height + 10);

        if (this.list.el.scrollHeight < bottomScrollPosition) {
            this.getNewPartners();
        }
    }
    async editPartner(p = false) {
        const partner = await this.pos.editPartner(p);
        if (partner) {
            this.clickPartner(partner);
        }
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
            .getOpenOrders()
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
    getPartners(partnersSet) {
        const partners = Array.from(partnersSet);
        const searchWord = unaccent((this.state.query || "").trim(), false);
        const exactMatches = partners.filter((partner) => partner.exactMatch(searchWord));

        if (exactMatches.length > 0) {
            return exactMatches;
        }

        const availablePartners = searchWord
            ? fuzzyLookup(searchWord, partners, (partner) => unaccent(partner.searchString, false))
            : partners
                  .slice(0, 1000)
                  .toSorted((a, b) =>
                      this.props.partner?.id === a.id
                          ? -1
                          : this.props.partner?.id === b.id
                          ? 1
                          : (a.name || "").localeCompare(b.name || "")
                  );

        return availablePartners;
    }
    get isBalanceDisplayed() {
        return false;
    }
    clickPartner(partner) {
        this.props.getPayload(partner);
        this.props.close();
    }
    async searchPartner() {
        const partner = await this.getNewPartners();
        return partner;
    }
    async getNewPartners() {
        let domain = [];
        const offset = this.globalState.offsetBySearch[this.state.query] || 0;

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

        try {
            this.state.loading = true;
            const result = await this.pos.data.callRelated("res.partner", "get_new_partner", [
                this.pos.config.id,
                domain,
                offset,
            ]);

            this.globalState.offsetBySearch[this.state.query] =
                offset + (result["res.partner"].length || 100);
            this.state.loadedPartners = new Set([
                ...this.state.loadedPartners,
                ...result["res.partner"],
            ]);

            return result;
        } catch {
            this.state.loading = false;
            return [];
        }
    }
}
