/** @odoo-module **/

import { Component, onWillStart, useChildSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { download } from "@web/core/network/download";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { Spreadsheet, Model, registries } from "@odoo/o-spreadsheet";
import { _lt } from "@web/core/l10n/translation";
import { loadSpreadsheetDependencies } from "../helpers/helpers";
import { migrate } from "../o_spreadsheet/migration";

registries.topbarMenuRegistry.addChild("download_public_excel", ["file"], {
    name: _lt("Download"),
    execute: (env) => env.downloadExcel(),
    isReadonlyAllowed: true,
});

export class PublicReadonlySpreadsheet extends Component {
    static props = {
        dataUrl: String,
        downloadExcelUrl: String,
    };

    setup() {
        this.http = useService("http");
        useChildSubEnv({
            downloadExcel: () =>
                download({
                    url: this.props.downloadExcelUrl,
                    data: {},
                }),
        });
        onWillStart(loadSpreadsheetDependencies);
        onWillStart(this.createModel.bind(this));
    }

    async createModel() {
        const data = await this.http.get(this.props.dataUrl);
        this.model = new Model(migrate(data), {
            mode: "readonly",
        });
        if (this.env.debug) {
            // eslint-disable-next-line no-import-assign
            spreadsheet.__DEBUG__ = spreadsheet.__DEBUG__ || {};
            spreadsheet.__DEBUG__.model = this.model;
        }
    }
}

PublicReadonlySpreadsheet.template = "spreadsheet.PublicReadonlySpreadsheet";
PublicReadonlySpreadsheet.components = { Spreadsheet };
