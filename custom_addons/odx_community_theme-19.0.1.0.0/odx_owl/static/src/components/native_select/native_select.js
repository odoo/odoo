/** @odoo-module **/

import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

function normalizeNativeOptions(options = []) {
    const groups = new Map();
    for (const option of options) {
        const groupKey = option.group || "__default__";
        if (!groups.has(groupKey)) {
            groups.set(groupKey, {
                key: groupKey,
                label: option.group || "",
                options: [],
            });
        }
        groups.get(groupKey).options.push({
            disabled: Boolean(option.disabled),
            label: option.label ?? option.value,
            value: option.value,
        });
    }
    return [...groups.values()];
}

export class NativeSelect extends Component {
    static template = "odx_owl.NativeSelect";
    static props = {
        ariaLabel: { type: String, optional: true },
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
        containerClassName: { type: String, optional: true },
        defaultValue: { optional: true, validate: () => true },
        disabled: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        name: { type: String, optional: true },
        onChange: { type: Function, optional: true },
        options: { type: Array, optional: true },
        required: { type: Boolean, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        containerClassName: "",
        disabled: false,
        options: [],
        required: false,
        size: "default",
    };

    setup() {
        this.state = useState({
            value: this.props.value ?? this.props.defaultValue ?? "",
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.value !== undefined) {
                this.state.value = nextProps.value;
            }
        });
    }

    get containerClasses() {
        return cn("odx-native-select", this.props.containerClassName);
    }

    get currentValue() {
        return this.props.value ?? this.state.value;
    }

    get groupedOptions() {
        return normalizeNativeOptions(this.props.options);
    }

    get selectClasses() {
        return cn(
            "odx-native-select__select",
            `odx-native-select__select--${this.props.size}`,
            this.props.className
        );
    }

    onChange(ev) {
        const nextValue = ev.target.value;
        if (this.props.value === undefined) {
            this.state.value = nextValue;
        }
        this.props.onChange?.(nextValue, ev);
    }
}

export class NativeSelectOption extends Component {
    static template = "odx_owl.NativeSelectOption";
    static props = {
        disabled: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        selected: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        disabled: false,
        label: "",
        selected: false,
    };
}

export class NativeSelectOptGroup extends Component {
    static template = "odx_owl.NativeSelectOptGroup";
    static props = {
        disabled: { type: Boolean, optional: true },
        label: { type: String },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        disabled: false,
    };
}
