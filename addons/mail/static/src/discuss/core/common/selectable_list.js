import { ImStatus } from "@mail/core/common/im_status";

import { Component, useState, useRef, onMounted } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

function makeSelectableListState() {
    return useState({
        searchTerm: "",
        options: [],
        selectedOptions: [],
        isLoading: false,
    });
}

export function useSelectableListState() {
    return makeSelectableListState();
}

export class SelectableList extends Component {
    static components = { ImStatus };
    static props = ["state?", "slots", "autofocus?", "optionAvatarUrl"];
    static template = "discuss.SelectableList";

    setup() {
        this.store = useService("mail.store");
        this.inputRef = useRef("input");
        this.internalState = makeSelectableListState();
        onMounted(() => {
            if (this.props.autofocus) {
                this.inputRef.el.focus();
            }
        });
    }

    get state() {
        return this.props.state || this.internalState;
    }

    get search() {
        return this.state.search;
    }

    set search(value) {
        this.state.search = value;
    }

    get maxSelectionLimit() {
        return false;
    }

    get searchPlaceholder() {
        return _t("Search...");
    }

    onInput() {
        const value = this.inputRef.el?.value ?? "";
        this.search = value;
    }

    clearSearch() {
        this.search = "";
    }

    toggleSelection = (option) => {
        const selectedOptions = [...this.state.selectedOptions];
        const idx = selectedOptions.findIndex((selected) => selected.id === option.id);
        if (idx === -1) {
            if (this.maxSelectionLimit && selectedOptions.length >= this.maxSelectionLimit) {
                return;
            }
            selectedOptions.push(option);
        } else {
            selectedOptions.splice(idx, 1);
        }
        this.state.selectedOptions = selectedOptions;
    };

    isSelected(option) {
        return this.state.selectedOptions.some((selected) => selected.id === option.id);
    }

    getOptionDisplayName(option) {
        if (option.isPartner && option.partner) {
            return option.partner.displayName ?? option.partner.name ?? "";
        }
        if (option.email) {
            return option.email;
        }
        return option.displayName ?? option.name ?? "";
    }

    getOptionAvatarUrl(option) {
        const optionFromProp = this.props.optionAvatarUrl(option);
        if (optionFromProp) {
            return optionFromProp;
        }
        if (option.isPartner && option.partner) {
            return option.partner.avatarUrl;
        }
        return option.avatarUrl ?? "";
    }

    get emptyStateText() {
        return this.isLoading ? _t("Searching...") : _t("No results found");
    }
}
