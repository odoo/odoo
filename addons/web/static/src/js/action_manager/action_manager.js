odoo.define('web.ActionManager', function (require) {
"use strict";

const ActionAbstractPlugin = require('web.ActionAbstractPlugin');
const Context = require('web.Context');
const { action_registry } = require('web.core');

var pyUtils = require('web.py_utils');
const { TransactionalChain } = require('web.concurrency');

const { core } = owl;

class ActionManager extends core.EventBus {
    static registerPlugin(Plugin) {
        if (!(Plugin.prototype instanceof ActionAbstractPlugin)) {
            throw new Error('Plugin must be sublass of ActionAbstractPlugin');
        }
        // TODO control Plugin.type
        ActionManager.Plugins[Plugin.type] = Plugin;
    }
    constructor(env) {
        super();
        this.env = env;
        this._transaction = new TransactionalChain();
        this.env.bus.on('do-action', this, payload => {
            // Calling on_success and on_fail is necessary for legacy
            // compatibility. Some widget may need to do stuff when a report
            // has been printed
            return this.doAction(payload.action, payload.options)
                .then(() => {
                    if (payload.on_success) {
                        payload.on_success();
                    }
                })
                .guardedCatch(() => {
                    if (payload.on_fail) {
                        payload.on_fail();
                    }
                });
        });
        // Before switching views, an event is triggered
        // containing the state of the current controller
        this.env.bus.on('legacy-export-state', this, this._onLegacyExportState);
        this.env.bus.on('history-back', this, this._onHistoryBack);
        this.plugins = new WeakMap();

        // handled by the ActionManager (either stacked in the current window,
        // or opened in dialogs)
        this.actions = {};

        // 'controllers' is an Object that registers the alive controllers
        // linked registered actions, a controller being an Object with keys
        // (amongst others) 'jsID' (a local identifier) and 'widget' (the
        // instance of the controller's widget)
        this.controllers = {};

        // 'controllerStack' is the stack of ids of the controllers currently
        // displayed in the current window
        this.currentStack = [];
        this.currentDialogController = null;
    }
    //--------------------------------------------------------------------------
    // Main API
    //--------------------------------------------------------------------------
    commit(newStack, newDialog, onCommit) {
        this.currentStack = newStack.map(obj => {
            return obj.controller.jsID;
        });
        let controller, action;
        if (!newDialog && newStack.length) {
            const main = newStack[newStack.length - 1];
            controller = main.controller;
            action = main.action;
            // always close dialogs when the current controller changes
            // use case: have a controller that opens a dialog, and from this dialog, have a
            // link/button to perform an action that will be stacked in the breadcrumbs
            // (for instance, a many2one in readonly)
            this.env.bus.trigger('close_dialogs');
            this.currentDialogController = null;

            // store the action into the sessionStorage so that it can be fully restored on F5
            this.env.services.session_storage.setItem('current_action', action._originalAction);
        } else if (newDialog) {
            controller = newDialog.controller;
            this.currentDialogController = controller;
        }

        if (controller && controller.options && controller.options.on_success) {
            controller.options.on_success();
            controller.options.on_success = null;
        }
        if (onCommit) {
            onCommit();
        }
        this._cleanActions();
    }
    /**
     * Executes Odoo actions, given as an ID in database, an xml ID, a client
     * action tag or an action descriptor.
     *
     * @param {number|string|Object} action the action to execute
     * @param {Object} [options] available options detailed below
     * @param {Object} [options.additional_context={}] additional context to be
     *   merged with the action's context.
     * @param {boolean} [options.clear_breadcrumbs=false] set to true to clear
     *   the breadcrumbs history list
     * @param {Function} [options.on_close] callback to be executed when the
     *   current action is active again (typically, if the new action is
     *   executed in target="new", on_close will be executed when the dialog is
     *   closed, if the current controller is still active)
     * @param {Function} [options.on_reverse_breadcrumb] callback to be executed
     *   whenever an anterior breadcrumb item is clicked on
     * @param {boolean} [options.pushState=true] set to false to prevent the
     *   ActionManager from pushing the state when the action is executed (this
     *   is useful when we come from a loadState())
     * @param {boolean} [options.replace_last_action=false] set to true to
     *   replace last part of the breadcrumbs with the action
     * @return {Promise<Object>} resolved with the action when the action is
     *   loaded and appended to the DOM ; rejected if the action can't be
     *   executed (e.g. if doAction has been called to execute another action
     *   before this one was complete).
     */
    async doAction(action, options) {
        // cancel potential current rendering
        this.trigger('cancel');

        const defaultOptions = {
            additional_context: {},
            clear_breadcrumbs: false,
            on_close: function () {},
            on_reverse_breadcrumb: function () {},
            replace_last_action: false,
        };
        options = Object.assign(defaultOptions, options);

        if (options && options.on_close) {
            console.warn('doAction: on_close callback is deprecated');
        }

        // build or load an action descriptor for the given action
        // TODO maybe registry can do this
        if (typeof action === 'string' && action_registry.contains(action)) {
            // action is a tag of a client action
            action = { type: 'ir.actions.client', tag: action };
        } else if (typeof action === 'string' || typeof action === 'number') {
            // action is an id or xml id
            const loadActionProm = this.env.dataManager.load_action(action, {
                active_id: options.additional_context.active_id,
                active_ids: options.additional_context.active_ids,
                active_model: options.additional_context.active_model,
            });
            action = await this._transaction.add(loadActionProm);
        }
        if (action.target !== 'new') {
            await this._clearUncommittedChanges();
        }
        // action.target 'main' is equivalent to 'current' except that it
        // also clears the breadcrumbs
        options.clear_breadcrumbs = action.target === 'main' || options.clear_breadcrumbs;

        action = this._preprocessAction(action, options);
        this.actions[action.jsID] = action;
        return this._handleAction(action, options);
    }
    /**
     * Handler for event 'execute_action', which is typically called when a
     * button is clicked. The button may be of type 'object' (call a given
     * method of a given model) or 'action' (execute a given action).
     * Alternatively, the button may have the attribute 'special', and in this
     * case an 'ir.actions.act_window_close' is executed.
     *
     * @param {Object} params
     * @param {Object} params.action_data typically, the html attributes of the
     *   button extended with additional information like the context
     * @param {Object} [params.action_data.special=false]
     * @param {Object} [params.action_data.type] 'object' or 'action', if set
     * @param {Object} params.env
     * @param {function} [params.on_closed]
     * @param {function} [params.on_fail]
     * @param {function} [params.on_success]
     */
    async executeInFlowAction(params) {
        // cancel potential current rendering
        this.trigger('cancel');

        const actionData = params.action_data;
        const env = params.env;
        const context = new Context(env.context, actionData.context || {});
        const recordID = env.currentID || null; // pyUtils handles null value, not undefined
        let prom;

        // determine the action to execute according to the actionData
        if (actionData.special) {
            prom = Promise.resolve({
                type: 'ir.actions.act_window_close',
                infos: { special: true },
            });
        } else if (actionData.type === 'object') {
            // call a Python Object method, which may return an action to execute
            let args = recordID ? [[recordID]] : [env.resIDs];
            if (actionData.args) {
                try {
                    // warning: quotes and double quotes problem due to json and xml clash
                    // maybe we should force escaping in xml or do a better parse of the args array
                    const additionalArgs = JSON.parse(actionData.args.replace(/'/g, '"'));
                    args = args.concat(additionalArgs);
                } catch (e) {
                    console.error("Could not JSON.parse arguments", actionData.args);
                }
            }
            prom = this.rpc({
                route: '/web/dataset/call_button',
                params: {
                    args: args,
                    kwargs: {context: context.eval()},
                    method: actionData.name,
                    model: env.model,
                },
            });
        } else if (actionData.type === 'action') {
            // FIXME: couldn't we directly call doAction?
            // execute a given action, so load it first
            const additionalContext = Object.assign(pyUtils.eval('context', context), {
                active_model: env.model,
                active_ids: env.resIDs,
                active_id: recordID,
            });
            prom = this.env.dataManager.load_action(actionData.name, additionalContext);
        } else {
            prom = Promise.reject();
        }

        let action = await this._transaction.add(prom);
        // show effect if button have effect attribute
        // rainbowman can be displayed from two places: from attribute on a button or from python
        // code below handles the first case i.e 'effect' attribute on button.
        let effect = false;
        if (actionData.effect) {
            effect = pyUtils.py_eval(actionData.effect);
        }

        if (action && action.constructor === Object) {
            // filter out context keys that are specific to the current action, because:
            //  - wrong default_* and search_default_* values won't give the expected result
            //  - wrong group_by values will fail and forbid rendering of the destination view
            this.rejectKeysRegex = this.rejectKeysRegex || new RegExp(`\
                ^(?:(?:default_|search_default_|show_).+|\
                .+_view_ref|group_by|group_by_no_leaf|active_id|\
                active_ids|orderedBy)$`
            );
            const oldCtx = {};
            for (const key in env.context) {
                if (!key.match(this.rejectKeysRegex)) {
                    oldCtx[key] = env.context[key];
                }
            }
            const ctx = new Context(oldCtx);
            ctx.add(actionData.context || {});
            ctx.add({active_model: env.model});
            if (recordID) {
                ctx.add({
                    active_id: recordID,
                    active_ids: [recordID],
                });
            }
            ctx.add(action.context || {});
            action.context = ctx;
            // in case an effect is returned from python and there is already an effect
            // attribute on the button, the priority is given to the button attribute
            action.effect = effect || action.effect;
        } else {
            // if action doesn't return anything, but there is an effect
            // attribute on the button, display rainbowman
            action = {
                effect: effect,
                type: 'ir.actions.act_window_close',
            };
        }
        let options = {
            on_close: params.on_closed,
            on_success: params.on_success,
            on_fail: params.on_fail,
        };
        if (this.env.device.isMobile && actionData.mobile) {
            options = Object.assign({}, options, actionData.mobile);
        }
        action.flags = Object.assign({}, action.flags, { searchPanelDefaultNoFilter: true });
        return this.doAction(action, options);
    }
    /**
     * @param {Object} state
     * @returns {Promise}
     */
    async loadState(state, options) {
        const pluginKeys = Object.keys(ActionManager.Plugins);
        const plugins = pluginKeys.map(key => this._getPlugin(key));
        options = Object.assign({ clear_breadcrumbs: true }, options);
        let result;
        for (const plugin of plugins) {
            result = plugin.loadState(state, options);
            if (result) {
                break;
            }
        }
        if (!result) {
            // no suitable plugin or state
            // the caller must handle this
            return null;
        }
        return result;
    }
    /**
     * Restores a controller from the controllerStack and removes all
     * controllers stacked over the given controller (called when coming back
     * using the breadcrumbs).
     *
     * @param {string} controllerID
     */
    async restoreController(controllerID) {
        if (!controllerID) {
            controllerID = this.currentStack[this.currentStack.length - 1];
        }
        await this._clearUncommittedChanges();
        const { action, controller } = this._getStateFromController(controllerID);
        if (action) {
            if (controller.onReverseBreadcrumb) {
                await controller.onReverseBreadcrumb();
            }
            const plugin = this._getPlugin(action.type);
            if (plugin.restoreControllerHook) {
                return plugin.restoreControllerHook(action, controller);
            }
        }
        this.pushControllers([this.controllers[controllerID]]);
    }
    rollBack(newStack, newDialog) {
        let controller;
        if (!newDialog) {
            const main = newStack[newStack.length - 1];
            controller = main.controller;
        } else {
            controller = newDialog.controller;
        }
        if (controller.options && controller.options.on_fail) {
            controller.options.on_fail();
        }
        this.restoreController();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Object}
     */
    getCurrentState() {
        const res = {
            main: null,
            dialog: null,
        };
        const currentControllerID = this.currentStack[this.currentStack.length - 1];
        if (currentControllerID) {
            const {action, controller} = this._getStateFromController(currentControllerID);
            res.main = {
                action: action,
                controller: controller,
            }
         }
         if (this.currentDialogController) {
             res.dialog = {
                 action: this._getStateFromController(this.currentDialogController.jsID).action,
                 controller: this.currentDialogController,
              }
         }
         return res;
    }
    makeBaseController(action, params) {
        const controllerID = params.controllerID || this._nextID('controller');
        const index = this._getControllerStackIndex(params);
        const newController = {
            actionID: action.jsID,
            Component: params.Component,
            index: index,
            jsID: controllerID,
        };
        action.controller = newController;
        this.controllers[controllerID] = newController;
        return newController;
    }
    rpc() {
        return this.env.services.rpc(...arguments);
    }
    /**
     * Updates the pendingStack with a given controller. It triggers a rendering
     * of the ActionManager with that controller as active controller (last one
     * of the stack).
     *
     * @private
     * @param {Object} controller
     */
    pushControllers(controllerArray, options) {
        let nextStack = this.currentStack;
        if (controllerArray && controllerArray.length > 1) {
            nextStack = nextStack.slice(0, controllerArray[0].index || 0);
            for (const cont of controllerArray) {
                nextStack.push(cont.jsID);
            }
        }
        const controller = controllerArray && controllerArray[controllerArray.length -1];
        if (!controller) {
            this.trigger('update', {
                controllerStack: [],
                dialog: null,
                onCommit: options && options.onCommit,
                doOwlReload: options && 'doOwlReload' in options ? options.doOwlReload : true,
            });
            return;
        }
        const action = this.actions[controller.actionID];

        let dialog;
        if (action.target !== 'new') {
            nextStack = nextStack.slice(0, controller.index || 0);
            nextStack.push(controller.jsID);
            dialog = null;
            if (controller.options && controller.options.on_reverse_breadcrumb) {
               const currentControllerID = this.currentStack[this.currentStack.length - 1];
               if (currentControllerID) {
                   const currentController = this.controllers[currentControllerID];
                   currentController.onReverseBreadcrumb = controller.options.on_reverse_breadcrumb;
               }
            }
        } else {
            dialog = { action , controller };
            if (this.currentDialogController) {
                const dialogController = this.currentDialogController;
                controller.options.on_close = dialogController.options.on_close;
            }
        }

        const controllerStack = nextStack.map(jsID => {
            const controller = this.controllers[jsID];
            const action = this.actions[controller.actionID];
            return { action, controller };
        });
        this.trigger('update', {
            controllerStack,
            dialog,
            onCommit: options && options.onCommit,
            doOwlReload: options && 'doOwlReload' in options ? options.doOwlReload : true,
        });
    }
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Cleans this.actions and this.controllers according to the current stack.
     *
     * @private
     */
    _cleanActions() {
        const usedActionIDs = this.currentStack.map(controllerID => {
            return this.controllers[controllerID].actionID;
        });
        if (this.currentDialogController) {
            usedActionIDs.push(this.currentDialogController.actionID);
        }
        const cleanedControllers = [];
        for (const controllerID in this.controllers) {
            const controller = this.controllers[controllerID];
            if (!usedActionIDs.includes(controller.actionID)) {
                cleanedControllers.push(controllerID);
                delete this.controllers[controllerID];
            }
        }
        const unusedActionIDs = Object.keys(this.actions).filter(actionID => {
            return !usedActionIDs.includes(actionID);
        });
        this.trigger('controller-cleaned', cleanedControllers);
        unusedActionIDs.forEach(actionID => delete this.actions[actionID]);
    }
    /**
     * This function is called when the current controller is about to be
     * removed from the DOM, because a new one will be pushed, or an old one
     * will be restored. It ensures that the current controller can be left (for
     * instance, that it has no unsaved changes).
     *
     * @returns {Promise} resolved if the current controller can be left,
     *   rejected otherwise.
     */
    _clearUncommittedChanges() {
        if (this.currentStack.length) {
            return new Promise((resolve) => {
                this.trigger('clear-uncommitted-changes', resolve);
            });
        }
    }
    /**
     * Returns the index where a controller should be inserted in the controller
     * stack according to the given options. By default, a controller is pushed
     * on the top of the stack.
     *
     * @private
     * @param {options} [options.clear_breadcrumbs=false] if true, insert at
     *   index 0 and remove all other controllers
     * @param {options} [options.index=null] if given, that index is returned
     * @param {options} [options.replace_last_action=false] if true, replace the
     *   last controller of the stack
     * @returns {integer} index
     */
    _getControllerStackIndex(options) {
        let index;
        if ('index' in options) {
            index = options.index;
        } else if (options.clear_breadcrumbs) {
            index = 0;
        } else if (options.replace_last_action) {
            index = this.currentStack.length - 1;
        } else {
            index = this.currentStack.length;
        }
        return index;
    }
    _getPlugin(actionType) {
        const Plugin = ActionManager.Plugins[actionType];
        if (!Plugin) {
            console.error(`The ActionManager can't handle actions of type ${actionType}`);
            return null;
        }
        let plugin = this.plugins.get(Plugin);
        if (!plugin) {
            plugin = new Plugin(this, this.env);
            this.plugins.set(Plugin, plugin);
        }
        return plugin;
    }
    _getStateFromController(controllerID) {
        const controller = this.controllers[controllerID];
        return {
            action: controller && this.actions[controller.actionID],
            controller: controller,
        };
    }
    /**
     * Dispatches the given action to the corresponding handler to execute it,
     * according to its type. This function can be overridden to extend the
     * range of supported action types.
     *
     * @private
     * @param {Object} action
     * @param {string} action.type
     * @param {Object} options
     * @returns {Promise} resolved when the action has been executed ; rejected
     *   if the type of action isn't supported, or if the action can't be
     *   executed
     */
    _handleAction(action, options) {
        if (!action.type) {
            console.error(`No type for action ${action}`);
            return Promise.reject();
        }
        const plugin = this._getPlugin(action.type);
        if (!plugin) {return Promise.reject();}
        try {
            return plugin.executeAction(action, options);
        } catch (e) {
            if (e.message === 'Plugin Error') {
                return this.restoreController();
            } else {
                throw e;
            }
        }
    }
    _nextID(type) {
        return `${type}${this.constructor.nextID++}`;
    }
    /**
     * Preprocesses the action before it is handled by the ActionManager
     * (assigns a JS id, evaluates its context and domains...).
     *
     * @param {Object} action
     * @param {Object} options
     * @returns {Object} shallow copy of action with some new/updated values
     */
    _preprocessAction(action, options) {
        action = Object.assign({}, action);

        // ensure that the context and domain are evaluated
        var context = new Context(this.env.session.user_context, options.additional_context, action.context);
        action.context = pyUtils.eval('context', context);
        if (action.domain) {
            action.domain = pyUtils.eval('domain', action.domain, action.context);
        }
        action._originalAction = JSON.stringify(action);
        action.jsID = this._nextID('action');
        return action;
    }
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Goes back in the history: if a controller is opened in a dialog, closes
     * the dialog, otherwise, restores the second to last controller from the
     * stack.
     *
     * @private
     */
    _onHistoryBack() {
        if (this.currentDialogController) {
            this.doAction({type: 'ir.actions.act_window_close'});
        } else {
            const length = this.currentStack.length;
            if (length > 1) {
                this.restoreController(this.currentStack[length - 2]);
            }
        }
    }
    _onLegacyExportState(payload) {
        const { action } = this.getCurrentState().main;
        Object.assign(action, payload.commonState);
        action.controllerState = Object.assign({}, action.controllerState, payload.controllerState);
    }
}
ActionManager.nextID = 1;
ActionManager.Plugins = {};

return ActionManager;

});
