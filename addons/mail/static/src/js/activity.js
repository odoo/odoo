odoo.define('mail.Activity', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var BasicModel = require('web.BasicModel');
var core = require('web.core');
var field_registry = require('web.field_registry');
var time = require('web.time');
var utils = require('mail.utils');

var QWeb = core.qweb;
var _t = core._t;

/**
 * Fetches activities and postprocesses them.
 *
 * This standalone function performs an RPC, but to do so, it needs an instance
 * of a widget that implements the _rpc() function.
 *
 * @todo i'm not very proud of the widget instance given in arguments, we should
 *   probably try to do it a better way in the future.
 *
 * @param {Widget} self a widget instance that can perform RPCs
 * @param {Array} ids the ids of activities to read
 * @return {Deferred<Array>} resolved with the activities
 */
function _readActivities(self, ids) {
    if (!ids.length) {
        return $.when([]);
    }
    return self._rpc({
        model: 'mail.activity',
        method: 'read',
        args: [ids],
        context: (self.record && self.record.getContext()) || self.getSession().user_context,
    }).then(function (activities) {
        // convert create_date and date_deadline to moments
        _.each(activities, function (activity) {
            activity.create_date = moment(time.auto_str_to_date(activity.create_date));
            activity.date_deadline = moment(time.auto_str_to_date(activity.date_deadline));
        });

        // sort activities by due date
        activities = _.sortBy(activities, 'date_deadline');

        return activities;
    });
}

BasicModel.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetches the activities displayed by the activity field widget in form
     * views.
     *
     * @private
     * @param {Object} record - an element from the localData
     * @param {string} fieldName
     * @return {Deferred<Array>} resolved with the activities
     */
    _fetchSpecialActivity: function (record, fieldName) {
        var localID = (record._changes && fieldName in record._changes) ?
                        record._changes[fieldName] :
                        record.data[fieldName];
        return _readActivities(this, this.localData[localID].res_ids);
    },
});

/**
 * Set the 'label_delay' entry in activity data according to the deadline date
 * @param {Array} activities list of activity Object
 * @return {Array} : list of modified activity Object
 */
var setDelayLabel = function(activities){
    var today = moment().startOf('day');
    _.each(activities, function(activity){
        var to_display = '';
        var diff = activity.date_deadline.diff(today, 'days', true); // true means no rounding
        if(diff === 0){
            to_display = _t('Today');
        }else{
            if(diff < 0){ // overdue
                if(diff === -1){
                    to_display = _t('Yesterday');
                }else{
                    to_display = _.str.sprintf(_t('%d days overdue'), Math.abs(diff));
                }
            }else{ // due
                if(diff === 1){
                    to_display = _t('Tomorrow');
                }else{
                    to_display = _.str.sprintf(_t('Due in %d days'), Math.abs(diff));
                }
            }
        }
        activity.label_delay = to_display;
    });
    return activities;
};

var AbstractActivityField = AbstractField.extend({
    // private
    _markActivityDone: function (id, feedback) {
        return this._rpc({
                model: 'mail.activity',
                method: 'action_feedback',
                args: [[id]],
                kwargs: {feedback: feedback},
                context: this.record.getContext(),
            });
    },
    _scheduleActivity: function (id, previous_activity_type_id, callback) {
        var action = {
            type: 'ir.actions.act_window',
            res_model: 'mail.activity',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_res_id: this.res_id,
                default_res_model: this.model,
                default_previous_activity_type_id: previous_activity_type_id,
            },
            res_id: id || false,
        };
        return this.do_action(action, { on_close: callback });
    },
});

// -----------------------------------------------------------------------------
// Activities Widget for Form views ('mail_activity' widget)
// -----------------------------------------------------------------------------
var Activity = AbstractActivityField.extend({
    className: 'o_mail_activity',
    events: {
        'click .o_activity_edit': '_onEditActivity',
        'click .o_activity_unlink': '_onUnlinkActivity',
        'click .o_activity_done': '_onMarkActivityDone',
    },
    specialData: '_fetchSpecialActivity',

    // inherited
    init: function () {
        this._super.apply(this, arguments);
        this.activities = this.record.specialData[this.name];
    },
    _render: function () {
        _.each(this.activities, function (activity) {
            if (activity.note) {
                activity.note = utils.parse_and_transform(activity.note, utils.add_link);
            }
        });
        var activities = setDelayLabel(this.activities);
        if (activities.length) {
            var nbActivities = _.countBy(activities, 'state');
            this.$el.html(QWeb.render('mail.activity_items', {
                activities: activities,
                nbPlannedActivities: nbActivities.planned,
                nbTodayActivities: nbActivities.today,
                nbOverdueActivities: nbActivities.overdue,
                date_format: time.getLangDateFormat(),
                datetime_format: time.getLangDatetimeFormat(),
            }));
        } else {
            this.$el.empty();
        }
    },
    _reset: function (record) {
        this._super.apply(this, arguments);
        this.activities = this.record.specialData[this.name];
        // the mail widgets being persistent, one need to update the res_id on reset
        this.res_id = record.res_id;
    },

    // public
    scheduleActivity: function (previous_activity_type_id) {
        var callback = this._reload.bind(this, {activity: true, thread: true});
        return this._scheduleActivity(false, previous_activity_type_id, callback);
    },
    // private
    _reload: function (fieldsToReload) {
        this.trigger_up('reload_mail_fields', fieldsToReload);
    },

    /** Binds a focusout handler on a bootstrap popover
     *  Useful to do some operations on the popover's HTML,
     *  like keeping the user's input for the feedback
     *  @param {JQuery} $popover_el: the element on which
     *    the popover() method has been called
     */
    _bindPopoverFocusout: function ($popover_el) {
        var self = this;
        // Retrieve the actual popover's HTML
        var $popover = $popover_el.data("bs.popover").tip();
        var activity_id = $popover_el.data('activity-id');
        $popover.off('focusout');
        $popover.focusout(function (e) {
            // outside click of popover hides the popover
            // e.relatedTarget is the element receiving the focus
            self.feedbackValue[activity_id] = $popover.find('#activity_feedback').val().trim();
            if(!$popover.is(e.relatedTarget) && !$popover.find(e.relatedTarget).length) {
                $popover_el.popover('hide');
            }
        });
    },

    // handlers
    _onEditActivity: function (event, options) {
        event.preventDefault();
        var self = this;
        var activity_id = $(event.currentTarget).data('activity-id');
        var action = _.defaults(options || {}, {
            type: 'ir.actions.act_window',
            res_model: 'mail.activity',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_res_id: this.res_id,
                default_res_model: this.model,
            },
            res_id: activity_id,
        });
        return this.do_action(action, {
            on_close: function () {
                self._reload({activity: true, thread: true});
            },
        });
    },
    _onUnlinkActivity: function (event, options) {
        event.preventDefault();
        var activity_id = $(event.currentTarget).data('activity-id');
        options = _.defaults(options || {}, {
            model: 'mail.activity',
            args: [[activity_id]],
        });
        return this._rpc({
                model: options.model,
                method: 'unlink',
                args: options.args,
            })
            .then(this._reload.bind(this, {activity: true}));
    },

    _onMarkActivityDone: function (event) {
        event.preventDefault();
        var self = this;
        this.feedbackValue = this.feedbackValue || {};
        var $popover_el = $(event.currentTarget);
        var activity_id = $popover_el.data('activity-id');
        var previous_activity_type_id = $popover_el.data('previous-activity-type-id');
        if (!$popover_el.data('bs.popover')) {
            this.feedbackValue[activity_id] = "";
            $popover_el.popover({
                title : _t('Feedback'),
                html: 'true',
                trigger:'click',
                content : function() {
                    var $popover = $(QWeb.render("mail.activity_feedback_form", {'previous_activity_type_id': previous_activity_type_id}));
                    $popover.find('#activity_feedback').val(self.feedbackValue[activity_id]);
                    $popover.on('click', '.o_activity_popover_done_next', function () {
                        var feedback = _.escape($popover.find('#activity_feedback').val());
                        var previous_activity_type_id = $popover_el.data('previous-activity-type-id') || false;
                        self._markActivityDone(activity_id, feedback)
                            .then(self.scheduleActivity.bind(self, previous_activity_type_id));
                    });
                    $popover.on('click', '.o_activity_popover_done', function () {
                        var feedback = _.escape($popover.find('#activity_feedback').val());
                        self._markActivityDone(activity_id, feedback)
                            .then(self._reload.bind(self, {activity: true, thread: true}));
                    });
                    $popover.on('click', '.o_activity_popover_discard', function () {
                        $popover_el.popover('hide');
                    });
                    return $popover;
                },
            }).on("show.bs.popover", function (e) {
                var $popover = $(this).data("bs.popover").tip();
                $popover.addClass('o_mail_activity_feedback').attr('tabindex', 0);
                $(".o_mail_activity_feedback.popover").not(e.target).popover("hide");
            }).on("shown.bs.popover", function () {
                var $popover = $(this).data("bs.popover").tip();
                $popover.find('#activity_feedback').focus();
                self._bindPopoverFocusout($(this));
            }).popover('show');
        }
    },
});

// -----------------------------------------------------------------------------
// Activities Widget for Kanban views ('kanban_activity' widget)
// -----------------------------------------------------------------------------
var KanbanActivity = AbstractActivityField.extend({
    template: 'mail.KanbanActivity',
    events: {
        'click .o_activity_btn': '_onButtonClicked',
        'click .o_schedule_activity': '_onScheduleActivity',
        'click .o_mark_as_done': '_onMarkActivityDone',
    },

    // inherited
    init: function (parent, name, record) {
        this._super.apply(this, arguments);
        var selection = {};
        _.each(record.fields.activity_state.selection, function (value) {
            selection[value[0]] = value[1];
        });
        this.selection = selection;
        this._setState(record);
    },
    _render: function () {
        var $span = this.$(".o_activity_btn > span");
        $span.removeClass(function (index, classNames) {
            return classNames.split(/\s+/).filter(function (className) {
                return _.str.startsWith(className, 'o_activity_color_');
            }).join(' ');
        });
        $span.addClass('o_activity_color_' + (this.activity_state || 'default'));
        if (this.$el.hasClass('open')) {
            // note: this part of the rendering might be asynchronous
            this._renderDropdown();
        }
    },
    _reset: function (record) {
        this._super.apply(this, arguments);
        this._setState(record);
    },

    // private
    _reload: function () {
        this.trigger_up('reload', {db_id: this.record_id});
    },
    _renderDropdown: function () {
        var self = this;
        this.$('.o_activity').html(QWeb.render("mail.KanbanActivityLoading"));
        return _readActivities(this, this.value.res_ids).then(function (activities) {
            self.$('.o_activity').html(QWeb.render("mail.KanbanActivityDropdown", {
                selection: self.selection,
                records: _.groupBy(setDelayLabel(activities), 'state'),
                uid: self.getSession().uid,
            }));
        });
    },
    _setState: function (record) {
        this.record_id = record.id;
        this.activity_state = this.recordData.activity_state;
    },

    // handlers
    _onButtonClicked: function (event) {
        event.preventDefault();
        if (!this.$el.hasClass('open')) {
            this._renderDropdown();
        }
    },
    _onMarkActivityDone: function (event) {
        event.stopPropagation();
        var activity_id = $(event.currentTarget).data('activity-id');
        this._markActivityDone(activity_id).then(this._reload.bind(this));
    },
    _onScheduleActivity: function (event) {
        var activity_id = $(event.currentTarget).data('activity-id') || false;
        return this._scheduleActivity(activity_id, false, this._reload.bind(this));
    },
});

field_registry
    .add('mail_activity', Activity)
    .add('kanban_activity', KanbanActivity);

return Activity;

});
