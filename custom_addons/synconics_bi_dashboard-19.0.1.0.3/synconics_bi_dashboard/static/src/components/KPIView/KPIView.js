/** @odoo-module **/

import { Component, onMounted, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { KpiLayoutOne } from "../KPILayouts/KpiLayoutOne/KpiLayoutOne";
import { KpiLayoutTwo } from "../KPILayouts/KpiLayoutTwo/KpiLayoutTwo";
import { KpiLayoutThree } from "../KPILayouts/KpiLayoutThree/KpiLayoutThree";
import { KpiLayoutFour } from "../KPILayouts/KpiLayoutFour/KpiLayoutFour";
import { KpiLayoutFive } from "../KPILayouts/KpiLayoutFive/KpiLayoutFive";

export class KPIView extends Component {
  static template = "synconics_bi_dashboard.KPIView";
  static components = {
    KpiLayoutOne,
    KpiLayoutTwo,
    KpiLayoutThree,
    KpiLayoutFour,
    KpiLayoutFive,
  };
  static props = {
    chartId: String,
    name: String,
    isDirty: { optional: true, type: Boolean },
    data: { optional: true, type: Object },
    update_chart: { optional: true, type: Function },
    theme: String,
    recordSets: Object,
  };

  setup() {
    this.state = useState({
      layout_type: "layout1",
      data: {},
      isError: false,
      errorMessage: false,
      title: "KPI",
    });
    useEffect(
      () => {
        this.render_tile_view();
      },
      () => [
        this.props.chartId,
        this.props.recordSets,
        this.props.isDirty,
        this.props.name,
        this.props.data,
      ],
    );

    onMounted(() => {
      this.render_tile_view();
    });
  }

  render_tile_view() {
    let data = this.props.recordSets;
    this.state.name = data.name;
    if (typeof data == "object" && data.type) {
      this.state.isError = true;
      this.state.errorMessage = data.message;
      if (data && data.name) {
        this.state.title = data.name;
      }
      return;
    }
    if (Array.isArray(data)) {
      return;
    }

    this.state.isError = false;
    this.state.layout_type = data.layout_type;
    this.state.name = data.name;
    this.state.data = data;
    this.render();
  }
}
