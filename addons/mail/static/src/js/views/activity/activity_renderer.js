odoo.define('mail.ActivityRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var ActivityRecord = require('mail.ActivityRecord');
var core = require('web.core');
var field_registry = require('web.field_registry');
var qweb = require('web.QWeb');
var session = require('web.session');
var utils = require('web.utils');

var KanbanActivity = field_registry.get('kanban_activity');
var _t = core._t;
var QWeb = core.qweb;

var ActivityRenderer = AbstractRenderer.extend({
    className: 'o_activity_view',
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

        this.qweb = new qweb(session.debug, {_s: session.origin});
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
        this.$el.addClass('table-responsive');
        this.$el.html(QWeb.render('mail.ActivityView', { isEmpty: !this.state.activity_types.length }));
        this.$('table')
            .append(this._renderHeader())
            .append(this._renderBody())
            .append(this._renderFooter());
        return this._super.apply(this, arguments);
    },
    /**
     * @private
     * @returns {jQueryElement} a jquery element <tbody>
     */
    _renderBody: function () {
        var $rows = _.map(this.state.activity_res_ids, this._renderRow.bind(this));
        return $('<tbody>').append($rows);
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
     * @returns {jQueryElement} a jquery element <thead>
     */
    _renderHeader: function () {
        var $tr = $('<tr>')
                .append($('<th>')) //empty cell for name
                .append(_.map(this.state.activity_types, this._renderHeaderCell.bind(this)));
        return $('<thead>').append($tr);
    },
    /**
     * @private
     * @param {Object} activity_type
     * @returns {jQueryElement} a <th> element
     */
    _renderHeaderCell: function (activity_type) {
        return QWeb.render('mail.ActivityViewHeaderCell', {
            id: activity_type[0],
            name: activity_type[1],
            template_list: activity_type[2] || [],
        });
    },
    /**
     * @private
     * @param {integer} resId
     * @returns {jQueryElement} a <tr> element
     */
    _renderRow: function (resId) {
        var self = this;
        var record = this._getRecord(resId);
        var $nameTD = $('<td>', {
            class: _.contains(this.filteredResIDs, resId) ? 'o_activity_filter_' + this.activeFilter : '',
        });
        var activityRecord = new ActivityRecord(this, record, { qweb: this.qweb });
        activityRecord.appendTo($nameTD);

        var $cells = _.map(this.state.activity_types, function (node) {
            var activity_type_id = node[0];
            var activity_group = self.state.grouped_activities[resId];
            activity_group = activity_group && activity_group[activity_type_id] || {count: 0, ids: [], state: false};

            var $td = $(QWeb.render('mail.ActivityViewRow', {
                resId: resId,
                activityGroup: activity_group,
                activityTypeId: activity_type_id,
            }));
            if (activity_group.state) {
                var record = self.getKanbanActivityData(activity_group, resId);
                var widget = new KanbanActivity(self, "activity_ids", record, {});
                widget.appendTo($td).then(function() {
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
            }
            return $td;
        });
        var $tr = $('<tr/>', {class: 'o_data_row'})
            .append($nameTD)
            .append($cells);
        return $tr;
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
});

return ActivityRenderer;

});
