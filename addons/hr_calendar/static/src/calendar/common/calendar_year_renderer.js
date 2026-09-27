/** @odoo-module **/

import { t } from "@odoo/owl";
import { calendarYearRendererProps } from "@web/views/calendar/calendar_year/calendar_year_renderer";

calendarYearRendererProps.openWorkLocationWizard = t.function().optional();
