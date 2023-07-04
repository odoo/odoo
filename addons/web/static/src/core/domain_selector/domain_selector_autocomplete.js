/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { formatAST, toPyValue } from "@web/core/py_js/py_utils";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { Expression } from "@web/core/domain_tree";

const SEARCH_LIMIT = 7;
const SEARCH_MORE_LIMIT = 320;

const isId = (val) => Number.isInteger(val) && val >= 1;

class AutoCompleteWithSources extends Component {
    static props = {
        resModel: String,
        update: Function,
        multiSelect: Boolean,
        getIds: Function,
        value: String,
        className: { type: String, optional: true },
        fieldString: { type: String, optional: true },
    };
    static components = { AutoComplete };
    static template = "web.DomainSelector.AutoCompleteWithSources";

    setup() {
        this.orm = useService("orm");
        this.nameService = useService("name");
        this.addDialog = useOwnedDialogs();
        this.sources = [
            {
                placeholder: _t("Loading..."),
                options: this.loadOptionsSource.bind(this),
            },
        ];
    }

    addNames(nameGets) {
        const displayNames = {};
        for (const [id, label] of nameGets) {
            displayNames[id] = label.split("\n")[0];
        }
        this.nameService.addDisplayNames(this.props.resModel, displayNames);
    }

    getIds() {
        return this.props.getIds();
    }

    async loadOptionsSource(name) {
        if (this.lastProm) {
            this.lastProm.abort(false);
        }
        this.lastProm = this.search(name, SEARCH_LIMIT + 1);
        const nameGets = await this.lastProm;
        this.addNames(nameGets);
        const options = nameGets.map(([value, label]) => ({ value, label: label.split("\n")[0] }));
        if (SEARCH_LIMIT < nameGets.length) {
            options.push({
                label: _t("Search More..."),
                action: this.onSearchMore.bind(this, name),
                classList: "o_m2o_dropdown_option",
            });
        }
        if (options.length === 0) {
            options.push({ label: _t("(no result)"), unselectable: true });
        }
        return options;
    }

    async onSearchMore(name) {
        const { fieldString, multiSelect, resModel } = this.props;
        let operator;
        const ids = [];
        if (name) {
            const nameGets = await this.search(name, SEARCH_MORE_LIMIT);
            this.addNames(nameGets);
            operator = "in";
            ids.push(...nameGets.map((nameGet) => nameGet[0]));
        } else {
            operator = "not in";
            ids.push(...this.getIds());
        }
        const dynamicFilters = ids.length
            ? [
                  {
                      description: sprintf(_t("Quick search: %s"), name),
                      domain: [["id", operator, ids]],
                  },
              ]
            : undefined;
        // fine for now but we don't like this kind of dependence of core to views
        const SelectCreateDialog = registry.category("dialogs").get("select_create");
        this.addDialog(SelectCreateDialog, {
            title: sprintf(_t("Search: %s"), fieldString),
            dynamicFilters,
            resModel,
            noCreate: true,
            multiSelect,
            onSelected: (resId) => {
                const resIds = Array.isArray(resId) ? resId : [resId];
                this.props.update([...resIds]);
            },
        });
    }

    onSelect({ value: resId, action }, params) {
        if (action) {
            return action(params);
        }
        this.props.update([resId]);
    }

    search(name, limit) {
        const ids = this.getIds();
        const domain = [["id", "not in", ids]];
        return this.orm.call(this.props.resModel, "name_search", [], {
            name,
            args: domain,
            limit,
        });
    }

    onChange({ inputValue }) {
        if (!inputValue.length) {
            this.props.update([]);
        }
    }
}

const getFormat = (val, displayNames) => {
    let text;
    let colorIndex;
    if (isId(val)) {
        text =
            typeof displayNames[val] === "string"
                ? displayNames[val]
                : sprintf(_t(`Inaccessible/missing record ID: %s`), val);
        colorIndex = typeof displayNames[val] === "string" ? 0 : 2; // 0 = grey, 2 = orange
    } else {
        text =
            val instanceof Expression
                ? String(val)
                : sprintf(_t(`Invalid record ID: %s`), formatAST(toPyValue(val)));
        colorIndex = val instanceof Expression ? 2 : 1; // 1 = red
    }
    return { text, colorIndex };
};

export class DomainSelectorAutocomplete extends Component {
    static props = {
        resModel: String,
        update: Function,
        value: true,
        fieldString: { type: String, optional: true },
    };
    static components = { AutoCompleteWithSources, TagsList };
    static template = "web.DomainSelector.DomainSelectorAutocomplete";

    setup() {
        this.nameService = useService("name");
        onWillStart(() => this.computeDerivedParams());
        onWillUpdateProps((nextProps) => this.computeDerivedParams(nextProps));
    }

    async computeDerivedParams(props = this.props) {
        const displayNames = await this.getDisplayNames(props);
        this.tags = this.getTags(props, displayNames);
    }

    async getDisplayNames(props) {
        const ids = this.getIds(props);
        return this.nameService.loadDisplayNames(props.resModel, ids);
    }

    getIds(props = this.props) {
        return props.value.filter((val) => isId(val));
    }

    getTags(props, displayNames) {
        return props.value.map((val, index) => {
            const { text, colorIndex } = getFormat(val, displayNames);
            return {
                text,
                colorIndex,
                onDelete: () => {
                    this.props.update([
                        ...this.props.value.slice(0, index),
                        ...this.props.value.slice(index + 1),
                    ]);
                },
            };
        });
    }

    update(resIds) {
        this.props.update([...this.props.value, ...resIds]);
    }
}

export class DomainSelectorSingleAutocomplete extends Component {
    static props = {
        resModel: String,
        update: Function,
        value: true,
        fieldString: { type: String, optional: true },
    };
    static components = { AutoCompleteWithSources };
    static template = "web.DomainSelector.DomainSelectorSingleAutocomplete";

    setup() {
        this.nameService = useService("name");
        onWillStart(() => this.computeDerivedParams());
        onWillUpdateProps((nextProps) => this.computeDerivedParams(nextProps));
    }

    async computeDerivedParams(props = this.props) {
        const displayNames = await this.getDisplayNames(props);
        this.displayName = this.getDisplayName(props, displayNames);
    }

    async getDisplayNames(props) {
        const ids = this.getIds(props);
        return this.nameService.loadDisplayNames(props.resModel, ids);
    }

    getDisplayName(props = this.props, displayNames) {
        const { value } = props;
        if (value === false) {
            return "";
        }
        const { text } = getFormat(value, displayNames);
        return text;
    }

    getIds(props = this.props) {
        if (isId(props.value)) {
            return [props.value];
        }
        return [];
    }

    update(resIds) {
        this.props.update(resIds[0] || false);
        this.render(true);
    }
}
