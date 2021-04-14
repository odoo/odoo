/** @odoo-module **/

import { useService } from "@web/core/hooks";

export default class ToursDialog extends owl.Component {
  setup() {
    this.tourService = useService("tour");
    this.onboardingTours = this.tourService.getOnboardingTours();
    this.testingTours = this.tourService.getTestingTours();
  }

  //--------------------------------------------------------------------------
  // Getters
  //--------------------------------------------------------------------------

  get dialogTitle() {
    return this.env._t("Tours");
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
  }
  /**
   * Starts the given tour in test mode.
   *
   * @private
   * @param {MouseEvent} ev
   */
  _onTestTour(ev) {
    this.tourService.run(ev.target.dataset.name);
  }
}
ToursDialog.template = "web_tour.ToursDialog";
