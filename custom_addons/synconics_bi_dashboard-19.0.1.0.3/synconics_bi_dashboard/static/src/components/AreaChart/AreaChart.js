/** @odoo-module **/

import { Component, onMounted, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AreaChart extends Component {
  static template = "synconics_bi_dashboard.AreaChart";
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
        this.render_area_chart();
      },
      () => [this.props.chartId, this.props.recordSets, this.props.data],
    );
    onMounted(() => {
      this.render_area_chart();
    });
  }

  render_area_chart() {
    let data = this.props.recordSets;
    var self = this;
    if (this.root) {
      this.root.dispose();
    }
    if (typeof data == "object" && !Array.isArray(data)) {
      this.state.isError = true;
      this.state.errorMessage = data.message;
      return;
    }

    this.state.isError = false;
    this.state.errorMessage = false;
    this.root = am5.Root.new("area_chart__" + this.props.chartId);
    const theme = this.themeMap[this.props.theme];
    this.root.setThemes([theme.new(this.root)]);
    const formatLabel = (text, maxLength = 15) => {
      if (!text) return text;
      if (typeof text !== "string") return text;
      if (text.length <= maxLength) return text;
      return (
        text
          .replace(/\[/g, "(")
          .replace(/\]/g, ")")
          .substring(0, maxLength - 3) + "..."
      );
    };

    // Apply formatting to your data
    data = data.map((item) => ({
      ...item,
      category: formatLabel(item.category), // Assuming 'category' is your label field
    }));
    var chart = this.root.container.children.push(
      am5radar.RadarChart.new(this.root, {
        panX: false,
        panY: false,
        wheelX: "panX",
        wheelY: "zoomX",
      }),
    );

    var cursor = chart.set(
      "cursor",
      am5radar.RadarCursor.new(this.root, {
        behavior: "zoomX",
      }),
    );

    cursor.lineY.set("visible", false);

    var xRenderer = am5radar.AxisRendererCircular.new(this.root, {});
    xRenderer.labels.template.setAll({
      radius: 10,
      centerX: am5.p50,
      centerY: am5.p50,
      textType: "adjusted",
      oversizedBehavior: "wrap",
      maxWidth: 100,
    });

    var xAxis = chart.xAxes.push(
      am5xy.CategoryAxis.new(this.root, {
        maxDeviation: 0,
        categoryField: "category",
        renderer: xRenderer,
        tooltip: am5.Tooltip.new(this.root, {}),
      }),
    );

    var yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(this.root, {
        renderer: am5radar.AxisRendererRadial.new(this.root, {}),
      }),
    );

    let keys = Object.keys(data[0]).filter(
      (k) => k !== "category" && k !== "record_id" && k !== "isSubGroupBy",
    );

    for (let key of keys) {
      let series = chart.series.push(
        am5radar.RadarColumnSeries.new(this.root, {
          name: key,
          xAxis: xAxis,
          yAxis: yAxis,
          valueYField: key,
          categoryXField: "category",
          tooltip: am5.Tooltip.new(this.root, {
            labelText: "{name}\n{categoryX}: {valueY}",
          }),
        }),
      );
      series.columns.template.events.on("click", function (ev) {
        if (self.props.update_chart) {
          self.props.update_chart(
            parseInt(self.props.chartId),
            "area_chart",
            ev.target.dataItem.dataContext,
          );
        }
      });

      series.data.setAll(data);
      series.appear(1000);
    }

    xAxis.data.setAll(data);

    var legend = chart.bottomAxesContainer.children.push(
      am5.Legend.new(this.root, {
        centerX: am5.p50,
        x: am5.p50,
        marginTop: 50,
      }),
    );

    legend.data.setAll(chart.series.values);

    chart.appear(1000, 100);
    let exporting = am5plugins_exporting.Exporting.new(this.root, {
      filePrefix: "my_chart",
      dataSource: chart.series.getIndex(0), // optional
    });
    this.root.events.once("frameended", () => {
      if (this.props.export) {
        this.props.export(exporting);
      }
    });
  }
}
