odoo.define('web.AbstractController', function (require) {
"use strict";

/**
 * The Controller class is the class coordinating the model and the renderer.
 * It is the C in MVC, and is what was formerly known in Odoo as a View.
 *
 * Its role is to listen to events bubbling up from the model/renderer, and call
 * the appropriate methods if necessary.  It also render control panel buttons,
 * and react to changes in the search view.  Basically, all interactions from
 * the renderer/model with the outside world (meaning server/reading in session/
 * reading localstorage, ...) has to go through the controller.
 */

var ActionMixin = require('web.ActionMixin');
var ajax = require('web.ajax');
var concurrency = require('web.concurrency');
const { ComponentWrapper } = require('web.OwlCompatibility');
const ControlPanel = require('web.ControlPanel');
var mvc = require('web.mvc');
var session = require('web.session');


var AbstractController = mvc.Controller.extend(ActionMixin, {
    custom_events: _.extend({}, ActionMixin.custom_events, {
        navigation_move: '_onNavigationMove',
        open_record: '_onOpenRecord',
        search_panel_domain_updated: '_onSearchPanelDomainUpdated',
        switch_view: '_onSwitchView',
    }),
    events: {
        'click a[type="action"]': '_onActionClicked',
    },

    /**
     * @param {Object} param
     * @param {Object[]} params.actionViews
     * @param {string} params.activeActions
     * @param {string} params.bannerRoute
     * @param {Array[]} params.controlPanelDomain
     * @param {ControlPanelModel} [params.controlPanelModel]
     * @param {Object} [params.controlPanelProps]
     * @param {string} params.controllerID an id to ease the communication with
     *      upstream components
     * @param {string} params.displayName
     * @param {Object} params.initialState
     * @param {string} params.modelName
     * @param {string} [params.searchPanel]
     * @param {string} params.viewType
     * @param {boolean} [params.withControlPanel]
     * @param {boolean} [params.withSearchPanel]
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this._title = params.displayName;
        this.modelName = params.modelName;
        this.activeActions = params.activeActions;
        this.controllerID = params.controllerID;
        this.initialState = params.initialState;
        this.bannerRoute = params.bannerRoute;
        this.actionViews = params.actionViews;
        this.viewType = params.viewType;
        // use a DropPrevious to correctly handle concurrent updates
        this.dp = new concurrency.DropPrevious();

        this.withControlPanel = params.withControlPanel;
        if (this.withControlPanel) {
            this.controlPanelProps = params.controlPanelProps;
            this._controlPanelModel = params.controlPanelModel;
        }

        this.withSearchPanel = params.withSearchPanel && params.searchPanel;
        // the following attributes are used when there is a searchPanel
        if (this.withSearchPanel) {
            this._searchPanel = params.searchPanel;
        }
        this.controlPanelDomain = params.controlPanelDomain || [];
        this.searchPanelDomain = this._searchPanel ? this._searchPanel.getDomain() : [];
    },

    /**
     * Simply renders and updates the url.
     *
     * @returns {Promise}
     */
    start: async function () {
        if (this.withSearchPanel) {
            this.$('.o_content')
                .addClass('o_controller_with_searchpanel')
                .prepend(this._searchPanel.$el);
        }
        this.$el.addClass('o_view_controller');

        this.renderButtons();
        const promises = [this._super(...arguments)];
        if (this.withControlPanel) {
            this._updateControlPanelProps(this.initialState);
            this._controlPanelWrapper = new ComponentWrapper(this, ControlPanel, this.controlPanelProps);
            this._controlPanelWrapper.env.bus.on('focus-view', this, () => this.renderer.giveFocus());
            promises.push(this._controlPanelWrapper.mount(this.el, { position: 'first-child' }));
        }
        await Promise.all(promises);
        await this._update(this.initialState, { shouldUpdateControlPanel: false });
        this.updateButtons();
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$buttons) {
            this.$buttons.off();
        }
        ActionMixin.destroy.call(this);
        this._super.apply(this, arguments);
    },
    /**
     * Called each time the controller is attached into the DOM.
     */
    on_attach_callback: function () {
        ActionMixin.on_attach_callback.call(this);
        if (this.withSearchPanel) {
            this._searchPanel.on_attach_callback();
        }
        if (this.withControlPanel) {
            this._controlPanelModel.on('search', this, this._onSearch);
            this._controlPanelModel.on('get-controller-query-params', this, this._onGetOwnedQueryParams);
        }
        this.renderer.on_attach_callback();
    },
    /**
     * Called each time the controller is detached from the DOM.
     */
    on_detach_callback: function () {
        ActionMixin.on_detach_callback.call(this);
        if (this.withControlPanel) {
            this._controlPanelModel.off('search', this);
            this._controlPanelModel.off('get-controller-query-params', this);
        }
        this.renderer.on_detach_callback();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    canBeRemoved: function () {
        // AAB: get rid of 'readonlyIfRealDiscard' option when on_hashchange mechanism is improved
        return this.discardChanges(undefined, {
            noAbandon: true,
            readonlyIfRealDiscard: true,
        });
    },
    /**
     * Discards the changes made on the record associated to the given ID, or
     * all changes made by the current controller if no recordID is given. For
     * example, when the user opens the 'home' screen, the action manager calls
     * this method on the active view to make sure it is ok to open the home
     * screen (and lose all current state).
     *
     * Note that it returns a Promise, because the view could choose to ask the
     * user if he agrees to discard.
     *
     * @param {string} [recordID]
     *        if not given, we consider all the changes made by the controller
     * @param {Object} [options]
     * @returns {Promise} resolved if properly discarded, rejected otherwise
     */
    discardChanges: function (recordID, options) {
        return Promise.resolve();
    },
    /**
     * Export the state of the controller containing information that is shared
     * between different controllers of a same action (like the current
     * searchQuery of the controlPanel).
     *
     * @returns {Object}
     */
    exportState: function () {
        var state = {};
        if (this.withControlPanel) {
            state.cpState = this._controlPanelModel.exportState();
        }
        if (this.withSearchPanel) {
            state.spState = this._searchPanel.exportState();
        }
        return state;
    },
    /**
     * Gives the focus to the renderer
     */
    giveFocus: function () {
        this.renderer.giveFocus();
    },
    /**
     * The use of this method is discouraged.  It is still snakecased, because
     * it currently is used in many templates, but we will move to a simpler
     * mechanism as soon as we can.
     *
     * @deprecated
     * @param {string} action type of action, such as 'create', 'read', ...
     * @returns {boolean}
     */
    is_action_enabled: function (action) {
        return this.activeActions[action];
    },
    /**
     * Short helper method to reload the view
     *
     * @param {Object} [params={}] This object will simply be given to the update
     * @returns {Promise}
     */
    reload: async function (params = {}) {
        let searchPanelUpdateProm;
        const controllerState = params.controllerState || {};
        const cpState = controllerState.cpState;
        if (this.withControlPanel && cpState) {
            this._controlPanelModel.importState(cpState);
            const searchQuery = this._controlPanelModel.getQuery();
            params = Object.assign({}, params, searchQuery);
        }
        let postponeRendering = false;
        if (this.withSearchPanel) {
            this.controlPanelDomain = params.domain || this.controlPanelDomain;
            if (controllerState.spState) {
                this._searchPanel.importState(controllerState.spState);
                this.searchPanelDomain = this._searchPanel.getDomain();
            } else {
                const viewDomain = await this._getViewDomain();
                searchPanelUpdateProm =  this._searchPanel.update({
                    searchDomain: this.controlPanelDomain,
                    viewDomain,
                });
                postponeRendering = !params.noRender;
                params.noRender = true; // wait for searchpanel to be ready to render
            }
            params.domain = this.controlPanelDomain.concat(this.searchPanelDomain);
        }
        await Promise.all([this.update(params, {}), searchPanelUpdateProm]);
        if (postponeRendering) {
            return this.renderer._render();
        }
    },
    /**
     * This is the main entry point for the controller.  Changes from the search
     * view arrive in this method, and internal changes can sometimes also call
     * this method.  It is basically the way everything notifies the controller
     * that something has changed.
     *
     * The update method is responsible for fetching necessary data, then
     * updating the renderer and wait for the rendering to complete.
     *
     * @param {Object} params will be given to the model and to the renderer
     * @param {Object} [options]
     * @param {boolean} [options.reload=true] if true, the model will reload data
     *
     * @returns {Promise}
     */
    update: async function (params, options = {}) {
        const shouldReload = 'reload' in options ? options.reload : true;
        if (shouldReload) {
            this.handle = await this.dp.add(this.model.reload(this.handle, params));
        }
        const localState = this.renderer.getLocalState();
        const state = this.model.get(this.handle);
        const promises = [
            this.updateRendererState(state, params).then(() => {
                this.renderer.setLocalState(localState);
            }),
            this._update(state, params),
        ];
        await this.dp.add(Promise.all(promises));
        this.updateButtons();
    },
    /**
     * Update the state of the renderer (handle both Widget and Component
     * renderers).
     *
     * @param {Object} state the model state
     * @param {Object} params will be given to the model and to the renderer
     */
    updateRendererState: function (state, params) {
        if (this.renderer instanceof owl.Component) {
            return this.renderer.update(state);
        }
        return this.renderer.updateState(state, params);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------


    /**
     * Meant to be overriden to return a proper object.
     * @private
     * @param {Object} [state]
     * @return {(Object|null)}
     */
    _getPagingInfo: function (state) {
        return null;
    },
    /**
     * Get the domain defined by the view. It is meant to be overridden.
     *
     * @private
     * @returns {Promise<Array[]>}
     */
    _getViewDomain: async function () {
        return [];
    },
    /**
     * Meant to be overriden to return a proper object.
     * @private
     * @param {Object} [state]
     * @return {(Object|null)}
     */
    _getActionMenuItems: function (state) {
        return null;
    },
    /**
     * This method is the way a view can notifies the outside world that
     * something has changed.  The main use for this is to update the url, for
     * example with a new id.
     *
     * @private
     */
    _pushState: function () {
        this.trigger_up('push_state', {
            controllerID: this.controllerID,
            state: this.getState(),
        });
    },
    /**
     * Renders the html provided by the route specified by the
     * bannerRoute attribute on the controller (banner_route in the template).
     * Renders it before the view output and add a css class 'o_has_banner' to it.
     * There can be only one banner displayed at a time.
     *
     * If the banner contains stylesheet links or js files, they are moved to <head>
     * (and will only be fetched once).
     *
     * Route example:
     * @http.route('/module/hello', auth='user', type='json')
     * def hello(self):
     *     return {'html': '<h1>hello, world</h1>'}
     *
     * @private
     * @returns {Promise}
     */
    _renderBanner: async function () {
        if (this.bannerRoute !== undefined) {
            const response = await this._rpc({route: this.bannerRoute});
            if (!response.html) {
                this.$el.removeClass('o_has_banner');
                return Promise.resolve();
            }
            this.$el.addClass('o_has_banner');
            var $banner = $(response.html);
            // we should only display one banner at a time
            if (this._$banner && this._$banner.remove) {
                this._$banner.remove();
            }
            // Css and js are moved to <head>
            var defs = [];
            $('link[rel="stylesheet"]', $banner).each(function (i, link) {
                defs.push(ajax.loadCSS(link.href));
                link.remove();
            });
            $('script[type="text/javascript"]', $banner).each(function (i, js) {
                defs.push(ajax.loadJS(js.src));
                js.remove();
            });
            await Promise.all(defs);
            $banner.insertBefore(this.$('> .o_content'));
            this._$banner = $banner;
        }
    },
    /**
     * @override
     * @private
     */
    _startRenderer: function () {
        if (this.renderer instanceof owl.Component) {
            return this.renderer.mount(this.$('.o_content')[0]);
        }
        return this.renderer.appendTo(this.$('.o_content'));
    },
    /**
     * This method is called after each update or when the start method is
     * completed.
     *
     * Its primary use is to be used as a hook to update all parts of the UI,
     * besides the renderer.  For example, it may be used to enable/disable
     * some buttons in the control panel, such as the current graph type for a
     * graph view.
     *
     * @private
     * @param {Object} state the state given by the model
     * @param {Object} [params={}]
     * @param {Object} [params.shouldUpdateControlPanel]
     * @returns {Promise}
     */
    _update: function (state, params) {
        // AAB: update the control panel -> this will be moved elsewhere at some point
        if (!this.$buttons) {
            this.renderButtons();
        }
        const promises = [this._renderBanner()];
        if (this.withControlPanel && params.shouldUpdateControlPanel !== false) {
            this._updateControlPanelProps(state);
            if (params.breadcrumbs) {
                this.controlPanelProps.breadcrumbs = params.breadcrumbs;
            }
            promises.push(this.updateControlPanel());
        }
        this._pushState();
        return Promise.all(promises);
    },
    /**
     * Can be used to update the key 'cp_content'. This method is called in start and _update methods.
     *
     * @private
     * @param {Object} state the state given by the model
     */
     _updateControlPanelProps(state) {
        if (!this.controlPanelProps.cp_content) {
            this.controlPanelProps.cp_content = {};
        }
        if (this.$buttons) {
            this.controlPanelProps.cp_content.$buttons = this.$buttons;
        }
        Object.assign(this.controlPanelProps, {
            actionMenus: this._getActionMenuItems(state),
            pager: this._getPagingInfo(state),
            title: this.getTitle(),
        });
    },
    /**
     * @private
     * @param {Object} state
     * @param {Object} newProps
     * @returns {Promise}
     */
    _updatePaging: async function (state, newProps) {
        const pagingInfo = this._getPagingInfo(state);
        if (pagingInfo) {
            Object.assign(pagingInfo, newProps);
            return this.updateControlPanel({ pager: pagingInfo });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When a user clicks on an <a> link with type="action", we need to actually
     * do the action. This kind of links is used a lot in no-content helpers.
     *
     * * if the link has both data-model and data-method attributes, the
     *   corresponding method is called, chained to any action it would
     *   return. An optional data-reload-on-close (set to a non-falsy value)
     *   also causes th underlying view to be reloaded after the dialog is
     *   closed.
     * * if the link has a name attribute, invoke the action with that
     *   identifier (see :class:`ActionManager.doAction` to not get the
     *   details)
     * * otherwise an *action descriptor* is built from the link's data-
     *   attributes (model, res-id, views, domain and context)
     *
     * @private
     * @param ev
     */
    _onActionClicked: function (ev) { // FIXME: maybe this should also work on <button> tags?
        ev.preventDefault();
        var $target = $(ev.currentTarget);
        var self = this;
        var data = $target.data();

        if (data.method !== undefined && data.model !== undefined) {
            var options = {};
            if (data.reloadOnClose) {
                options.on_close = function () {
                    self.trigger_up('reload');
                };
            }
            this.dp.add(this._rpc({
                model: data.model,
                method: data.method,
                context: session.user_context,
            })).then(function (action) {
                if (action !== undefined) {
                    self.do_action(action, options);
                }
            });
        } else if ($target.attr('name')) {
            this.do_action(
                $target.attr('name'),
                data.context && {additional_context: data.context}
            );
        } else {
            this.do_action({
                name: $target.attr('title') || _.str.strip($target.text()),
                type: 'ir.actions.act_window',
                res_model: data.model || this.modelName,
                res_id: data.resId,
                target: 'current', // TODO: make customisable?
                views: data.views || (data.resId ? [[false, 'form']] : [[false, 'list'], [false, 'form']]),
                domain: data.domain || [],
            }, {
                additional_context: _.extend({}, data.context)
            });
        }
    },
    /**
     * Called either from the control panel to focus the controller
     * or from the view to focus the search bar
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onNavigationMove: function (ev) {
        switch (ev.data.direction) {
            case 'up':
                ev.stopPropagation();
                this._controlPanelModel.trigger('focus-control-panel');
                break;
            case 'down':
                ev.stopPropagation();
                this.giveFocus();
                break;
        }
    },
    /**
     * When an Odoo event arrives requesting a record to be opened, this method
     * gets the res_id, and request a switch view in the appropriate mode
     *
     * Note: this method seems wrong, it relies on the model being a basic model,
     * to get the res_id.  It should receive the res_id in the event data
     * @todo move this to basic controller?
     *
     * @private
     * @param {OdooEvent} ev
     * @param {number} ev.data.id The local model ID for the record to be
     *   opened
     * @param {string} [ev.data.mode='readonly']
     */
    _onOpenRecord: function (ev) {
        ev.stopPropagation();
        var record = this.model.get(ev.data.id, {raw: true});
        this.trigger_up('switch_view', {
            view_type: 'form',
            res_id: record.res_id,
            mode: ev.data.mode || 'readonly',
            model: this.modelName,
        });
    },
    /**
     * Called when there is a change in the search view, so the current action's
     * environment needs to be updated with the new domain, context, groupby,...
     *
     * @private
     * @param {Object} searchQuery
     */
    _onSearch: function (searchQuery) {
        this.reload(_.extend({ offset: 0, groupsOffset: 0 }, searchQuery));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Array[]} ev.data.domain the current domain of the searchPanel
     */
    _onSearchPanelDomainUpdated: function (ev) {
        this.searchPanelDomain = ev.data.domain;
        this.reload({offset: 0});
    },
    /**
     * Intercepts the 'switch_view' event to add the controllerID into the data,
     * and lets the event bubble up.
     *
     * @param {OdooEvent} ev
     */
    _onSwitchView: function (ev) {
        ev.data.controllerID = this.controllerID;
    },
});

return AbstractController;

});
