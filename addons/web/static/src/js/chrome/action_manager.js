odoo.define('web.ActionManager', function (require) {
"use strict";

// const AbstractAction = require('web.AbstractAction');
const Context = require('web.Context');
const { _t, action_registry } = require('web.core');
const { redirect } = require('web.framework');
var pyUtils = require('web.py_utils');
const Widget = require('web.Widget');

const { Component, core } = owl;

let nextID = 1;

class ActionManagerPlugin {
    constructor(actionManager, env) {
        this.actionManager = actionManager;
        this.env = env;
    }
    async executeAction(/*action, options*/) {
        throw new Error(`ActionManagerPlugin for type ${this.type} doesn't implement executeAction.`);
    }
    rpc() {
        return this.env.services.rpc(...arguments);
    }
    _resolveLast() {
        return this.actionManager._resolveLast(...arguments);
    }
    loadState(/* state, options */) {}

    // FIXME: create a 'createController' or something function and get rid of these
    _getBreadcrumbs() {
        return this.actionManager._getBreadcrumbs(...arguments);
    }
    _getControllerStackIndex() {
        return this.actionManager._getControllerStackIndex(...arguments);
    }
    _pushController() {
        return this.actionManager._pushController(...arguments);
    }
    _nextID() {
        return this.actionManager._nextID(...arguments);
    }
    restoreController(controllerID) {
        return this.actionManager.restoreController(controllerID);
    }
    get currentStack() {
        return this.actionManager.currentStack;
    }
    get controllers() {
        return this.actionManager.controllers;
    }
    get actions() {
        return this.actionManager.actions;
    }
    doAction() {
        return this.actionManager.doAction(...arguments);
    }
    _getCurrentAction() {
        const currentState = this.getCurrentState();
        return currentState.main || {};
    }
    getCurrentState() {
        return this.actionManager.getCurrentState();
    }
}
ActionManagerPlugin.type = null;

class UrlActionPlugin extends ActionManagerPlugin {
    /**
     * Executes actions of type 'ir.actions.act_url', i.e. redirects to the
     * given url.
     *
     * @param {Object} action the description of the action to execute
     * @param {string} action.url
     * @param {string} [action.target] set to 'self' to redirect in the current page,
     *   redirects to a new page by default
     * @param {Object} options @see doAction for details
     */
    executeAction(action, options) {
        if (action.target === 'self') {
            redirect(action.url);
        } else {
            const w = window.open(action.url, '_blank');
            if (!w || w.closed || typeof w.closed === 'undefined') {
                const message = _t('A popup window has been blocked. You ' +
                    'may need to change your browser settings to allow ' +
                    'popup windows for this page.');
                this.env.services.notification.notify({
                    title: _t('Warning'),
                    type: 'danger',
                    message: message,
                    sticky: true,
                });
            }
            options.on_close();
        }
    }
}
UrlActionPlugin.type = 'ir.actions.act_url';

class ServerActionPlugin extends ActionManagerPlugin {
    /**
     * Executes actions of type 'ir.actions.server'.
     *
     * @param {Object} action the description of the action to execute
     * @param {integer} action.id the db ID of the action to execute
     * @param {Object} [action.context]
     * @param {Object} options @see doAction for details
     * @returns {Promise} resolved when the action has been executed
     */
    async executeAction(action, options) {
        const runActionProm = this.rpc({
            route: '/web/action/run',
            params: {
                action_id: action.id,
                context: action.context || {},
            },
        });
        action = await this._resolveLast(runActionProm);
        action = action || { type: 'ir.actions.act_window_close' };
        return this.actionManager.doAction(action, options);
    }
}
ServerActionPlugin.type = 'ir.actions.server';

class ClientActionPlugin extends ActionManagerPlugin {
    /**
     * Executes actions of type 'ir.actions.client'.
     *
     * @param {Object} action the description of the action to execute
     * @param {string} action.tag the key of the action in the action_registry
     * @param {Object} options @see doAction for details
     */
    async executeAction(action, options) {
        const ClientAction = action_registry.get(action.tag);
        if (!ClientAction) {
            console.error(`Could not find client action ${action.tag}`, action);
            return Promise.reject();
        } else {
            const proto = ClientAction.prototype;
            if (!(proto instanceof Component) && !(proto instanceof Widget)) {
                // the client action might be a function, which is executed and
                // whose returned value might be another action to execute
                const nextAction = ClientAction(this.env, action);
                if (nextAction) {
                    action = nextAction;
                    return this._resolveLast(this.doAction(action)); // _resolveLast necessary here??
                }
                return;
            }
        }

        const controllerID = this._nextID('controller');
        const index = this._getControllerStackIndex(options);
        options.breadcrumbs = this._getBreadcrumbs(this.currentStack.slice(0, index));
        options.controllerID = controllerID;
        action.controller = {
            actionID: action.jsID,
            Component: ClientAction,
            index: index,
            jsID: controllerID,
            options: options,
            // title: widget.getTitle(),
        };
        action.id = action.id || action.tag;
        this._pushController(action.controller);
    }
    /**
     * @override
     */
    loadState(state, options) {
        if (typeof state.action === 'string' && action_registry.contains(state.action)) {
            const action = {
                params: state,
                tag: state.action,
                type: 'ir.actions.client',
            };
            return this.doAction(action, options);
        }
    }
}
ClientActionPlugin.type = 'ir.actions.client';

class CloseActionPlugin extends ActionManagerPlugin {
    async executeAction(action, options) {
        let owlReload = true;
        const { main , dialog } = this.getCurrentState();
        if (dialog && !dialog.controller.isClosing) {
            if (dialog.controller.options && dialog.controller.options.on_close) {
                dialog.controller.options.on_close(action.infos);
                owlReload = false;
                dialog.controller.isClosing = true;
            }
        } else if (options.on_close) {
            options.on_close(action.infos);
            owlReload = false;
        }
        let pushCallBack = null;
        if (action.effect) {
            pushCallBack = () => {
                this.env.bus.trigger('show-effect', action.effect);
            }
        }
        const controller = main ? main.controller : null;
        if (controller) {
            controller.owlReload = owlReload;
            controller.options = controller.options || {};
            controller.options.on_success = options.on_success;
        }
        return this._pushController(controller, pushCallBack);
    }
}
CloseActionPlugin.type = 'ir.actions.act_window_close';


class ActionManager extends core.EventBus {
    static registerPlugin(Plugin) {
        if (!(Plugin.prototype instanceof ActionManagerPlugin)) {
            throw new Error('Plugin must be sublass of ActionManagerPlugin');
        }
        // TODO control Plugin.type
        ActionManager.Plugins[Plugin.type] = Plugin;
    }

    constructor(env) {
        super();
        this.env = env;
        this.env.bus.on('do-action', this, payload => {
            this.doAction(payload.action, payload.options);
        });
        // same as above except it is triggered on their reload
        // Made for clarity and transparency
        this.env.bus.on('legacy-reloaded', this, payload => {
            this.legacyLoaded(payload);
        });
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

        this.currentRequestID = 0;
        this.menus = null;
    }
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This function is called when the current controller is about to be
     * removed from the DOM, because a new one will be pushed, or an old one
     * will be restored. It ensures that the current controller can be left (for
     * instance, that it has no unsaved changes).
     *
     * @returns {Promise} resolved if the current controller can be left,
     *   rejected otherwise.
     */
    clearUncommittedChanges() {
        const mainState = this.getCurrentState().main;
        if (mainState && mainState.controller) {
            return mainState.controller.component.canBeRemoved();
        }
        return Promise.resolve();
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
        this.currentRequestID++;

        const defaultOptions = {
            additional_context: {},
            clear_breadcrumbs: false,
            on_close: function () {},
            on_reverse_breadcrumb: function () {},
            // pushState: true,
            replace_last_action: false,
            shouldReload: !options || !options.on_close,
        };
        options = Object.assign(defaultOptions, options);

        if (!options.shouldReload) {
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
            action = await this._resolveLast(loadActionProm);
        }
        if (!this.currentDialogController && action.target !== 'new') {
            await this.clearUncommittedChanges();
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
    async executeContextualActionTODONAME(params) {
        // cancel potential current rendering
        this.trigger('cancel');
        this.currentRequestID++;

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

        return this._resolveLast(prom).then(action => {
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
                const ctx = new Context(
                    _.object(_.reject(_.pairs(env.context), function (pair) {
                        return pair[0].match('^(?:(?:default_|search_default_|show_).+|' +
                                             '.+_view_ref|group_by|group_by_no_leaf|active_id|' +
                                             'active_ids|orderedBy)$') !== null;
                    }))
                );
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
        });
    }
    getStateFromController(controllerID) {
        const controller = this.controllers[controllerID];
        return {
            action: controller && this.actions[controller.actionID],
            controller: controller,
        };
    }
    /**
     * @returns {Object}
     */
    getCurrentState() {
        const res = {
            main: null,
            dialog: null,
            menuID: this.menuID,
        };
        const currentControllerID = this.currentStack[this.currentStack.length - 1];
        if (currentControllerID) {
            const {action, controller} = this.getStateFromController(currentControllerID);
            res.main = {
                action: action,
                controller: controller,
            }
         }
         if (this.currentDialogController) {
             res.dialog = {
                 action: this.getStateFromController(this.currentDialogController.jsID).action,
                 controller: this.currentDialogController,
              }
         }
         return res;
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
        if (!result && 'menu_id' in state) {
            const action = this.menus[state.menu_id].actionID;
            return this.doAction(action, state);
        }
        if (!result && ('home' in state || Object.keys(state).filter(key => key !== 'cids').length === 0)) {
            const { menuID , actionID } = this._getHomeAction();
            if (actionID) {
                return this.doAction(actionID, {menuID, clear_breadcrumbs: true});
            }
        }
        return result;
    }
    _getHomeAction() {
        const menuID = this.menus ? this.menus.root.children[0] : null;
        const actionID =  menuID ? this.menus[menuID].actionID : null;
        return { menuID, actionID };
    }
    /**
     * Restores a controller from the controllerStack and removes all
     * controllers stacked over the given controller (called when coming back
     * using the breadcrumbs).
     *
     * @param {string} controllerID
     */
    async restoreController(controllerID) {
        // TODO
        //  - move logic from act window (clear uncommitted changes + on _reverse_bc)
        //  - add hook onRestoreController (async)
        if (!controllerID) {
            controllerID = this.currentStack[this.currentStack.length - 1];
        }
        if (!this.currentDialogController) {
            await this.clearUncommittedChanges();
        }
        const { action, controller } = this.getStateFromController(controllerID);
        if (action) {
            if (controller.onReverseBreadcrumb) {
                await controller.onReverseBreadcrumb();
            }
            // TODO: call willRestore here?
            const plugin = this._getPlugin(action.type);
            if (plugin.restoreControllerHook) {
                return plugin.restoreControllerHook(action, controller);
            }
        }
        this._pushController(this.controllers[controllerID]);

        // AAB: AbstractAction should define a proper hook to execute code when
        // it is restored (other than do_show), and it should return a promise
        // var def;
        // if (action.on_reverse_breadcrumb) {
        //     def = action.on_reverse_breadcrumb();
        // }
        // return Promise.resolve(def).then(function () {
        //     return Promise.resolve(controller.widget.do_show()).then(function () {
        //         var index = _.indexOf(self.controllerStack, controllerID);
        //         self._pushController(controller, index);
        //     });
        // });
    }
    storeScrollPosition(scrollPosition) {
        const currentState = this.getCurrentState();
        if (currentState.main) {
            currentState.main.controller.scrollPosition = scrollPosition;
        }
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
        for (const controllerID in this.controllers) {
            const controller = this.controllers[controllerID];
            if (!usedActionIDs.includes(controller.actionID)) {
                if (controller.component) { // component may not exist yet
                    controller.component.destroy(true);
                }
                delete this.controllers[controllerID];
            }
        }
        const unusedActionIDs = Object.keys(this.actions).filter(actionID => {
            return !usedActionIDs.includes(actionID);
        });
        unusedActionIDs.forEach(actionID => delete this.actions[actionID]);
    }
    /**
     * Returns a description of the controllers in the given controller stack.
     * It is used to render the breadcrumbs. It is an array of Objects with keys
     * 'title' (what to display in the breadcrumbs) and 'controllerID' (the ID
     * of the corresponding controller, used to restore it when this part of the
     * breadcrumbs is clicked).
     *
     * @private
     * @param {string[]} controllerStack
     * @returns {Object[]}
     */
    _getBreadcrumbs(controllerStack) {
        return controllerStack.map(controllerID => {
            const controller = this.controllers[controllerID];
            const component = controller.component;
            return {
                controllerID: controllerID,
                title: component && component.title || this.actions[controller.actionID].name,
            };
        });
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
        return plugin.executeAction(action, options);
        //     // case 'ir.actions.act_window_close':
        //     //     return this._executeCloseAction(action);
    }
    _nextID(type) {
        return `${type}${nextID++}`;
    }
    legacyLoaded(payload, initialLoading) {
        const { action } = this.getCurrentState().main;
        Object.assign(action, payload.commonState);
        action.controllerState = Object.assign({}, action.controllerState, payload.controllerState);
    }
    rpc() {
        return this.env.services.rpc(...arguments);
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
        // action.pushState = options.pushState;

        return action;
    }
    /**
     * Updates the pendingStack with a given controller. It triggers a rendering
     * of the ActionManager with that controller as active controller (last one
     * of the stack).
     *
     * @private
     * @param {Object} controller
     */
    _pushController(controller, cb) {
        if (!controller) {
            this.trigger('update', {
                main: null,
                dialog: null,
                onSuccess: () => {
                    this.currentDialogController = null;
                },
                onFail: () => {},
            });
            return;
        }
        this.controllers[controller.jsID] = controller;
        const action = this.actions[controller.actionID];

        const { main, dialog } = this.getCurrentState();
        let newMain = null;
        let newDialog = null;
        let newMenuID;
        if (action.target !== 'new') {
            newMain = {};
            newMain.reload = 'owlReload' in controller ? controller.owlReload : true;
            delete controller.owlReload;
            newMain.action = action;
            newMain.controller = controller;
            newMenuID = controller.options && controller.options.menuID || this.menuID;
        } else {
            if (main) {
                newMain = main;
                newMain.reload = false;
            }
            newDialog = {};
            newDialog.action = action;
            newDialog.controller = controller;
            newMenuID = this.currentMenuID;
        }
        if (dialog) {
            const oldCt = dialog.controller;
            if (newDialog) {
                const newCt = newDialog.controller;
                newCt.options.on_close = oldCt.options.on_close;
            } else {
                newMain.reload = oldCt.options.shouldReload;
            }
        }
        const nextStack = this.currentStack.slice(0, newMain ? newMain.controller.index : 0);
        if (newMain) {
            nextStack.push(newMain.controller.jsID);
        }
        const onFail = () => {
            if (action.target !== 'new') {
                if (newMain.controller.options && newMain.controller.options.on_fail) {
                    newMain.controller.options.on_fail();
                }
            } else {
                if (newDialog.controller.options && newDialog.controller.options.on_fail) {
                    newDialog.controller.options.on_fail();
                }
            }
        };
        const onSuccess = (mainComponent, dialogComponent) => {
            if (action.target !== 'new') {
                newMain.controller.component = mainComponent;
                this.currentDialogController = newDialog;
                this.menuID = newMenuID || this.menuID;
                // FIXME: we could probably get rid of this on_reverse_breadcrumb stuff, and use
                // the willRestore hook instead (but some client actions would need to be adapted)
                if (controller.options && controller.options.on_reverse_breadcrumb) {
                    const currentControllerID = this.currentStack[this.currentStack.length - 1];
                    if (currentControllerID) {
                        const currentController = this.controllers[currentControllerID];
                        currentController.onReverseBreadcrumb = controller.options.on_reverse_breadcrumb;
                    }
                }

                // always close dialogs when the current controller changes
                // use case: have a controller that opens a dialog, and from this dialog, have a
                // link/button to perform an action that will be stacked in the breadcrumbs
                // (for instance, a many2one in readonly)
                this.env.bus.trigger('close_dialogs');

                // store the action into the sessionStorage so that it can be fully restored on F5
                this.env.services.session_storage.setItem('current_action', action._originalAction);
            } else {
                newDialog.controller.component = dialogComponent;
                this.currentDialogController = newDialog.controller;
            }
            if (controller && controller.options && controller.options.on_success) {
                controller.options.on_success();
            }
            this.currentStack = nextStack;
            this._cleanActions();

            // FIXME: for lazy loaded controllers... we must find a better solution
            if (cb) {
                cb();
            }
        };
        const payload = {
            main: newMain,
            dialog: newDialog,
            fullscreen: this.getFullScreen(nextStack),
            menuID: newMenuID,
            onSuccess: onSuccess,
            onFail: onFail,
        };
        this.trigger('update', payload);
    }
    getFullScreen(nextStack) {
        return nextStack.find(controllerID => {
            const controller = this.controllers[controllerID];
            return this.actions[controller.actionID].target === 'fullscreen';
        });
    }
    /**
     * Wraps a promise to resolve/reject it when it is resolved/rejected: iff
     * the pending controller hasn't changed between the moment when the request
     * was initiated and the moment it is completed. If the controller changed,
     * the returned promise stays pending forever.
     *
     * TODO: find a better name, and validate this solution (!= DropPrevious)
     * TODO: memory leak?
     *
     * @private
     * @param {Promise} promise
     * @returns {Promise}
     */
    _resolveLast(promise) {
        const currentRequestID = this.currentRequestID;
        return new Promise((resolve, reject) => {
            promise.then(result => {
                if (currentRequestID === this.currentRequestID) {
                    resolve(result);
                }
            });
            promise.guardedCatch(reason => {
                if (currentRequestID === this.currentRequestID) {
                    reject(reason);
                }
            });
        });
    }
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
}
ActionManager.Plugins = {};
ActionManager.AbstractPlugin = ActionManagerPlugin;

ActionManager.registerPlugin(ServerActionPlugin);
ActionManager.registerPlugin(ClientActionPlugin);
ActionManager.registerPlugin(UrlActionPlugin);
ActionManager.registerPlugin(CloseActionPlugin);

return ActionManager;

});
