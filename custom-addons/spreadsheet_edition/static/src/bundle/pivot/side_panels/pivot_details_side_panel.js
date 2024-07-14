/** @odoo-module */

import { Domain } from "@web/core/domain";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { EditableName } from "../../o_spreadsheet/editable_name/editable_name";

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";

export class PivotDetailsSidePanel extends Component {
    setup() {
        this.dialog = useService("dialog");
        /** @type {import("@spreadsheet/pivot/pivot_data_source").default} */
        this.dataSource = undefined;
        const loadData = async (pivotId) => {
            this.dataSource = await this.env.model.getters.getAsyncPivotDataSource(pivotId);
            this.modelDisplayName = await this.dataSource.getModelLabel();
        };
        onWillStart(() => loadData(this.props.pivotId));
        onWillUpdateProps((nextProps) => loadData(nextProps.pivotId));
    }

    get pivotDefinition() {
        const definition = this.env.model.getters.getPivotDefinition(this.props.pivotId);
        return {
            model: definition.model,
            modelDisplayName: this.modelDisplayName,
            domain: new Domain(definition.domain).toString(),
            dimensions: [...definition.rowGroupBys, ...definition.colGroupBys].map((fieldName) =>
                this.dataSource.getFormattedGroupBy(fieldName)
            ),
            measures: definition.measures.map((measure) =>
                this.dataSource.getMeasureDisplayName(measure)
            ),
            sortedColumn: definition.sortedColumn,
        };
    }

    onNameChanged(name) {
        this.env.model.dispatch("RENAME_ODOO_PIVOT", {
            pivotId: this.props.pivotId,
            name,
        });
    }

    formatSort() {
        const sortedColumn = this.pivotDefinition.sortedColumn;
        const order = sortedColumn.order === "asc" ? _t("ascending") : _t("descending");
        const measureDisplayName = this.dataSource.getMeasureDisplayName(sortedColumn.measure);
        return `${measureDisplayName} (${order})`;
    }

    /**
     * Get the last update date, formatted
     *
     * @returns {string} date formatted
     */
    getLastUpdate() {
        const lastUpdate = this.dataSource.lastUpdate;
        if (lastUpdate) {
            return new Date(lastUpdate).toLocaleTimeString();
        }
        return _t("never");
    }

    /**
     * Refresh the cache of the current pivot
     *
     */
    refresh() {
        this.env.model.dispatch("REFRESH_PIVOT", { id: this.props.pivotId });
    }

    openDomainEdition() {
        const definition = this.env.model.getters.getPivotDefinition(this.props.pivotId);
        this.dialog.add(DomainSelectorDialog, {
            resModel: definition.model,
            domain: new Domain(definition.domain).toString(),
            isDebugMode: !!this.env.debug,
            onConfirm: (domain) =>
                this.env.model.dispatch("UPDATE_ODOO_PIVOT_DOMAIN", {
                    pivotId: this.props.pivotId,
                    domain: new Domain(domain).toJson(),
                }),
        });
    }
}
PivotDetailsSidePanel.template = "spreadsheet_edition.PivotDetailsSidePanel";
PivotDetailsSidePanel.components = { DomainSelector, EditableName };
PivotDetailsSidePanel.props = {
    pivotId: {
        type: String,
        optional: true,
    },
};
