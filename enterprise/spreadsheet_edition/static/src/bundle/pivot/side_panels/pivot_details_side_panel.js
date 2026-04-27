import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { components, helpers, stores, hooks } from "@odoo/o-spreadsheet";
import { Component, onWillStart, onWillUpdateProps, useRef } from "@odoo/owl";
import { OdooPivotLayoutConfigurator } from "./odoo_pivot_layout_configurator/odoo_pivot_layout_configurator";
import { SidePanelDomain } from "../../components/side_panel_domain/side_panel_domain";

const { Checkbox, Section, ValidationMessages, PivotTitleSection, PivotDeferUpdate } = components;
const { useHighlights } = hooks;
const { useLocalStore, PivotSidePanelStore } = stores;
const { getPivotHighlights } = helpers;

export class PivotDetailsSidePanel extends Component {
    static template = "spreadsheet_edition.PivotDetailsSidePanel";
    static components = {
        ValidationMessages,
        Checkbox,
        Section,
        OdooPivotLayoutConfigurator,
        PivotDeferUpdate,
        PivotTitleSection,
        SidePanelDomain,
    };
    static props = {
        onCloseSidePanel: Function,
        pivotId: String,
    };

    setup() {
        this.notification = useService("notification");
        /**@type {PivotSidePanelStore} */
        this.store = useLocalStore(PivotSidePanelStore, this.props.pivotId);
        this.pivotSidePanelRef = useRef("pivotSidePanel");

        const loadData = async () => {
            await this.pivot.load();
            this.modelDisplayName = this.isModelValid && (await this.pivot.getModelLabel());
        };
        onWillStart(loadData);
        onWillUpdateProps(loadData);
        useHighlights(this);
    }

    get isModelValid() {
        return this.pivot.isModelValid();
    }

    /** @returns {import("@spreadsheet/pivot/odoo_pivot").default} */
    get pivot() {
        return this.store.pivot;
    }

    get hasValidSortedColumn() {
        const definition = this.pivot.definition;
        return (
            definition?.sortedColumn &&
            definition.measures.find((m) => m.fieldName === definition.sortedColumn.measure)
        );
    }

    getScrollableContainerEl() {
        return this.pivotSidePanelRef.el;
    }

    formatSort() {
        const sortedColumn = this.pivot.definition.sortedColumn;
        const order = sortedColumn.order === "asc" ? _t("ascending") : _t("descending");
        const measure = this.pivot.definition.measures.find(
            (m) => m.fieldName === sortedColumn.measure
        );
        const measureDisplayName = this.pivot.getMeasure(measure.id).displayName;
        return `${measureDisplayName} (${order})`;
    }

    /**
     * Get the last update date, formatted
     *
     * @returns {string} date formatted
     */
    getLastUpdate() {
        const lastUpdate = this.pivot.lastUpdate;
        if (lastUpdate) {
            return new Date(lastUpdate).toLocaleTimeString();
        }
        return _t("never");
    }

    onDomainUpdate(domain) {
        this.store.update({ domain });
    }

    get unusedPivotWarning() {
        return _t("This pivot is not used");
    }

    get invalidPivotModel() {
        const model = this.env.model.getters.getPivotCoreDefinition(this.props.pivotId).model;
        return _t(
            "The model (%(model)s) of this pivot is not valid (it may have been renamed/deleted). Please re-insert a new pivot.",
            {
                model,
            }
        );
    }

    get deferUpdatesLabel() {
        return _t("Defer updates");
    }

    get deferUpdatesTooltip() {
        return _t(
            "Changing the pivot definition requires to reload the data. It may take some time."
        );
    }

    onDimensionsUpdated(definition) {
        this.store.update(definition);
    }

    get highlights() {
        return getPivotHighlights(this.env.model.getters, this.props.pivotId);
    }

    flipAxis() {
        const { rows, columns } = this.store.definition;
        this.onDimensionsUpdated({
            rows: columns,
            columns: rows,
        });
    }

    delete() {
        this.env.model.dispatch("REMOVE_PIVOT", { pivotId: this.props.pivotId });
    }
}
