/** @odoo-module native */
import { Component, onWillDestroy, status, useEffect, useState } from "@odoo/owl";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { normalize } from "@web/core/l10n/utils";
import { _t } from "@web/core/translation";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { Dialog } from "@web/ui/dialog";
const log = makeLogger("pos.screen.partner_list");

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
        useLifecycleLog(log);
        this.pos = usePos();
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.modalRef = useChildRef();
        this.modalContent = null;
        this.state = useState({
            initialPartners: this.pos.models["res.partner"].filter((p) => {
                const par = p.property_account_receivable_id;
                return !par || par.non_trade !== true;
            }),
            loadedPartners: [],
            query: "",
            loading: false,
        });
        this.searchInputRef = null;
        this.loadedPartnerIds = new Set(this.state.initialPartners.map((p) => p.id));
        this.partnerRequests = new Map();
        this.exhaustedQueries = new Set();
        log.lifecycle("setup: partners", () => ({
            initial: this.state.initialPartners.length,
            total: this.pos.models["res.partner"].length,
            current: this.props.partner?.id,
        }));
        useHotkey("enter", () => this.onEnter(), {
            bypassEditableProtection: true,
        });
        this.onScroll = debounce(this.onScroll.bind(this), 200);
        onWillDestroy(() => this.onScroll.cancel());

        useEffect(
            () => {
                const content = this.modalRef.el?.querySelector(".modal-body");
                if (!content) {
                    return;
                }
                this.modalContent = content;
                content.addEventListener("scroll", this.onScroll);
                return () => {
                    content.removeEventListener("scroll", this.onScroll);
                    this.onScroll.cancel();
                    this.modalContent = null;
                };
            },
            () => [this.modalRef.el],
        );
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
            log.logic("onScroll: load more", () => ({
                query: this.state.query,
                loaded: this.loadedPartnerIds.size,
            }));
            this.getNewPartners().catch(() => {
                log.logic("onScroll: page failed; retry remains available");
            });
        }
    }
    async editPartner(p = false) {
        const partner = await this.pos.editPartner(p);
        log.logic("editPartner", () => ({ from: p?.id, result: partner?.id }));
        if (partner) {
            this.clickPartner(partner);
        }
    }
    async onEnter() {
        if (this.searchInputRef?.el) {
            this.state.query = this.searchInputRef.el.value;
        }
        if (!this.state.query) {
            return;
        }
        const query = this.state.query;
        let result;
        try {
            result = await this.searchPartner();
        } catch {
            if (status(this) !== "destroyed" && query === this.state.query) {
                this.notification.add(_t("Customer search failed. Please try again."), {
                    type: "warning",
                });
            }
            return;
        }
        if (status(this) === "destroyed" || query !== this.state.query) {
            log.logic("onEnter: stale search ignored", () => ({
                query,
                currentQuery: this.state.query,
            }));
            return;
        }
        log.logic("onEnter: server search", () => ({
            query: this.state.query,
            results: result.length,
        }));
        if (result.length > 0) {
            this.notification.add(
                _t('%s customer(s) found for "%s".', result.length, this.state.query),
                { autocloseDelay: 3000 },
            );
        } else {
            this.notification.add(
                _t('No more customer found for "%s".', this.state.query),
            );
        }
    }

    goToOrders(partner) {
        this.clickPartner(partner);
        const partnerHasActiveOrders = this.pos
            .getOpenOrders()
            .some((order) => order.getPartner()?.id === partner.id);
        const stateOverride = {
            search: {
                fieldName: "PARTNER",
                searchTerm: partner.name,
                partnerId: partner.id,
            },
            filter: partnerHasActiveOrders ? "" : "SYNCED",
        };
        log.pipeline("goToOrders", () => ({
            partner: partner.id,
            partnerHasActiveOrders,
            filter: stateOverride.filter,
        }));
        this.pos.navigate("TicketScreen", { stateOverride });
    }

    getPartners(partners) {
        const endFilter = log.perf("getPartners");
        const searchWord = normalize(this.state.query?.trim() ?? "");
        const exactMatches = partners.filter((partner) =>
            partner.exactMatch(searchWord),
        );

        if (exactMatches.length > 0) {
            endFilter({
                searchWord,
                candidates: partners.length,
                exact: exactMatches.length,
            });
            return exactMatches;
        }
        const numberString = searchWord.replace(/[+\s()-]/g, "");
        const isSearchWordNumber = /^[0-9]+$/.test(numberString);

        const patternBase = isSearchWordNumber ? numberString : searchWord;
        const regex = new RegExp(
            patternBase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/%/g, ".*"),
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
                            : (a.name || "").localeCompare(b.name || ""),
                  );

        endFilter({
            searchWord,
            candidates: partners.length,
            isSearchWordNumber,
            result: availablePartners.length,
        });
        return availablePartners;
    }
    get isBalanceDisplayed() {
        return false;
    }
    clickPartner(partner) {
        log.logic("clickPartner", () => ({ partner: partner?.id }));
        this.props.getPayload(partner);
        this.props.close();
    }
    async searchPartner() {
        const partner = await this.getNewPartners();
        return partner;
    }
    getNewPartners() {
        const query = this.state.query;
        if (this.exhaustedQueries.has(query)) {
            log.logic("getNewPartners: query exhausted", () => ({ query }));
            return Promise.resolve([]);
        }
        if (this.partnerRequests.has(query)) {
            log.logic("getNewPartners: reuse pending page", () => ({ query }));
            return this.partnerRequests.get(query);
        }
        this.state.loading = true;
        const request = this.getPartnerPage(query).finally(() => {
            this.partnerRequests.delete(query);
            this.state.loading = this.partnerRequests.size > 0;
        });
        this.partnerRequests.set(query, request);
        return request;
    }
    async getPartnerPage(query) {
        let domain = [];
        const offsets = this.globalState.offsetBySearch;
        const offset = Object.hasOwn(offsets, query) ? offsets[query] : 0;
        log.logic("getNewPartners", () => ({
            query,
            offset,
            loaded: this.loadedPartnerIds.size,
        }));
        if (query) {
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
                ...search_fields.map((field) => [field, "ilike", query + "%"]),
            ];
        }

        const endFetch = log.perf("getNewPartners");
        try {
            const result = await this.pos.data.callRelated(
                "res.partner",
                "get_new_partner",
                [this.pos.config.id, domain, offset],
            );

            const partners = result["res.partner"];
            this.globalState.offsetBySearch = {
                ...this.globalState.offsetBySearch,
                [query]: offset + partners.length,
            };
            if (!partners.length) {
                this.exhaustedQueries.add(query);
            }

            let added = 0;
            for (const partner of partners) {
                if (!this.loadedPartnerIds.has(partner.id)) {
                    this.loadedPartnerIds.add(partner.id);
                    this.state.loadedPartners.push(partner);
                    added++;
                }
            }

            endFetch({
                query,
                offset,
                fetched: partners.length,
                added,
            });
            return partners;
        } catch (error) {
            endFetch({ query, offset, failed: true });
            throw error;
        }
    }
}
