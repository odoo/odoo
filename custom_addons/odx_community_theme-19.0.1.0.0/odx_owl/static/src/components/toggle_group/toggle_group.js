/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillDestroy,
    onWillUpdateProps,
    useChildSubEnv,
    useState,
} from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { isSameCollectionValue } from "@odx_owl/core/utils/collection";
import { nextId, sanitizeIdFragment } from "@odx_owl/core/utils/ids";
import { toggleVariants } from "@odx_owl/components/toggle/toggle";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";

function normalizeValues(value, type) {
    if (value === undefined || value === null || value === "") {
        return [];
    }
    if (Array.isArray(value)) {
        return value;
    }
    return type === "multiple" ? [value] : [value];
}

function sortRegisteredItems(items = []) {
    return [...items].sort((left, right) => left.order - right.order);
}

export class ToggleGroup extends Component {
    static template = "odx_owl.ToggleGroup";
    static props = {
        className: { type: String, optional: true },
        defaultValue: { optional: true, validate: () => true },
        disabled: { type: Boolean, optional: true },
        dir: { type: String, optional: true },
        loop: { type: Boolean, optional: true },
        onValueChange: { type: Function, optional: true },
        orientation: { type: String, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        spacing: { type: Number, optional: true },
        type: { type: String, optional: true },
        value: { optional: true, validate: () => true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
        loop: true,
        orientation: "horizontal",
        size: "default",
        spacing: 0,
        type: "single",
        variant: "default",
    };

    setup() {
        const self = this;
        this.state = useState({
            baseId: nextId("odx-toggle-group"),
            tabStopValue: null,
            registeredItems: [],
            registryOrder: 0,
            values: normalizeValues(this.props.value ?? this.props.defaultValue, this.props.type),
        });

        useChildSubEnv({
            odxToggleGroup: {
                get disabled() {
                    return self.props.disabled;
                },
                get dir() {
                    return self.direction;
                },
                get size() {
                    return self.props.size;
                },
                get spacing() {
                    return self.props.spacing;
                },
                get type() {
                    return self.props.type;
                },
                get values() {
                    return self.currentValues;
                },
                get variant() {
                    return self.props.variant;
                },
                getTabIndex: (value) => self.getTabIndex(value),
                getItemId: (value) =>
                    `${self.state.baseId}-item-${sanitizeIdFragment(value)}`,
                isPressed: (value) =>
                    self.currentValues.some((item) => isSameCollectionValue(item, value)),
                registerItem: (token, item) => self.registerItem(token, item),
                setTabStop: (value) => self.setTabStop(value),
                toggleValue: (value) => self.toggleValue(value),
                unregisterItem: (token) => self.unregisterItem(token),
            },
        });

        onMounted(() => {
            this.syncTabStop(true);
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.value !== undefined) {
                this.state.values = normalizeValues(nextProps.value, nextProps.type ?? this.props.type);
            }
            this.syncTabStop(nextProps.value !== undefined);
        });
    }

    get currentValues() {
        return normalizeValues(this.props.value ?? this.state.values, this.props.type);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get registeredItems() {
        return sortRegisteredItems(this.state.registeredItems);
    }

    get enabledItems() {
        return this.registeredItems.filter((item) => !item.disabled);
    }

    get defaultTabStopValue() {
        const pressedItem = this.enabledItems.find((item) =>
            this.currentValues.some((value) => isSameCollectionValue(value, item.value))
        );
        return pressedItem?.value ?? this.enabledItems[0]?.value ?? null;
    }

    get classes() {
        return cn(
            "odx-toggle-group",
            {
                "odx-toggle-group--vertical": this.props.orientation === "vertical",
                "odx-toggle-group--horizontal": this.props.orientation !== "vertical",
                "odx-toggle-group--spaced": this.props.spacing > 0,
            },
            this.props.className
        );
    }

    get style() {
        return `--odx-toggle-group-gap: ${this.props.spacing}px;`;
    }

    registerItem(token, item) {
        const existingIndex = this.state.registeredItems.findIndex((entry) => entry.token === token);
        const existingItem = existingIndex === -1 ? null : this.state.registeredItems[existingIndex];
        const nextItem = {
            ...item,
            order:
                existingIndex === -1
                    ? this.state.registryOrder++
                    : existingItem.order,
            token,
        };
        if (
            existingItem &&
            existingItem.disabled === nextItem.disabled &&
            existingItem.id === nextItem.id &&
            isSameCollectionValue(existingItem.value, nextItem.value)
        ) {
            return;
        }
        if (existingIndex === -1) {
            this.state.registeredItems.push(nextItem);
        } else {
            this.state.registeredItems.splice(existingIndex, 1, nextItem);
        }
        this.syncTabStop();
    }

    unregisterItem(token) {
        const existingIndex = this.state.registeredItems.findIndex((entry) => entry.token === token);
        if (existingIndex !== -1) {
            this.state.registeredItems.splice(existingIndex, 1);
        }
        this.syncTabStop();
    }

    syncTabStop(preferSelection = false) {
        const enabledItems = this.enabledItems;
        if (!enabledItems.length) {
            this.state.tabStopValue = null;
            return;
        }
        const currentTabStop = enabledItems.find((item) =>
            isSameCollectionValue(item.value, this.state.tabStopValue)
        );
        if (currentTabStop && !preferSelection) {
            return;
        }
        this.state.tabStopValue = this.defaultTabStopValue;
    }

    setTabStop(value) {
        if (this.enabledItems.some((item) => isSameCollectionValue(item.value, value))) {
            this.state.tabStopValue = value;
        }
    }

    getTabIndex(value) {
        if (this.props.disabled) {
            return -1;
        }
        return isSameCollectionValue(value, this.state.tabStopValue ?? this.defaultTabStopValue)
            ? 0
            : -1;
    }

    toggleValue(value) {
        if (this.props.disabled) {
            return;
        }
        const current = this.currentValues;
        const exists = current.some((item) => isSameCollectionValue(item, value));
        let nextValues;
        if (this.props.type === "multiple") {
            nextValues = exists
                ? current.filter((item) => !isSameCollectionValue(item, value))
                : [...current, value];
        } else {
            nextValues = exists ? [] : [value];
        }
        if (this.props.value === undefined) {
            this.state.values = nextValues;
        }
        this.setTabStop(value);
        this.props.onValueChange?.(
            this.props.type === "multiple" ? nextValues : nextValues[0] ?? null
        );
    }

    onKeydown(ev) {
        const vertical = this.props.orientation === "vertical";
        const validKeys = vertical
            ? ["ArrowDown", "ArrowUp", "Home", "End"]
            : ["ArrowRight", "ArrowLeft", "Home", "End"];
        if (!validKeys.includes(ev.key)) {
            return;
        }
        const items = [...ev.currentTarget.querySelectorAll('[data-odx-toggle-group-item]:not([disabled])')];
        if (!items.length) {
            return;
        }
        let currentIndex = items.indexOf(document.activeElement);
        if (currentIndex === -1) {
            currentIndex = items.findIndex((item) =>
                isSameCollectionValue(item.dataset.value, this.state.tabStopValue)
            );
        }
        if (currentIndex === -1) {
            currentIndex = 0;
        }
        ev.preventDefault();
        if (ev.key === "Home") {
            items[0].focus();
            return;
        }
        if (ev.key === "End") {
            items[items.length - 1].focus();
            return;
        }
        const isRtl = !vertical && isRtlDirection(this.direction);
        const direction =
            ev.key === "ArrowDown"
                ? 1
                : ev.key === "ArrowUp"
                  ? -1
                  : ev.key === "ArrowRight"
                    ? isRtl
                        ? -1
                        : 1
                    : isRtl
                      ? 1
                      : -1;
        let nextIndex = currentIndex + direction;
        if (this.props.loop) {
            nextIndex = (nextIndex + items.length) % items.length;
        } else {
            nextIndex = Math.max(0, Math.min(items.length - 1, nextIndex));
        }
        items[nextIndex].focus();
    }
}

export class ToggleGroupItem extends Component {
    static template = "odx_owl.ToggleGroupItem";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        value: { validate: () => true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
    };

    setup() {
        this.token = nextId("odx-toggle-group-item");

        onMounted(() => {
            this.register(this.props);
        });

        onWillUpdateProps((nextProps) => {
            this.register(nextProps);
        });

        onWillDestroy(() => {
            this.env.odxToggleGroup.unregisterItem(this.token);
        });
    }

    get isPressed() {
        return this.env.odxToggleGroup.isPressed(this.props.value);
    }

    get isDisabled() {
        return this.props.disabled || this.env.odxToggleGroup.disabled;
    }

    get classes() {
        return toggleVariants({
            variant: this.props.variant ?? this.env.odxToggleGroup.variant,
            size: this.props.size ?? this.env.odxToggleGroup.size,
            className: cn(
                "odx-toggle-group__item",
                {
                    "odx-toggle-group__item--pressed": this.isPressed,
                    "odx-toggle-group__item--joined": !this.env.odxToggleGroup.spacing,
                },
                this.props.className
            ),
        });
    }

    get itemId() {
        return this.props.id || this.env.odxToggleGroup.getItemId(this.props.value);
    }

    get tabIndex() {
        return this.isDisabled ? -1 : this.env.odxToggleGroup.getTabIndex(this.props.value);
    }

    toggle(ev) {
        if (this.isDisabled) {
            ev.preventDefault();
            return;
        }
        this.env.odxToggleGroup.toggleValue(this.props.value);
    }

    register(props = this.props) {
        this.env.odxToggleGroup.registerItem(this.token, {
            disabled: Boolean(props.disabled),
            id: props.id,
            value: props.value,
        });
    }

    onFocus() {
        if (!this.isDisabled) {
            this.env.odxToggleGroup.setTabStop(this.props.value);
        }
    }
}
