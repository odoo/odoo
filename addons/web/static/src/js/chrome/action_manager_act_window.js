odoo.define('web.ActWindowActionManager', function (require) {
    "use strict";

    /**
     * The purpose of this file is to add the support of Odoo actions of type
     * 'ir.actions.act_window' to the ActionManager.
     */

    const ActionManager = require('web.ActionManager');
    const { action_registry } = require('web.core');
    const viewRegistry = require('web.view_registry');

    class WindowActionPlugin extends ActionManager.AbstractPlugin {
        constructor() {
            super(...arguments);
            this.env.bus.on('switch-view', this, this._onSwitchView);
        }

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        loadState(state, options) {
            let action;
            if (state.action) {
                const x = this._getCurrentAction(); // FIXME
                const currentAction = x.action;
                const currentController = x.controller;
                if (currentAction && currentAction.id === state.action &&
                    currentAction.type === 'ir.actions.act_window') {
                    // the action to load is already the current one, so update it
                    // this._closeDialog(true); // there may be a currently opened dialog, close it // FIXME
                    var viewOptions = {currentId: state.id};
                    var viewType = state.view_type || currentController.viewType;
                    return this._switchController(currentAction, viewType, viewOptions);
                } else if (!action_registry.contains(state.action)) {
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
                    options = Object.assign(options, {
                        additional_context: context,
                        resID: state.id || undefined, // empty string with bbq
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
                const storedAction = this.env.services.session_storage.getItem('current_action');
                const lastAction = JSON.parse(storedAction || '{}');
                if (lastAction.res_model === state.model) {
                    action = lastAction;
                    options.viewType = state.view_type;
                }
            }
            if (action) {
                return this.doAction(action, options);
            }
        }

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
         */
        _createViewController(action, viewType, viewOptions, options) {
            options = options || {};
            if (action.controllers[viewType]) {
                action.controller = action.controllers[viewType];
                action.controller.viewOptions.breadcrumbs = this._getBreadcrumbs(options.virtualStack || this.currentStack.slice(0, action.controller.index));
                if (action.controllerState && action.controllerState.currentId) {
                   action.controller.viewOptions.currentId = action.controllerState.currentId;
                }
                delete action.controller.viewOptions.mode;
                Object.assign(action.controller.viewOptions, viewOptions);
                return;
            }

            const viewDescr = action.views.find(view => view.type === viewType);
            // FIXME
            if (!viewDescr) {
                return this.restoreController();
            }

            const index = options.index || 0;
            const controllerID = options.controllerID || this._nextID('controller');
            // build the view options from different sources
            const flags = action.flags || {};
            viewOptions = Object.assign({}, flags, flags[viewType], viewOptions, {
                action: action,
                breadcrumbs: this._getBreadcrumbs(options.virtualStack || this.currentStack.slice(0, index)),
                // pass the controllerID to the views as an hook for further communication
                controllerID: controllerID,
            });
            action.controller = {
                actionID: action.jsID,
                className: 'o_act_window', // used to remove the padding in dialogs
                Component: viewDescr.View,
                index: index,
                jsID: controllerID,
                viewType: viewType,
                viewOptions: viewOptions,
            };
            action.controllers[viewType] = action.controller;
        }
        /**
         * Executes actions of type 'ir.actions.act_window'.
         *
         * @override
         * @param {Object} action the description of the action to execute
         * @param {Array} action.views list of tuples [viewID, viewType]
         * @param {Object} options @see doAction for details
         * @param {integer} [options.resID] the current res ID
         * @param {string} [options.viewType] the view to open
         * @returns {Promise} resolved when the action is appended to the DOM
         */
        async executeAction(action, options) {
            const fieldsViews = await this._resolveLast(this._loadViews(action));
            const views = this._generateActionViews(action, fieldsViews);
            action._views = action.views; // save the initial attribute
            action.views = views;
            action.controlPanelFieldsView = fieldsViews.search;
            action.controllers = {};
            // select the current view to display, and optionally the main view
            // of the action which will be lazyloaded
            let curView = options.viewType && views.find(view => view.type === options.viewType);
            let lazyView;
            if (curView) {
                if (!curView.multiRecord && views[0].multiRecord) {
                    lazyView = views[0];
                }
            } else {
                curView = views[0];
            }
            // use mobile-friendly view by default in mobile, if possible
            if (this.env.device.isMobile) {
                if (!curView.isMobileFriendly) {
                    curView = this._findMobileView(views, curView.multiRecord) || curView;
                }
                if (lazyView && !lazyView.isMobileFriendly) {
                    lazyView = this._findMobileView(views, lazyView.multiRecord) || lazyView;
                }
            }

            let index = this._getControllerStackIndex(options);
            const virtualStack = this.currentStack.slice(0, index);

            let lazyControllerID;
            if (lazyView) {
                this._createViewController(action, lazyView.type, {controllerState: options.controllerState}, {
                    index,
                    virtualStack,
                });
                action.controller.options = options;
                this.controllers[action.controller.jsID] = action.controller;
                virtualStack.push(action.controller.jsID);
                index += 1;
                lazyControllerID = action.controller.jsID;
            }

            const viewOptions = {
                controllerState: options.controllerState,
                currentId: options.resID,
            };
            this._createViewController(action, curView.type, viewOptions, { index, virtualStack });
            action.controller.options = options;
            this._pushController(action.controller, () => {
                // FIXME: can we find a better way?
                if (lazyControllerID) {
                    this.currentStack.splice(this.currentStack.length - 1, 0, lazyControllerID);
                }
            });
        }
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
        _findMobileView(views, multiRecord) {
            return views.find(view => view.isMobileFriendly && view.multiRecord === multiRecord);
        }
        /**
         * Generate the description of the views of a given action. For each view,
         * it generates a dict with information like the fieldsView, the view type,
         * the Component to use...
         *
         * @private
         * @param {Object} action
         * @param {Object} fieldsViews
         * @returns {Object}
         */
        _generateActionViews(action, fieldsViews) {
            const views = [];
            action.views.forEach(view => {
                const viewType = view[1];
                const fieldsView = fieldsViews[viewType];
                const parsedXML = new DOMParser().parseFromString(fieldsView.arch, "text/xml");
                const key = parsedXML.documentElement.getAttribute('js_class');
                const View = viewRegistry.get(key || viewType);
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
                        View: View,
                    });
                } else if (this.env.isDebug('assets')) {
                    console.log("View type '" + viewType + "' is not present in the view registry.");
                }
            });
            return views;
        }
        /**
         * Loads the fields_views and fields for the given action.
         *
         * @private
         * @param {Object} action
         * @returns {Promise}
         */
        _loadViews(action) {
            const inDialog = action.target === 'new';
            const inline = action.target === 'inline';
            const options = {
                action_id: action.id,
                toolbar: !inDialog && !inline,
            };
            const views = action.views.slice();
            if (!inline && !(inDialog && action.views[0][1] === 'form')) {
                options.load_filters = true;
                const searchviewID = action.search_view_id && action.search_view_id[0];
                views.push([searchviewID || false, 'search']);
            }
            const params = {
                model: action.res_model,
                context: action.context,
                views_descr: views,
            };
            return this._resolveLast(this.env.dataManager.load_views(params, options)); // remove _resolveLast
        }
        /**
         * Overrides to handle the case where the controller to restore is from an
         * 'ir.actions.act_window' action. In this case we simply switch to this
         * controller.
         *
         * For instance, when going back to the list controller from a form
         * controller of the same action using the breadcrumbs, the form controller
         * is kept, as it might be reused in the future.
         *
         * @override
         * @private
         */
        restoreControllerHook(action, controller) {
            this._switchController(action, controller.viewType);
        }
        /**
         * Handles the switch from a controller to another (either inside the same
         * window action, or from a window action to another using the breadcrumbs).
         *
         * @private
         * @param {Object} controller the controller to switch to
         * @param {Object} [viewOptions]
         */
        _switchController(action, viewType, viewOptions) {
            var viewDescr = action.views.find(view => view.type === viewType);

            const currentControllerID = this.currentStack[this.currentStack.length - 1];
            const currentController = this.controllers[currentControllerID];
            let index;
            if (currentController.actionID === action.jsID) {
                // the requested controller is from the same action as the current
                // one, so we either
                //   1) go one step back from a mono record view to a multi record
                //      one using the breadcrumbs
                //   2) or we switched from a view to another  using the view
                //      switcher
                //   3) or we opened a record from a multi record view
                if (viewDescr && viewDescr.multiRecord) {
                    // cases 1) and 2) (with multi record views): replace the first
                    // controller linked to the same action in the stack
                    index = _.findIndex(this.currentStack, controllerID => {
                        return this.controllers[controllerID].actionID === action.jsID;
                    });
                } else if (!viewDescr || !_.findWhere(action.views, {type: currentController.viewType}).multiRecord) {
                    // case 2) (with mono record views): replace the last
                    // controller by the new one if they are from the same action
                    // and if they both are mono record
                    index = this.currentStack.length - 1;
                } else {
                    // case 3): insert the controller on the top of the controller
                    // stack
                    index = this.currentStack.length;
                }
            } else {
                // the requested controller is from another action, so we went back
                // to a previous action using the breadcrumbs
                index = this.currentStack.findIndex(controllerID => {
                    const c = this.controllers[controllerID];
                    return c.viewType === viewType && c.actionID === action.jsID;
                });
            }

            this._createViewController(action, viewType, viewOptions, { index });
            this._pushController(action.controller);

            // var newController = function (controllerID) {
            //     var options = {
            //         controllerID: controllerID,
            //         index: index,
            //     };
            //     return self
            //         ._createViewController(action, viewType, viewOptions, options)
            //         .then(function (controller) {
            //             return self._startController(controller);
            //         });
            // };

            // var controllerDef = action.controllers[viewType];
            // if (controllerDef) {
            //     controllerDef = controllerDef.then(function (controller) {
            //         if (!controller.widget) {
            //             // lazy loaded -> load it now (with same jsID)
            //             return newController(controller.jsID);
            //         } else {
            //             return Promise.resolve(controller.widget.willRestore()).then(function () {
            //                 viewOptions = _.extend({}, viewOptions, {
            //                     breadcrumbs: self._getBreadcrumbs(self.controllerStack.slice(0, index)),
            //                     shouldUpdateControlPanel: true, // FIXME: aab rebase
            //                 });
            //                 return controller.widget.reload(viewOptions).then(function () {
            //                     return controller;
            //                 });
            //             });
            //         }
            //     }, function () {
            //         // if the controllerDef is rejected, it probably means that the js
            //         // code or the requests made to the server crashed.  In that case,
            //         // if we reuse the same promise, then the switch to the view is
            //         // definitely blocked.  We want to use a new controller, even though
            //         // it is very likely that it will recrash again.  At least, it will
            //         // give more feedback to the user, and it could happen that one
            //         // record crashes, but not another.
            //         return newController();
            //     });
            // } else {
            //     controllerDef = newController();
            // }

            // return this.dp.add(controllerDef).then(function (controller) {
            //     return self._pushController(controller);
            // });
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {Object} payload
         * @param {string} payload.controllerID the id of the controller that
         *   triggered the event
         * @param {string} payload.viewType the type of view to switch to
         * @param {integer} [payload.res_id] the id of the record to open (for
         *   mono-record views)
         * @param {mode} [payload.mode] the mode to open, i.e. 'edit' or 'readonly'
         *   (only relevant for form views)
         */
        _onSwitchView(payload) {
            const viewType = payload.view_type;
            const { action } = this._getCurrentAction();
            // TODO: find a way to save/restore state
            // const currentController = action.controller;
            // var currentControllerState = currentController.widget.exportState();
            // action.controllerState = _.extend({}, action.controllerState, currentControllerState);
            const options = {
                // controllerState: action.controllerState,
                currentId: payload.res_id,
            };
            if (payload.mode) {
                options.mode = payload.mode;
            }
            console.log('switch view', viewType);
            this._switchController(action, viewType, options);
        }
    }
    WindowActionPlugin.type = 'ir.actions.act_window';
    ActionManager.registerPlugin(WindowActionPlugin);

    return WindowActionPlugin;

});
