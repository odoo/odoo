/** @odoo-module **/

import { Component, onMounted, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MeterChart extends Component {
  static template = "synconics_bi_dashboard.MeterChart";
  static props = {
    chartId: String,
    name: String,
    isDirty: { optional: true, type: Boolean },
    data: { optional: true, type: Object },
    update_chart: { optional: true, type: Function },
    theme: String,
    recordSets: Object,
    export: { optional: true, type: Function },
  };

  setup() {
    this.orm = useService("orm");
    this.root = null;
    this.themeMap = {
      animated: am5themes_Animated,
      frozen: am5themes_Frozen,
      kelly: am5themes_Kelly,
      material: am5themes_Material,
      moonrise: am5themes_Moonrise,
      spirited: am5themes_Spirited,
    };
    this.state = useState({ isError: false, errorMessage: false });
    useEffect(
      () => {
        this.render_meter_chart();
      },
      () => [this.props.chartId, this.props.recordSets, this.props.data],
    );
    onMounted(() => {
      this.render_meter_chart();
    });
  }

  render_meter_chart() {
    let data = this.props.recordSets;
    if (
      typeof data == "object" &&
      !Array.isArray(data) &&
      data.type == "error"
    ) {
      this.state.isError = true;
      this.state.errorMessage = data.message;
      return;
    }

    this.state.isError = false;
    this.state.errorMessage = false;
    if (this.root) {
      this.root.dispose();
    }
    this.root = am5.Root.new("meter_chart__" + this.props.chartId);

    this.root.setThemes([am5themes_Animated.new(this.root)]);

    var chart = this.root.container.children.push(
      am5radar.RadarChart.new(this.root, {
        panX: false,
        panY: false,
        startAngle: 180,
        endAngle: 360,
      }),
    );

    var axisRenderer = am5radar.AxisRendererCircular.new(this.root, {
      innerRadius: 0, // Change from -10 to 0
      strokeOpacity: 1,
      strokeWidth: 15,
      strokeGradient: am5.LinearGradient.new(this.root, {
        rotation: 0,
        stops: [
          { color: am5.color(0xfb7116) },
          { color: am5.color(0xf6d32b) },
          { color: am5.color(0xf4fb16) },
          { color: am5.color(0x19d228) },
        ],
      }),
    });

    var xAxis = chart.xAxes.push(
      am5xy.ValueAxis.new(this.root, {
        maxDeviation: 0,
        min: 0,
        max: data.target,
        strictMinMax: true,
        renderer: axisRenderer,
      }),
    );
    var axisDataItem = xAxis.makeDataItem({});
    axisDataItem.set("value", 0);

    var bullet = axisDataItem.set(
      "bullet",
      am5xy.AxisBullet.new(this.root, {
        sprite: am5radar.ClockHand.new(this.root, {
          radius: am5.percent(99),
          topWidth: 3,
          bottomWidth: 5,
          fill: am5.color(0x000000),
          pinRadius: 8,
        }),
      }),
    );

    xAxis.createAxisRange(axisDataItem);

    var label = chart.radarContainer.children.push(
      am5.Label.new(this.root, {
        centerX: am5.percent(50),
        centerY: am5.percent(0),
        textAlign: "center",
        fontSize: "2em",
        fill: am5.color(0x000000),
      }),
    );

    // Update the label when value changes
    axisDataItem.on("value", function () {
      label.set("text", data.current_value);
    });

    axisDataItem.get("grid").set("visible", false);

    axisDataItem.animate({
      key: "value",
      to: data.current_value,
      duration: 800,
      easing: am5.ease.out(am5.ease.cubic),
    });

    chart.appear(1000, 100);
    let exporting = am5plugins_exporting.Exporting.new(this.root, {
      filePrefix: "my_chart",
      dataSource: chart.series.getIndex(0),
    });
    this.root.events.once("frameended", () => {
      if (this.props.export) {
        this.props.export(exporting);
      }
    });
  }
}
