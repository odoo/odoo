/** @odoo-module **/

import AbstractField from 'web.AbstractField';
import config from 'web.config';
import core from 'web.core';
import field_registry from 'web.field_registry';
import session from 'web.session';
import { sprintf } from '@web/core/utils/strings';
import framework from 'web.framework';
import time from 'web.time';

const QWeb = core.qweb;
const _t = core._t;
const _lt = core._lt;

// -----------------------------------------------------------------------------
// Activities Widget for Kanban views ('kanban_activity' widget)
// -----------------------------------------------------------------------------
const KanbanActivity = AbstractField.extend({
    template: 'mail.KanbanActivity',
    events: {
        'change input.o_input_file': '_onFileChanged',
        'click .o_activity_template_preview': '_onPreviewMailTemplate',
        'click .o_activity_template_send': '_onSendMailTemplate',
        'click .o_edit_activity': '_onEditActivity',
        'click .o_mark_as_done': '_onMarkActivityDone',
        'click .o_mark_as_done_upload_file': '_onMarkActivityDoneUploadFile',
        'click .o_schedule_activity': '_onScheduleActivity',
        'show.bs.dropdown': '_onDropdownShow',
    },
    fieldDependencies: {
        activity_exception_decoration: { type: 'selection' },
        activity_exception_icon: { type: 'char' },
        activity_state: { type: 'selection' },
    },

    /**
     * @override
     */
    init(parent, name, record) {
        this._super.apply(this, arguments);
        this._draftFeedback = {};
        this.selection = {};
        for (const [key, value] of record.fields.activity_state.selection) {
            this.selection[key] = value;
        }
    },

    /**
     * @param {integer} previousActivityTypeID
     * @return {Promise}
     */
    scheduleActivity() {
        const callback = this._reload.bind(this, { activity: true, thread: true });
        return this._openActivityForm(false, callback);
    },

    //------------------------------------------------------------
    // Private
    //------------------------------------------------------------

    _getActivityFormAction(id) {
        return {
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
    },
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
    async _markActivityDone(params) {
        const activityID = params.activityID;
        const feedback = params.feedback || false;
        const attachmentIds = params.attachmentIds || [];
        await this._rpc({
            model: 'mail.activity',
            method: 'action_feedback',
            args: [[activityID]],
            kwargs: {
                feedback: feedback,
                attachment_ids: attachmentIds || [],
            },
            context: this.record.getContext(),
        });
        this._reload({ activity: true, thread: true });
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
    async _markActivityDoneAndScheduleNext(params) {
        const activityID = params.activityID;
        const feedback = params.feedback;
        const action = await this._rpc({
            model: 'mail.activity',
            method: 'action_feedback_schedule_next',
            args: [[activityID]],
            kwargs: { feedback: feedback },
            context: this.record.getContext(),
        });
        if (action) {
            this.do_action(action, {
                on_close: () => {
                    this.trigger_up('reload', { keepChanges: true });
                },
            });
        } else {
            this.trigger_up('reload', { keepChanges: true });
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {Promise}
     */
    _onEditActivity(ev) {
        ev.preventDefault();
        const activityID = $(ev.currentTarget).data('activity-id');
        return this._openActivityForm(activityID, this._reload.bind(this, { activity: true, thread: true }));
    },
    /**
     * @private
     * @param {FormEvent} ev
     */
    _onFileChanged(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const $form = $(ev.currentTarget).closest('form');
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
    _onMarkActivityDone(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const self = this;
        const $markDoneBtn = $(ev.currentTarget);
        const activityID = $markDoneBtn.data('activity-id');
        const previousActivityTypeID = $markDoneBtn.data('previous-activity-type-id') || false;
        const chainingTypeActivity = $markDoneBtn.data('chaining-type-activity');

        if ($markDoneBtn[0].dataset.bsToggle === 'collapse') {
            const $actLi = $markDoneBtn.parents('.o_log_activity');
            const $panel = this.$('#o_activity_form_' + activityID);

            if (!$panel.data('bs.collapse')) {
                const $form = $(QWeb.render('mail.activity_feedback_form', {
                    previous_activity_type_id: previousActivityTypeID,
                    chaining_type: chainingTypeActivity
                }));
                $panel.append($form);
                this._onMarkActivityDoneActions($markDoneBtn, $form, activityID);

                // Close and reset any other open panels
                _.each($panel.siblings('.o_activity_form'), function (el) {
                    if ($(el).data('bs.collapse')) {
                        $(el).empty().collapse('dispose').removeClass('show');
                    }
                    $(el).data('bs.collapse', false);
                });

                // Scroll  to selected activity
                $markDoneBtn.parents('.o_activity_log_container').scrollTo($actLi.position().top, 100);
                $panel.data('bs.collapse', true);
            }

            // Empty and reset panel on close
            $panel.on('hidden.bs.collapse', function () {
                if ($panel.data('bs.collapse')) {
                    $actLi.removeClass('o_activity_selected');
                    $panel.collapse('dispose');
                    $panel.empty();
                }
                $panel.data('bs.collapse', false);
            });

            this.$('.o_activity_selected').removeClass('o_activity_selected');
            $actLi.toggleClass('o_activity_selected');
            $panel.collapse('toggle');
            $panel.find('#activity_feedback').focus();

        } else if (!$markDoneBtn.data('bs.popover')) {
            $markDoneBtn.popover({
                template: $(Popover.Default.template).addClass('o_mail_activity_feedback')[0].outerHTML, // Ugly but cannot find another way
                container: $markDoneBtn,
                title: _t("Feedback"),
                html: true,
                trigger: 'manual',
                placement: 'right', // FIXME: this should work, maybe a bug in the popper lib
                content: () => {
                    const $popover = $(QWeb.render('mail.activity_feedback_form', {
                        previous_activity_type_id: previousActivityTypeID,
                        chaining_type: chainingTypeActivity
                    }));
                    this._onMarkActivityDoneActions($markDoneBtn, $popover, activityID);
                    return $popover;
                },
            }).on('shown.bs.popover', function () {
                const $popover = $($(this).data("bs.popover").tip);
                $(".o_mail_activity_feedback.popover").not($popover).popover("hide");
                $popover.addClass('o_mail_activity_feedback').attr('tabindex', 0);
                $popover.find('#activity_feedback').focus();
                const activityID = $(this).data('activity-id');
                $popover.off('focusout');
                $popover.focusout(e => {
                    // outside click of popover hide the popover
                    // e.relatedTarget is the element receiving the focus
                    if (!$popover.is(e.relatedTarget) && !$popover.find(e.relatedTarget).length) {
                        self._draftFeedback[activityID] = $popover.find('#activity_feedback').val();
                        $popover.popover('hide');
                    }
                });
            }).popover('show');
        } else {
            const popover = $markDoneBtn.data('bs.popover');
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
    _onMarkActivityDoneActions($btn, $form, activityID) {
        $form.find('#activity_feedback').val(this._draftFeedback[activityID]);
        $form.on('keydown', '#activity_feedback', ev => {
            if (ev.key === 'Enter') {
                ev.stopPropagation(); // Prevent list view actions
            }
        });
        $form.on('click', '.o_activity_popover_done', ev => {
            ev.stopPropagation();
            this._markActivityDone({
                activityID: activityID,
                feedback: $form.find('#activity_feedback').val(),
            });
        });
        $form.on('keydown', '.o_activity_popover_done', ev => {
            if (ev.key === 'Enter') {
                ev.stopPropagation(); // Prevent list view actions
                ev.preventDefault();
                this._markActivityDone({
                    activityID,
                    feedback: $form.find('#activity_feedback').val(),
                });
            }
        });
        $form.on('click', '.o_activity_popover_done_next', ev => {
            ev.stopPropagation();
            this._markActivityDoneAndScheduleNext({
                activityID: activityID,
                feedback: $form.find('#activity_feedback').val(),
            });
        });
        $form.on('keydown', '.o_activity_popover_done_next', ev => {
            if (ev.key === 'Enter') {
                ev.stopPropagation(); // Prevent list view actions
                ev.preventDefault();
                this._markActivityDoneAndScheduleNext({
                    activityID,
                    feedback: $form.find('#activity_feedback').val(),
                });
            }
        });
        $form.on('click', '.o_activity_popover_discard', ev => {
            ev.stopPropagation();
            if ($btn.data('bs.popover')) {
                $btn.popover('hide');
            } else if ($btn[0].dataset.bsToggle === 'collapse') {
                this.$('#o_activity_form_' + activityID).collapse('hide');
            }
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMarkActivityDoneUploadFile(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const fileuploadID = $(ev.currentTarget).data('fileupload-id');
        const $input = this.$("[target='" + fileuploadID + "'] > input.o_input_file");
        $input.click();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {Promise}
     */
    _onPreviewMailTemplate(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const templateID = $(ev.currentTarget).data('template-id');
        const action = {
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
        return this.do_action(action, {
            on_close: () => {
                this.trigger_up('reload', { keepChanges: true });
            },
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {Promise}
     */
    _onScheduleActivity(ev) {
        ev.preventDefault();
        return this._openActivityForm(false, this._reload.bind(this));
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {Promise}
     */
    async _onSendMailTemplate(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const templateID = $(ev.currentTarget).data('template-id');
        await this._rpc({
            model: this.model,
            method: 'activity_send_mail',
            args: [[this.res_id], templateID],
        });
        this._reload({ activity: true, thread: true, followers: true });
    },
    /**
     * @private
     * @param {integer} id
     * @param {function} callback
     * @return {Promise}
     */
    _openActivityForm(id, callback) {
        const action = this._getActivityFormAction(id);
        return this.do_action(action, { on_close: callback });
    },
    /**
     * @private
     */
    _reload() {
        this.trigger_up('reload', { db_id: this.record.id, keepChanges: true });
    },
    /**
     * @override
     * @private
     */
    _render() {
        // span classes need to be updated manually because the template cannot
        // be re-rendered eaasily (because of the dropdown state)
        const spanClasses = ['fa', 'fa-lg', 'fa-fw'];
        spanClasses.push('o_activity_color_' + (this.record.data.activity_state || 'default'));
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
    async _renderDropdown() {
        this.$('.o_activity')
            .toggleClass('dropdown-menu-end', config.device.isMobile)
            .html(QWeb.render('mail.KanbanActivityLoading'));
        let context = this.getSession().user_context;
        if (this.record && !_.isEmpty(this.record.getContext())) {
            context = this.record.getContext();
        }
        const activities = this.value.res_ids.length ? await this._rpc({
            model: 'mail.activity',
            method: 'activity_format',
            args: [this.value.res_ids],
            context: context,
        }) : [];
        const today = moment().startOf('day');
        for (const activity of activities) {
            activity.create_date = moment(time.auto_str_to_date(activity.create_date));
            activity.date_deadline = moment(time.auto_str_to_date(activity.date_deadline));
            if (activity.activity_category === 'upload_file') {
                activity.fileuploadID = _.uniqueId('o_fileupload');
            }
            let toDisplay = '';
            const diff = activity.date_deadline.diff(today, 'days', true); // true means no rounding
            if (diff === 0) {
                toDisplay = _t("Today");
            } else {
                if (diff < 0) { // overdue
                    if (diff === -1) {
                        toDisplay = _t("Yesterday");
                    } else {
                        toDisplay = sprintf(_t("%s days overdue"), Math.round(Math.abs(diff)));
                    }
                } else { // due
                    if (diff === 1) {
                        toDisplay = _t("Tomorrow");
                    } else {
                        toDisplay = sprintf(_t("Due in %s days"), Math.round(Math.abs(diff)));
                    }
                }
            }
            activity.label_delay = toDisplay;
        }
        const sortedActivities = _.sortBy(activities, 'date_deadline');
        this.$('.o_activity').html(QWeb.render('mail.KanbanActivityDropdown', {
            records: _.groupBy(sortedActivities, 'state'),
            session: session,
            widget: this,
        }));
        for (const activity of sortedActivities) {
            if (activity.fileuploadID) {
                $(window).on(activity.fileuploadID, async () => {
                    framework.unblockUI();
                    // find the button clicked and display the feedback popup on it
                    const files = Array.prototype.slice.call(arguments, 1);
                    await this._markActivityDone({
                        activityID: activity.id,
                        attachmentIds: _.pluck(files, 'id')
                    });
                    this.trigger_up('reload', { keepChanges: true });
                });
            }
        }
    },

    //------------------------------------------------------------
    // Handlers
    //------------------------------------------------------------

    /**
     * @private
     */
    _onDropdownShow() {
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
        activity_summary: { type: 'char' },
        activity_type_id: { type: 'many2one', relation: 'mail.activity.type' },
        activity_type_icon: { type: 'char' },
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
    _onDropdownClicked(ev) {
        ev.stopPropagation();
    },
});

// -----------------------------------------------------------------------------
// Activity Exception Widget to display Exception icon ('activity_exception' widget)
// -----------------------------------------------------------------------------

const ActivityException = AbstractField.extend({
    noLabel: true,
    fieldDependencies: _.extend({}, AbstractField.prototype.fieldDependencies, {
        activity_exception_icon: { type: 'char' },
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
    _renderEdit() {
        return this._renderReadonly();
    },

    /**
     * Displays the exception icon if there is one.
     *
     * @override
     * @private
     */
    _renderReadonly() {
        this.$el.empty();
        if (this.value) {
            this.$el.attr({
                title: _t('This record has an exception activity.'),
                class: "float-end mt-1 text-" + this.value + " fa " + this.recordData.activity_exception_icon
            });
        }
    }
});

field_registry
    .add('kanban_activity', KanbanActivity)
    .add('list_activity', ListActivity)
    .add('activity_exception', ActivityException);
