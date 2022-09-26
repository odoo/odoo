/** @odoo-module **/

import { usePopover } from "@web/core/popover/popover_hook";
import { _t } from "@web/core/l10n/translation";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Transition } from "@web/core/transition";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

const { Component, useState } = owl;

class FilterAutoComplete extends Component {
    setup() {
        this.orm = useService("orm");
        this.addDialog = useOwnedDialogs();
        this.state = useState({
            value: "",
        });
        this.sources = [{ placeholder: _t("Loading..."), options: this.loadSource.bind(this) }];
    }
    async loadSource(request) {
        const records = await this.orm.call(this.props.resModel, "name_search", [], {
            name: request,
            operator: "ilike",
            args: this.props.domain,
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
                action: this.onSearchMore.bind(this, request),
            });
        }

        return options;
    }
    async onSearchMore(request) {
        let dynamicFilters = [];
        if (request.length) {
            const nameGets = await this.orm.call(this.props.resModel, "name_search", [], {
                name: request,
                args: this.props.domain,
                operator: "ilike",
                context: {},
            });

            dynamicFilters = [
                {
                    description: sprintf(_t("Quick search: %s"), request),
                    domain: [["id", "in", nameGets.map((nameGet) => nameGet[0])]],
                },
            ];
        }
        const title = sprintf(this.env._t("Search: %s"), this.props.searchMoreTitle);
        this.addDialog(SelectCreateDialog, {
            title: title || _t("Select records"),
            noCreate: true,
            multiSelect: false,
            resModel: this.props.resModel,
            context: {},
            domain: this.props.domain,
            onSelected: (...args) => {
                console.log(...args);
            },
            dynamicFilters,
        });
    }

    onInput({ inputValue }) {
        this.state.value = inputValue;
    }
    onSelect(option, params = {}) {
        this.props.onSelect(option.value);
        this.state.value = "";
    }
}
FilterAutoComplete.template = "web.FilterAutoComplete";
FilterAutoComplete.components = {
    AutoComplete,
};

class CalendarFilterTooltip extends Component {}
CalendarFilterTooltip.template = "web.CalendarFilterPanel.tooltip";

let nextId = 1;

export class CalendarFilterPanel extends Component {
    setup() {
        this.state = useState({
            collapsed: {},
            fieldRev: 1,
        });

        this.popover = usePopover();
        this.removePopover = null;
    }

    getAutoCompleteProps(section) {
        return {
            resModel: this.props.model.fields[section.fieldName].relation,
            domain: [
                [
                    "id",
                    "not in",
                    section.filters.filter((f) => f.type !== "all").map((f) => f.value),
                ],
            ],
            searchMoreTitle: section.label,
            placeholder: `+ ${_t("Add")} ${section.label}`,
            onSelect: (value) => {
                this.props.model.createFilter(section.fieldName, value);
            },
        };
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
                if (a.type === "dynamic" && va !== vb) {
                    return va - vb;
                }
                return b.label.localeCompare(a.label);
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

    closeTooltip() {
        if (this.removePopover) {
            this.removePopover();
            this.removePopover = null;
        }
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

    onFilterMouseEnter(section, filter, ev) {
        this.closeTooltip();
        if (!section.hasAvatar || !filter.hasAvatar) {
            return;
        }

        this.removePopover = this.popover.add(
            ev.currentTarget,
            CalendarFilterTooltip,
            { section, filter },
            {
                closeOnClickAway: false,
                popoverClass: "o-calendar-filter--tooltip",
                position: "top",
            }
        );
    }

    onFilterMouseLeave() {
        this.closeTooltip();
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
    FilterAutoComplete,
    Transition,
};
CalendarFilterPanel.template = "web.CalendarFilterPanel";
CalendarFilterPanel.subTemplates = {
    filter: "web.CalendarFilterPanel.filter",
};
