/** @odoo-module **/

import { Component, onWillUpdateProps, useChildSubEnv, useRef, useState } from "@odoo/owl";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownGroup } from "@web/core/dropdown/dropdown_group";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId } from "@odx_owl/core/utils/ids";
import { resolveOverlayPosition } from "@odx_owl/core/utils/overlay_position";

const ClosingMode = {
    None: "none",
    ClosestParent: "closest",
    AllParents: "all",
};

function getItemClasses(props, options = {}) {
    return cn(
        "odx-menubar__item",
        {
            "odx-menubar__item--submenu": options.submenu,
            "odx-menubar__item--destructive": props.destructive,
            "odx-menubar__item--disabled": props.disabled,
            "odx-menubar__item--inset": props.inset,
        },
        props.className
    );
}

function getItemAttrs(props, extraAttrs = {}) {
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

class MenubarBase extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

class MenubarActionBase extends Component {
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
        return getItemClasses(this.props);
    }

    get itemAttrs() {
        return getItemAttrs(this.props);
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

export class MenubarMenu extends Component {
    static template = "odx_owl.MenubarMenu";
    static props = {
        align: { type: String, optional: true },
        contentClassName: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        position: { type: String, optional: true },
        side: { type: String, optional: true },
        slots: { type: Object, optional: true },
        triggerClassName: { type: String, optional: true },
    };
    static defaultProps = {
        contentClassName: "",
        disabled: false,
        label: "",
        position: "bottom-start",
        triggerClassName: "",
    };

    get menuClasses() {
        return cn("odx-menubar__content", this.props.contentClassName);
    }

    get resolvedPosition() {
        return resolveOverlayPosition({
            align: this.props.align,
            fallback: "bottom-start",
            position: this.props.position,
            side: this.props.side,
        });
    }
}

export class MenubarTrigger extends Component {
    static template = "odx_owl.MenubarTrigger";
    static props = {
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
        text: "",
    };

    get classes() {
        return this.env.odxMenubar.getTriggerClass(this.props.disabled, this.props.className);
    }

    onKeydown(ev) {
        this.env.odxMenubar.onTriggerKeydown(ev);
    }
}

export class MenubarContent extends MenubarBase {
    static template = "odx_owl.MenubarContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-menubar__surface";
}

export class MenubarGroup extends MenubarBase {
    static template = "odx_owl.MenubarGroup";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-menubar__group";
}

export class MenubarLabel extends Component {
    static template = "odx_owl.MenubarLabel";
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
        return cn("odx-menubar__label", { "odx-menubar__label--inset": this.props.inset }, this.props.className);
    }
}

export class MenubarSeparator extends MenubarBase {
    static template = "odx_owl.MenubarSeparator";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };
    baseClass = "odx-menubar__separator";
}

export class MenubarShortcut extends Component {
    static template = "odx_owl.MenubarShortcut";
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
        return cn("odx-menubar__shortcut", this.props.className);
    }
}

export class MenubarSubTrigger extends Component {
    static template = "odx_owl.MenubarSubTrigger";
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
        return getItemClasses(this.props, { submenu: true });
    }

    get submenuChevronPath() {
        return this.env.odxMenubar?.dir === "rtl"
            ? "M10 3.5L5.5 8L10 12.5"
            : "M6 3.5L10.5 8L6 12.5";
    }
}

export class MenubarSubContent extends MenubarBase {
    static template = "odx_owl.MenubarSubContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-menubar__surface odx-menubar__surface--submenu";
}

export class MenubarSub extends Component {
    static template = "odx_owl.MenubarSub";
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
        return cn("odx-menubar__content", "odx-menubar__content--submenu", this.props.contentClassName);
    }

    get resolvedPosition() {
        return resolveOverlayPosition({
            align: this.props.align,
            fallback: isRtlDirection(this.env.odxMenubar?.dir) ? "left-start" : "right-start",
            position: this.props.position,
            side: this.props.side,
        });
    }
}

MenubarMenu.components = {
    Dropdown,
    MenubarTrigger,
};

MenubarSub.components = {
    Dropdown,
    MenubarSubTrigger,
};

export class MenubarItem extends MenubarActionBase {
    static template = "odx_owl.MenubarItem";
    static components = {
        DropdownItem,
        MenubarShortcut,
    };
}

export class MenubarCheckboxItem extends MenubarActionBase {
    static template = "odx_owl.MenubarCheckboxItem";
    static components = {
        CheckboxItem,
        MenubarShortcut,
    };
    static props = {
        ...MenubarActionBase.props,
        checked: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...MenubarActionBase.defaultProps,
        checked: false,
    };
}

export class MenubarRadioGroup extends Component {
    static template = "odx_owl.MenubarRadioGroup";
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
            odxMenubarRadioGroup: {
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
        return cn("odx-menubar__group", "odx-menubar__radio-group", this.props.className);
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

export class MenubarRadioItem extends DropdownItem {
    static template = "odx_owl.MenubarRadioItem";
    static components = {
        MenubarShortcut,
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
        return getItemClasses(this.props);
    }

    get isChecked() {
        return this.env.odxMenubarRadioGroup
            ? this.env.odxMenubarRadioGroup.currentValue === this.props.value
            : this.props.checked;
    }

    get itemAttrs() {
        return getItemAttrs(this.props, {
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
        this.env.odxMenubarRadioGroup?.setValue(this.props.value);
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

class MenubarMenuItems extends Component {
    static template = "odx_owl.MenubarMenuItems";
    static components = {
        MenubarCheckboxItem,
        MenubarContent,
        MenubarItem,
        MenubarLabel,
        MenubarMenuItems,
        MenubarRadioItem,
        MenubarSeparator,
        MenubarSub,
    };
    static props = {
        items: { type: Array, optional: true },
    };
    static defaultProps = {
        items: [],
    };

    getItemKey(item, index) {
        return item.id || item.value || item.label || `menubar-item-${index}`;
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

export class Menubar extends Component {
    static template = "odx_owl.Menubar";
    static components = {
        DropdownGroup,
        MenubarMenu,
        MenubarMenuItems,
    };
    static props = {
        className: { type: String, optional: true },
        dir: { type: String, optional: true },
        menus: { type: Array, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        menus: [],
    };

    setup() {
        const self = this;
        this.rootRef = useRef("rootRef");
        this.state = useState({
            groupId: nextId("odx-menubar"),
        });

        useChildSubEnv({
            odxMenubar: {
                get dir() {
                    return self.direction;
                },
                getTriggerClass: (disabled = false, className = "") =>
                    cn("odx-menubar__trigger", { "odx-menubar__trigger--disabled": disabled }, className),
                onTriggerKeydown: (ev) => this.onDynamicTriggerKeydown(ev),
            },
        });
    }

    get classes() {
        return cn("odx-menubar", this.props.className);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    getMenuKey(menu, index) {
        return menu.id || menu.value || menu.label || `menubar-menu-${index}`;
    }

    get triggerButtons() {
        return this.rootRef.el
            ? [...this.rootRef.el.querySelectorAll(".odx-menubar__trigger")]
            : [];
    }

    focusTrigger(startIndex, direction) {
        const buttons = this.triggerButtons;
        if (!buttons.length) {
            return;
        }
        let currentIndex = startIndex;
        for (let step = 0; step < buttons.length; step++) {
            currentIndex = (currentIndex + direction + buttons.length) % buttons.length;
            if (!buttons[currentIndex].disabled) {
                buttons[currentIndex].focus();
                return;
            }
        }
    }

    focusEdgeTrigger(edge) {
        const buttons = this.triggerButtons;
        const orderedButtons = edge === "start" ? buttons : [...buttons].reverse();
        const target = orderedButtons.find((button) => !button.disabled);
        target?.focus();
    }

    onDynamicTriggerKeydown(ev) {
        const index = this.triggerButtons.indexOf(ev.currentTarget);
        if (index !== -1) {
            this.onTriggerKeydown(index, ev);
        }
    }

    onTriggerKeydown(index, ev) {
        if (!["ArrowLeft", "ArrowRight", "ArrowDown", "Enter", " ", "Home", "End"].includes(ev.key)) {
            return;
        }

        const isRtl = isRtlDirection(this.direction);

        if (ev.key === "ArrowLeft") {
            ev.preventDefault();
            this.focusTrigger(index, isRtl ? 1 : -1);
            return;
        }
        if (ev.key === "ArrowRight") {
            ev.preventDefault();
            this.focusTrigger(index, isRtl ? -1 : 1);
            return;
        }
        if (ev.key === "Home") {
            ev.preventDefault();
            this.focusEdgeTrigger("start");
            return;
        }
        if (ev.key === "End") {
            ev.preventDefault();
            this.focusEdgeTrigger("end");
            return;
        }

        ev.preventDefault();
        this.triggerButtons[index]?.click();
    }
}
