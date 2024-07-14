/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { useService } from "@web/core/utils/hooks";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import { SidePanelCollapsible } from "../side_panel_collapsible/side_panel_collapsible";
import { FilterEditorLabel } from "./filter_editor_label";

import { onWillStart, Component, useRef, useState, toRaw } from "@odoo/owl";

const { toNumber } = spreadsheet.helpers;
const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

/**
 * @typedef {import("@spreadsheet/data_sources/metadata_repository").Field} Field
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").GlobalFilter} GlobalFilter
 *
 * @typedef State
 * @property {boolean} saved
 * @property {string} label label of the filter
 */

/**
 * This is the side panel to define/edit a global filter.
 * It can be of 3 different type: text, date and relation.
 */
export class AbstractFilterEditorSidePanel extends Component {
    setup() {
        this.id = undefined;
        this.type = "";
        /** @type {State} */
        this.genericState = useState({
            saved: false,
            label: undefined,
        });
        this.fieldMatchings = useState([]);
        this._wrongFieldMatchingsSet = useState(new Set());
        this.getters = this.env.model.getters;
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.labelInput = useRef("labelInput");

        /** @type {string[]} */
        this.ALLOWED_FIELD_TYPES = [];

        onWillStart(this.onWillStart);
    }

    /**
     * Retrieve the placeholder of the label
     */
    get placeholder() {
        return _t("New %s filter", this.type);
    }

    get missingLabel() {
        return this.genericState.saved && !this.genericState.label;
    }

    get wrongFieldMatchings() {
        return this.genericState.saved ? [...this._wrongFieldMatchingsSet] : [];
    }

    get missingRequired() {
        return !!this.missingLabel || this.wrongFieldMatchings.length !== 0;
    }

    get filterValues() {
        const id = this.id || uuidGenerator.uuidv4();
        return {
            id,
            type: this.type,
            label: this.genericState.label,
        };
    }

    get isNewFilter() {
        return this.props.id === undefined;
    }

    /**
     * @param {Event & { target: HTMLInputElement }} ev
     */
    setLabel(ev) {
        this.genericState.label = ev.target.value;
    }

    shouldDisplayFieldMatching() {
        throw new Error("Not implemented by children");
    }

    loadValues() {
        this.id = this.props.id;
        const globalFilter = this.id && this.getters.getGlobalFilter(this.id);
        if (globalFilter) {
            this.genericState.label = _t(globalFilter.label);
            this.loadSpecificFilterValues(globalFilter);
        }
    }

    /**
     * @param {GlobalFilter} globalFilter
     */
    loadSpecificFilterValues(globalFilter) {
        return;
    }

    /**
     * @private
     */
    async _loadFieldMatchings() {
        for (const [type, el] of Object.entries(globalFiltersFieldMatchers)) {
            for (const objectId of el.getIds()) {
                const tag = await el.getTag(objectId);
                this.fieldMatchings.push({
                    name: el.getDisplayName(objectId),
                    tag,
                    fieldMatch: el.getFieldMatching(objectId, this.id) || {},
                    fields: () => el.getFields(objectId),
                    model: () => el.getModel(objectId),
                    payload: () => ({ id: objectId, type }),
                });
            }
        }
    }

    async onWillStart() {
        this.loadValues();
        const proms = [];
        proms.push(
            ...Object.values(globalFiltersFieldMatchers)
                .map((el) => el.waitForReady())
                .flat()
        );
        await this._loadFieldMatchings();
        await Promise.all(proms);
    }

    /**
     * @param {Field} field
     * @returns {boolean}
     */
    isFieldValid(field) {
        return !!field.searchable;
    }

    /**
     * Function that will be called by ModelFieldSelector on each fields, to
     * filter the ones that should be displayed
     * @param {Field} field
     * @returns {boolean}
     */
    filterModelFieldSelectorField(field) {
        if (!field.searchable) {
            return false;
        }
        return this.ALLOWED_FIELD_TYPES.includes(field.type) || !!field.relation;
    }

    /**
     *
     * @param {Object} field
     * @returns {boolean}
     */
    matchingRelation(field) {
        return !field.relation;
    }

    /**
     * @param {number} index
     * @param {string|undefined} chain
     * @param {Field|undefined} field
     */
    onSelectedField(index, chain, field) {
        //ensure index type to use it in a set
        index = toNumber(index);
        if (!chain) {
            this._wrongFieldMatchingsSet.delete(index);
            this.fieldMatchings[index].fieldMatch = {};
            return;
        }
        if (!field) {
            this._wrongFieldMatchingsSet.add(index);
        }
        const fieldName = chain;
        this.fieldMatchings[index].fieldMatch = {
            chain: fieldName,
            type: field?.type || "",
        };
        if (!field || !this.matchingRelation(field) || !field.searchable) {
            this._wrongFieldMatchingsSet.add(index);
        } else {
            this._wrongFieldMatchingsSet.delete(index);
        }
    }

    onSave() {
        this.genericState.saved = true;
        if (this.missingRequired) {
            this.notification.add(_t("Some required fields are not valid"), {
                type: "danger",
                sticky: false,
            });
            return;
        }
        const cmd = this.id ? "EDIT_GLOBAL_FILTER" : "ADD_GLOBAL_FILTER";
        const filter = this.filterValues;
        // Populate the command a bit more with a key chart, pivot or list
        const additionalPayload = {};
        this.fieldMatchings.forEach((fm) => {
            const { type, id } = fm.payload();
            additionalPayload[type] = additionalPayload[type] || {};
            //remove reactivity
            additionalPayload[type][id] = toRaw(fm.fieldMatch);
        });
        const result = this.env.model.dispatch(cmd, {
            filter,
            ...additionalPayload,
        });
        if (result.isCancelledBecause(CommandResult.DuplicatedFilterLabel)) {
            this.notification.add(_t("Duplicated Label"), {
                type: "danger",
                sticky: false,
            });
            return;
        }
        this.env.openSidePanel("GLOBAL_FILTERS_SIDE_PANEL", {});
    }

    onCancel() {
        this.env.openSidePanel("GLOBAL_FILTERS_SIDE_PANEL", {});
    }

    onDelete() {
        if (this.id) {
            this.env.model.dispatch("REMOVE_GLOBAL_FILTER", { id: this.id });
        }
        this.env.openSidePanel("GLOBAL_FILTERS_SIDE_PANEL", {});
    }
}
AbstractFilterEditorSidePanel.components = {
    FilterEditorLabel,
    SidePanelCollapsible,
};
AbstractFilterEditorSidePanel.props = {
    id: { type: String, optional: true },
    onCloseSidePanel: { type: Function, optional: true },
};
