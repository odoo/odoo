/** @odoo-module */

import {
  SelectionField,
  selectionField,
} from "@web/views/fields/selection/selection_field";
import { registry } from "@web/core/registry";

export class DashboardSelectionField extends SelectionField {
  static template = "synconics_bi_dashboard.DashboardSelectionField";
  static props = {
    ...SelectionField.props,
  };

  setup() {
    super.setup();
  }

  /**
   * @param {Event} ev
   */
  onClickDashboard(ev, selected) {
    const value = JSON.parse(selected);
    this.props.record.update(
      { [this.props.name]: value },
      { save: this.props.autosave },
    );
  }
}

export const dashboardSelectionField = {
  ...selectionField,
  component: DashboardSelectionField,
};

registry.category("fields").add("dashboard_selection", dashboardSelectionField);
