import { useChildSubEnv, useState } from "@web/owl2/utils";
import { Component, markRaw, onMounted, onWillStart, onWillUnmount } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

import { useSpreadsheetNotificationStore } from "@spreadsheet/hooks";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { Spreadsheet, Model } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";

spreadsheet.registries.topbarMenuRegistry.addChild("download_public_excel", ["file"], {
    name: _t("Download"),
    execute: (env) => env.downloadExcel(),
    isReadonlyAllowed: true,
    icon: "o-spreadsheet-Icon.DOWNLOAD",
    isVisible: (env) => env.canDownloadExcel?.(),
    isEnabledOnLockedSheet: true,
});

function readSheetIdFromURL() {
    const url = new URL(browser.location.href);
    return url.searchParams.get("sid");
}

function writeSheetIdToURL(sheetId) {
    const url = new URL(browser.location.href);
    if (url.searchParams.get("sid") !== sheetId) {
        url.searchParams.set("sid", sheetId);
        browser.history.replaceState(browser.history.state, null, url);
    }
}

export class PublicReadonlySpreadsheet extends Component {
    static template = "spreadsheet.PublicReadonlySpreadsheet";
    static components = { Spreadsheet };
    static props = {
        dataUrl: String,
        downloadExcelUrl: { type: [String, Boolean], optional: true },
        mode: { type: String, optional: true },
    };

    setup() {
        useSpreadsheetNotificationStore();
        this.http = useService("http");
        this.state = useState({
            isFilterShown: false,
        });
        useChildSubEnv({
            downloadExcel: () =>
                download({
                    url: this.props.downloadExcelUrl,
                    data: {},
                }),
            canDownloadExcel: () => Boolean(this.props.downloadExcelUrl),
        });
        onWillStart(async () => {
            await this.createModel();
            this.syncSheetFromURL();
        });
        onMounted(() => {
            this.model.on("command-dispatched", this, this.syncURLFromSheet);
        });
        onWillUnmount(() => {
            this.model.off("command-dispatched", this);
        });
    }

    get showFilterButton() {
        return (
            this.props.mode === "dashboard" &&
            this.globalFilters.length > 0 &&
            !this.state.isFilterShown
        );
    }

    get globalFilters() {
        if (!this.data.globalFilters || this.data.globalFilters.length === 0) {
            return [];
        }
        return this.data.globalFilters.filter((filter) => filter.value !== "");
    }

    async createModel() {
        this.data = await this.http.get(this.props.dataUrl);
        this.model = new Model(
            this.data,
            {
                mode: this.props.mode === "dashboard" ? "dashboard" : "readonly",
                custom: {
                    isFrozenSpreadsheet: true,
                },
            },
            this.data.revisions || []
        );
        markRaw(this.model);
        if (this.env.debug) {
            // eslint-disable-next-line no-import-assign
            spreadsheet.__DEBUG__ = spreadsheet.__DEBUG__ || {};
            spreadsheet.__DEBUG__.model = this.model;
        }
    }

    syncSheetFromURL() {
        const urlSheetId = readSheetIdFromURL();
        const sheetIds = this.model.getters.getSheetIds();
        const activeSheetId = this.model.getters.getActiveSheetId();
        const targetSheetId = sheetIds.includes(urlSheetId) ? urlSheetId : sheetIds[0];
        if (activeSheetId !== targetSheetId) {
            this.model.dispatch("ACTIVATE_SHEET", {
                sheetIdFrom: activeSheetId,
                sheetIdTo: targetSheetId,
            });
        }
        writeSheetIdToURL(targetSheetId);
    }

    syncURLFromSheet(cmd) {
        if (cmd.type === "ACTIVATE_SHEET" && readSheetIdFromURL() !== cmd.sheetIdTo) {
            writeSheetIdToURL(cmd.sheetIdTo);
        }
    }

    toggleGlobalFilters() {
        this.state.isFilterShown = !this.state.isFilterShown;
    }
}
