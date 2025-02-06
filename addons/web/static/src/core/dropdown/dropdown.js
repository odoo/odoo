import {
    Component,
    onMounted,
    onRendered,
    onWillUpdateProps,
    reactive,
    status,
    useEffect,
    xml,
} from "@odoo/owl";
import { useDropdownGroup } from "@web/core/dropdown/_behaviours/dropdown_group_hook";
import { useDropdownNesting } from "@web/core/dropdown/_behaviours/dropdown_nesting";
import { DropdownPopover } from "@web/core/dropdown/_behaviours/dropdown_popover";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useNavigation } from "@web/core/navigation/navigation";
import { usePopover } from "@web/core/popover/popover_hook";
import { mergeClasses } from "@web/core/utils/classname";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { deepMerge } from "@web/core/utils/objects";
import { effect } from "@web/core/utils/reactive";

function getFirstElementOfNode(node) {
    if (!node) {
        return null;
    }
    if (node.el) {
        return node.el.nodeType === Node.ELEMENT_NODE ? node.el : null;
    }
    if (node.bdom || node.child) {
        return getFirstElementOfNode(node.bdom || node.child);
    }
    if (node.children) {
        for (const child of node.children) {
            const el = getFirstElementOfNode(child);
            if (el) {
                return el;
            }
        }
    }
    return null;
}

/**
 * The Dropdown component allows to define a menu that will
 * show itself when a target is toggled.
 *
 * Items are defined using DropdownItems. Dropdowns are
 * also allowed as items to be able to create nested
 * dropdown menus.
 */
export class Dropdown extends Component {
    static template = xml`<t t-slot="default"/>`;
    static components = {};
    static props = {
        arrow: { optional: true },
        menuClass: { optional: true },
        position: { type: String, optional: true },
        slots: {
            type: Object,
            shape: {
                default: { optional: true },
                content: { optional: true },
            },
        },

        items: {
            optional: true,
            type: Array,
            elements: {
                type: Object,
                shape: {
                    label: String,
                    onSelected: Function,
                    class: { optional: true },
                    "*": true,
                },
            },
        },

        menuRef: { type: Function, optional: true }, // to be used with useChildRef
        disabled: { type: Boolean, optional: true },
        holdOnHover: { type: Boolean, optional: true },

        beforeOpen: { type: Function, optional: true },
        onOpened: { type: Function, optional: true },
        onStateChanged: { type: Function, optional: true },

        /** Manual state handling, @see useDropdownState */
        state: {
            type: Object,
            shape: {
                isOpen: Boolean,
                close: Function,
                open: Function,
                "*": true,
            },
            optional: true,
        },
        manual: { type: Boolean, optional: true },

        /**
         * Override the internal navigation hook options
         * @type {import("@web/core/navigation/navigation").NavigationOptions}
         */
        navigationOptions: { type: Object, optional: true },
    };
    static defaultProps = {
        arrow: false,
        disabled: false,
        holdOnHover: false,
        menuClass: "",
        state: undefined,
        navigationOptions: {},
    };

    setup() {
        this.menuRef = this.props.menuRef || useChildRef();

        this.state = this.props.state || useDropdownState();
        this.nesting = useDropdownNesting(this.state);
        this.group = useDropdownGroup();
        this.navigation = useNavigation(this.menuRef, {
            focusInitialElementOnDisabled: () => !this.group.isInGroup,
            itemsSelector: ":scope .o-navigable, :scope .o-dropdown",
            // Using deepMerge allows to keep entries of both option.hotkeys
            ...deepMerge(this.nesting.navigationOptions, this.props.navigationOptions),
        });

        // Set up UI active element related behavior ---------------------------
        let activeEl;
        this.uiService = useService("ui");
        useEffect(
            () => {
                Promise.resolve().then(() => {
                    activeEl = this.uiService.activeElement;
                });
            },
            () => []
        );

        this.popover = usePopover(DropdownPopover, {
            animation: false,
            arrow: this.props.arrow,
            closeOnClickAway: (target) => {
                return this.popoverCloseOnClickAway(target, activeEl);
            },
            closeOnEscape: false, // Handled via navigation and prevents closing root of nested dropdown
            env: this.__owl__.childEnv,
            holdOnHover: this.props.holdOnHover,
            onClose: () => this.state.close(),
            onPositioned: (el, { direction }) => this.setTargetDirectionClass(direction),
            popoverClass: mergeClasses(
                "o-dropdown--menu dropdown-menu mx-0",
                { "o-dropdown--menu-submenu": this.hasParent },
                this.props.menuClass
            ),
            popoverRole: "menu",
            position: this.position,
            ref: this.menuRef,
            setActiveElement: false,
        });

        // As the popover is in another context we need to force
        // its re-rendering when the dropdown re-renders
        onRendered(() => (this.popoverRefresher ? this.popoverRefresher.token++ : null));

        onMounted(() => this.onStateChanged(this.state));
        effect((state) => this.onStateChanged(state), [this.state]);

        useEffect(
            (target) => this.setTargetElement(target),
            () => [this.target]
        );

        onWillUpdateProps(({ disabled }) => {
            if (disabled) {
                this.closePopover();
            }
        });
    }

    /** @type {string} */
    get position() {
        return this.props.position || (this.hasParent ? "right-start" : "bottom-start");
    }

    get hasParent() {
        return this.nesting.hasParent;
    }

    /** @type {HTMLElement|null} */
    get target() {
        const target = getFirstElementOfNode(this.__owl__.bdom);
        if (!target) {
            throw new Error(
                "Could not find a valid dropdown toggler, prefer a single html element and put any dynamic content inside of it."
            );
        }
        return target;
    }

    handleClick(event) {
        if (this.props.disabled) {
            return;
        }

        event.stopPropagation();
        if (this.state.isOpen && !this.hasParent) {
            this.state.close();
        } else {
            this.state.open();
        }
    }

    handleMouseEnter() {
        if (this.props.disabled) {
            return;
        }

        if (this.hasParent || this.group.isOpen) {
            this.target.focus();
            this.state.open();
        }
    }

    onStateChanged(state) {
        if (state.isOpen) {
            this.openPopover();
        } else {
            this.closePopover();
        }
    }

    popoverCloseOnClickAway(target, activeEl) {
        const rootNode = target.getRootNode();
        if (rootNode instanceof ShadowRoot) {
            target = rootNode.host;
        }
        return this.uiService.getActiveElementOf(target) === activeEl;
    }

    setTargetElement(target) {
        if (!target) {
            return;
        }

        target.ariaExpanded = false;
        target.classList.add("o-dropdown");

        if (this.hasParent) {
            target.classList.add("o-dropdown--has-parent");
        }

        const tagName = target.tagName.toLowerCase();
        if (!["input", "textarea", "table", "thead", "tbody", "tr", "th", "td"].includes(tagName)) {
            target.classList.add("dropdown-toggle");
            if (this.hasParent) {
                target.classList.add("o-dropdown-item", "o-navigable", "dropdown-item");

                if (!target.classList.contains("o-dropdown--no-caret")) {
                    target.classList.add("o-dropdown-caret");
                }
            }
        }

        this.defaultDirection = this.position.split("-")[0];
        this.setTargetDirectionClass(this.defaultDirection);

        if (!this.props.manual) {
            target.addEventListener("click", this.handleClick.bind(this));
            target.addEventListener("mouseenter", this.handleMouseEnter.bind(this));

            return () => {
                target.removeEventListener("click", this.handleClick.bind(this));
                target.removeEventListener("mouseenter", this.handleMouseEnter.bind(this));
            };
        }
    }

    setTargetDirectionClass(direction) {
        if (!this.target) {
            return;
        }
        const directionClasses = {
            bottom: "dropdown",
            top: "dropup",
            left: "dropstart",
            right: "dropend",
        };
        this.target.classList.remove(...Object.values(directionClasses));
        this.target.classList.add(directionClasses[direction]);
    }

    openPopover() {
        if (this.popover.isOpen || status(this) !== "mounted") {
            return;
        }
        if (!this.target || !this.target.isConnected) {
            this.state.close();
            return;
        }

        this.popoverRefresher = reactive({ token: 0 });
        const props = {
            beforeOpen: () => this.props.beforeOpen?.(),
            onOpened: () => this.onOpened(),
            onClosed: () => this.onClosed(),
            refresher: this.popoverRefresher,
            items: this.props.items,
            slots: this.props.slots,
        };
        this.popover.open(this.target, props);
    }

    closePopover() {
        this.popover.close();
        this.navigation.disable();
    }

    onOpened() {
        this.navigation.enable();
        this.props.onOpened?.();
        this.props.onStateChanged?.(true);

        if (this.target) {
            this.target.ariaExpanded = true;
            this.target.classList.add("show");
        }
    }

    onClosed() {
        this.props.onStateChanged?.(false);

        if (this.target) {
            this.target.ariaExpanded = false;
            this.target.classList.remove("show");
            this.setTargetDirectionClass(this.defaultDirection);
        }
    }
}
