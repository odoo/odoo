odoo.define('web.ActionManager', function (require) {
"use strict";

/**
 * ActionManager
 *
 * The ActionManager is one of the centrepieces in the WebClient architecture.
 * Its role is to makes sure that Odoo actions are properly started and
 * coordinated.
 */

var Bus = require('web.Bus');
var concurrency = require('web.concurrency');
var Context = require('web.Context');
var ControlPanel = require('web.ControlPanel');
var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var framework = require('web.framework');
var pyeval = require('web.pyeval');
var Widget = require('web.Widget');

var ActionManager = Widget.extend({
    className: 'o_content',
    custom_events: {
        breadcrumb_clicked: '_onBreadcrumbClicked',
        history_back: '_onHistoryBack',
        push_state: '_onPushState',
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
     * @override
     */
    start: function () {
        // AAB: temporarily instantiate a unique main ControlPanel used by
        // controllers in the controllerStack
        this.controlPanel = new ControlPanel(this);
        var def = this.controlPanel.insertBefore(this.$el);

        return $.when(def, this._super.apply(this, arguments));
    },
    /**
     * Called each time the action manager is attached into the DOM.
     */
    on_attach_callback: function() {
        this.isInDOM = true;
        var currentController = this.getCurrentController();
        if (currentController && currentController.widget.on_attach_callback) {
            currentController.widget.on_attach_callback();
        }
    },
    /**
     * Called each time the action manager is detached from the DOM.
     */
    on_detach_callback: function() {
        this.isInDOM = false;
        var currentController = this.getCurrentController();
        if (currentController && currentController.widget.on_detach_callback) {
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
     * @returns {Deferred} resolved if the current controller can be left,
     *   rejected otherwise.
     */
    clearUncommittedChanges: function () {
        var currentController = this.getCurrentController();
        // AAB: with AbstractAction, the second part of the condition won't be
        // necessary anymore, as there will be such a function it its API
        if (currentController && currentController.widget.discardChanges) {
            return currentController.widget.discardChanges(undefined, {
                // AAB: get rid of this option when on_hashchange mechanism is improved
                readonlyIfRealDiscard: true,
            });
        }
        return $.when();
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
     * @return {Deferred} resolved when the action is loaded and appended to the
     *   DOM ; rejected if the action can't be executed (e.g. if doAction has
     *   been called to execute another action before this one was complete).
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

        return this.dp.add($.when(def)).then(function () {
            action.jsID = _.uniqueId('action_');
            action.pushState = options.pushState;

            // action.target 'main' is equivalent to 'current' except that it
            // also clears the breadcrumbs
            options.clear_breadcrumbs = action.target === 'main' ||
                                        options.clear_breadcrumbs;

            // ensure that the context and domain are evaluated
            var context = new Context(self.userContext, options.additional_context, action.context);
            action.context = pyeval.eval('context', context);
            if (action.domain) {
                action.domain = pyeval.eval('domain', action.domain, action.context);
            }

            return self._handleAction(action, options);
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
     * @returns {Deferred} resolved when the UI has been updated
     */
    loadState: function (state) {
        var action;
        if (!state.action) {
            return $.when();
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

        this.trigger_up('scrollTo', {offset: controller.scrollTop || 0});

        if (!controller.widget.need_control_panel) {
            this.controlPanel.do_hide();
        } else {
            this.controlPanel.update({
                breadcrumbs: this._getBreadcrumbs(),
            }, {clear: false});
        }
    },
    /**
     * Closes the current dialog, if any. Because we listen to the 'closed'
     * event triggered by the dialog when it is closed, this also destroys the
     * embedded controller and removes the reference to the corresponding action.
     * This also executes the 'on_close' handler in some cases.
     *
     * @private
     * @param {boolean} [silent=false] if true, the 'on_close' handler won't be
     *   called ; this is in general the case when the current dialog is closed
     *   because another action is opened, so we don't want the former action
     *   to execute its handler as it won't be displayed anyway
     */
    _closeDialog: function (silent) {
        if (this.currentDialogController) {
            this.currentDialogController.dialog.destroy(silent);
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
            currentController.scrollTop = this._getScrollTop();
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
     * @returns {Deferred} resolved when the controller is started and appended
     */
    _executeAction: function (action, options) {
        var self = this;
        this.actions[action.jsID] = action;

        if (action.target === 'new') {
            return this._executeActionInDialog(action, options);
        }

        return this.clearUncommittedChanges()
            .then(function () {
                var controller = self.controllers[action.controllerID];
                var widget = controller.widget;
                // AAB: this will be moved to the Controller
                if (widget.need_control_panel) {
                    // set the ControlPanel bus on the controller to allow it to
                    // communicate its status
                    widget.set_cp_bus(self.controlPanel.get_bus());
                }
                return self._startController(controller);
            })
            .then(function (controller) {
                if (self.currentDialogController) {
                    self._closeDialog(true);
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
                self._pushController(controller, options);

                // toggle the fullscreen mode for actions in target='fullscreen'
                self._toggleFullscreen();

                return action;
            })
            .fail(function () {
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
     * @returns {Deferred} resolved when the controller is rendered inside a
     *   dialog appended to the DOM
     */
    _executeActionInDialog: function (action, options) {
        var self = this;
        var controller = this.controllers[action.controllerID];
        var widget = controller.widget;
        // AAB: this will be moved to the Controller
        if (widget.need_control_panel) {
            // set the ControlPanel bus on the controller to allow it to
            // communicate its status
            widget.set_cp_bus(new Bus());
        }

        return this._startController(controller).then(function (controller) {
            if (self.currentDialogController) {
                self._closeDialog(true);
            }

            var dialog = new Dialog(self, _.defaults({}, options, {
                buttons: [],
                dialogClass: controller.className,
                title: action.name,
                size: action.context.dialog_size,
            }));
            dialog.on('closed', self, function (silent) {
                self._removeAction(action.jsID);
                self.currentDialogController = null;
                if (silent !== true) {
                    options.on_close();
                }
            });
            controller.dialog = dialog;

            return dialog.open().opened(function () {
                dom.append(dialog.$el, widget.$el, {
                    in_DOM: true,
                    callbacks: [{widget: dialog}],
                });
                // AAB: renderButtons will be a function of AbstractAction, so this
                // test won't be necessary anymore
                if (widget.renderButtons) {
                    widget.renderButtons(dialog.$footer);
                }

                self.currentDialogController = controller;

                return action;
            });
        }).fail(function () {
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
     * @returns {Deferred} resolved when the client action has been executed
     */
    _executeClientAction: function (action, options) {
        var self = this;
        var ClientAction = core.action_registry.get(action.tag);
        if (!ClientAction) {
            console.error("Could not find client action " + action.tag, action);
            return $.Deferred().reject();
        }
        if (!(ClientAction.prototype instanceof Widget)) {
            // the client action might be a function, which is executed and
            // whose returned value might be another action to execute
            var next = ClientAction(this, action);
            if (next) {
                return this.doAction(next, options);
            }
            return $.when();
        }

        var controllerID = _.uniqueId('controller_');
        var controller = {
            actionID: action.jsID,
            jsID: controllerID,
            widget: new ClientAction(this, action, options),
        };
        // AAB: TODO: simplify this with AbstractAction (implement a getTitle
        // function that returns action.name by default, and that can be
        // overriden in client actions and view controllers)
        Object.defineProperty(controller, 'title', {
            get: function () {
                return controller.widget.get('title') || action.display_name || action.name;
            },
        });
        this.controllers[controllerID] = controller;
        action.controllerID = controllerID;
        return this._executeAction(action, options).done(function () {
            // AAB: this should be done automatically in AbstractAction, so that
            // it can be overriden by actions that have specific stuff to push
            // (e.g. Discuss, Views)
            self._pushState(controllerID, {});
        });
    },
    /**
     * Executes actions of type 'ir.actions.act_window_close', i.e. closes the
     * last opened dialog.
     *
     * @private
     * @param {Object} action
     * @returns {Deferred} resolved immediately
     */
    _executeCloseAction: function (action, options) {
        if (!this.currentDialogController) {
            options.on_close();
        }

        this._closeDialog();

        // display some effect (like rainbowman) on appropriate actions
        if (action.effect) {
            this.trigger_up('show_effect', action.effect);
        }

        return $.when();
    },
    /**
     * Executes actions of type 'ir.actions.server'.
     *
     * @private
     * @param {Object} action the description of the action to execute
     * @param {integer} action.id the db ID of the action to execute
     * @param {Object} [action.context]
     * @param {Object} options @see doAction for details
     * @returns {Deferred} resolved when the action has been executed
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
     * @returns {Deferred} resolved when the redirection is done (immediately
     *   when redirecting to a new page)
     */
    _executeURLAction: function (action, options) {
        var url = action.url;
        if (config.debug && url && url.length && url[0] === '/') {
            url = $.param.querystring(url, {debug: config.debug});
        }

        if (action.target === 'self') {
            framework.redirect(url);
            return $.Deferred();
        } else {
            window.open(url, '_blank');
        }

        options.on_close();

        return $.when();
    },
    /**
     * Returns a description of the current stack of controllers, used to render
     * the breadcrumbs. It is an array of Objects with keys 'title' (what to
     * display in the breadcrumbs) and 'controllerID' (the ID of the
     * corresponding controller, used to restore it when this part of the
     * breadcrumbs is clicked).
     * Ignores the content of the stack of controllers if the action of the
     * last controller of the stack is flagged with 'no_breadcrumbs', indicating
     * that the breadcrumbs should not be displayed for that action.
     *
     * @private
     * @returns {Object[]}
     */
    _getBreadcrumbs: function () {
        var self = this;
        var currentController = this.getCurrentController();
        var noBreadcrumbs = !currentController ||
                            this.actions[currentController.actionID].context.no_breadcrumbs;
        if (noBreadcrumbs) {
            return [];
        }
        return _.map(this.controllerStack, function (controllerID) {
            return {
                title: self.controllers[controllerID].title,
                controllerID: controllerID,
            };
        });
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
            title: controller.title,
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
        return state;
    },
    /**
     * Returns the current vertical scroll position.
     *
     * @private
     * @returns {integer}
     */
    _getScrollTop: function () {
        var scrollTop;
        this.trigger_up('getScrollTop', {
            callback: function (value) {
                scrollTop = value;
            }
        });
        return scrollTop;
    },
    /**
     * Dispatches the given action to the corresponding handler to execute it,
     * according to its type. This function can be overriden to extend the
     * range of supported action types.
     *
     * @private
     * @param {Object} action
     * @param {string} action.type
     * @param {Object} options
     * @returns {Deferred} resolved when the action has been executed ; rejected
     *   if the type of action isn't supported, or if the action can't be
     *   executed
     */
    _handleAction: function (action, options) {
        if (!action.type) {
            console.error("No type for action", action);
            return $.Deferred().reject();
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
                return $.Deferred().reject();
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
     * @param {Object} [options]
     * @param {Object} [options.clear_breadcrumbs=false] if true, destroys all
     *   controllers from the controller stack before adding the given one
     * @param {Object} [options.replace_last_action=false] if true, replaces the
     *   last controller of the controller stack by the given one
     * @param {integer} [options.index] if given, pushes the controller at that
     *   position in the controller stack, and destroys the controllers with an
     *   higher index
     */
    _pushController: function (controller, options) {
        options = options || {};
        var self = this;

        // detach the current controller
        this._detachCurrentController();

        // empty the controller stack or replace the last controller as requested,
        // destroy the removed controllers and push the new controller to the stack
        var toDestroy;
        if (options.clear_breadcrumbs) {
            toDestroy = this.controllerStack;
            this.controllerStack = [];
        } else if (options.replace_last_action && this.controllerStack.length > 0) {
            toDestroy = [this.controllerStack.pop()];
        } else if (options.index !== undefined) {
            toDestroy = this.controllerStack.splice(options.index);
            // reject from the list of controllers to destroy the one that we are
            // currently pushing, or those linked to the same action as the one
            // linked to the controller that we are pushing
            toDestroy = _.reject(toDestroy, function (controllerID) {
                return controllerID === controller.jsID ||
                       self.controllers[controllerID].actionID === controller.actionID;
            });
        }
        this._removeControllers(toDestroy);
        this.controllerStack.push(controller.jsID);

        // append the new controller to the DOM
        this._appendController(controller);

        // notify the environment of the new action
        this.trigger_up('current_action_updated', {
            action: this.getCurrentAction(),
            controller: controller,
        });
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
            if (action.target === 'new' || action.pushState === false) {
                // do not push state for actions in target="new" or for actions
                // that have been explicitly marked as not pushable
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
     * @returns {Deferred<Object>} resolved with the description of the action
     */
    _loadAction: function (actionID, context) {
        var def = $.Deferred();
        this.trigger_up('load_action', {
            actionID: actionID,
            context: context,
            on_success: def.resolve.bind(def),
        });
        return def;
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
     * @returns {Deferred} resolved when the controller has been restored
     */
    _restoreController: function (controllerID) {
        var self = this;
        var controller = this.controllers[controllerID];
        // AAB: AbstractAction should define a proper hook to execute code when
        // it is restored (other than do_show), and it should return a deferred
        var action = this.actions[controller.actionID];
        var def;
        if (action.on_reverse_breadcrumb) {
            def = action.on_reverse_breadcrumb();
        }
        return $.when(def).then(function () {
            return $.when(controller.widget.do_show()).then(function () {
                var index = _.indexOf(self.controllerStack, controllerID);
                self._pushController(controller, {index: index});
            });
        });
    },
    /**
     * Starts the controller by appending it in a document fragment, so that it
     * is ready when it will be appended to the DOM. This allows to prevent
     * flickering for widgets doing async stuff in willStart() or start().
     *
     * @private
     * @param {Object} controller
     * @returns {Deferred<Object>} resolved with the controller when it is ready
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
     * @param {OdooEvent} ev.data.controllerID
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
});

return ActionManager;

});
