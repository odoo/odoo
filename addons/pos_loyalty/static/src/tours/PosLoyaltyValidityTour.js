/** @odoo-module **/

import { PosLoyalty } from 'pos_loyalty.tour.PosCouponTourMethods';
import { ProductScreen } from 'point_of_sale.tour.ProductScreenTourMethods';
import { getSteps, startSteps } from 'point_of_sale.tour.utils';
import Tour from 'web_tour.tour';

// First tour should not get any automatic rewards
startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();

// Not valid -> date
ProductScreen.exec.addOrderline('Whiteboard Pen', '5');
PosLoyalty.check.checkNoClaimableRewards();
PosLoyalty.exec.finalizeOrder('Cash');

Tour.register('PosLoyaltyValidity1', { test: true, url: '/pos/web' }, getSteps());

// Second tour
startSteps();

ProductScreen.do.clickHomeCategory();

// Valid
ProductScreen.exec.addOrderline('Whiteboard Pen', '5');
PosLoyalty.check.hasRewardLine('90% on the cheapest product', '-2.88');
PosLoyalty.exec.finalizeOrder('Cash');

// Not valid -> usage
ProductScreen.exec.addOrderline('Whiteboard Pen', '5');
PosLoyalty.check.checkNoClaimableRewards();
PosLoyalty.exec.finalizeOrder('Cash');

Tour.register('PosLoyaltyValidity2', { test: true, url: '/pos/web' }, getSteps());
