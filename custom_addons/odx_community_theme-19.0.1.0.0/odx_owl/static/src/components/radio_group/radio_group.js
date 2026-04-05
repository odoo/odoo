/** @odoo-module **/

import {
    Component,
    onMounted,
    status,
    onWillDestroy,
    onWillUpdateProps,
    useChildSubEnv,
    useState,
} from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { nextId, sanitizeIdFragment } from "@odx_owl/core/utils/ids";
import { isSameCollectionValue } from "@odx_owl/core/utils/collection";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";

function moveFocus(items, nextIndex, group) {
    const target = items[nextIndex];
    if (!target) {
        return;
    }
    target.focus();
    group.setValue(target.dataset.value);
}

function sortRegisteredItems(items = []) {
    return [...items].sort((left, right) => left.order - right.order);
}

export class RadioGroup extends Component {
    static template = "odx_owl.RadioGroup";
    static props = {
        attrs: { type: Object, optional: true },
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        defaultValue: { optional: true, validate: () => true },
        disabled: { type: Boolean, optional: true },
        dir: { type: String, optional: true },
        loop: { type: Boolean, optional: true },
        name: { type: String, optional: true },
        onValueChange: { type: Function, optional: true },
        orientation: { type: String, optional: true },
        required: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        disabled: false,
        loop: true,
        orientation: "vertical",
        required: false,
    };

    setup() {
        const self = this;
        this.pendingRender = false;
        this.state = useState({
            baseId: nextId("odx-radio-group"),
            registeredItems: [],
            registryOrder: 0,
            value: this.props.value ?? this.props.defaultValue ?? null,
            version: 0,
        });

        useChildSubEnv({
            odxRadioGroup: {
                get disabled() {
                    return self.props.disabled;
                },
                get dir() {
                    return self.direction;
                },
                get orientation() {
                    return self.props.orientation;
                },
                state: self.state,
                get value() {
                    return self.currentValue;
                },
                getTabIndex: (value) => self.getTabIndex(value),
                getItemId: (value) =>
                    `${self.state.baseId}-item-${sanitizeIdFragment(value)}`,
                isChecked: (value) => isSameCollectionValue(self.currentValue, value),
                registerItem: (token, item) => self.registerItem(token, item),
                setValue: (value) => self.setValue(value),
                unregisterItem: (token) => self.unregisterItem(token),
            },
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.value !== undefined) {
                this.state.value = nextProps.value;
                this.bumpVersion();
            }
        });

        onMounted(() => {
            if (this.pendingRender) {
                this.pendingRender = false;
                this.render(true);
            }
        });
    }

    get currentValue() {
        return this.props.value ?? this.state.value;
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

    get tabStopValue() {
        const selectedItem = this.enabledItems.find((item) =>
            isSameCollectionValue(item.value, this.currentValue)
        );
        return selectedItem?.value ?? this.enabledItems[0]?.value ?? null;
    }

    get classes() {
        return cn(
            "odx-radio-group",
            {
                "odx-radio-group--horizontal": this.props.orientation === "horizontal",
                "odx-radio-group--vertical": this.props.orientation !== "horizontal",
            },
            this.props.className
        );
    }

    registerItem(token, item) {
        const existingIndex = this.state.registeredItems.findIndex((entry) => entry.token === token);
        const existingItem =
            existingIndex === -1 ? null : this.state.registeredItems[existingIndex];
        const nextItem = {
            ...item,
            order:
                existingIndex === -1
                    ? this.state.registryOrder++
                    : this.state.registeredItems[existingIndex].order,
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
        this.bumpVersion();
    }

    unregisterItem(token) {
        const existingIndex = this.state.registeredItems.findIndex((entry) => entry.token === token);
        if (existingIndex !== -1) {
            this.state.registeredItems.splice(existingIndex, 1);
            this.bumpVersion();
        }
    }

    getTabIndex(value) {
        if (this.props.disabled) {
            return -1;
        }
        return isSameCollectionValue(value, this.tabStopValue) ? 0 : -1;
    }

    setValue(value) {
        if (this.props.disabled || value === undefined || value === null) {
            return;
        }
        if (this.props.value === undefined) {
            this.state.value = value;
        }
        this.bumpVersion();
        this.props.onValueChange?.(value);
    }

    bumpVersion() {
        this.state.version += 1;
        if (status(this) === "mounted") {
            this.render(true);
        } else {
            this.pendingRender = true;
        }
    }

    onKeydown(ev) {
        const horizontal = this.props.orientation === "horizontal";
        const keys = horizontal
            ? ["ArrowRight", "ArrowLeft", "Home", "End"]
            : ["ArrowDown", "ArrowUp", "Home", "End"];
        if (!keys.includes(ev.key)) {
            return;
        }

        const items = [...ev.currentTarget.querySelectorAll('[role="radio"]:not([disabled])')];
        if (!items.length) {
            return;
        }

        const activeElement = document.activeElement;
        let currentIndex = items.indexOf(activeElement);
        if (currentIndex === -1) {
            currentIndex = items.findIndex((item) => item.dataset.value === String(this.currentValue));
        }
        if (currentIndex === -1) {
            currentIndex = 0;
        }

        ev.preventDefault();
        if (ev.key === "Home") {
            moveFocus(items, 0, this);
            return;
        }
        if (ev.key === "End") {
            moveFocus(items, items.length - 1, this);
            return;
        }

        const isRtl = horizontal && isRtlDirection(this.direction);
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
        moveFocus(items, nextIndex, this);
    }
}

export class RadioGroupItem extends Component {
    static template = "odx_owl.RadioGroupItem";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        value: { validate: () => true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
    };

    setup() {
        this.token = nextId("odx-radio-item");

        onMounted(() => {
            this.register(this.props);
        });

        onWillUpdateProps((nextProps) => {
            this.register(nextProps);
        });

        onWillDestroy(() => {
            this.env.odxRadioGroup.unregisterItem(this.token);
        });
    }

    get isChecked() {
        this.env.odxRadioGroup.state.version;
        return this.env.odxRadioGroup.isChecked(this.props.value);
    }

    get isDisabled() {
        return this.props.disabled || this.env.odxRadioGroup.disabled;
    }

    get itemId() {
        return this.props.id || this.env.odxRadioGroup.getItemId(this.props.value);
    }

    get tabIndex() {
        this.env.odxRadioGroup.state.version;
        return this.isDisabled ? -1 : this.env.odxRadioGroup.getTabIndex(this.props.value);
    }

    get classes() {
        return cn(
            "odx-radio-group__item",
            {
                "odx-radio-group__item--checked": this.isChecked,
                "odx-radio-group__item--disabled": this.isDisabled,
            },
            this.props.className
        );
    }

    register(props = this.props) {
        this.env.odxRadioGroup.registerItem(this.token, {
            disabled: Boolean(props.disabled),
            id: props.id,
            value: props.value,
        });
    }

    select() {
        if (!this.isDisabled) {
            this.env.odxRadioGroup.setValue(this.props.value);
        }
    }
}
