/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

import { Component } from "@odoo/owl";

export default class ToursDialog extends Component {
    setup() {
        this.title = _t("Tours");
        this.tourService = useService("tour_service");
        this.onboardingTours = this.tourService.getSortedTours().filter(tour => !tour.test);
        this.testingTours = this.tourService.getSortedTours().filter(tour => tour.test);
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
        this.tourService.startTour(ev.target.dataset.name, { mode: 'manual' });
        this.props.close();
    }
    /**
     * Starts the given tour in test mode.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onTestTour(ev) {
        this.tourService.startTour(ev.target.dataset.name, { mode: 'auto', stepDelay: 500, showPointerDuration: 250 });
        this.props.close();
    }
}
ToursDialog.template = "web_tour.ToursDialog";
ToursDialog.components = { Dialog };
