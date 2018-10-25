odoo.define('web.KanbanView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var config = require('web.config');
var core = require('web.core');
var KanbanController = require('web.KanbanController');
var kanbanExamplesRegistry = require('web.kanban_examples_registry');
var KanbanModel = require('web.KanbanModel');
var KanbanRenderer = require('web.KanbanRenderer');
var pyUtils = require('web.py_utils');
var SearchPanel = require('web.SearchPanel');
var utils = require('web.utils');

var _lt = core._lt;

var KanbanView = BasicView.extend({
    accesskey: "k",
    display_name: _lt("Kanban"),
    icon: 'fa-th-large',
    mobile_friendly: true,
    config: {
        Model: KanbanModel,
        Controller: KanbanController,
        Renderer: KanbanRenderer,
        SearchPanel: SearchPanel,
    },
    jsLibs: [],
    viewType: 'kanban',

    /**
     * @constructor
     */
    init: function (viewInfo, params) {
        this.searchPanelSections = Object.create(null);

        this._super.apply(this, arguments);

        this.loadParams.limit = this.loadParams.limit || 40;
        // in mobile, columns are lazy-loaded, so set 'openGroupByDefault' to
        // false so that they will won't be loaded by the initial load
        this.loadParams.openGroupByDefault = config.device.isMobile ? false : true;
        this.loadParams.type = 'list';
        var progressBar;
        utils.traverse(this.arch, function (n) {
            var isProgressBar = (n.tag === 'progressbar');
            if (isProgressBar) {
                progressBar = _.clone(n.attrs);
                progressBar.colors = JSON.parse(progressBar.colors);
                progressBar.sum_field = progressBar.sum_field || false;
            }
            return !isProgressBar;
        });
        if (progressBar) {
            this.loadParams.progressBar = progressBar;
        }

        var activeActions = this.controllerParams.activeActions;
        var archAttrs = this.arch.attrs;
        activeActions = _.extend(activeActions, {
            group_create: this.arch.attrs.group_create ? !!JSON.parse(archAttrs.group_create) : true,
            group_edit: archAttrs.group_edit ? !!JSON.parse(archAttrs.group_edit) : true,
            group_delete: archAttrs.group_delete ? !!JSON.parse(archAttrs.group_delete) : true,
        });

        this.rendererParams.column_options = {
            editable: activeActions.group_edit,
            deletable: activeActions.group_delete,
            archivable: archAttrs.archivable ? !!JSON.parse(archAttrs.archivable) : true,
            group_creatable: activeActions.group_create && !config.device.isMobile,
            quickCreateView: archAttrs.quick_create_view || null,
            hasProgressBar: !!progressBar,
        };
        this.rendererParams.record_options = {
            editable: activeActions.edit,
            deletable: activeActions.delete,
            read_only_mode: params.readOnlyMode,
        };
        this.rendererParams.quickCreateEnabled = this._isQuickCreateEnabled();
        this.rendererParams.readOnlyMode = params.readOnlyMode;
        var examples = archAttrs.examples;
        if (examples) {
            this.rendererParams.examples = kanbanExamplesRegistry.get(examples);
        }

        this.controllerParams.on_create = archAttrs.on_create;
        this.controllerParams.hasButtons = true;
        this.controllerParams.quickCreateEnabled = this.rendererParams.quickCreateEnabled;


        if (config.device.isMobile) {
            this.jsLibs.push('/web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js');
        }

        this.hasSearchPanel = !_.isEmpty(this.searchPanelSections);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Override to set the controller as parent of the optional searchPanel
     *
     * @override
     */
    getController: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function (controller) {
            if (self.hasSearchPanel) {
                self.controllerParams.searchPanel.setParent(controller);
            }
            return controller;
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Override to create the searchPanel (if necessary) with the domain coming
     * from the controlPanel
     *
     * @override
     * @private
     */
    _createControlPanel: function (parent) {
        if (!this.hasSearchPanel) {
            return this._super.apply(this, arguments);
        }
        var self = this;
        return this._super.apply(this, arguments).then(function (controlPanel) {
            return self._createSearchPanel(parent).then(function () {
                return controlPanel;
            });
        });
    },
    /**
     * @private
     * @param {Widget} parent
     * @returns {Promise} resolved when the searchPanel is ready
     */
    _createSearchPanel: function (parent) {
        var self = this;
        var defaultValues = {};
        Object.keys(this.loadParams.context).forEach(function (key) {
            var match = /^searchpanel_default_(.*)$/.exec(key);
            if (match) {
                defaultValues[match[1]] = self.loadParams.context[key];
            }
        });
        var controlPanelDomain = this.loadParams.domain;
        var searchPanel = new this.config.SearchPanel(parent, {
            defaultValues: defaultValues,
            fields: this.fields,
            model: this.loadParams.modelName,
            searchDomain: controlPanelDomain,
            sections: this.searchPanelSections,
        });
        this.controllerParams.searchPanel = searchPanel;
        this.controllerParams.controlPanelDomain = controlPanelDomain;
        return searchPanel.appendTo(document.createDocumentFragment()).then(function () {
            var searchPanelDomain = searchPanel.getDomain();
            self.loadParams.domain = controlPanelDomain.concat(searchPanelDomain);
        });
    },
    /**
     * @private
     * @param {Object} viewInfo
     * @returns {boolean} true iff the quick create feature is not explicitely
     *   disabled (with create="False" or quick_create="False" in the arch)
     */
    _isQuickCreateEnabled: function () {
        if (!this.controllerParams.activeActions.create) {
            return false;
        }
        if (this.arch.attrs.quick_create !== undefined) {
            return !!JSON.parse(this.arch.attrs.quick_create);
        }
        return true;
    },
    /**
     * Override to handle nodes with tagname 'searchpanel'.
     *
     * @override
     * @private
     */
    _processNode: function (node, fv) {
        if (node.tag === 'searchpanel') {
            if (!config.device.isMobile) {
                this._processSearchPanelNode(node, fv);
            }
            return false;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Populate this.searchPanelSections with category/filter descriptions.
     *
     * @private
     * @param {Object} node
     * @param {Object} fv
     */
    _processSearchPanelNode: function (node, fv) {
        var self = this;
        node.children.forEach(function (childNode, index) {
            if (childNode.tag !== 'field') {
                return;
            }
            if (childNode.attrs.invisible === "1") {
                return;
            }
            var fieldName = childNode.attrs.name;
            var type = childNode.attrs.select === 'multi' ? 'filter' : 'category';

            var sectionId = _.uniqueId('section_');
            var section = {
                color: childNode.attrs.color,
                description: childNode.attrs.string || fv.fields[fieldName].string,
                fieldName: fieldName,
                icon: childNode.attrs.icon,
                id: sectionId,
                index: index,
                type: type,
            };
            if (section.type === 'category') {
                section.icon = section.icon || 'fa-folder';
            } else if (section.type === 'filter') {
                section.disableCounters = !!pyUtils.py_eval(childNode.attrs.disable_counters || '0');
                section.domain = childNode.attrs.domain || '[]';
                section.groupBy = childNode.attrs.groupby;
                section.icon = section.icon || 'fa-filter';
            }
            self.searchPanelSections[sectionId] = section;
        });
    },
    /**
     * @override
     * @private
     */
    _updateMVCParams: function () {
        this._super.apply(this, arguments);
        var defaultGroupBy = this.arch.attrs.default_group_by;
        this.loadParams.groupBy = defaultGroupBy ?
                                    [defaultGroupBy] :
                                    (this.loadParams.groupedBy || []);
    },
});

return KanbanView;

});
