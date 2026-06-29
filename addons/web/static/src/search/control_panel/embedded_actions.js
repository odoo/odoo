import { Component, proxy, props, t, useRef, useLayoutEffect, useEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { AccordionItem } from "@web/core/dropdown/accordion_item";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Transition } from "@web/core/transition";
import { useSortable } from "@web/core/utils/sortable_owl";
import { user } from "@web/core/user";
import { makeContext } from "@web/core/context";

export class EmbeddedActionsConfigHandler {
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

export class EmbeddedActionsState {
    constructor(env, orm, actionService, dialogService, notificationService) {
        this.env = env;
        this.orm = orm;
        this.actionService = actionService;
        this.dialogService = dialogService;
        this.notificationService = notificationService;

        let defaultEmbeddedActions = this.env.config.embeddedActions;
        if (this.env.config.embeddedActions?.length > 0 && !this.env.config.parentActionId) {
            const { parent_res_model, parent_action_id } = this.env.config.embeddedActions[0];
            defaultEmbeddedActions = [
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
            this.env.config.setEmbeddedActions(defaultEmbeddedActions);
        }

        const parentActionId =
            this.env.config.parentActionId ||
            this.env.config.embeddedActions?.[0]?.parent_action_id[0] ||
            this.env.config.embeddedActions?.[0]?.parent_action_id ||
            "";
        const currentActiveId = this.env.searchModel?.globalContext.active_id || false;

        this.currentEmbeddedActionId = this.env.config.currentEmbeddedActionId;
        this.currentEmbeddedAction =
            defaultEmbeddedActions?.find(({ id }) => id === this.currentEmbeddedActionId) ||
            defaultEmbeddedActions?.[0];

        this.configHandler = new EmbeddedActionsConfigHandler(
            parentActionId,
            currentActiveId,
            this.currentEmbeddedAction?.parent_res_model,
            this.orm
        );

        this.embeddedInfos = {
            showEmbedded: !!this.configHandler.getEmbeddedActionsConfig("embedded_visibility"),
            embeddedActions: defaultEmbeddedActions || [],
            newActionIsShared: false,
            newActionName: this.currentEmbeddedAction?.name
                ? _t("Custom %s", this.currentEmbeddedAction.name)
                : _t("Custom Embedded Action"),
            visibleEmbeddedActions:
                this.configHandler.getEmbeddedActionsConfig("embedded_actions_visibility") || [],
            currentEmbeddedAction: this.currentEmbeddedAction,
        };

        if (this.embeddedInfos.embeddedActions.length > 0) {
            const embeddedOrder =
                this.configHandler.getEmbeddedActionsConfig("embedded_actions_order");
            if (embeddedOrder) {
                this.sortEmbeddedActions(embeddedOrder);
            }
        }
    }

    async onClickShowEmbedded() {
        if (!this.embeddedInfos.showEmbedded && !this.configHandler.hasEmbeddedActionsConfig()) {
            const embeddedSettings = await this.configHandler.fetchEmbeddedActionsConfig();
            if (this.configHandler.embeddedActionsKey in embeddedSettings) {
                this.configHandler.updateEmbeddedActionsConfig(embeddedSettings);
                this.embeddedInfos.visibleEmbeddedActions =
                    this.configHandler.getEmbeddedActionsConfig("embedded_actions_visibility") ||
                    [];
                const embeddedOrder =
                    this.configHandler.getEmbeddedActionsConfig("embedded_actions_order");
                if (embeddedOrder) {
                    this.sortEmbeddedActions(embeddedOrder);
                }
                this.configHandler.setEmbeddedActionsConfig({ embedded_visibility: true });
            } else {
                const config = {
                    res_model: this.embeddedInfos.currentEmbeddedAction.parent_res_model,
                    embedded_actions_visibility: [],
                    embedded_visibility: true,
                    embedded_actions_order: [],
                };
                if (this.embeddedInfos.embeddedActions?.length > 0) {
                    const embeddedActionKey = this.embeddedInfos.currentEmbeddedAction?.id || false;
                    if (!this.embeddedInfos.visibleEmbeddedActions.includes(embeddedActionKey)) {
                        this.embeddedInfos.visibleEmbeddedActions.push(embeddedActionKey);
                        config.embedded_actions_visibility =
                            this.embeddedInfos.visibleEmbeddedActions;
                    }
                }
                this.configHandler.setEmbeddedActionsConfig(config);
            }
        } else {
            this.configHandler.setEmbeddedActionsConfig({
                embedded_visibility: !this.embeddedInfos.showEmbedded,
            });
        }
        this.embeddedInfos.showEmbedded = !this.embeddedInfos.showEmbedded;
    }

    isEmbeddedActionVisible(action) {
        return this.embeddedInfos.visibleEmbeddedActions.includes(action.id);
    }

    setVisibility(actionId) {
        if (this.embeddedInfos.visibleEmbeddedActions.includes(actionId)) {
            const index = this.embeddedInfos.visibleEmbeddedActions.indexOf(actionId);
            if (index !== -1) {
                this.embeddedInfos.visibleEmbeddedActions.splice(index, 1);
            }
        } else {
            this.embeddedInfos.visibleEmbeddedActions.push(actionId);
        }
        this.configHandler.setEmbeddedActionsConfig({
            embedded_actions_visibility: this.embeddedInfos.visibleEmbeddedActions,
        });
    }

    onShareCheckboxChange() {
        this.embeddedInfos.newActionIsShared = !this.embeddedInfos.newActionIsShared;
    }

    async saveNewAction(ev, newActionNameRef) {
        const {
            newActionName,
            newActionIsShared,
            embeddedActions,
            currentEmbeddedAction,
            visibleEmbeddedActions,
        } = this.embeddedInfos;
        if (!newActionName) {
            this.notificationService.add(_t("A name for your new action is required."), {
                type: "danger",
            });
            ev.stopPropagation();
            return newActionNameRef.el.focus();
        }
        const duplicateName = embeddedActions.some(({ name }) => name === newActionName);
        if (duplicateName) {
            this.notificationService.add(_t("An action with the same name already exists."), {
                type: "danger",
            });
            ev.stopPropagation();
            return newActionNameRef.el.focus();
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

        Object.assign(this.embeddedInfos, { newActionName: "", newActionIsShared: false });
        const enrichedNewEmbeddedAction = {
            ...values,
            parent_action_id,
            action_id,
            id: embeddedActionId[0],
        };

        this.embeddedInfos.embeddedActions.push(enrichedNewEmbeddedAction);
        visibleEmbeddedActions.push(embeddedActionId[0]);

        const order = this.embeddedInfos.embeddedActions.map((el) => el.id);
        this.configHandler.setEmbeddedActionsConfig({
            embedded_actions_visibility: visibleEmbeddedActions,
            embedded_actions_order: order,
        });
        this.env.config.setCurrentEmbeddedAction(embeddedActionId);
        this.embeddedInfos.currentEmbeddedAction = enrichedNewEmbeddedAction;
        this.embeddedInfos.newActionName = `${newActionName} Custom`;
    }

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

    async _deleteEmbeddedAction(action) {
        const { visibleEmbeddedActions, embeddedActions, currentEmbeddedAction } =
            this.embeddedInfos;
        const index = visibleEmbeddedActions.indexOf(action.id);
        if (index !== -1) {
            visibleEmbeddedActions.splice(index, 1);
        }

        this.embeddedInfos.embeddedActions = embeddedActions.filter(({ id }) => id !== action.id);
        const order = this.embeddedInfos.embeddedActions.map((el) => el.id);
        this.configHandler.setEmbeddedActionsConfig({
            embedded_actions_visibility: visibleEmbeddedActions,
            embedded_actions_order: order,
        });
        await this.orm.unlink("ir.embedded.actions", [action.id]);

        if (action.id === currentEmbeddedAction?.id) {
            const { active_id, active_model } = this.env.searchModel.globalContext;
            const actionContext = action.context ? makeContext([action.context]) : {};
            this.actionService.doAction(action.parent_action_id[0] || action.parent_action_id, {
                additionalContext: { ...actionContext, active_id, active_model },
                stackPosition: "replaceCurrentAction",
            });
        }
    }

    async onEmbeddedActionClick(action) {
        this.env.config.setEmbeddedActions(this.embeddedInfos.embeddedActions);
        const { active_id, active_model } = this.env.searchModel.globalContext;
        const actionContext = action.context ? makeContext([action.context]) : {};
        const context = {
            ...actionContext,
            active_id,
            active_model,
            current_embedded_action_id: action.id,
            parent_action_embedded_actions: this.embeddedInfos.embeddedActions,
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

    sortEmbeddedActions(order) {
        this.embeddedInfos.embeddedActions = this.embeddedInfos.embeddedActions.sort((a, b) => {
            const indexA = order.indexOf(a.id);
            const indexB = order.indexOf(b.id);
            if (!indexA) {
                return -1;
            }
            if (!indexB) {
                return 1;
            }
            return indexA - indexB;
        });
    }

    sortEmbeddedActionStart({ element, addClass }) {
        addClass(element, "o_dragged_embedded_action");
    }

    sortEmbeddedActionDrop({ element, previous }) {
        const order = this.embeddedInfos.embeddedActions.map((el) => el.id);
        const elementId = Number(element.dataset.id) || false;
        const elementIndex = order.indexOf(elementId);
        order.splice(elementIndex, 1);
        if (previous) {
            const prevIndex = order.indexOf(Number(previous.dataset.id) || false);
            order.splice(prevIndex + 1, 0, elementId);
        } else {
            order.splice(0, 0, elementId);
        }
        this.sortEmbeddedActions(order);
        this.configHandler.setEmbeddedActionsConfig({ embedded_actions_order: order });
    }
}

export function useEmbeddedActions() {
    const env = useEnv();
    const orm = useService("orm");
    const actionService = useService("action");
    const dialogService = useService("dialog");
    const notificationService = useService("notification");

    const state = proxy(
        new EmbeddedActionsState(env, orm, actionService, dialogService, notificationService)
    );

    return state;
}

export class EmbeddedActionsPanel extends Component {
    static template = "web.EmbeddedActionsPanel";
    static components = {
        Transition,
        Dropdown,
        DropdownItem,
        AccordionItem,
        CheckBox,
    };
    props = props({ state: t.object() });

    setup() {
        this.root = useRef("root");
        useSortable({
            enable: true,
            ref: this.root,
            elements: ".o_draggable",
            cursor: "move",
            delay: 200,
            tolerance: 10,
            onWillStartDrag: (params) => this.props.state.sortEmbeddedActionStart(params),
            onDrop: (params) => this.props.state.sortEmbeddedActionDrop(params),
        });

        this.newActionNameRef = useRef("newActionNameRef");
        // Delay opening embedded actions dropdown to avoid flicker
        useLayoutEffect(
            (el, showEmbedded) => {
                const timer = setTimeout(() => {
                    if (
                        showEmbedded &&
                        this.props.state.embeddedInfos.visibleEmbeddedActions.length === 1
                    ) {
                        el?.querySelector(".btn[name='openEmbeddedActions']")?.click();
                    }
                }, 100);
                return () => clearTimeout(timer);
            },
            () => [this.root.el, this.props.state.embeddedInfos.showEmbedded]
        );
    }

    isEmbeddedActionVisible(action) {
        return this.props.state.isEmbeddedActionVisible(action);
    }

    getDropdownClass(action) {
        return (!this.env.isSmall && this.isEmbeddedActionVisible(action)) ||
            (this.env.isSmall &&
                this.props.state.embeddedInfos.currentEmbeddedAction?.id === action.id)
            ? "selected"
            : "";
    }
}
