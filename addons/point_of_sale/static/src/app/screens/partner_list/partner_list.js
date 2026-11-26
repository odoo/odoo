import { Component, computed, markRaw, proxy, signal, t, useListener, useProps } from "@odoo/owl";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ResPartner } from "@point_of_sale/app/models/res_partner";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { Dialog } from "@web/core/dialog/dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { localeCompare, normalize } from "@web/core/l10n/utils";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

const DISPLAY_LIMIT_STEP = 100;
const MAX_DISPLAY_LIMIT = 1000;

export class PartnerList extends Component {
    static components = { PartnerLine, Dialog, Input };
    static template = "point_of_sale.PartnerList";
    props = useProps({
        partner: t.or([t.instanceOf(ResPartner), t.literal(null)]).optional(),
        getPayload: t.function(),
        close: t.function(),
        order: t.instanceOf(PosOrder).optional(),
    });

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.modalRef = signal.ref();
        this.modalContent = computed(() => this.modalRef()?.querySelector(".modal-body") ?? null);
        this.searchInputRef = signal.ref();
        const initialPartners = this.pos.models["res.partner"].toRaw().filter((p) => {
            const par = p.property_account_receivable_id;
            return !par || par.non_trade !== true;
        });
        this.sortedInitialPartners = markRaw(
            initialPartners
                .slice(0, MAX_DISPLAY_LIMIT)
                .toSorted((a, b) =>
                    this.props.partner?.id === a.id
                        ? -1
                        : this.props.partner?.id === b.id
                        ? 1
                        : localeCompare(a.name, b.name)
                )
        );
        this.state = proxy({
            initialPartners: markRaw(initialPartners),
            loadedPartners: [],
            query: "",
            loading: false,
            displayLimit: DISPLAY_LIMIT_STEP,
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
            const maxLocalDisplay = Math.min(this.state.initialPartners.length, MAX_DISPLAY_LIMIT);
            if (!this.state.query?.trim() && this.state.displayLimit < maxLocalDisplay) {
                this.state.displayLimit = Math.min(
                    this.state.displayLimit + DISPLAY_LIMIT_STEP,
                    maxLocalDisplay
                );
                return;
            }
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
    getPartners(partners, limit = MAX_DISPLAY_LIMIT) {
        const searchWord = normalize(this.state.query?.trim() ?? "");
        if (!searchWord) {
            if (partners === this.state.initialPartners) {
                return this.sortedInitialPartners.slice(0, limit);
            }
            return partners
                .slice(0, MAX_DISPLAY_LIMIT)
                .toSorted((a, b) =>
                    this.props.partner?.id === a.id
                        ? -1
                        : this.props.partner?.id === b.id
                        ? 1
                        : localeCompare(a.name, b.name)
                )
                .slice(0, limit);
        }

        const exactMatches = partners.filter((partner) => partner.exactMatch(searchWord));
        if (exactMatches.length > 0) {
            return exactMatches;
        }

        const numberString = searchWord.replace(/[+\s()-]/g, "");
        const isSearchWordNumber = /^[0-9]+$/.test(numberString);
        const patternBase = isSearchWordNumber ? numberString : searchWord;
        const regex = new RegExp(
            patternBase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/%/g, ".*")
        );

        const availablePartners = [];
        for (const partner of partners) {
            if (regex.test(partner.searchString)) {
                availablePartners.push(partner);
                if (availablePartners.length === 50) {
                    break;
                }
            }
        }
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

            this.globalState.offsetBySearch[query] =
                offset + (modelLimit["res.partner"] || this.pos.config._limited_partner_count);

            for (const partner of result["res.partner"]) {
                if (!this.loadedPartnerIds.has(partner.id)) {
                    this.loadedPartnerIds.add(partner.id);
                    this.state.loadedPartners.push(partner);
                }
            }

            return result["res.partner"];
        } catch {
            return [];
        } finally {
            this.state.loading = false;
        }
    }
}
