/** @odoo-module **/

import { Component, onWillStart, useState, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { AreaChart } from "../components/AreaChart/AreaChart";
import { BarChart } from "../components/BarChart/BarChart";
import { ColumnChart } from "../components/ColumnChart/ColumnChart";
import { DoughnutChart } from "../components/DoughnutChart/DoughnutChart";
import { FunnelChart } from "../components/FunnelChart/FunnelChart";
import { PyramidChart } from "../components/PyramidChart/PyramidChart";
import { LineChart } from "../components/LineChart/LineChart";
import { PieChart } from "../components/PieChart/PieChart";
import { RadarChart } from "../components/RadarChart/RadarChart";
import { StackedColumnChart } from "../components/StackedColumnChart/StackedColumnChart";
import { RadialChart } from "../components/RadialChart/RadialChart";
import { ScatterChart } from "../components/ScatterChart/ScatterChart";
import { MapChart } from "../components/MapChart/MapChart";
import { MeterChart } from "../components/MeterChart/MeterChart";
import { ListView } from "../components/ListView/ListView";
import { TileView } from "../components/TileView/TileView";
import { KPIView } from "../components/KPIView/KPIView";
import { TodoView } from "../components/TodoView/TodoView";

export class FormDashboardPreviewComponent extends Component {
  static template = "synconics_bi_dashboard.formDashboardPreview";
  setup() {
    super.setup();
    this.orm = useService("orm");
    this.state = useState({
      id: this.props.record.resId || 0,
      chart_type: this.props.record.data.chart_type,
      name: this.props.record.data.name,
      isDirty: false,
      data: {},
      theme: this.props.record.data.theme,
      recordSets: {},
    });

    // onWillStart(() => {
    //   this.updateRecordSets(
    //     this.state.id,
    //     this.state.chart_type,
    //     this.state.name,
    //     {},
    //   );
    // });
    useEffect(
      () => {
        this.state.id = this.props.record.resId || 0;
        this.state.chart_type = this.props.record.data.chart_type;
        this.state.name = this.props.record.data.name;
        this.state.theme = this.props.record.data.theme;
        this.isRecordDirty();
        let prepared_data = {
          name: this.props.record.data.name,
          layout_type: this.props.record.data.layout_type,
          tile_layout_type: this.props.record.data.tile_layout_type,
          text_align: this.props.record.data.text_align,
          background_color: this.props.record.data.background_color,
          font_color: this.props.record.data.font_color,
          group_by_id: this.props.record.data.group_by_id.id,
          time_range: this.props.record.data.time_range,
          map_group_by_id: this.props.record.data.map_group_by_id.id,
          measurement_field_id: this.props.record.data.measurement_field_id.id,
          measurement_field_ids: Array.prototype.slice.call(
            this.props.record.data.measurement_field_ids._currentIds,
          ),
          model_id: this.props.record.data.model_id.id,
          hide_false_value: this.props.record.data.hide_false_value,
          kpi_model_id: this.props.record.data.kpi_model_id.id,
          kpi_data_type: this.props.record.data.kpi_data_type,
          kpi_measurement_field_id:
            this.props.record.data.kpi_measurement_field_id.id,
          kpi_limit_record: this.props.record.data.kpi_limit_record,
          limit_record: this.props.record.data.limit_record,
          kpi_domain: this.props.record.data.kpi_domain,
          kpi_date_filter_field_id:
            this.props.record.data.kpi_date_filter_field_id.id,
          kpi_date_filter_option: this.props.record.data.kpi_date_filter_option,
          kpi_include_periods: this.props.record.data.kpi_include_periods,
          kpi_same_period_period_previous_years:
            this.props.record.data.kpi_same_period_period_previous_years,
          previous_period_comparison:
            this.props.record.data.previous_period_comparison,
          previous_period_duration:
            this.props.record.data.previous_period_duration,
          previous_period_type: this.props.record.data.previous_period_type,
          domain: this.props.record.data.domain,
          meter_target: this.props.record.data.meter_target,
          sort_field_id: this.props.record.data.sort_field_id.id,
          sort_order: this.props.record.data.sort_order,
          sub_group_by_id: this.props.record.data.sub_group_by_id.id,
          sub_time_range: this.props.record.data.sub_time_range,
          data_type: this.props.record.data.data_type,
          font_size: this.props.record.data.font_size,
          font_weight: this.props.record.data.font_weight,
          previous_period_comparision:
            this.props.record.data.previous_period_comparision,
          date_filter_field_id: this.props.record.data.date_filter_field_id.id,
          date_filter_option: this.props.record.data.date_filter_option,
          company_id: this.props.record.data.company_id.id,
          is_kpi_border: this.props.record.data.is_kpi_border,
          kpi_border_type: this.props.record.data.kpi_border_type,
          kpi_border_color: this.props.record.data.kpi_border_color,
          kpi_border_width: this.props.record.data.kpi_border_width,
          icon_option: this.props.record.data.icon_option,
          default_icon: this.props.record.data.default_icon,
          todo_layout: this.props.record.data.todo_layout,
          todo_action_ids: this.props.record.data.todo_action_ids.records.map(
            (res) => {
              return {
                name: res.data.name,
                action_line_ids: res.data.action_line_ids.records.map((sub) => {
                  return {
                    name: sub.data.name,
                    active_record: sub.data.active_record,
                  };
                }),
              };
            },
          ),
          is_apply_multiplier: this.props.record.data.is_apply_multiplier,
          kpi_comparison_type: this.props.record.data.kpi_comparison_type,
          kpi_enable_target: this.props.record.data.kpi_enable_target,
          kpi_target_value: this.props.record.data.kpi_target_value,
          kpi_view_type: this.props.record.data.kpi_view_type,
          show_unit: this.props.record.data.show_unit,
          unit_type: this.props.record.data.unit_type,
          custom_unit: this.props.record.data.custom_unit,
          chart_multiplier_ids:
            this.props.record.data.chart_multiplier_ids.records.map((res) => {
              return {
                field_id: res.data.field_id.id,
                multiplier: res.data.multiplier,
              };
            }),
          list_measure_ids: this.props.record.data.list_measure_ids.records
            .filter((measure) => measure.data.list_measure_id)
            .map((res) => {
              return {
                list_measure_id: res.data.list_measure_id.id,
                value_type: res.data.value_type,
              };
            }),
          list_field_ids: this.props.record.data.list_field_ids.records
            .filter((list_field) => list_field.data.list_field_id)
            .map((res) => {
              return {
                list_field_id: res.data.list_field_id.id,
                sequence: res.data.sequence,
              };
            }),
          list_type: this.props.record.data.list_type,
          include_periods: this.props.record.data.include_periods,
          same_period_previous_years:
            this.props.record.data.same_period_previous_years,
        };
        // this.state.data = prepared_data;
        this.updateRecordSets(
          this.props.record.resId || 0,
          this.props.record.data.chart_type,
          this.state.name,
          prepared_data,
        );
        this.render();
      },
      () => [
        ...Object.values(this.props.record.data),
        ...Object.values(this.props.record.data.measurement_field_ids),
        ...this.props.record.data.chart_multiplier_ids.records.map(
          (res) => res.data.multiplier,
        ),
        ...this.props.record.data.list_field_ids.records.map(
          (res) => res.data.list_field_id,
        ),
        ...this.props.record.data.todo_action_ids.records.map(
          (res) => res.data.name,
        ),
        ...this.props.record.data.todo_action_ids.records.flatMap((res) =>
          res.data.action_line_ids.records.map(
            (sub) => `${sub.data.name}-${sub.data.active_record}`,
          ),
        ),
        ...this.props.record.data.list_measure_ids.records.map(
          (res) => res.data.list_measure_id,
        ),
        ...this.props.record.data.list_measure_ids.records.map(
          (res) => res.data.value_type,
        ),
      ],
    );
  }

  async updateRecordSets(recordId, chart_type, name, data) {
    let isDirty = await this.isRecordDirty();
    if (this.__owl__.status === 3) {
      return;
    }
    let recordSets = await this.orm.call(
      "dashboard.chart",
      "get_chart_data",
      [recordId],
      { chart_type, name, isDirty, data },
    );
    Object.assign(this.state, { data, recordSets });
  }

  async isRecordDirty() {
    let check_dirty = await this.props.record.isDirty();
    this.state.isDirty = check_dirty;
    return check_dirty;
  }
}

FormDashboardPreviewComponent.components = {
  AreaChart,
  BarChart,
  ColumnChart,
  DoughnutChart,
  FunnelChart,
  PyramidChart,
  LineChart,
  PieChart,
  RadarChart,
  StackedColumnChart,
  RadialChart,
  ScatterChart,
  MapChart,
  MeterChart,
  ListView,
  TileView,
  KPIView,
  TodoView,
};

export const FormDashboardPreview = {
  component: FormDashboardPreviewComponent,
};

registry
  .category("view_widgets")
  .add("form_dashboard_preview", FormDashboardPreview);
