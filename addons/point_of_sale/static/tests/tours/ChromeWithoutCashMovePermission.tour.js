/** @odoo-module **/

import { getSteps, startSteps } from "point_of_sale.tour.utils";
import { Chrome } from "point_of_sale.tour.ChromeTourMethods";
import Tour from "web_tour.tour";

startSteps();

Chrome.check.isCashMoveButtonHidden();

Tour.register('chrome_without_cash_move_permission', { test: true, url: '/pos/ui' }, getSteps());
