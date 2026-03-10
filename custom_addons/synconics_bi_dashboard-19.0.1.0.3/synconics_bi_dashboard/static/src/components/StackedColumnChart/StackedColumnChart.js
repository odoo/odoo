/** @odoo-module **/

import { Component, onMounted, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class StackedColumnChart extends Component {
  static template = "synconics_bi_dashboard.StackedColumnChart";
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
    this.themeMap = {
      animated: am5themes_Animated,
      frozen: am5themes_Frozen,
      kelly: am5themes_Kelly,
      material: am5themes_Material,
      moonrise: am5themes_Moonrise,
      spirited: am5themes_Spirited,
    };

    this.root = null;
    this.state = useState({ isError: false, errorMessage: false });
    useEffect(
      () => {
        this.render_stacked_column_chart();
      },
      () => [this.props.chartId, this.props.recordSets, this.props.data],
    );
    onMounted(() => {
      this.render_stacked_column_chart();
    });
  }

  async render_stacked_column_chart() {
    var data = this.props.recordSets;
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
    this.root = am5.Root.new("stacked_column_chart__" + this.props.chartId);
    const theme = this.themeMap[this.props.theme];
    this.root.setThemes([theme.new(this.root)]);
    const formatLabel = (text, maxLength = 15) => {
      if (!text) return text;
      if (typeof text !== "string") return text;
      if (text.length <= maxLength) return text;
      return text.substring(0, maxLength - 3) + "...";
    };

    // Apply formatting to your data
    data = data.map((item) => ({
      ...item,
      category: formatLabel(item.category), // Assuming 'category' is your label field
    }));
    var chart = this.root.container.children.push(
      am5xy.XYChart.new(this.root, {
        panX: false,
        panY: false,
        wheelX: "panX",
        wheelY: "zoomX",
        paddingLeft: 0,
        layout: this.root.verticalLayout,
      }),
    );

    chart.set(
      "scrollbarX",
      am5.Scrollbar.new(this.root, {
        orientation: "horizontal",
      }),
    );

    // var xRenderer = am5xy.AxisRendererX.new(this.root, {
    //   minorGridEnabled: true,
    // });
    var xRenderer = am5xy.AxisRendererX.new(this.root, {
      cellStartLocation: 0.1,
      cellEndLocation: 0.9,
      minorGridEnabled: true,
    });

    var xAxis = chart.xAxes.push(
      am5xy.CategoryAxis.new(this.root, {
        categoryField: "category",
        renderer: xRenderer,
        tooltip: am5.Tooltip.new(this.root, {}),
      }),
    );

    xRenderer.labels.template.setAll({
      rotation: -20,
      centerY: am5.p50,
      centerX: am5.p100,
      paddingRight: 15,
    });
    // xRenderer.grid.template.setAll({
    //   location: 1,
    // });

    xAxis.data.setAll(data);

    var yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(this.root, {
        min: 0,
        renderer: am5xy.AxisRendererY.new(this.root, {
          strokeOpacity: 0.1,
        }),
      }),
    );

    var self = this;

    function makeSeries(name, fieldName) {
      var series = chart.series.push(
        am5xy.ColumnSeries.new(self.root, {
          name: name,
          stacked: true,
          xAxis: xAxis,
          yAxis: yAxis,
          valueYField: fieldName,
          categoryXField: "category",
        }),
      );

      series.columns.template.setAll({
        tooltipText: "{name}, {categoryX}: {valueY}",
        tooltipY: am5.percent(10),
      });
      series.data.setAll(data);

      series.appear();

      series.columns.template.events.on("click", function (ev) {
        if (self.props.update_chart) {
          self.props.update_chart(
            parseInt(self.props.chartId),
            "stackedcolumn_chart",
            ev.target.dataItem.dataContext,
          );
        }
      });

      series.bullets.push(function () {
        return am5.Bullet.new(self.root, {
          sprite: am5.Label.new(self.root, {
            text: "{valueY}",
            fill: self.root.interfaceColors.get("alternativeText"),
            centerY: am5.p50,
            centerX: am5.p50,
            populateText: true,
          }),
        });
      });
    }
    let keys = Object.keys(data[0]).filter(
      (k) => k !== "category" && k !== "record_id" && k !== "isSubGroupBy",
    );
    for (var key = 0; key < keys.length; key++) {
      makeSeries(keys[key], keys[key]);
    }
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
