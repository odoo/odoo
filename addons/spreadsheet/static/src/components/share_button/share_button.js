/** @odoo-module native */
import { Model } from "@odoo/o-spreadsheet";
import { Component, useState } from "@odoo/owl";
import { freezeOdooData, waitForDataLoaded } from "@spreadsheet/helpers/model";
import { CopyButton } from "@web/components/copy_button";
import { Dropdown, DropdownItem } from "@web/components/dropdown";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/translation";

/**
 * Share button to share a spreadsheet
 */
export class SpreadsheetShareButton extends Component {
    static template = "spreadsheet.ShareButton";
    static components = { Dropdown, DropdownItem, CopyButton };
    static props = {
        model: { type: Model, optional: true },
        onSpreadsheetShared: Function,
        togglerClass: { type: String, optional: true },
    };

    setup() {
        this.copiedText = _t("Copied");
        this.state = useState({ url: undefined });
    }

    get togglerClass() {
        return ["btn", this.props.togglerClass].join(" ");
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
        setTimeout(async () => {
            try {
                await browser.navigator.clipboard.writeText(url);
            } catch (error) {
                browser.console.warn(error);
            }
        });
    }

    /**
     * Check whether the locale/global filters/contents have changed
     * compared to the last time of sharing (in the same session)
     */
    isChanged(data) {
        const contentsChanged = data.revisionId !== this.lastRevisionId;
        let globalFilterChanged = this.lastGlobalFilters === undefined;
        const newCells = {};
        for (const sheet of data.sheets) {
            for (const [cellId, cellValue] of Object.entries(sheet.cells)) {
                newCells[`${sheet.id}:${cellId}`] = cellValue;
            }
        }
        if (this.lastGlobalFilters !== undefined) {
            for (const key of Object.keys(newCells)) {
                if (this.lastGlobalFilters[key] !== newCells[key]) {
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
