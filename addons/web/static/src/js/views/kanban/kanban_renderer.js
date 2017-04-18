odoo.define('web.KanbanRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var core = require('web.core');
var KanbanColumn = require('web.KanbanColumn');
var KanbanRecord = require('web.KanbanRecord');
var quick_create = require('web.kanban_quick_create');
var QWeb = require('web.QWeb');
var session = require('web.session');
var utils = require('web.utils');

var ColumnQuickCreate = quick_create.ColumnQuickCreate;

var qweb = core.qweb;

function findInNode(node, predicate) {
    if (predicate(node)) {
        return node;
    }
    if (!node.children) {
        return undefined;
    }
    for (var i = 0; i < node.children.length; i++) {
        if (findInNode(node.children[i], predicate)) {
            return node.children[i];
        }
    }
}

function qwebAddIf(node, condition) {
    if (node.attrs[qweb.prefix + '-if']) {
        condition = _.str.sprintf("(%s) and (%s)", node.attrs[qweb.prefix + '-if'], condition);
    }
    node.attrs[qweb.prefix + '-if'] = condition;
}

function transformQwebTemplate(node, fields) {
    // Process modifiers
    if (node.tag && node.attrs.modifiers) {
        var modifiers = JSON.parse(node.attrs.modifiers || "{}");
        if (modifiers.invisible) {
            qwebAddIf(node, _.str.sprintf("!kanban_compute_domain(%s)", JSON.stringify(modifiers.invisible)));
        }
    }
    switch (node.tag) {
        case 'button':
        case 'a':
            var type = node.attrs.type || '';
            if (_.indexOf('action,object,edit,open,delete,url,set_cover'.split(','), type) !== -1) {
                _.each(node.attrs, function (v, k) {
                    if (_.indexOf('icon,type,name,args,string,context,states,kanban_states'.split(','), k) !== -1) {
                        node.attrs['data-' + k] = v;
                        delete(node.attrs[k]);
                    }
                });
                if (node.attrs['data-string']) {
                    node.attrs.title = node.attrs['data-string'];
                }
                if (node.tag === 'a' && node.attrs['data-type'] !== "url") {
                    node.attrs.href = '#';
                } else {
                    node.attrs.type = 'button';
                }

                var action_classes = " oe_kanban_action oe_kanban_action_" + node.tag;
                if (node.attrs['t-attf-class']) {
                    node.attrs['t-attf-class'] += action_classes;
                } else if (node.attrs['t-att-class']) {
                    node.attrs['t-att-class'] += " + '" + action_classes + "'";
                } else {
                    node.attrs['class'] = (node.attrs['class'] || '') + action_classes;
                }
            }
            break;
    }
    if (node.children) {
        for (var i = 0, ii = node.children.length; i < ii; i++) {
            transformQwebTemplate(node.children[i], fields);
        }
    }
}

var KanbanRenderer = BasicRenderer.extend({
    className: 'o_kanban_view',
    /**
     * @override
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);

        this.widgets = [];
        this.qweb = new QWeb(session.debug, {_s: session.origin});
        var templates = findInNode(this.arch, function (n) { return n.tag === 'templates';});
        transformQwebTemplate(templates, state.fields);
        this.qweb.add_template(utils.json_node_to_xml(templates));

        this.recordOptions = _.extend({}, params.record_options, {
            qweb: this.qweb,
            viewType: 'kanban',
        });
        this.columnOptions = _.extend({}, params.column_options, { qweb: this.qweb });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Displays the quick create record in the first column.
     */
    addQuickCreate: function () {
        this.widgets[0].addQuickCreate();
    },
    /**
     * @returns {Deferred}
     */
    canBeSaved: function () {
        return $.when();
    },
    /**
     * Removes a widget (record if ungrouped, column if grouped) from the view.
     *
     * @param {Widget} widget the instance of the widget to remove
     */
    removeWidget: function (widget) {
        this.widgets.splice(this.widgets.indexOf(widget), 1);
        widget.destroy();
    },
    /**
     * Updates a given column with its new state.
     *
     * @param {string} localID the column id
     * @param {Object} columnState
     *
     * @returns {Deferred}
     */
    updateColumn: function (localID, columnState) {
        var column = _.findWhere(this.widgets, {db_id: localID});
        this.widgets.splice(_.indexOf(this.widgets, column), 1); // remove column from widgets' list
        var newColumn = new KanbanColumn(this, columnState, this.columnOptions, this.recordOptions);
        this.widgets.push(newColumn);
        return newColumn.insertAfter(column.$el).then(column.destroy.bind(column));
    },
    /**
     * Updates a given record with its new state.
     *
     * @param {Object} recordState
     */
    updateRecord: function (recordState) {
        var isGrouped = !!this.state.groupedBy.length;
        var record;

        if (isGrouped) {
            // if grouped, this.widgets are kanban columns so we need to find
            // the kanban record inside
            _.each(this.widgets, function (widget) {
                record = record || _.findWhere(widget.records, {
                    db_id: recordState.id,
                });
            });
        } else {
            record = _.findWhere(this.widgets, {db_id: recordState.id});
        }

        if (record) {
            record.update(recordState);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Renders empty invisible divs in a document fragment.
     *
     * @private
     * @param {DocumentFragment} fragment
     * @param {integer} nbDivs the number of divs to append
     */
    _renderGhostDivs: function (fragment, nbDivs) {
        for (var $ghost, i = 0; i < nbDivs; i++) {
            $ghost = $('<div>').addClass('o_kanban_record o_kanban_ghost');
            $ghost.appendTo(fragment);
        }
    },
    /**
     * Renders an grouped kanban view in a fragment.
     *
     * @private
     * @param {DocumentFragment} fragment
     */
    _renderGrouped: function (fragment) {
        var self = this;
        var groupByFieldAttrs = this.state.fields[this.state.groupedBy[0]];
        // Deactivate the drag'n'drop if the groupedBy field:
        // - is a date or datetime since we group by month or
        // - is readonly
        var draggable = true;
        if (groupByFieldAttrs) {
            if (groupByFieldAttrs.type === "date" || groupByFieldAttrs.type === "datetime") {
                draggable = false;
            } else if (groupByFieldAttrs.readonly !== undefined) {
                draggable = !(groupByFieldAttrs.readonly);
            }
        }
        var groupedByM2O = groupByFieldAttrs && (groupByFieldAttrs.type === 'many2one');
        var grouped_by_field = groupedByM2O && groupByFieldAttrs.relation;
        this.columnOptions = _.extend(this.columnOptions, {
            draggable: draggable,
            grouped_by_m2o: groupedByM2O,
            relation: grouped_by_field,
        });

        // Render columns
        _.each(this.state.data, function (group) {
            var column = new KanbanColumn(self, group, self.columnOptions, self.recordOptions);
            if (!group.value) {
                column.prependTo(fragment); // display the 'Undefined' group first
                self.widgets.unshift(column);
            } else {
                column.appendTo(fragment);
                self.widgets.push(column);
            }
        });

        if (groupedByM2O) {
            // Enable column sorting
            this.$el.sortable({
                axis: 'x',
                items: '> .o_kanban_group',
                handle: '.o_kanban_header',
                cursor: 'move',
                revert: 150,
                delay: 100,
                tolerance: 'pointer',
                forcePlaceholderSize: true,
                stop: function () {
                    var ids = [];
                    self.$('.o_kanban_group').each(function (index, u) {
                        ids.push($(u).data('id'));
                    });
                    self.trigger_up('resequence_columns', {ids: ids});
                },
            });

            // Enable column quickcreate
            if (this.columnOptions.group_creatable) {
                var quickCreate = new ColumnQuickCreate(this);
                quickCreate.appendTo(fragment);
            }
        }

    },
    /**
     * Renders an ungrouped kanban view in a fragment.
     *
     * @private
     * @param {DocumentFragment} fragment
     */
    _renderUngrouped: function (fragment) {
        var self = this;
        _.each(this.state.data, function (record) {
            var kanbanRecord = new KanbanRecord(self, record, self.recordOptions);
            self.widgets.push(kanbanRecord);
            kanbanRecord.appendTo(fragment);
        });

        // append ghost divs to ensure that all kanban records are left aligned
        this._renderGhostDivs(fragment, 6);
    },
    /**
     * @override
     * @private
     */
    _renderView: function () {
        var isGrouped = !!this.state.groupedBy.length;
        this.$el.toggleClass('o_kanban_grouped', isGrouped);
        this.$el.toggleClass('o_kanban_ungrouped', !isGrouped);
        this.$el.empty();

        var fragment = document.createDocumentFragment();
        if (isGrouped) {
            this._renderGrouped(fragment);
        } else {
            this._renderUngrouped(fragment);
        }
        this.$el.append(fragment);
        return this._super.apply(this, arguments);
    },
});

return KanbanRenderer;

});
