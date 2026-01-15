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
import { utils } from "@web/core/ui/ui_service";
import { hasTouch } from "@web/core/browser/feature_detection";

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
        focusToggleOnClosed: { type: Boolean, optional: true },

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

        /** When true, do not add optional styling css classes on the target*/
        noClasses: { type: Boolean, optional: true },

        /**
         * Override the internal navigation hook options
         * @type {import("@web/core/navigation/navigation").NavigationOptions}
         */
        navigationOptions: { type: Object, optional: true },
        bottomSheet: { type: Boolean, optional: true },
    };
    static defaultProps = {
        disabled: false,
        holdOnHover: false,
        focusToggleOnClosed: true,
        menuClass: "",
        state: undefined,
        noClasses: false,
        navigationOptions: {},
        bottomSheet: true,
    };

    setup() {
        this.menuRef = this.props.menuRef || useChildRef();

        this.state = this.props.state || useDropdownState();
        this.nesting = useDropdownNesting(this.state);
        this.group = useDropdownGroup();

        this.navigation = useNavigation(this.menuRef, {
            shouldRegisterHotkeys: false,
            isNavigationAvailable: () => this.state.isOpen,
            getItems: () => {
                if (this.state.isOpen && this.menuRef.el) {
                    return this.menuRef.el.querySelectorAll(
                        ":scope .o-navigable, :scope .o-dropdown"
                    );
                } else {
                    return [];
                }
            },
            // Using deepMerge allows to keep entries of both option.hotkeys
            ...deepMerge(this.nesting.navigationOptions, this.props.navigationOptions),
        });

        this.uiService = useService("ui");

        const getPosition = () => this.position;
        const options = {
            animation: false,
            arrow: false,
            closeOnClickAway: (target) => this.popoverCloseOnClickAway(target),
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
            role: "menu",
            get position() {
                return getPosition();
            },
            ref: this.menuRef,
            setActiveElement: false,
        };
        if (this.isBottomSheet) {
            Object.assign(options, {
                useBottomSheet: true,
                class: mergeClasses("o-dropdown--menu dropdown-menu show", this.props.menuClass),
            });
        }
        this.popover = usePopover(DropdownPopover, options);

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

    get isBottomSheet() {
        return utils.isSmall() && hasTouch() && this.props.bottomSheet;
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

    popoverCloseOnClickAway(target) {
        const rootNode = target.getRootNode();
        if (rootNode instanceof ShadowRoot) {
            target = rootNode.host;
        }
        return this.uiService.getActiveElementOf(target) === this.activeEl;
    }

    setTargetElement(target) {
        if (!target) {
            return;
        }

        target.ariaExpanded = false;
        const optionalClasses = [];
        const requiredClasses = [];
        optionalClasses.push("o-dropdown");

        if (this.hasParent) {
            requiredClasses.push("o-dropdown--has-parent");
        }

        const tagName = target.tagName.toLowerCase();
        if (!["input", "textarea", "table", "thead", "tbody", "tr", "th", "td"].includes(tagName)) {
            optionalClasses.push("dropdown-toggle");
            if (this.hasParent) {
                optionalClasses.push("o-dropdown-item", "dropdown-item");
                requiredClasses.push("o-navigable");

                if (!target.classList.contains("o-dropdown--no-caret")) {
                    requiredClasses.push("o-dropdown-caret");
                }
            }
        }

        target.classList.add(...requiredClasses);
        if (!this.props.noClasses) {
            target.classList.add(...optionalClasses);
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
        if (!this.target || this.props.noClasses) {
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
        if (this.props.focusToggleOnClosed && !this.group.isInGroup) {
            this._focusedElBeforeOpen?.focus();
            this._focusedElBeforeOpen = undefined;
        }
    }

    onOpened() {
        this._focusedElBeforeOpen = document.activeElement;
        this.activeEl = this.uiService.activeElement;
        this.navigation.registerHotkeys();
        this.navigation.update();
        this.props.onOpened?.();
        this.props.onStateChanged?.(true);

        if (this.target) {
            this.target.ariaExpanded = true;
            this.target.classList.add("show");
        }

        this.observer = new MutationObserver(() => this.navigation.update());
        this.observer.observe(this.menuRef.el, {
            childList: true,
            subtree: true,
        });
    }

    onClosed() {
        this.navigation.unregisterHotkeys();
        this.navigation.update();
        this.props.onStateChanged?.(false);
        delete this.activeEl;

        if (this.target) {
            this.target.ariaExpanded = false;
            this.target.classList.remove("show");
            this.setTargetDirectionClass(this.defaultDirection);
        }

        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
    }
}
