odoo.define('web.ActionManager', function (require) {
"use strict";

/**
 * ActionManager
 *
 * The ActionManager is one of the centrepieces in the WebClient architecture.
 * Its role is to makes sure that Odoo actions are properly started and
 * coordinated.
 */

var AbstractAction = require('web.AbstractAction');
var concurrency = require('web.concurrency');
var Context = require('web.Context');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var framework = require('web.framework');
var pyUtils = require('web.py_utils');
var Widget = require('web.Widget');

var _t = core._t;
var ActionManager = Widget.extend({
    className: 'o_action_manager',
    custom_events: {
        breadcrumb_clicked: '_onBreadcrumbClicked',
        history_back: '_onHistoryBack',
        push_state: '_onPushState',
        redirect: '_onRedirect',
    },

    /**
     * @override
     * @param {Object} [userContext={}]
     */
    init: function (parent, userContext) {
        this._super.apply(this, arguments);
        this.userContext = userContext || {};

        // use a DropPrevious to drop previous actions when multiple actions are
        // run simultaneously
        this.dp = new concurrency.DropPrevious();

        // 'actions' is an Object that registers the actions that are currently
        // handled by the ActionManager (either stacked in the current window,
        // or opened in dialogs)
        this.actions = {};

        // 'controllers' is an Object that registers the alive controllers
        // linked registered actions, a controller being Object with keys
        // (amongst others) 'jsID' (a local identifier) and 'widget' (the
        // instance of the controller's widget)
        this.controllers = {};

        // 'controllerStack' is the stack of ids of the controllers currently
        // displayed in the current window
        this.controllerStack = [];

        // 'currentDialogController' is the current controller opened in a
        // dialog (i.e. coming from an action with target='new')
        this.currentDialogController = null;
    },
    /**
     * Called each time the action manager is attached into the DOM.
     */
    on_attach_callback: function () {
        this.isInDOM = true;
        var currentController = this.getCurrentController();
        if (currentController) {
            currentController.widget.on_attach_callback();
        }
    },
    /**
     * Called each time the action manager is detached from the DOM.
     */
    on_detach_callback: function () {
        this.isInDOM = false;
        var currentController = this.getCurrentController();
        if (currentController) {
            currentController.widget.on_detach_callback();
        }
    },

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
    clearUncommittedChanges: function () {
        var currentController = this.getCurrentController();
        if (currentController) {
            return currentController.widget.canBeRemoved();
        }
        return Promise.resolve();
    },
    /**
     * This is the entry point to execute Odoo actions, given as an ID in
     * database, an xml ID, a client action tag or an action descriptor.
     *
     * @param {number|string|Object} action the action to execute
     * @param {Object} [options]
     * @param {Object} [options.additional_context] additional context to be
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
    doAction: function (action, options) {
        var self = this;
        options = _.defaults({}, options, {
            additional_context: {},
            clear_breadcrumbs: false,
            on_close: function () {},
            on_reverse_breadcrumb: function () {},
            pushState: true,
            replace_last_action: false,
        });

        // build or load an action descriptor for the given action
        var def;
        if (_.isString(action) && core.action_registry.contains(action)) {
            // action is a tag of a client action
            action = { type: 'ir.actions.client', tag: action };
        } else if (_.isNumber(action) || _.isString(action)) {
            // action is an id or xml id
            def = this._loadAction(action, {
                active_id: options.additional_context.active_id,
                active_ids: options.additional_context.active_ids,
                active_model: options.additional_context.active_model,
            }).then(function (result) {
                action = result;
            });
        }

        return this.dp.add(Promise.resolve(def)).then(function () {
            // action.target 'main' is equivalent to 'current' except that it
            // also clears the breadcrumbs
            options.clear_breadcrumbs = action.target === 'main' ||
                                        options.clear_breadcrumbs;

            self._preprocessAction(action, options);

            return self._handleAction(action, options).then(function () {
                // now that the action has been executed, force its 'pushState'
                // flag to 'true', as we don't want to prevent its controller
                // from pushing its state if it changes in the future
                action.pushState = true;

                return action;
            });
        }).then(function(action) {
            self.trigger_up('webclient_started');
            return action;
        });
    },
    /**
     * Compatibility with client actions that are still using do_push_state.
     *
     * @todo: convert all of them to trigger_up('push_state') instead.
     * @param {Object} state
     */
    do_push_state: function (state) {
        this.trigger_up('push_state', {state: state});
    },
    /**
     * Returns the action of the last controller in the controllerStack, i.e.
     * the action of the currently displayed controller in the main window (not
     * in a dialog), and null if there is no controller in the stack.
     *
     * @returns {Object|null}
     */
    getCurrentAction: function () {
        var controller = this.getCurrentController();
        return controller ? this.actions[controller.actionID] : null;
    },
    /**
     * Returns the last controller in the controllerStack, i.e. the currently
     * displayed controller in the main window (not in a dialog), and
     * null if there is no controller in the stack.
     *
     * @returns {Object|null}
     */
    getCurrentController: function () {
        var currentControllerID = _.last(this.controllerStack);
        return currentControllerID ? this.controllers[currentControllerID] : null;
    },
    /**
     * Updates the UI according to the given state, for instance, executes a new
     * action, or updates the state of the current action.
     *
     * @param {Object} state
     * @param {integer|string} [state.action] the action to execute (given its
     *   id or tag for client actions)
     * @returns {Promise} resolved when the UI has been updated
     */
    loadState: function (state) {
        var action;
        if (!state.action) {
            return Promise.resolve();
        }
        if (_.isString(state.action) && core.action_registry.contains(state.action)) {
            action = {
                params: state,
                tag: state.action,
                type: 'ir.actions.client',
            };
        } else {
            action = state.action;
        }
        return this.doAction(action, {
            clear_breadcrumbs: true,
            pushState: false,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Appends the given controller to the DOM and restores its scroll position.
     * Also updates the control panel.
     *
     * @private
     * @param {Object} controller
     */
    _appendController: function (controller) {
        dom.append(this.$el, controller.widget.$el, {
            in_DOM: this.isInDOM,
            callbacks: [{widget: controller.widget}],
        });

        if (controller.scrollPosition) {
            this.trigger_up('scrollTo', controller.scrollPosition);
        }
    },
    /**
     * Closes the current dialog, if any. Because we listen to the 'closed'
     * event triggered by the dialog when it is closed, this also destroys the
     * embedded controller and removes the reference to the corresponding action.
     * This also executes the 'on_close' handler in some cases, and may also
     * provide infos for closing this dialog.
     *
     * @private
     * @param {Object} options
     * @param {Object} [options.infos] some infos related to the closing the
     *   dialog.
     * @param {boolean} [options.silent=false] if true, the 'on_close' handler
     *   won't be called ; this is in general the case when the current dialog
     *   is closed because another action is opened, so we don't want the former
     *   action to execute its handler as it won't be displayed anyway
     */
    _closeDialog: function (options) {
        if (this.currentDialogController) {
            this.currentDialogController.dialog.destroy(options);
        }
    },
    /**
     * Detaches the current controller from the DOM and stores its scroll
     * position, in case we'd come back to that controller later.
     *
     * @private
     */
    _detachCurrentController: function () {
        var currentController = this.getCurrentController();
        if (currentController) {
            currentController.scrollPosition = this._getScrollPosition();
            dom.detach([{widget: currentController.widget}]);
        }
    },
    /**
     * Executes actions for which a controller has to be appended to the DOM,
     * either in the main content (target="current", by default), or in a dialog
     * (target="new").
     *
     * @private
     * @param {Object} action
     * @param {widget} action.controller a Widget instance to append to the DOM
     * @param {string} [action.target="current"] set to "new" to render the
     *   controller in a dialog
     * @param {Object} options @see doAction for details
     * @returns {Promise} resolved when the controller is started and appended
     */
    _executeAction: function (action, options) {
        var self = this;
        this.actions[action.jsID] = action;

        if (action.target === 'new') {
            return this._executeActionInDialog(action, options);
        }

        var controller = self.controllers[action.controllerID];
        return this.clearUncommittedChanges()
            .then(function () {
                return self.dp.add(self._startController(controller));
            })
            .then(function () {
                if (self.currentDialogController) {
                    self._closeDialog({ silent: true });
                }

                // store the optional 'on_reverse_breadcrumb' handler
                // AAB: store it on the AbstractAction instance, and call it
                // automatically when the action is restored
                if (options.on_reverse_breadcrumb) {
                    var currentAction = self.getCurrentAction();
                    if (currentAction) {
                        currentAction.on_reverse_breadcrumb = options.on_reverse_breadcrumb;
                    }
                }

                // update the internal state and the DOM
                self._pushController(controller);

                // store the action into the sessionStorage so that it can be
                // fully restored on F5
                self.call('session_storage', 'setItem', 'current_action', action._originalAction);

                return action;
            })
            .guardedCatch(function () {
                self._removeAction(action.jsID);
            });
    },
    /**
     * Executes actions with attribute target='new'. Such actions are rendered
     * in a dialog.
     *
     * @private
     * @param {Object} action
     * @param {Object} options @see doAction for details
     * @returns {Promise} resolved when the controller is rendered inside a
     *   dialog appended to the DOM
     */
    _executeActionInDialog: function (action, options) {
        var self = this;
        var controller = this.controllers[action.controllerID];
        var widget = controller.widget;

        return this._startController(controller).then(function (controller) {
            var prevDialogOnClose;
            if (self.currentDialogController) {
                prevDialogOnClose = self.currentDialogController.onClose;
                self._closeDialog({ silent: true });
            }

            controller.onClose = prevDialogOnClose || options.on_close;
            var dialog = new Dialog(self, _.defaults({}, options, {
                buttons: [],
                dialogClass: controller.className,
                title: action.name,
                size: action.context.dialog_size,
            }));
            /**
             * @param {Object} [options={}]
             * @param {Object} [options.infos] if provided and `silent` is
             *   unset, the `on_close` handler will pass this information,
             *   which gives some context for closing this dialog.
             * @param {boolean} [options.silent=false] if set, do not call the
             *   `on_close` handler.
             */
            dialog.on('closed', self, function (options) {
                options = options || {};
                self._removeAction(action.jsID);
                self.currentDialogController = null;
                if (options.silent !== true) {
                    controller.onClose(options.infos);
                }
            });
            controller.dialog = dialog;

            return dialog.open().opened(function () {
                self.currentDialogController = controller;
                widget.setParent(dialog);
                dom.append(dialog.$el, widget.$el, {
                    in_DOM: true,
                    callbacks: [{widget: controller.widget}],
                });
                widget.renderButtons(dialog.$footer);
                dialog.rebindButtonBehavior();

                return action;
            });
        }).guardedCatch(function () {
            self._removeAction(action.jsID);
        });
    },
    /**
     * Executes actions of type 'ir.actions.client'.
     *
     * @private
     * @param {Object} action the description of the action to execute
     * @param {string} action.tag the key of the action in the action_registry
     * @param {Object} options @see doAction for details
     * @returns {Promise} resolved when the client action has been executed
     */
    _executeClientAction: function (action, options) {
        var self = this;
        var ClientAction = core.action_registry.get(action.tag);
        if (!ClientAction) {
            console.error("Could not find client action " + action.tag, action);
            return Promise.reject();
        }
        if (!(ClientAction.prototype instanceof Widget)) {
            // the client action might be a function, which is executed and
            // whose returned value might be another action to execute
            var next = ClientAction(this, action);
            if (next) {
                return this.doAction(next, options);
            }
            return Promise.resolve();
        }
        if (!(ClientAction.prototype instanceof AbstractAction)) {
            console.warn('The client action ' + action.tag + ' should be an instance of AbstractAction!');
        }

        var controllerID = _.uniqueId('controller_');

        var index = this._getControllerStackIndex(options);
        options.breadcrumbs = this._getBreadcrumbs(this.controllerStack.slice(0, index));
        options.controllerID = controllerID;
        var widget = new ClientAction(this, action, options);
        var controller = {
            actionID: action.jsID,
            index: index,
            jsID: controllerID,
            title: widget.getTitle(),
            widget: widget,
        };
        this.controllers[controllerID] = controller;
        action.controllerID = controllerID;
        var prom = this._executeAction(action, options);
        prom.then(function () {
            self._pushState(controllerID, {});
        });
        return prom;
    },
    /**
     * Executes actions of type 'ir.actions.act_window_close', i.e. closes the
     * last opened dialog.
     *
     * The action may also specify an effect to display right after the close
     * action (e.g. rainbow man), or provide a reason for the close action.
     * This is useful for decision making for the `on_close` handler.
     *
     * @private
     * @param {Object} action
     * @param {Object} [action.effect] effect to show up, e.g. rainbow man.
     * @param {Object} [action.infos] infos on performing the close action.
     *   Useful for providing some context for the `on_close` handler.
     * @returns {Promise} resolved immediately
     */
    _executeCloseAction: function (action, options) {
        var result;
        if (!this.currentDialogController) {
            result = options.on_close(action.infos);
        }

        this._closeDialog({ infos: action.infos });

        // display some effect (like rainbowman) on appropriate actions
        if (action.effect) {
            this.trigger_up('show_effect', action.effect);
        }

        return Promise.resolve(result);
    },
    /**
     * Executes actions of type 'ir.actions.server'.
     *
     * @private
     * @param {Object} action the description of the action to execute
     * @param {integer} action.id the db ID of the action to execute
     * @param {Object} [action.context]
     * @param {Object} options @see doAction for details
     * @returns {Promise} resolved when the action has been executed
     */
    _executeServerAction: function (action, options) {
        var self = this;
        var runDef = this._rpc({
            route: '/web/action/run',
            params: {
                action_id: action.id,
                context: action.context || {},
            },
        });
        return this.dp.add(runDef).then(function (action) {
            action = action || { type: 'ir.actions.act_window_close' };
            return self.doAction(action, options);
        });
    },
    /**
     * Executes actions of type 'ir.actions.act_url', i.e. redirects to the
     * given url.
     *
     * @private
     * @param {Object} action the description of the action to execute
     * @param {string} action.url
     * @param {string} [action.target] set to 'self' to redirect in the current page,
     *   redirects to a new page by default
     * @param {Object} options @see doAction for details
     * @returns {Promise} resolved when the redirection is done (immediately
     *   when redirecting to a new page)
     */
    _executeURLAction: function (action, options) {
        var url = action.url;

        if (action.target === 'self') {
            framework.redirect(url);
            return Promise.resolve();
        } else {
            var w = window.open(url, '_blank');
            if (!w || w.closed || typeof w.closed === 'undefined') {
                var message = _t('A popup window has been blocked. You ' +
                             'may need to change your browser settings to allow ' +
                             'popup windows for this page.');
                this.do_warn(false, message, true);
            }
        }

        options.on_close();

        return Promise.resolve();
    },
    /**
     * Returns a description of the controllers in the given  controller stack.
     * It is used to render the breadcrumbs. It is an array of Objects with keys
     * 'title' (what to display in the breadcrumbs) and 'controllerID' (the ID
     * of the corresponding controller, used to restore it when this part of the
     * breadcrumbs is clicked).
     *
     * @private
     * @param {string[]} controllerStack
     * @returns {Object[]}
     */
    _getBreadcrumbs: function (controllerStack) {
        var self = this;
        return _.map(controllerStack, function (controllerID) {
            return {
                controllerID: controllerID,
                title: self.controllers[controllerID].title,
            };
        });
    },
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
    _getControllerStackIndex: function (options) {
        var index;
        if ('index' in options) {
            index = options.index;
        } else if (options.clear_breadcrumbs) {
            index = 0;
        } else if (options.replace_last_action) {
            index = this.controllerStack.length - 1;
        } else {
            index = this.controllerStack.length;
        }
        return index;
    },
    /**
     * Returns an object containing information about the given controller, like
     * its title, its action's id, the active_id and active_ids of the action...
     *
     * @private
     * @param {string} controllerID
     * @returns {Object}
     */
    _getControllerState: function (controllerID) {
        var controller = this.controllers[controllerID];
        var action = this.actions[controller.actionID];
        var state = {
            title: controller.widget.getTitle(),
        };
        if (action.id) {
            state.action = action.id;
        } else if (action.type === 'ir.actions.client') {
            state.action = action.tag;
            var params = _.pick(action.params, function (v) {
                return _.isString(v) || _.isNumber(v);
            });
            state = _.extend(params || {}, state);
        }
        if (action.context) {
            var active_id = action.context.active_id;
            if (active_id) {
                state.active_id = active_id;
            }
            var active_ids = action.context.active_ids;
            // we don't push active_ids if it's a single element array containing the active_id
            // to make the url shorter in most cases
            if (active_ids && !(active_ids.length === 1 && active_ids[0] === active_id)) {
                state.active_ids = action.context.active_ids.join(',');
            }
        }
        state = _.extend({}, controller.widget.getState(), state);
        return state;
    },
    /**
     * Returns the current horizontal and vertical scroll positions.
     *
     * @private
     * @returns {Object}
     */
    _getScrollPosition: function () {
        var scrollPosition;
        this.trigger_up('getScrollPosition', {
            callback: function (_scrollPosition) {
                scrollPosition = _scrollPosition;
            }
        });
        return scrollPosition;
    },
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
    _handleAction: function (action, options) {
        if (!action.type) {
            console.error("No type for action", action);
            return Promise.reject();
        }
        switch (action.type) {
            case 'ir.actions.act_url':
                return this._executeURLAction(action, options);
            case 'ir.actions.act_window_close':
                return this._executeCloseAction(action, options);
            case 'ir.actions.client':
                return this._executeClientAction(action, options);
            case 'ir.actions.server':
                return this._executeServerAction(action, options);
            default:
                console.error("The ActionManager can't handle actions of type " +
                    action.type, action);
                return Promise.reject();
        }
    },
    /**
     * Updates the internal state and the DOM with the given controller as
     * current controller.
     *
     * @private
     * @param {Object} controller
     * @param {string} controller.jsID
     * @param {Widget} controller.widget
     * @param {integer} controller.index the controller is pushed at that
     *   position in the controller stack and controllers with an higher index
     *   are destroyed
     */
    _pushController: function (controller) {
        var self = this;

        // detach the current controller
        this._detachCurrentController();

        // push the new controller to the stack at the given position, and
        // destroy controllers with an higher index
        var toDestroy = this.controllerStack.slice(controller.index);
        // reject from the list of controllers to destroy the one that we are
        // currently pushing, or those linked to the same action as the one
        // linked to the controller that we are pushing
        toDestroy = _.reject(toDestroy, function (controllerID) {
            return controllerID === controller.jsID ||
                   self.controllers[controllerID].actionID === controller.actionID;
        });
        this._removeControllers(toDestroy);
        this.controllerStack = this.controllerStack.slice(0, controller.index);
        this.controllerStack.push(controller.jsID);

        // append the new controller to the DOM
        this._appendController(controller);

        // notify the environment of the new action
        this.trigger_up('current_action_updated', {
            action: this.getCurrentAction(),
            controller: controller,
        });

        // close all dialogs when the current controller changes
        core.bus.trigger('close_dialogs');

        // toggle the fullscreen mode for actions in target='fullscreen'
        this._toggleFullscreen();
    },
    /**
     * Pushes the given state, with additional information about the given
     * controller, like the action's id and the controller's title.
     *
     * @private
     * @param {string} controllerID
     * @param {Object} [state={}]
     */
    _pushState: function (controllerID, state) {
        var controller = this.controllers[controllerID];
        if (controller) {
            var action = this.actions[controller.actionID];
            if (action.target === 'new') {
                // do not push state for actions in target="new"
                return;
            }
            if (action.pushState === false) {
                // do not push state for actions that have been explicitly
                // marked as not pushable but trigger the title change
                this.trigger_up('set_title_part', {
                    part: "action",
                    title: controller.widget.getTitle()
                });
                return;
            }
            state = _.extend({}, state, this._getControllerState(controller.jsID));
            this.trigger_up('push_state', {state: state});
        }
    },
    /**
     * Loads an action from the database given its ID.
     *
     * @todo: turn this in a service (DataManager)
     * @private
     * @param {integer|string} action's ID or xml ID
     * @param {Object} context
     * @returns {Promise<Object>} resolved with the description of the action
     */
    _loadAction: function (actionID, context) {
        var self = this;
        return new Promise(function (resolve, reject) {
            self.trigger_up('load_action', {
                actionID: actionID,
                context: context,
                on_success: resolve,
            });
        });
    },
    /**
     * Preprocesses the action before it is handled by the ActionManager
     * (assigns a JS id, evaluates its context and domains, etc.).
     *
     * @param {Object} action
     * @param {Object} options see @doAction options
     */
    _preprocessAction: function (action, options) {
        // ensure that the context and domain are evaluated
        var context = new Context(this.userContext, options.additional_context, action.context);
        action.context = pyUtils.eval('context', context);
        if (action.domain) {
            action.domain = pyUtils.eval('domain', action.domain, action.context);
        }

        action._originalAction = JSON.stringify(action);

        action.jsID = _.uniqueId('action_');
        action.pushState = options.pushState;
    },
    /**
     * Unlinks the given action and its controller from the internal structures
     * and destroys its controllers.
     *
     * @private
     * @param {string} actionID the id of the action to remove
     */
    _removeAction: function (actionID) {
        var action = this.actions[actionID];
        var controller = this.controllers[action.controllerID];
        delete this.actions[action.jsID];
        delete this.controllers[action.controllerID];
        controller.widget.destroy();
    },
    /**
     * Removes the given controllers and their corresponding actions.
     *
     * @see _removeAction
     * @private
     * @param {string[]} controllerIDs
     */
    _removeControllers: function (controllerIDs) {
        var self = this;
        var actionsToRemove = _.map(controllerIDs, function (controllerID) {
            return self.controllers[controllerID].actionID;
        });
        _.each(_.uniq(actionsToRemove), this._removeAction.bind(this));
    },
    /**
     * Restores a controller from the controllerStack and destroys all
     * controllers stacked over the given controller (called when coming back
     * using the breadcrumbs).
     *
     * @private
     * @param {string} controllerID
     * @returns {Promise} resolved when the controller has been restored
     */
    _restoreController: function (controllerID) {
        var self = this;
        var controller = this.controllers[controllerID];
        // AAB: AbstractAction should define a proper hook to execute code when
        // it is restored (other than do_show), and it should return a promise
        var action = this.actions[controller.actionID];
        var def;
        if (action.on_reverse_breadcrumb) {
            def = action.on_reverse_breadcrumb();
        }
        return Promise.resolve(def).then(function () {
            return Promise.resolve(controller.widget.do_show()).then(function () {
                var index = _.indexOf(self.controllerStack, controllerID);
                self._pushController(controller, index);
            });
        });
    },
    /**
     * Starts the controller by appending it in a document fragment, so that it
     * is ready when it will be appended to the DOM. This allows to prevent
     * flickering for widgets doing async stuff in willStart() or start().
     *
     * Also updates the control panel on any change of the title on controller's
     * widget.
     *
     * @private
     * @param {Object} controller
     * @returns {Promise<Object>} resolved with the controller when it is ready
     */
    _startController: function (controller) {
        var fragment = document.createDocumentFragment();
        return controller.widget.appendTo(fragment).then(function () {
            return controller;
        });
    },
    /**
     * Toggles the fullscreen mode if there is an action in target='fullscreen'
     * in the current stack.
     *
     * @private
     */
    _toggleFullscreen: function () {
        var self = this;
        var fullscreen = _.some(this.controllerStack, function (controllerID) {
            var controller = self.controllers[controllerID];
            return self.actions[controller.actionID].target === 'fullscreen';
        });
        this.trigger_up('toggle_fullscreen', {fullscreen: fullscreen});
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.data.controllerID
     */
    _onBreadcrumbClicked: function (ev) {
        ev.stopPropagation();
        this._restoreController(ev.data.controllerID);
    },
    /**
     * Goes back in the history: if a controller is opened in a dialog, closes
     * the dialog, otherwise, restores the second to last controller from the
     * stack.
     *
     * @private
     */
    _onHistoryBack: function () {
        if (this.currentDialogController) {
            this._closeDialog();
        } else {
            var length = this.controllerStack.length;
            if (length > 1) {
                this._restoreController(this.controllerStack[length - 2]);
            }
        }
    },
    /**
     * Intercepts and triggers a new push_state event, with additional
     * information about the given controller.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.controllerID
     * @param {Object} [ev.state={}]
     */
    _onPushState: function (ev) {
        if (ev.target !== this) {
            ev.stopPropagation();
            this._pushState(ev.data.controllerID, ev.data.state);
        }
    },
    /**
     * Intercepts and triggers a redirection on a link.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.res_id
     * @param {string} ev.data.res_model
     */
    _onRedirect: function (ev) {
        this.do_action({
            type:'ir.actions.act_window',
            view_mode: 'form',
            res_model: ev.data.res_model,
            views: [[false, 'form']],
            res_id: ev.data.res_id,
        });
    },
});

return ActionManager;

});
