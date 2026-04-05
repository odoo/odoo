/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillDestroy,
    onWillUpdateProps,
    useChildSubEnv,
    useEffect,
    useState,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@odx_owl/components/dialog/dialog";
import { cn } from "@odx_owl/core/utils/cn";
import {
    filterCollectionItems,
    findCollectionItemByValue,
    firstEnabledItem,
    groupCollectionItems,
    isSameCollectionValue,
    normalizeCollectionItems,
} from "@odx_owl/core/utils/collection";
import { resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId, sanitizeIdFragment } from "@odx_owl/core/utils/ids";

function resolveActiveValue(items, ...candidates) {
    for (const candidate of candidates) {
        const match = items.find(
            (item) => !item.disabled && isSameCollectionValue(item.value, candidate)
        );
        if (match) {
            return match.value;
        }
    }
    return firstEnabledItem(items)?.value ?? null;
}

function sortRegisteredItems(items = []) {
    return [...items].sort((left, right) => left.order - right.order);
}

class CommandAutoItems extends Component {
    static template = "odx_owl.CommandAutoItems";

    get groupedItems() {
        return this.env.odxCommand.groupedItems;
    }

    getItemId(item) {
        return this.env.odxCommand.getItemId(item);
    }

    getItemClasses(item) {
        return this.env.odxCommand.getItemClasses(item);
    }

    isSelected(item) {
        return this.env.odxCommand.isSelected(item.value);
    }

    isActive(item) {
        return this.env.odxCommand.isActive(item.value);
    }

    setActive(value) {
        this.env.odxCommand.setActive(value);
    }

    selectItem(item) {
        this.env.odxCommand.selectItem(item);
    }
}

export class CommandInput extends Component {
    static template = "odx_owl.CommandInput";
    static props = {
        className: { type: String, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        placeholder: "",
    };

    get inputClasses() {
        return this.env.odxCommand.getInputClasses(this.props.className);
    }

    get placeholder() {
        return this.props.placeholder || this.env.odxCommand.placeholder;
    }

    onInput(ev) {
        this.env.odxCommand.onInput(ev);
    }

    onKeydown(ev) {
        this.env.odxCommand.onInputKeydown(ev);
    }
}

export class CommandList extends Component {
    static template = "odx_owl.CommandList";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };

    get classes() {
        return cn("odx-command__list", this.props.className);
    }
}

export class CommandEmpty extends Component {
    static template = "odx_owl.CommandEmpty";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        text: "",
    };

    get classes() {
        return cn("odx-command__empty", this.props.className);
    }

    get isVisible() {
        return !this.env.odxCommand.isLoading && !this.env.odxCommand.hasResults;
    }

    get text() {
        return this.props.text || this.env.odxCommand.emptyLabel;
    }
}

export class CommandLoading extends Component {
    static template = "odx_owl.CommandLoading";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        text: "",
    };

    get classes() {
        return cn("odx-command__loading", this.props.className);
    }

    get isVisible() {
        return this.env.odxCommand.isLoading;
    }

    get text() {
        return this.props.text || this.env.odxCommand.loadingLabel;
    }
}

export class CommandGroup extends Component {
    static template = "odx_owl.CommandGroup";
    static props = {
        className: { type: String, optional: true },
        heading: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        heading: "",
        tag: "section",
        text: "",
    };

    setup() {
        this.token = nextId("odx-command-group");
        useChildSubEnv({
            odxCommandGroup: {
                heading: this.headingText,
                token: this.token,
            },
        });
    }

    get classes() {
        return cn("odx-command__group", this.props.className);
    }

    get headingText() {
        return this.props.heading || this.props.text;
    }

    get isVisible() {
        return !this.env.odxCommand.hasQuery || this.env.odxCommand.getVisibleCount(this.token) > 0;
    }
}

export class CommandSeparator extends Component {
    static template = "odx_owl.CommandSeparator";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-command__separator", this.props.className);
    }

    get isVisible() {
        return !this.env.odxCommand.hasQuery;
    }
}

export class CommandShortcut extends Component {
    static template = "odx_owl.CommandShortcut";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "span",
        text: "",
    };

    get classes() {
        return cn("odx-command__shortcut", this.props.className);
    }
}

export class CommandItemText extends Component {
    static template = "odx_owl.CommandItemText";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "span",
        text: "",
    };

    get classes() {
        return cn("odx-command__item-label", this.props.className);
    }
}

export class CommandItemDescription extends Component {
    static template = "odx_owl.CommandItemDescription";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "span",
        text: "",
    };

    get classes() {
        return cn("odx-command__item-description", this.props.className);
    }
}

export class CommandItem extends Component {
    static template = "odx_owl.CommandItem";
    static props = {
        className: { type: String, optional: true },
        description: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        keywords: { type: String, optional: true },
        label: { type: String, optional: true },
        shortcut: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        className: "",
        description: "",
        disabled: false,
        keywords: "",
        label: "",
        shortcut: "",
        text: "",
    };

    setup() {
        this.token = nextId("odx-command-item");

        onMounted(() => {
            this.register(this.props);
        });

        onWillUpdateProps((nextProps) => {
            this.register(nextProps);
        });

        onWillDestroy(() => {
            this.env.odxCommand.unregisterItem(this.token);
        });
    }

    buildMeta(props = this.props) {
        const label = props.label || props.text || String(props.value ?? "");
        const group = this.env.odxCommandGroup || {};
        return {
            description: props.description || "",
            disabled: Boolean(props.disabled),
            group: group.heading || "",
            groupToken: group.token || "",
            id:
                props.id ||
                `${this.env.odxCommand.listId}-${sanitizeIdFragment(label)}-${sanitizeIdFragment(
                    this.token
                )}`,
            key: this.token,
            keywords: props.keywords || "",
            label,
            shortcut: props.shortcut || "",
            value: props.value,
        };
    }

    register(props = this.props) {
        this.env.odxCommand.registerItem(this.token, this.buildMeta(props));
    }

    get item() {
        return this.buildMeta();
    }

    get classes() {
        return cn(this.env.odxCommand.getItemClasses(this.item), this.props.className);
    }

    get isVisible() {
        return this.env.odxCommand.isItemVisible(this.token);
    }

    get isActive() {
        return this.env.odxCommand.isActive(this.props.value);
    }

    get isSelected() {
        return this.env.odxCommand.isSelected(this.props.value);
    }

    onMouseenter() {
        this.env.odxCommand.setActive(this.props.value);
    }

    onClick() {
        this.env.odxCommand.selectItem(this.item);
    }
}

CommandItem.components = {
    CommandItemDescription,
    CommandItemText,
    CommandShortcut,
};

export class Command extends Component {
    static template = "odx_owl.Command";
    static components = {
        CommandAutoItems,
        CommandEmpty,
        CommandGroup,
        CommandInput,
        CommandItem,
        CommandItemDescription,
        CommandItemText,
        CommandList,
        CommandLoading,
        CommandSeparator,
        CommandShortcut,
    };
    static props = {
        ariaLabel: { type: String, optional: true },
        autoFocus: { type: Boolean, optional: true },
        className: { type: String, optional: true },
        defaultQuery: { type: String, optional: true },
        dir: { type: String, optional: true },
        emptyLabel: { type: String, optional: true },
        inputClassName: { type: String, optional: true },
        inputId: { type: String, optional: true },
        items: { type: Array, optional: true },
        listId: { type: String, optional: true },
        loading: { type: Boolean, optional: true },
        loadingLabel: { type: String, optional: true },
        onQueryChange: { type: Function, optional: true },
        onSelect: { type: Function, optional: true },
        placeholder: { type: String, optional: true },
        query: { type: String, optional: true },
        selectedValue: { optional: true, validate: () => true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        autoFocus: false,
        className: "",
        defaultQuery: "",
        emptyLabel: "No results found.",
        inputClassName: "",
        items: [],
        loading: false,
        loadingLabel: "Loading...",
        placeholder: "Type a command or search...",
    };

    setup() {
        const self = this;
        this.state = useState({
            activeValue: null,
            inputId: nextId("odx-command-input"),
            listId: nextId("odx-command-list"),
            query: this.props.query ?? this.props.defaultQuery,
            registeredItems: [],
            registryOrder: 0,
        });
        this.syncActiveValue();

        useChildSubEnv({
            odxCommand: {
                get activeItemId() {
                    return self.activeItemId;
                },
                get ariaLabel() {
                    return self.props.ariaLabel;
                },
                get currentQuery() {
                    return self.currentQuery;
                },
                get dir() {
                    return self.direction;
                },
                get emptyLabel() {
                    return self.props.emptyLabel;
                },
                get groupedItems() {
                    return self.groupedItems;
                },
                get hasQuery() {
                    return Boolean(String(self.currentQuery || "").trim());
                },
                get hasResults() {
                    return Boolean(self.filteredItems.length);
                },
                get isLoading() {
                    return self.props.loading;
                },
                get inputId() {
                    return self.inputId;
                },
                get listId() {
                    return self.listId;
                },
                get loadingLabel() {
                    return self.props.loadingLabel;
                },
                get placeholder() {
                    return self.props.placeholder;
                },
                getInputClasses: (className = "") => self.getInputClasses(className),
                getItemClasses: (item) => self.getItemClasses(item),
                getItemId: (item) => self.getItemId(item),
                getVisibleCount: (groupToken) => self.getVisibleCount(groupToken),
                isActive: (value) => self.isActiveValue(value),
                isItemVisible: (token) => self.isItemVisible(token),
                isSelected: (value) => self.isSelectedValue(value),
                onInput: (ev) => self.onInput(ev),
                onInputKeydown: (ev) => self.onInputKeydown(ev),
                registerItem: (token, item) => self.registerItem(token, item),
                selectItem: (item) => self.selectItem(item),
                setActive: (value) => self.setActive(value),
                setQuery: (value) => self.setQuery(value),
                unregisterItem: (token) => self.unregisterItem(token),
            },
        });

        useEffect(
            () => {
                if (!this.props.autoFocus) {
                    return;
                }
                browser.requestAnimationFrame(() =>
                    document.getElementById(this.inputId)?.focus()
                );
            },
            () => [this.props.autoFocus, this.inputId]
        );

        onWillUpdateProps((nextProps) => {
            if (nextProps.query !== undefined) {
                this.state.query = nextProps.query;
            }
            const nextItems = nextProps.items?.length
                ? filterCollectionItems(
                      normalizeCollectionItems(nextProps.items || []),
                      nextProps.query ?? this.state.query
                  )
                : this.filteredItems;
            this.state.activeValue = resolveActiveValue(
                nextItems,
                this.state.activeValue,
                nextProps.selectedValue
            );
        });
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get registeredItems() {
        return sortRegisteredItems(this.state.registeredItems);
    }

    get sourceItems() {
        return this.props.items.length
            ? normalizeCollectionItems(this.props.items)
            : this.registeredItems;
    }

    get currentQuery() {
        return this.props.query ?? this.state.query;
    }

    get inputId() {
        return this.props.inputId || this.state.inputId;
    }

    get listId() {
        return this.props.listId || this.state.listId;
    }

    get filteredItems() {
        return filterCollectionItems(this.sourceItems, this.currentQuery);
    }

    get groupedItems() {
        return groupCollectionItems(this.filteredItems);
    }

    get selectableItems() {
        return this.filteredItems.filter((item) => !item.disabled);
    }

    get filteredItemTokens() {
        return new Set(this.filteredItems.map((item) => item.key || item.token));
    }

    get classes() {
        return cn("odx-command", this.props.className);
    }

    get hasCustomContent() {
        return Boolean(this.props.slots?.default);
    }

    getInputClasses(className = "") {
        return cn("odx-command__input", this.props.inputClassName, className);
    }

    registerItem(token, item) {
        const existingIndex = this.state.registeredItems.findIndex((entry) => entry.token === token);
        const nextItem = {
            ...item,
            order:
                existingIndex === -1
                    ? this.state.registryOrder++
                    : this.state.registeredItems[existingIndex].order,
            token,
        };
        if (existingIndex === -1) {
            this.state.registeredItems.push(nextItem);
        } else {
            this.state.registeredItems.splice(existingIndex, 1, nextItem);
        }
        this.syncActiveValue(this.state.activeValue);
    }

    unregisterItem(token) {
        const existingIndex = this.state.registeredItems.findIndex((entry) => entry.token === token);
        if (existingIndex !== -1) {
            this.state.registeredItems.splice(existingIndex, 1);
        }
        this.syncActiveValue(this.state.activeValue);
    }

    syncActiveValue(preferredValue) {
        this.state.activeValue = resolveActiveValue(
            this.selectableItems,
            preferredValue,
            this.state.activeValue,
            this.props.selectedValue
        );
    }

    setQuery(value) {
        if (this.props.query === undefined) {
            this.state.query = value;
        }
        this.props.onQueryChange?.(value);
        this.syncActiveValue();
    }

    onInput(ev) {
        this.setQuery(ev.target.value);
    }

    moveActive(direction) {
        if (!this.selectableItems.length) {
            this.state.activeValue = null;
            return;
        }
        const currentIndex = this.selectableItems.findIndex((item) =>
            isSameCollectionValue(item.value, this.state.activeValue)
        );
        const safeIndex = currentIndex === -1 ? 0 : currentIndex;
        const nextIndex =
            (safeIndex + direction + this.selectableItems.length) % this.selectableItems.length;
        this.state.activeValue = this.selectableItems[nextIndex].value;
    }

    onInputKeydown(ev) {
        if (!this.selectableItems.length) {
            if (ev.key === "Escape") {
                ev.preventDefault();
                ev.stopPropagation();
            }
            return;
        }
        if (!["ArrowDown", "ArrowUp", "Home", "End", "Enter"].includes(ev.key)) {
            return;
        }
        ev.preventDefault();
        if (ev.key === "Home") {
            this.state.activeValue = this.selectableItems[0].value;
            return;
        }
        if (ev.key === "End") {
            this.state.activeValue = this.selectableItems[this.selectableItems.length - 1].value;
            return;
        }
        if (ev.key === "ArrowDown") {
            this.moveActive(1);
            return;
        }
        if (ev.key === "ArrowUp") {
            this.moveActive(-1);
            return;
        }
        const activeItem = findCollectionItemByValue(this.selectableItems, this.state.activeValue);
        if (activeItem) {
            this.selectItem(activeItem);
        }
    }

    setActive(value) {
        this.state.activeValue = value;
    }

    selectItem(item) {
        if (item.disabled) {
            return;
        }
        this.props.onSelect?.(item.value, item);
    }

    isActiveValue(value) {
        return isSameCollectionValue(value, this.state.activeValue);
    }

    isSelectedValue(value) {
        return isSameCollectionValue(value, this.props.selectedValue);
    }

    getItemClasses(item) {
        return cn("odx-command__item", {
            "odx-command__item--active": this.isActiveValue(item.value),
            "odx-command__item--selected": this.isSelectedValue(item.value),
            "odx-command__item--disabled": item.disabled,
        });
    }

    getItemId(item) {
        return item.id || `${this.listId}-${item.key}`;
    }

    get activeItemId() {
        const item = findCollectionItemByValue(this.filteredItems, this.state.activeValue);
        return item ? this.getItemId(item) : undefined;
    }

    isItemVisible(token) {
        return !this.currentQuery || this.filteredItemTokens.has(token);
    }

    getVisibleCount(groupToken) {
        return this.filteredItems.filter((item) => item.groupToken === groupToken).length;
    }
}

export class CommandDialog extends Component {
    static template = "odx_owl.CommandDialog";
    static components = {
        Command,
        Dialog,
    };
    static props = {
        className: { type: String, optional: true },
        contentClass: { type: String, optional: true },
        defaultOpen: { type: Boolean, optional: true },
        description: { type: String, optional: true },
        emptyLabel: { type: String, optional: true },
        items: { type: Array, optional: true },
        loading: { type: Boolean, optional: true },
        loadingLabel: { type: String, optional: true },
        onOpenChange: { type: Function, optional: true },
        onQueryChange: { type: Function, optional: true },
        onSelect: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        placeholder: { type: String, optional: true },
        query: { type: String, optional: true },
        selectedValue: { optional: true, validate: () => true },
        slots: { type: Object, optional: true },
        title: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        contentClass: "",
        defaultOpen: false,
        description: "Search for a command to run...",
        emptyLabel: "No results found.",
        items: [],
        loading: false,
        loadingLabel: "Loading...",
        placeholder: "Type a command or search...",
        title: "Command Palette",
    };

    setup() {
        this.state = useState({
            open: this.props.open ?? this.props.defaultOpen,
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.open !== undefined) {
                this.state.open = nextProps.open;
            }
        });
    }

    get isOpen() {
        return this.props.open ?? this.state.open;
    }

    get contentClasses() {
        return cn("odx-command-dialog__content", this.props.contentClass);
    }

    setOpen(open) {
        if (this.props.open === undefined) {
            this.state.open = open;
        }
        this.props.onOpenChange?.(open);
    }

    onCommandSelect(value, item) {
        this.props.onSelect?.(value, item);
        this.setOpen(false);
    }
}

CommandAutoItems.components = {
    CommandGroup,
    CommandItemDescription,
    CommandItemText,
    CommandShortcut,
};

CommandItem.components = {
    CommandItemDescription,
    CommandItemText,
    CommandShortcut,
};
