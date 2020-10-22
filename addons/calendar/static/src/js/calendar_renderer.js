odoo.define('calendar.CalendarRenderer', function (require) {
    "use strict";

    const { CalendarPopover } = require('web.CalendarPopover');
    const CalendarRenderer = require('web.CalendarRenderer');

    const STATUS_COLOR = {
        accepted: 'text-success',
        declined: 'text-danger',
        tentative: 'text-muted',
        needsAction: 'text-dark',
    };

    class AttendeeCalendarPopover extends CalendarPopover {
        /**
         * @constructor
         */
        constructor() {
            super(...arguments);
            this.status = this.props.record.attendee_status;
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        /**
         * @returns {Object}
         */
        get allStatus() {
            return this.props.fields.attendee_status.selection
                .filter(s => s[0] !== 'needsAction');
        }
        /**
         * @returns {boolean}
         */
        get displayEventDetails() {
            return this._isEventPrivate ?
                this.isCurrentPartnerAttendee :
                super.displayEventDetails;
        }
        /**
         * @return {boolean}
         */
        get isCurrentPartnerAttendee() {
            return this.props.record.partner_ids.includes(this.env.session.partner_id);
        }
        /**
         * @returns {boolean}
         */
        get isEventDeletable() {
            return super.isEventDeletable && (
                this._isEventPrivate ? this.isCurrentPartnerAttendee : true 
            );
        }
        /**
         * @returns {boolean}
         */
        get isEventEditable() {
            return this._isEventPrivate ?
                this.isCurrentPartnerAttendee :
                super.isEventEditable;
        }
        /**
         * @returns {Object}
         */
        get statusInfo() {
            return this.getStatusInfo(this.status);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {string} status
         * @returns {Object}
         */
        getStatusInfo(status) {
            return {
                color: this.getStatusColor(status),
                label: Object.fromEntries(this.allStatus)[status],
            };
        }
        /**
         * @param {string} status
         * @returns {string}
         */
        getStatusColor(status) {
            return STATUS_COLOR[status];
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @return {boolean}
         */
        get _isEventPrivate() {
            return this.props.record.privacy === 'private';
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {string} status
         */
        _onClickAttendeeStatus(status) {
            this.status = status;
            this.trigger('attendee-status-changed', {
                eventId: this.props.eventId,
                status,
            });
        }
    }
    AttendeeCalendarPopover.template = 'calendar.CalendarPopover';

    class AttendeeCalendarRenderer extends CalendarRenderer {
    }
    AttendeeCalendarRenderer.components = {
        ...CalendarRenderer.components,
        CalendarPopover: AttendeeCalendarPopover,
    };

    return AttendeeCalendarRenderer;
});
