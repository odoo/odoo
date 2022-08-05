/** @odoo-module alias=calendar.CalendarRenderer **/

import {_t} from 'web.core';
import CalendarRenderer from 'web.CalendarRenderer';
import CalendarPopover from 'web.CalendarPopover';
import session from 'web.session';

const AttendeeCalendarPopover = CalendarPopover.extend({
    template: 'Calendar.attendee.status.popover',
    events: _.extend({}, CalendarPopover.prototype.events, {
        'click .o-calendar-attendee-status .dropdown-item': '_onClickAttendeeStatus'
    }),
    /**
     * @constructor
     */
    init: function () {
        var self = this;
        this._super.apply(this, arguments);
        // Show status dropdown if user is in attendees list
        if (this.isCurrentPartnerAttendee()) {
            this.statusColors = {accepted: 'text-success', declined: 'text-danger', tentative: 'text-muted', needsAction: 'text-dark'};
            this.statusInfo = {};
            _.each(this.fields.attendee_status.selection, function (selection) {
                self.statusInfo[selection[0]] = {text: selection[1], color: self.statusColors[selection[0]]};
            });
            this.selectedStatusInfo = this.statusInfo[this.event.extendedProps.record.attendee_status];
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {boolean}
     */
    isCurrentPartnerOrganizer() {
        return this.event.extendedProps.record.partner_id[0] === session.partner_id;
    },
    /**
     * @return {boolean}
     */
    isCurrentPartnerAttendee() {
        return this.event.extendedProps.record.partner_ids.includes(session.partner_id);
    },
    /**
     * @override
     * @return {boolean}
     */
    isEventDeletable() {
        return this._super() && this.isCurrentPartnerAttendee();
    },
    /**
     * @override
     * @return {boolean}
     */
    isEventDetailsVisible() {
        return this._isEventPrivate() ? this.isCurrentPartnerAttendee() : this._super();
    },
    /**
     * @override
     * @return {boolean}
     */
    isEventEditable() {
        return this._isEventPrivate() ? this.isCurrentPartnerAttendee() : this._super();
    },
    /**
     * Check if we are a partner and if we are the only attendee.
     * This avoid to display attendee answer dropdown for single user attendees
     * @return {boolean}
     */
    displayAttendeeAnswerChoice() {
        const isCurrentpartner = (currentValue) => currentValue === session.partner_id;
        const onlyAttendee =  this.event.extendedProps.record.partner_ids.every(isCurrentpartner);
        return this.isCurrentPartnerAttendee() && this.event.extendedProps.record.is_current_partner && !onlyAttendee;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {boolean}
     */
    _isEventPrivate() {
        return this.event.extendedProps.record.privacy === 'private';
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAttendeeStatus: function (ev) {
        ev.preventDefault();
        const selectedStatus = $(ev.currentTarget).attr('data-action');
        this.trigger_up('AttendeeStatus', {id: parseInt(this.event.id), record: this.event.extendedProps.record,
        selectedStatus: selectedStatus});
    },
});


const AttendeeCalendarRenderer = CalendarRenderer.extend({
    template: 'calendar.CalendarView',

	config: _.extend({}, CalendarRenderer.prototype.config, {
        CalendarPopover: AttendeeCalendarPopover,
        eventTemplate: 'Calendar.calendar-box',
    }),

    events: _.extend({}, CalendarRenderer.prototype.events, {
        'click #google_sync_activate': '_onConfigureExternalCalendarGoogle',
        'click #microsoft_sync_activate': '_onConfigureExternalCalendarMicrosoft',
    }),

    _onConfigureExternalCalendarGoogle: function (e) {
        e.preventDefault();
        this._configureCalendarProviderSync('google');
    },
    _onConfigureExternalCalendarMicrosoft: function (e) {
        e.preventDefault();
        this._configureCalendarProviderSync('microsoft');
    },
    /**
     * Add the attendee-id attribute in order to distinct the events when there are
     * several attendees in the event.
     * @override
     */
    _addEventAttributes: function (element, event) {
        this._super(...arguments);
        element.attr('data-attendee-id', event.extendedProps.attendee_id);
    },
    /**
     * If an attendee_id has been set on the event, we check also the attendee-id attribute
     * to select the good event on which the CSS class will be applied.
     * @override
     */
    _computeEventSelector: function (info) {
        let selector = this._super(...arguments);
        if (info.event.extendedProps.attendee_id) {
            selector += `[data-attendee-id=${info.event.extendedProps.attendee_id}]`;
        }
        return selector;
    },
    _configureCalendarProviderSync: function (ProviderName) {
        this.do_action({
            name: _t('Connect your Calendar'),
            type: 'ir.actions.act_window',
            res_model: 'calendar.provider.config',
            views: [[false, "form"]],
            view_mode: "form",
            target: 'new',
            context: {
                'default_external_calendar_provider': ProviderName,
                'dialog_size': 'medium',
            }
        });
    },
});

export default {
    AttendeeCalendarRenderer: AttendeeCalendarRenderer,
    AttendeeCalendarPopover: AttendeeCalendarPopover,
};
