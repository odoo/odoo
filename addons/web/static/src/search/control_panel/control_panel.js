import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Pager } from "@web/core/pager/pager";
import { useService } from "@web/core/utils/hooks";
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
import { Transition } from "@web/core/transition";
import { Breadcrumbs } from "../breadcrumbs/breadcrumbs";
import { SearchBar } from "../search_bar/search_bar";

import { Component, useState, onMounted, useExternalListener, useRef, useEffect } from "@odoo/owl";

const STICKY_CLASS = "o_mobile_sticky";

/**
 * @typedef EmbeddedAction
 * @property {number} id
 * @property {[number, string]} parent_action_id
 * @property {string} name
 * @property {number} sequence
 * @property {number} parent_res_id
 * @property {string} parent_res_model
 * @property {[number, string]} action_id
 * @property {string} python_method
 * @property {number} user_id
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
        Breadcrumbs,
        AccordionItem,
        CheckBox,
        Transition,
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
        this.isEmbeddedActionsOrderModifiable = false;
        this.defaultEmbeddedActions = this.env.config.embeddedActions;
        if (this.env.config.embeddedActions?.length > 0 && !this.env.config.parentActionId) {
            const { parent_res_model, parent_action_id } = this.env.config.embeddedActions[0];
            this.defaultEmbeddedActions = [
                {
                    id: false,
                    name: this.env.config?.actionName,
                    parent_action_id,
                    parent_res_model,
                    action_id: parent_action_id,
                    user_id: false,
                    context: {},
                },
                ...this.env.config.embeddedActions,
            ];
            this.env.config.setEmbeddedActions(this.defaultEmbeddedActions);
        }

        /**
         * The visible embedded actions are unique to each user and to each res_id. The visible actions chosen by the
         * user are stored in the local storage in a key corresponding to a combination of the actionId, the activeId
         * and the currrent userId. Each key contains a dict. The keys of the latter are the id of the visible embedded
         * actions.
         */
        const parentActionId =
            this.env.config.parentActionId ||
            this.env.config.embeddedActions?.[0]?.parent_action_id[0] ||
            this.env.config.embeddedActions?.[0]?.parent_action_id ||
            "";
        this.embeddedActionsVisibilityKey = `visibleEmbeddedActions${parentActionId}+${
            this.env.searchModel?.globalContext.active_id || ""
        }+${user.userId}`;

        this.embeddedVisibilityKey = `visibleEmbedded${parentActionId}+${
            this.env.searchModel?.globalContext.active_id || ""
        }+${user.userId}`;

        this.embeddedOrderKey = `orderEmbedded${parentActionId}+${
            this.env.searchModel?.globalContext.active_id || ""
        }+${user.userId}`;

        this.state = useState({
            showSearchBar: false,
            showMobileSearch: false,
            showViewSwitcher: false,
            embeddedInfos: {
                showEmbedded:
                    this.env.config.embeddedActions?.length > 0 &&
                    ((!!this.env.config.parentActionId &&
                        !!JSON.parse(browser.localStorage.getItem("showEmbeddedActions"))) ||
                        !!JSON.parse(browser.localStorage.getItem(this.embeddedVisibilityKey))),
                embeddedActions: this.defaultEmbeddedActions || [],
                newActionIsShared: false,
                newActionName: this.newActionNameGetter,
                visibleEmbeddedActions:
                    (this.env.config.embeddedActions?.length > 0 &&
                        JSON.parse(
                            browser.localStorage.getItem(this.embeddedActionsVisibilityKey)
                        )) ||
                    {},
                currentEmbeddedAction: this.currentEmbeddedAction,
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

        onMounted(async () => {
            if (this.state.embeddedInfos.embeddedActions?.length > 0) {
                // If there is no visible embedded actions, the current action (if it exists) is put by default
                const embeddedActionKey =
                    this.state.embeddedInfos.currentEmbeddedAction?.id || false;
                if (
                    !Object.keys(this.state.embeddedInfos.visibleEmbeddedActions).includes(
                        embeddedActionKey.toString()
                    )
                ) {
                    this._setVisibility(embeddedActionKey);
                }
                const embeddedOrderLocalStorageKey = browser.localStorage.getItem(
                    this.embeddedOrderKey
                );
                if (embeddedOrderLocalStorageKey) {
                    this._sortEmbeddedActions(JSON.parse(embeddedOrderLocalStorageKey));
                }
            }
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
            enable: true,
            ref: this.root,
            elements: ".o_draggable",
            cursor: "move",
            delay: 200,
            tolerance: 10,
            onWillStartDrag: (params) => this._sortEmbeddedActionStart(params),
            onDrop: (params) => this._sortEmbeddedActionDrop(params),
        });
    }

    getDropdownClass(action) {
        return (!this.env.isSmall && this._checkValueLocalStorage(action)) ||
            (this.env.isSmall && this.state.embeddedInfos.currentEmbeddedAction?.id === action.id)
            ? "selected"
            : "";
    }

    getScrollingElement() {
        return this.root.el.parentElement;
    }

    /**
     * @returns {EmbeddedAction}
     */
    get currentEmbeddedAction() {
        if (!this.env.config) {
            return {};
        }
        const { currentEmbeddedActionId } = this.env.config;
        return (
            this.defaultEmbeddedActions?.find(({ id }) => id === currentEmbeddedActionId) ||
            this.defaultEmbeddedActions?.[0]
        );
    }

    get newActionNameGetter() {
        if (this.currentEmbeddedAction?.name) {
            return _t("Custom %s", this.currentEmbeddedAction.name);
        } else {
            return _t("Custom Embedded Action");
        }
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
     * @returns {Object}
     */
    get display() {
        return {
            layoutActions: true,
            ...this.props.display,
        };
    }

    onClickShowEmbedded() {
        if (this.state.embeddedInfos.showEmbedded) {
            browser.localStorage.removeItem(this.embeddedVisibilityKey);
        } else {
            browser.localStorage.setItem(this.embeddedVisibilityKey, true);
        }
        this.state.embeddedInfos.showEmbedded = !this.state.embeddedInfos.showEmbedded;
        browser.localStorage.setItem("showEmbeddedActions", this.state.embeddedInfos.showEmbedded);
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
     * @param {import("@web/views/view").ViewType} viewType
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
     * @param {EmbeddedAction} action
     */
    _checkValueLocalStorage(action) {
        const actionIdStr = action.id.toString();
        return this.state.embeddedInfos.visibleEmbeddedActions[actionIdStr];
    }

    /**
     * The selected action is put into (or removed from) the localStorage and its visibility changes.
     * The state variable visibleEmbeddedActions keeps track of the visible actions to avoid  having to parse
     * the localStorage values every time we want to access them.
     * @param {EmbeddedAction} action
     */
    _setVisibility(actionId) {
        const actionIdStr = actionId.toString();
        if (this.state.embeddedInfos.visibleEmbeddedActions[actionIdStr]) {
            delete this.state.embeddedInfos.visibleEmbeddedActions[actionIdStr];
        } else {
            this.state.embeddedInfos.visibleEmbeddedActions[actionIdStr] = true;
        }
        browser.localStorage.setItem(
            this.embeddedActionsVisibilityKey,
            JSON.stringify(this.state.embeddedInfos.visibleEmbeddedActions)
        );
    }

    _onShareCheckboxChange() {
        this.state.embeddedInfos.newActionIsShared = !this.state.embeddedInfos.newActionIsShared;
    }

    /**
     * @param {Event} ev
     */
    async _saveNewAction(ev) {
        const {
            newActionName,
            newActionIsShared,
            embeddedActions,
            currentEmbeddedAction,
            visibleEmbeddedActions,
        } = this.state.embeddedInfos;
        if (!newActionName) {
            this.notificationService.add(_t("A name for your new action is required."), {
                type: "danger",
            });
            ev.stopPropagation();
            return this.newActionNameRef.el.focus();
        }
        const duplicateName = embeddedActions.some(({ name }) => name === newActionName);
        if (duplicateName) {
            this.notificationService.add(_t("An action with the same name already exists."), {
                type: "danger",
            });
            ev.stopPropagation();
            return this.newActionNameRef.el.focus();
        }
        const userId = newActionIsShared ? false : user.userId;

        const {
            parent_action_id,
            action_id,
            parent_res_model,
            python_method,
            domain,
            context,
            groups_ids,
        } = currentEmbeddedAction;
        const values = {
            parent_action_id: parent_action_id[0],
            parent_res_model,
            parent_res_id: this.env.searchModel.globalContext.active_id,
            user_id: userId,
            is_deletable: true,
            default_view_mode: this.env.config.viewType,
            domain,
            context,
            groups_ids,
            name: newActionName,
        };
        if (python_method) {
            values.python_method = python_method;
        } else {
            values.action_id = action_id[0] || this.env.config.actionId;
        }
        const embeddedActionId = await this.orm.create("ir.embedded.actions", [values]);
        const description = `${newActionName}`;
        this.env.searchModel.createNewFavorite({
            description,
            isDefault: true,
            isShared: newActionIsShared,
            embeddedActionId: embeddedActionId[0],
        });
        Object.assign(this.state.embeddedInfos, {
            newActionName: "",
            newActionIsShared: false,
        });
        const enrichedNewEmbeddedAction = {
            ...values,
            parent_action_id,
            action_id,
            id: embeddedActionId[0],
        };
        this.state.embeddedInfos.embeddedActions.push(enrichedNewEmbeddedAction);
        const embeddedActionIdStr = embeddedActionId[0].toString();
        visibleEmbeddedActions[embeddedActionIdStr] = true;
        const order = this.state.embeddedInfos.embeddedActions.map((el) => el.id);
        browser.localStorage.setItem(
            this.embeddedActionsVisibilityKey,
            JSON.stringify(visibleEmbeddedActions)
        );
        browser.localStorage.setItem(this.embeddedOrderKey, JSON.stringify(order));
        this.env.config.setCurrentEmbeddedAction(embeddedActionId);
        this.state.embeddedInfos.currentEmbeddedAction = enrichedNewEmbeddedAction;
        this.state.embeddedInfos.newActionName = `${newActionName} Custom`;
    }

    /**
     * @param {EmbeddedAction} action
     */
    openConfirmationDialog(action) {
        const dialogProps = {
            title: _t("Warning"),
            body: action.user_id
                ? _t("Are you sure that you want to remove this embedded action?")
                : _t("This embedded action is global and will be removed for everyone."),
            confirmLabel: _t("Delete"),
            confirm: async () => await this._deleteEmbeddedAction(action),
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }

    /**
     * @param {EmbeddedAction} action
     */
    async _deleteEmbeddedAction(action) {
        const { visibleEmbeddedActions, embeddedActions, currentEmbeddedAction } =
            this.state.embeddedInfos;
        const actionIdStr = action.id.toString();
        if (visibleEmbeddedActions[actionIdStr]) {
            delete visibleEmbeddedActions[actionIdStr];
        }
        browser.localStorage.setItem(
            this.embeddedActionsVisibilityKey,
            JSON.stringify(visibleEmbeddedActions)
        );
        this.state.embeddedInfos.embeddedActions = embeddedActions.filter(
            ({ id }) => id !== action.id
        );
        await this.orm.unlink("ir.embedded.actions", [action.id]);
        if (action.id === currentEmbeddedAction?.id) {
            const { active_id, active_model } = this.env.searchModel.globalContext;
            const actionContext = action.context ? makeContext([action.context]) : {};
            const additionalContext = {
                ...actionContext,
                active_id,
                active_model,
            };
            this.actionService.doAction(action.parent_action_id[0] || action.parent_action_id, {
                additionalContext,
                stackPosition: "replaceCurrentAction",
            });
        }
    }

    /**
     * @param {EmbeddedAction} action
     */
    async onEmbeddedActionClick(action) {
        this.env.config.setEmbeddedActions(this.state.embeddedInfos.embeddedActions);
        const { active_id, active_model } = this.env.searchModel.globalContext;
        const actionContext = action.context ? makeContext([action.context]) : {};
        const context = {
            ...actionContext,
            active_id,
            active_model,
            current_embedded_action_id: action.id,
            parent_action_embedded_actions: this.state.embeddedInfos.embeddedActions,
            parent_action_id: action.parent_action_id[0] || action.parent_action_id,
        };
        this.actionService.doActionButton(
            {
                type: action.python_method ? "object" : "action",
                resId: this.env.searchModel?.globalContext.active_id,
                name: action.python_method || action.action_id[0] || action.action_id,
                resModel: action.parent_res_model,
                context,
                stackPosition: this.env.config.parentActionId ? "replaceCurrentAction" : "",
                viewType: action.default_view_mode,
            },
            { isEmbeddedAction: true }
        );
    }

    /**
     * @param {number[]} order
     */
    _sortEmbeddedActions(order) {
        this.state.embeddedInfos.embeddedActions = this.state.embeddedInfos.embeddedActions.sort(
            (a, b) => {
                const indexA = order.indexOf(a.id);
                if (!indexA) {
                    return -1;
                }
                const indexB = order.indexOf(b.id);
                if (!indexB) {
                    return 1;
                }
                return indexA - indexB;
            }
        );
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     */
    _sortEmbeddedActionStart({ element, addClass }) {
        addClass(element, "o_dragged_embedded_action");
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} params.previous
     */
    _sortEmbeddedActionDrop({ element, previous }) {
        const order = this.state.embeddedInfos.embeddedActions.map((el) => el.id);
        const elementId = Number(element.dataset.id) || false;
        const elementIndex = order.indexOf(elementId);
        order.splice(elementIndex, 1);
        if (previous) {
            const prevIndex = order.indexOf(Number(previous.dataset.id) || false);
            order.splice(prevIndex + 1, 0, elementId);
        } else {
            order.splice(0, 0, elementId);
        }
        this._sortEmbeddedActions(order);
        browser.localStorage.setItem(this.embeddedOrderKey, JSON.stringify(order));
    }
}
