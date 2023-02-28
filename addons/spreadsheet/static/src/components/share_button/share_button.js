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
        if (this.state.url) {
            return;
        }
        const model = this.props.model;
        await waitForDataLoaded(model);
        const data = await freezeOdooData(model);
        const url = await this.props.onSpreadsheetShared(data, model.exportXLSX());
        this.state.url = url;
        browser.navigator.clipboard.writeText(url);
    }
}
