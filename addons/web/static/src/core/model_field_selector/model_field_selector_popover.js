import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";
import { _t } from "@web/core/l10n/translation";
import { fuzzyLookup } from "@web/core/utils/search";
import { KeepLast } from "@web/core/utils/concurrency";
import { sortBy } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";

class Page {
    constructor(resModel, fieldDefs, options = {}) {
        this.resModel = resModel;
        this.fieldDefs = fieldDefs;
        const {
            previousPage = null,
            selectedName = null,
            isDebugMode,
            readProperty = false,
        } = options;
        this.previousPage = previousPage;
        this.selectedName = selectedName;
        this.isDebugMode = isDebugMode;
        this.readProperty = readProperty;
        this.sortedFieldNames = sortBy(Object.keys(fieldDefs), (key) => fieldDefs[key].string);
        this.fieldNames = this.sortedFieldNames;
        this.query = "";
        this.focusedFieldName = null;
        this.resetFocusedFieldName();
    }

    get path() {
        const previousPath = this.previousPage?.path || "";
        const name = this.selectedName;

        if (this.readProperty && this.selectedField && this.selectedField.is_property) {
            if (this.selectedField.relation) {
                return `${previousPath}.get('${name}', env['${this.selectedField.relation}'])`;
            }
            return `${previousPath}.get('${name}')`;
        }
        if (name) {
            if (previousPath) {
                return `${previousPath}.${name}`;
            }
            return name;
        }
        return previousPath;
    }

    get selectedField() {
        return this.fieldDefs[this.selectedName];
    }

    get title() {
        const prefix = this.previousPage?.previousPage ? "... > " : "";
        const title = this.previousPage?.selectedField?.string || "";
        if (prefix.length || title.length) {
            return `${prefix}${title}`;
        }
        return _t("Select a field");
    }

    focus(direction) {
        if (!this.fieldNames.length) {
            return;
        }
        const index = this.fieldNames.indexOf(this.focusedFieldName);
        if (direction === "previous") {
            if (index === 0) {
                this.focusedFieldName = this.fieldNames[this.fieldNames.length - 1];
            } else {
                this.focusedFieldName = this.fieldNames[index - 1];
            }
        } else {
            if (index === this.fieldNames.length - 1) {
                this.focusedFieldName = this.fieldNames[0];
            } else {
                this.focusedFieldName = this.fieldNames[index + 1];
            }
        }
    }

    resetFocusedFieldName() {
        if (this.selectedName && this.fieldNames.includes(this.selectedName)) {
            this.focusedFieldName = this.selectedName;
        } else {
            this.focusedFieldName = this.fieldNames.length ? this.fieldNames[0] : null;
        }
    }

    searchFields(query = "") {
        this.query = query;
        this.fieldNames = this.sortedFieldNames;
        if (query) {
            this.fieldNames = fuzzyLookup(query, this.fieldNames, (key) => {
                const vals = [this.fieldDefs[key].string];
                if (this.isDebugMode) {
                    vals.push(key);
                }
                return vals;
            });
        }
        this.resetFocusedFieldName();
    }
}

export class ModelFieldSelectorPopover extends Component {
    static template = "web.ModelFieldSelectorPopover";
    static props = {
        close: Function,
        filter: { type: Function, optional: true },
        followRelations: { type: Boolean, optional: true },
        showDebugInput: { type: Boolean, optional: true },
        isDebugMode: { type: Boolean, optional: true },
        path: { optional: true },
        readProperty: { type: Boolean, optional: true },
        resModel: String,
        showSearchInput: { type: Boolean, optional: true },
        update: Function,
    };
    static defaultProps = {
        filter: (value) => value.searchable && value.type != "json" && value.type !== "separator",
        isDebugMode: false,
        followRelations: true,
    };

    setup() {
        this.fieldService = useService("field");
        this.state = useState({ page: null });
        this.keepLast = new KeepLast();
        this.debouncedSearchFields = debounce(this.searchFields.bind(this), 250);

        onWillStart(async () => {
            this.state.page = await this.loadPages(this.props.resModel, this.props.path);
        });

        const rootRef = useRef("root");
        useEffect(() => {
            const focusedElement = rootRef.el.querySelector(
                ".o_model_field_selector_popover_item.active"
            );
            if (focusedElement) {
                // current page can be empty (e.g. after a search)
                focusedElement.scrollIntoView({ block: "center" });
            }
        });
        useEffect(
            () => {
                if (this.props.showSearchInput) {
                    const searchInput = rootRef.el.querySelector(
                        ".o_model_field_selector_popover_search .o_input"
                    );
                    searchInput.focus();
                }
            },
            () => [this.state.page]
        );
    }

    get fieldNames() {
        return this.state.page.fieldNames;
    }

    get showDebugInput() {
        return this.props.showDebugInput ?? this.props.isDebugMode;
    }

    filter(fieldDefs, path) {
        const filteredKeys = Object.keys(fieldDefs).filter((k) =>
            this.props.filter(fieldDefs[k], path)
        );
        return Object.fromEntries(filteredKeys.map((k) => [k, fieldDefs[k]]));
    }

    async followRelation(fieldDef) {
        const { modelsInfo } = await this.keepLast.add(
            this.fieldService.loadPath(
                fieldDef.relation || this.state.page.resModel,
                `${fieldDef.name}.*`
            )
        );
        this.state.page.selectedName = fieldDef.name;
        const { resModel, fieldDefs } = modelsInfo.at(-1);
        this.openPage(
            new Page(resModel, this.filter(fieldDefs, this.state.page.path), {
                previousPage: this.state.page,
                isDebugMode: this.props.isDebugMode,
                readProperty: this.props.readProperty,
            })
        );
    }

    goToPreviousPage() {
        this.keepLast.add(Promise.resolve());
        this.openPage(this.state.page.previousPage);
    }

    async loadNewPath(path) {
        const newPage = await this.keepLast.add(this.loadPages(this.props.resModel, path));
        this.openPage(newPage);
    }

    async loadPages(resModel, path) {
        if (typeof path !== "string" || !path.length) {
            const fieldDefs = await this.fieldService.loadFields(resModel);
            return new Page(resModel, this.filter(fieldDefs, path), {
                isDebugMode: this.props.isDebugMode,
                readProperty: this.props.readProperty,
            });
        }
        const { isInvalid, modelsInfo, names } = await this.fieldService.loadPath(resModel, path);
        switch (isInvalid) {
            case "model":
                throw new Error(`Invalid model name: ${resModel}`);
            case "path": {
                const { resModel, fieldDefs } = modelsInfo[0];
                return new Page(resModel, this.filter(fieldDefs, path), {
                    selectedName: path,
                    isDebugMode: this.props.isDebugMode,
                    readProperty: this.props.readProperty,
                });
            }
            default: {
                let page = null;
                for (let index = 0; index < names.length; index++) {
                    const name = names[index];
                    const { resModel, fieldDefs } = modelsInfo[index];
                    page = new Page(resModel, this.filter(fieldDefs, path), {
                        previousPage: page,
                        selectedName: name,
                        isDebugMode: this.props.isDebugMode,
                        readProperty: this.props.readProperty,
                    });
                }
                return page;
            }
        }
    }

    openPage(page) {
        this.state.page = page;
        this.state.page.searchFields();
        this.props.update(page.path);
    }

    searchFields(query) {
        this.state.page.searchFields(query);
    }

    selectField(field) {
        if (field.type === "properties") {
            return this.followRelation(field);
        }
        this.keepLast.add(Promise.resolve());
        this.state.page.selectedName = field.name;
        this.props.update(this.state.page.path, field);
        this.props.close(true);
    }

    onDebugInputKeydown(ev) {
        switch (ev.key) {
            case "Enter": {
                ev.preventDefault();
                ev.stopPropagation();
                this.loadNewPath(ev.currentTarget.value);
                break;
            }
        }
    }

    // @TODO should rework/improve this and maybe use hotkeys
    async onInputKeydown(ev) {
        const { page } = this.state;
        switch (ev.key) {
            case "ArrowUp": {
                if (ev.target.selectionStart === 0) {
                    page.focus("previous");
                }
                break;
            }
            case "ArrowDown": {
                if (ev.target.selectionStart === page.query.length) {
                    page.focus("next");
                }
                break;
            }
            case "ArrowLeft": {
                if (ev.target.selectionStart === 0 && page.previousPage) {
                    this.goToPreviousPage();
                }
                break;
            }
            case "ArrowRight": {
                if (ev.target.selectionStart === page.query.length) {
                    const focusedFieldName = this.state.page.focusedFieldName;
                    if (focusedFieldName) {
                        const fieldDef = this.state.page.fieldDefs[focusedFieldName];
                        if (fieldDef.relation || fieldDef.type === "properties") {
                            this.followRelation(fieldDef);
                        }
                    }
                }
                break;
            }
            case "Enter": {
                const focusedFieldName = this.state.page.focusedFieldName;
                if (focusedFieldName) {
                    const fieldDef = this.state.page.fieldDefs[focusedFieldName];
                    this.selectField(fieldDef);
                } else {
                    ev.preventDefault();
                    ev.stopPropagation();
                }
                break;
            }
            case "Escape": {
                ev.preventDefault();
                ev.stopPropagation();
                this.props.close();
                break;
            }
        }
    }
}
