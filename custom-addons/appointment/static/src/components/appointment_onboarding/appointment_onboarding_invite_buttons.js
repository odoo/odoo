/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from '@web/core/registry';
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class AppointmentOnboardingInviteButtons extends Component {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService('orm');
        this.actionService = useService('action');
    }
    /**
     *
     * @param ev
     */
    async onSaveAndCopy (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        const { bookUrl } = await this._getInviteURL();
        setTimeout(async () => {
            await browser.navigator.clipboard.writeText(bookUrl);
            this.notification.add(
                _t("Link copied to clipboard!"),
                { type: "success" }
            );
            this.env.dialogData.close();
            // refresh the view below the onboarding panel as we may have created a record
            this.actionService.restore(this.actionService.currentController.jsId);
        });
    }
    /**
     *
     * @param ev
     */
    async onPreview (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        const { bookUrl } = await this._getInviteURL();
        window.location = bookUrl;
    }
    /**
     * Create invite with slug as shortcode both for copying to clipboard and to redirect.
     *
     * @return {Promise<String>} bookUrl
     * @private
     */
    async _getInviteURL () {
        if (!await this.props.record.save()) {
            return Promise.reject();
        }
        return this.orm.call(
            this.props.record.resModel,
            'search_or_create_onboarding_invite',
            [this.props.record.resId]
        );
    }
}
AppointmentOnboardingInviteButtons.props = {
    ...standardWidgetProps,
};
AppointmentOnboardingInviteButtons.template = 'appointment.AppointmentOnboardingInviteButtons';

export const appointmentOnboardingInviteButtons = {
    component: AppointmentOnboardingInviteButtons,
};
registry
    .category("view_widgets")
    .add("appointment_onboarding_invite_buttons", appointmentOnboardingInviteButtons);
