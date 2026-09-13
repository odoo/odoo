// @ts-check
/** @odoo-module native */

import { reactive, useComponent } from "@odoo/owl";
import { useAction } from "@web/core/action_port";
import { makeContext } from "@web/core/context";
import { makeLogger } from "@web/core/debug/debug_logger";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/ui/dialog";

const log = makeLogger("web.search.embedded");

/** @type {WeakMap<object, Map<string, {confirmed: any[], pending: number}>>} */
const layoutWrites = new WeakMap();

/**
 * The config handler serializes writes. Keep their last acknowledged snapshot
 * separately from optimistic UI state, including when several writes fail.
 * @param {any} owner
 * @param {string} field
 * @param {any[]} previous
 * @param {Record<string, any>} config
 */
async function persistLayout(owner, field, previous, config) {
    let writes = layoutWrites.get(owner);
    if (!writes) {
        writes = new Map();
        layoutWrites.set(owner, writes);
    }
    let state = writes.get(field);
    if (!state) {
        state = { confirmed: previous, pending: 0 };
        writes.set(field, state);
    }
    state.pending++;
    const optimistic = owner.embeddedInfos[field];
    let saved = false;
    try {
        saved = await owner.configHandler.setEmbeddedActionsConfig(config);
        return saved;
    } finally {
        if (saved) {
            state.confirmed = optimistic;
        } else if (owner.embeddedInfos[field] === optimistic) {
            if (field === "embeddedActions") {
                // A layout rollback must not recreate actions deleted while saving,
                // or discard newly created actions and refreshed action metadata.
                owner.sortActions(state.confirmed.map(({ id }) => id));
            } else {
                const actions = owner.embeddedInfos.embeddedActions;
                const liveIds = actions && new Set(actions.map(({ id }) => id));
                owner.embeddedInfos[field] = liveIds
                    ? state.confirmed.filter((id) => liveIds.has(id))
                    : state.confirmed;
            }
        }
        log.logic("layout-settled", () => ({
            field,
            saved,
            pending: state.pending - 1,
        }));
        if (!--state.pending) {
            writes.delete(field);
        }
    }
}

/**
 * @typedef EmbeddedAction
 * @property {number} id
 * @property {[number, string] | number} parent_action_id
 * @property {string} name
 * @property {number} [sequence]
 * @property {number} [parent_res_id]
 * @property {string} parent_res_model
 * @property {[number, string] | number} action_id
 * @property {string} [python_method]
 * @property {number} [user_id]
 * @property {boolean} [is_deletable]
 * @property {string} [default_view_mode]
 * @property {string} [filter_ids]
 * @property {string} [domain]
 * @property {string} [context]
 * @property {any} [group_ids]
 */

/**
 * @param {[number, string] | number | undefined} value
 * @returns {number|undefined}
 */
function relationId(value) {
    return Array.isArray(value) ? value[0] : value;
}

export class EmbeddedActionsConfigHandler {
    /**
     * @param {number|string} parentActionId
     * @param {number|false} currentActiveId
     * @param {string} parentResModel
     * @param {import("services").ServiceFactories["orm"]} ormService
     * @param {import("services").ServiceFactories["notification"]} notificationService
     */
    constructor(
        parentActionId,
        currentActiveId,
        parentResModel,
        ormService,
        notificationService,
    ) {
        this.parentActionId = parentActionId;
        this.currentActiveId = currentActiveId;
        this.parentResModel = parentResModel;
        this.embeddedActionsKey = `${this.parentActionId}+${this.currentActiveId || ""}`;
        this.embeddedActionsConfig = user.settings.embedded_actions_config_ids || {};
        this.orm = ormService;
        this.notification = notificationService;
        /** @type {Promise<any>} */
        this._writeQueue = Promise.resolve();
    }

    /**
     * @param {Object} config
     * @returns {Promise<boolean>}
     */
    async setEmbeddedActionsConfig(config) {
        config = structuredClone(config);
        const run = async () => {
            const hadConfig = this.embeddedActionsKey in this.embeddedActionsConfig;
            const previousConfig = hadConfig
                ? structuredClone(this.embeddedActionsConfig[this.embeddedActionsKey])
                : null;
            if (hadConfig) {
                Object.assign(
                    this.embeddedActionsConfig[this.embeddedActionsKey],
                    config,
                );
            } else {
                this.embeddedActionsConfig[this.embeddedActionsKey] = config;
            }
            try {
                await this.orm.call(
                    "res.users.settings",
                    "set_embedded_actions_setting",
                    [
                        user.settings.id,
                        this.parentActionId,
                        this.currentActiveId,
                        config,
                    ],
                );
                return true;
            } catch {
                if (hadConfig) {
                    this.embeddedActionsConfig[this.embeddedActionsKey] =
                        previousConfig;
                } else {
                    delete this.embeddedActionsConfig[this.embeddedActionsKey];
                }
                this.notification.add(
                    _t("Failed to save the embedded actions configuration."),
                    { type: "danger" },
                );
                return false;
            }
        };
        const result = this._writeQueue.then(run, run);
        this._writeQueue = result.catch(() => {});
        return result;
    }

    /**
     * @param {string} key
     * @returns {any}
     */
    getEmbeddedActionsConfig(key) {
        return this.embeddedActionsConfig[this.embeddedActionsKey]?.[key];
    }

    /** @returns {boolean} */
    hasEmbeddedActionsConfig() {
        return this.embeddedActionsKey in this.embeddedActionsConfig;
    }

    /** @returns {Promise<Object>} */
    async fetchEmbeddedActionsConfig() {
        return await this.orm.call(
            "res.users.settings",
            "get_embedded_actions_settings",
            [user.settings.id],
            {
                context: {
                    res_model: this.parentResModel,
                    res_id: this.currentActiveId,
                },
            },
        );
    }

    /** @param {Object} newSettings */
    updateEmbeddedActionsConfig(newSettings) {
        for (const [key, value] of Object.entries(newSettings)) {
            this.embeddedActionsConfig[key] = value;
        }
    }
}

export class EmbeddedActions {
    /**
     * @param {object} params
     * @param {import("@web/env").OdooEnv} params.env
     * @param {import("services").ServiceFactories["orm"]} params.orm
     * @param {import("services").ServiceFactories["notification"]} params.notification
     * @param {import("services").ServiceFactories["dialog"]} params.dialog
     * @param {import("@web/core/action_port").ActionPort} params.action
     */
    constructor({ env, orm, notification, dialog, action }) {
        this.env = env;
        const config = /** @type {NonNullable<typeof env.config>} */ (env.config);
        this.orm = orm;
        this.notificationService = notification;
        this.dialogService = dialog;
        this.actionService = action;

        /** @type {EmbeddedAction[]} */
        this.defaultEmbeddedActions = config.embeddedActions;
        if (config.embeddedActions?.length > 0 && !config.parentActionId) {
            const { parent_res_model, parent_action_id } = config.embeddedActions[0];
            this.defaultEmbeddedActions = [
                {
                    id: false,
                    name: env.config?.actionName,
                    parent_action_id,
                    parent_res_model,
                    action_id: parent_action_id,
                    user_id: false,
                    context: {},
                },
                ...config.embeddedActions,
            ];
        }

        const parentActionId =
            config.parentActionId ||
            relationId(config.embeddedActions?.[0]?.parent_action_id) ||
            "";
        const currentActiveId = env.searchModel?.globalContext.active_id || false;
        this.configHandler = new EmbeddedActionsConfigHandler(
            parentActionId,
            currentActiveId,
            this.currentEmbeddedAction?.parent_res_model,
            this.orm,
            this.notificationService,
        );

        /** @type {{showEmbedded: boolean, embeddedActions: EmbeddedAction[], newActionIsShared: boolean, newActionName: string, visibleEmbeddedActions: (number|false)[], showAllEmbeddedActions: boolean, currentEmbeddedAction: EmbeddedAction}} */
        this.embeddedInfos = reactive({
            showEmbedded:
                !!this.configHandler.getEmbeddedActionsConfig("embedded_visibility"),
            embeddedActions: this.defaultEmbeddedActions || [],
            newActionIsShared: false,
            newActionName: this.defaultNewActionName,
            visibleEmbeddedActions: [],
            showAllEmbeddedActions: false,
            currentEmbeddedAction: this.currentEmbeddedAction,
        });
        this._applyStoredConfig();
    }

    _applyStoredConfig() {
        this.embeddedInfos.visibleEmbeddedActions = [
            ...(this.configHandler.getEmbeddedActionsConfig(
                "embedded_actions_visibility",
            ) || []),
        ];
        const embeddedOrder = this.configHandler.getEmbeddedActionsConfig(
            "embedded_actions_order",
        );
        if (embeddedOrder) {
            this.sortActions(embeddedOrder);
        }
    }

    /** @returns {EmbeddedAction} */
    get currentEmbeddedAction() {
        const { currentEmbeddedActionId } = this.env.config ?? {};
        return (
            this.defaultEmbeddedActions?.find(
                ({ id }) => id === currentEmbeddedActionId,
            ) || this.defaultEmbeddedActions?.[0]
        );
    }

    /**
     * @param {EmbeddedAction} action
     * @returns {Record<string, any>}
     */
    _actionContext(action) {
        const { active_id, active_model } = this.env.searchModel.globalContext;
        return {
            ...(action.context ? makeContext([action.context]) : {}),
            active_id,
            active_model,
        };
    }

    /** @returns {string} */
    get defaultNewActionName() {
        if (this.currentEmbeddedAction?.name) {
            return _t("Custom %s", this.currentEmbeddedAction.name);
        } else {
            return _t("Custom Embedded Action");
        }
    }

    /**
     * @param {{visibleEmbeddedActions: (number|false)[], showAllEmbeddedActions?: boolean}} embeddedInfos
     * @param {Pick<EmbeddedAction, "id">} candidate
     * @returns {boolean}
     */
    static isVisible(embeddedInfos, candidate) {
        return (
            !!embeddedInfos.showAllEmbeddedActions ||
            embeddedInfos.visibleEmbeddedActions.includes(candidate.id)
        );
    }

    async toggleBar() {
        if (this._togglingBar) {
            return;
        }
        this._togglingBar = true;
        const showEmbedded = !this.embeddedInfos.showEmbedded;
        try {
            await this._applyBarVisibility(showEmbedded);
            this.embeddedInfos.showEmbedded = showEmbedded;
        } finally {
            this._togglingBar = false;
        }
    }

    /** @param {boolean} showEmbedded */
    async _applyBarVisibility(showEmbedded) {
        if (showEmbedded && !this.configHandler.hasEmbeddedActionsConfig()) {
            const embeddedSettings =
                await this.configHandler.fetchEmbeddedActionsConfig();
            if (this.configHandler.embeddedActionsKey in embeddedSettings) {
                this.configHandler.updateEmbeddedActionsConfig(embeddedSettings);
                this._applyStoredConfig();
                await this.configHandler.setEmbeddedActionsConfig({
                    embedded_visibility: true,
                });
            } else {
                /** @type {{res_model: string, embedded_actions_visibility: (number|false)[], embedded_visibility: boolean, embedded_actions_order: (number|false)[]}} */
                const embeddedConfig = {
                    res_model:
                        this.embeddedInfos.currentEmbeddedAction.parent_res_model,
                    embedded_actions_visibility: [],
                    embedded_visibility: true,
                    embedded_actions_order: [],
                };
                if (this.embeddedInfos.embeddedActions?.length > 0) {
                    const embeddedActionKey =
                        this.embeddedInfos.currentEmbeddedAction?.id || false;
                    if (
                        !this.embeddedInfos.visibleEmbeddedActions.includes(
                            embeddedActionKey,
                        )
                    ) {
                        this.embeddedInfos.visibleEmbeddedActions = [
                            ...this.embeddedInfos.visibleEmbeddedActions,
                            embeddedActionKey,
                        ];
                        embeddedConfig.embedded_actions_visibility = [
                            ...this.embeddedInfos.visibleEmbeddedActions,
                        ];
                    }
                }
                await this.configHandler.setEmbeddedActionsConfig(embeddedConfig);
            }
        } else {
            await this.configHandler.setEmbeddedActionsConfig({
                embedded_visibility: showEmbedded,
            });
        }
    }

    /**
     * @param {number|false} actionId
     * @returns {Promise<void>}
     */
    async toggleActionVisibility(actionId) {
        const previous = this.embeddedInfos.visibleEmbeddedActions;
        const wasVisible = previous.includes(actionId);
        this.embeddedInfos.visibleEmbeddedActions = wasVisible
            ? this.embeddedInfos.visibleEmbeddedActions.filter((id) => id !== actionId)
            : [...this.embeddedInfos.visibleEmbeddedActions, actionId];
        await persistLayout(this, "visibleEmbeddedActions", previous, {
            embedded_actions_visibility: [...this.embeddedInfos.visibleEmbeddedActions],
        });
    }

    /** @returns {boolean} */
    _validateNewActionName() {
        const { newActionName, embeddedActions } = this.embeddedInfos;
        let problem;
        if (!newActionName) {
            problem = _t("A name for your new action is required.");
        } else if (embeddedActions.some(({ name }) => name === newActionName)) {
            problem = _t("An action with the same name already exists.");
        }
        if (problem) {
            this.notificationService.add(problem, { type: "danger" });
            return false;
        }
        return true;
    }

    /** @returns {Record<string, any>} */
    _newActionValues() {
        const actionConfig = /** @type {any} */ (this.env.config);
        const { newActionName, newActionIsShared, currentEmbeddedAction } =
            this.embeddedInfos;
        const {
            parent_action_id,
            action_id,
            parent_res_model,
            python_method,
            domain,
            context,
            group_ids,
        } = currentEmbeddedAction;
        /** @type {Record<string, any>} */
        const values = {
            parent_action_id: relationId(parent_action_id),
            parent_res_model,
            parent_res_id: this.env.searchModel.globalContext.active_id,
            user_id: newActionIsShared ? false : user.userId,
            is_deletable: true,
            default_view_mode: actionConfig.viewType,
            domain,
            context,
            group_ids,
            name: newActionName,
        };
        if (python_method) {
            values.python_method = python_method;
        } else {
            values.action_id = relationId(action_id) || actionConfig.actionId;
        }
        return values;
    }

    /** @returns {Promise<boolean>} */
    async saveNewAction() {
        if (!this._validateNewActionName()) {
            return false;
        }
        const { newActionName, newActionIsShared, currentEmbeddedAction } =
            this.embeddedInfos;
        const { parent_action_id, action_id } = currentEmbeddedAction;
        const values = this._newActionValues();
        const [embeddedActionId] = await this.orm.create("ir.embedded.actions", [
            values,
        ]);
        const description = `${newActionName}`;
        await this.env.searchModel.createNewFavorite({
            description,
            isDefault: true,
            isShared: newActionIsShared,
            embeddedActionId,
        });
        this.embeddedInfos.newActionIsShared = false;
        const enrichedNewEmbeddedAction = /** @type {EmbeddedAction} */ ({
            ...values,
            parent_action_id,
            action_id,
            id: embeddedActionId,
        });
        this.embeddedInfos.embeddedActions = [
            ...this.embeddedInfos.embeddedActions,
            enrichedNewEmbeddedAction,
        ];
        this.embeddedInfos.visibleEmbeddedActions = [
            ...this.embeddedInfos.visibleEmbeddedActions,
            embeddedActionId,
        ];
        const order = this.embeddedInfos.embeddedActions.map((el) => el.id);
        const saved = await this.configHandler.setEmbeddedActionsConfig({
            embedded_actions_visibility: [...this.embeddedInfos.visibleEmbeddedActions],
            embedded_actions_order: order,
        });
        if (!saved) {
            this.notificationService.add(
                _t("The action was created, but saving its position failed."),
                { type: "warning" },
            );
        }
        this.embeddedInfos.currentEmbeddedAction = enrichedNewEmbeddedAction;
        this.embeddedInfos.newActionName = _t("Custom %s", newActionName);
        return true;
    }

    /** @param {EmbeddedAction} action */
    confirmDelete(action) {
        const dialogProps = {
            title: _t("Warning"),
            body: action.user_id
                ? _t("Are you sure that you want to remove this embedded action?")
                : _t(
                      "This embedded action is global and will be removed for everyone.",
                  ),
            confirmLabel: _t("Delete"),
            confirm: async () => await this.removeAction(action),
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }

    /** @param {EmbeddedAction} action */
    async removeAction(action) {
        await this.orm.unlink("ir.embedded.actions", [action.id]);
        const { visibleEmbeddedActions, embeddedActions } = this.embeddedInfos;
        this.embeddedInfos.visibleEmbeddedActions = visibleEmbeddedActions.filter(
            (id) => id !== action.id,
        );
        this.embeddedInfos.embeddedActions = embeddedActions.filter(
            ({ id }) => id !== action.id,
        );
        const order = this.embeddedInfos.embeddedActions.map((el) => el.id);
        const saved = await this.configHandler.setEmbeddedActionsConfig({
            embedded_actions_visibility: [...this.embeddedInfos.visibleEmbeddedActions],
            embedded_actions_order: order,
        });
        if (!saved) {
            this.notificationService.add(
                _t("The action was deleted, but saving the bar's layout failed."),
                { type: "warning" },
            );
        }
        if (action.id === this.embeddedInfos.currentEmbeddedAction?.id) {
            this.actionService.doAction(relationId(action.parent_action_id), {
                additionalContext: this._actionContext(action),
                stackPosition: "replaceCurrentAction",
            });
        }
    }

    /** @param {EmbeddedAction} action */
    async openAction(action) {
        /** @type {Record<string, any>} */
        const context = {
            ...this._actionContext(action),
            current_embedded_action_id: action.id,
            parent_action_embedded_actions: this.embeddedInfos.embeddedActions,
            parent_action_id: relationId(action.parent_action_id),
        };
        this.actionService.doActionButton(
            {
                type: action.python_method ? "object" : "action",
                resId: context.active_id,
                name: action.python_method || relationId(action.action_id),
                resModel: action.parent_res_model,
                context,
                stackPosition: "replaceCurrentAction",
                viewType: action.default_view_mode,
            },
            { isEmbeddedAction: true },
        );
    }

    /** @param {(number|false)[]} order */
    sortActions(order) {
        const positions = new Map();
        for (const [index, id] of order.entries()) {
            if (!positions.has(id)) {
                positions.set(id, index);
            }
        }
        this.embeddedInfos.embeddedActions = [
            ...this.embeddedInfos.embeddedActions,
        ].sort((a, b) => {
            const indexA = positions.get(a.id) ?? -1;
            const indexB = positions.get(b.id) ?? -1;
            if (indexA === -1 && indexB === -1) {
                return 0;
            }
            if (indexA === -1) {
                return 1;
            }
            if (indexB === -1) {
                return -1;
            }
            return indexA - indexB;
        });
    }

    /**
     * @param {object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.previous]
     */
    async reorderFromDrop({ element, previous }) {
        const actions = this.embeddedInfos.embeddedActions;
        /** @param {HTMLElement} [el] */
        const positionOf = (el) => {
            const position = Number(el?.dataset.embeddedIndex);
            return Number.isInteger(position) && actions[position] ? position : -1;
        };
        const elementIndex = positionOf(element);
        if (elementIndex === -1) {
            return;
        }
        const previousIndex = positionOf(previous);
        const order = actions.map((el) => el.id);
        const elementId = order[elementIndex];
        const previousId = previousIndex === -1 ? undefined : order[previousIndex];
        const previousActions = [...actions];
        order.splice(elementIndex, 1);
        const insertAt = previousId === undefined ? 0 : order.indexOf(previousId) + 1;
        order.splice(insertAt, 0, elementId);
        this.sortActions(order);
        await persistLayout(this, "embeddedActions", previousActions, {
            embedded_actions_order: order,
        });
    }
}

/** @returns {EmbeddedActions | null} */
export function useEmbeddedActions() {
    const component = useComponent();
    const env = /** @type {import("@web/env").OdooEnv} */ (component.env);
    if (!(env.config?.embeddedActions?.length > 0)) {
        return null;
    }
    return new EmbeddedActions({
        env,
        orm: useService("orm"),
        notification: useService("notification"),
        dialog: useService("dialog"),
        action: useAction(),
    });
}
