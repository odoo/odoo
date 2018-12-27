odoo.define('mail.ActivityRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var core = require('web.core');
var field_registry = require('web.field_registry');

var QWeb = core.qweb;
var _t = core._t;

var ActivityRenderer = AbstractRenderer.extend({
    className: 'o_activity_view',
    events: {
        'click .o_res_name_cell': '_onResNameClicked',
        'click .o_send_mail_template': '_onSenMailTemplateClicked',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        this.$el
            .removeClass('table-responsive')
            .empty();

        if (this.state.data.activity_types.length === 0) {
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
        var $rows = _.map(this.state.data.res_ids, this._renderRow.bind(this));
        return $('<tbody>').append($rows);
    },
    /**
     * @private
     * @returns {jQueryElement} a jquery element <thead>
     */
    _renderHeader: function () {
        var $tr = $('<tr>')
                .append($('<th>')) //empty cell for name
                .append(_.map(this.state.data.activity_types, this._renderHeaderCell.bind(this)));
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
     * @param {Object} data
     * @returns {jQueryElement} a <tr> element
     */
    _renderRow: function (data) {
        var self = this;
        var res_id = data[0];
        var name = data[1];
        var $nameTD = $('<td>')
            .addClass("o_res_name_cell")
            .html(name)
            .data('res-id', res_id);
        var $cells = _.map(this.state.data.activity_types, function (node) {
            var $td = $('<td>').addClass("o_activity_summary_cell");
            var activity_type_id = node[0];
            var activity_group = self.state.data.grouped_activities[res_id][activity_type_id];
            activity_group = activity_group || {count: 0, ids: [], state: false};
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
                            ['overdue', "Overdue"],
                            ['today', "Today"],
                            ['planned', "Planned"],
                        ],
                    },
                },
                fieldsInfo: {},
                model: self.state.data.model,
                ref: res_id, // not necessary, i think
                type: 'record',
                res_id: res_id,
                getContext: function () {
                    return {}; // session.user_context
                },
                //todo intercept event or changes on record to update view
            };
            var KanbanActivity = field_registry.get('kanban_activity');
            var widget = new KanbanActivity(self, "activity_ids", record, {});
            widget.appendTo($td);
            // replace clock by closest deadline
            var $date = $('<div>');
            var formated_date = moment(activity_group.o_closest_deadline).format('ll');
            var current_year = (new Date()).getFullYear();
            if (formated_date.endsWith(current_year)) { // Dummy logic to remove year (only if current year), we will maybe need to improve it
                formated_date = formated_date.slice(0, -4);
                formated_date = formated_date.replace(/( |,)*$/g, "");
            }
            $date
                .text(formated_date)
                .addClass('o_closest_deadline');
            $td.find('a')
                .empty()
                .append($date);
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
    /**
     * @private
     * @override
     * @param {MouseEvent} ev
     */
    _onResNameClicked: function (ev) {
        var resID = $(ev.currentTarget).data('res-id');
        this.trigger_up('open_view_form', {resID: resID});
    },
});

return ActivityRenderer;

});
