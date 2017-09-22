odoo.define('web.KanbanRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var core = require('web.core');
var config = require("web.config");
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
    events: {
        'click .o_kanban_mobile_tab': function(event) {
            this._moveToGroup($(event.currentTarget).index());
        }
    },
    custom_events: _.extend({}, BasicRenderer.prototype.custom_events || {}, {
        'set_progress_bar_state': '_onSetProgressBarState',
    }),
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
        if (this.columnOptions.hasProgressBar) {
            this.columnOptions.progressBarStates = {};
        }
        this._setState(state);
        // Used for mobile, when returning back to view
        this.lastActiveMobileTab = -1;
        this.isMobile = config.isMobile;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Displays the quick create record in the first column if not mobile otherwise,
     * Uses active column index.
     */
    addQuickCreate: function () {
        var index = this.lastActiveMobileTab > -1 ? this.lastActiveMobileTab : 0;
        this.widgets[index].addQuickCreate();
    },
    /**
     * Toggle fold/unfold the Column quick create widget
     */
    quickCreateToggleFold: function () {
        this.quickCreate.toggleFold();
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
        var self = this;
        var column = _.findWhere(this.widgets, {db_id: localID});
        var index = _.indexOf(this.widgets, column);
        var newColumn = new KanbanColumn(this, columnState, this.columnOptions, this.recordOptions);
        this.widgets[index] = newColumn; // Replacing old column to new column
        return newColumn.insertAfter(column.$el).then(function (){
            column.destroy();
            if (self.isMobile) {
                newColumn.$el.addClass("current");
                self._enableSwipeOnRecordGroup(newColumn);
            }
        });
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
    /**
     * @override
     */
    updateState: function (state) {
        this._setState(state);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * The nocontent helper should be displayed in kanban:
     *   - ungrouped: if there is no records
     *   - grouped: if there is no groups and no column quick create
     *
     * @override
     * @private
     */
    _hasContent: function () {
        return this._super.apply(this, arguments) ||
               this.createColumnEnabled ||
               (this.state.groupedBy.length && this.state.data.length);
    },
    /* Enable swipe event on kanban column in mobile
     *
     * @private
     * @param {KanbanColumn} column
     */
    _enableSwipeOnRecordGroup: function (column) {
        var self = this;
        column.$el.swipe({
            swipeLeft: function() {
                self._moveToGroup(++self.lastActiveMobileTab);
            },
            swipeRight: function() {
                self._moveToGroup(--self.lastActiveMobileTab);
            }
        });
    },
    /**
     * Moving to kanan column group when swiping kanban column in mobile
     *
     * @private
     * @param {integer} moveToIndex
     */
    _moveToGroup: function (moveToIndex) {
        var self = this;
        if (this.widgets.length - 1 < moveToIndex) {
            this.lastActiveMobileTab = this.widgets.length - 1;
            return;
        } else if (moveToIndex < 0) {
            this.lastActiveMobileTab = 0;
            return;
        }
        this.lastActiveMobileTab = moveToIndex;
        var moveTo = moveToIndex;
        var next = moveToIndex + 1;
        var previous = moveToIndex - 1;
        this.$(".o_kanban_group").removeClass("previous next current before after");
        this.$(".o_kanban_mobile_tab").removeClass("previous next current before after");
        _.each(this.widgets, function(column, index) {
            var recordPane = self.$(".o_kanban_group[data-id=" + column.id + "]");
            var tab = self.$(".o_kanban_mobile_tab[data-id=" + column.id + "]");
            if (index == previous) {
                tab.addClass("previous");
                tab.css("margin-left", "-" + (tab.outerWidth() / 2) + "px");
                recordPane.addClass("previous");
            } else if (index == next) {
                tab.addClass("next");
                tab.css("margin-left", "-" + (tab.outerWidth() / 2) + "px");
                recordPane.addClass("next");
            } else if (index < moveTo) {
                tab.addClass("before");
                tab.css("margin-left", "-" + tab.outerWidth() + "px");
                recordPane.addClass("before");
            } else if (index == moveTo) {
                var marginLeft = tab.outerWidth() / 2;
                tab.css("margin-left", "-" + marginLeft + "px");
                tab.addClass("current");
                recordPane.addClass("current");
                if (column.isEmpty())
                    column.trigger_up('kanban_load_records');
            } else if (index > moveTo) {
                tab.addClass("after");
                tab.css("margin-left", "0");
                recordPane.addClass("after");
            }
        });
    },
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

        // Render columns
        if (this.isMobile) {
            this.$el.append($(qweb.render("KanbanView.MobileTabs", {'data': this.state.data})));
            this.$(".o_kanban_mobile_tab").on('click', function (event) {
                self._moveToGroup($(event.currentTarget).index());
            });
        }
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

        if (this.groupedByM2O) {
            // Enable column sorting
            this.$el.sortable({
                axis: 'x',
                items: '> .o_kanban_group',
                handle: '.o_kanban_header_title',
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
            if (this.createColumnEnabled) {
                this.quickCreate = new ColumnQuickCreate(this);
                this.quickCreate.appendTo(fragment);
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
        var oldWidgets = this.widgets;
        this.widgets = [];
        this.$el.empty();

        var displayNoContentHelper = !this._hasContent() && !!this.noContentHelp;
        this.$el.toggleClass('o_kanban_nocontent', displayNoContentHelper);
        if (displayNoContentHelper) {
            // display the no content helper if there is no data to display
            this._renderNoContentHelper();
        } else {
            var isGrouped = !!this.state.groupedBy.length;
            this.$el.toggleClass('o_kanban_grouped', isGrouped);
            this.$el.toggleClass('o_kanban_ungrouped', !isGrouped);
            var fragment = document.createDocumentFragment();
            // render the kanban view
            if (isGrouped) {
                this._renderGrouped(fragment);
            } else {
                this._renderUngrouped(fragment);
            }
            this.$el.append(fragment);
            if (this.widgets && config.isMobile && isGrouped) {
                core.bus.on("DOM_updated", this, function() {
                    this._enableSwipeOnRecordGroups();
                    this._moveToGroup(this.lastActiveMobileTab);
                });
                // Required to allow mobile kanban stage tabs to enable swipe and move to active tab
                core.bus.trigger('DOM_updated');
            }
        }

        return this._super.apply(this, arguments).then(_.invoke.bind(_, oldWidgets, 'destroy'));
    },
    /**
     * Sets the current state and updates some internal attributes accordingly.
     *
     * @private
     * @param {Object} state
     */
    _setState: function (state) {
        this.state = state;

        var groupByFieldAttrs = state.fields[state.groupedBy[0]];
        var groupByFieldInfo = state.fieldsInfo.kanban[state.groupedBy[0]];
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
        this.groupedByM2O = groupByFieldAttrs && (groupByFieldAttrs.type === 'many2one');
        var grouped_by_field = this.groupedByM2O && groupByFieldAttrs.relation;
        var groupByTooltip = groupByFieldInfo && groupByFieldInfo.options.group_by_tooltip;
        this.columnOptions = _.extend(this.columnOptions, {
            draggable: draggable,
            group_by_tooltip: groupByTooltip,
            grouped_by_m2o: this.groupedByM2O,
            relation: grouped_by_field,
        });
        this.createColumnEnabled = this.groupedByM2O && this.columnOptions.group_creatable;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Updates progressbar internal states (necessary for animations) with
     * received data.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSetProgressBarState: function (ev) {
        if (!this.columnOptions.progressBarStates[ev.data.columnID]) {
            this.columnOptions.progressBarStates[ev.data.columnID] = {};
        }
        _.extend(this.columnOptions.progressBarStates[ev.data.columnID], ev.data.values);
    },
});

return KanbanRenderer;

});
