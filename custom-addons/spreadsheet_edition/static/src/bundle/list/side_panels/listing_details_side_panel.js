/** @odoo-module */

import { Domain } from "@web/core/domain";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { EditableName } from "../../o_spreadsheet/editable_name/editable_name";

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";

export class ListingDetailsSidePanel extends Component {
    setup() {
        this.getters = this.env.model.getters;
        this.dialog = useService("dialog");
        const loadData = async (listId) => {
            this.dataSource = await this.env.model.getters.getAsyncListDataSource(listId);
            this.modelDisplayName = await this.dataSource.getModelLabel();
        };
        onWillStart(() => loadData(this.props.listId));
        onWillUpdateProps((nextProps) => loadData(nextProps.listId));
    }

    get listDefinition() {
        const listId = this.props.listId;
        const def = this.getters.getListDefinition(listId);
        return {
            model: def.model,
            modelDisplayName: this.modelDisplayName,
            domain: new Domain(def.domain).toString(),
            orderBy: def.orderBy,
        };
    }

    formatSort(sort) {
        const sortName = this.dataSource.getListHeaderValue(sort.name);
        if (sort.asc) {
            return _t("%(sortName)s (ascending)", { sortName });
        }
        return _t("%(sortName)s (descending)", { sortName });
    }

    getLastUpdate() {
        const lastUpdate = this.dataSource.lastUpdate;
        if (lastUpdate) {
            return new Date(lastUpdate).toLocaleTimeString();
        }
        return _t("never");
    }

    onNameChanged(name) {
        this.env.model.dispatch("RENAME_ODOO_LIST", {
            listId: this.props.listId,
            name,
        });
    }

    async refresh() {
        this.env.model.dispatch("REFRESH_ODOO_LIST", { listId: this.props.listId });
        this.env.model.dispatch("EVALUATE_CELLS", { sheetId: this.getters.getActiveSheetId() });
    }

    openDomainEdition() {
        this.dialog.add(DomainSelectorDialog, {
            resModel: this.listDefinition.model,
            domain: this.listDefinition.domain,
            isDebugMode: !!this.env.debug,
            onConfirm: (domain) =>
                this.env.model.dispatch("UPDATE_ODOO_LIST_DOMAIN", {
                    listId: this.props.listId,
                    domain: new Domain(domain).toJson(),
                }),
        });
    }
}
ListingDetailsSidePanel.template = "spreadsheet_edition.ListingDetailsSidePanel";
ListingDetailsSidePanel.components = { DomainSelector, EditableName };
ListingDetailsSidePanel.props = {
    listId: {
        type: String,
        optional: true,
    },
};
