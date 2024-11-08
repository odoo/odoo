import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { Dialog } from "@web/core/dialog/dialog";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { Component, onMounted, useState } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { unaccent } from "@web/core/utils/strings";
import { useTrackedAsync } from "@point_of_sale/app/utils/hooks";

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
        this.partnersDisplay = useState(new Map());
        this.partnerListElement = null;
        this.loadNewPartners = useTrackedAsync(() => this.searchPartner());
        this.state = useState({
            query: null,
            previousQuery: "",
            currentOffset: 0,
        });

        useHotkey("enter", () => this.onEnter());
        this.getPartners();

        onMounted(() => {
            this.partnerListElement = document.querySelector(".partner-list");

            if (this.partnerListElement) {
                this.partnerListElement.addEventListener("scroll", this.onScroll.bind(this));
            }
        });
    }
    async editPartner(p = false) {
        const partner = await this.pos.editPartner(p);
        if (partner) {
            this.clickPartner(partner);
        }
    }

    onScroll() {
        if (
            this.partnerListElement.clientHeight + this.partnerListElement.scrollTop >=
            this.partnerListElement.scrollHeight
        ) {
            this.onEnter();
        }
    }

    async onEnter() {
        if (!this.state.query) {
            return;
        }

        if (unaccent((this.state.query || "").trim(), false).length > 1) {
            await this.loadNewPartners.call();
        } else {
            await this.loadNewPartners.call();
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
    getPartners() {
        const searchWord = unaccent((this.state.query || "").trim(), false);
        const partners = this.pos.models["res.partner"].getAll();
        const exactMatches = partners.filter((product) => product.exactMatch(searchWord));
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
                          : (a.name || "").localeCompare(b.name || "")
                  );
        for (const partner of availablePartners) {
            this.partnersDisplay.set(partner.id, partner);
        }
    }

    handleInputChange() {
        this.partnersDisplay = new Map();
        this.getPartners();
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
        this.getPartners();

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
