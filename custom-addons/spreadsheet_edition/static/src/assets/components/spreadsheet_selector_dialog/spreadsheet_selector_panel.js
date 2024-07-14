/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { Pager } from "@web/core/pager/pager";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

import { Component, onWillStart, useState, onWillUnmount } from "@odoo/owl";

const DEFAULT_LIMIT = 9;

/**
 * @typedef State
 * @property {Object} spreadsheets
 * @property {string} panel
 * @property {string} name
 * @property {number|false} selectedSpreadsheetId
 * @property {string} [threshold]
 * @property {Object} pagerProps
 * @property {number} pagerProps.offset
 * @property {number} pagerProps.limit
 * @property {number} pagerProps.total
 */

export class SpreadsheetSelectorPanel extends Component {
    setup() {
        /** @type {State} */
        this.state = useState({
            spreadsheets: {},
            selectedSpreadsheetId: false,
            pagerProps: {
                offset: 0,
                limit: this.props.displayBlank ? DEFAULT_LIMIT : DEFAULT_LIMIT + 1,
                total: 0,
            },
        });
        this.keepLast = new KeepLast();
        this.orm = useService("orm");
        this.domain = [];
        this.debounce = undefined;

        onWillStart(async () => {
            await this._fetchSpreadsheets();
            this.state.pagerProps.total = await this._fetchPagerTotal();
        });

        onWillUnmount(() => {
            browser.clearTimeout(this.debounce);
        });
        this._selectItem(false);

        useHotkey("Enter", () => {
            this.props.onSpreadsheetDblClicked();
        });
    }

    _fetchSpreadsheets() {
        throw new Error("Should be implemented by subclass.");
    }

    /**
     * @returns {Promise<number>}
     */
    async _fetchPagerTotal() {
        throw new Error("Should be implemented by subclass.");
    }

    async _getOpenSpreadsheetAction() {
        throw new Error("Should be implemented by subclass.");
    }

    async _getCreateAndOpenSpreadsheetAction() {
        throw new Error("Should be implemented by subclass.");
    }

    async onSearchInput(ev) {
        const currentSearch = ev.target.value;
        this.domain = currentSearch !== "" ? [["name", "ilike", currentSearch]] : [];

        // Reset pager offset and get the total count based on the search criteria
        this.state.pagerProps.offset = 0;
        this._debouncedFetchSpreadsheets();
    }

    _debouncedFetchSpreadsheets() {
        browser.clearTimeout(this.debounce);
        this.debounce = browser.setTimeout(async () => {
            const [, total] = await Promise.all([
                this._fetchSpreadsheets(),
                this._fetchPagerTotal(),
            ]);
            this.state.pagerProps.total = total;
        }, 400);
    }

    /**
     * @param {Object} param0
     * @param {number} param0.offset
     * @param {number} param0.limit
     */
    onUpdatePager({ offset, limit }) {
        this.state.pagerProps.offset = offset;
        this.state.pagerProps.limit = limit;
        this._fetchSpreadsheets();
    }

    /**
     * @param {string} [base64]
     * @returns {string}
     */
    getUrl(base64) {
        return base64 ? `data:image/jpeg;charset=utf-8;base64,${base64}` : "";
    }

    /**
     * @param {number|false} id
     */
    _selectItem(id) {
        this.state.selectedSpreadsheetId = id;
        const spreadsheet =
            this.state.selectedSpreadsheetId &&
            this.state.spreadsheets.find((s) => s.id === this.state.selectedSpreadsheetId);
        const notificationMessage = spreadsheet
            ? _t("New sheet inserted in '%s'", spreadsheet.name)
            : this.notificationMessage;
        this.props.onSpreadsheetSelected({
            spreadsheet,
            notificationMessage,
            getOpenSpreadsheetAction: spreadsheet
                ? this._getOpenSpreadsheetAction.bind(this)
                : this._getCreateAndOpenSpreadsheetAction.bind(this),
        });
    }
}

SpreadsheetSelectorPanel.template = "spreadsheet_edition.SpreadsheetSelectorPanel";
SpreadsheetSelectorPanel.components = { Pager };
SpreadsheetSelectorPanel.defaultProps = {
    displayBlank: true,
};
SpreadsheetSelectorPanel.props = {
    onSpreadsheetSelected: Function,
    onSpreadsheetDblClicked: Function,
    displayBlank: {
        type: Boolean,
        optional: true,
    },
};
