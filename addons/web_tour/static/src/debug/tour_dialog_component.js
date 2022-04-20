/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _lt } from "@web/core/l10n/translation";

const { Component } = owl;

export default class ToursDialog extends Component {
    setup() {
        this.tourService = useService("tour");
        this.onboardingTours = this.tourService.getOnboardingTours();
        this.testingTours = this.tourService.getTestingTours();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Resets the given tour to its initial step, in onboarding mode.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onStartTour(ev) {
        this.tourService.reset(ev.target.dataset.name);
        this.props.close();
    }
    /**
     * Starts the given tour in test mode.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onTestTour(ev) {
        this.tourService.run(ev.target.dataset.name);
        this.props.close();
    }
}
ToursDialog.template = "web_tour.ToursDialog";
ToursDialog.components = { Dialog };
ToursDialog.title = _lt("Tours");
