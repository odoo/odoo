import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Pager } from "@web/core/pager/pager";
import { useService } from "@web/core/utils/hooks";
import { SearchBar } from "../search_bar/search_bar";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useCommand } from "@web/core/commands/command_hook";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useSortable } from "@web/core/utils/sortable_owl";
import { user } from "@web/core/user";
import { AccordionItem } from "@web/core/dropdown/accordion_item";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { makeContext } from "@web/core/context";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import {
    Component,
    useState,
    onMounted,
    useExternalListener,
    useRef,
    useEffect,
    onWillStart,
} from "@odoo/owl";

const STICKY_CLASS = "o_mobile_sticky";
/**
 * @typedef TopBarAction
 * @property {number} id
 * @property {[number, string] | false} parent_action_id
 * @property {string} name
 * @property {number} sequence
 * @property {number} res_id
 * @property {string} res_model
 * @property {[number, string] | false} action_id
 * @property {string} python_action
 * @property {[number, string] | false} user_id
 * @property {boolean} is_deletable
 * @property {string} default_view_mode
 * @property {string} filter_ids
 * @property {string} domain
 * @property {string} context
 */

export class ControlPanel extends Component {
    static template = "web.ControlPanel";
    static components = {
        Pager,
        SearchBar,
        Dropdown,
        DropdownItem,
        AccordionItem,
        CheckBox,
    };
    static props = {
        display: { type: Object, optional: true },
        slots: { type: Object, optional: true },
    };

    setup() {
        this.actionService = useService("action");
        this.pagerProps = this.env.config.pagerProps
            ? useState(this.env.config.pagerProps)
            : undefined;
        this.notificationService = useService("notification");
        this.breadcrumbs = useState(this.env.config.breadcrumbs);
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.root = useRef("root");
        this.newActionNameRef = useRef("newActionNameRef");
        this.isTopBarActionsOrderModifiable = false;
        /**
         * The visible topbar actions are unique to each user and to each res_id. The visible actions chosen by the
         * user are stored in the local storage in a key corresponding to a combination of the actionId, the activeId
         * and the currrent userId. Each key contains a dict. The keys of the latter are the id of the visible topbar
         * actions.
         */
        this.localStorageKeyActionIdResId = `visibleTopBarActions${
            this.env.config.parentActionId || ""
        }+${this.env.searchModel?.globalContext.active_id || ""}+${user.userId}`;

        this.topBarLocalStorageKeyActionIdResId = `visibleTopBar${
            this.env.config.parentActionId || ""
        }+${this.env.searchModel?.globalContext.active_id || ""}+${user.userId}`;

        this.topBarOrderLocalStorageKeyActionIdResId = `orderTopBar${
            this.env.config.parentActionId || ""
        }+${this.env.searchModel?.globalContext.active_id || ""}+${user.userId}`;

        this.state = useState({
            showSearchBar: false,
            showMobileSearch: false,
            showViewSwitcher: false,
            topbarInfos: {
                showTopBar:
                    !!this.env.config.fromParentAction ||
                    !!JSON.parse(localStorage.getItem(this.topBarLocalStorageKeyActionIdResId)),
                topBarActions: this.env.config.topBarActions,
                newActionIsShared: false,
                newActionName: `Custom ${this.currentTopBarAction?.name || "Topbar Action"}`,
                visibleTopBarActions:
                    JSON.parse(localStorage.getItem(this.localStorageKeyActionIdResId)) || {},
                currentTopBarAction: this.currentTopBarAction,
            },
        });

        this.onScrollThrottledBound = this.onScrollThrottled.bind(this);

        const { viewSwitcherEntries, viewType } = this.env.config;
        for (const view of viewSwitcherEntries || []) {
            useCommand(_t("Show %s view", view.name), () => this.switchView(view.type), {
                category: "view_switcher",
                isAvailable: () => view.type !== viewType,
            });
        }

        if (viewSwitcherEntries?.length > 1) {
            useHotkey(
                "alt+shift+v",
                () => {
                    this.cycleThroughViews();
                },
                {
                    bypassEditableProtection: true,
                    withOverlay: () => this.root.el.querySelector("nav.o_cp_switch_buttons"),
                }
            );
        }

        onWillStart(async () => {
            // This is meant to be overriden
            this.isTopBarActionsOrderModifiable = await user.hasGroup("base.group_system");
            // If there is no visible topbar actions, the current action (if it exists) is put by default
            const localStorageKey = browser.localStorage.getItem(this.localStorageKeyActionIdResId);
            const topBarOrderLocalStorageKey = browser.localStorage.getItem(
                this.topBarOrderLocalStorageKeyActionIdResId
            );
            if (!localStorageKey || !Object.keys(JSON.parse(localStorageKey)).length) {
                const { currentTopBarAction, topBarActions } = this.state.topbarInfos;
                if (currentTopBarAction) {
                    this._setVisibility(currentTopBarAction);
                } else if (topBarActions?.[0]) {
                    this._setVisibility(topBarActions?.[0]);
                }
            }
            if (topBarOrderLocalStorageKey) {
                this._sortTopBarActions(JSON.parse(topBarOrderLocalStorageKey));
            }
        });

        useExternalListener(window, "click", this.onWindowClick);
        useEffect(() => {
            if (
                !this.env.isSmall ||
                ("adaptToScroll" in this.display && !this.display.adaptToScroll)
            ) {
                return;
            }
            const scrollingEl = this.getScrollingElement();
            scrollingEl.addEventListener("scroll", this.onScrollThrottledBound);
            this.root.el.style.top = "0px";
            return () => {
                scrollingEl.removeEventListener("scroll", this.onScrollThrottledBound);
            };
        });
        onMounted(() => {
            if (
                !this.env.isSmall ||
                ("adaptToScroll" in this.display && !this.display.adaptToScroll)
            ) {
                return;
            }
            this.oldScrollTop = 0;
            this.lastScrollTop = 0;
            this.initialScrollTop = this.getScrollingElement().scrollTop;
        });

        this.mainButtons = useRef("mainButtons");

        useEffect(() => {
            // on small screen, clean-up the dropdown elements
            const dropdownButtons = this.mainButtons.el.querySelectorAll(
                ".o_control_panel_collapsed_create.dropdown-menu button"
            );
            if (!dropdownButtons.length) {
                this.mainButtons.el
                    .querySelectorAll(
                        ".o_control_panel_collapsed_create.dropdown-menu, .o_control_panel_collapsed_create.dropdown-toggle"
                    )
                    .forEach((el) => el.classList.add("d-none"));
                this.mainButtons.el
                    .querySelectorAll(".o_control_panel_collapsed_create.btn-group")
                    .forEach((el) => el.classList.remove("btn-group"));
                return;
            }
            for (const button of dropdownButtons) {
                for (const cl of Array.from(button.classList)) {
                    button.classList.toggle(cl, !cl.startsWith("btn-"));
                }
                button.classList.add("dropdown-item", "btn", "btn-link");
            }
        });

        useSortable({
            enable: () => this.isTopBarActionsOrderModifiable,
            ref: this.root,
            elements: ".o_draggable",
            cursor: "move",
            delay: 200,
            tolerance: 10,
            onWillStartDrag: (params) => this._sortTopBarActionStart(params),
            onDrop: (params) => this._sortTopBarActionDrop(params),
        });
    }

    getDropdownClass(action) {
        return (!this.env.isSmall && this._checkValueLocalStorage(action)) ||
            (this.env.isSmall && this.state.topbarInfos.currentTopBarAction?.id === action.id)
            ? "selected"
            : "";
    }

    getScrollingElement() {
        return this.root.el.parentElement;
    }

    /**
     * Reset mobile search state
     */
    resetSearchState() {
        Object.assign(this.state, {
            showSearchBar: false,
            showMobileSearch: false,
            showViewSwitcher: false,
        });
    }

    /**
     * @returns {TopBarAction}
     */
    get currentTopBarAction() {
        if (!this.env.config) {
            return {};
        }
        const { topBarActions, currentTopbarActionId } = this.env.config;
        return topBarActions?.find(({ id }) => id === currentTopbarActionId);
    }

    /**
     * @returns {Object}
     */
    get display() {
        return {
            layoutActions: true,
            ...this.props.display,
        };
    }

    /**
     * Called when an element of the breadcrumbs is clicked.
     *
     * @param {string} jsId
     */
    onBreadcrumbClicked(jsId) {
        this.actionService.restore(jsId);
    }

    onClickShowTopBar() {
        if (this.state.topbarInfos.showTopBar) {
            localStorage.removeItem(this.topBarLocalStorageKeyActionIdResId);
        } else {
            localStorage.setItem(this.topBarLocalStorageKeyActionIdResId, true);
        }
        this.state.topbarInfos.showTopBar = !this.state.topbarInfos.showTopBar;
    }

    /**
     * Show or hide the control panel on the top screen.
     * The function is throttled to avoid refreshing the scroll position more
     * often than necessary.
     */
    onScrollThrottled() {
        if (this.isScrolling) {
            return;
        }
        this.isScrolling = true;
        browser.requestAnimationFrame(() => (this.isScrolling = false));

        const scrollTop = this.getScrollingElement().scrollTop;
        const delta = Math.round(scrollTop - this.oldScrollTop);

        if (scrollTop > this.initialScrollTop) {
            // Beneath initial position => sticky display
            this.root.el.classList.add(STICKY_CLASS);
            if (delta < 0) {
                // Going up
                this.lastScrollTop = Math.min(0, this.lastScrollTop - delta);
            } else {
                // Going down | not moving
                this.lastScrollTop = Math.max(
                    -this.root.el.offsetHeight,
                    -this.root.el.offsetTop - delta
                );
            }
            this.root.el.style.top = `${this.lastScrollTop}px`;
        } else {
            // Above initial position => standard display
            this.root.el.classList.remove(STICKY_CLASS);
            this.lastScrollTop = 0;
        }

        this.oldScrollTop = scrollTop;
    }

    /**
     * Allow to switch from the current view to another.
     * Called when a view is clicked in the view switcher
     * and reset mobile search state on switch view.
     *
     * @param {ViewType} viewType
     */
    switchView(viewType) {
        this.resetSearchState();
        this.actionService.switchView(viewType);
    }

    cycleThroughViews() {
        const currentViewType = this.env.config.viewType;
        const viewSwitcherEntries = this.env.config.viewSwitcherEntries;
        const currentIndex = viewSwitcherEntries.findIndex(
            (entry) => entry.type === currentViewType
        );
        const nextIndex = (currentIndex + 1) % viewSwitcherEntries.length;
        this.switchView(viewSwitcherEntries[nextIndex].type);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    onWindowClick(ev) {
        if (this.state.showViewSwitcher && !ev.target.closest(".o_cp_switch_buttons")) {
            this.state.showViewSwitcher = false;
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onMainButtonsKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "arrowdown") {
            this.env.searchModel.trigger("focus-view");
            ev.preventDefault();
            ev.stopPropagation();
        }
    }

    /**
     * @param {TopBarAction} action
     */
    _checkValueLocalStorage(action) {
        const actionIdStr = action.id.toString();
        return this.state.topbarInfos.visibleTopBarActions[actionIdStr];
    }

    /**
     * The selected action is put into (or removed from) the localStorage and its visibility changes.
     * The state variable visibleTopBarActions keeps track of the visible actions to avoid  having to parse
     * the localStorage values every time we want to access them.
     * @param {TopBarAction} action
     */
    _setVisibility(action) {
        const actionIdStr = action.id.toString();
        if (this.state.topbarInfos.visibleTopBarActions[actionIdStr]) {
            delete this.state.topbarInfos.visibleTopBarActions[actionIdStr];
        } else {
            this.state.topbarInfos.visibleTopBarActions[actionIdStr] = true;
        }
        localStorage.setItem(
            this.localStorageKeyActionIdResId,
            JSON.stringify(this.state.topbarInfos.visibleTopBarActions)
        );
    }

    _onShareCheckboxChange() {
        this.state.topbarInfos.newActionIsShared = !this.state.topbarInfos.newActionIsShared;
    }

    /**
     * @param {Event} ev
     */
    async _saveNewAction(ev) {
        const {
            newActionName,
            newActionIsShared,
            topBarActions,
            visibleTopBarActions,
            currentTopBarAction,
        } = this.state.topbarInfos;
        if (!newActionName) {
            this.notificationService.add(_t("A name for your new action is required."), {
                type: "danger",
            });
            ev.stopPropagation();
            return this.newActionNameRef.el.focus();
        }
        const duplicateName = topBarActions.some(({ name }) => name === newActionName);
        if (duplicateName) {
            this.notificationService.add(_t("An action with the same name already exists."), {
                type: "danger",
            });
            ev.stopPropagation();
            return this.newActionNameRef.el.focus();
        }
        const userId = newActionIsShared ? false : user.userId;

        const extractCommonValues = ({ parent_action_id, action_id, res_model }) => ({
            parent_action_id: parent_action_id[0],
            action_id: action_id ? action_id[0] : this.env.config.actionId,
            res_model,
            res_id: this.env.searchModel.globalContext.active_id,
            user_id: userId,
            is_deletable: true,
            default_view_mode: this.env.config.viewType,
        });
        let values;
        let parentActionIdTuple, actionIdTuple;
        if (currentTopBarAction) {
            const { parent_action_id, action_id, python_action, domain, context } =
                currentTopBarAction;
            parentActionIdTuple = parent_action_id;
            actionIdTuple = action_id;
            values = {
                ...extractCommonValues(currentTopBarAction),
                python_action,
                domain,
                context,
                name: newActionName,
            };
        } else {
            const { parent_action_id, res_model } = topBarActions[0];
            parentActionIdTuple = parent_action_id;
            actionIdTuple = this.env.config.actionId;

            values = {
                ...extractCommonValues({ parent_action_id, action_id: undefined, res_model }),
                name: newActionName,
            };
        }
        const topBarActionId = await this.orm.call("ir.actions.topbar", "create", [values]);
        const description = `${newActionName} Filter`;
        this.env.searchModel.createNewFavorite({
            description,
            isDefault: true,
            isShared: userId,
            topBarActionId,
        });
        Object.assign(this.state.topbarInfos, {
            newActionName: "",
            newActionIsShared: false,
        });
        const enrichedNewTopBarAction = {
            ...values,
            parent_action_id: parentActionIdTuple,
            action_id: actionIdTuple,
            id: topBarActionId,
        };
        this.state.topbarInfos.topBarActions.push(enrichedNewTopBarAction);
        const topBarActionIdStr = topBarActionId.toString();
        visibleTopBarActions[topBarActionIdStr] = true;
        localStorage.setItem(
            this.localStorageKeyActionIdResId,
            JSON.stringify(visibleTopBarActions)
        );
        this.env.config.currentTopbarActionId = topBarActionId;
        this.state.topbarInfos.currentTopBarAction = enrichedNewTopBarAction;
        this.state.topbarInfos.newActionName = `${newActionName} Custom`;
    }

    /**
     * @param {TopBarAction} action
     */
    openConfirmationDialog(action) {
        const dialogProps = {
            title: _t("Warning"),
            body: action.user_id
                ? _t("Are you sure that you want to remove this topbar action?")
                : _t("This topbar action is global and will be removed for everyone."),
            confirmLabel: _t("Delete"),
            confirm: async () => await this._deleteTopBarAction(action),
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }

    /**
     * @param {TopBarAction} action
     */
    async _deleteTopBarAction(action) {
        const { visibleTopBarActions, topBarActions, currentTopBarAction } = this.state.topbarInfos;
        const actionIdStr = action.id.toString();
        if (visibleTopBarActions[actionIdStr]) {
            delete visibleTopBarActions[actionIdStr];
        }
        localStorage.setItem(
            this.localStorageKeyActionIdResId,
            JSON.stringify(visibleTopBarActions)
        );
        this.state.topbarInfos.topBarActions = topBarActions.filter(({ id }) => id !== action.id);
        await this.orm.call("ir.actions.topbar", "unlink", [action.id]);
        if (action.id === currentTopBarAction?.id) {
            const { active_id, active_model } = this.env.searchModel.globalContext;
            const additionalContext = {
                ...makeContext([action.context]),
                active_id,
                active_model,
                fromParentAction: true,
            };
            this.actionService.doAction(action.parent_action_id[0], {
                additionalContext,
                stackPosition: "replaceCurrentAction",
            });
        }
    }

    /**
     * @param {TopBarAction} action
     */
    async onTopBarActionClick(action) {
        this.env.config.topBarActions = this.state.topbarInfos.topBarActions;
        const { active_id, active_model } = this.env.searchModel.globalContext;
        const context = {
            ...makeContext([action.context]),
            active_id,
            active_model,
            currentTopbarActionId: action.id,
            parentActionChildren: this.env.config.topBarActions,
            fromParentAction: true,
        };
        this.actionService.doActionButton({
            type: action.python_action ? "object" : "action",
            resId: this.env.searchModel?.globalContext.active_id,
            name: action.python_action || action.action_id[0] || action.action_id,
            resModel: action.res_model,
            context,
            stackPosition: this.env.config.fromParentAction ? "replaceCurrentAction" : "",
            viewType: action.default_view_mode,
        });
    }

    _sortTopBarActions(order) {
        this.state.topbarInfos.topBarActions = this.state.topbarInfos.topBarActions.sort((a, b) => {
            return order.indexOf(a.id) - order.indexOf(b.id);
        });
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     */
    _sortTopBarActionStart({ element, addClass }) {
        addClass(element, "o_dragged_topBar_action");
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} params.previous
     */
    _sortTopBarActionDrop({ element, previous }) {
        const order = this.state.topbarInfos.topBarActions.map((el) => el.id);
        const elementId = Number(element.dataset.id);
        const elementIndex = order.indexOf(elementId);
        order.splice(elementIndex, 1);
        if (previous) {
            const prevIndex = order.indexOf(Number(previous.dataset.id));
            order.splice(prevIndex + 1, 0, elementId);
        } else {
            order.splice(0, 0, elementId);
        }
        this._sortTopBarActions(order);
        browser.localStorage.setItem(
            this.topBarOrderLocalStorageKeyActionIdResId,
            JSON.stringify(order)
        );
    }
}
