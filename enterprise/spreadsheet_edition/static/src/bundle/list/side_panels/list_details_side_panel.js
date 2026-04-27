/** @odoo-module */

import { Domain } from "@web/core/domain";
import { EditListSortingSection } from "./edit_list_sorting_section/edit_list_sorting_section";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart } from "@odoo/owl";
import { getListHighlights } from "../list_highlight_helpers";

import { hooks, components, helpers } from "@odoo/o-spreadsheet";
import { SidePanelDomain } from "../../components/side_panel_domain/side_panel_domain";

const { useHighlights } = hooks;
const { ValidationMessages, EditableName, CogWheelMenu, Section } = components;
const { isDefined } = helpers;

export class ListDetailsSidePanel extends Component {
    static template = "spreadsheet_edition.ListDetailsSidePanel";
    static components = {
        EditableName,
        ValidationMessages,
        CogWheelMenu,
        Section,
        SidePanelDomain,
        EditListSortingSection,
    };
    static props = {
        onCloseSidePanel: Function,
        listId: String,
    };

    setup() {
        this.getters = this.env.model.getters;
        this.notification = useService("notification");
        const loadData = async (listId) => {
            const dataSource = await this.env.model.getters.getAsyncListDataSource(listId);
            this.isModelValid = dataSource.isModelValid();
            if (this.isModelValid) {
                this.modelDisplayName = await dataSource.getModelLabel();
                // Store the fields here because the data source can be reset when updating the list.
                // Forcing a reload with onWillUpdateProps would introduce flickering
                // and the fields never change anyway.
                this.listFields = dataSource.getFields();
            }
        };
        onWillStart(async () => {
            // it's assumed `this.props.listId` never changes (t-key is required when using this component)
            await loadData(this.props.listId);
        });
        useHighlights(this);
    }

    get cogWheelMenuItems() {
        return [
            {
                name: "Duplicate",
                icon: "o-spreadsheet-Icon.COPY",
                execute: () => this.duplicateList(),
            },
            {
                name: "Delete",
                icon: "o-spreadsheet-Icon.TRASH",
                execute: () => this.deleteList(),
            },
        ];
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

    get invalidListModel() {
        const model = this.env.model.getters.getListDefinition(this.props.listId).model;
        return _t(
            "The model (%(model)s) of this list is not valid (it may have been renamed/deleted). Please re-insert a new list.",
            {
                model,
            }
        );
    }

    getLastUpdate() {
        const lastUpdate = this.env.model.getters.getListDataSource(this.props.listId).lastUpdate;
        if (lastUpdate) {
            return new Date(lastUpdate).toLocaleTimeString();
        }
        return _t("never");
    }

    getColumnFields() {
        return this.getters
            .getListDefinition(this.props.listId)
            .columns.map((col) => this.listFields[col])
            .filter(isDefined);
    }

    onNameChanged(name) {
        this.env.model.dispatch("RENAME_ODOO_LIST", {
            listId: this.props.listId,
            name,
        });
    }

    onDomainUpdate(domain) {
        const listDefinition = this.getters.getListModelDefinition(this.props.listId);
        this.env.model.dispatch("UPDATE_ODOO_LIST", {
            listId: this.props.listId,
            list: {
                ...listDefinition,
                searchParams: {
                    ...listDefinition.searchParams,
                    domain,
                },
            },
        });
    }

    /**
     * @param {{name: string, asc: boolean}[]} orderBy
     */
    onUpdateSorting(orderBy) {
        const listDefinition = this.getters.getListModelDefinition(this.props.listId);
        this.env.model.dispatch("UPDATE_ODOO_LIST", {
            listId: this.props.listId,
            list: {
                ...listDefinition,
                searchParams: {
                    ...listDefinition.searchParams,
                    orderBy,
                },
            },
        });
    }

    duplicateList() {
        const newListId = this.env.model.getters.getNextListId();
        const result = this.env.model.dispatch("DUPLICATE_ODOO_LIST", {
            listId: this.props.listId,
            newListId,
        });
        const msg = result.isSuccessful
            ? _t('List duplicated. Use the "Re-insert list" menu item to insert it in a sheet.')
            : _t("List duplication failed");
        const type = result.isSuccessful ? "success" : "danger";
        this.notification.add(msg, { sticky: false, type });
        if (result.isSuccessful) {
            this.env.openSidePanel("LIST_PROPERTIES_PANEL", { listId: newListId });
        }
    }

    deleteList() {
        this.env.askConfirmation(_t("Are you sure you want to delete this list?"), () => {
            this.env.model.dispatch("REMOVE_ODOO_LIST", { listId: this.props.listId });
            this.props.onCloseSidePanel();
        });
    }

    get unusedListWarning() {
        return _t("This list is not used");
    }

    get highlights() {
        return getListHighlights(this.env.model.getters, this.props.listId);
    }
}
