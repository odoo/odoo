odoo.define('web.KanbanRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var ColumnQuickCreate = require('web.kanban_column_quick_create');
var config = require('web.config');
var core = require('web.core');
var KanbanColumn = require('web.KanbanColumn');
var KanbanRecord = require('web.KanbanRecord');
var QWeb = require('web.QWeb');
var session = require('web.session');
var utils = require('web.utils');
var viewUtils = require('web.viewUtils');

var qweb = core.qweb;
var _t = core._t;

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
        var modifiers = node.attrs.modifiers || {};
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
    config: { // the KanbanRecord and KanbanColumn classes to use (may be overridden)
        KanbanColumn: KanbanColumn,
        KanbanRecord: KanbanRecord,
    },
    custom_events: _.extend({}, BasicRenderer.prototype.custom_events || {}, {
        close_quick_create: '_onCloseQuickCreate',
        cancel_quick_create: '_onCancelQuickCreate',
        set_progress_bar_state: '_onSetProgressBarState',
        start_quick_create: '_onStartQuickCreate',
        quick_create_column_updated: '_onQuickCreateColumnUpdated',
    }),
    events:_.extend({}, BasicRenderer.prototype.events || {}, {
        'keydown .o_kanban_record' : '_onRecordKeyDown'
    }),
    sampleDataTargets: [
        '.o_kanban_counter',
        '.o_kanban_record',
        '.o_kanban_toggle_fold',
        '.o_column_folded',
        '.o_column_archive_records',
        '.o_column_unarchive_records',
    ],

    /**
     * @override
     * @param {Object} params
     * @param {boolean} params.quickCreateEnabled set to false to disable the
     *   quick create feature
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);

        this.widgets = [];
        this.qweb = new QWeb(config.isDebug(), {_s: session.origin}, false);
        var templates = findInNode(this.arch, function (n) { return n.tag === 'templates';});
        transformQwebTemplate(templates, state.fields);
        this.qweb.add_template(utils.json_node_to_xml(templates));
        this.examples = params.examples;
        this.recordOptions = _.extend({}, params.record_options, {
            qweb: this.qweb,
            viewType: 'kanban',
        });
        this.columnOptions = _.extend({KanbanRecord: this.config.KanbanRecord}, params.column_options);
        if (this.columnOptions.hasProgressBar) {
            this.columnOptions.progressBarStates = {};
        }
        this.quickCreateEnabled = params.quickCreateEnabled;
        if (!params.readOnlyMode) {
            var handleField = _.findWhere(this.state.fieldsInfo.kanban, {widget: 'handle'});
            this.handleField = handleField && handleField.name;
        }
        this._setState(state);
    },
    /**
     * Called each time the renderer is attached into the DOM.
     */
    on_attach_callback: function () {
        this._super(...arguments);
        if (this.quickCreate) {
            this.quickCreate.on_attach_callback();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Displays the quick create record in the requested column (first one by
     * default)
     *
     * @params {string} [groupId] local id of the group in which the quick create
     *   must be inserted
     * @returns {Promise}
     */
    addQuickCreate: function (groupId) {
        let kanbanColumn;
        if (groupId) {
            kanbanColumn = this.widgets.find(column => column.db_id === groupId);
        }
        kanbanColumn = kanbanColumn || this.widgets[0];
        return kanbanColumn.addQuickCreate();
    },
    /**
     * Focuses the first kanban record
     */
    giveFocus: function () {
        this.$('.o_kanban_record:first').focus();
    },
    /**
     * Toggle fold/unfold the Column quick create widget
     */
    quickCreateToggleFold: function () {
        this.quickCreate.toggleFold();
        this._toggleNoContentHelper();
    },
    /**
     * Updates a given column with its new state.
     *
     * @param {string} localID the column id
     * @param {Object} columnState
     * @param {Object} [options]
     * @param {Object} [options.state] if set, this represents the new state
     * @param {boolean} [options.openQuickCreate] if true, directly opens the
     *   QuickCreate widget in the updated column
     *
     * @returns {Promise}
     */
    updateColumn: function (localID, columnState, options) {
        var self = this;
        var KanbanColumn = this.config.KanbanColumn;
        var newColumn = new KanbanColumn(this, columnState, this.columnOptions, this.recordOptions);
        var index = _.findIndex(this.widgets, {db_id: localID});
        var column = this.widgets[index];
        this.widgets[index] = newColumn;
        if (options && options.state) {
            this._setState(options.state);
        }
        return newColumn.appendTo(document.createDocumentFragment()).then(function () {
            var def;
            if (options && options.openQuickCreate) {
                def = newColumn.addQuickCreate();
            }
            return Promise.resolve(def).then(function () {
                newColumn.$el.insertAfter(column.$el);
                self._toggleNoContentHelper();
                // When a record has been quick created, the new column directly
                // renders the quick create widget (to allow quick creating several
                // records in a row). However, as we render this column in a
                // fragment, the quick create widget can't be correctly focused. So
                // we manually call on_attach_callback to focus it once in the DOM.
                newColumn.on_attach_callback();
                column.destroy();
            });
        });
    },
    /**
     * Updates a given record with its new state.
     *
     * @param {Object} recordState
     * @returns {Promise}
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
            return record.update(recordState);
        }
        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {DOMElement} currentColumn
     */
    _focusOnNextCard: function (currentCardElement) {
        var nextCard = currentCardElement.nextElementSibling;
        if (nextCard) {
            nextCard.focus();
        }
    },
    /**
     * Tries to give focus to the previous card, and returns true if successful
     *
     * @private
     * @param {DOMElement} currentColumn
     * @returns {boolean}
     */
    _focusOnPreviousCard: function (currentCardElement) {
        var previousCard = currentCardElement.previousElementSibling;
        if (previousCard && previousCard.classList.contains("o_kanban_record")) { //previous element might be column title
            previousCard.focus();
            return true;
        }
    },
    /**
     * Returns the default columns for the kanban view example background.
     * You can override this method to easily customize the column names.
     *
     * @private
     */
    _getGhostColumns: function () {
        if (this.examples && this.examples.ghostColumns) {
            return this.examples.ghostColumns;
        }
        return _.map(_.range(1, 5), function (num) {
            return _.str.sprintf(_t("Column %s"), num);
        });
    },
    /**
     * Render the Example Ghost Kanban card on the background
     *
     * @private
     * @param {DocumentFragment} fragment
     */
    _renderExampleBackground: function (fragment) {
        var $background = $(qweb.render('KanbanView.ExamplesBackground', {ghostColumns: this._getGhostColumns()}));
        $background.appendTo(fragment);
    },
    /**
     * Renders empty invisible divs in a document fragment.
     *
     * @private
     * @param {DocumentFragment} fragment
     * @param {integer} nbDivs the number of divs to append
     * @param {Object} [options]
     * @param {string} [options.inlineStyle]
     */
    _renderGhostDivs: function (fragment, nbDivs, options) {
        var ghostDefs = [];
        for (var $ghost, i = 0; i < nbDivs; i++) {
            $ghost = $('<div>').addClass('o_kanban_record o_kanban_ghost');
            if (options && options.inlineStyle) {
                $ghost.attr('style', options.inlineStyle);
            }
            var def = $ghost.appendTo(fragment);
            ghostDefs.push(def);
        }
        return Promise.all(ghostDefs);
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
        var KanbanColumn = this.config.KanbanColumn;
        _.each(this.state.data, function (group) {
            var column = new KanbanColumn(self, group, self.columnOptions, self.recordOptions);
            var def;
            if (!group.value) {
                def = column.prependTo(fragment); // display the 'Undefined' group first
                self.widgets.unshift(column);
            } else {
                def = column.appendTo(fragment);
                self.widgets.push(column);
            }
            self.defs.push(def);
        });

        // remove previous sorting
        if(this.$el.sortable('instance') !== undefined) {
            this.$el.sortable('destroy');
        }
        if (this.groupedByM2O) {
            // Enable column sorting
            this.$el.sortable({
                axis: 'x',
                items: '> .o_kanban_group',
                handle: '.o_column_title',
                cursor: 'move',
                revert: 150,
                delay: 100,
                tolerance: 'pointer',
                forcePlaceholderSize: true,
                stop: function () {
                    var ids = [];
                    self.$('.o_kanban_group').each(function (index, u) {
                        // Ignore 'Undefined' column
                        if (_.isNumber($(u).data('id'))) {
                            ids.push($(u).data('id'));
                        }
                    });
                    self.trigger_up('resequence_columns', {ids: ids});
                },
            });

            if (this.createColumnEnabled) {
                this.quickCreate = new ColumnQuickCreate(this, {
                    applyExamplesText: this.examples && this.examples.applyExamplesText,
                    examples: this.examples && this.examples.examples,
                });
                this.defs.push(this.quickCreate.appendTo(fragment).then(function () {
                    // Open it directly if there is no column yet
                    if (!self.state.data.length) {
                        self.quickCreate.toggleFold();
                        self._renderExampleBackground(fragment);
                    }
                }));
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
        var KanbanRecord = this.config.KanbanRecord;
        var kanbanRecord;
        _.each(this.state.data, function (record) {
            kanbanRecord = new KanbanRecord(self, record, self.recordOptions);
            self.widgets.push(kanbanRecord);
            var def = kanbanRecord.appendTo(fragment);
            self.defs.push(def);
        });

        // enable record resequencing if there is a field with widget='handle'
        // and if there is no orderBy (in this case we assume that the widget
        // has been put on the first default order field of the model), or if
        // the first orderBy field is the one with widget='handle'
        var orderedBy = this.state.orderedBy;
        var hasHandle = this.handleField &&
                        (orderedBy.length === 0 || orderedBy[0].name === this.handleField);
        if (hasHandle) {
            this.$el.sortable({
                items: '.o_kanban_record:not(.o_kanban_ghost)',
                cursor: 'move',
                revert: 0,
                delay: 0,
                tolerance: 'pointer',
                forcePlaceholderSize: true,
                stop: function (event, ui) {
                    self._moveRecord(ui.item.data('record').db_id, ui.item.index());
                },
            });
        }

        // append ghost divs to ensure that all kanban records are left aligned
        var prom = Promise.all(self.defs).then(function () {
            var options = {};
            if (kanbanRecord) {
                options.inlineStyle = kanbanRecord.$el.attr('style');
            }
            return self._renderGhostDivs(fragment, 6, options);
        });
        this.defs.push(prom);
    },
    /**
     * @override
     * @private
     */
    _renderView: function () {
        var self = this;

        // render the kanban view
        var isGrouped = !!this.state.groupedBy.length;
        var fragment = document.createDocumentFragment();
        var defs = [];
        this.defs = defs;
        if (isGrouped) {
            this._renderGrouped(fragment);
        } else {
            this._renderUngrouped(fragment);
        }
        delete this.defs;

        return this._super.apply(this, arguments).then(function () {
            return Promise.all(defs).then(function () {
                self.$el.empty();
                self.$el.toggleClass('o_kanban_grouped', isGrouped);
                self.$el.toggleClass('o_kanban_ungrouped', !isGrouped);
                self.$el.append(fragment);
                self._toggleNoContentHelper();
            });
        });
    },
    /**
     * @param {boolean} [remove] if true, the nocontent helper is always removed
     * @private
     */
    _toggleNoContentHelper: function (remove) {
        var displayNoContentHelper =
            !remove &&
            !this._hasContent() &&
            !!this.noContentHelp &&
            !(this.quickCreate && !this.quickCreate.folded) &&
            !this.state.isGroupedByM2ONoColumn;

        var $noContentHelper = this.$('.o_view_nocontent');

        if (displayNoContentHelper && !$noContentHelper.length) {
            this._renderNoContentHelper();
        }
        if (!displayNoContentHelper && $noContentHelper.length) {
            $noContentHelper.remove();
        }
    },
    /**
     * Sets the current state and updates some internal attributes accordingly.
     *
     * @override
     */
    _setState: function () {
        this._super(...arguments);

        var groupByField = this.state.groupedBy[0];
        var cleanGroupByField = this._cleanGroupByField(groupByField);
        var groupByFieldAttrs = this.state.fields[cleanGroupByField];
        var groupByFieldInfo = this.state.fieldsInfo.kanban[cleanGroupByField];
        // Deactivate the drag'n'drop if the groupedBy field:
        // - is a date or datetime since we group by month or
        // - is readonly (on the field attrs or in the view)
        var draggable = true;
        var grouped_by_date = false;
        if (groupByFieldAttrs) {
            if (groupByFieldAttrs.type === "date" || groupByFieldAttrs.type === "datetime") {
                draggable = false;
                grouped_by_date = true;
            } else if (groupByFieldAttrs.readonly !== undefined) {
                draggable = !(groupByFieldAttrs.readonly);
            }
        }
        if (groupByFieldInfo) {
            if (draggable && groupByFieldInfo.readonly !== undefined) {
                draggable = !(groupByFieldInfo.readonly);
            }
        }
        this.groupedByM2O = groupByFieldAttrs && (groupByFieldAttrs.type === 'many2one');
        var relation = this.groupedByM2O && groupByFieldAttrs.relation;
        var groupByTooltip = groupByFieldInfo && groupByFieldInfo.options.group_by_tooltip;
        this.columnOptions = _.extend(this.columnOptions, {
            draggable: draggable,
            group_by_tooltip: groupByTooltip,
            groupedBy: groupByField,
            grouped_by_m2o: this.groupedByM2O,
            grouped_by_date: grouped_by_date,
            relation: relation,
            quick_create: this.quickCreateEnabled && viewUtils.isQuickCreateEnabled(this.state),
        });
        this.createColumnEnabled = this.groupedByM2O && this.columnOptions.group_creatable;
    },
    /**
     * Remove date/datetime magic grouping info to get proper field attrs/info from state
     * ex: sent_date:month will become sent_date
     *
     * @private
     * @param {string} groupByField
     * @returns {string}
     */
    _cleanGroupByField: function (groupByField) {
        var cleanGroupByField = groupByField;
        if (cleanGroupByField && cleanGroupByField.indexOf(':') > -1) {
            cleanGroupByField = cleanGroupByField.substring(0, cleanGroupByField.indexOf(':'));
        }

        return cleanGroupByField;
    },
    /**
     * Moves the focus on the first card of the next column in a given direction
     * This ignores the folded columns and skips over the empty columns.
     * In ungrouped kanban, moves the focus to the next/previous card
     *
     * @param {DOMElement} eventTarget  the target of the keydown event
     * @param {string} direction  contains either 'LEFT' or 'RIGHT'
     */
    _focusOnCardInColumn: function(eventTarget, direction) {
        var currentColumn = eventTarget.parentElement;
        var hasSelectedACard = false;
        var cannotSelectAColumn = false;
        while (!hasSelectedACard && !cannotSelectAColumn) {
            var candidateColumn = direction === 'LEFT' ?
                                    currentColumn.previousElementSibling :
                                    currentColumn.nextElementSibling ;
            currentColumn = candidateColumn;
            if (candidateColumn) {
                var allCardsOfCandidateColumn =
                    candidateColumn.getElementsByClassName('o_kanban_record');
                if (allCardsOfCandidateColumn.length) {
                    allCardsOfCandidateColumn[0].focus();
                    hasSelectedACard = true;
                }
            }
            else { // either there are no more columns in the direction or
                   // this is not a grouped kanban
                direction === 'LEFT' ?
                    this._focusOnPreviousCard(eventTarget) :
                    this._focusOnNextCard(eventTarget);
                cannotSelectAColumn = true;
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCancelQuickCreate: function () {
        this._toggleNoContentHelper();
    },
    /**
     * Closes the opened quick create widgets in columns
     *
     * @private
     */
    _onCloseQuickCreate: function () {
        if (this.state.groupedBy.length) {
            _.invoke(this.widgets, 'cancelQuickCreate');
        }
        this._toggleNoContentHelper();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onQuickCreateColumnUpdated: function (ev) {
        ev.stopPropagation();
        this._toggleNoContentHelper();
        this._updateExampleBackground();
    },
    /**
     * @private
     * @param {KeyboardEvent} e
     */
    _onRecordKeyDown: function(e) {
        switch(e.which) {
            case $.ui.keyCode.DOWN:
                this._focusOnNextCard(e.currentTarget);
                e.stopPropagation();
                e.preventDefault();
                break;
            case $.ui.keyCode.UP:
                const previousFocused = this._focusOnPreviousCard(e.currentTarget);
                if (!previousFocused) {
                    this.trigger_up('navigation_move', { direction: 'up' });
                }
                e.stopPropagation();
                e.preventDefault();
                break;
            case $.ui.keyCode.RIGHT:
                this._focusOnCardInColumn(e.currentTarget, 'RIGHT');
                e.stopPropagation();
                e.preventDefault();
                break;
            case $.ui.keyCode.LEFT:
                this._focusOnCardInColumn(e.currentTarget, 'LEFT');
                e.stopPropagation();
                e.preventDefault();
                break;
        }
    },
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
    /**
     * Closes the opened quick create widgets in columns
     *
     * @private
     */
    _onStartQuickCreate: function () {
        this._toggleNoContentHelper(true);
    },
    /**
     * Hide or display the background example:
     *  - displayed when quick create column is display and there is no column else
     *  - hidden otherwise
     *
     * @private
     **/
    _updateExampleBackground: function () {
        var $elem = this.$('.o_kanban_example_background_container');
        if (!this.state.data.length && !$elem.length) {
            this._renderExampleBackground(this.$el);
        } else {
            $elem.remove();
        }
    },
});

return KanbanRenderer;

});
