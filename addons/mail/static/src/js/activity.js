odoo.define('mail.Activity', function (require) {
"use strict";

var mailUtils = require('mail.utils');

var AbstractField = require('web.AbstractField');
var BasicModel = require('web.BasicModel');
var config = require('web.config');
var core = require('web.core');
var field_registry = require('web.field_registry');
var session = require('web.session');
var framework = require('web.framework');
var time = require('web.time');

var QWeb = core.qweb;
var _t = core._t;
const _lt = core._lt;

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
 * @return {Promise<Array>} resolved with the activities
 */
function _readActivities(self, ids) {
    if (!ids.length) {
        return Promise.resolve([]);
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
     * @return {Promise<Array>} resolved with the activities
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
var setDelayLabel = function (activities) {
    var today = moment().startOf('day');
    _.each(activities, function (activity) {
        var toDisplay = '';
        var diff = activity.date_deadline.diff(today, 'days', true); // true means no rounding
        if (diff === 0) {
            toDisplay = _t("Today");
        } else {
            if (diff < 0) { // overdue
                if (diff === -1) {
                    toDisplay = _t("Yesterday");
                } else {
                    toDisplay = _.str.sprintf(_t("%d days overdue"), Math.abs(diff));
                }
            } else { // due
                if (diff === 1) {
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

/**
 * Set the file upload identifier for 'upload_file' type activities
 *
 * @param {Array} activities list of activity Object
 * @return {Array} : list of modified activity Object
 */
var setFileUploadID = function (activities) {
    _.each(activities, function (activity) {
        if (activity.activity_category === 'upload_file') {
            activity.fileuploadID = _.uniqueId('o_fileupload');
        }
    });
    return activities;
};

var BasicActivity = AbstractField.extend({
    events: {
        'click .o_edit_activity': '_onEditActivity',
        'change input.o_input_file': '_onFileChanged',
        'click .o_mark_as_done': '_onMarkActivityDone',
        'click .o_mark_as_done_upload_file': '_onMarkActivityDoneUploadFile',
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
     * @return {Promise}
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
     * @param {integer[]} params.attachmentIds
     * @param {string} params.feedback
     *
     * @return {$.Promise}
     */
    _markActivityDone: function (params) {
        var activityID = params.activityID;
        var feedback = params.feedback || false;
        var attachmentIds = params.attachmentIds || [];

        return this._sendActivityFeedback(activityID, feedback, attachmentIds)
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
     * @param {function} callback
     * @return {Promise}
     */
    _openActivityForm: function (id, callback) {
        var action = {
            type: 'ir.actions.act_window',
            name: _t("Schedule Activity"),
            res_model: 'mail.activity',
            view_mode: 'form',
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
     * @param {integer[]} attachmentIds
     * @return {Promise}
     */
    _sendActivityFeedback: function (activityID, feedback, attachmentIds) {
        return this._rpc({
                model: 'mail.activity',
                method: 'action_feedback',
                args: [[activityID]],
                kwargs: {
                    feedback: feedback,
                    attachment_ids: attachmentIds || [],
                },
                context: this.record.getContext(),
            });
    },

    //------------------------------------------------------------
    // Handlers
    //------------------------------------------------------------

    /**
     * @private
     * @param {Object[]} activities
     */
    _bindOnUploadAction: function (activities) {
        var self = this;
        _.each(activities, function (activity) {
            if (activity.fileuploadID) {
                $(window).on(activity.fileuploadID, function () {
                    framework.unblockUI();
                    // find the button clicked and display the feedback popup on it
                    var files = Array.prototype.slice.call(arguments, 1);
                    self._markActivityDone({
                        activityID: activity.id,
                        attachmentIds: _.pluck(files, 'id')
                    }).then(function () {
                        self.trigger_up('reload');
                    });
                });
            }
        });
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
     * @returns {Promise}
     */
    _onEditActivity: function (ev) {
        ev.preventDefault();
        var activityID = $(ev.currentTarget).data('activity-id');
        return this._openActivityForm(activityID, this._reload.bind(this, { activity: true, thread: true }));
    },
    /**
     * @private
     * @param {FormEvent} ev
     */
    _onFileChanged: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var $form = $(ev.currentTarget).closest('form');
        $form.submit();
        framework.blockUI();
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

        if ($markDoneBtn.data('toggle') === 'collapse') {
            var $actLi = $markDoneBtn.parents('.o_log_activity');
            var $panel = self.$('#o_activity_form_' + activityID);

            if (!$panel.data('bs.collapse')) {
                var $form = $(QWeb.render('mail.activity_feedback_form', {
                    previous_activity_type_id: previousActivityTypeID,
                    force_next: forceNextActivity
                }));
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
                title: _t("Feedback"),
                html: true,
                trigger: 'manual',
                placement: 'right', // FIXME: this should work, maybe a bug in the popper lib
                content: function () {
                    var $popover = $(QWeb.render('mail.activity_feedback_form', {
                        previous_activity_type_id: previousActivityTypeID,
                        force_next: forceNextActivity
                    }));
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
        } else {
            var popover = $markDoneBtn.data('bs.popover');
            if ($('#' + popover.tip.id).length === 0) {
               popover.show();
            }
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
                feedback: $form.find('#activity_feedback').val(),
            });
        });
        $form.on('click', '.o_activity_popover_done_next', function (ev) {
            ev.stopPropagation();
            self._markActivityDoneAndScheduleNext({
                activityID: activityID,
                feedback: $form.find('#activity_feedback').val(),
            });
        });
        $form.on('click', '.o_activity_popover_discard', function (ev) {
            ev.stopPropagation();
            if ($btn.data('bs.popover')) {
                $btn.popover('hide');
            } else if ($btn.data('toggle') === 'collapse') {
                self.$('#o_activity_form_' + activityID).collapse('hide');
            }
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMarkActivityDoneUploadFile: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var fileuploadID = $(ev.currentTarget).data('fileupload-id');
        var $input = this.$("[target='" + fileuploadID + "'] > input.o_input_file");
        $input.click();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {Promise}
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
     * @returns {Promise}
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
     * @returns {Promise}
     */
    _onScheduleActivity: function (ev) {
        ev.preventDefault();
        return this._openActivityForm(false, this._reload.bind(this));
    },

    /**
     * @private
     * @param {MouseEvent} ev
     * @param {Object} options
     * @returns {Promise}
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
    /**
     * Unbind event triggered when a file is uploaded.
     *
     * @private
     * @param {Array} activities: list of activity to unbind
     */
    _unbindOnUploadAction: function (activities) {
        _.each(activities, function (activity) {
            if (activity.fileuploadID) {
                $(window).off(activity.fileuploadID);
            }
        });
    },
});

// -----------------------------------------------------------------------------
// Activities Widget for Form views ('mail_activity' widget)
// -----------------------------------------------------------------------------
// FIXME seems to still be needed in some cases like systray
var Activity = BasicActivity.extend({
    className: 'o_mail_activity',
    events: _.extend({}, BasicActivity.prototype.events, {
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
    /**
     * @override
     */
    destroy: function () {
        this._unbindOnUploadAction();
        return this._super.apply(this, arguments);
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
        var activities = setFileUploadID(setDelayLabel(this._activities));
        if (activities.length) {
            var nbActivities = _.countBy(activities, 'state');
            this.$el.html(QWeb.render('mail.activity_items', {
                uid: session.uid,
                activities: activities,
                nbPlannedActivities: nbActivities.planned,
                nbTodayActivities: nbActivities.today,
                nbOverdueActivities: nbActivities.overdue,
                dateFormat: time.getLangDateFormat(),
                datetimeFormat: time.getLangDatetimeFormat(),
                session: session,
                widget: this,
            }));
            this._bindOnUploadAction(this._activities);
        } else {
            this._unbindOnUploadAction(this._activities);
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
    template: 'mail.KanbanActivity',
    events: _.extend({}, BasicActivity.prototype.events, {
        'show.bs.dropdown': '_onDropdownShow',
    }),
    fieldDependencies: _.extend({}, BasicActivity.prototype.fieldDependencies, {
        activity_exception_decoration: {type: 'selection'},
        activity_exception_icon: {type: 'char'},
        activity_state: {type: 'selection'},
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
    /**
     * @override
     */
    destroy: function () {
        this._unbindOnUploadAction();
        return this._super.apply(this, arguments);
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
        // span classes need to be updated manually because the template cannot
        // be re-rendered eaasily (because of the dropdown state)
        const spanClasses = ['fa', 'fa-lg', 'fa-fw'];
        spanClasses.push('o_activity_color_' + (this.activityState || 'default'));
        if (this.recordData.activity_exception_decoration) {
            spanClasses.push('text-' + this.recordData.activity_exception_decoration);
            spanClasses.push(this.recordData.activity_exception_icon);
        } else {
            spanClasses.push('fa-clock-o');
        }
        this.$('.o_activity_btn > span').removeClass().addClass(spanClasses.join(' '));

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
        this.$('.o_activity')
            .toggleClass('dropdown-menu-right', config.device.isMobile)
            .html(QWeb.render('mail.KanbanActivityLoading'));
        return _readActivities(this, this.value.res_ids).then(function (activities) {
            activities = setFileUploadID(activities);
            self.$('.o_activity').html(QWeb.render('mail.KanbanActivityDropdown', {
                selection: self.selection,
                records: _.groupBy(setDelayLabel(activities), 'state'),
                session: session,
                widget: self,
            }));
            self._bindOnUploadAction(activities);
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

// -----------------------------------------------------------------------------
// Activities Widget for List views ('list_activity' widget)
// -----------------------------------------------------------------------------
const ListActivity = KanbanActivity.extend({
    template: 'mail.ListActivity',
    events: Object.assign({}, KanbanActivity.prototype.events, {
        'click .dropdown-menu.o_activity': '_onDropdownClicked',
    }),
    fieldDependencies: _.extend({}, KanbanActivity.prototype.fieldDependencies, {
        activity_summary: {type: 'char'},
        activity_type_id: {type: 'many2one', relation: 'mail.activity.type'},
        activity_type_icon: {type: 'char'},
    }),
    label: _lt('Next Activity'),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: async function () {
        await this._super(...arguments);
        // set the 'special_click' prop on the activity icon to prevent from
        // opening the record when the user clicks on it (as it opens the
        // activity dropdown instead)
        this.$('.o_activity_btn > span').prop('special_click', true);
        if (this.value.count) {
            let text;
            if (this.recordData.activity_exception_decoration) {
                text = _t('Warning');
            } else {
                text = this.recordData.activity_summary ||
                          this.recordData.activity_type_id.data.display_name;
            }
            this.$('.o_activity_summary').text(text);
        }
        if (this.recordData.activity_type_icon) {
            this.el.querySelector('.o_activity_btn > span').classList.replace('fa-clock-o', this.recordData.activity_type_icon);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * As we are in a list view, we don't want clicks inside the activity
     * dropdown to open the record in a form view.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onDropdownClicked: function (ev) {
        ev.stopPropagation();
    },
});

// -----------------------------------------------------------------------------
// Activity Exception Widget to display Exception icon ('activity_exception' widget)
// -----------------------------------------------------------------------------

var ActivityException = AbstractField.extend({
    noLabel: true,
    fieldDependencies: _.extend({}, AbstractField.prototype.fieldDependencies, {
        activity_exception_icon: {type: 'char'}
    }),

    //------------------------------------------------------------
    // Private
    //------------------------------------------------------------

    /**
     * There is no edit mode for this widget, the icon is always readonly.
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        return this._renderReadonly();
    },

    /**
     * Displays the exception icon if there is one.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.empty();
        if (this.value) {
            this.$el.attr({
                title: _t('This record has an exception activity.'),
                class: "pull-right mt-1 text-" + this.value + " fa " + this.recordData.activity_exception_icon
            });
        }
    }
});

field_registry
    .add('kanban_activity', KanbanActivity)
    .add('list_activity', ListActivity)
    .add('activity_exception', ActivityException);

return Activity;

});
