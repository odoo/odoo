/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CopyButton } from "@web/views/fields/copy_clipboard/copy_button";
import { waitForDataLoaded, freezeOdooData } from "@spreadsheet/helpers/model";
import { Model } from "@odoo/o-spreadsheet";

/**
 * Share button to share a spreadsheet
 */
export class SpreadsheetShareButton extends Component {
    static template = "spreadsheet.ShareButton";
    static components = { Dropdown, DropdownItem, CopyButton };
    static props = {
        model: Model,
        onSpreadsheetShared: Function,
    };

    setup() {
        this.copiedText = _t("Copied");
        this.state = useState({ url: undefined });
    }

    async onOpened() {
        const model = this.props.model;
        await waitForDataLoaded(model);
        const data = await freezeOdooData(model);
        if (!this.isChanged(data)) {
            return;
        }
        const url = await this.props.onSpreadsheetShared(data, model.exportXLSX());
        this.state.url = url;
        browser.navigator.clipboard.writeText(url);
    }

    /**
     * Check whether the locale/global filters/contents have changed
     * compared to the last time of sharing (in the same session)
     */
    isChanged(data) {
        const contentsChanged = data.revisionId !== this.lastRevisionId;
        let globalFilterChanged = this.lastGlobalFilters === undefined;
        const newCells = data.sheets[data.sheets.length - 1].cells;
        if (this.lastGlobalFilters !== undefined) {
            for (const key of Object.keys(newCells)) {
                if (this.lastGlobalFilters[key]?.content !== newCells[key].content) {
                    globalFilterChanged = true;
                    break;
                }
            }
        }
        const localeChanged = data.settings.locale.code !== this.lastLocale;
        if (!(localeChanged || globalFilterChanged || contentsChanged)) {
            return false;
        }

        this.lastRevisionId = data.revisionId;
        this.lastGlobalFilters = newCells;
        this.lastLocale = data.settings.locale.code;
        return true;
    }
}
