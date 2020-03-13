odoo.define('web.AbstractAction', function (require) {
"use strict";

/**
 * We define here the AbstractAction widget, which implements the ActionMixin.
 * All client actions must extend this widget.
 *
 * @module web.AbstractAction
 */

var ActionMixin = require('web.ActionMixin');
var ControlPanel = require('web.ControlPanel');
var ControlPanelModel = require('web.ControlPanelModel');
var Widget = require('web.Widget');
const { ComponentWrapper } = require('web.OwlCompatibility');

var AbstractAction = Widget.extend(ActionMixin, {
    config: {
        ControlPanel: ControlPanel,
    },

    /**
     * If this flag is set to true, the client action will create a control
     * panel whenever it is created.
     *
     * @type boolean
     */
    hasControlPanel: false,

    /**
     * If true, this flag indicates that the client action should automatically
     * fetch the <arch> of a search view (or control panel view).  Note that
     * to do that, it also needs a specific modelName.
     *
     * For example, the Discuss application adds the following line in its
     * constructor::
     *
     *      this.controlPanelModelConfig.modelName = 'mail.message';
     *
     * @type boolean
     */
    loadControlPanel: false,

    /**
     * A client action might want to use a search bar in its control panel, or
     * it could choose not to use it.
     *
     * Note that it only makes sense if hasControlPanel is set to true.
     *
     * @type boolean
     */
    withSearchBar: false,

    /**
     * This parameter can be set to customize the available sub menus in the
     * controlpanel (Filters/Group By/Favorites).  This is basically a list of
     * the sub menus that we want to use.
     *
     * Note that it only makes sense if hasControlPanel is set to true.
     *
     * For example, set ['filter', 'favorite'] to enable the Filters and
     * Favorites menus.
     *
     * @type string[]
     */
    searchMenuTypes: [],

    /**
     * @override
     *
     * @param {Widget} parent
     * @param {Object} action
     * @param {Object} [options]
     */
    init: function (parent, action, options) {
        this._super(parent);
        this._title = action.display_name || action.name;

        if (this.hasControlPanel) {
            this.controlPanelModelConfig = {
                actionId: action.id,
                actionContext: action.context || {},
                actionDomain: action.domain || [],
                env: owl.Component.env,
                withSearchBar: this.withSearchBar,
            };

            this.viewId = action.search_view_id && action.search_view_id[0];

            this.controlPanelProps = {
                action,
                breadcrumbs: options && options.breadcrumbs,
                withSearchBar: this.withSearchBar,
                searchMenuTypes: this.searchMenuTypes,
            };
        }
    },
    /**
     * The willStart method is actually quite complicated if the client action
     * has a controlPanel, because it needs to prepare it.
     *
     * @override
     */
    willStart: async function () {
        const proms = [this._super(...arguments)];
        if (this.hasControlPanel) {
            if (this.loadControlPanel) {
                const { context, searchMenuTypes } = this.controlPanelProps;
                const { modelName } = this.controlPanelModelConfig;
                const options = { load_filters: searchMenuTypes.includes('favorite') };
                const args = [modelName, context || {}, this.viewId, 'search', options];
                const loadFieldViewPromise = this.loadFieldView(...args);
                const {arch, fields, favoriteFilters } = await loadFieldViewPromise;
                this.controlPanelModelConfig.viewInfo = {arch, fields, favoriteFilters };
                this.controlPanelProps.fields = fields;
            }
            this._controlPanelModel = new ControlPanelModel(this.controlPanelModelConfig);
            this.controlPanelProps.controlPanelModel = this._controlPanelModel;
            proms.push(this._controlPanelModel.isReady);
        }
        return Promise.all(proms);
    },
    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        if (this.hasControlPanel) {
            if ('title' in this.controlPanelProps) {
                this._setTitle(this.controlPanelProps.title);
            }
            this.controlPanelProps.title = this.getTitle();
            this._controlPanelWrapper = new ComponentWrapper(this, ControlPanel, this.controlPanelProps);
            await this._controlPanelWrapper.mount(this.el, { position: 'first-child' });

        }
    },
    /**
     * @override
     */
    destroy: function() {
        this._super.apply(this, arguments);
        ActionMixin.destroy.call(this);
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        ActionMixin.on_attach_callback.call(this);
        if (this.hasControlPanel) {
            this._controlPanelModel.on('search', this, this._onSearch);
            this._controlPanelModel.on('get-controller-query-params', this, this._onGetOwnedQueryParams);
        }
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        ActionMixin.on_detach_callback.call(this);
        if (this.hasControlPanel) {
            this._controlPanelModel.off('search', this);
            this._controlPanelModel.off('get-controller-query-params', this);
        }
    },

    /**
     * @private
     * @param {Object} [searchQuery]
     */
    _onSearch: function () {},
});

return AbstractAction;

});
