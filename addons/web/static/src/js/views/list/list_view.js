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
var ListModel = require('web.ListModel');
var ListRenderer = require('web.ListRenderer');
var ListController = require('web.ListController');

var _lt = core._lt;

var ListView = BasicView.extend({
    accesskey: "l",
    display_name: _lt('List'),
    icon: 'fa-list-ul',
    config: _.extend({}, BasicView.prototype.config, {
        Model: ListModel,
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
        var self = this;
        this._super.apply(this, arguments);
        var selectedRecords = []; // there is no selected records by default

        var mode = this.arch.attrs.editable && !params.readonly ? "edit" : "readonly";
        var expandGroups = !!JSON.parse(this.arch.attrs.expand || "0");

        this.groupbys = {};
        this.arch.children.forEach(function (child) {
            if (child.tag === 'groupby') {
                self._extractGroup(child);
            }
        });

        this.controllerParams.editable = this.arch.attrs.editable;
        this.controllerParams.hasSidebar = params.hasSidebar;
        this.controllerParams.toolbarActions = viewInfo.toolbar;
        this.controllerParams.mode = mode;
        this.controllerParams.selectedRecords = selectedRecords;

        this.rendererParams.arch = this.arch;
        this.rendererParams.groupbys = this.groupbys;
        this.rendererParams.hasSelectors =
                'hasSelectors' in params ? params.hasSelectors : true;
        this.rendererParams.editable = params.readonly ? false : this.arch.attrs.editable;
        this.rendererParams.selectedRecords = selectedRecords;
        this.rendererParams.addCreateLine = false;
        this.rendererParams.addCreateLineInGroups = this.rendererParams.editable && this.controllerParams.activeActions.create;

        this.modelParams.groupbys = this.groupbys;

        this.loadParams.limit = this.loadParams.limit || 80;
        this.loadParams.openGroupByDefault = expandGroups;
        this.loadParams.type = 'list';
        var groupsLimit = parseInt(this.arch.attrs.groups_limit, 10);
        this.loadParams.groupsLimit = groupsLimit || (expandGroups ? 10 : 80);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} node
     */
    _extractGroup: function (node) {
        var innerView = this.fields[node.attrs.name].views.groupby;
        this.groupbys[node.attrs.name] = this._processFieldsView(innerView, 'groupby');
    },
    /**
     * @override
     */
    _extractParamsFromAction: function (action) {
        var params = this._super.apply(this, arguments);
        var inDialog = action.target === 'new';
        var inline = action.target === 'inline';
        params.hasSidebar = !inDialog && !inline;
        params.withBreadcrumbs = !inDialog;
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
