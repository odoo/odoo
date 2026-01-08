import { ImStatus } from "@mail/core/common/im_status";

import { Component, useState, useRef } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class SelectableList extends Component {
    static components = { ImStatus };
    static props = {};
    static template = "discuss.SelectableList";

    setup() {
        this.store = useService("mail.store");
        this.inputRef = useRef("input");
        this.internalState = useState({
            search: "",
            selectedOptions: [],
            isLoading: false,
        });
    }

    get search() {
        return this.internalState.search;
    }

    set search(value) {
        this.internalState.search = value;
    }

    get selectedOptions() {
        return this.internalState.selectedOptions;
    }

    get options() {
        return [];
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
        const selectedOptions = [...this.selectedOptions];
        const idx = selectedOptions.findIndex((selected) => selected.id === option.id);
        if (idx === -1) {
            if (this.maxSelectionLimit && selectedOptions.length >= this.maxSelectionLimit) {
                return;
            }
            selectedOptions.push(option);
        } else {
            selectedOptions.splice(idx, 1);
        }
        this.internalState.selectedOptions = selectedOptions;
    };

    isSelected(option) {
        return this.selectedOptions.some((selected) => selected.id === option.id);
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
        if (option.isPartner && option.partner) {
            return option.partner.avatarUrl;
        }
        return option.avatarUrl ?? "";
    }

    get emptyStateText() {
        return this.isLoading ? _t("Searching...") : _t("No results found");
    }
}
