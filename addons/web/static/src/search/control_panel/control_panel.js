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

import { Component, useState, onMounted, useRef, useEffect } from "@odoo/owl";

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

class EmbeddedActionsConfigHandler {
    constructor(parentActionId, currentActiveId, parentResModel, ormService) {
        this.parentActionId = parentActionId;
        this.currentActiveId = currentActiveId;
        this.parentResModel = parentResModel;
        this.embeddedActionsKey = `${this.parentActionId}+${this.currentActiveId || ""}`;
        this.embeddedActionsConfig = user.settings.embedded_actions_config_ids || {};
        this.orm = ormService;
    }

    setEmbeddedActionsConfig(config) {
        if (this.embeddedActionsKey in this.embeddedActionsConfig) {
            Object.assign(this.embeddedActionsConfig[this.embeddedActionsKey], config);
        } else {
            this.embeddedActionsConfig[this.embeddedActionsKey] = config;
        }
        this.orm.call("res.users.settings", "set_embedded_actions_setting", [
            user.settings.id,
            this.parentActionId,
            this.currentActiveId,
            config,
        ]);
    }

    getEmbeddedActionsConfig(key) {
        return this.embeddedActionsConfig[this.embeddedActionsKey]?.[key];
    }

    hasEmbeddedActionsConfig() {
        return this.embeddedActionsKey in this.embeddedActionsConfig;
    }

    async fetchEmbeddedActionsConfig() {
        return await this.orm.call(
            "res.users.settings",
            "get_embedded_actions_settings",
            [user.settings.id],
            { context: { res_model: this.parentResModel, res_id: this.currentActiveId } }
        );
    }

    updateEmbeddedActionsConfig(newSettings) {
        for (const key in newSettings) {
            this.embeddedActionsConfig[key] = newSettings[key];
        }
    }
}

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

        const parentActionId =
            this.env.config.parentActionId ||
            this.env.config.embeddedActions?.[0]?.parent_action_id[0] ||
            this.env.config.embeddedActions?.[0]?.parent_action_id ||
            "";
        const currentActiveId = this.env.searchModel?.globalContext.active_id || false;
        this.embeddedActionsConfigHandler = new EmbeddedActionsConfigHandler(
            parentActionId,
            currentActiveId,
            this.currentEmbeddedAction?.parent_res_model,
            this.orm
        );

        this.state = useState({
            embeddedInfos: {
                showEmbedded:
                    !!this.embeddedActionsConfigHandler.getEmbeddedActionsConfig(
                        "embedded_visibility"
                    ),
                embeddedActions: this.defaultEmbeddedActions || [],
                newActionIsShared: false,
                newActionName: this.newActionNameGetter,
                visibleEmbeddedActions:
                    this.embeddedActionsConfigHandler.getEmbeddedActionsConfig(
                        "embedded_actions_visibility"
                    ) || [],
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

        useEffect(() => {
            if (
                !this.env.isSmall ||
                ("adaptToScroll" in this.display && !this.display.adaptToScroll)
            ) {
                return;
            }
            const scrollingEl = this.getScrollingElement();
            this.scrollingElementResizeObserver.observe(scrollingEl);
            scrollingEl.addEventListener("scroll", this.onScrollThrottledBound);
            this.root.el.style.top = "0px";
            this.scrollingElementHeight = scrollingEl.scrollHeight;
            return () => {
                this.scrollingElementResizeObserver.unobserve(scrollingEl);
                scrollingEl.removeEventListener("scroll", this.onScrollThrottledBound);
            };
        });

        // The goal is to automatically open the dropdown menu of embedded actions if there is only one visible embedded action
        // We use a timer to delay the display of that dropdown menu to avoid flicker issues
        useEffect(
            (el, showEmbedded) => {
                const timer = setTimeout(() => {
                    if (
                        showEmbedded &&
                        this.state.embeddedInfos.visibleEmbeddedActions.length === 1
                    ) {
                        el.querySelector(".btn[name='openEmbeddedActions']")?.click();
                    }
                }, 100);
                return () => clearTimeout(timer);
            },
            () => [this.root.el, this.state.embeddedInfos.showEmbedded]
        );

        onMounted(() => {
            if (this.state.embeddedInfos.embeddedActions?.length > 0) {
                const embeddedOrder =
                    this.embeddedActionsConfigHandler.getEmbeddedActionsConfig(
                        "embedded_actions_order"
                    );
                if (embeddedOrder) {
                    this._sortEmbeddedActions(embeddedOrder);
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

    scrollingElementResizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
            if (this.scrollingElementHeight !== entry.target.scrollingElementHeight) {
                this.oldScrollTop +=
                    entry.target.scrollingElementHeight - this.scrollingElementHeight;
                this.scrollingElementHeight = entry.target.scrollingElementHeight;
            }
        }
    });

    getDropdownClass(action) {
        return (!this.env.isSmall && this._isEmbeddedActionVisible(action)) ||
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
     * @returns {Object}
     */
    get display() {
        return {
            layoutActions: true,
            ...this.props.display,
        };
    }

    async onClickShowEmbedded() {
        if (
            !this.state.embeddedInfos.showEmbedded &&
            !this.embeddedActionsConfigHandler.hasEmbeddedActionsConfig()
        ) {
            // If there are embedded actions and no config has been found in the settings, we will fetch it from DB
            // We need to fetch because it's possible that the config from DB was changed while it wasn't in the browser user settings
            // We then need to keep the browser user settings up to date with the DB
            const embeddedSettings =
                await this.embeddedActionsConfigHandler.fetchEmbeddedActionsConfig();
            if (this.embeddedActionsConfigHandler.embeddedActionsKey in embeddedSettings) {
                this.embeddedActionsConfigHandler.updateEmbeddedActionsConfig(embeddedSettings);
                this.state.embeddedInfos.visibleEmbeddedActions =
                    this.embeddedActionsConfigHandler.getEmbeddedActionsConfig(
                        "embedded_actions_visibility"
                    ) || [];
                const embeddedOrder =
                    this.embeddedActionsConfigHandler.getEmbeddedActionsConfig(
                        "embedded_actions_order"
                    );
                if (embeddedOrder) {
                    this._sortEmbeddedActions(embeddedOrder);
                }
                this.embeddedActionsConfigHandler.setEmbeddedActionsConfig({
                    embedded_visibility: true,
                });
            } else {
                // Store a new embedded actions config if still not found in the settings
                const config = {
                    res_model: this.state.embeddedInfos.currentEmbeddedAction.parent_res_model,
                    embedded_actions_visibility: [],
                    embedded_visibility: true,
                    embedded_actions_order: [],
                };
                // If there is no visible embedded actions, the current action (if it exists) is put by default
                if (this.state.embeddedInfos.embeddedActions?.length > 0) {
                    const embeddedActionKey =
                        this.state.embeddedInfos.currentEmbeddedAction?.id || false;
                    if (
                        !this.state.embeddedInfos.visibleEmbeddedActions.includes(embeddedActionKey)
                    ) {
                        this.state.embeddedInfos.visibleEmbeddedActions.push(embeddedActionKey);
                        config.embedded_actions_visibility =
                            this.state.embeddedInfos.visibleEmbeddedActions;
                    }
                }
                this.embeddedActionsConfigHandler.setEmbeddedActionsConfig(config);
            }
        } else {
            this.embeddedActionsConfigHandler.setEmbeddedActionsConfig({
                embedded_visibility: !this.state.embeddedInfos.showEmbedded,
            });
        }
        this.state.embeddedInfos.showEmbedded = !this.state.embeddedInfos.showEmbedded;
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
            if (delta <= 0) {
                // Going up | not moving
                this.lastScrollTop = Math.min(0, this.lastScrollTop - delta);
            } else {
                // Going down
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
    switchView(viewType, newWindow) {
        this.actionService.switchView(viewType, {}, { newWindow });
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
    _isEmbeddedActionVisible(action) {
        return this.state.embeddedInfos.visibleEmbeddedActions.includes(action.id);
    }

    /**
     * The selected action is put into (or removed from) the user settings and its visibility changes.
     * The state variable visibleEmbeddedActions keeps track of the visible actions to avoid  having to parse
     * the user settings values every time we want to access them.
     * @param {EmbeddedAction} action
     */
    _setVisibility(actionId) {
        if (this.state.embeddedInfos.visibleEmbeddedActions.includes(actionId)) {
            const embeddedActionIndex =
                this.state.embeddedInfos.visibleEmbeddedActions.indexOf(actionId);
            if (embeddedActionIndex !== -1) {
                this.state.embeddedInfos.visibleEmbeddedActions.splice(embeddedActionIndex, 1);
            }
        } else {
            this.state.embeddedInfos.visibleEmbeddedActions.push(actionId);
        }
        this.embeddedActionsConfigHandler.setEmbeddedActionsConfig({
            embedded_actions_visibility: this.state.embeddedInfos.visibleEmbeddedActions,
        });
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
        const embeddedActionResId = embeddedActionId[0];
        visibleEmbeddedActions.push(embeddedActionResId);
        const order = this.state.embeddedInfos.embeddedActions.map((el) => el.id);
        this.embeddedActionsConfigHandler.setEmbeddedActionsConfig({
            embedded_actions_visibility: visibleEmbeddedActions,
            embedded_actions_order: order,
        });
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
        const embeddedActionIndex = visibleEmbeddedActions.indexOf(action.id);
        if (embeddedActionIndex !== -1) {
            visibleEmbeddedActions.splice(embeddedActionIndex, 1);
        }
        this.state.embeddedInfos.embeddedActions = embeddedActions.filter(
            ({ id }) => id !== action.id
        );
        const order = this.state.embeddedInfos.embeddedActions.map((el) => el.id);
        this.embeddedActionsConfigHandler.setEmbeddedActionsConfig({
            embedded_actions_visibility: visibleEmbeddedActions,
            embedded_actions_order: order,
        });
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
                stackPosition: "replaceCurrentAction",
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
        this.embeddedActionsConfigHandler.setEmbeddedActionsConfig({
            embedded_actions_order: order,
        });
    }

    dropdownifyButtons() {
        const adaptiveMenu = document.querySelector(
            ".o-control-panel-adaptive-dropdown.dropdown-menu"
        );
        const meaningfulElements = this.getBoxedElements(adaptiveMenu.children);
        for (const el of meaningfulElements) {
            el.classList.add("dropdown-item");
            el.classList.remove("btn");
        }
    }

    getBoxedElements(elements) {
        const boxed = [];
        for (const el of [...elements]) {
            const elStyles = el.ownerDocument.defaultView.getComputedStyle(el);
            if (elStyles.getPropertyValue("display") === "contents") {
                boxed.push(...this.getBoxedElements(el.children));
            } else if (elStyles.getPropertyValue("display") === "none") {
                continue;
            } else {
                boxed.push(el);
            }
        }
        return boxed;
    }
}
