/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Transition } from "@web/core/transition";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { getColor } from "../colors";
import { Component, useState } from "@odoo/owl";

let nextId = 1;

export class CalendarFilterPanel extends Component {
    setup() {
        this.state = useState({
            collapsed: {},
            fieldRev: 1,
        });
        this.addDialog = useOwnedDialogs();
        this.orm = useService("orm");
    }

    getFilterColor(filter) {
        return filter.colorIndex !== null ? "o_cw_filter_color_" + getColor(filter.colorIndex) : "";
    }

    getAutoCompleteProps(section) {
        return {
            autoSelect: true,
            resetOnSelect: true,
            placeholder: _t("+ Add %s", section.label),
            sources: [
                {
                    placeholder: _t("Loading..."),
                    options: (request) => this.loadSource(section, request),
                },
            ],
            onSelect: (option, params = {}) => {
                if (option.action) {
                    option.action(params);
                    return;
                }
                this.props.model.createFilter(section.fieldName, option.value);
            },
            value: "",
        };
    }

    async loadSource(section, request) {
        const resModel = this.props.model.fields[section.fieldName].relation;
        const domain = [
            ["id", "not in", section.filters.filter((f) => f.type !== "all").map((f) => f.value)],
        ];
        const records = await this.orm.call(resModel, "name_search", [], {
            name: request,
            operator: "ilike",
            args: domain,
            limit: 8,
            context: {},
        });

        const options = records.map((result) => ({
            value: result[0],
            label: result[1],
        }));

        if (records.length > 7) {
            options.push({
                label: _t("Search More..."),
                action: () => this.onSearchMore(section, resModel, domain, request),
            });
        }

        if (records.length === 0) {
            options.push({
                label: _t("No records"),
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }

        return options;
    }

    async onSearchMore(section, resModel, domain, request) {
        const dynamicFilters = [];
        if (request.length) {
            const nameGets = await this.orm.call(resModel, "name_search", [], {
                name: request,
                args: domain,
                operator: "ilike",
                context: {},
            });
            dynamicFilters.push({
                description: _t("Quick search: %s", request),
                domain: [["id", "in", nameGets.map((nameGet) => nameGet[0])]],
            });
        }
        const title = _t("Search: %s", section.label);
        this.addDialog(SelectCreateDialog, {
            title,
            noCreate: true,
            multiSelect: false,
            resModel,
            context: {},
            domain,
            onSelected: ([resId]) => this.props.model.createFilter(section.fieldName, resId),
            dynamicFilters,
        });
    }

    get nextFilterId() {
        nextId += 1;
        return nextId;
    }

    isAllActive(section) {
        let active = true;
        for (const filter of section.filters) {
            if (filter.type !== "all" && !filter.active) {
                active = false;
                break;
            }
        }
        return active;
    }
    getFilterTypePriority(type) {
        return ["user", "record", "dynamic", "all"].indexOf(type);
    }
    getSortedFilters(section) {
        return section.filters.slice().sort((a, b) => {
            if (a.type === b.type) {
                const va = a.value ? -1 : 0;
                const vb = b.value ? -1 : 0;
                //Condition to put unvaluable item (eg: Open Shifts) at the end of the sorted list.
                if (a.type === "dynamic" && va !== vb) {
                    return va - vb;
                }
                return a.label.localeCompare(b.label, undefined, {
                    numeric: true,
                    sensitivity: "base",
                    ignorePunctuation: true,
                });
            } else {
                return this.getFilterTypePriority(a.type) - this.getFilterTypePriority(b.type);
            }
        });
    }

    toggleSection(section) {
        if (section.canCollapse) {
            this.state.collapsed[section.fieldName] = !this.state.collapsed[section.fieldName];
        }
    }

    isSectionCollapsed(section) {
        return this.state.collapsed[section.fieldName] || false;
    }

    onFilterInputChange(section, filter, ev) {
        this.props.model.updateFilters(section.fieldName, {
            [filter.value]: ev.target.checked,
        });
    }

    onAllFilterInputChange(section, ev) {
        const filters = {};
        for (const filter of section.filters) {
            if (filter.type !== "all") {
                filters[filter.value] = ev.target.checked;
            }
        }
        this.props.model.updateFilters(section.fieldName, filters);
    }

    onFilterRemoveBtnClick(section, filter) {
        this.props.model.unlinkFilter(section.fieldName, filter.recordId);
    }

    onFieldChanged(fieldName, filterValue) {
        this.state.fieldRev += 1;
        this.props.model.createFilter(fieldName, filterValue);
    }
}

CalendarFilterPanel.components = {
    AutoComplete,
    Transition,
};
CalendarFilterPanel.template = "web.CalendarFilterPanel";
CalendarFilterPanel.subTemplates = {
    filter: "web.CalendarFilterPanel.filter",
};
