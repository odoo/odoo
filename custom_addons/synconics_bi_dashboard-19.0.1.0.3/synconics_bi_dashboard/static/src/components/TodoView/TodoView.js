/** @odoo-module **/

import { Component, onMounted, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class TodoView extends Component {
  static template = "synconics_bi_dashboard.TodoView";

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
      name: "",
      data: [],
      lines: [],
      layout_type: "default",
      isError: false,
      errorMessage: false,
      currentTask: false,
      totalTasks: 0,
      completedTasks: 0,
      activeSelectedRecord: false,
    });
    useEffect(
      () => {
        this.render_todo_view();
      },
      () => [
        this.props.name,
        this.props.chartId,
        this.props.recordSets,
        this.props.isDirty,
        this.props.data,
      ],
    );

    onMounted(() => {
      this.render_todo_view();
    });

    this.setChildElements = (ev, record, lines) => {
      this.state.lines = lines;
      this.state.currentTask = record.name;
      this.state.totalTasks = lines.length;
      this.state.activeSelectedRecord = record.id;
      this.state.completedTasks = lines.filter((cl) => cl.active_record).length;
    };
  }

  render_todo_view() {
    let data = this.props.recordSets;
    if (Array.isArray(data)) {
      return;
    }
    if (data.type == "error") {
      this.state.isError = true;
      this.state.errorMessage = data.message;
      return;
    }
    this.state.isError = false;
    if (!data.layout_type) {
      return;
    }
    this.state.layout_type = data.layout_type;
    let dataList = data.records.map((project, index) => ({
      id: index + 1,
      ...project,
    }));
    this.state.data = dataList;
    this.state.name = data.name;
    this.state.currentTask = data.records[0].name;
    if (data.layout_type == "default") {
      this.state.activeSelectedRecord = dataList[0].id;
      this.state.totalTasks = data.records[0].action_line_ids.length;
      this.state.completedTasks = data.records[0].action_line_ids.filter(
        (cl) => cl.active_record,
      ).length;
      this.state.lines = data.records[0].action_line_ids;
    }
  }
}
