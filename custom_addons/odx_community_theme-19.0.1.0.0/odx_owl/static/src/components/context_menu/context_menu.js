/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillDestroy,
    onWillUpdateProps,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { usePopover } from "@web/core/popover/popover_hook";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { resolveOverlayPosition } from "@odx_owl/core/utils/overlay_position";

function getItemClasses(props, options = {}) {
    return cn(
        "odx-context-menu__item",
        "o-navigable",
        {
            "odx-context-menu__item--submenu": options.submenu,
            "odx-context-menu__item--destructive": props.destructive,
            "odx-context-menu__item--disabled": props.disabled,
            "odx-context-menu__item--inset": props.inset,
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
    attrs["data-context-item"] = "true";
    return attrs;
}

class ContextMenuBase extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

class ContextMenuActionBase extends Component {
    static props = {
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
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

    get tag() {
        return this.itemAttrs.href ? "a" : "button";
    }

    closeRoot() {
        this.env.odxContextMenu?.closeRoot?.();
    }

    onClick(ev) {
        if (this.itemAttrs.href) {
            ev.preventDefault();
        }
        if (this.props.disabled) {
            ev.preventDefault();
            return;
        }
        this.props.onSelect?.(ev);
        if (!this.props.keepOpen) {
            this.closeRoot();
        }
    }
}

export class ContextMenuTrigger extends Component {
    static template = "odx_owl.ContextMenuTrigger";
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

    get classes() {
        return cn("odx-context-menu__trigger-content", this.props.className);
    }
}

export class ContextMenuContent extends ContextMenuBase {
    static template = "odx_owl.ContextMenuContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-context-menu__panel";
}

export class ContextMenuGroup extends ContextMenuBase {
    static template = "odx_owl.ContextMenuGroup";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-context-menu__group";
}

export class ContextMenuLabel extends Component {
    static template = "odx_owl.ContextMenuLabel";
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
        return cn("odx-context-menu__label", { "odx-context-menu__label--inset": this.props.inset }, this.props.className);
    }
}

export class ContextMenuSeparator extends ContextMenuBase {
    static template = "odx_owl.ContextMenuSeparator";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };
    baseClass = "odx-context-menu__separator";
}

export class ContextMenuShortcut extends Component {
    static template = "odx_owl.ContextMenuShortcut";
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
        return cn("odx-context-menu__shortcut", this.props.className);
    }
}

export class ContextMenuSubTrigger extends Component {
    static template = "odx_owl.ContextMenuSubTrigger";
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
        return this.env.odxContextMenu?.dir === "rtl"
            ? "M10 3.5L5.5 8L10 12.5"
            : "M6 3.5L10.5 8L6 12.5";
    }
}

export class ContextMenuSubContent extends ContextMenuBase {
    static template = "odx_owl.ContextMenuSubContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-context-menu__panel odx-context-menu__panel--submenu";
}

export class ContextMenuSub extends Component {
    static template = "odx_owl.ContextMenuSub";
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
            "odx-context-menu__content",
            "odx-context-menu__content--submenu",
            this.props.contentClassName
        );
    }

    get resolvedPosition() {
        return resolveOverlayPosition({
            align: this.props.align,
            fallback: isRtlDirection(this.env.odxContextMenu?.dir) ? "left-start" : "right-start",
            position: this.props.position,
            side: this.props.side,
        });
    }
}

ContextMenuSub.components = {
    Dropdown,
    ContextMenuSubTrigger,
};

export class ContextMenuItem extends ContextMenuActionBase {
    static template = "odx_owl.ContextMenuItem";
    static components = {
        ContextMenuShortcut,
    };
}

export class ContextMenuCheckboxItem extends ContextMenuActionBase {
    static template = "odx_owl.ContextMenuCheckboxItem";
    static components = {
        ContextMenuShortcut,
    };
    static props = {
        ...ContextMenuActionBase.props,
        checked: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...ContextMenuActionBase.defaultProps,
        checked: false,
    };
}

export class ContextMenuRadioGroup extends Component {
    static template = "odx_owl.ContextMenuRadioGroup";
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
            odxContextMenuRadioGroup: {
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
        return cn("odx-context-menu__group", "odx-context-menu__radio-group", this.props.className);
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

export class ContextMenuRadioItem extends ContextMenuActionBase {
    static template = "odx_owl.ContextMenuRadioItem";
    static components = {
        ContextMenuShortcut,
    };
    static props = {
        ...ContextMenuActionBase.props,
        checked: { type: Boolean, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        ...ContextMenuActionBase.defaultProps,
        checked: false,
    };

    get isChecked() {
        return this.env.odxContextMenuRadioGroup
            ? this.env.odxContextMenuRadioGroup.currentValue === this.props.value
            : this.props.checked;
    }

    get itemAttrs() {
        return getItemAttrs(this.props, {
            "aria-checked": this.isChecked ? "true" : "false",
        });
    }

    onClick(ev) {
        if (this.itemAttrs.href) {
            ev.preventDefault();
        }
        if (this.props.disabled) {
            ev.preventDefault();
            return;
        }
        this.env.odxContextMenuRadioGroup?.setValue(this.props.value);
        this.props.onSelect?.(ev, this.props.value);
        if (!this.props.keepOpen) {
            this.closeRoot();
        }
    }
}

class ContextMenuItems extends Component {
    static template = "odx_owl.ContextMenuItems";
    static components = {
        ContextMenuCheckboxItem,
        ContextMenuContent,
        ContextMenuItem,
        ContextMenuLabel,
        ContextMenuRadioItem,
        ContextMenuSeparator,
        ContextMenuSub,
    };
    static props = {
        items: { type: Array, optional: true },
    };
    static defaultProps = {
        items: [],
    };

    getItemKey(item, index) {
        return item.id || item.value || item.label || `context-menu-item-${index}`;
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
        if (!item.keepOpen) {
            this.env.odxContextMenu?.closeRoot?.();
        }
    }
}

ContextMenuItems.components = {
    ...ContextMenuItems.components,
    ContextMenuItems,
};

class OdxContextMenuPanel extends Component {
    static template = "odx_owl.ContextMenuPanel";
    static components = {
        ContextMenuItems,
    };
    static props = {
        className: { type: String, optional: true },
        close: { type: Function, optional: true },
        dir: { type: String, optional: true },
        items: { type: Array, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        items: [],
    };

    setup() {
        const self = this;
        this.menuRef = useRef("menuRef");

        useChildSubEnv({
            odxContextMenu: {
                closeRoot: () => this.props.close?.(),
                get dir() {
                    return self.direction;
                },
            },
        });

        onMounted(() => this.focusFirstItem());
    }

    get menuClasses() {
        return cn("odx-context-menu__viewport", this.props.className);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    getFocusableItems() {
        return this.menuRef.el
            ? [...this.menuRef.el.querySelectorAll("[data-context-item='true']")]
                .filter((item) => !item.disabled && item.getAttribute("aria-disabled") !== "true")
            : [];
    }

    focusFirstItem() {
        this.getFocusableItems()[0]?.focus();
    }

    focusRelativeItem(direction) {
        const items = this.getFocusableItems();
        if (!items.length) {
            return;
        }
        const currentIndex = Math.max(items.indexOf(document.activeElement), 0);
        const nextIndex = (currentIndex + direction + items.length) % items.length;
        items[nextIndex].focus();
    }

    onKeydown(ev) {
        const openSubmenuKey = this.direction === "rtl" ? "ArrowLeft" : "ArrowRight";
        if (!["ArrowDown", "ArrowUp", "Home", "End", openSubmenuKey].includes(ev.key)) {
            return;
        }
        if (ev.key === openSubmenuKey) {
            const activeElement = document.activeElement;
            if (activeElement?.dataset?.contextSubtrigger === "true") {
                ev.preventDefault();
                activeElement.click();
            }
            return;
        }

        ev.preventDefault();
        if (ev.key === "ArrowDown") {
            this.focusRelativeItem(1);
            return;
        }
        if (ev.key === "ArrowUp") {
            this.focusRelativeItem(-1);
            return;
        }
        const items = this.getFocusableItems();
        if (!items.length) {
            return;
        }
        if (ev.key === "Home") {
            items[0].focus();
        } else {
            items[items.length - 1].focus();
        }
    }
}

export class ContextMenu extends Component {
    static template = "odx_owl.ContextMenu";
    static props = {
        className: { type: String, optional: true },
        contentClassName: { type: String, optional: true },
        defaultOpen: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
        dir: { type: String, optional: true },
        items: { type: Array, optional: true },
        onOpenChange: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        contentClassName: "",
        defaultOpen: false,
        disabled: false,
        items: [],
    };

    setup() {
        this.anchorRef = useRef("anchorRef");
        this.triggerRef = useRef("triggerRef");
        this.state = useState({
            open: this.props.open ?? this.props.defaultOpen,
            x: 0,
            y: 0,
        });

        this.popover = usePopover(OdxContextMenuPanel, {
            animation: false,
            arrow: false,
            closeOnClickAway: true,
            closeOnEscape: true,
            onClose: () => this.setOpen(false),
            popoverClass: "odx-context-menu__surface",
            position: "bottom-start",
            setActiveElement: false,
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.open !== undefined) {
                this.state.open = nextProps.open;
            }
        });

        useEffect(
            (open, anchor) => {
                if (!open || !anchor || this.props.disabled) {
                    this.popover.close();
                    return;
                }
                this.openPanel(anchor);
                return () => this.popover.close();
            },
            () => [this.isOpen, this.anchorRef.el, this.state.x, this.state.y]
        );

        onWillDestroy(() => this.popover.close());
    }

    get anchorStyle() {
        return `left: ${this.state.x}px; top: ${this.state.y}px;`;
    }

    get classes() {
        return cn("odx-context-menu", this.props.className);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get isOpen() {
        return this.props.open ?? this.state.open;
    }

    setOpen(open) {
        if (this.props.open === undefined) {
            this.state.open = open;
        }
        this.props.onOpenChange?.(open);
    }

    openAt(x, y) {
        this.state.x = x;
        this.state.y = y;
        this.setOpen(true);
    }

    openPanel(target) {
        if (!target?.isConnected) {
            return;
        }
        this.popover.open(target, {
            className: cn("odx-context-menu__content", this.props.contentClassName),
            close: () => this.setOpen(false),
            dir: this.direction,
            items: this.props.items,
            slots: this.props.slots,
        });
    }

    onContextMenu(ev) {
        if (this.props.disabled) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.openAt(ev.clientX, ev.clientY);
    }

    onTriggerKeydown(ev) {
        if (this.props.disabled) {
            return;
        }
        if (ev.key !== "ContextMenu" && !(ev.shiftKey && ev.key === "F10")) {
            return;
        }
        ev.preventDefault();
        const rect = this.triggerRef.el?.getBoundingClientRect();
        if (!rect) {
            return;
        }
        this.openAt(rect.left + 8, rect.top + 8);
    }
}
