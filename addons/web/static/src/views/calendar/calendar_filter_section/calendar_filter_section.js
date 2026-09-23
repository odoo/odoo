// @ts-check
/** @odoo-module native */

import { Component, useState } from "@odoo/owl";
import { AutoComplete } from "@web/components/autocomplete/autocomplete";
import { Transition } from "@web/core/transition";
import { _t } from "@web/core/translation";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { getColor, sortCalendarFilters } from "@web/views/calendar/calendar_utils";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

let nextId = 1;

export class CalendarFilterSection extends Component {
    static components = {
        AutoComplete,
        Transition,
    };
    static template = "web.CalendarFilterSection";
    static subTemplates = {
        filter: "web.CalendarFilterSection.filter",
    };
    static props = {
        model: Object,
        section: Object,
    };

    /** @type {ReturnType<typeof useOwnedDialogs>} */
    addDialog;
    /** @type {import("services").ServiceFactories["orm"]} */
    orm;
    /** @type {{ collapsed: boolean; fieldRev: number }} */
    state;
    /** @type {Set} */
    unlinkingFilterIds;

    setup() {
        this.state = useState({
            collapsed: false,
            fieldRev: 1,
        });
        this.addDialog = useOwnedDialogs();
        this.orm = useService("orm");

        this.filterIdBase = nextId++;
        this.unlinkingFilterIds = new Set();
    }

    get autoCompleteProps() {
        return {
            autoSelect: true,
            resetOnSelect: true,
            placeholder: _t("+ Add %s", this.section.label),
            sources: [
                {
                    placeholder: _t("Loading..."),
                    options: (request) => this.loadSource(request),
                    optionSlot: "option",
                },
            ],
            value: "",
            class: "mt-1",
        };
    }

    get isAllActive() {
        return (
            this.section.filters.length &&
            this.section.filters.every((filter) => filter.active)
        );
    }

    /** @param {number | "all"} position */
    filterId(position) {
        return `${this.filterIdBase}_${position}`;
    }

    get section() {
        return this.props.section;
    }

    getFilterColor(filter) {
        return filter.colorIndex !== null
            ? `o_cw_filter_color_${getColor(filter.colorIndex)}`
            : "";
    }

    /** @returns {Object[]} */
    getSortedFilters() {
        return sortCalendarFilters(this.section.filters, ["user", "record", "dynamic"]);
    }

    /**
     * @param {string} request
     * @returns {Promise<Object[]>}
     */
    async loadSource(request) {
        const resModel = this.props.model.fields[this.section.fieldName].relation;
        const activeIds = this.section.filters.map((f) => f.value);
        const domain = [["id", "not in", activeIds]];
        const records = await this.orm.call(resModel, "name_search", [], {
            name: request,
            operator: "ilike",
            domain: domain,
            limit: 8,
            context: this.section.context,
        });

        const options = records.map((result) => ({
            data: {
                id: result[0],
            },
            label: result[1],
            onSelect: () =>
                this.props.model.createFilter(this.section.fieldName, result[0]),
        }));

        if (records.length > 7) {
            options.push({
                cssClass: "o_calendar_dropdown_option",
                label: _t("Search More..."),
                onSelect: () => this.onSearchMore(resModel, domain, request),
            });
        }

        if (!records.length) {
            options.push({
                cssClass: "o_m2o_no_result",
                label: _t("No records"),
            });
        }

        return options;
    }

    toggleSection() {
        this.state.collapsed = !this.state.collapsed;
    }

    onFilterInputChange(filter, ev) {
        this.props.model.updateFilters(
            this.section.fieldName,
            [filter],
            ev.target.checked,
        );
        this.render();
    }

    onAllFilterInputChange(ev) {
        const { fieldName, filters } = this.section;
        this.props.model.updateFilters(fieldName, filters, ev.target.checked);
        this.render();
    }

    onFilterRemoveBtnClick(filter) {
        if (this.unlinkingFilterIds.has(filter.recordId)) {
            return;
        }
        this.unlinkingFilterIds.add(filter.recordId);
        Promise.resolve(
            this.props.model.unlinkFilter(this.section.fieldName, filter.recordId),
        ).finally(() => this.unlinkingFilterIds.delete(filter.recordId));
        this.render();
    }

    async onSearchMore(resModel, domain, request) {
        const dynamicFilters = [];
        if (request.length) {
            const nameGets = await this.orm.call(resModel, "name_search", [], {
                name: request,
                domain: domain,
                operator: "ilike",
                context: this.section.context,
            });
            dynamicFilters.push({
                description: _t("Quick search: %s", request),
                domain: [["id", "in", nameGets.map((nameGet) => nameGet[0])]],
            });
        }
        this.addDialog(SelectCreateDialog, {
            title: _t("Search: %s", this.section.label),
            noCreate: true,
            multiSelect: true,
            resModel,
            context: this.section.context,
            domain,
            onSelected: (resId) =>
                this.props.model.createFilter(this.section.fieldName, resId),
            dynamicFilters,
        });
    }
}
