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

var ajax = require('web.ajax');
var concurrency = require('web.concurrency');
var config = require('web.config');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var AbstractAction = require('web.AbstractAction');

var session = require('web.session');

var QWeb = core.qweb;

var AbstractController = AbstractAction.extend(ControlPanelMixin, {
    custom_events: {
        open_record: '_onOpenRecord',
        switch_view: '_onSwitchView',
    },
    events: {
        'click a[type="action"]': '_onActionClicked',
    },

    /**
     * @constructor
     * @param {Widget} parent
     * @param {AbstractModel} model
     * @param {AbstractRenderer} renderer
     * @param {object} params
     * @param {string} params.modelName
     * @param {string} [params.controllerID] an id to ease the communication
     *   with upstream components
     * @param {any} [params.handle] a handle that will be given to the model (some id)
     * @param {any} params.initialState the initialState
     * @param {boolean} params.isMultiRecord
     * @param {Object[]} params.actionViews
     * @param {string} params.viewType
     * @param {boolean} params.withControlPanel set to false to hide the
     *   ControlPanel
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.model = model;
        this.renderer = renderer;
        this.modelName = params.modelName;
        this.handle = params.handle;
        this.activeActions = params.activeActions;
        this.controllerID = params.controllerID;
        this.initialState = params.initialState;
        this.bannerRoute = params.bannerRoute;
        // use a DropPrevious to correctly handle concurrent updates
        this.dp = new concurrency.DropPrevious();
        // those arguments are temporary, they won't be necessary as soon as the
        // ControlPanel will be handled by the View
        this.displayName = params.displayName;
        this.isMultiRecord = params.isMultiRecord;
        this.searchable = params.searchable;
        this.searchView = params.searchView;
        this.searchViewHidden = params.searchViewHidden;
        this.groupable = params.groupable;
        this.enableTimeRangeMenu = params.enableTimeRangeMenu;
        this.actionViews = params.actionViews;
        this.viewType = params.viewType;
        this.withControlPanel = params.withControlPanel !== false;
        // override this.need_control_panel so that the ActionManager doesn't
        // update the control panel when it isn't visible (this is a temporary
        // hack that can be removed as soon as the CP'll be handled by the view)
        this.need_control_panel = this.withControlPanel;
    },
    /**
     * Simply renders and updates the url.
     *
     * @returns {Deferred}
     */
    start: function () {
        var self = this;

        this.$el.addClass('o_view_controller');

        // render the ControlPanel elements (buttons, pager, sidebar...)
        this.controlPanelElements = this._renderControlPanelElements();

        return $.when(
            this._super.apply(this, arguments),
            this.renderer.appendTo(this.$el)
        ).then(function () {
            return self._update(self.initialState);
        });
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$buttons) {
            this.$buttons.off();
        }
        if (this.controlPanelElements && this.controlPanelElements.$switch_buttons) {
            this.controlPanelElements.$switch_buttons.off();
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Called each time the controller is attached into the DOM.
     */
    on_attach_callback: function () {
        if (this.searchView) {
            this.searchView.on_attach_callback();
        }
        this.renderer.on_attach_callback();
    },
    /**
     * Called each time the controller is detached from the DOM.
     */
    on_detach_callback: function () {
        this.renderer.on_detach_callback();
    },

    /**
     * Gives the focus to the renderer
     */
    giveFocus:function(){
        this.renderer.giveFocus();
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    canBeRemoved: function () {
        // AAB: get rid of this option when on_hashchange mechanism is improved
        return this.discardChanges(undefined, {readonlyIfRealDiscard: true});
    },
    /**
     * Discards the changes made on the record associated to the given ID, or
     * all changes made by the current controller if no recordID is given. For
     * example, when the user opens the 'home' screen, the action manager calls
     * this method on the active view to make sure it is ok to open the home
     * screen (and lose all current state).
     *
     * Note that it returns a deferred, because the view could choose to ask the
     * user if he agrees to discard.
     *
     * @param {string} [recordID]
     *        if not given, we consider all the changes made by the controller
     * @returns {Deferred} resolved if properly discarded, rejected otherwise
     */
    discardChanges: function (recordID) {
        return $.when();
    },
    /**
     * Returns any special keys that may be useful when reloading the view to
     * get the same effect.  This is necessary for saving the current view in
     * the favorites.  For example, a graph view might want to add a key to
     * save the current graph type.
     *
     * @returns {Object}
     */
    getContext: function () {
        return {};
    },
    /**
     * Returns a title that may be displayed in the breadcrumb area.  For
     * example, the name of the record.
     *
     * note: this will be moved to AbstractAction
     *
     * @returns {string}
     */
    getTitle: function () {
        return this.displayName;
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
     * @param {Object} [params] This object will simply be given to the update
     * @returns {Deferred}
     */
    reload: function (params) {
        return this.update(params || {});
    },
    /**
     * For views that require a pager, this method will be called to allow the
     * controller to instantiate and render a pager. Note that in theory, the
     * controller can actually render whatever he wants in the pager zone.  If
     * your view does not want a pager, just let this method empty.
     *
     * @param {jQuery Node} $node
     */
    renderPager: function ($node) {
    },
    /**
     * Same as renderPager, but for the 'sidebar' zone (the zone with the menu
     * dropdown in the control panel next to the buttons)
     *
     * @param {jQuery Node} $node
     */
    renderSidebar: function ($node) {
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
     * @returns {Deferred}
     */
    update: function (params, options) {
        var self = this;
        var shouldReload = (options && 'reload' in options) ? options.reload : true;
        var def = shouldReload ? this.model.reload(this.handle, params) : $.when();
        // we check here that the updateIndex of the control panel hasn't changed
        // between the start of the update request and the moment the controller
        // asks the control panel to update itself ; indeed, it could happen that
        // another action/controller is executed during this one reloads itself,
        // and if that one finishes first, it replaces this controller in the DOM,
        // and this controller should no longer update the control panel.
        // note that this won't be necessary as soon as each controller will have
        // its own control panel
        var cpUpdateIndex = this.cp_bus && this.cp_bus.updateIndex;
        return this.dp.add(def).then(function (handle) {
            if (self.cp_bus && cpUpdateIndex !== self.cp_bus.updateIndex) {
                return;
            }
            self.handle = handle || self.handle; // update handle if we reloaded
            var state = self.model.get(self.handle);
            var localState = self.renderer.getLocalState();
            return self.dp.add(self.renderer.updateState(state, params)).then(function () {
                if (self.cp_bus && cpUpdateIndex !== self.cp_bus.updateIndex) {
                    return;
                }
                self.renderer.setLocalState(localState);
                return self._update(state);
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This method is the way a view can notifies the outside world that
     * something has changed.  The main use for this is to update the url, for
     * example with a new id.
     *
     * @private
     * @param {Object} [state] information that will be pushed to the outside
     *   world
     */
    _pushState: function (state) {
        this.trigger_up('push_state', {
            controllerID: this.controllerID,
            state: state || {},
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
    * @returns {Deferred}
    */
    _renderBanner: function () {
        if (this.bannerRoute !== undefined) {
            var self = this;
            return this.dp
                .add(this._rpc({route: this.bannerRoute}))
                .then(function (response) {
                    if (!response.html) {
                        self.$el.removeClass('o_has_banner');
                        return $.when();
                    }
                    self.$el.addClass('o_has_banner');
                    var $banner = $(response.html);
                    // we should only display one banner at a time
                    if (self._$banner && self._$banner.remove) {
                        self._$banner.remove();
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
                    return $.when.apply($, defs).then(function () {
                        $banner.prependTo(self.$el);
                        self._$banner = $banner;
                    });
                });
        }
        return $.when();
    },
    /**
     * Renders the control elements (buttons, pager and sidebar) of the current
     * view.
     *
     * @private
     * @returns {Object} an object containing the control panel jQuery elements
     */
    _renderControlPanelElements: function () {
        var elements = {};

        if (this.withControlPanel) {
            elements = {
                $buttons: $('<div>'),
                $sidebar: $('<div>'),
                $pager: $('<div>'),
            };

            this.renderButtons(elements.$buttons);
            this.renderSidebar(elements.$sidebar);
            this.renderPager(elements.$pager);
            // remove the unnecessary outer div
            elements = _.mapObject(elements, function($node) {
                return $node && $node.contents();
            });
            elements.$switch_buttons = this._renderSwitchButtons();
        }

        return elements;
    },
    /**
     * Renders the switch buttons and binds listeners on them.
     *
     * @private
     * @returns {jQuery}
     */
    _renderSwitchButtons: function () {
        var self = this;
        var views = _.filter(this.actionViews, {multiRecord: this.isMultiRecord});

        if (views.length <= 1) {
            return $();
        }

        var template = config.device.isMobile ? 'ControlPanel.SwitchButtons.Mobile' : 'ControlPanel.SwitchButtons';
        var $switchButtons = $(QWeb.render(template, {
            views: views,
        }));
        // create bootstrap tooltips
        _.each(views, function (view) {
            $switchButtons.filter('.o_cp_switch_' + view.type).tooltip();
        });
        // add onclick event listener
        var $switchButtonsFiltered = config.device.isMobile ? $switchButtons.find('button') : $switchButtons.filter('button');
        $switchButtonsFiltered.click(_.debounce(function (event) {
            var viewType = $(event.target).data('view-type');
            self.trigger_up('switch_view', {view_type: viewType});
        }, 200, true));

        if (config.device.isMobile) {
            // set active view's icon as view switcher button's icon
            var activeView = _.findWhere(views, {type: this.viewType});
            $switchButtons.find('.o_switch_view_button_icon').addClass('fa fa-lg ' + activeView.icon);
        }

        return $switchButtons;
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
     * @returns {Deferred}
     */
    _update: function (state) {
        // AAB: update the control panel -> this will be moved elsewhere at some point
        var cpContent = _.extend({}, this.controlPanelElements);
        if (this.searchView) {
            _.extend(cpContent, {
                $searchview: this.searchView.$el,
                $searchview_buttons: this.searchView.$buttons,
            });
        }
        this.update_control_panel({
            active_view_selector: '.o_cp_switch_' + this.viewType,
            cp_content: cpContent,
            hidden: !this.withControlPanel,
            searchview: this.searchView,
            search_view_hidden: !this.searchable || this.searchviewHidden,
            groupable: this.groupable,
            enableTimeRangeMenu: this.enableTimeRangeMenu,
        });

        this._pushState();
        return this._renderBanner();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When an Odoo event arrives requesting a record to be opened, this method
     * gets the res_id, and request a switch view in the appropriate mode
     *
     * Note: this method seems wrong, it relies on the model being a basic model,
     * to get the res_id.  It should receive the res_id in the event data
     * @todo move this to basic controller?
     *
     * @private
     * @param {OdooEvent} event
     * @param {number} event.data.id The local model ID for the record to be
     *   opened
     * @param {string} [event.data.mode='readonly']
     */
    _onOpenRecord: function (event) {
        event.stopPropagation();
        var record = this.model.get(event.data.id, {raw: true});
        this.trigger_up('switch_view', {
            view_type: 'form',
            res_id: record.res_id,
            mode: event.data.mode || 'readonly',
            model: this.modelName,
        });
    },
    /**
     * When a user clicks on an <a> link with type="action", we need to actually
     * do the action. This kind of links is used a lot in no-content helpers.
     *
     * The <a> may have
     * - a data-method and data-model attribute, in that case the corresponding
     *   rpc will be called. If that rpc returns an action it will be executed.
     * - a data-reload-on-close attribute, in that case the view will be
     *   reloaded after the dialog has been closed.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onActionClicked: function (event) {
        var $target = $(event.currentTarget);
        var self = this;
        var model = $target.data('model');
        var method = $target.data('method');

        if (method !== undefined && model !== undefined) {
            var options = {};
            if ($target.data('reload-on-close')) {
                options.on_close = function () {
                    self.trigger_up('reload');
                };
            }
            this.dp.add(this._rpc({
                model: model,
                method: method,
                context: session.user_context,
            })).then(function (action) {
                if (action !== undefined) {
                    self.do_action(action, options);
                }
            });
        } else {
            this.do_action($target.attr('name'));
        }
    },
    /**
     * Intercepts the 'switch_view' event to add the controllerID into the data,
     * and lets the event bubble up.
     *
     * @param {OdooEvent} event
     */
    _onSwitchView: function (event) {
        event.data.controllerID = this.controllerID;
    },

});

return AbstractController;

});
