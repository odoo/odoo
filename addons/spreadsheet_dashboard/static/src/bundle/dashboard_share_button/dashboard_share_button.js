import { Component, proxy, t, usePlugin, useProps } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { DashboardSharePlugin } from "@spreadsheet_dashboard/bundle/owl_plugins/dashboard_share_owl_plugin";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { waitForDataLoaded, freezeOdooData } from "@spreadsheet/helpers/model";
import { Model } from "@odoo/o-spreadsheet";

/**
 * Share button to share a spreadsheet
 */
export class DashboardShareButton extends Component {
    static template = "spreadsheet.ShareButton";
    static components = { Dropdown, DropdownItem, CopyButton };
    props = useProps({
        model: t.instanceOf(Model).optional(),
        togglerClass: t.string().optional(),
    });

    dashboardSharePlugin = usePlugin(DashboardSharePlugin);

    setup() {
        this.copiedText = _t("Copied");
        this.state = proxy({ url: undefined });
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
        const excelExport = await model.exportXLSX();
        const url = await this.dashboardSharePlugin.shareDashboard(data, excelExport);
        model.dispatch("LOG_DATASOURCE_EXPORT", { action: "freeze" });
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
        const newCells = data.sheets[data.sheets.length - 1].cells;
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
