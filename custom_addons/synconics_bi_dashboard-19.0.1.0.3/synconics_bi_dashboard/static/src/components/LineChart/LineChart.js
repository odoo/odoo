/** @odoo-module **/

import { Component, onMounted, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class LineChart extends Component {
  static template = "synconics_bi_dashboard.LineChart";
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
        this.render_line_chart();
      },
      () => [this.props.chartId, this.props.recordSets, this.props.data],
    );
    onMounted(() => {
      this.render_line_chart();
    });
  }

  async render_line_chart() {
    var rawData = this.props.recordSets;
    if (typeof rawData == "object" && !Array.isArray(rawData)) {
      this.state.isError = true;
      this.state.errorMessage = rawData.message;
      return;
    }

    this.state.isError = false;
    this.state.errorMessage = false;
    if (this.root) {
      this.root.dispose();
    }
    this.root = am5.Root.new("line_chart__" + this.props.chartId);
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

    // Apply formatting to your rawData
    rawData = rawData.map((item) => ({
      ...item,
      category: formatLabel(item.category), // Assuming 'category' is your label field
    }));
    var chart = this.root.container.children.push(
      am5xy.XYChart.new(this.root, {
        layout: this.root.verticalLayout,
      }),
    );

    chart.set("paddingBottom", 50);

    let valueTypes = [];
    let companies = new Set();
    Object.keys(rawData[0]).forEach((key) => {
      if (key !== "category" && key !== "record_id" && key !== "isSubGroupBy") {
        let [company, valueType] = key.split(" - ");
        companies.add(company);
        if (!valueTypes.includes(valueType)) {
          valueTypes.push(valueType);
        }
      }
    });
    companies = [...companies];

    let data = rawData.map((item) => {
      let newItem = { category: item.category };
      companies.forEach((company) => {
        valueTypes.forEach((type) => {
          let key = `${company} - ${type}`;
          if (item[key] != null) {
            newItem[`${company}_${type}`] = item[key];
          }
        });
      });
      return newItem;
    });

    data.unshift({
      category: "0",
      ...Object.fromEntries(
        companies.flatMap((company) =>
          valueTypes.map((type) => [`${company}_${type}`, 0]),
        ),
      ),
    });

    var xRenderer = am5xy.AxisRendererX.new(this.root, {
      minorGridEnabled: true,
    });
    xRenderer.grid.template.set("location", 0.5);
    xRenderer.labels.template.setAll({
      location: 0.5,
      multiLocation: 0.5,
      rotation: -45,
      centerY: am5.p0,
      centerX: am5.p100,
      maxWidth: 120,
      oversizedBehavior: "truncate",
      // paddingRight: 10,
      fontSize: 11,
    });
    var xAxis = chart.xAxes.push(
      am5xy.CategoryAxis.new(this.root, {
        categoryField: "category",
        renderer: xRenderer,
        tooltip: am5.Tooltip.new(this.root, {}),
        snapTooltip: true,
      }),
    );
    xAxis.data.setAll(data);
    xRenderer.set("minGridDistance", 1);

    var yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(this.root, {
        maxPrecision: 0,
        min: 0,
        renderer: am5xy.AxisRendererY.new(this.root, {}),
      }),
    );

    yAxis.get("renderer").labels.template.setAll({
      rotation: -30,
      centerX: am5.p100,
      centerY: am5.p50,
    });

    var cursor = chart.set(
      "cursor",
      am5xy.XYCursor.new(this.root, {
        alwaysShow: true,
        xAxis: xAxis,
        positionX: 1,
      }),
    );
    cursor.lineY.set("visible", false);
    cursor.lineX.set("focusable", true);

    var self = this;

    function createSeries(name, field) {
      var series = chart.series.push(
        am5xy.LineSeries.new(self.root, {
          name: name,
          xAxis: xAxis,
          yAxis: yAxis,
          valueYField: field,
          categoryXField: "category",
          tooltip: am5.Tooltip.new(self.root, {
            pointerOrientation: "horizontal",
            labelText: "[bold]{name}[/]\n{categoryX}: {valueY}",
          }),
        }),
      );

      series.strokes.template.setAll({
        strokeWidth: 3,
      });

      series.bullets.push(function () {
        return am5.Bullet.new(self.root, {
          sprite: am5.Circle.new(self.root, {
            radius: 5,
            fill: series.get("fill"),
          }),
        });
      });

      series.set("setStateOnChildren", true);
      series.states.create("hover", {});
      series.mainContainer.set("setStateOnChildren", true);
      series.mainContainer.states.create("hover", {});
      series.strokes.template.states.create("hover", { strokeWidth: 4 });
      series.bullets.push(function (root, series, dataItem) {
        let circle = am5.Circle.new(root, {
          radius: 5,
          fill: series.get("fill"),
        });

        circle.events.on("click", function () {
          if (self.props.update_chart) {
            self.props.update_chart(
              parseInt(self.props.chartId),
              "column_chart",
              dataItem.dataContext,
            );
          }
        });

        return am5.Bullet.new(root, { sprite: circle });
      });
      series.data.setAll(data);
      series.appear(1000);
    }

    // Create series for each company + value type
    companies.forEach((company) => {
      valueTypes.forEach((type) => {
        const field = `${company}_${type}`;
        if (data[0][field] !== undefined) {
          createSeries(`${company} (${type})`, field);
        }
      });
    });

    // Scrollbar
    // chart.set(
    //   "scrollbarX",
    //   am5.Scrollbar.new(this.root, {
    //     orientation: "horizontal",
    //     marginBottom: 20,
    //   }),
    // );

    // Legend
    var legend = chart.children.push(
      am5.Legend.new(this.root, {
        centerX: am5.p50,
        x: am5.p50,
      }),
    );

    // Hover interaction via legend
    legend.itemContainers.template.states.create("hover", {});
    legend.itemContainers.template.events.on("pointerover", function (e) {
      e.target.dataItem.dataContext.hover();
    });
    legend.itemContainers.template.events.on("pointerout", function (e) {
      e.target.dataItem.dataContext.unhover();
    });
    legend.data.setAll(chart.series.values);

    // Cursor position toggle on hover
    chart.plotContainer.events.on("pointerout", function () {
      cursor.set("positionX", 1);
    });
    chart.plotContainer.events.on("pointerover", function () {
      cursor.set("positionX", undefined);
    });

    // Animate chart
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
