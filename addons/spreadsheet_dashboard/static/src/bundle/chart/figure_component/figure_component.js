import { components } from "@odoo/o-spreadsheet";
import { ChartTypeSwitcherMenu } from "../chart_type_switcher/chart_type_switcher";

const { FigureComponent } = components;

FigureComponent.components = { ...FigureComponent.components, ChartTypeSwitcherMenu };
