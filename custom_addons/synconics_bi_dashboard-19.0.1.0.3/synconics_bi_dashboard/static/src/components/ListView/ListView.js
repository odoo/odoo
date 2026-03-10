/** @odoo-module **/

import { Component, onMounted, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ListView extends Component {
  static template = "synconics_bi_dashboard.ListView";
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
    this.action = useService("action");
    this.state = useState({
      columns: [],
      data: [],
      isError: false,
      errorMessage: false,
      chartName: "",
      columns_order: {},
      currentRecords: [],
      currentPage: 1,
      totalRecords: 0,
      totalPages: 0,
      dataModel: "",
    });
    this.sortTable = (ev, column) => {
      let current_order = this.state.columns_order[column["column_name"]];
      this.state.columns_order = this.state.columns.reduce((acc, item) => {
        acc[item.column_name] = undefined;
        return acc;
      }, {});
      this.state.columns_order[column["column_name"]] =
        current_order == "asc"
          ? "desc"
          : current_order == "desc"
            ? "asc"
            : "asc";
    };

    this.openRecords = async (ev, currentIds) => {
      this.action.doAction({
        type: "ir.actions.act_window",
        name: this.state.chartName,
        res_model: this.state.dataModel,
        views: [[false, "list"]],
        domain: [["id", "in", Object.values(currentIds)]],
        target: "current",
      });
    };

    this.goToPage = (ev) => {
      this.state.currentPage = parseInt(ev.target.value);
    };

    this.changePage = (updateIndex) => {
      this.state.currentPage = this.state.currentPage + updateIndex;
    };

    useEffect(
      () => {
        this.render_list_view();
      },
      () => [
        this.props.chartId,
        this.props.recordSets,
        this.props.isDirty,
        this.props.data,
      ],
    );

    useEffect(
      () => {
        const sortKeys = Object.entries(this.state.columns_order).filter(
          ([_, dir]) => dir === "asc" || dir === "desc",
        );
        const updatedData = this.state.data.slice().sort((a, b) => {
          for (const [key, direction] of sortKeys) {
            if (a[key] < b[key]) return direction === "asc" ? -1 : 1;
            if (a[key] > b[key]) return direction === "asc" ? 1 : -1;
          }
          return 0;
        });
        this.state.data = updatedData;
      },
      () => [...Object.values(this.state.columns_order)],
    );

    useEffect(
      () => {
        const start = (this.state.currentPage - 1) * 10;
        const end = start + 10;
        this.state.currentRecords = this.state.data.slice(start, end);
      },
      () => [this.state.currentPage, ...this.state.data],
    );

    onMounted(() => {
      this.render_list_view();
    });
  }

  render_list_view() {
    let data = this.props.recordSets;
    if (typeof data == "object" && data.type) {
      this.state.isError = true;
      this.state.errorMessage = data.message;
      return;
    }

    if (Array.isArray(data)) {
      return;
    }
    if (!data.columns || !data.records) {
      return;
    }
    this.state.isError = false;
    this.state.chartName = data.name;
    this.state.columns = data.columns;
    this.state.columns_order = data.columns.reduce((acc, item) => {
      acc[item.column_name] = undefined;
      return acc;
    }, {});

    this.state.data = data.records;
    this.state.totalRecords = data.records.length;
    this.state.totalPages = Math.ceil(data.records.length / 10);
    this.state.dataModel = data.model;
  }
}
