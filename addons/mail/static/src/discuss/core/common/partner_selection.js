import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { useRef, useState } from "@web/owl2/utils";

/** @typedef {@import("models").ResPartner} Partner */

/** Internal function for typedef */
function _usePartnerSelectionState() {
    return {
        searchResultCount: 0,
        searchStr: "",
        /** @type {string[]} */
        selectableEmails: [],
        /** @type {Partner[]} */
        selectablePartners: [],
        /** @type {string[]} */
        selectedEmails: [],
        /** @type {Partner[]} */
        selectedPartners: [],
    };
}

/** @return {ReturnType<typeof _usePartnerSelectionState>} */
export function usePartnerSelectionState() {
    return useState(_usePartnerSelectionState());
}

/**
 * @typedef {Object} Props
 * @property {ReturnType<typeof _usePartnerSelectionState>} [state]
 * @property {string} [searchClass]
 * @property {string} [searchPlaceholder]
 * @extends {Component<Props, Env>}
 */
export class PartnerSelection extends Component {
    static components = { DiscussAvatar };
    static props = [
        "autofocus?",
        "onInput?",
        "slots?",
        "state?",
        "searchClass?",
        "searchEmptyText?",
        "searchPlaceholder?",
        "selectableClass?",
    ];
    static template = "discuss.PartnerSelection";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.internalState = usePartnerSelectionState();
        this.inputRef = useRef("input");
        if (this.props.autofocus) {
            useAutofocus({ refName: "input" });
        }
    }

    get searchPlaceholder() {
        return this.props.searchPlaceholder ?? _t("Search people");
    }

    get showingResultNarrowText() {
        return _t(
            "Showing %(result_count)s results out of %(total_count)s. Narrow your search to see more choices.",
            {
                result_count: this.state.selectablePartners.length,
                total_count: this.state.searchResultCount,
            }
        );
    }

    /** @returns {ReturnType<usePartnerSelectionState>} */
    get state() {
        return this.props.state || this.internalState;
    }

    /** @param {string} email */
    onClickSelectableEmail(email) {
        const index = this.state.selectedEmails.indexOf(email);
        if (index !== -1) {
            this.state.selectedEmails.splice(index, 1);
            return;
        }
        this.state.selectedEmails.push(email);
    }

    /** @param {Partner} partner */
    onClickSelectablePartner(partner) {
        if (partner.in(this.state.selectedPartners)) {
            const index = this.state.selectedPartners.indexOf(partner);
            if (index !== -1) {
                this.state.selectedPartners.splice(index, 1);
            }
            return;
        }
        this.state.selectedPartners.push(partner);
    }

    onInput() {
        this.state.searchStr = this.inputRef.el.value;
        this.props.onInput();
    }
}
