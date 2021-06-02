odoo.define('web.AbstractAction', function (require) {
"use strict";

/**
 * We define here the AbstractAction widget, which implements the ActionMixin.
 * All client actions must extend this widget.
 *
 * @module web.AbstractAction
 */

var ActionMixin = require('web.ActionMixin');
var ControlPanelView = require('web.ControlPanelView');
var Widget = require('web.Widget');

var AbstractAction = Widget.extend(ActionMixin, {
    config: {
        ControlPanelView: ControlPanelView,
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
     *      this.controlPanelParams.modelName = 'mail.message';
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
        this.controlPanelParams = {
            actionId: action.id,
            context: action.context,
            breadcrumbs: options && options.breadcrumbs || [],
            title: this.getTitle(),
            viewId: action.search_view_id && action.search_view_id[0],
            withSearchBar: this.withSearchBar,
            searchMenuTypes: this.searchMenuTypes,
        };
    },
    /**
     * The willStart method is actually quite complicated if the client action
     * has a controlPanel, because it needs to prepare it.
     *
     * @override
     */
    willStart: function () {
        var self = this;
        var proms = [this._super.apply(this, arguments)];
        if (this.hasControlPanel) {
            var params = this.controlPanelParams;
            if (this.loadControlPanel) {
                proms.push(this
                    .loadFieldView(params.modelName, params.context || {}, params.viewId, 'search')
                    .then(function (fieldsView) {
                        params.viewInfo = {
                            arch: fieldsView.arch,
                            fields: fieldsView.fields,
                        };
                    }));
            }
            return Promise.all(proms).then(function () {
                var controlPanelView = new self.config.ControlPanelView(params);
                return controlPanelView.getController(self).then(function (controlPanel) {
                    self._controlPanel = controlPanel;
                    return self._controlPanel.appendTo(document.createDocumentFragment());
                });
            });
        }
        return Promise.all(proms);
    },
    /**
     * @override
     */
    start: function () {
        if (this._controlPanel) {
            this._controlPanel.$el.prependTo(this.$el);
        }
        return this._super.apply(this, arguments);
    },
});

return AbstractAction;

});
