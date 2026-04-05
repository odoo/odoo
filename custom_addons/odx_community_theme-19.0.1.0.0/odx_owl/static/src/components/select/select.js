/** @odoo-module **/

import {
    Component,
    onMounted,
    status,
    onWillDestroy,
    onWillUpdateProps,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Popover } from "@odx_owl/components/popover/popover";
import { cn } from "@odx_owl/core/utils/cn";
import {
    findCollectionItemByValue,
    firstEnabledItem,
    groupCollectionItems,
    isSameCollectionValue,
    normalizeCollectionItems,
} from "@odx_owl/core/utils/collection";
import { resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId, sanitizeIdFragment } from "@odx_owl/core/utils/ids";

const TYPEAHEAD_RESET_DELAY = 700;

function resolveHighlightValue(items, ...candidates) {
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

function isTypeaheadKey(ev) {
    return (
        ev.key.length === 1 &&
        !ev.altKey &&
        !ev.ctrlKey &&
        !ev.metaKey &&
        !ev.isComposing &&
        ev.key.trim() !== ""
    );
}

function normalizeTypeaheadLabel(item) {
    return String(item?.label ?? item?.value ?? "")
        .trim()
        .toLowerCase();
}

function buildTypeaheadQuery(currentQuery, key) {
    const nextCharacter = String(key || "").toLowerCase();
    const nextQuery = `${currentQuery}${nextCharacter}`;
    return nextQuery.length > 1 && [...nextQuery].every((char) => char === nextCharacter)
        ? nextCharacter
        : nextQuery;
}

function findTypeaheadMatch(items, query, currentValue) {
    const enabledItems = items.filter((item) => !item.disabled);
    if (!enabledItems.length) {
        return null;
    }
    const normalizedQuery = String(query || "").trim().toLowerCase();
    if (!normalizedQuery) {
        return null;
    }
    const currentIndex = enabledItems.findIndex((item) =>
        isSameCollectionValue(item.value, currentValue)
    );
    const orderedItems =
        currentIndex === -1
            ? enabledItems
            : enabledItems
                  .slice(currentIndex + 1)
                  .concat(enabledItems.slice(0, currentIndex + 1));
    return (
        orderedItems.find((item) => normalizeTypeaheadLabel(item).startsWith(normalizedQuery)) ||
        null
    );
}

class SelectBase extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

class SelectItems extends Component {
    static template = "odx_owl.SelectItems";
    get groupedItems() {
        this.env.odxSelect.state.version;
        return this.env.odxSelect.groupedItems;
    }

    getItemId(item) {
        return this.env.odxSelect.getItemId(item);
    }

    getItemClasses(item) {
        return this.env.odxSelect.getItemClasses(item);
    }

    isSelected(item) {
        return this.env.odxSelect.isSelected(item.value);
    }

    isHighlighted(item) {
        return this.env.odxSelect.isHighlighted(item.value);
    }

    setHighlighted(value) {
        this.env.odxSelect.setHighlighted(value);
    }

    selectItem(item) {
        this.env.odxSelect.selectItem(item);
    }
}

export class SelectTrigger extends Component {
    static template = "odx_owl.SelectTrigger";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return this.env.odxSelect.getTriggerClasses(this.props.className);
    }

    get selectedItem() {
        this.env.odxSelect.state.version;
        return this.env.odxSelect.selectedItem;
    }

    onKeydown(ev) {
        this.env.odxSelect.onTriggerKeydown(ev);
    }
}

export class SelectValue extends Component {
    static template = "odx_owl.SelectValue";
    static props = {
        className: { type: String, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        placeholder: "",
    };

    get classes() {
        return cn("odx-select__value", this.props.className);
    }

    get text() {
        this.env.odxSelect.state.version;
        return (
            this.env.odxSelect.getSelectedLabel() ||
            this.props.placeholder ||
            this.env.odxSelect.placeholder
        );
    }
}

export class SelectIcon extends Component {
    static template = "odx_owl.SelectIcon";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "span",
    };

    get classes() {
        return cn("odx-select__icon", this.props.className);
    }
}

SelectTrigger.components = {
    SelectIcon,
    SelectValue,
};

export class SelectScrollUpButton extends Component {
    static template = "odx_owl.SelectScrollUpButton";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-select__scroll-button", "odx-select__scroll-button--up", this.props.className);
    }

    get isVisible() {
        this.env.odxSelect.state.version;
        return this.env.odxSelect.canScrollUp;
    }

    onClick() {
        this.env.odxSelect.scrollViewport("up");
    }
}

export class SelectScrollDownButton extends Component {
    static template = "odx_owl.SelectScrollDownButton";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-select__scroll-button", "odx-select__scroll-button--down", this.props.className);
    }

    get isVisible() {
        this.env.odxSelect.state.version;
        return this.env.odxSelect.canScrollDown;
    }

    onClick() {
        this.env.odxSelect.scrollViewport("down");
    }
}

export class SelectViewport extends Component {
    static template = "odx_owl.SelectViewport";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };

    setup() {
        this.viewportRef = useRef("viewportRef");
        onMounted(() => this.env.odxSelect.registerViewport(this.viewportRef.el));
        onWillDestroy(() => this.env.odxSelect.unregisterViewport(this.viewportRef.el));
    }

    get classes() {
        return cn("odx-select__viewport", this.props.className);
    }

    onKeydown(ev) {
        this.env.odxSelect.onListKeydown(ev);
    }

    onScroll() {
        this.env.odxSelect.syncViewportState();
    }
}

export class SelectContent extends SelectBase {
    static template = "odx_owl.SelectContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-select__list";

    onKeydown(ev) {
        this.env.odxSelect.onListKeydown(ev);
    }
}

export class SelectGroup extends SelectBase {
    static template = "odx_owl.SelectGroup";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "section",
    };
    baseClass = "odx-select__group";
}

export class SelectLabel extends SelectBase {
    static template = "odx_owl.SelectLabel";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
        text: "",
    };
    baseClass = "odx-select__group-label";
}

export class SelectSeparator extends SelectBase {
    static template = "odx_owl.SelectSeparator";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };
    baseClass = "odx-select__separator";
}

export class SelectItem extends Component {
    static template = "odx_owl.SelectItem";
    static props = {
        className: { type: String, optional: true },
        description: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        label: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
        value: { validate: () => true },
    };
    static defaultProps = {
        className: "",
        description: "",
        disabled: false,
        label: "",
        text: "",
    };

    setup() {
        this.token = nextId("odx-select-item");

        onMounted(() => {
            this.register(this.props);
        });

        onWillUpdateProps((nextProps) => {
            this.register(nextProps);
        });

        onWillDestroy(() => {
            this.env.odxSelect.unregisterItem(this.token);
        });
    }

    buildItemMeta(props = this.props) {
        const label = props.label || props.text || String(props.value ?? "");
        const itemId =
            props.id ||
            `${this.env.odxSelect.listId}-${sanitizeIdFragment(label)}-${sanitizeIdFragment(
                this.token
            )}`;
        return {
            description: props.description || "",
            disabled: Boolean(props.disabled),
            id: itemId,
            label,
            value: props.value,
        };
    }

    register(props = this.props) {
        this.env.odxSelect.registerItem(this.token, this.buildItemMeta(props));
    }

    get itemMeta() {
        return this.buildItemMeta();
    }

    get itemId() {
        return this.itemMeta.id;
    }

    get classes() {
        return cn(
            "odx-select__item",
            {
                "odx-select__item--highlighted": this.isHighlighted,
                "odx-select__item--selected": this.isSelected,
                "odx-select__item--disabled": this.props.disabled,
            },
            this.props.className
        );
    }

    get isHighlighted() {
        return this.env.odxSelect.isHighlighted(this.props.value);
    }

    get isSelected() {
        return this.env.odxSelect.isSelected(this.props.value);
    }

    onMouseenter() {
        this.env.odxSelect.setHighlighted(this.props.value);
    }

    onClick() {
        if (!this.props.disabled) {
            this.env.odxSelect.selectItem(this.itemMeta);
        }
    }
}

export class SelectItemText extends Component {
    static template = "odx_owl.SelectItemText";
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
        return cn("odx-select__item-label", this.props.className);
    }
}

export class SelectItemDescription extends Component {
    static template = "odx_owl.SelectItemDescription";
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
        return cn("odx-select__item-description", this.props.className);
    }
}

export class SelectItemIndicator extends Component {
    static template = "odx_owl.SelectItemIndicator";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "span",
    };

    get classes() {
        return cn("odx-select__indicator", this.props.className);
    }
}

SelectItem.components = {
    SelectItemDescription,
    SelectItemIndicator,
    SelectItemText,
};

export class Select extends Component {
    static template = "odx_owl.Select";
    static components = {
        Popover,
        SelectContent,
        SelectGroup,
        SelectItem,
        SelectItems,
        SelectLabel,
        SelectScrollDownButton,
        SelectScrollUpButton,
        SelectSeparator,
        SelectTrigger,
        SelectValue,
        SelectViewport,
    };
    static props = {
        align: { type: String, optional: true },
        attrs: { type: Object, optional: true },
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        contentClassName: { type: String, optional: true },
        defaultOpen: { type: Boolean, optional: true },
        defaultValue: { optional: true, validate: () => true },
        disabled: { type: Boolean, optional: true },
        dir: { type: String, optional: true },
        emptyLabel: { type: String, optional: true },
        items: { type: Array, optional: true },
        name: { type: String, optional: true },
        onOpenChange: { type: Function, optional: true },
        onValueChange: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        placeholder: { type: String, optional: true },
        position: { type: String, optional: true },
        side: { type: String, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        contentClassName: "",
        defaultOpen: false,
        disabled: false,
        emptyLabel: "No options found.",
        items: [],
        placeholder: "Select an option",
        size: "default",
    };

    setup() {
        const self = this;
        this.pendingRender = false;
        this.typeaheadQuery = "";
        this.typeaheadTimer = null;
        this.state = useState({
            canScrollDown: false,
            canScrollUp: false,
            highlightedValue: null,
            listId: nextId("odx-select-list"),
            open: this.props.open ?? this.props.defaultOpen,
            registeredItems: [],
            registryOrder: 0,
            value: this.props.value ?? this.props.defaultValue ?? null,
            version: 0,
        });
        this.viewportEl = null;
        this.syncHighlight();

        useChildSubEnv({
            odxSelect: {
                get activeItemId() {
                    return self.activeItemId;
                },
                get ariaLabel() {
                    return self.props.ariaLabel;
                },
                get canScrollDown() {
                    return self.state.canScrollDown;
                },
                get canScrollUp() {
                    return self.state.canScrollUp;
                },
                get disabled() {
                    return self.props.disabled;
                },
                get dir() {
                    return self.direction;
                },
                get groupedItems() {
                    return self.groupedItems;
                },
                get emptyLabel() {
                    return self.props.emptyLabel;
                },
                get isOpen() {
                    return self.isOpen;
                },
                get listId() {
                    return self.state.listId;
                },
                get placeholder() {
                    return self.props.placeholder;
                },
                get selectedItem() {
                    return self.selectedItem;
                },
                state: self.state,
                get triggerAttrs() {
                    return self.props.attrs;
                },
                getTriggerClasses: (className = "") => self.getTriggerClasses(className),
                getItemClasses: (item) => self.getItemClasses(item),
                getItemId: (item) => self.getItemId(item),
                getSelectedLabel: () => self.selectedItem?.label || null,
                isHighlighted: (value) => isSameCollectionValue(value, self.state.highlightedValue),
                isSelected: (value) => isSameCollectionValue(value, self.currentValue),
                onListKeydown: (ev) => self.onListKeydown(ev),
                onTriggerKeydown: (ev) => self.onTriggerKeydown(ev),
                registerItem: (token, item) => self.registerItem(token, item),
                registerViewport: (el) => self.registerViewport(el),
                scrollViewport: (direction) => self.scrollViewport(direction),
                selectItem: (item) => self.selectItem(item),
                setHighlighted: (value) => self.setHighlighted(value),
                setOpen: (open) => self.setOpen(open),
                syncViewportState: () => self.syncViewportState(),
                toggleOpen: () => self.toggleOpen(),
                unregisterItem: (token) => self.unregisterItem(token),
                unregisterViewport: (el) => self.unregisterViewport(el),
            },
        });

        useEffect(
            (isOpen, listId) => {
                if (!isOpen) {
                    return;
                }
                browser.requestAnimationFrame(() => {
                    document.getElementById(listId)?.focus();
                    this.syncViewportState();
                    this.scrollHighlightedIntoView();
                });
            },
            () => [this.isOpen, this.state.listId]
        );

        onWillUpdateProps((nextProps) => {
            let didChange = false;
            if (nextProps.open !== undefined) {
                this.state.open = nextProps.open;
                didChange = true;
            }
            if (nextProps.value !== undefined) {
                this.state.value = nextProps.value;
                didChange = true;
            }
            const nextItems = nextProps.items?.length
                ? normalizeCollectionItems(nextProps.items)
                : this.registeredItems;
            this.state.highlightedValue = resolveHighlightValue(
                nextItems,
                this.state.highlightedValue,
                nextProps.value ?? this.state.value
            );
            didChange = true;
            if (didChange) {
                this.bumpVersion();
            }
        });

        onWillDestroy(() => {
            this.clearTypeahead();
        });

        onMounted(() => {
            if (this.pendingRender) {
                this.pendingRender = false;
                this.render(true);
            }
        });
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get registeredItems() {
        return sortRegisteredItems(this.state.registeredItems);
    }

    get collectionItems() {
        return this.props.items.length
            ? normalizeCollectionItems(this.props.items)
            : this.registeredItems;
    }

    get groupedItems() {
        return groupCollectionItems(this.collectionItems);
    }

    get selectableItems() {
        return this.collectionItems.filter((item) => !item.disabled);
    }

    get currentValue() {
        return this.props.value ?? this.state.value;
    }

    get isOpen() {
        return this.props.open ?? this.state.open;
    }

    get selectedItem() {
        return findCollectionItemByValue(this.collectionItems, this.currentValue);
    }

    get triggerClasses() {
        return this.getTriggerClasses(this.props.className);
    }

    get panelClasses() {
        return cn("odx-select__panel", this.props.contentClassName);
    }

    get hasCustomTrigger() {
        return Boolean(this.props.slots?.default);
    }

    get hasCustomContent() {
        return Boolean(this.props.slots?.content);
    }

    getTriggerClasses(className = "") {
        return cn(
            "odx-select__trigger",
            `odx-select__trigger--${this.props.size}`,
            className
        );
    }

    registerViewport(el) {
        this.viewportEl = el;
        browser.requestAnimationFrame(() => {
            this.syncViewportState();
            this.scrollHighlightedIntoView();
        });
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
        this.syncHighlight(this.state.highlightedValue);
        this.bumpVersion();
    }

    unregisterItem(token) {
        const existingIndex = this.state.registeredItems.findIndex((entry) => entry.token === token);
        if (existingIndex !== -1) {
            this.state.registeredItems.splice(existingIndex, 1);
        }
        this.syncHighlight(this.state.highlightedValue);
        this.bumpVersion();
    }

    unregisterViewport(el) {
        if (this.viewportEl === el) {
            this.viewportEl = null;
        }
        this.syncViewportState();
    }

    syncHighlight(preferredValue) {
        this.state.highlightedValue = resolveHighlightValue(
            this.selectableItems,
            preferredValue,
            this.currentValue
        );
    }

    syncViewportState() {
        const viewport = this.viewportEl;
        if (!viewport) {
            this.state.canScrollUp = false;
            this.state.canScrollDown = false;
            return;
        }
        this.state.canScrollUp = viewport.scrollTop > 0;
        this.state.canScrollDown =
            viewport.scrollTop + viewport.clientHeight < viewport.scrollHeight - 1;
        this.bumpVersion();
    }

    scrollViewport(direction) {
        const viewport = this.viewportEl;
        if (!viewport) {
            return;
        }
        const delta = Math.max(viewport.clientHeight * 0.6, 40);
        viewport.scrollBy({
            top: direction === "up" ? -delta : delta,
            behavior: "smooth",
        });
        browser.requestAnimationFrame(() => this.syncViewportState());
    }

    scrollHighlightedIntoView() {
        const viewport = this.viewportEl;
        if (!viewport || !this.activeItemId) {
            return;
        }
        const item = document.getElementById(this.activeItemId);
        if (!item) {
            return;
        }
        item.scrollIntoView({ block: "nearest" });
        this.syncViewportState();
    }

    clearTypeahead() {
        if (this.typeaheadTimer) {
            browser.clearTimeout(this.typeaheadTimer);
            this.typeaheadTimer = null;
        }
        this.typeaheadQuery = "";
    }

    bumpVersion() {
        this.state.version += 1;
        if (status(this) === "mounted") {
            this.render(true);
        } else {
            this.pendingRender = true;
        }
    }

    queueTypeaheadReset() {
        if (this.typeaheadTimer) {
            browser.clearTimeout(this.typeaheadTimer);
        }
        this.typeaheadTimer = browser.setTimeout(() => {
            this.typeaheadTimer = null;
            this.typeaheadQuery = "";
        }, TYPEAHEAD_RESET_DELAY);
    }

    handleTypeahead(key, currentValue, { select = false } = {}) {
        if (!this.selectableItems.length) {
            return false;
        }
        const query = buildTypeaheadQuery(this.typeaheadQuery, key);
        const match = findTypeaheadMatch(this.selectableItems, query, currentValue);
        this.typeaheadQuery = query;
        this.queueTypeaheadReset();
        if (!match) {
            return false;
        }
        if (select) {
            this.selectItem(match);
        } else {
            this.state.highlightedValue = match.value;
            this.bumpVersion();
            browser.requestAnimationFrame(() => this.scrollHighlightedIntoView());
        }
        return true;
    }

    setOpen(open) {
        if (this.props.open === undefined) {
            this.state.open = open;
        }
        if (open) {
            this.syncHighlight();
            browser.requestAnimationFrame(() => {
                this.syncViewportState();
                this.scrollHighlightedIntoView();
            });
        } else {
            this.clearTypeahead();
            this.state.canScrollUp = false;
            this.state.canScrollDown = false;
        }
        this.bumpVersion();
        this.props.onOpenChange?.(open);
    }

    toggleOpen() {
        if (!this.props.disabled) {
            this.setOpen(!this.isOpen);
        }
    }

    onTriggerKeydown(ev) {
        if (this.props.disabled) {
            return;
        }
        if (isTypeaheadKey(ev)) {
            if (this.handleTypeahead(ev.key, this.currentValue, { select: true })) {
                ev.preventDefault();
            }
            return;
        }
        if (["ArrowDown", "ArrowUp"].includes(ev.key)) {
            ev.preventDefault();
            this.setOpen(true);
        }
    }

    onListKeydown(ev) {
        if (!this.selectableItems.length) {
            if (ev.key === "Escape") {
                ev.preventDefault();
                this.setOpen(false);
            }
            return;
        }
        if (isTypeaheadKey(ev)) {
            if (this.handleTypeahead(ev.key, this.state.highlightedValue)) {
                ev.preventDefault();
            }
            return;
        }
        if (!["ArrowDown", "ArrowUp", "Home", "End", "Enter", " ", "Escape"].includes(ev.key)) {
            return;
        }
        ev.preventDefault();
        if (ev.key === "Escape") {
            this.setOpen(false);
            return;
        }
        if (ev.key === "Home") {
            this.state.highlightedValue = this.selectableItems[0].value;
            this.scrollHighlightedIntoView();
            return;
        }
        if (ev.key === "End") {
            this.state.highlightedValue = this.selectableItems[this.selectableItems.length - 1].value;
            this.scrollHighlightedIntoView();
            return;
        }
        if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
            const currentIndex = this.selectableItems.findIndex((item) =>
                isSameCollectionValue(item.value, this.state.highlightedValue)
            );
            const safeIndex = currentIndex === -1 ? 0 : currentIndex;
            const direction = ev.key === "ArrowDown" ? 1 : -1;
            const nextIndex =
                (safeIndex + direction + this.selectableItems.length) % this.selectableItems.length;
            this.state.highlightedValue = this.selectableItems[nextIndex].value;
            this.scrollHighlightedIntoView();
            return;
        }
        const activeItem = findCollectionItemByValue(
            this.selectableItems,
            this.state.highlightedValue
        );
        if (activeItem) {
            this.selectItem(activeItem);
        }
    }

    getItemId(item) {
        return item.id || `${this.state.listId}-${sanitizeIdFragment(item.value)}`;
    }

    get activeItemId() {
        const item = findCollectionItemByValue(this.selectableItems, this.state.highlightedValue);
        return item ? this.getItemId(item) : undefined;
    }

    setHighlighted(value) {
        this.state.highlightedValue = value;
        this.bumpVersion();
        browser.requestAnimationFrame(() => this.scrollHighlightedIntoView());
    }

    selectItem(item) {
        if (item.disabled) {
            return;
        }
        if (this.props.value === undefined) {
            this.state.value = item.value;
        }
        this.bumpVersion();
        this.props.onValueChange?.(item.value, item);
        this.setOpen(false);
    }

    getItemClasses(item) {
        return cn("odx-select__item", {
            "odx-select__item--highlighted": isSameCollectionValue(
                item.value,
                this.state.highlightedValue
            ),
            "odx-select__item--selected": isSameCollectionValue(item.value, this.currentValue),
            "odx-select__item--disabled": item.disabled,
        });
    }
}

SelectItems.components = {
    SelectGroup,
    SelectItemDescription,
    SelectItemIndicator,
    SelectItemText,
    SelectLabel,
};
