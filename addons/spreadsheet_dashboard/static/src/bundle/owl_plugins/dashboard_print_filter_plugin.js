import { owlPlugins, components } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";
import { providePlugins, t, useConfig, usePlugin } from "@odoo/owl";
import { getFacetInfo } from "@spreadsheet/global_filters/helpers";

const { SpreadsheetPrintFilterPlugin, ModelPlugin } = owlPlugins;
const { SpreadsheetPrint } = components;
const { DateTime } = luxon;

const MAX_ELEMENTS_PER_FILTERS = 30;
const MAX_ELEMENTS_PER_FILTERS_IF_AGGREGATED = 15;

patch(SpreadsheetPrint.prototype, {
    setup() {
        if (this.model().getters.isDashboard()) {
            providePlugins([DashboardPrintFilterPlugin], { env: this.env });
        }
        super.setup();
    }
});

export class DashboardPrintFilterPlugin extends SpreadsheetPrintFilterPlugin {
    static id = "SpreadsheetPrintFilterPlugin";

    env = useConfig("env", t.object().optional({}));
    modelPlugin = usePlugin(ModelPlugin);

    printFilters(page) {
        const title = document.createElement("h1");
        title.textContent = document.querySelector(".o_search_panel_category_value.active").title;
        page.appendChild(title);
        const printDate = document.createElement("h3");
        printDate.textContent = ("Printed on: " + DateTime.now().toLocaleString());
        page.appendChild(printDate);
        const filters = this.modelPlugin.model().getters.getGlobalFilters();
        const ulDiv = document.createElement("div");
        ulDiv.classList.add("o-ul-filters");
        const promises = [];
        const elements = [];
        filters.forEach(async filter => {
            if (this.modelPlugin.model().getters.isGlobalFilterActive(filter.id)) {
                const filterValue = this.modelPlugin.model().getters.getGlobalFilterValue(filter.id);
                promises.push(getFacetInfo(this.env, filter, filterValue, this.modelPlugin.model().getters).then((info) => {
                    switch (filter.type) {
                        case "date": {
                            if (info.values.length > MAX_ELEMENTS_PER_FILTERS) {
                                const tail = " and " + (info.values.length - MAX_ELEMENTS_PER_FILTERS_IF_AGGREGATED).toString() + " more";
                                elements.push(" • " + info.title + " : " + info.values.splice(0, MAX_ELEMENTS_PER_FILTERS_IF_AGGREGATED).join(" " + info.separator + " ") + tail);
                            } else {
                                elements.push(" • " + info.title + " : " + info.values.join(" " + info.separator + " "));
                            }
                            break;
                        }
                        default: {
                            if (info.values.length > MAX_ELEMENTS_PER_FILTERS) {
                                const tail = " and " + (info.values.length - MAX_ELEMENTS_PER_FILTERS_IF_AGGREGATED).toString() + " more";
                                elements.push(" • " + info.title + " : " + info.operator + " " + info.values.splice(0, MAX_ELEMENTS_PER_FILTERS_IF_AGGREGATED).join(" " + info.separator + " ") + tail);
                            } else {
                                elements.push(" • " + info.title + " : " + info.operator + " " + info.values.join(" " + info.separator + " "));
                            }
                            break;
                        }
                    }
                }));
            }
        });
        Promise.all(promises).then(() => {
            ulDiv.innerText = elements.join("\n\n");
            page.appendChild(ulDiv);
        });
        return page;
    }
}
