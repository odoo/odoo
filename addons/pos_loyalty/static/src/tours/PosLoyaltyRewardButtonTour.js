/** @odoo-module **/

import { PosLoyalty } from 'pos_loyalty.tour.PosCouponTourMethods';
import { ProductScreen } from 'point_of_sale.tour.ProductScreenTourMethods';
import { SelectionPopup } from 'point_of_sale.tour.SelectionPopupTourMethods';
import { getSteps, startSteps } from 'point_of_sale.tour.utils';
import Tour from 'web_tour.tour';

startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();

ProductScreen.exec.addOrderline('Desk Organizer', '2');

// At this point, the free_product program is triggered.
// The reward button should be highlighted.
PosLoyalty.check.isRewardButtonHighlighted(true);
// Since the reward button is highlighted, clicking the reward product should be added as reward.
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
ProductScreen.check.selectedOrderlineHas('Desk Organizer', '3.00');
PosLoyalty.check.hasRewardLine('Free Product - Desk Organizer', '-5.10', '1.00');
// In the succeeding 2 clicks on the product, it is considered as a regular product.
// In the third click, the product will be added as reward.
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
PosLoyalty.check.isRewardButtonHighlighted(true);
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
ProductScreen.check.selectedOrderlineHas('Desk Organizer', '6.00');
PosLoyalty.check.hasRewardLine('Free Product - Desk Organizer', '-10.20', '2.00');


ProductScreen.do.clickDisplayedProduct('Desk Organizer');
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.orderTotalIs('25.50');
// Finalize order that consumed a reward.
PosLoyalty.exec.finalizeOrder('Cash', '30');

ProductScreen.do.clickDisplayedProduct('Desk Organizer');
ProductScreen.check.selectedOrderlineHas('Desk Organizer', '1.00');
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
ProductScreen.check.selectedOrderlineHas('Desk Organizer', '2.00');
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
PosLoyalty.check.hasRewardLine('Free Product - Desk Organizer', '-5.10', '1.00');
ProductScreen.do.pressNumpad('Backspace');
ProductScreen.check.selectedOrderlineHas('Desk Organizer', '0.00');
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
ProductScreen.check.selectedOrderlineHas('Desk Organizer', '1.00');
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
ProductScreen.check.selectedOrderlineHas('Desk Organizer', '2.00');
PosLoyalty.check.isRewardButtonHighlighted(true);
// Finalize order but without the reward.
// This step is important. When syncing the order, no reward should be synced.
PosLoyalty.check.orderTotalIs('10.20');
PosLoyalty.exec.finalizeOrder('Cash', '20');


ProductScreen.exec.addOrderline('Magnetic Board', '2');
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.do.clickDisplayedProduct('Magnetic Board');
PosLoyalty.check.isRewardButtonHighlighted(true);
ProductScreen.do.clickDisplayedProduct('Whiteboard Pen');
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.hasRewardLine('Free Product - Whiteboard Pen', '-3.20', '1.00');
ProductScreen.do.clickOrderline('Magnetic Board', '3.00');
ProductScreen.check.selectedOrderlineHas('Magnetic Board', '3.00');
ProductScreen.do.pressNumpad('6');
ProductScreen.check.selectedOrderlineHas('Magnetic Board', '6.00');
PosLoyalty.check.isRewardButtonHighlighted(true);
PosLoyalty.do.clickRewardButton();
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.hasRewardLine('Free Product - Whiteboard Pen', '-6.40', '2.00');
// Finalize order that consumed a reward.
PosLoyalty.check.orderTotalIs('11.88');
PosLoyalty.exec.finalizeOrder('Cash', '20');

ProductScreen.exec.addOrderline('Magnetic Board', '6');
ProductScreen.do.clickDisplayedProduct('Whiteboard Pen');
PosLoyalty.check.hasRewardLine('Free Product - Whiteboard Pen', '-3.20', '1.00');
PosLoyalty.check.isRewardButtonHighlighted(true);

ProductScreen.do.clickOrderline('Magnetic Board', '6.00');
ProductScreen.do.pressNumpad('Backspace');
// At this point, the reward should have been removed.
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.check.selectedOrderlineHas('Magnetic Board', '0.00');
ProductScreen.do.clickDisplayedProduct('Magnetic Board');
ProductScreen.check.selectedOrderlineHas('Magnetic Board', '1.00');
ProductScreen.do.clickDisplayedProduct('Magnetic Board');
ProductScreen.check.selectedOrderlineHas('Magnetic Board', '2.00');
ProductScreen.do.clickDisplayedProduct('Magnetic Board');
ProductScreen.check.selectedOrderlineHas('Magnetic Board', '3.00');
PosLoyalty.check.hasRewardLine('Free Product - Whiteboard Pen', '-3.20', '1.00');
PosLoyalty.check.isRewardButtonHighlighted(false);

PosLoyalty.check.orderTotalIs('5.94');
PosLoyalty.exec.finalizeOrder('Cash', '10');

// Promotion: 2 items of shelves, get desk_pad/monitor_stand free
// This is the 5th order.
ProductScreen.do.clickDisplayedProduct('Wall Shelf Unit');
ProductScreen.check.selectedOrderlineHas('Wall Shelf Unit', '1.00');
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.do.clickDisplayedProduct('Small Shelf');
ProductScreen.check.selectedOrderlineHas('Small Shelf', '1.00');
PosLoyalty.check.isRewardButtonHighlighted(true);
// Click reward product. Should be automatically added as reward.
ProductScreen.do.clickDisplayedProduct('Desk Pad');
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.hasRewardLine('Free Product', '-1.98', '1.00');
// Remove the reward line. The next steps will check if cashier
// can select from the different reward products.
ProductScreen.do.pressNumpad('Backspace');
ProductScreen.do.pressNumpad('Backspace');
PosLoyalty.check.isRewardButtonHighlighted(true);
PosLoyalty.do.clickRewardButton();
SelectionPopup.check.hasSelectionItem('Monitor Stand');
SelectionPopup.check.hasSelectionItem('Desk Pad');
SelectionPopup.do.clickItem('Desk Pad');
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.hasRewardLine('Free Product', '-1.98', '1.00');
ProductScreen.do.pressNumpad('Backspace');
ProductScreen.do.pressNumpad('Backspace');
PosLoyalty.check.isRewardButtonHighlighted(true);
PosLoyalty.do.claimReward('Monitor Stand');
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.check.selectedOrderlineHas('Monitor Stand', '1.00', '3.19');
PosLoyalty.check.hasRewardLine('Free Product', '-3.19', '1.00');
PosLoyalty.check.orderTotalIs('4.81');
PosLoyalty.exec.finalizeOrder('Cash', '10');

Tour.register('PosLoyaltyFreeProductTour', { test: true, url: '/pos/web' }, getSteps());

startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();

ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('AAA Partner');
ProductScreen.exec.addOrderline('Test Product A', '1');
PosLoyalty.check.isRewardButtonHighlighted(true);
PosLoyalty.do.clickRewardButton();
PosLoyalty.check.hasRewardLine('Free Product - Test Product A', '-11.50', '1.00');

Tour.register('PosLoyaltyFreeProductTour2', { test: true, url: '/pos/web' }, getSteps());
