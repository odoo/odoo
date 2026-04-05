/** @odoo-module **/

import {
    Component,
    onMounted,
    onRendered,
    onWillDestroy,
    onWillUpdateProps,
    useChildSubEnv,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId, sanitizeIdFragment } from "@odx_owl/core/utils/ids";

function isSameValue(left, right) {
    if (left === right) {
        return true;
    }
    if (left === undefined || left === null || right === undefined || right === null) {
        return false;
    }
    return String(left) === String(right);
}

export class NavigationMenuList extends Component {
    static template = "odx_owl.NavigationMenuList";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-navigation-menu__list", this.props.className);
    }
}

export class NavigationMenuItem extends Component {
    static template = "odx_owl.NavigationMenuItem";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-navigation-menu__item", this.props.className);
    }
}

export class NavigationMenuTrigger extends Component {
    static template = "odx_owl.NavigationMenuTrigger";
    static props = {
        active: { type: Boolean, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        hasContent: { type: Boolean, optional: true },
        href: { type: String, optional: true },
        onSelected: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        active: false,
        className: "",
        disabled: false,
        hasContent: false,
        href: "",
        text: "",
    };

    get resolvedValue() {
        return this.props.value ?? this.props.text ?? "";
    }

    get isLink() {
        return !this.props.hasContent && Boolean(this.props.href);
    }

    get classes() {
        return this.env.odxNavigationMenu.getTriggerClasses(this.resolvedValue, this.props.className);
    }

    get triggerId() {
        return this.env.odxNavigationMenu.getTriggerId(this.resolvedValue);
    }

    get contentId() {
        return this.props.hasContent
            ? this.env.odxNavigationMenu.getContentId(this.resolvedValue)
            : undefined;
    }

    get isCurrent() {
        return this.env.odxNavigationMenu.isActive(this.resolvedValue);
    }

    onClick(ev) {
        this.env.odxNavigationMenu.onTriggerSelect(
            {
                disabled: this.props.disabled,
                hasContent: this.props.hasContent,
                href: this.props.href,
                onSelected: this.props.onSelected,
                value: this.resolvedValue,
            },
            ev
        );
    }

    onKeydown(ev) {
        this.env.odxNavigationMenu.onTriggerKeydown(
            {
                disabled: this.props.disabled,
                hasContent: this.props.hasContent,
                value: this.resolvedValue,
            },
            ev
        );
    }

    onMouseenter(ev) {
        this.env.odxNavigationMenu.onTriggerMouseenter(
            {
                disabled: this.props.disabled,
                hasContent: this.props.hasContent,
                value: this.resolvedValue,
            },
            ev
        );
    }
}

export class NavigationMenuIndicator extends Component {
    static template = "odx_owl.NavigationMenuIndicator";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-navigation-menu__indicator", this.props.className);
    }

    get isVisible() {
        return this.env.odxNavigationMenu.hasActiveContent;
    }

    get style() {
        return this.env.odxNavigationMenu.indicatorStyle;
    }
}

export class NavigationMenuViewport extends Component {
    static template = "odx_owl.NavigationMenuViewport";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-navigation-menu__viewport", this.props.className);
    }
}

export class NavigationMenuContent extends Component {
    static template = "odx_owl.NavigationMenuContent";
    static components = {
        NavigationMenuViewport,
    };
    static props = {
        className: { type: String, optional: true },
        disableViewport: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
        viewportClassName: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        disableViewport: false,
        viewportClassName: "",
    };

    setup() {
        onMounted(() => this.env.odxNavigationMenu.registerContent(this.props.value));
        onWillUpdateProps((nextProps) => {
            if (!isSameValue(nextProps.value, this.props.value)) {
                this.env.odxNavigationMenu.unregisterContent(this.props.value);
                this.env.odxNavigationMenu.registerContent(nextProps.value);
            }
        });
        onWillDestroy(() => this.env.odxNavigationMenu.unregisterContent(this.props.value));
    }

    get isVisible() {
        return this.env.odxNavigationMenu.isActive(this.props.value);
    }

    get classes() {
        return cn(this.env.odxNavigationMenu.contentClasses, this.props.className);
    }

    get contentId() {
        return this.env.odxNavigationMenu.getContentId(this.props.value);
    }

    onKeydown(ev) {
        this.env.odxNavigationMenu.onContentKeydown(ev);
    }
}

export class NavigationMenuLink extends Component {
    static template = "odx_owl.NavigationMenuLink";
    static props = {
        className: { type: String, optional: true },
        description: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        href: { type: String, optional: true },
        onSelected: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        title: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        description: "",
        disabled: false,
        href: "",
        title: "",
    };

    get classes() {
        return cn("odx-navigation-menu__link", this.props.className);
    }

    onClick(ev) {
        this.env.odxNavigationMenu.onContentItemSelected(
            {
                disabled: this.props.disabled,
                href: this.props.href,
                onSelected: this.props.onSelected,
            },
            ev
        );
    }
}

export class NavigationMenu extends Component {
    static template = "odx_owl.NavigationMenu";
    static components = {
        NavigationMenuContent,
        NavigationMenuIndicator,
        NavigationMenuItem,
        NavigationMenuLink,
        NavigationMenuList,
        NavigationMenuTrigger,
        NavigationMenuViewport,
    };
    static props = {
        className: { type: String, optional: true },
        contentClassName: { type: String, optional: true },
        defaultValue: { optional: true, validate: () => true },
        dir: { type: String, optional: true },
        items: { type: Array, optional: true },
        onValueChange: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
        viewport: { type: Boolean, optional: true },
    };
    static defaultProps = {
        className: "",
        contentClassName: "",
        items: [],
        viewport: true,
    };

    setup() {
        const self = this;
        this.rootRef = useRef("rootRef");
        this.state = useState({
            baseId: nextId("odx-navigation-menu"),
            closeTimer: null,
            contentValues: [],
            indicatorStyle: "",
            value: this.props.value ?? this.props.defaultValue ?? null,
        });

        useChildSubEnv({
            odxNavigationMenu: {
                clearCloseTimer: () => self.clearCloseTimer(),
                closeMenu: () => self.closeMenu(),
                get contentClasses() {
                    return self.contentClasses;
                },
                get dir() {
                    return self.direction;
                },
                get currentValue() {
                    return self.currentValue;
                },
                getContentId: (value) => self.getContentIdFromValue(value),
                get indicatorStyle() {
                    return self.state.indicatorStyle;
                },
                getTriggerClasses: (value, className = "") =>
                    self.getTriggerClassesByValue(value, className),
                getTriggerId: (value) => self.getTriggerIdFromValue(value),
                get viewport() {
                    return self.props.viewport;
                },
                get hasActiveContent() {
                    return self.hasActiveContent;
                },
                isActive: (value) => self.isActiveValue(value),
                onContentItemSelected: (item, ev) => self.onContentItemSelected(item, ev),
                onContentKeydown: (ev) => self.onContentKeydown(ev),
                onTriggerKeydown: (options, ev) => self.onTriggerKeydown(options, ev),
                onTriggerMouseenter: (options, ev) => self.onTriggerMouseenter(options, ev),
                onTriggerSelect: (options, ev) => self.onTriggerSelect(options, ev),
                registerContent: (value) => self.registerContent(value),
                scheduleClose: () => self.scheduleClose(),
                unregisterContent: (value) => self.unregisterContent(value),
            },
        });

        onMounted(() => this.refreshIndicator());
        onRendered(() => this.refreshIndicator());
        onWillDestroy(() => this.clearCloseTimer());

        useExternalListener(window, "resize", () => this.refreshIndicator());
        useExternalListener(window, "pointerdown", (ev) => this.onWindowPointerDown(ev));

        onWillUpdateProps((nextProps) => {
            if (nextProps.value !== undefined) {
                this.state.value = nextProps.value;
            }
        });
    }

    get usesLegacyItems() {
        return this.props.items.length && !(this.props.slots && this.props.slots.default);
    }

    get classes() {
        return cn(
            "odx-navigation-menu",
            {
                "odx-navigation-menu--viewport": this.props.viewport,
                "odx-navigation-menu--floating": !this.props.viewport,
            },
            this.props.className
        );
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get currentValue() {
        return this.props.value ?? this.state.value;
    }

    get activeItem() {
        return (
            this.props.items.find((item, index) =>
                isSameValue(this.getItemValue(item, index), this.currentValue)
            ) || null
        );
    }

    get activeIndex() {
        return this.props.items.findIndex((item, index) =>
            isSameValue(this.getItemValue(item, index), this.currentValue)
        );
    }

    get contentClasses() {
        return cn(
            "odx-navigation-menu__content",
            {
                "odx-navigation-menu__content--viewport": this.props.viewport,
                "odx-navigation-menu__content--floating": !this.props.viewport,
            },
            this.props.contentClassName
        );
    }

    get featuredItem() {
        return this.activeItem?.featured || null;
    }

    get contentItems() {
        return Array.isArray(this.activeItem?.items) ? this.activeItem.items : [];
    }

    get hasActiveContent() {
        if (this.usesLegacyItems) {
            return Boolean(this.activeItem && (this.featuredItem || this.contentItems.length));
        }
        return this.state.contentValues.some((value) => isSameValue(value, this.currentValue));
    }

    clearCloseTimer() {
        if (this.state.closeTimer) {
            browser.clearTimeout(this.state.closeTimer);
            this.state.closeTimer = null;
        }
    }

    registerContent(value) {
        if (this.state.contentValues.some((entry) => isSameValue(entry, value))) {
            return;
        }
        this.state.contentValues.push(value);
    }

    unregisterContent(value) {
        this.state.contentValues = this.state.contentValues.filter(
            (entry) => !isSameValue(entry, value)
        );
    }

    getContentColumns(item) {
        const columns = Number(item?.columns) || 2;
        return cn("odx-navigation-menu__grid", {
            "odx-navigation-menu__grid--1": columns <= 1,
            "odx-navigation-menu__grid--2": columns === 2,
            "odx-navigation-menu__grid--3": columns >= 3,
        });
    }

    getContentId(item, index) {
        return this.getContentIdFromValue(this.getItemValue(item, index));
    }

    getContentIdFromValue(value) {
        return `${this.state.baseId}-content-${sanitizeIdFragment(String(value ?? "item"))}`;
    }

    getItemValue(item, index) {
        return item.value || item.id || item.label || `item-${index}`;
    }

    getTriggerId(item, index) {
        return this.getTriggerIdFromValue(this.getItemValue(item, index));
    }

    getTriggerIdFromValue(value) {
        return `${this.state.baseId}-trigger-${sanitizeIdFragment(String(value ?? "item"))}`;
    }

    getTriggerClasses(item, index) {
        return this.getTriggerClassesByValue(this.getItemValue(item, index));
    }

    getTriggerClassesByValue(value, className = "") {
        return cn(
            "odx-navigation-menu__trigger",
            {
                "odx-navigation-menu__trigger--active": this.isActiveValue(value),
            },
            className
        );
    }

    getTriggerElements() {
        return this.rootRef.el
            ? [...this.rootRef.el.querySelectorAll("[data-nav-trigger='true']")]
            : [];
    }

    focusFirstContentItem() {
        const firstItem = this.rootRef.el?.querySelector(
            ".odx-navigation-menu__content [data-nav-content-item='true']:not([disabled]):not([aria-disabled='true'])"
        );
        firstItem?.focus();
    }

    focusRelativeTriggerElement(element, direction) {
        const triggers = this.getTriggerElements().filter(
            (entry) => !entry.disabled && entry.getAttribute("aria-disabled") !== "true"
        );
        if (!triggers.length) {
            return;
        }
        const currentIndex = Math.max(triggers.indexOf(element), 0);
        const nextIndex = (currentIndex + direction + triggers.length) % triggers.length;
        triggers[nextIndex]?.focus();
    }

    focusTriggerEdge(edge) {
        const triggers = this.getTriggerElements().filter(
            (element) => !element.disabled && element.getAttribute("aria-disabled") !== "true"
        );
        if (!triggers.length) {
            return;
        }
        const target = edge === "start" ? triggers[0] : triggers[triggers.length - 1];
        target?.focus();
    }

    getTriggerMovementStep(key) {
        const isRtl = isRtlDirection(this.direction);
        if (key === "ArrowLeft") {
            return isRtl ? 1 : -1;
        }
        if (key === "ArrowRight") {
            return isRtl ? -1 : 1;
        }
        return 0;
    }

    hasContent(item) {
        return Boolean(item && (item.featured || (Array.isArray(item.items) && item.items.length)));
    }

    hasRegisteredContent(value) {
        return this.state.contentValues.some((entry) => isSameValue(entry, value));
    }

    shouldPreventNavigation(item) {
        return !item.href || item.href === "#" || Boolean(item.onSelected);
    }

    isActiveValue(value) {
        return isSameValue(value, this.currentValue);
    }

    onContentItemSelected(item, ev) {
        if (item.disabled) {
            ev.preventDefault();
            return;
        }
        if (this.shouldPreventNavigation(item)) {
            ev.preventDefault();
        }
        item.onSelected?.(ev, item);
        this.closeMenu();
    }

    onDirectLinkSelected(item, ev) {
        if (item.disabled) {
            ev.preventDefault();
            return;
        }
        if (this.shouldPreventNavigation(item)) {
            ev.preventDefault();
        }
        item.onSelected?.(ev, item);
        this.closeMenu();
    }

    onTriggerKeydown(options, ev) {
        if (!["ArrowLeft", "ArrowRight", "Home", "End", "ArrowDown", "Enter", " "].includes(ev.key)) {
            return;
        }

        if (ev.key === "ArrowLeft") {
            ev.preventDefault();
            this.focusRelativeTriggerElement(
                ev.currentTarget,
                this.getTriggerMovementStep("ArrowLeft")
            );
            return;
        }
        if (ev.key === "ArrowRight") {
            ev.preventDefault();
            this.focusRelativeTriggerElement(
                ev.currentTarget,
                this.getTriggerMovementStep("ArrowRight")
            );
            return;
        }
        if (ev.key === "Home") {
            ev.preventDefault();
            this.focusTriggerEdge("start");
            return;
        }
        if (ev.key === "End") {
            ev.preventDefault();
            this.focusTriggerEdge("end");
            return;
        }
        if (!options.hasContent) {
            return;
        }

        ev.preventDefault();
        this.openValue(options.value, ev.currentTarget);
        browser.setTimeout(() => this.focusFirstContentItem(), 0);
    }

    onTriggerMouseenter(options, ev) {
        this.clearCloseTimer();
        if (options.disabled) {
            return;
        }
        if (options.hasContent) {
            this.openValue(options.value, ev.currentTarget);
        } else if (this.currentValue !== null) {
            this.closeMenu();
        }
    }

    onWindowPointerDown(ev) {
        if (this.currentValue && this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
            this.closeMenu();
        }
    }

    openValue(value, element = null) {
        this.setValue(value);
        this.updateIndicatorForElement(element);
    }

    closeMenu() {
        this.clearCloseTimer();
        this.setValue(null);
        this.state.indicatorStyle = "";
    }

    scheduleClose() {
        this.clearCloseTimer();
        this.state.closeTimer = browser.setTimeout(() => {
            this.closeMenu();
        }, 120);
    }

    setValue(value) {
        if (this.props.value === undefined) {
            this.state.value = value;
        }
        this.props.onValueChange?.(value);
    }

    updateIndicatorForElement(element) {
        const root = this.rootRef.el;
        if (!root || !element) {
            return;
        }
        const rootRect = root.getBoundingClientRect();
        const triggerRect = element.getBoundingClientRect();
        const left = triggerRect.left - rootRect.left + triggerRect.width / 2 - 6;
        this.state.indicatorStyle = `left: ${left}px;`;
    }

    refreshIndicator() {
        if (!this.currentValue || !this.rootRef.el) {
            return;
        }
        const activeTrigger = this.rootRef.el.querySelector(
            `[data-nav-value="${CSS.escape(String(this.currentValue))}"]`
        );
        if (activeTrigger) {
            this.updateIndicatorForElement(activeTrigger);
        }
    }

    toggleItem(item, index, ev) {
        this.onTriggerSelect(
            {
                disabled: item.disabled,
                hasContent: this.hasContent(item),
                href: item.href,
                onSelected: item.onSelected,
                value: this.getItemValue(item, index),
            },
            ev
        );
    }

    onTriggerSelect(options, ev) {
        if (options.disabled) {
            ev.preventDefault();
            return;
        }
        if (!options.hasContent) {
            this.onDirectLinkSelected(options, ev);
            return;
        }
        if (this.isActiveValue(options.value)) {
            this.closeMenu();
        } else {
            this.openValue(options.value, ev.currentTarget);
        }
    }

    onContentKeydown(ev) {
        if (ev.key !== "Escape") {
            return;
        }
        ev.preventDefault();
        const activeValue = this.currentValue;
        this.closeMenu();
        if (!activeValue || !this.rootRef.el) {
            return;
        }
        const trigger = this.rootRef.el.querySelector(
            `[data-nav-value="${CSS.escape(String(activeValue))}"]`
        );
        trigger?.focus();
    }
}
