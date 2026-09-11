/** @odoo-module **/
/*
    Copyright (C) 2022-Today GRAP (http://www.grap.coop)
    @author Sylvain LE GAL (https://twitter.com/legalsylvain)
    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
*/

import {PosOrderToSaleOrder} from "./helpers/PosOrderToSaleOrderMethods.esm";
import {ProductScreen} from "point_of_sale.tour.ProductScreenTourMethods";
import {TextAreaPopup} from "point_of_sale.tour.TextAreaPopupTourMethods";
import {getSteps, startSteps} from "point_of_sale.tour.utils";
import Tour from "web_tour.tour";

startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();

ProductScreen.exec.addOrderline("Whiteboard Pen", "1");
ProductScreen.exec.addOrderline("Wall Shelf Unit", "1");

ProductScreen.do.clickOrderlineCustomerNoteButton();
TextAreaPopup.check.isShown();
TextAreaPopup.do.inputText("Product Note");
TextAreaPopup.do.clickConfirm();

ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Addison Olson");

PosOrderToSaleOrder.do.clickCreateOrderButton();
PosOrderToSaleOrder.do.clickCreateInvoicedOrderButton();

ProductScreen.check.isShown();

Tour.register("PosOrderToSaleOrderTour", {test: true, url: "/pos/ui"}, getSteps());
