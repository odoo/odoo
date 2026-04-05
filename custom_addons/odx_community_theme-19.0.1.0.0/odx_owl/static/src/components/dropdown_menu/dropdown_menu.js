/** @odoo-module **/

import { Component, onWillUpdateProps, useChildSubEnv, useState } from "@odoo/owl";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { buttonVariants } from "@odx_owl/components/button/button";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { resolveOverlayPosition } from "@odx_owl/core/utils/overlay_position";

const ClosingMode = {
    None: "none",
    ClosestParent: "closest",
    AllParents: "all",
};

function getEntryClasses(props) {
    return cn(
        "odx-dropdown-menu__item",
        {
            "odx-dropdown-menu__item--disabled": props.disabled,
            "odx-dropdown-menu__item--destructive": props.destructive,
            "odx-dropdown-menu__item--inset": props.inset,
        },
        props.className
    );
}

function getEntryAttrs(props, extraAttrs = {}) {
    const attrs = {
        ...(props.attrs || {}),
        ...extraAttrs,
    };
    const href = props.href ?? props.attrs?.href;
    const rel = props.rel ?? props.attrs?.rel;
    const target = props.target ?? props.attrs?.target;

    if (href) {
        attrs.href = href;
    }
    if (rel) {
        attrs.rel = rel;
    }
    if (target) {
        attrs.target = target;
    }
    if (props.disabled) {
        attrs["aria-disabled"] = "true";
        attrs["data-disabled"] = "true";
    }
    return attrs;
}

class DropdownMenuEntry extends Component {
    static props = {
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
        closingMode: { type: String, optional: true },
        destructive: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
        href: { type: String, optional: true },
        inset: { type: Boolean, optional: true },
        keepOpen: { type: Boolean, optional: true },
        onSelect: { type: Function, optional: true },
        rel: { type: String, optional: true },
        shortcut: { type: String, optional: true },
        slots: { type: Object, optional: true },
        target: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        closingMode: ClosingMode.AllParents,
        destructive: false,
        disabled: false,
        href: undefined,
        inset: false,
        keepOpen: false,
        rel: undefined,
        shortcut: "",
        target: undefined,
        text: "",
    };

    get classes() {
        return getEntryClasses(this.props);
    }

    get itemAttrs() {
        return getEntryAttrs(this.props);
    }

    get resolvedClosingMode() {
        return this.props.keepOpen ? ClosingMode.None : this.props.closingMode;
    }

    onSelected(ev) {
        if (this.props.disabled) {
            ev.preventDefault();
            return;
        }
        this.props.onSelect?.(ev);
    }
}

class DropdownMenuBase extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

export class DropdownMenuTrigger extends Component {
    static template = "odx_owl.DropdownMenuTrigger";
    static props = {
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
        size: "default",
        tag: "button",
        text: "",
        variant: "outline",
    };

    get classes() {
        return buttonVariants({
            variant: this.props.variant,
            size: this.props.size,
            className: cn("odx-dropdown-menu__trigger", this.props.className),
        });
    }
}

export class DropdownMenuContent extends DropdownMenuBase {
    static template = "odx_owl.DropdownMenuContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-dropdown-menu__surface";
}

export class DropdownMenuGroup extends DropdownMenuBase {
    static template = "odx_owl.DropdownMenuGroup";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-dropdown-menu__group";
}

export class DropdownMenuLabel extends Component {
    static template = "odx_owl.DropdownMenuLabel";
    static props = {
        className: { type: String, optional: true },
        inset: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        inset: false,
        tag: "div",
        text: "",
    };

    get classes() {
        return cn("odx-dropdown-menu__label", { "odx-dropdown-menu__label--inset": this.props.inset }, this.props.className);
    }
}

export class DropdownMenuSeparator extends DropdownMenuBase {
    static template = "odx_owl.DropdownMenuSeparator";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };
    baseClass = "odx-dropdown-menu__separator";
}

export class DropdownMenuShortcut extends Component {
    static template = "odx_owl.DropdownMenuShortcut";
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
        return cn("odx-dropdown-menu__shortcut", this.props.className);
    }
}

export class DropdownMenuSubTrigger extends Component {
    static template = "odx_owl.DropdownMenuSubTrigger";
    static props = {
        className: { type: String, optional: true },
        destructive: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
        inset: { type: Boolean, optional: true },
        shortcut: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        destructive: false,
        disabled: false,
        inset: false,
        shortcut: "",
        text: "",
    };

    get classes() {
        return cn(
            "odx-dropdown-menu__item",
            "odx-dropdown-menu__item--submenu",
            "o-navigable",
            {
                "odx-dropdown-menu__item--disabled": this.props.disabled,
                "odx-dropdown-menu__item--destructive": this.props.destructive,
                "odx-dropdown-menu__item--inset": this.props.inset,
            },
            this.props.className
        );
    }

    get submenuChevronPath() {
        return this.env.odxDropdownMenu?.dir === "rtl"
            ? "M10 3.5L5.5 8L10 12.5"
            : "M6 3.5L10.5 8L6 12.5";
    }
}

export class DropdownMenuSubContent extends DropdownMenuBase {
    static template = "odx_owl.DropdownMenuSubContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-dropdown-menu__surface odx-dropdown-menu__surface--submenu";
}

export class DropdownMenuSub extends Component {
    static template = "odx_owl.DropdownMenuSub";
    static props = {
        align: { type: String, optional: true },
        contentClassName: { type: String, optional: true },
        destructive: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
        inset: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        position: { type: String, optional: true },
        side: { type: String, optional: true },
        shortcut: { type: String, optional: true },
        slots: { type: Object, optional: true },
        triggerClassName: { type: String, optional: true },
    };
    static defaultProps = {
        contentClassName: "",
        destructive: false,
        disabled: false,
        inset: false,
        label: "",
        position: "right-start",
        shortcut: "",
        triggerClassName: "",
    };

    get menuClasses() {
        return cn(
            "odx-dropdown-menu__content",
            "odx-dropdown-menu__content--submenu",
            this.props.contentClassName
        );
    }

    get resolvedPosition() {
        return resolveOverlayPosition({
            align: this.props.align,
            fallback: isRtlDirection(this.env.odxDropdownMenu?.dir) ? "left-start" : "right-start",
            position: this.props.position,
            side: this.props.side,
        });
    }
}

DropdownMenuSub.components = {
    Dropdown,
    DropdownMenuSubTrigger,
};

export class DropdownMenuItem extends DropdownMenuEntry {
    static template = "odx_owl.DropdownMenuItem";
    static components = {
        DropdownItem,
        DropdownMenuShortcut,
    };
}

export class DropdownMenuCheckboxItem extends DropdownMenuEntry {
    static template = "odx_owl.DropdownMenuCheckboxItem";
    static components = {
        CheckboxItem,
        DropdownMenuShortcut,
    };
    static props = {
        ...DropdownMenuEntry.props,
        checked: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...DropdownMenuEntry.defaultProps,
        checked: false,
    };
}

export class DropdownMenuRadioGroup extends Component {
    static template = "odx_owl.DropdownMenuRadioGroup";
    static props = {
        className: { type: String, optional: true },
        defaultValue: { optional: true, validate: () => true },
        onValueChange: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };

    setup() {
        const self = this;
        this.state = useState({
            value: this.props.value ?? this.props.defaultValue ?? null,
        });

        useChildSubEnv({
            odxDropdownMenuRadioGroup: {
                get currentValue() {
                    return self.currentValue;
                },
                setValue: (value) => self.setValue(value),
            },
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.value !== undefined) {
                this.state.value = nextProps.value;
            }
        });
    }

    get classes() {
        return cn("odx-dropdown-menu__group", "odx-dropdown-menu__radio-group", this.props.className);
    }

    get currentValue() {
        return this.props.value ?? this.state.value;
    }

    setValue(value) {
        if (value === undefined || value === null) {
            return;
        }
        if (this.props.value === undefined) {
            this.state.value = value;
        }
        this.props.onValueChange?.(value);
    }
}

export class DropdownMenuRadioItem extends DropdownItem {
    static template = "odx_owl.DropdownMenuRadioItem";
    static components = {
        DropdownMenuShortcut,
    };
    static props = {
        attrs: { type: Object, optional: true },
        checked: { type: Boolean, optional: true },
        className: { type: String, optional: true },
        closingMode: { type: String, optional: true },
        destructive: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
        href: { type: String, optional: true },
        inset: { type: Boolean, optional: true },
        keepOpen: { type: Boolean, optional: true },
        onSelect: { type: Function, optional: true },
        rel: { type: String, optional: true },
        shortcut: { type: String, optional: true },
        slots: { type: Object, optional: true },
        target: { type: String, optional: true },
        text: { type: String, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        attrs: {},
        checked: false,
        className: "",
        closingMode: ClosingMode.AllParents,
        destructive: false,
        disabled: false,
        href: undefined,
        inset: false,
        keepOpen: false,
        rel: undefined,
        shortcut: "",
        target: undefined,
        text: "",
    };

    get classes() {
        return getEntryClasses(this.props);
    }

    get isChecked() {
        return this.env.odxDropdownMenuRadioGroup
            ? this.env.odxDropdownMenuRadioGroup.currentValue === this.props.value
            : this.props.checked;
    }

    get itemAttrs() {
        return getEntryAttrs(this.props, {
            "aria-checked": this.isChecked ? "true" : "false",
        });
    }

    get resolvedClosingMode() {
        return this.props.keepOpen ? ClosingMode.None : this.props.closingMode;
    }

    onClick(ev) {
        if (this.itemAttrs.href) {
            ev.preventDefault();
        }
        if (this.props.disabled) {
            ev.preventDefault();
            return;
        }
        this.env.odxDropdownMenuRadioGroup?.setValue(this.props.value);
        this.props.onSelect?.(ev, this.props.value);
        switch (this.resolvedClosingMode) {
            case ClosingMode.ClosestParent:
                this.dropdownControl.close();
                break;
            case ClosingMode.AllParents:
                this.dropdownControl.closeAll();
                break;
        }
    }
}

class DropdownMenuItems extends Component {
    static template = "odx_owl.DropdownMenuItems";
    static components = {
        DropdownMenuCheckboxItem,
        DropdownMenuItem,
        DropdownMenuLabel,
        DropdownMenuRadioItem,
        DropdownMenuSeparator,
        DropdownMenuSub,
        DropdownMenuSubContent,
    };
    static props = {
        items: { type: Array, optional: true },
    };
    static defaultProps = {
        items: [],
    };

    getItemKey(item, index) {
        return item.id || item.value || item.label || `${item.type || "item"}-${index}`;
    }

    getSubmenuItems(item) {
        return Array.isArray(item.items) ? item.items : [];
    }

    onItemSelected(item, ev) {
        if (item.disabled) {
            ev.preventDefault();
            return;
        }
        item.onSelected?.(ev, item);
    }
}

DropdownMenuItems.components = {
    ...DropdownMenuItems.components,
    DropdownMenuItems,
};

export class DropdownMenu extends Component {
    static template = "odx_owl.DropdownMenu";
    static components = {
        Dropdown,
        DropdownMenuCheckboxItem,
        DropdownMenuContent,
        DropdownMenuItems,
        DropdownMenuItem,
        DropdownMenuLabel,
        DropdownMenuRadioItem,
        DropdownMenuSeparator,
        DropdownMenuSub,
        DropdownMenuSubContent,
        DropdownMenuSubTrigger,
        DropdownMenuTrigger,
    };
    static props = {
        align: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        dir: { type: String, optional: true },
        items: { type: Array, optional: true },
        label: { type: String, optional: true },
        position: { type: String, optional: true },
        side: { type: String, optional: true },
        slots: { type: Object, optional: true },
        triggerClassName: { type: String, optional: true },
        triggerSize: { type: String, optional: true },
        triggerVariant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
        items: [],
        label: "Open menu",
        position: "bottom-start",
        triggerClassName: "",
        triggerSize: "default",
        triggerVariant: "outline",
    };

    setup() {
        const self = this;
        useChildSubEnv({
            odxDropdownMenu: {
                get dir() {
                    return self.direction;
                },
            },
        });
    }

    get triggerClasses() {
        return buttonVariants({
            variant: this.props.triggerVariant,
            size: this.props.triggerSize,
            className: cn("odx-dropdown-menu__trigger", this.props.triggerClassName),
        });
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get menuClasses() {
        return cn("odx-dropdown-menu__content", this.props.className);
    }

    get resolvedPosition() {
        return resolveOverlayPosition({
            align: this.props.align,
            fallback: "bottom-start",
            position: this.props.position,
            side: this.props.side,
        });
    }

    getItemKey(item, index) {
        return item.id || item.value || item.label || `${item.type || "item"}-${index}`;
    }
}
