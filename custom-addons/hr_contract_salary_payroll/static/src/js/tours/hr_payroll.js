/** @odoo-module **/

import { registry } from "@web/core/registry";
import '@hr_payroll/js/tours/hr_payroll';

registry.category("web_tour.tours").remove("payroll_tours");
