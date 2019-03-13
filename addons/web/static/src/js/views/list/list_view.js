odoo.define('web.ListView', function (require) {
"use strict";

/**
 * The list view is one of the core and most basic view: it is used to look at
 * a list of records in a table.
 *
 * Note that a list view is not instantiated to display a one2many field in a
 * form view. Only a ListRenderer is used in that case.
 */

var BasicView = require('web.BasicView');
var core = require('web.core');
var ListRenderer = require('web.ListRenderer');
var ListController = require('web.ListController');

var _lt = core._lt;

var ListView = BasicView.extend({
    accesskey: "l",
    display_name: _lt('List'),
    icon: 'fa-list-ul',
    config: _.extend({}, BasicView.prototype.config, {
        Renderer: ListRenderer,
        Controller: ListController,
    }),
    viewType: 'list',
    /**
     * @override
     *
     * @param {Object} viewInfo
     * @param {Object} params
     * @param {boolean} params.hasSidebar
     * @param {boolean} [params.hasSelectors=true]
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        var selectedRecords = []; // there is no selected records by default

        var mode = this.arch.attrs.editable && !params.readonly ? "edit" : "readonly";

        this.controllerParams.editable = this.arch.attrs.editable;
        this.controllerParams.hasSidebar = params.hasSidebar;
        this.controllerParams.toolbarActions = viewInfo.toolbar;
        this.controllerParams.mode = mode;
        this.controllerParams.selectedRecords = selectedRecords;

        this.rendererParams.arch = this.arch;
        this.rendererParams.hasSelectors =
                'hasSelectors' in params ? params.hasSelectors : true;
        this.rendererParams.editable = params.readonly ? false : this.arch.attrs.editable;
        this.rendererParams.selectedRecords = selectedRecords;
        this.rendererParams.addCreateLine = false;
        this.rendererParams.addCreateLineInGroups = this.rendererParams.editable && this.controllerParams.activeActions.create;

        this.loadParams.limit = this.loadParams.limit || 80;
        this.loadParams.openGroupByDefault = !!JSON.parse(this.arch.attrs.expand || "0");
        this.loadParams.type = 'list';
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _extractParamsFromAction: function (action) {
        var params = this._super.apply(this, arguments);
        var inDialog = action.target === 'new';
        var inline = action.target === 'inline';
        params.hasSidebar = !inDialog && !inline;
        return params;
    },
    /**
     * @override
     */
    _updateMVCParams: function () {
        this._super.apply(this, arguments);
        this.controllerParams.noLeaf = !!this.loadParams.context.group_by_no_leaf;
    },
});

return ListView;

});
