import { useLayoutEffect } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import { Component, proxy } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { localeCompare, normalize } from "@web/core/l10n/utils";
import { debounce } from "@web/core/utils/timing";

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
        this.modalRef = useChildRef();
        this.modalContent = null;
        this.state = proxy({
            partners: new Map(),
            query: "",
            loading: false,
        });
        useHotkey("enter", () => this.onEnter(), {
            bypassEditableProtection: true,
        });
        this.onScroll = debounce(this.onScroll.bind(this), 200);

        useLayoutEffect(
            () => {
                if (!this.modalRef.el) {
                    return;
                }

                if (!this.modalContent) {
                    this.modalContent = this.modalRef.el.querySelector(".modal-body");
                }

                const scrollMethod = this.onScroll.bind(this);
                this.modalContent.addEventListener("scroll", scrollMethod);
                return () => {
                    this.modalContent.removeEventListener("scroll", scrollMethod);
                };
            },
            () => [this.modalRef.el]
        );
        this.initPartnerLoad();
    }

    async initPartnerLoad() {
        const initialPartners = this.pos.models["res.partner"].filter((p) => {
            const par = p.property_account_receivable_id;
            return !par || par.non_trade !== true;
        });
        this.mergeBatch(initialPartners);

        let safeCount = 0;
        while (this.state.partners.size < 25) {
            const batch = await this.getNewPartners();
            if (batch.length === 0) {
                break;
            }

            safeCount++;
            if (safeCount === 10) {
                break;
            }
        }
    }
    mergeBatch(incoming) {
        const merged = new Map();
        for (const partner of incoming) {
            const key = this.getDeduplicationKey(partner);
            const existing = this.state.partners.get(key);

            if (!existing || this.isRicherThan(partner, existing)) {
                this.state.partners.set(key, partner);
                merged.set(key, partner);
            }
        }
        return Array.from(merged.values());
    }
    getDeduplicationKey(partner) {
        if (partner.total_due > 0) {
            const shortId = Math.random().toString(36).slice(2, 7);
            return `id:${shortId}`;
        }

        if (partner.email) {
            return `email:${partner.email.toLowerCase().trim()}`;
        }
        if (partner.phone) {
            return `phone:${partner.phone.replace(/\D/g, "")}`;
        }
        return `name:${partner.name?.toLowerCase().trim() ?? "__unknown__"}`;
    }
    isRicherThan(challenger, current) {
        return this.countFields(challenger) > this.countFields(current);
    }
    countFields(partner) {
        return [
            partner.email,
            partner.phone,
            partner.name,
            partner.city,
            partner.country_id,
            partner.state_id,
            partner.street,
            partner.street2,
            partner.zip,
        ].filter(Boolean).length;
    }

    get globalState() {
        return this.pos.screenState.partnerList;
    }
    onScroll(ev) {
        if (this.state.loading || !this.modalContent) {
            return;
        }
        const height = this.modalContent.offsetHeight;
        const scrollTop = this.modalContent.scrollTop;
        const scrollHeight = this.modalContent.scrollHeight;

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
        return await this.getNewPartners();
    }
    async getNewPartners() {
        let domain = [];
        const offset = this.globalState.offsetBySearch[this.state.query] || 0;
        if (this.globalState.fullyLoadedBySearch[this.state.query]) {
            return [];
        }
        if (this.state.query) {
            const search_fields = this._getSearchFields(this.state.query);
            domain = [
                ...Array(search_fields.length - 1).fill("|"),
                ...search_fields.map((field) => [field, "ilike", this.state.query]),
            ];
        }

        try {
            this.state.loading = true;

            const result = await this.pos.data.callRelated("res.partner", "get_new_partner", [
                this.pos.config.id,
                domain,
                offset,
            ]);
            const partners = result["res.partner"];

            this.globalState.offsetBySearch[this.state.query] = offset + partners.length;
            this.globalState.fullyLoadedBySearch[this.state.query] = partners.length === 0;
            return this.mergeBatch(partners);
        } catch {
            return [];
        } finally {
            this.state.loading = false;
        }
    }
}
