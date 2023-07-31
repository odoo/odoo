/** @odoo-module **/

import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { Chrome } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import Tour from "web_tour.tour";

startSteps();

Chrome.check.isCashMoveButtonHidden();

Tour.register('chrome_without_cash_move_permission', { test: true, url: '/pos/ui' }, getSteps());
