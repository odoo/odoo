import { Component, computed, proxy, signal, t, useListener, useProps } from "@odoo/owl";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ResPartner } from "@point_of_sale/app/models/res_partner";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { Dialog } from "@web/core/dialog/dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { localeCompare, normalize } from "@web/core/l10n/utils";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

export class PartnerList extends Component {
    static components = { PartnerLine, Dialog, Input };
    static template = "point_of_sale.PartnerList";
    props = useProps({
        partner: t.or([t.instanceOf(ResPartner), t.literal(null)]).optional(),
        getPayload: t.function(),
        close: t.function(),
    });

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.modalRef = signal.ref();
        this.modalContent = computed(() => this.modalRef()?.querySelector(".modal-body") ?? null);
        this.searchInputRef = signal.ref();
        this.state = proxy({
            initialPartners: this.pos.models["res.partner"].filter((p) => {
                const par = p.property_account_receivable_id;
                return !par || par.non_trade !== true;
            }),
            loadedPartners: [],
            query: "",
            loading: false,
        });
        this.loadedPartnerIds = new Set(this.state.initialPartners.map((p) => p.id));
        useHotkey("enter", () => this.onEnter(), {
            bypassEditableProtection: true,
        });
        this.onScroll = debounce(this.onScroll.bind(this), 200);

        useListener(this.modalContent, "scroll", this.onScroll);
    }
    get globalState() {
        return this.pos.screenState.partnerList;
    }
    onScroll(ev) {
        const modalContent = this.modalContent();
        if (this.state.loading || !modalContent) {
            return;
        }
        const height = modalContent.offsetHeight;
        const scrollTop = modalContent.scrollTop;
        const scrollHeight = modalContent.scrollHeight;

        if (scrollTop + height >= scrollHeight * 0.8) {
            this.getNewPartners();
        }
    }
    async editPartner(p = false) {
        if (this.state.query) {
            this.pos.partnerSearchContext = this.state.query;
        }
        try {
            const partner = await this.pos.editPartner(p);
            if (partner) {
                this.clickPartner(partner);
            }
        } finally {
            delete this.pos.partnerSearchContext;
        }
    }
    async onEnter() {
        // The search input uses a debounce, so state.query may lag behind what the user
        // typed. Read the live DOM value and sync it before triggering the server search.
        if (this.searchInputRef()) {
            this.state.query = this.searchInputRef().value;
        }
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
        this.clickPartner(this.props.partner);
        const partnerHasActiveOrders = this.pos
            .getOpenOrders()
            .some((order) => order.partner?.id === partner.id);
        const stateOverride = {
            search: {
                fieldName: "PARTNER",
                searchTerm: partner.name,
                partnerId: partner.id,
            },
            filter: partnerHasActiveOrders ? "" : "SYNCED",
        };
        this.pos.navigate("TicketScreen", { stateOverride });
    }

    confirm() {
        this.props.resolve({ confirmed: true, payload: this.state.selectedPartner });
        this.pos.closeTempScreen();
    }
    getPartners(partners) {
        const searchWord = normalize(this.state.query?.trim() ?? "");
        const exactMatches = partners.filter((partner) => partner.exactMatch(searchWord));

        if (exactMatches.length > 0) {
            return exactMatches;
        }
        const numberString = searchWord.replace(/[+\s()-]/g, "");
        const isSearchWordNumber = /^[0-9]+$/.test(numberString);

        const patternBase = isSearchWordNumber ? numberString : searchWord;
        // Build a RegExp that mimics SQL ILIKE behavior:
        // 1) Escape all RegExp metacharacters so user input is treated literally
        //    (e.g. '.', '+', '[', ']' should not change regex meaning or cause errors)
        // 2) Replace SQL wildcard '%' with RegExp wildcard '.*'
        const regex = new RegExp(
            patternBase
                .replace(/[.*+?^${}()|[\]\\]/g, "\\$&") // escape regex special characters
                .replace(/%/g, ".*") // convert SQL wildcard to regex wildcard
        );

        const availablePartners = searchWord
            ? partners.filter((p) => regex.test(normalize(p.searchString))).slice(0, 50)
            : partners
                  .slice(0, 1000)
                  .toSorted((a, b) =>
                      this.props.partner?.id === a.id
                          ? -1
                          : this.props.partner?.id === b.id
                          ? 1
                          : localeCompare(a.name, b.name)
                  );

        return availablePartners;
    }
    _getSearchFields(query) {
        if (query.includes("@")) {
            return ["email"];
        }
        const stripped = query.replace(/[+\s()\-./]/g, "");
        if (/^\d+$/.test(stripped) && stripped.length >= 3) {
            return ["phone_mobile_search", "barcode", "vat", "zip"];
        }
        return [
            "complete_name",
            "ref",
            "vat",
            "street",
            "zip",
            "email",
            "phone_mobile_search",
            "barcode",
        ];
    }
    get isBalanceDisplayed() {
        return false;
    }
    clickPartner(partner) {
        this.props.getPayload(partner);
        this.state.query = "";
        delete this.pos.partnerSearchContext;
        this.props.close();
    }
    async searchPartner() {
        const partner = await this.getNewPartners();
        return partner;
    }
    async getNewPartners() {
        const query = this.state.query;
        let domain = [];
        const offset = this.globalState.offsetBySearch[query] || 0;
        if (offset > this.loadedPartnerIds.size) {
            return [];
        }
        if (query) {
            const search_fields = this._getSearchFields(query);
            domain = [
                ...Array(search_fields.length - 1).fill("|"),
                ...search_fields.map((field) => [field, "ilike", query]),
            ];
        }

        try {
            this.state.loading = true;

            const modelDomain = {
                "res.partner": domain.length == 0 ? false : domain,
            };
            const modelOffset = {
                "res.partner": offset,
            };
            const modelLimit = {
                "res.partner": domain.length == 0 ? false : 100,
            };
            const result = await this.pos.data.loadRecordsFromPos(
                ["res.partner", "account.fiscal.position"],
                modelDomain,
                modelOffset,
                modelLimit,
                {},
                false
            );

            for (const partner of result["res.partner"]) {
                if (!this.loadedPartnerIds.has(partner.id)) {
                    this.loadedPartnerIds.add(partner.id);
                    this.state.loadedPartners.push(partner);
                }
            }

            this.globalState.offsetBySearch[query] = query
                ? offset + modelLimit["res.partner"]
                : this.loadedPartnerIds.size;

            return result["res.partner"];
        } catch {
            return [];
        } finally {
            this.state.loading = false;
        }
    }
}
