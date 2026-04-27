/** @odoo-module **/

import options from '@web_editor/js/editor/snippets.options';

options.registry.AppointmentTypeOptions = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * Load appointment type data related to website customization.
     *
     * @override
     */
    async willStart() {
        const res = await this._super(...arguments);
        this.appointmentTypeId = Number(this.ownerDocument.querySelector('.o_wappointment_type_options').dataset.appointmentTypeId);

        const appointmentType = (await this.orm.read(
            "appointment.type",
            [this.appointmentTypeId],
            ["allow_guests", "avatars_display", "hide_duration", "hide_timezone"]
        ))[0];

        this.allowGuests = appointmentType.allow_guests;
        this.avatarsDisplay = appointmentType.avatars_display;
        this.hideDuration = appointmentType.hide_duration;
        this.hideTimezone = appointmentType.hide_timezone;
        return res;
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    async toggleAllowGuests(previewMode, widgetValue, params) {
        await this.orm.write("appointment.type", [this.appointmentTypeId], {
            allow_guests: !this.allowGuests,
        });
    },

    async toggleAvatarsDisplay(previewMode, widgetValue, params) {
        await this.orm.write("appointment.type", [this.appointmentTypeId], {
            avatars_display: this.avatarsDisplay === 'show' ? 'hide' : 'show',
        });
    },

    async toggleHideTimezone(previewMode, widgetValue, params) {
        await this.orm.write("appointment.type", [this.appointmentTypeId], {
            hide_timezone: !this.hideTimezone,
        });
    },

    async toggleHideDuration(previewMode, widgetValue, params) {
        await this.orm.write("appointment.type", [this.appointmentTypeId], {
            hide_duration: !this.hideDuration,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'toggleAllowGuests') {
            return this.allowGuests;
        } else if (methodName === 'toggleAvatarsDisplay') {
            return this.avatarsDisplay === 'show';
        } else if (methodName === 'toggleHideTimezone') {
            return !this.hideTimezone;
        } else if (methodName === 'toggleHideDuration') {
            return !this.hideDuration;
        }
        return this._super(...arguments);
    },
});
