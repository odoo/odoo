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
        this.$el
            .removeClass('table-responsive')
            .empty();

        if (this.state.activity_types.length === 0) {
            this.$el.append(QWeb.render('ActivityView.nodata'));
        } else {
            var $table = $('<table>')
                .addClass('table-bordered')
                .append(this._renderHeader())
                .append(this._renderBody());
            this.$el
                .addClass('table-responsive')
                .append($table);
        }
        return this._super();
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
        this.defs.push(activityRecord.appendTo($nameTD));

        var $cells = _.map(this.state.activity_types, function (node) {
            var $td = $('<td>').addClass("o_activity_summary_cell");
            var activity_type_id = node[0];
            var activity_group = self.state.grouped_activities[resId];
            activity_group = activity_group && activity_group[activity_type_id] || {count: 0, ids: [], state: false};
            if (activity_group.state) {
                $td.addClass(activity_group.state);
            }
            // we need to create a fake record in order to instanciate the KanbanActivity
            // this is the minimal information in order to make it work
            // AAB: move this to a function
            var record = {
                data: {
                    activity_ids: {
                        model: 'mail.activity',
                        res_ids: activity_group.ids,
                    },
                    activity_state: activity_group.state,
                },
                fields: {
                    activity_ids: {},
                    activity_state: {
                        selection: [
                            ['overdue', _t("Overdue")],
                            ['today', _t("Today")],
                            ['planned', _t("Planned")],
                        ],
                    },
                },
                fieldsInfo: {},
                model: self.state.model,
                ref: resId, // not necessary, i think
                type: 'record',
                res_id: resId,
                getContext: function () {
                    return {}; // session.user_context
                },
                //todo intercept event or changes on record to update view
            };
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
                $td.find('a')
                    .empty()
                    .append($date);
            });
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
