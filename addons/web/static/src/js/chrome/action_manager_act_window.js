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
var data = require('web.data'); // this will be removed at some point
var pyUtils = require('web.py_utils');
var SearchView = require('web.SearchView');
var view_registry = require('web.view_registry');

var _t = core._t;

ActionManager.include({
    custom_events: _.extend({}, ActionManager.prototype.custom_events, {
        env_updated: '_onEnvUpdated',
        execute_action: '_onExecuteAction',
        get_controller_context: '_onGetControllerContext',
        update_filters: '_onUpdateFilters',
        search: '_onSearch',
        switch_view: '_onSwitchView',
        navigation_move: '_onNavigationMove',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

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
                currentAction.env.currentId = state.id;
                var viewType = state.view_type || currentController.viewType;
                return this._switchController(currentAction, viewType);
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
                    context.active_ids = state.active_ids.split(',').map(function (id) {
                        return parseInt(id, 10) || id;
                    });
                } else if (state.active_id) {
                    context.active_ids = [state.active_id];
                }
                context.params = state;
                action = state.action;
                options = _.extend(options, {
                    additional_context: context,
                    resID: state.id,
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
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instantiates a search view for a given action, and starts it so that it
     * is ready to be appended to the DOM.
     *
     * @private
     * @param {Object} action
     * @returns {Deferred} resolved with the search view when it is ready
     */
    _createSearchView: function (action) {
        // if requested, keep the searchview of the current action instead of
        // creating a new one
        if (action._keepSearchView) {
            var currentAction = this.getCurrentAction();
            if (currentAction) {
                action.searchView = currentAction.searchView;
                action.env = currentAction.env; // make those actions share the same env
                return $.when(currentAction.searchView);
            } else {
                // there is not searchview to keep, so reset the flag to false
                // to ensure that the one that will be created will be correctly
                // destroyed
                action._keepSearchView = false;
            }
        }

        // AAB: temporarily create a dataset, until the SearchView is refactored
        // and stops using it
        var dataset = new data.DataSetSearch(this, action.res_model, action.context, action.domain);
        if (action.res_id) {
            dataset.ids.push(action.res_id);
            dataset.index = 0;
        }

        // find 'search_default_*' keys in actions's context
        var searchDefaults = {};
        _.each(action.context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                searchDefaults[match[1]] = value;
            }
        });
        var searchView = new SearchView(this, dataset, action.searchFieldsView, {
            $buttons: $('<div>'),
            action: action,
            disable_custom_filters: action.flags.disableCustomFilters,
            search_defaults: searchDefaults,
        });

        return searchView.appendTo(document.createDocumentFragment()).then(function () {
            action.searchView = searchView;
            return searchView;
        });
    },
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
     * @param {boolean} [options.lazy=false] set to true to differ the
     *   initialization of the controller's widget
     * @returns {Deferred<Object>} resolved with the created controller
     */
    _createViewController: function (action, viewType, viewOptions, options) {
        var self = this;
        var viewDescr = _.findWhere(action.views, {type: viewType});
        if (!viewDescr) {
            // the requested view type isn't specified in the action (e.g.
            // action with list view only, user clicks on a row in the list, it
            // tries to switch to form view)
            return $.Deferred().reject();
        }

        var controllerID = _.uniqueId('controller_');
        var controller = {
            actionID: action.jsID,
            className: 'o_act_window', // used to remove the padding in dialogs
            jsID: controllerID,
            viewType: viewType,
        };
        Object.defineProperty(controller, 'title', {
            get: function () {
                // handle the case where the widget is lazy loaded
                return controller.widget ? controller.widget.getTitle() : (action.display_name || action.name);
            },
        });
        this.controllers[controllerID] = controller;

        if (!options || !options.lazy) {
            // build the view options from different sources
            viewOptions = _.extend({
                action: action,
                limit: action.limit,
            }, action.flags, action.flags[viewType], viewOptions, action.env);
            // pass the controllerID to the views as an hook for further
            // communication with trigger_up (e.g. for 'env_updated' event)
            viewOptions = _.extend(viewOptions, { controllerID: controllerID });

            var view = new viewDescr.Widget(viewDescr.fieldsView, viewOptions);
            var def = $.Deferred();
            action.controllers[viewType] = def;
            view.getController(this).then(function (widget) {
                if (def.state() === 'rejected') {
                    // the deferred has been rejected meanwhile, meaning that
                    // the action has been removed, so simply destroy the widget
                    widget.destroy();
                } else {
                    controller.widget = widget;
                    def.resolve(controller);
                }
            }).fail(def.reject.bind(def));
            def.fail(function () {
                delete self.controllers[controllerID];
            });
        } else {
            action.controllers[viewType] = $.Deferred().resolve(controller);
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
        _.each(action.controllers, function (controllerDef) {
            controllerDef.then(function (controller) {
                delete self.controllers[controller.jsID];
                if (controller.widget) {
                    controller.widget.destroy();
                }
            });
            // reject the deferred if it is not yet resolved, so that the
            // controller is correctly destroyed as soon as it is ready, and
            // its reference is removed
            controllerDef.reject();
        });
        if (action.searchView && !action._keepSearchView) {
            action.searchView.destroy();
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
     * @returns {Deferred} resolved when the action is appended to the DOM
     */
    _executeWindowAction: function (action, options) {
        var self = this;

        if (action.context.active_id || action.context.active_ids) {
            // we assume that when 'active_id' or 'active_ids' is used in the
            // context, we are in a 'related' action, so we disable the
            // searchview's default custom filters
            action.context.search_disable_custom_filters = true;
        }
        action.flags = this._generateActionFlags(action);

        return this.dp.add(this._loadViews(action)).then(function (fieldsViews) {
            var views = self._generateActionViews(action, fieldsViews);
            action._views = action.views;  // save the initial attribute
            action.views = views;
            if (fieldsViews.search) {
                action.searchFieldsView = fieldsViews.search;
            }
            action.env = self._generateActionEnv(action, options);
            action.controllers = {};

            // select the first view to display, and optionally the main view
            // which will be lazyloaded
            var firstView = options.viewType && _.findWhere(views, {type: options.viewType});
            var mainView;
            if (firstView) {
                if (!firstView.multiRecord && views[0].multiRecord) {
                    mainView = views[0];
                }
            } else {
                firstView = views[0];
            }

            // use mobile-friendly view by default in mobile, if possible
            if (config.device.isMobile) {
                if (!firstView.isMobileFriendly) {
                    firstView = self._findMobileView(views, firstView.multiRecord) || firstView;
                }
                if (mainView && !mainView.isMobileFriendly) {
                    mainView = self._findMobileView(views, mainView.multiRecord) || mainView;
                }
            }

            var def;
            if (action.flags.hasSearchView) {
                def = self._createSearchView(action).then(function (searchView) {
                    // udpate domain, context and groupby in the env
                    var searchData = searchView.build_search_data();
                    _.extend(action.env, self._processSearchData(action, searchData));
                });
            }
            return $.when(def).then(function () {
                var defs = [];
                defs.push(self._createViewController(action, firstView.type));
                if (mainView) {
                    defs.push(self._createViewController(action, mainView.type, {}, {lazy: true}));
                }
                return self.dp.add($.when.apply($, defs));
            }).then(function (controller, lazyLoadedController) {
                action.controllerID = controller.jsID;
                return self._executeAction(action, options).done(function () {
                    if (lazyLoadedController) {
                        // controller should be placed just before the current one
                        var index = self.controllerStack.length - 1;
                        self.controllerStack.splice(index, 0, lazyLoadedController.jsID);
                        self.controlPanel.update({
                            breadcrumbs: self._getBreadcrumbs(),
                        }, {clear: false});
                    }
                });
            }).fail(self._destroyWindowAction.bind(self, action));
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
     * Generates the initial environment of a given action, which is a dict
     * containing information like the model name, the domain, the context...
     * That information is shared between the controllers of the corresponding
     * action.
     *
     * @private
     * @param {Object} action
     * @param {Object} options
     * @param {integer} [options.resID]
     * @returns {Object}
     */
    _generateActionEnv: function (action, options) {
        var resID = options.resID || action.res_id;
        return {
            modelName: action.res_model,
            ids: resID ? [resID] : undefined,
            currentId: resID || undefined,
            domain: [],
            context: action.context || {},
            groupBy: [],
        };
    },
    /**
     * Generates the flags of a given action.
     *
     * @private
     * @param {Object} action
     * @returns {Object}
     */
    _generateActionFlags: function (action) {
        var popup = action.target === 'new';
        var inline = action.target === 'inline';
        var form = action.views[0][1] === 'form';
        return _.defaults({}, action.flags, {
            disableCustomFilters: action.context && action.context.search_disable_custom_filters,
            footerToButtons: popup,
            hasSearchView: !(popup && form) && !inline,
            hasSidebar: !popup && !inline,
            headless: (popup || inline) && form,
            mode: (popup || inline || action.target === 'fullscreen') && 'edit',
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
            } else {
                console.error("View type '" + viewType + "' is not present in the view registry.");
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
     * @returns {Deferred}
     */
    _loadViews: function (action) {
        var options = {
            action_id: action.id,
            toolbar: action.flags.hasSidebar,
        };
        var views = action.views.slice();
        if (action.flags.hasSearchView) {
            options.load_filters = true;
            var searchviewID = action.search_view_id && action.search_view_id[0];
            views.push([searchviewID || false, 'search']);
        }
        return this.loadViews(action.res_model, action.context, views, options);
    },
    /**
     * Overrides to handle the 'keepSearchView' option. If set to true, the
     * search view of the current action will be re-used in the new action, i.e.
     * the environment (domain, context, groupby) will be shared between both
     * actions.
     *
     * @override
     */
    _preprocessAction: function (action, options) {
        this._super.apply(this, arguments);
        if (action.type === 'ir.actions.act_window' && options.keepSearchView) {
            action._keepSearchView = true;
        }
    },
    /**
     * Processes the search data sent by the search view.
     *
     * @private
     * @param {Object} action
     * @param {Object} searchData
     * @param {Object} [searchData.contexts=[]]
     * @param {Object} [searchData.domains=[]]
     * @param {Object} [searchData.groupbys=[]]
     * @returns {Object} an object with keys 'context', 'domain', 'groupBy'
     */
    _processSearchData: function (action, searchData) {
        var contexts = searchData.contexts;
        var domains = searchData.domains;
        var groupbys = searchData.groupbys;
        var action_context = action.context || {};
        var results = pyUtils.eval_domains_and_contexts({
            domains: [action.domain || []].concat(domains || []),
            contexts: [action_context].concat(contexts || []),
            group_by_seq: groupbys || [],
            eval_context: this.userContext,
        });
        var groupBy = results.group_by.length ?
                        results.group_by :
                        (action.context.group_by || []);
        groupBy = (typeof groupBy === 'string') ? [groupBy] : groupBy;

        if (results.error) {
            throw new Error(_.str.sprintf(_t("Failed to evaluate search criterions")+": \n%s",
                            JSON.stringify(results.error)));
        }

        var context = _.omit(results.context, 'time_ranges');

        return {
            context: context,
            domain: results.domain,
            groupBy: groupBy,
        };
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
                var def;
                if (action.on_reverse_breadcrumb) {
                    def = action.on_reverse_breadcrumb();
                }
                return $.when(def).then(function () {
                    return self._switchController(action, controller.viewType);
                });
            });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Handles the switch from a controller to another inside the same window
     * action.
     *
     * @private
     * @param {Object} controller the controller to switch to
     * @param {Object} [viewOptions]
     * @return {Deferred} resolved when the new controller is in the DOM
     */
    _switchController: function (action, viewType, viewOptions) {
        var self = this;

        var newController = function () {
            return self
                ._createViewController(action, viewType, viewOptions)
                .then(function (controller) {
                    // AAB: this will be moved to the Controller
                    var widget = controller.widget;
                    if (widget.need_control_panel) {
                        // set the ControlPanel bus on the controller to allow it to
                        // communicate its status
                        widget.set_cp_bus(self.controlPanel.get_bus());
                    }
                    return self._startController(controller);
                });
        };

        var controllerDef = action.controllers[viewType];
        if (!controllerDef || controllerDef.state() === 'rejected') {
            // if the controllerDef is rejected, it probably means that the js
            // code or the requests made to the server crashed.  In that case,
            // if we reuse the same deferred, then the switch to the view is
            // definitely blocked.  We want to use a new controller, even though
            // it is very likely that it will recrash again.  At least, it will
            // give more feedback to the user, and it could happen that one
            // record crashes, but not another.
            controllerDef = newController();
        } else {
            controllerDef = controllerDef.then(function (controller) {
                if (!controller.widget) {
                    // lazy loaded -> load it now
                    return newController().done(function (newController) {
                        // replace the old controller (without widget) by the new one
                        var index = self.controllerStack.indexOf(controller.jsID);
                        self.controllerStack[index] = newController.jsID;
                        delete self.controllers[controller.jsID];
                    });
                } else {
                    viewOptions = _.extend(viewOptions || {}, action.env);
                    return $.when(controller.widget.willRestore()).then(function () {
                        return controller.widget.reload(viewOptions).then(function () {
                            return controller;
                        });
                    });
                }
            });
        }

        return this.dp.add(controllerDef).then(function (controller) {
            var view = _.findWhere(action.views, {type: viewType});
            var currentController = self.getCurrentController();
            var index;
            if (currentController.actionID !== action.jsID) {
                index = _.indexOf(self.controllerStack, controller.jsID);
            } else if (view.multiRecord) {
                // remove other controllers linked to the same action from the stack
                index = _.findIndex(self.controllerStack, function (controllerID) {
                    return self.controllers[controllerID].actionID === action.jsID;
                });
            } else if (!_.findWhere(action.views, {type: currentController.viewType}).multiRecord) {
                // replace the last controller by the new one if they are from the
                // same action and if they both are mono record
                index = self.controllerStack.length - 1;
            }
            return self._pushController(controller, {index: index});
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.data.controllerID
     * @param {Object} ev.data.env
     */
    _onEnvUpdated: function (ev) {
        ev.stopPropagation();
        var controller = this.controllers[ev.data.controllerID];
        var action = this.actions[controller.actionID];
        _.extend(action.env, ev.data.env);
    },
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
        var def = $.Deferred();

        // determine the action to execute according to the actionData
        if (actionData.special) {
            def = $.when({type: 'ir.actions.act_window_close', infos: 'special'});
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
            args.push(context.eval());
            def = this._rpc({
                route: '/web/dataset/call_button',
                params: {
                    args: args,
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
        }

        // use the DropPrevious to prevent from executing the handler if another
        // request (doAction, switchView...) has been done meanwhile ; execute
        // the fail handler if the 'call_button' or 'loadAction' failed but not
        // if the request failed due to the DropPrevious,
        def.fail(ev.data.on_fail);
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
            return self.doAction(action, options).then(ev.data.on_success, ev.data.on_fail);
        });
    },
    /**
     * Handles a context request: provides to the caller the context of the
     * current controller.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {function} ev.data.callback used to send the requested context
     */
    _onGetControllerContext: function (ev) {
        ev.stopPropagation();
        var currentController = this.getCurrentController();
        var context = currentController && currentController.widget.getContext();
        ev.data.callback(context || {});
    },
    /**
     * Handles a request to add/remove search view filters.
     *
     * @param {OdooEvent} ev
     * @param {string} ev.data.controllerID
     * @param {Array[Object]} [ev.data.newFilters]
     * @param {Array[Object]} [ev.data.filtersToRemove]
     * @param {function} ev.data.callback called with the added filters as arg
     */
    _onUpdateFilters: function (ev) {
        var controller = this.controllers[ev.data.controllerID];
        var action = this.actions[controller.actionID];
        var data = ev.data;
        var addedFilters = action.searchView.updateFilters(data.newFilters, data.filtersToRemove);
        data.callback(addedFilters);
    },
    /**
     * Called mainly from the control panel when the focus should be given to a controller
     * 
     * @param {OdooEvent} event
     * @private
     */
    _onNavigationMove : function(event) {
        switch(event.data.direction) {
            case 'down' :
                var currentController = this.getCurrentController().widget;
                currentController.giveFocus();
                event.stopPropagation();
                break;
        }
    },
    /**
     * Called when there is a change in the search view, so the current action's
     * environment needs to be updated with the new domain, context and groupby.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSearch: function (ev) {
        ev.stopPropagation();
        // AAB: the id of the correct controller should be given in data
        var currentController = this.getCurrentController();
        var action = this.actions[currentController.actionID];
        _.extend(action.env, this._processSearchData(action, ev.data));
        currentController.widget.reload(_.extend({offset: 0}, action.env));
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
        var viewType = ev.data.view_type;
        var currentController = this.getCurrentController();
        if (currentController.jsID === ev.data.controllerID) {
            // only switch to the requested view if the controller that
            // triggered the request is the current controller
            var action = this.actions[currentController.actionID];
            if ('res_id' in ev.data) {
                action.env.currentId = ev.data.res_id;
            }
            var options = {};
            if (viewType === 'form' && !action.env.currentId) {
                options.mode = 'edit';
            } else if (ev.data.mode) {
                options.mode = ev.data.mode;
            }
            this._switchController(action, viewType, options);
        }
    },
});

});
