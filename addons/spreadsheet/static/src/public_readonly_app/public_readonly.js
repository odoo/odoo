/** @odoo-module native */
import * as spreadsheet from "@odoo/o-spreadsheet";
import { Model, registries, Spreadsheet } from "@odoo/o-spreadsheet";
import { Component, onWillStart, useChildSubEnv, useState } from "@odoo/owl";
import { useSpreadsheetNotificationStore } from "@spreadsheet/hooks";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { download } from "@web/core/network";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";

import { useSpreadsheetPrint } from "../hooks.js";

const log = makeLogger("spreadsheet.public");

registries.topbarMenuRegistry.addChild("download_public_excel", ["file"], {
    name: _t("Download"),
    execute: (env) => env.downloadExcel(),
    isReadonlyAllowed: true,
    icon: "o-spreadsheet-Icon.DOWNLOAD",
    isVisible: (env) => env.canDownloadExcel?.(),
});

export class PublicReadonlySpreadsheet extends Component {
    static template = "spreadsheet.PublicReadonlySpreadsheet";
    static components = { Spreadsheet };
    static props = {
        dataUrl: String,
        downloadExcelUrl: { type: [String, Boolean], optional: true },
        mode: { type: String, optional: true },
    };

    setup() {
        useLifecycleLog(log);
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
        useSpreadsheetPrint(() => this.model);
        onWillStart(this.createModel.bind(this));
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
        const endData = log.perf("fetchPublicData");
        this.data = await this.http.get(this.props.dataUrl);
        endData({
            mode: this.props.mode,
            revisions: this.data.revisions?.length ?? 0,
            globalFilters: this.data.globalFilters?.length ?? 0,
        });
        this.model = new Model(
            this.data,
            {
                mode: this.props.mode === "dashboard" ? "dashboard" : "readonly",
            },
            this.data.revisions || [],
        );
        if (this.env.debug) {
            const debugObj = spreadsheet.__DEBUG__ || {};
            debugObj.model = this.model;
            globalThis.__SPREADSHEET_DEBUG__ = debugObj;
        }
    }

    toggleGlobalFilters() {
        this.state.isFilterShown = !this.state.isFilterShown;
    }
}
