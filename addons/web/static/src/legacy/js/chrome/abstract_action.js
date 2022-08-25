/** @odoo-module alias=web.AbstractAction **/

/**
 * We define here the AbstractAction widget, which implements the ActionMixin.
 * All client actions must extend this widget.
 *
 * @module @web/chrome/abstract_action
 */

import ActionMixin from "web.ActionMixin";
import ActionModel from "web.ActionModel";
import ControlPanel from "web.ControlPanel";
import Widget from "web.Widget";
import { ComponentWrapper } from "web.OwlCompatibility";

const { Component } = owl;
const AbstractAction = Widget.extend(ActionMixin, {
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
     *      this.searchModelConfig.modelName = 'mail.message';
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

        this.searchModelConfig = {
            context: Object.assign({}, action.context),
            domain: action.domain || [],
            env: Component.env,
            searchMenuTypes: this.searchMenuTypes,
        };
        this.extensions = {};
        if (this.hasControlPanel) {
            this.extensions.ControlPanel = {
                actionId: action.id,
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
        const superPromise = this._super(...arguments);
        if (this.hasControlPanel) {
            if (this.loadControlPanel) {
                const { context, modelName } = this.searchModelConfig;
                const options = { load_filters: this.searchMenuTypes.includes('favorite') };
                const { arch, fields, favoriteFilters } = await this.loadFieldView(
                    modelName,
                    context || {},
                    this.viewId,
                    'search',
                    options
                );
                const archs = { search: arch };
                const { ControlPanel: controlPanelInfo } = ActionModel.extractArchInfo(archs);
                Object.assign(this.extensions.ControlPanel, {
                    archNodes: controlPanelInfo.children,
                    favoriteFilters,
                    fields,
                });
                this.controlPanelProps.fields = fields;
            }
        }
        this.searchModel = new ActionModel(this.extensions, this.searchModelConfig);
        if (this.hasControlPanel) {
            this.controlPanelProps.searchModel = this.searchModel;
        }
        return Promise.all([
            superPromise,
            this.searchModel.load(),
        ]);
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
            this._controlPanelWrapper = new ComponentWrapper(this, this.config.ControlPanel, this.controlPanelProps);
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
        this.searchModel.on('search', this, this._onSearch);
        if (this.hasControlPanel) {
            this.searchModel.on('get-controller-query-params', this, this._onGetOwnedQueryParams);
        }
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        ActionMixin.on_detach_callback.call(this);
        this.searchModel.off('search', this);
        if (this.hasControlPanel) {
            this.searchModel.off('get-controller-query-params', this);
        }
    },

    /**
     * @private
     * @param {Object} [searchQuery]
     */
    _onSearch: function () {},
});

export default AbstractAction;
