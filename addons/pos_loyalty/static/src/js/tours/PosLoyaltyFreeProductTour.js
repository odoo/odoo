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
PosLoyalty.check.hasRewardLine('Desk Organizer (free)', '0.00', '1.00');

// In the succeeding 2 clicks on the product, it is considered as a regular product.
// In the third click, the product will be added as reward.
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
PosLoyalty.check.isRewardButtonHighlighted(true);
ProductScreen.do.clickDisplayedProduct('Desk Organizer');
PosLoyalty.check.hasRewardLine('Desk Organizer (free)', '0.00', '2.00');


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
PosLoyalty.check.hasRewardLine('Desk Organizer (free)', '0.00', '1.00');
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
PosLoyalty.check.hasRewardLine('Whiteboard Pen (free)', '0.00', '1.00');

ProductScreen.do.pressNumpad('6');
PosLoyalty.check.isRewardButtonHighlighted(true);
PosLoyalty.do.clickRewardButton();
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.hasRewardLine('Whiteboard Pen (free)', '0.00', '2.00');
// Finalize order that consumed a reward.
PosLoyalty.check.orderTotalIs('11.88');
PosLoyalty.exec.finalizeOrder('Cash', '20');

ProductScreen.exec.addOrderline('Magnetic Board', '6');
ProductScreen.do.clickDisplayedProduct('Whiteboard Pen');
PosLoyalty.check.hasRewardLine('Whiteboard Pen (free)', '0.00', '1.00');
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
PosLoyalty.check.isRewardButtonHighlighted(true);

PosLoyalty.check.orderTotalIs('5.94');
PosLoyalty.exec.finalizeOrder('Cash', '10');

// Promotion: 2 items of shelves, get desk_pad/monitor_stand free
// This is the 5th order.
ProductScreen.exec.addOrderline('Wall Shelf Unit', '1');
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.exec.addOrderline('Small Shelf', '1');
PosLoyalty.check.isRewardButtonHighlighted(true);
// Click reward product. Should be automatically added as reward.
ProductScreen.do.clickDisplayedProduct('Desk Pad');
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.hasRewardLine('Desk Pad (free)', '0.00', '1.00');
// Remove the reward line. The next steps will check if cashier
// can select from the different reward products.
PosLoyalty.exec.removeRewardLine('Desk Pad (free)');
PosLoyalty.check.isRewardButtonHighlighted(true);
PosLoyalty.do.clickRewardButton();
SelectionPopup.check.hasSelectionItem('Monitor Stand');
SelectionPopup.check.hasSelectionItem('Desk Pad');
SelectionPopup.do.clickItem('Desk Pad');
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.hasRewardLine('Desk Pad (free)', '0.00', '1.00');
PosLoyalty.exec.removeRewardLine('Desk Pad (free)');
PosLoyalty.check.isRewardButtonHighlighted(true);
PosLoyalty.do.claimReward('Monitor Stand');
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.hasRewardLine('Monitor Stand (free)', '0.00', '1.00');
PosLoyalty.check.orderTotalIs('4.81');
PosLoyalty.exec.finalizeOrder('Cash', '10');

Tour.register('PosLoyaltyFreeProductTour', { test: true, url: '/pos/web' }, getSteps());
