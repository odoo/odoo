/** @odoo-module **/

import { Component, onMounted, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class RadarChart extends Component {
  static template = "synconics_bi_dashboard.RadarChart";
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
        this.render_radar_chart();
      },
      () => [this.props.chartId, this.props.recordSets, this.props.data],
    );
    onMounted(() => {
      this.render_radar_chart();
    });
  }

  async render_radar_chart() {
    var data = this.props.recordSets;
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
    this.root = am5.Root.new("radar_chart__" + this.props.chartId);
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
        panX: true,
        panY: true,
        wheelX: "none",
        wheelY: "none",
        innerRadius: am5.percent(40),
      }),
    );

    chart.zoomOutButton.set("forceHidden", true);

    var xRenderer = am5radar.AxisRendererCircular.new(this.root, {
      minGridDistance: 30,
    });

    xRenderer.labels.template.setAll({
      radius: 20,
      centerX: am5.p50,
      centerY: am5.p50,
      textType: "adjusted",
      oversizedBehavior: "wrap",
      maxWidth: 100,
    });

    xRenderer.grid.template.set("visible", false);

    var xAxis = chart.xAxes.push(
      am5xy.CategoryAxis.new(this.root, {
        maxDeviation: 0.3,
        categoryField: "category",
        renderer: xRenderer,
      }),
    );

    var yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(this.root, {
        maxDeviation: 0.3,
        min: 0,
        renderer: am5radar.AxisRendererRadial.new(this.root, {}),
      }),
    );

    var series = chart.series.push(
      am5radar.RadarColumnSeries.new(this.root, {
        name: "Series 1",
        xAxis: xAxis,
        yAxis: yAxis,
        valueYField: "value",
        categoryXField: "category",
      }),
    );

    series.columns.template.setAll({
      cornerRadius: 5,
      tooltipText: "{categoryX}: {valueY}",
    });

    series.columns.template.events.on("click", function (ev) {
      if (self.props.update_chart) {
        self.props.update_chart(
          parseInt(self.props.chartId),
          "column_chart",
          ev.target.dataItem.dataContext,
        );
      }
    });

    series.columns.template.adapters.add("fill", function (fill, target) {
      return chart.get("colors").getIndex(series.columns.indexOf(target));
    });

    series.columns.template.adapters.add("stroke", function (stroke, target) {
      return chart.get("colors").getIndex(series.columns.indexOf(target));
    });

    xAxis.data.setAll(data);
    series.data.setAll(data);

    function updateData() {
      am5.array.each(series.dataItems, function (dataItem) {
        var value = dataItem.get("valueY");
        if (value < 0) {
          value = 10;
        }

        dataItem.set("valueY", value);
        dataItem.animate({
          key: "valueYWorking",
          to: value,
          duration: 600,
          easing: am5.ease.out(am5.ease.cubic),
        });
      });

      sortCategoryAxis();
    }

    function getSeriesItem(category) {
      for (var i = 0; i < series.dataItems.length; i++) {
        var dataItem = series.dataItems[i];
        if (dataItem.get("categoryX") == category) {
          return dataItem;
        }
      }
    }

    function sortCategoryAxis() {
      series.dataItems.sort(function (x, y) {
        return y.get("valueY") - x.get("valueY"); // descending
      });

      am5.array.each(xAxis.dataItems, function (dataItem) {
        var seriesDataItem = getSeriesItem(dataItem.get("category"));

        if (seriesDataItem) {
          var index = series.dataItems.indexOf(seriesDataItem);
          var deltaPosition =
            (index - dataItem.get("index", 0)) / series.dataItems.length;
          dataItem.set("index", index);
          dataItem.set("deltaPosition", -deltaPosition);
          dataItem.animate({
            key: "deltaPosition",
            to: 0,
            duration: 1000,
            easing: am5.ease.out(am5.ease.cubic),
          });
        }
      });

      xAxis.dataItems.sort(function (x, y) {
        return x.get("index") - y.get("index");
      });
    }

    series.appear(1000);
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
