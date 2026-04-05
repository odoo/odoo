/** @odoo-module **/

import { Component, onWillUpdateProps, useChildSubEnv, useState } from "@odoo/owl";
import { Command } from "@odx_owl/components/command/command";
import { Popover } from "@odx_owl/components/popover/popover";
import { cn } from "@odx_owl/core/utils/cn";
import {
    findCollectionItemByValue,
    normalizeCollectionItems,
} from "@odx_owl/core/utils/collection";
import { resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId } from "@odx_owl/core/utils/ids";

export class ComboboxValue extends Component {
    static template = "odx_owl.ComboboxValue";
    static props = {
        className: { type: String, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        placeholder: "",
    };

    get classes() {
        return cn("odx-combobox__value", this.props.className);
    }

    get text() {
        return (
            this.env.odxCombobox.getSelectedLabel() ||
            this.props.placeholder ||
            this.env.odxCombobox.placeholder
        );
    }
}

export class ComboboxIcon extends Component {
    static template = "odx_owl.ComboboxIcon";
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
        return cn("odx-combobox__icon", this.props.className);
    }
}

export class ComboboxTrigger extends Component {
    static template = "odx_owl.ComboboxTrigger";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return this.env.odxCombobox.getTriggerClasses(this.props.className);
    }

    get selectedItem() {
        return this.env.odxCombobox.selectedItem;
    }

    onKeydown(ev) {
        this.env.odxCombobox.onTriggerKeydown(ev);
    }
}

ComboboxTrigger.components = {
    ComboboxIcon,
    ComboboxValue,
};

export class ComboboxContent extends Component {
    static template = "odx_owl.ComboboxContent";
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
        return cn("odx-combobox__panel", this.props.className);
    }
}

export class Combobox extends Component {
    static template = "odx_owl.Combobox";
    static components = {
        ComboboxContent,
        ComboboxIcon,
        ComboboxTrigger,
        ComboboxValue,
        Command,
        Popover,
    };
    static props = {
        align: { type: String, optional: true },
        ariaLabel: { type: String, optional: true },
        attrs: { type: Object, optional: true },
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
        searchPlaceholder: { type: String, optional: true },
        side: { type: String, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        contentClassName: "",
        defaultOpen: false,
        disabled: false,
        emptyLabel: "No results found.",
        items: [],
        placeholder: "Select a value",
        searchPlaceholder: "Search...",
    };

    setup() {
        const self = this;
        this.state = useState({
            listId: nextId("odx-combobox-list"),
            open: this.props.open ?? this.props.defaultOpen,
            value: this.props.value ?? this.props.defaultValue ?? null,
        });

        useChildSubEnv({
            odxCombobox: {
                get ariaLabel() {
                    return self.props.ariaLabel;
                },
                get disabled() {
                    return self.props.disabled;
                },
                get dir() {
                    return self.direction;
                },
                get emptyLabel() {
                    return self.props.emptyLabel;
                },
                get isOpen() {
                    return self.isOpen;
                },
                get listId() {
                    return self.listId;
                },
                get panelClasses() {
                    return self.panelClasses;
                },
                get placeholder() {
                    return self.props.placeholder;
                },
                get searchPlaceholder() {
                    return self.props.searchPlaceholder;
                },
                get selectedItem() {
                    return self.selectedItem;
                },
                get triggerAttrs() {
                    return self.props.attrs;
                },
                getTriggerClasses: (className = "") => self.getTriggerClasses(className),
                getSelectedLabel: () => self.selectedItem?.label || null,
                onTriggerKeydown: (ev) => self.onTriggerKeydown(ev),
                setOpen: (open) => self.setOpen(open),
                toggleOpen: () => self.toggleOpen(),
            },
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.open !== undefined) {
                this.state.open = nextProps.open;
            }
            if (nextProps.value !== undefined) {
                this.state.value = nextProps.value;
            }
        });
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get normalizedItems() {
        return normalizeCollectionItems(this.props.items);
    }

    get currentValue() {
        return this.props.value ?? this.state.value;
    }

    get isOpen() {
        return this.props.open ?? this.state.open;
    }

    get selectedItem() {
        return findCollectionItemByValue(this.normalizedItems, this.currentValue);
    }

    get listId() {
        return this.hasCustomContent ? undefined : this.state.listId;
    }

    get hasCustomTrigger() {
        return Boolean(this.props.slots?.default);
    }

    get hasCustomContent() {
        return Boolean(this.props.slots?.content);
    }

    get triggerClasses() {
        return this.getTriggerClasses(this.props.className);
    }

    getTriggerClasses(className = "") {
        return cn("odx-combobox__trigger", className);
    }

    get panelClasses() {
        return cn("odx-combobox__panel", this.props.contentClassName);
    }

    setOpen(open) {
        if (this.props.open === undefined) {
            this.state.open = open;
        }
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
        if (["ArrowDown", "ArrowUp"].includes(ev.key)) {
            ev.preventDefault();
            this.setOpen(true);
        }
    }

    onCommandSelect(value, item) {
        if (this.props.value === undefined) {
            this.state.value = value;
        }
        this.props.onValueChange?.(value, item);
        this.setOpen(false);
    }
}
