odoo.define('web.ActWindowActionManager', function (require) {
"use strict";

/**
 * The purpose of this file is to add the support of Odoo actions of type
 * 'ir.actions.act_window' to the ActionManager.
 */

var ActionManager = require('web.ActionManager');
var config = require('web.config');
var Context = require('web.Context');
var core = require('web.core');
var pyUtils = require('web.py_utils');
var view_registry = require('web.view_registry');

ActionManager.include({
    custom_events: _.extend({}, ActionManager.prototype.custom_events, {
        execute_action: '_onExecuteAction',
        switch_view: '_onSwitchView',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Override to handle the case of lazy-loaded controllers, which may be the
     * last controller in the stack, but which should not be considered as
     * current controller as they don't have an alive widget.
     *
     * Note: this function assumes that there can be at most one lazy loaded
     * controller in the stack
     *
     * @override
     */
    getCurrentController: function () {
        var currentController = this._super.apply(this, arguments);
        var action = currentController && this.actions[currentController.actionID];
        if (action && action.type === 'ir.actions.act_window' && !currentController.widget) {
            var lastControllerID = this.controllerStack.pop();
            currentController = this._super.apply(this, arguments);
            this.controllerStack.push(lastControllerID);
        }
        return currentController;
    },
    /**
     * Overrides to handle the case where an 'ir.actions.act_window' has to be
     * loaded.
     *
     * @override
     * @param {Object} state
     * @param {integer|string} [state.action] the ID or xml ID of the action to
     *   execute
     * @param {integer} [state.active_id]
     * @param {string} [state.active_ids]
     * @param {integer} [state.id]
     * @param {integer} [state.view_id=false]
     * @param {string} [state.view_type]
     */
    loadState: function (state) {
        var _super = this._super.bind(this);
        var action;
        var options = {
            clear_breadcrumbs: true,
            pushState: false,
        };
        if (state.action) {
            var currentController = this.getCurrentController();
            var currentAction = currentController && this.actions[currentController.actionID];
            if (currentAction && currentAction.id === state.action &&
                currentAction.type === 'ir.actions.act_window') {
                // the action to load is already the current one, so update it
                this._closeDialog(true); // there may be a currently opened dialog, close it
                var viewOptions = {currentId: state.id};
                var viewType = state.view_type || currentController.viewType;
                return this._switchController(currentAction, viewType, viewOptions);
            } else if (!core.action_registry.contains(state.action)) {
                // the action to load isn't the current one, so execute it
                var context = {};
                if (state.active_id) {
                    context.active_id = state.active_id;
                }
                if (state.active_ids) {
                    // jQuery's BBQ plugin does some parsing on values that are valid integers
                    // which means that if there's only one item, it will do parseInt() on it,
                    // otherwise it will keep the comma seperated list as string
                    context.active_ids = state.active_ids.toString().split(',').map(function (id) {
                        return parseInt(id, 10) || id;
                    });
                } else if (state.active_id) {
                    context.active_ids = [state.active_id];
                }
                context.params = state;
                action = state.action;
                options = _.extend(options, {
                    additional_context: context,
                    resID: state.id || undefined,  // empty string with bbq
                    viewType: state.view_type,
                });
            }
        } else if (state.model && state.id) {
            action = {
                res_model: state.model,
                res_id: state.id,
                type: 'ir.actions.act_window',
                views: [[state.view_id || false, 'form']],
            };
        } else if (state.model && state.view_type) {
            // this is a window action on a multi-record view, so restore it
            // from the session storage
            var storedAction = this.call('session_storage', 'getItem', 'current_action');
            var lastAction = JSON.parse(storedAction || '{}');
            if (lastAction.res_model === state.model) {
                action = lastAction;
                options.viewType = state.view_type;
            }
        }
        if (action) {
            return this.doAction(action, options);
        }
        return _super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instantiates the controller for a given action and view type, and adds it
     * to the list of controllers in the action.
     *
     * @private
     * @param {Object} action
     * @param {AbstractController[]} action.controllers the already created
     *   controllers for this action
     * @param {Object[]} action.views the views available for the action, each
     *   one containing its fieldsView
     * @param {Object} action.env
     * @param {string} viewType
     * @param {Object} [viewOptions] dict of options passed to the initialization
     *   of the controller's widget
     * @param {Object} [options]
     * @param {string} [options.controllerID=false] when the controller has
     *   previously been lazy-loaded, we want to keep its jsID when loading it
     * @param {integer} [options.index=0] the controller's index in the stack
     * @param {boolean} [options.lazy=false] set to true to differ the
     *   initialization of the controller's widget
     * @returns {Promise<Object>} resolved with the created controller
     */
    _createViewController: function (action, viewType, viewOptions, options) {
        var self = this;
        var viewDescr = _.findWhere(action.views, {type: viewType});
        if (!viewDescr) {
            // the requested view type isn't specified in the action (e.g.
            // action with list view only, user clicks on a row in the list, it
            // tries to switch to form view)
            return Promise.reject();
        }

        options = options || {};
        var index = options.index || 0;
        var controllerID = options.controllerID || _.uniqueId('controller_');
        var controller = {
            actionID: action.jsID,
            className: 'o_act_window', // used to remove the padding in dialogs
            index: index,
            jsID: controllerID,
            viewType: viewType,
        };
        Object.defineProperty(controller, 'title', {
            get: function () {
                // handle the case where the widget is lazy loaded
                return controller.widget ?
                       controller.widget.getTitle() :
                       (action.display_name || action.name);
            },
        });
        this.controllers[controllerID] = controller;

        if (!options.lazy) {
            // build the view options from different sources
            var flags = action.flags || {};
            viewOptions = _.extend({}, flags, flags[viewType], viewOptions, {
                action: action,
                breadcrumbs: this._getBreadcrumbs(this.controllerStack.slice(0, index)),
                // pass the controllerID to the views as an hook for further
                // communication with trigger_up
                controllerID: controllerID,
            });
            var rejection;
            var view = new viewDescr.Widget(viewDescr.fieldsView, viewOptions);
            var def = new Promise(function (resolve, reject) {
                rejection = reject;
                view.getController(self).then(function (widget) {
                    if (def.rejected) {
                        // the promise has been rejected meanwhile, meaning that
                        // the action has been removed, so simply destroy the widget
                        widget.destroy();
                    } else {
                        controller.widget = widget;
                        resolve(controller);
                    }
                }).guardedCatch(reject);
            });
            // Need to define an reject property to call it into _destroyWindowAction
            def.reject = rejection;
            def.guardedCatch(function () {
                def.rejected = true;
                delete self.controllers[controllerID];
            });
            action.controllers[viewType] = def;
        } else {
            action.controllers[viewType] = Promise.resolve(controller);
        }
        return action.controllers[viewType];
    },
    /**
     * Destroys the controllers and search view of a given action of type
     * 'ir.actions.act_window'.
     *
     * @private
     * @param {Object} action
     */
    _destroyWindowAction: function (action) {
        var self = this;
        for (var c in action.controllers) {
            var controllerDef = action.controllers[c];
            controllerDef.then(function (controller) {
                delete self.controllers[controller.jsID];
                if (controller.widget) {
                    controller.widget.destroy();
                }
            });
            // If controllerDef is not resolved yet, reject it so that the
            // controller will be correctly destroyed as soon as it'll be ready,
            // and its reference will be removed. Lazy-loaded controllers do
            // not have a reject function on their promise
            if (controllerDef.reject) {
                controllerDef.reject();
            }
        }
    },
    /**
     * Executes actions of type 'ir.actions.act_window'.
     *
     * @private
     * @param {Object} action the description of the action to execute
     * @param {Array} action.views list of tuples [viewID, viewType]
     * @param {Object} options @see doAction for details
     * @param {integer} [options.resID] the current res ID
     * @param {string} [options.viewType] the view to open
     * @returns {Promise} resolved when the action is appended to the DOM
     */
    _executeWindowAction: function (action, options) {
        var self = this;
        return this.dp.add(this._loadViews(action)).then(function (fieldsViews) {
            var views = self._generateActionViews(action, fieldsViews);
            action._views = action.views; // save the initial attribute
            action.views = views;
            action.controlPanelFieldsView = fieldsViews.search;
            action.controllers = {};

            // select the current view to display, and optionally the main view
            // of the action which will be lazyloaded
            var curView = options.viewType && _.findWhere(views, {type: options.viewType});
            var lazyView;
            if (curView) {
                if (!curView.multiRecord && views[0].multiRecord) {
                    lazyView = views[0];
                }
            } else {
                curView = views[0];
            }

            // use mobile-friendly view by default in mobile, if possible
            if (config.device.isMobile) {
                if (!curView.isMobileFriendly) {
                    curView = self._findMobileView(views, curView.multiRecord) || curView;
                }
                if (lazyView && !lazyView.isMobileFriendly) {
                    lazyView = self._findMobileView(views, lazyView.multiRecord) || lazyView;
                }
            }

            var lazyViewDef;
            var lazyControllerID;
            if (lazyView) {
                // if the main view is lazy-loaded, its (lazy-loaded) controller is inserted
                // into the controller stack (so that breadcrumbs can be correctly computed),
                // so we force clear_breadcrumbs to false so that it won't be removed when the
                // current controller will be inserted afterwards
                options.clear_breadcrumbs = false;
                // this controller being lazy-loaded, this call is actually sync
                lazyViewDef = self._createViewController(action, lazyView.type, {}, {lazy: true})
                    .then(function (lazyLoadedController) {
                        lazyControllerID = lazyLoadedController.jsID;
                        self.controllerStack.push(lazyLoadedController.jsID);
                    });
            }
            return self.dp.add(Promise.resolve(lazyViewDef))
                .then(function () {
                    var viewOptions = {
                        controllerState: options.controllerState,
                        currentId: options.resID,
                    };
                    var curViewDef = self._createViewController(action, curView.type, viewOptions, {
                        index: self._getControllerStackIndex(options),
                    });
                    return self.dp.add(curViewDef);
                })
                .then(function (controller) {
                    action.controllerID = controller.jsID;
                    return self._executeAction(action, options);
                })
                .guardedCatch(function () {
                    if (lazyControllerID) {
                        var index = self.controllerStack.indexOf(lazyControllerID);
                        self.controllerStack = self.controllerStack.slice(0, index);
                    }
                    self._destroyWindowAction(action);
                });
        });
    },
    /**
     * Helper function to find the first mobile-friendly view, if any.
     *
     * @private
     * @param {Array} views an array of views
     * @param {boolean} multiRecord set to true iff we search for a multiRecord
     *   view
     * @returns {Object|undefined} a mobile-friendly view of the requested
     *   multiRecord type, undefined if there is no such view
     */
    _findMobileView: function (views, multiRecord) {
        return _.findWhere(views, {
            isMobileFriendly: true,
            multiRecord: multiRecord,
        });
    },
    /**
     * Generate the description of the views of a given action. For each view,
     * it generates a dict with information like the fieldsView, the view type,
     * the Widget to use...
     *
     * @private
     * @param {Object} action
     * @param {Object} fieldsViews
     * @returns {Object}
     */
    _generateActionViews: function (action, fieldsViews) {
        var views = [];
        _.each(action.views, function (view) {
            var viewType = view[1];
            var fieldsView = fieldsViews[viewType];
            var parsedXML = new DOMParser().parseFromString(fieldsView.arch, "text/xml");
            var key = parsedXML.documentElement.getAttribute('js_class');
            var View = view_registry.get(key || viewType);
            if (View) {
                views.push({
                    accessKey: View.prototype.accessKey || View.prototype.accesskey,
                    displayName: View.prototype.display_name,
                    fieldsView: fieldsView,
                    icon: View.prototype.icon,
                    isMobileFriendly: View.prototype.mobile_friendly,
                    multiRecord: View.prototype.multi_record,
                    type: viewType,
                    viewID: view[0],
                    Widget: View,
                });
            } else if (config.isDebug('assets')) {
                console.log("View type '" + viewType + "' is not present in the view registry.");
            }
        });
        return views;
    },
    /**
     * Overrides to add specific information for controllers from actions of
     * type 'ir.actions.act_window', like the res_model and the view_type.
     *
     * @override
     * @private
     */
    _getControllerState: function (controllerID) {
        var state = this._super.apply(this, arguments);
        var controller = this.controllers[controllerID];
        var action = this.actions[controller.actionID];
        if (action.type === 'ir.actions.act_window') {
            state.model = action.res_model;
            state.view_type = controller.viewType;
        }
        return state;
    },
    /**
     * Overrides to handle the 'ir.actions.act_window' actions.
     *
     * @override
     * @private
     */
    _handleAction: function (action, options) {
        if (action.type === 'ir.actions.act_window') {
            return this._executeWindowAction(action, options);
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Loads the fields_views and fields for the given action.
     *
     * @private
     * @param {Object} action
     * @returns {Promise}
     */
    _loadViews: function (action) {
        var inDialog = action.target === 'new';
        var inline = action.target === 'inline';
        var options = {
            action_id: action.id,
            toolbar: !inDialog && !inline,
        };
        var views = action.views.slice();
        if (!inline && !(inDialog && action.views[0][1] === 'form')) {
            options.load_filters = true;
            var searchviewID = action.search_view_id && action.search_view_id[0];
            views.push([searchviewID || false, 'search']);
        }
        return this.loadViews(action.res_model, action.context, views, options);
    },
    /**
     * Overrides to handle the case of 'ir.actions.act_window' actions, i.e.
     * destroys all controllers associated to the given action, and its search
     * view.
     *
     * @override
     * @private
     */
    _removeAction: function (actionID) {
        var action = this.actions[actionID];
        if (action.type === 'ir.actions.act_window') {
            delete this.actions[action.jsID];
            this._destroyWindowAction(action);
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to handle the case where the controller to restore is from an
     * 'ir.actions.act_window' action. In this case, only the controllers
     * stacked over the one to restore *that are not from the same action* are
     * destroyed.
     * For instance, when going back to the list controller from a form
     * controller of the same action using the breadcrumbs, the form controller
     * isn't destroyed, as it might be reused in the future.
     *
     * @override
     * @private
     */
    _restoreController: function (controllerID) {
        var self = this;
        var controller = this.controllers[controllerID];
        var action = this.actions[controller.actionID];
        if (action.type === 'ir.actions.act_window') {
            return this.clearUncommittedChanges().then(function () {
                // AAB: this will be done directly in AbstractAction's restore
                // function
                var def = Promise.resolve();
                if (action.on_reverse_breadcrumb) {
                    def = action.on_reverse_breadcrumb();
                }
                return Promise.resolve(def).then(function () {
                    return self._switchController(action, controller.viewType);
                });
            });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Handles the switch from a controller to another (either inside the same
     * window action, or from a window action to another using the breadcrumbs).
     *
     * @private
     * @param {Object} controller the controller to switch to
     * @param {Object} [viewOptions]
     * @return {Promise} resolved when the new controller is in the DOM
     */
    _switchController: function (action, viewType, viewOptions) {
        var self = this;
        var view = _.findWhere(action.views, {type: viewType});
        if (!view) {
            // can't switch to an unknown view
            return Promise.reject();
        }

        var currentController = this.getCurrentController();
        var index;
        if (currentController.actionID !== action.jsID) {
            // the requested controller is from another action, so we went back
            // to a previous action using the breadcrumbs
            var controller = _.findWhere(this.controllers, {
                actionID: action.jsID,
                viewType: viewType,
            });
            index = _.indexOf(this.controllerStack, controller.jsID);
        } else {
            // the requested controller is from the same action as the current
            // one, so we either
            //   1) go one step back from a mono record view to a multi record
            //      one using the breadcrumbs
            //   2) or we switched from a view to another  using the view
            //      switcher
            //   3) or we opened a record from a multi record view
            if (view.multiRecord) {
                // cases 1) and 2) (with multi record views): replace the first
                // controller linked to the same action in the stack
                index = _.findIndex(this.controllerStack, function (controllerID) {
                    return self.controllers[controllerID].actionID === action.jsID;
                });
            } else if (!_.findWhere(action.views, {type: currentController.viewType}).multiRecord) {
                // case 2) (with mono record views): replace the last
                // controller by the new one if they are from the same action
                // and if they both are mono record
                index = this.controllerStack.length - 1;
            } else {
                // case 3): insert the controller on the top of the controller
                // stack
                index = this.controllerStack.length;
            }
        }

        var newController = function (controllerID) {
            var options = {
                controllerID: controllerID,
                index: index,
            };
            return self
                ._createViewController(action, viewType, viewOptions, options)
                .then(function (controller) {
                    return self._startController(controller);
                });
        };

        var controllerDef = action.controllers[viewType];
        if (controllerDef) {
            controllerDef = controllerDef.then(function (controller) {
                if (!controller.widget) {
                    // lazy loaded -> load it now (with same jsID)
                    return newController(controller.jsID);
                } else {
                    return Promise.resolve(controller.widget.willRestore()).then(function () {
                        viewOptions = _.extend({}, viewOptions, {
                            breadcrumbs: self._getBreadcrumbs(self.controllerStack.slice(0, index)),
                            shouldUpdateSearchComponents: true,
                        });
                        return controller.widget.reload(viewOptions).then(function () {
                            return controller;
                        });
                    });
                }
            }, function () {
                // if the controllerDef is rejected, it probably means that the js
                // code or the requests made to the server crashed.  In that case,
                // if we reuse the same promise, then the switch to the view is
                // definitely blocked.  We want to use a new controller, even though
                // it is very likely that it will recrash again.  At least, it will
                // give more feedback to the user, and it could happen that one
                // record crashes, but not another.
                return newController();
            });
        } else {
            controllerDef = newController();
        }

        return this.dp.add(controllerDef).then(function (controller) {
            return self._pushController(controller);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handler for event 'execute_action', which is typically called when a
     * button is clicked. The button may be of type 'object' (call a given
     * method of a given model) or 'action' (execute a given action).
     * Alternatively, the button may have the attribute 'special', and in this
     * case an 'ir.actions.act_window_close' is executed.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data.action_data typically, the html attributes of the
     *   button extended with additional information like the context
     * @param {Object} [ev.data.action_data.special=false]
     * @param {Object} [ev.data.action_data.type] 'object' or 'action', if set
     * @param {Object} ev.data.env
     * @param {function} [ev.data.on_closed]
     * @param {function} [ev.data.on_fail]
     * @param {function} [ev.data.on_success]
     */
    _onExecuteAction: function (ev) {
        ev.stopPropagation();
        var self = this;
        var actionData = ev.data.action_data;
        var env = ev.data.env;
        var context = new Context(env.context, actionData.context || {});
        var recordID = env.currentID || null; // pyUtils handles null value, not undefined
        var def;

        // determine the action to execute according to the actionData
        if (actionData.special) {
            def = Promise.resolve({
                type: 'ir.actions.act_window_close',
                infos: { special: true },
            });
        } else if (actionData.type === 'object') {
            // call a Python Object method, which may return an action to execute
            var args = recordID ? [[recordID]] : [env.resIDs];
            if (actionData.args) {
                try {
                    // warning: quotes and double quotes problem due to json and xml clash
                    // maybe we should force escaping in xml or do a better parse of the args array
                    var additionalArgs = JSON.parse(actionData.args.replace(/'/g, '"'));
                    args = args.concat(additionalArgs);
                } catch (e) {
                    console.error("Could not JSON.parse arguments", actionData.args);
                }
            }
            def = this._rpc({
                route: '/web/dataset/call_button',
                params: {
                    args: args,
                    kwargs: {context: context.eval()},
                    method: actionData.name,
                    model: env.model,
                },
            });
        } else if (actionData.type === 'action') {
            // execute a given action, so load it first
            def = this._loadAction(actionData.name, _.extend(pyUtils.eval('context', context), {
                active_model: env.model,
                active_ids: env.resIDs,
                active_id: recordID,
            }));
        } else {
            def = Promise.reject();
        }

        // use the DropPrevious to prevent from executing the handler if another
        // request (doAction, switchView...) has been done meanwhile ; execute
        // the fail handler if the 'call_button' or 'loadAction' failed but not
        // if the request failed due to the DropPrevious,
        def.guardedCatch(ev.data.on_fail);
        this.dp.add(def).then(function (action) {
            // show effect if button have effect attribute
            // rainbowman can be displayed from two places: from attribute on a button or from python
            // code below handles the first case i.e 'effect' attribute on button.
            var effect = false;
            if (actionData.effect) {
                effect = pyUtils.py_eval(actionData.effect);
            }

            if (action && action.constructor === Object) {
                // filter out context keys that are specific to the current action, because:
                //  - wrong default_* and search_default_* values won't give the expected result
                //  - wrong group_by values will fail and forbid rendering of the destination view
                var ctx = new Context(
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
            var options = {on_close: ev.data.on_closed};
            if (config.device.isMobile && actionData.mobile) {
                options = Object.assign({}, options, actionData.mobile);
            }
            return self.doAction(action, options).then(ev.data.on_success, ev.data.on_fail);
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.data.controllerID the id of the controller that
     *   triggered the event
     * @param {string} ev.data.viewType the type of view to switch to
     * @param {integer} [ev.data.res_id] the id of the record to open (for
     *   mono-record views)
     * @param {mode} [ev.data.mode] the mode to open, i.e. 'edit' or 'readonly'
     *   (only relevant for form views)
     */
    _onSwitchView: function (ev) {
        ev.stopPropagation();
        const viewType = ev.data.view_type;
        const currentController = this.getCurrentController();
        if (currentController.jsID === ev.data.controllerID) {
            // only switch to the requested view if the controller that
            // triggered the request is the current controller
            const action = this.actions[currentController.actionID];
            const currentControllerState = currentController.widget.exportState();
            action.controllerState = _.extend({}, action.controllerState, currentControllerState);
            const options = {
                controllerState: action.controllerState,
                currentId: ev.data.res_id,
            };
            if (ev.data.mode) {
                options.mode = ev.data.mode;
            }
            this._switchController(action, viewType, options);
        }
    },
});

});
