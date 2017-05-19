odoo.define('mail.Activity', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var concurrency = require('web.concurrency');
var core = require('web.core');
var field_registry = require('web.field_registry');
var time = require('web.time');

var QWeb = core.qweb;
var _t = core._t;

/**
 * Set the 'label_delay' entry in activity data according to the deadline date
 * @param {Array} list of activity Object
 * @return {Array} : list of modified activity Object
 */
var setDelayLabel = function(activities){
    var today = moment().startOf('day');
    _.each(activities, function(activity){
        var to_display = '';
        var deadline = moment(activity.date_deadline + ' 00:00:00');
        var diff = deadline.diff(today, 'days', true); // true means no rounding
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
    // inherited
    init: function () {
        this._super.apply(this, arguments);
        this.activities = [];
    },

    // private
    _markActivityDone: function (id, feedback) {
        return this._rpc({
                model: 'mail.activity',
                method: 'action_done',
                args: [[id]],
                kwargs: {feedback: feedback},
            });
    },
    _readActivities: function () {
        var self = this;
        var missing_ids = _.difference(this.value.res_ids, _.pluck(this.activities, 'id'));
        var fetch_def;
        if (missing_ids.length) {
            fetch_def = this._rpc({
                    model: 'mail.activity',
                    method: 'read',
                    args: [missing_ids],
                });
        }
        return $.when(fetch_def).then(function (results) {
            // filter out activities that are no longer linked to this record
            self.activities = _.filter(self.activities.concat(results || []), function (activity) {
                return _.contains(self.value.res_ids, activity.id);
            });
            // sort activities by due date
            self.activities = _.sortBy(self.activities, 'date_deadline');
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

    // inherited
    init: function () {
        this._super.apply(this, arguments);
        this.dp = new concurrency.DropPrevious();
    },
    _render: function () {
        // note: the rendering of this widget is asynchronous as it needs to
        // fetch the details of the linked activities
        var self = this;
        var fetch_def = this.dp.add(this._readActivities());
        return fetch_def.then(function () {
            _.each(self.activities, function (activity) {
                activity.time_ago = moment(time.auto_str_to_date(activity.create_date)).fromNow();
            });
            self.$el.html(QWeb.render('mail.activity_items', {
                activities: setDelayLabel(self.activities),
            }));
        });
    },
    _reset: function (record) {
        this._super.apply(this, arguments);
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

    // handlers
    _onEditActivity: function (event) {
        event.preventDefault();
        var self = this;
        var activity_id = $(event.currentTarget).data('activity-id');
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
            },
            res_id: activity_id,
        };
        return this.do_action(action, {
            on_close: function () {
                // remove the edited activity from the array of fetched activities to
                // force a reload of that activity
                self.activities = _.reject(self.activities, {id: activity_id});
                self._reload({activity: true, thread: true});
            },
        });
    },
    _onUnlinkActivity: function (event) {
        event.preventDefault();
        var activity_id = $(event.currentTarget).data('activity-id');
        return this._rpc({
                model: 'mail.activity',
                method: 'unlink',
                args: [[activity_id]],
            })
            .then(this._reload.bind(this, {activity: true}));
    },
    _onMarkActivityDone: function (event) {
        event.preventDefault();
        var self = this;
        var $popover_el = $(event.currentTarget);
        var activity_id = $popover_el.data('activity-id');
        var previous_activity_type_id = $popover_el.data('previous-activity-type-id');
        if (!$popover_el.data('bs.popover')) {
            $popover_el.popover({
                title : _t('Feedback'),
                html: 'true',
                trigger:'click',
                content : function() {
                    var $popover = $(QWeb.render("mail.activity_feedback_form", {'previous_activity_type_id': previous_activity_type_id}));
                    $popover.on('click', '.o_activity_popover_done_next', function () {
                        var feedback = _.escape($popover.find('#activity_feedback').val());
                        var previous_activity_type_id = $popover_el.data('previous-activity-type-id');
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
                $popover.off('focusout');
                $popover.focusout(function (e) {
                    // outside click of popover hide the popover
                    // e.relatedTarget is the element receiving the focus
                    if(!$popover.is(e.relatedTarget) && !$popover.find(e.relatedTarget).length) {
                        $popover.popover('hide');
                    }
                });
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
        return this._readActivities().then(function () {
            self.$('.o_activity').html(QWeb.render("mail.KanbanActivityDropdown", {
                selection: self.selection,
                records: _.groupBy(setDelayLabel(self.activities), 'state'),
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
        this._renderDropdown();
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
