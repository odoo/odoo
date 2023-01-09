/** @odoo-module alias=web.ListView **/

/**
 * The list view is one of the core and most basic view: it is used to look at
 * a list of records in a table.
 *
 * Note that a list view is not instantiated to display a one2many field in a
 * form view. Only a ListRenderer is used in that case.
 */

import BasicView from 'web.BasicView';
import core from 'web.core';
import ListModel from 'web.ListModel';
import ListRenderer from 'web.ListRenderer';
import ListController from 'web.ListController';
import pyUtils from 'web.py_utils';

var _lt = core._lt;

var ListView = BasicView.extend({
    accesskey: "l",
    display_name: _lt('List'),
    icon: 'oi oi-view-list',
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
     * @param {boolean} params.hasActionMenus
     * @param {boolean} [params.hasSelectors=true]
     */
    init: function (viewInfo, params) {
        var self = this;
        this._super.apply(this, arguments);
        var selectedRecords = []; // there is no selected records by default

        var pyevalContext = py.dict.fromJSON(_.pick(params.context, function(value, key, object) {return !_.isUndefined(value)}) || {});
        var expandGroups = !!JSON.parse(pyUtils.py_eval(this.arch.attrs.expand || "0", {'context': pyevalContext}));

        this.groupbys = {};
        this.headerButtons = [];
        this.arch.children.forEach(function (child) {
            if (child.tag === 'groupby') {
                self._extractGroup(child);
            }
            if (child.tag === 'header') {
                self._extractHeaderButtons(child);
            }
        });

        let editable = false;
        if ((!this.arch.attrs.edit || !!JSON.parse(this.arch.attrs.edit)) && !params.readonly) {
            editable = this.arch.attrs.editable;
        }

        this.controllerParams.activeActions.export_xlsx = this.arch.attrs.export_xlsx ? !!JSON.parse(this.arch.attrs.export_xlsx): true;
        this.controllerParams.editable = editable;
        this.controllerParams.hasActionMenus = params.hasActionMenus;
        this.controllerParams.headerButtons = this.headerButtons;
        this.controllerParams.toolbarActions = viewInfo.toolbar;
        this.controllerParams.mode = 'readonly';
        this.controllerParams.selectedRecords = selectedRecords;

        this.rendererParams.arch = this.arch;
        this.rendererParams.groupbys = this.groupbys;
        this.rendererParams.hasSelectors =
                'hasSelectors' in params ? params.hasSelectors : true;
        this.rendererParams.editable = editable;
        this.rendererParams.selectedRecords = selectedRecords;
        this.rendererParams.addCreateLine = false;
        this.rendererParams.addCreateLineInGroups = editable && this.controllerParams.activeActions.create;
        this.rendererParams.isMultiEditable = this.arch.attrs.multi_edit && !!JSON.parse(this.arch.attrs.multi_edit);

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
     * Extracts action buttons definitions from the <header> node of the list
     * view definition
     *
     * @private
     * @param {Object} node
     */
    _extractHeaderButtons(node) {
        node.children.forEach(child => {
            if (child.tag === 'button' && !child.attrs.modifiers.invisible) {
                this.headerButtons.push(child);
            }
        });
    },
    /**
     * @override
     */
    _extractParamsFromAction: function (action) {
        var params = this._super.apply(this, arguments);
        var inDialog = action.target === 'new';
        var inline = action.target === 'inline';
        params.hasActionMenus = !inDialog && !inline;
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

export default ListView;
