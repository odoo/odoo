odoo.define('mail.ActivityRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var ActivityRecord = require('mail.ActivityRecord');
var config = require('web.config');
var core = require('web.core');
var field_registry = require('web.field_registry');
var KanbanColumnProgressBar = require('web.KanbanColumnProgressBar');
var qweb = require('web.QWeb');
var session = require('web.session');
var utils = require('web.utils');

var KanbanActivity = field_registry.get('kanban_activity');
var _t = core._t;
var QWeb = core.qweb;

var ActivityRenderer = AbstractRenderer.extend({
    className: 'o_activity_view',
    custom_events: {
        'set_progress_bar_state': '_onSetProgressBarState',
    },
    events: {
        'click .o_send_mail_template': '_onSenMailTemplateClicked',
        'click .o_activity_empty_cell': '_onEmptyCell',
        'click .o_record_selector': '_onRecordSelector',
    },

    /**
     * @override
     * @param {Object} params.templates
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);

        this.qweb = new qweb(config.isDebug(), {_s: session.origin});
        this.qweb.add_template(utils.json_node_to_xml(params.templates));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object} activityGroup
     * @param {integer} resID
     * @returns {Object}
     */
    getKanbanActivityData: function (activityGroup, resID) {
        return {
            data: {
                activity_ids: {
                    model: 'mail.activity',
                    res_ids: activityGroup.ids,
                },
                activity_state: activityGroup.state,
            },
            fields: {
                activity_ids: {},
                activity_state: {
                    selection: [
                        ['overdue', "Overdue"],
                        ['today', "Today"],
                        ['planned', "Planned"],
                    ],
                },
            },
            fieldsInfo: {},
            model: this.state.model,
            type: 'record',
            res_id: resID,
            getContext: function () {
                return {}; // session.user_context
            },
            //todo intercept event or changes on record to update view
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _getRecord: function (recordId) {
        return _.findWhere(this.state.data, { res_id: recordId });
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        this.$el.addClass('table-responsive');
        this.$el.html(QWeb.render('mail.ActivityView', { isEmpty: !this.state.activity_types.length }));
        return Promise.all([
            this._super.apply(this, arguments),
            this._renderHeader(),
            this._renderBody(),
        ]).then(function (result) {
            self.$('table')
                .append(result[1])
                .append(result[2])
                .append(self._renderFooter());
        });
    },
    /**
     * @private
     * @returns {Promise<jQueryElement>} a jquery element <tbody>
     */
    _renderBody: function () {
        var defs = _.map(this.state.activity_res_ids, this._renderRow.bind(this));
        return Promise.all(defs).then(function ($rows) {
            return $('<tbody>').append($rows);
        });
    },
    /**
     * @private
     * @returns {jQueryElement} a <tfoot> element
     */
    _renderFooter: function () {
        return QWeb.render('mail.ActivityViewFooter');
    },
    /**
     * @private
     * @returns {Promise<jQueryElement>}
     */
    _renderHeader: function () {
        var self = this;
        var activityTypeIds = _.unique(_.flatten(_.map(this.state.grouped_activities, function (act) { return _.keys(act); })));
        var $thead = $(QWeb.render('mail.ActivityViewHeader', {
            types: this.state.activity_types,
            activityTypeIDs: _.map(activityTypeIds, Number),
        }));
        var defs = [];
        activityTypeIds.forEach(function (typeId) {
            defs.push(self._renderProgressBar($thead, typeId));
        });
        return Promise.all(defs).then(function () {
            return $thead;
        });
    },
    /**
     * @private
     * @returns {Promise}
     */
    _renderProgressBar: function ($thead, typeId) {
        var counts = { planned: 0, today: 0, overdue: 0 };
        _.each(this.state.grouped_activities, function (act) {
            if (_.contains(_.keys(act), typeId.toString())) {
                counts[act[typeId].state] += 1;
            }
        });
        var progressBar = new KanbanColumnProgressBar(this, {
            columnID: typeId,
            progressBarStates: {},
        }, {
            count: _.reduce(_.values(counts), (x, y) => x + y),
            fields: {
                activity_state: {
                    type: 'selection',
                    selection: [
                        ['planned', _t('Planned')],
                        ['today', _t('Today')],
                        ['overdue', _t('Overdue')],
                    ],
                },
            },
            progressBarValues: {
                field: 'activity_state',
                colors: { planned: 'success', today: 'warning', overdue: 'danger' },
                counts: counts,
            },
        });
        return progressBar.appendTo($thead.find('th[data-activity-type-id=' + typeId + ']'));
    },
    /**
     * @private
     * @param {integer} resId
     * @returns {Promise<jQueryElement>}
     */
    _renderRow: function (resId) {
        var self = this;
        var defs = [];
        var record = this._getRecord(resId);
        var $nameTD = $('<td>', {
            class: _.contains(this.filteredResIDs, resId) ? 'o_activity_filter_' + this.activeFilter : '',
        });
        var activityRecord = new ActivityRecord(this, record, { qweb: this.qweb });
        defs.push(activityRecord.appendTo($nameTD));

        var $cells = _.map(this.state.activity_types, function (node) {
            var activity_type_id = node[0];
            var activity_group = self.state.grouped_activities[resId];
            activity_group = activity_group && activity_group[activity_type_id] || {count: 0, ids: [], state: false};

            var $td = $(QWeb.render('mail.ActivityViewRow', {
                resId: resId,
                activityGroup: activity_group,
                activityTypeId: activity_type_id,
                widget: self,
            }));
            if (activity_group.state) {
                var record = self.getKanbanActivityData(activity_group, resId);
                var widget = new KanbanActivity(self, "activity_ids", record, {});
                var def = widget.appendTo($td).then(function () {
                    // replace clock by closest deadline
                    var $date = $('<div class="o_closest_deadline">');
                    var date = new Date(activity_group.o_closest_deadline);
                    // To remove year only if current year
                    if (moment().year() === moment(date).year()) {
                        $date.text(date.toLocaleDateString(moment().locale(), { day: 'numeric', month: 'short' }));
                    } else {
                        $date.text(moment(date).format('ll'));
                    }
                    $td.find('a').html($date);
                    if (activity_group.count > 1) {
                        $td.find('a').append($('<span>', {
                            class: 'badge badge-light badge-pill border-0 ' + activity_group.state,
                            text: activity_group.count,
                        }));
                    }
                });
                defs.push(def);
            }
            return $td;
        });
        return Promise.all(defs).then(function () {
            var $tr = $('<tr/>', {class: 'o_data_row'}).attr('data-res-id', resId)
                .append($nameTD)
                .append($cells);
            return $tr;
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onEmptyCell: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        var data = $(ev.currentTarget).data();
        this.trigger_up('empty_cell_clicked', data);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onRecordSelector: function (ev) {
        ev.stopPropagation();
        this.trigger_up('schedule_activity');
    },
    /**
     * @private
     * @override
     * @param {MouseEvent} ev
     */
    _onSenMailTemplateClicked: function (ev) {
        var $target = $(ev.currentTarget);
        var templateID = $target.data('template-id');
        var activityTypeID = $target.closest('th').data('activity-type-id');
        this.trigger_up('send_mail_template', {
            activityTypeID: activityTypeID,
            templateID: templateID,
        });
    },
    /**
     * Rearrange body part of table based on active filter.
     *
     * @private
     * @param {OdooEvent} ev
     */
     _onSetProgressBarState: function (ev) {
        var self = this;

        this.$('th[class*="o_activity_filter_"]').attr('class', 'o_activity_type_cell');
        this.$('.o_kanban_counter_progress div').removeClass('active progress-bar-striped');

        var data = ev.data;
        var arrangedRecords = this.state.activity_res_ids;
        this.activeFilter = data.values.activeFilter;
        if (this.activeFilter) {
            var filteredResIds = _.map(_.keys(_.pick(this.state.grouped_activities, function (act) {
                return act[data.columnID] && act[data.columnID].state === self.activeFilter;
            })), Number);
            arrangedRecords = _.union(_.intersection(this.state.activity_res_ids, filteredResIds), this.state.activity_res_ids);
            this.filteredResIDs = filteredResIds;
        }
        var defs = _.map(arrangedRecords, this._renderRow.bind(this));
        Promise.all(defs).then(function ($rows) {
            self.$('tbody').html($rows);
        });

        if (this.activeFilter) {
            var $header = this.$('th.o_activity_type_cell[data-activity-type-id=' + data.columnID + ']');
            $header.addClass('o_activity_filter_' + this.activeFilter);
        }
    },
});

return ActivityRenderer;

});
