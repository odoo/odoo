/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillUpdateProps,
    useChildSubEnv,
    useExternalListener,
    useState,
} from "@odoo/owl";
import { Input } from "@odx_owl/components/input/input";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId } from "@odx_owl/core/utils/ids";
import { cva } from "@odx_owl/core/utils/variants";

const MOBILE_BREAKPOINT = 768;

function getStoredOpen(storageKey, fallbackValue) {
    if (!storageKey) {
        return fallbackValue;
    }
    const value = window.localStorage.getItem(storageKey);
    if (value === "true") {
        return true;
    }
    if (value === "false") {
        return false;
    }
    return fallbackValue;
}

function isMobileViewport() {
    return window.innerWidth < MOBILE_BREAKPOINT;
}

function resolveSidebarSide(side, dir) {
    if (side === "start") {
        return isRtlDirection(dir) ? "right" : "left";
    }
    if (side === "end") {
        return isRtlDirection(dir) ? "left" : "right";
    }
    return side || "left";
}

export const sidebarMenuButtonVariants = cva("odx-sidebar-menu-button", {
    variants: {
        size: {
            default: "odx-sidebar-menu-button--default",
            sm: "odx-sidebar-menu-button--sm",
            lg: "odx-sidebar-menu-button--lg",
        },
        variant: {
            default: "odx-sidebar-menu-button--default-variant",
            outline: "odx-sidebar-menu-button--outline",
        },
    },
    defaultVariants: {
        size: "default",
        variant: "default",
    },
});

export class SidebarProvider extends Component {
    static template = "odx_owl.SidebarProvider";
    static props = {
        className: { type: String, optional: true },
        collapsible: { type: String, optional: true },
        defaultOpen: { type: Boolean, optional: true },
        dir: { type: String, optional: true },
        onOpenChange: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        side: { type: String, optional: true },
        slots: { type: Object, optional: true },
        storageKey: { type: String, optional: true },
        tag: { type: String, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        collapsible: "icon",
        defaultOpen: true,
        side: "left",
        storageKey: "",
        tag: "div",
        variant: "sidebar",
    };

    setup() {
        const self = this;
        this.state = useState({
            baseId: nextId("odx-sidebar"),
            isMobile: isMobileViewport(),
            mobileOpen: false,
            open: getStoredOpen(
                this.props.storageKey,
                this.props.open ?? this.props.defaultOpen
            ),
        });

        useChildSubEnv({
            odxSidebar: {
                close: () => self.close(),
                get baseId() {
                    return self.state.baseId;
                },
                get collapsible() {
                    return self.currentCollapsible;
                },
                get dir() {
                    return self.direction;
                },
                get desktopOpen() {
                    return self.desktopOpen;
                },
                get isMobile() {
                    return self.state.isMobile;
                },
                get isOpen() {
                    return self.isOpen;
                },
                get side() {
                    return self.currentSide;
                },
                get state() {
                    return self.stateName;
                },
                get variant() {
                    return self.currentVariant;
                },
                setDesktopOpen: (open) => self.setDesktopOpen(open),
                setMobileOpen: (open) => self.setMobileOpen(open),
                toggle: () => self.toggle(),
            },
        });

        onMounted(() => this.updateViewportState());
        useExternalListener(window, "resize", () => this.updateViewportState());

        onWillUpdateProps((nextProps) => {
            if (nextProps.open !== undefined) {
                this.state.open = nextProps.open;
            }
        });
    }

    get classes() {
        return cn("odx-sidebar-provider", this.props.className);
    }

    get currentCollapsible() {
        return this.props.collapsible || "icon";
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get currentSide() {
        return resolveSidebarSide(this.props.side, this.direction);
    }

    get currentVariant() {
        return this.props.variant || "sidebar";
    }

    get desktopOpen() {
        if (this.currentCollapsible === "none") {
            return true;
        }
        return this.props.open ?? this.state.open;
    }

    get isOpen() {
        return this.state.isMobile ? this.state.mobileOpen : this.desktopOpen;
    }

    get stateName() {
        return this.isOpen ? "expanded" : "collapsed";
    }

    close() {
        if (this.state.isMobile) {
            this.setMobileOpen(false);
            return;
        }
        this.setDesktopOpen(false);
    }

    persistDesktopOpen(open) {
        if (!this.props.storageKey) {
            return;
        }
        window.localStorage.setItem(this.props.storageKey, String(open));
    }

    setDesktopOpen(open) {
        if (this.currentCollapsible === "none") {
            return;
        }
        if (this.props.open === undefined) {
            this.state.open = open;
            this.persistDesktopOpen(open);
        }
        this.props.onOpenChange?.(open);
    }

    setMobileOpen(open) {
        this.state.mobileOpen = open;
    }

    toggle() {
        if (this.state.isMobile) {
            this.setMobileOpen(!this.state.mobileOpen);
            return;
        }
        this.setDesktopOpen(!this.desktopOpen);
    }

    updateViewportState() {
        const mobile = isMobileViewport();
        if (mobile === this.state.isMobile) {
            return;
        }
        this.state.isMobile = mobile;
        if (!mobile) {
            this.state.mobileOpen = false;
        }
    }
}

export class Sidebar extends Component {
    static template = "odx_owl.Sidebar";
    static props = {
        className: { type: String, optional: true },
        collapsible: { type: String, optional: true },
        dir: { type: String, optional: true },
        side: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "aside",
    };

    get classes() {
        return cn(
            "odx-sidebar",
            {
                "odx-sidebar--mobile": this.isMobile,
                "odx-sidebar--desktop": !this.isMobile,
            },
            this.props.className
        );
    }

    get isMobile() {
        return this.env.odxSidebar.isMobile;
    }

    get isOpen() {
        return this.env.odxSidebar.isOpen;
    }

    get direction() {
        return resolveDirection(this.props.dir || this.env.odxSidebar.dir);
    }

    get resolvedCollapsible() {
        return this.props.collapsible || this.env.odxSidebar.collapsible;
    }

    get resolvedSide() {
        return resolveSidebarSide(this.props.side || this.env.odxSidebar.side, this.direction);
    }

    get resolvedVariant() {
        return this.props.variant || this.env.odxSidebar.variant;
    }

    closeSidebar() {
        this.env.odxSidebar.close();
    }
}

class SidebarSection extends Component {
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
        return cn(this.baseClass, this.props.className);
    }
}

export class SidebarInset extends SidebarSection {
    static template = "odx_owl.SidebarInset";
    baseClass = "odx-sidebar-inset";
}

export class SidebarHeader extends SidebarSection {
    static template = "odx_owl.SidebarHeader";
    baseClass = "odx-sidebar-header";
}

export class SidebarFooter extends SidebarSection {
    static template = "odx_owl.SidebarFooter";
    baseClass = "odx-sidebar-footer";
}

export class SidebarContent extends SidebarSection {
    static template = "odx_owl.SidebarContent";
    baseClass = "odx-sidebar-content";
}

export class SidebarGroup extends SidebarSection {
    static template = "odx_owl.SidebarGroup";
    baseClass = "odx-sidebar-group";
}

export class SidebarGroupContent extends SidebarSection {
    static template = "odx_owl.SidebarGroupContent";
    baseClass = "odx-sidebar-group-content";
}

export class SidebarMenu extends SidebarSection {
    static template = "odx_owl.SidebarMenu";
    baseClass = "odx-sidebar-menu";
    static defaultProps = {
        className: "",
        tag: "ul",
    };
}

export class SidebarMenuItem extends SidebarSection {
    static template = "odx_owl.SidebarMenuItem";
    baseClass = "odx-sidebar-menu-item";
    static defaultProps = {
        className: "",
        tag: "li",
    };
}

export class SidebarMenuSub extends SidebarSection {
    static template = "odx_owl.SidebarMenuSub";
    baseClass = "odx-sidebar-menu-sub";
    static defaultProps = {
        className: "",
        tag: "ul",
    };
}

export class SidebarMenuSubItem extends SidebarSection {
    static template = "odx_owl.SidebarMenuSubItem";
    baseClass = "odx-sidebar-menu-sub-item";
    static defaultProps = {
        className: "",
        tag: "li",
    };
}

export class SidebarSeparator extends Component {
    static template = "odx_owl.SidebarSeparator";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-sidebar-separator", this.props.className);
    }
}

export class SidebarTrigger extends Component {
    static template = "odx_owl.SidebarTrigger";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        slots: { type: Object, optional: true },
        title: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Toggle sidebar",
        className: "",
        disabled: false,
        label: "",
        title: "",
    };

    get classes() {
        return cn("odx-sidebar-trigger", this.props.className);
    }

    get isDisabled() {
        return this.props.disabled || this.env.odxSidebar.collapsible === "none";
    }

    onClick(ev) {
        if (this.isDisabled) {
            ev.preventDefault();
            return;
        }
        this.env.odxSidebar.toggle();
    }
}

export class SidebarRail extends Component {
    static template = "odx_owl.SidebarRail";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Toggle sidebar rail",
        className: "",
        disabled: false,
    };

    get classes() {
        return cn("odx-sidebar-rail", this.props.className);
    }

    get isDisabled() {
        return this.props.disabled || this.env.odxSidebar.collapsible === "none";
    }

    onClick(ev) {
        if (this.isDisabled) {
            ev.preventDefault();
            return;
        }
        this.env.odxSidebar.toggle();
    }
}

export class SidebarInput extends Component {
    static template = "odx_owl.SidebarInput";
    static components = {
        Input,
    };
    static props = Input.props;
    static defaultProps = {
        ...Input.defaultProps,
    };

    get classes() {
        return cn("odx-sidebar-input", this.props.className);
    }
}

export class SidebarGroupLabel extends Component {
    static template = "odx_owl.SidebarGroupLabel";
    static props = {
        className: { type: String, optional: true },
        label: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        label: "",
        tag: "div",
    };

    get classes() {
        return cn("odx-sidebar-group-label", this.props.className);
    }
}

export class SidebarGroupAction extends Component {
    static template = "odx_owl.SidebarGroupAction";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        type: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "",
        className: "",
        disabled: false,
        label: "",
        type: "button",
    };

    get classes() {
        return cn("odx-sidebar-group-action", this.props.className);
    }

    onClick(ev) {
        if (this.props.disabled) {
            ev.preventDefault();
            return;
        }
        this.props.onClick?.(ev);
    }
}

export class SidebarMenuButton extends Component {
    static template = "odx_owl.SidebarMenuButton";
    static props = {
        ariaLabel: { type: String, optional: true },
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        href: { type: String, optional: true },
        isActive: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        rel: { type: String, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        target: { type: String, optional: true },
        title: { type: String, optional: true },
        tooltip: { type: String, optional: true },
        type: { type: String, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        disabled: false,
        isActive: false,
        label: "",
        size: "default",
        tag: "button",
        title: "",
        tooltip: "",
        type: "button",
        variant: "default",
    };

    get classes() {
        return cn(
            sidebarMenuButtonVariants({
                size: this.props.size,
                variant: this.props.variant,
            }),
            {
                "odx-sidebar-menu-button--active": this.props.isActive,
            },
            this.props.className
        );
    }

    get computedTag() {
        if (this.props.tag !== "button") {
            return this.props.tag;
        }
        return this.props.href ? "a" : "button";
    }

    get isIconCollapsed() {
        return (
            !this.env.odxSidebar.isMobile &&
            this.env.odxSidebar.collapsible === "icon" &&
            !this.env.odxSidebar.desktopOpen
        );
    }

    get resolvedTitle() {
        return this.props.title || (this.isIconCollapsed ? this.props.tooltip || this.props.label : "");
    }

    onClick(ev) {
        if (this.props.disabled) {
            ev.preventDefault();
            ev.stopPropagation();
            return;
        }
        this.props.onClick?.(ev);
    }
}

export class SidebarMenuAction extends Component {
    static template = "odx_owl.SidebarMenuAction";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        type: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "",
        className: "",
        disabled: false,
        label: "",
        type: "button",
    };

    get classes() {
        return cn("odx-sidebar-menu-action", this.props.className);
    }

    onClick(ev) {
        if (this.props.disabled) {
            ev.preventDefault();
            return;
        }
        this.props.onClick?.(ev);
    }
}

export class SidebarMenuBadge extends Component {
    static template = "odx_owl.SidebarMenuBadge";
    static props = {
        className: { type: String, optional: true },
        label: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        label: "",
    };

    get classes() {
        return cn("odx-sidebar-menu-badge", this.props.className);
    }
}

export class SidebarMenuSubButton extends Component {
    static template = "odx_owl.SidebarMenuSubButton";
    static props = {
        ariaLabel: { type: String, optional: true },
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        href: { type: String, optional: true },
        isActive: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        rel: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        target: { type: String, optional: true },
        title: { type: String, optional: true },
        type: { type: String, optional: true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        disabled: false,
        isActive: false,
        label: "",
        tag: "button",
        title: "",
        type: "button",
    };

    get classes() {
        return cn(
            "odx-sidebar-menu-sub-button",
            {
                "odx-sidebar-menu-sub-button--active": this.props.isActive,
            },
            this.props.className
        );
    }

    get computedTag() {
        if (this.props.tag !== "button") {
            return this.props.tag;
        }
        return this.props.href ? "a" : "button";
    }

    onClick(ev) {
        if (this.props.disabled) {
            ev.preventDefault();
            ev.stopPropagation();
            return;
        }
        this.props.onClick?.(ev);
    }
}
