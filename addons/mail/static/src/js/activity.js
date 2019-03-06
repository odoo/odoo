odoo.define('mail.Activity', function (require) {
"use strict";

var mailUtils = require('mail.utils');

var AbstractField = require('web.AbstractField');
var BasicModel = require('web.BasicModel');
var core = require('web.core');
var field_registry = require('web.field_registry');
var time = require('web.time');

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
    var context = self.getSession().user_context;
    if (self.record && !_.isEmpty(self.record.getContext())) {
        context = self.record.getContext();
    }
    return self._rpc({
        model: 'mail.activity',
        method: 'activity_format',
        args: [ids],
        context: context,
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
 *
 * @param {Array} activities list of activity Object
 * @return {Array} : list of modified activity Object
 */
var setDelayLabel = function (activities){
    var today = moment().startOf('day');
    _.each(activities, function (activity){
        var toDisplay = '';
        var diff = activity.date_deadline.diff(today, 'days', true); // true means no rounding
        if (diff === 0){
            toDisplay = _t("Today");
        } else {
            if (diff < 0){ // overdue
                if (diff === -1){
                    toDisplay = _t("Yesterday");
                } else {
                    toDisplay = _.str.sprintf(_t("%d days overdue"), Math.abs(diff));
                }
            } else { // due
                if (diff === 1){
                    toDisplay = _t("Tomorrow");
                } else {
                    toDisplay = _.str.sprintf(_t("Due in %d days"), Math.abs(diff));
                }
            }
        }
        activity.label_delay = toDisplay;
    });
    return activities;
};

var BasicActivity = AbstractField.extend({
    events: {
        'click .o_edit_activity': '_onEditActivity',
        'click .o_mark_as_done': '_onMarkActivityDone',
        'click .o_activity_template_preview': '_onPreviewMailTemplate',
        'click .o_schedule_activity': '_onScheduleActivity',
        'click .o_activity_template_send': '_onSendMailTemplate',
        'click .o_unlink_activity': '_onUnlinkActivity',
    },
    init: function () {
        this._super.apply(this, arguments);
        this._draftFeedback = {};
    },

    //------------------------------------------------------------
    // Public
    //------------------------------------------------------------

    /**
     * @param {integer} previousActivityTypeID
     * @return {$.Promise}
     */
    scheduleActivity: function () {
        var callback = this._reload.bind(this, { activity: true, thread: true });
        return this._openActivityForm(false, callback);
    },

    //------------------------------------------------------------
    // Private
    //------------------------------------------------------------

    /**
     * Send a feedback and reload page in order to mark activity as done
     *
     * @private
     * @param {Object} params
     * @param {integer} params.activityID
     * @param {string} params.feedback
     */
    _markActivityDone: function (params) {
        var activityID = params.activityID;
        var feedback = params.feedback;

        this._sendActivityFeedback(activityID, feedback)
            .then(this._reload.bind(this, { activity: true, thread: true }));
    },
    /**
     * Send a feedback and proposes to schedule next activity
     * previousActivityTypeID will be given to new activity to propose activity
     * type based on recommended next activity
     *
     * @private
     * @param {Object} params
     * @param {integer} params.activityID
     * @param {string} params.feedback
     */
    _markActivityDoneAndScheduleNext: function (params) {
        var activityID = params.activityID;
        var feedback = params.feedback;
        var self = this;
        this._rpc({
            model: 'mail.activity',
            method: 'action_feedback_schedule_next',
            args: [[activityID]],
            kwargs: {feedback: feedback},
            context: this.record.getContext(),
        }).then(
            function (rslt_action) {
                if (rslt_action) {
                    self.do_action(rslt_action, {
                        on_close: function () {
                            self.trigger_up('reload');
                        },
                    });
                } else {
                    self.trigger_up('reload');
                }
            }
        );
    },
    /**
     * @private
     * @param {integer} id
     * @param {integer} previousActivityTypeID
     * @param {function} callback
     * @return {$.Deferred}
     */
    _openActivityForm: function (id, callback) {
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
            res_id: id || false,
        };
        return this.do_action(action, { on_close: callback });
    },
    /**
     * @private
     * @param {integer} activityID
     * @param {string} feedback
     * @return {$.Promise}
     */
    _sendActivityFeedback: function (activityID, feedback) {
        return this._rpc({
                model: 'mail.activity',
                method: 'action_feedback',
                args: [[activityID]],
                kwargs: {feedback: feedback},
                context: this.record.getContext(),
            });
    },

    //------------------------------------------------------------
    // Handlers
    //------------------------------------------------------------

    /** Binds a focusout handler on a bootstrap popover
     *  Useful to do some operations on the popover's HTML,
     *  like keeping the user's input for the feedback
     *  @param {JQuery} $popover_el: the element on which
     *    the popover() method has been called
     */
    _bindPopoverFocusout: function ($popover_el) {
        var self = this;
        // Retrieve the actual popover's HTML
        var $popover = $($popover_el.data("bs.popover").tip);
        var activityID = $popover_el.data('activity-id');
        $popover.off('focusout');
        $popover.focusout(function (e) {
            // outside click of popover hide the popover
            // e.relatedTarget is the element receiving the focus
            if (!$popover.is(e.relatedTarget) && !$popover.find(e.relatedTarget).length) {
                self._draftFeedback[activityID] = $popover.find('#activity_feedback').val();
                $popover.popover('hide');
            }
        });
    },

    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {$.Promise}
     */
    _onEditActivity: function (ev) {
        ev.preventDefault();
        var activityID = $(ev.currentTarget).data('activity-id');
        return this._openActivityForm(activityID, this._reload.bind(this, { activity: true, thread: true }));
    },
     /**
     * Called when marking an activity as done
     *
     * It lets the current user write a feedback in a popup menu.
     * After writing the feedback and confirm mark as done
     * is sent, it marks this activity as done for good with the feedback linked
     * to it.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMarkActivityDone: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var self = this;
        var $markDoneBtn = $(ev.currentTarget);
        var activityID = $markDoneBtn.data('activity-id');
        var previousActivityTypeID = $markDoneBtn.data('previous-activity-type-id') || false;
        var forceNextActivity = $markDoneBtn.data('force-next-activity');

        if ($markDoneBtn.data('toggle') == 'collapse') {
            var $actLi = $markDoneBtn.parents('.o_log_activity');
            var $panel = self.$('#o_activity_form_' + activityID);

            if (!$panel.data('bs.collapse')) {
                var $form = $(QWeb.render('mail.activity_feedback_form', { previous_activity_type_id: previousActivityTypeID, force_next: forceNextActivity}));
                $panel.append($form);
                self._onMarkActivityDoneActions($markDoneBtn, $form, activityID);

                // Close and reset any other open panels
                _.each($panel.siblings('.o_activity_form'), function (el) {
                    if ($(el).data('bs.collapse')) {
                        $(el).empty().collapse('dispose').removeClass('show');
                    }
                });

                // Scroll  to selected activity
                $markDoneBtn.parents('.o_activity_log_container').scrollTo($actLi.position().top, 100);
            }

            // Empty and reset panel on close
            $panel.on('hidden.bs.collapse', function () {
                if ($panel.data('bs.collapse')) {
                    $actLi.removeClass('o_activity_selected');
                    $panel.collapse('dispose');
                    $panel.empty();
                }
            });

            this.$('.o_activity_selected').removeClass('o_activity_selected');
            $actLi.toggleClass('o_activity_selected');
            $panel.collapse('toggle');

        } else if (!$markDoneBtn.data('bs.popover')) {
            $markDoneBtn.popover({
                template: $(Popover.Default.template).addClass('o_mail_activity_feedback')[0].outerHTML, // Ugly but cannot find another way
                container: $markDoneBtn,
                title : _t("Feedback"),
                html: true,
                trigger:'click',
                placement: 'right', // FIXME: this should work, maybe a bug in the popper lib
                content : function () {
                    var $popover = $(QWeb.render('mail.activity_feedback_form', { previous_activity_type_id: previousActivityTypeID, force_next: forceNextActivity}));
                    self._onMarkActivityDoneActions($markDoneBtn, $popover, activityID);
                    return $popover;
                },
            }).on('shown.bs.popover', function () {
                var $popover = $($(this).data("bs.popover").tip);
                $(".o_mail_activity_feedback.popover").not($popover).popover("hide");
                $popover.addClass('o_mail_activity_feedback').attr('tabindex', 0);
                $popover.find('#activity_feedback').focus();
                self._bindPopoverFocusout($(this));
            }).popover('show');
        }
    },
    /**
    * Bind all necessary actions to the 'mark as done' form
    *
    * @private
    * @param {Object} $form
    * @param {integer} activityID
    */
    _onMarkActivityDoneActions: function ($btn, $form, activityID) {
        var self = this;
        $form.find('#activity_feedback').val(self._draftFeedback[activityID]);
        $form.on('click', '.o_activity_popover_done', function (ev) {
            ev.stopPropagation();
            self._markActivityDone({
                activityID: activityID,
                feedback: _.escape($form.find('#activity_feedback').val()),
            });
        });
        $form.on('click', '.o_activity_popover_done_next', function (ev) {
            ev.stopPropagation();
            self._markActivityDoneAndScheduleNext({
                activityID: activityID,
                feedback: _.escape($form.find('#activity_feedback').val()),
            });
        });
        $form.on('click', '.o_activity_popover_discard', function (ev) {
            ev.stopPropagation();
            if ($btn.data('bs.popover')) {
                $btn.popover('hide');
            } else if ($btn.data('toggle') == 'collapse') {
                self.$('#o_activity_form_' + activityID).collapse('hide');
            }
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {$.Deferred}
     */
    _onPreviewMailTemplate: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var self = this;
        var templateID = $(ev.currentTarget).data('template-id');
        var action = {
            name: _t('Compose Email'),
            type: 'ir.actions.act_window',
            res_model: 'mail.compose.message',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_res_id: this.res_id,
                default_model: this.model,
                default_use_template: true,
                default_template_id: templateID,
                force_email: true,
            },
        };
        return this.do_action(action, { on_close: function () {
            self.trigger_up('reload');
        } });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {$.Promise}
     */
    _onSendMailTemplate: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var templateID = $(ev.currentTarget).data('template-id');
        return this._rpc({
                model: this.model,
                method: 'activity_send_mail',
                args: [[this.res_id], templateID],
            })
            .then(this._reload.bind(this, {activity: true, thread: true, followers: true}));
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {$.Deferred}
     */
    _onScheduleActivity: function (ev) {
        ev.preventDefault();
        return this._openActivityForm(false, this._reload.bind(this));
    },

    /**
     * @private
     * @param {MouseEvent} ev
     * @param {Object} options
     * @returns {$.Promise}
     */
    _onUnlinkActivity: function (ev, options) {
        ev.preventDefault();
        var activityID = $(ev.currentTarget).data('activity-id');
        options = _.defaults(options || {}, {
            model: 'mail.activity',
            args: [[activityID]],
        });
        return this._rpc({
                model: options.model,
                method: 'unlink',
                args: options.args,
            })
            .then(this._reload.bind(this, {activity: true}));
    },
});

// -----------------------------------------------------------------------------
// Activities Widget for Form views ('mail_activity' widget)
// -----------------------------------------------------------------------------
var Activity = BasicActivity.extend({
    className: 'o_mail_activity',
    events:_.extend({}, BasicActivity.prototype.events, {
        'click a': '_onClickRedirect',
    }),
    specialData: '_fetchSpecialActivity',
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._activities = this.record.specialData[this.name];
    },

    //------------------------------------------------------------
    // Private
    //------------------------------------------------------------

    /**
     * @private
     * @param {Object} fieldsToReload
     */
    _reload: function (fieldsToReload) {
        this.trigger_up('reload_mail_fields', fieldsToReload);
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        _.each(this._activities, function (activity) {
            var note = mailUtils.parseAndTransform(activity.note || '', mailUtils.inline);
            var is_blank = (/^\s*$/).test(note);
            if (!is_blank) {
                activity.note = mailUtils.parseAndTransform(activity.note, mailUtils.addLink);
            } else {
                activity.note = '';
            }
        });
        var activities = setDelayLabel(this._activities);
        if (activities.length) {
            var nbActivities = _.countBy(activities, 'state');
            this.$el.html(QWeb.render('mail.activity_items', {
                activities: activities,
                nbPlannedActivities: nbActivities.planned,
                nbTodayActivities: nbActivities.today,
                nbOverdueActivities: nbActivities.overdue,
                dateFormat: time.getLangDateFormat(),
                datetimeFormat: time.getLangDatetimeFormat(),
            }));
        } else {
            this.$el.empty();
        }
    },
    /**
     * @override
     * @private
     * @param {Object} record
     */
    _reset: function (record) {
        this._super.apply(this, arguments);
        this._activities = this.record.specialData[this.name];
        // the mail widgets being persistent, one need to update the res_id on reset
        this.res_id = record.res_id;
    },

    //------------------------------------------------------------
    // Handlers
    //------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRedirect: function (ev) {
        var id = $(ev.currentTarget).data('oe-id');
        if (id) {
            ev.preventDefault();
            var model = $(ev.currentTarget).data('oe-model');
            this.trigger_up('redirect', {
                res_id: id,
                res_model: model,
            });
        }
    },

});

// -----------------------------------------------------------------------------
// Activities Widget for Kanban views ('kanban_activity' widget)
// -----------------------------------------------------------------------------
var KanbanActivity = BasicActivity.extend({
    className: 'o_mail_activity_kanban',
    template: 'mail.KanbanActivity',
    events:_.extend({}, BasicActivity.prototype.events, {
        'show.bs.dropdown': '_onDropdownShow',
    }),

    /**
     * @override
     */
    init: function (parent, name, record) {
        this._super.apply(this, arguments);
        var selection = {};
        _.each(record.fields.activity_state.selection, function (value) {
            selection[value[0]] = value[1];
        });
        this.selection = selection;
        this._setState(record);
    },

    //------------------------------------------------------------
    // Private
    //------------------------------------------------------------

    /**
     * @private
     */
    _reload: function () {
        this.trigger_up('reload', { db_id: this.record_id });
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        var $span = this.$('.o_activity_btn > span');
        $span.removeClass(function (index, classNames) {
            return classNames.split(/\s+/).filter(function (className) {
                return _.str.startsWith(className, 'o_activity_color_');
            }).join(' ');
        });
        $span.addClass('o_activity_color_' + (this.activityState || 'default'));
        if (this.$el.hasClass('show')) {
            // note: this part of the rendering might be asynchronous
            this._renderDropdown();
        }
    },
    /**
     * @private
     */
    _renderDropdown: function () {
        var self = this;
        this.$('.o_activity').html(QWeb.render('mail.KanbanActivityLoading'));
        return _readActivities(this, this.value.res_ids).then(function (activities) {
            self.$('.o_activity').html(QWeb.render('mail.KanbanActivityDropdown', {
                selection: self.selection,
                records: _.groupBy(setDelayLabel(activities), 'state'),
                uid: self.getSession().uid,
            }));
        });
    },
    /**
     * @override
     * @private
     * @param {Object} record
     */
    _reset: function (record) {
        this._super.apply(this, arguments);
        this._setState(record);
    },
    /**
     * @private
     * @param {Object} record
     */
    _setState: function (record) {
        this.record_id = record.id;
        this.activityState = this.recordData.activity_state;
    },

    //------------------------------------------------------------
    // Handlers
    //------------------------------------------------------------

    /**
     * @private
     */
    _onDropdownShow: function () {
        this._renderDropdown();
    },
});

field_registry
    .add('mail_activity', Activity)
    .add('kanban_activity', KanbanActivity);

return Activity;

});
