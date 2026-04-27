/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { Pager } from "@web/core/pager/pager";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { SpreadsheetSelectorGrid } from "../spreadsheet_selector_grid/spreadsheet_selector_grid";

import { Component, onWillStart, useState, onWillUnmount } from "@odoo/owl";

const DEFAULT_LIMIT = 9;

/**
 * @typedef State
 * @property {Object} spreadsheets
 * @property {string} panel
 * @property {string} name
 * @property {number|null} selectedSpreadsheetId
 * @property {string} [threshold]
 * @property {Object} pagerProps
 * @property {number} pagerProps.offset
 * @property {number} pagerProps.limit
 * @property {number} pagerProps.total
 */

export class SpreadsheetSelectorPanel extends Component {
    static template = "spreadsheet_edition.SpreadsheetSelectorPanel";
    static components = { Pager, SpreadsheetSelectorGrid };
    static defaultProps = {
        displayBlank: true,
    };
    static props = {
        onSpreadsheetSelected: Function,
        onSpreadsheetDblClicked: Function,
        model: String,
        displayBlank: {
            type: Boolean,
            optional: true,
        },
    };

    setup() {
        /** @type {State} */
        this.state = useState({
            spreadsheets: {},
            selectedSpreadsheetId: null,
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
            const selectedItem =
                !this.props.displayBlank && this.state.spreadsheets.length
                    ? this.state.spreadsheets[0].id
                    : null;
            this._selectItem(selectedItem);
        });

        onWillUnmount(() => {
            browser.clearTimeout(this.debounce);
        });

        useHotkey("Enter", () => {
            this.props.onSpreadsheetDblClicked();
        });
    }

    async _fetchSpreadsheets() {
        const { offset, limit } = this.state.pagerProps;
        const { records, total } = await this.keepLast.add(
            this.orm.call(this.props.model, "get_spreadsheets", [this.domain], {
                offset,
                limit,
            })
        );
        this.state.spreadsheets = records;
        this.state.pagerProps.total = total;
    }

    async _getOpenSpreadsheetAction() {
        return this.orm.call(this.props.model, "action_open_spreadsheet", [
            [this.state.selectedSpreadsheetId],
        ]);
    }

    async _getCreateAndOpenSpreadsheetAction() {
        return this.orm.call(this.props.model, "action_open_new_spreadsheet");
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
        this.debounce = browser.setTimeout(this._fetchSpreadsheets.bind(this), 400);
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
     * @param {number|null} id
     */
    _selectItem(id) {
        this.state.selectedSpreadsheetId = id;
        const spreadsheet =
            this.state.selectedSpreadsheetId &&
            this.state.spreadsheets.find((s) => s.id === this.state.selectedSpreadsheetId);
        const notificationMessage = spreadsheet
            ? _t("New sheet inserted in '%s'", spreadsheet.display_name)
            : "";
        this.props.onSpreadsheetSelected({
            spreadsheet,
            notificationMessage,
            getOpenSpreadsheetAction: spreadsheet
                ? this._getOpenSpreadsheetAction.bind(this)
                : this._getCreateAndOpenSpreadsheetAction.bind(this),
        });
    }

    /**
     * @param {Object} spreadsheet
     * @returns {string} - URL for the spreadsheet thumbnail
     */
    getThumbnailURL(spreadsheet) {
        if (!spreadsheet.display_thumbnail) {
            return false;
        }

        return `data:image/jpeg;charset=utf-8;base64,${spreadsheet.display_thumbnail}`;
    }
}
