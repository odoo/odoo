/** @odoo-module **/

import { ErrorPopup } from 'point_of_sale.tour.ErrorPopupTourMethods';
import { PosLoyalty } from 'pos_loyalty.tour.PosCouponTourMethods';
import { ProductScreen } from 'point_of_sale.tour.ProductScreenTourMethods';
import { TicketScreen } from 'point_of_sale.tour.TicketScreenTourMethods';
import { Chrome } from 'point_of_sale.tour.ChromeTourMethods';
import { PartnerListScreen } from 'point_of_sale.tour.PartnerListScreenTourMethods';
import { getSteps, startSteps } from 'point_of_sale.tour.utils';
import Tour from 'web_tour.tour';

//#region EWalletProgramTour1

startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();

// Topup 50$ for partner_aaa
ProductScreen.do.clickDisplayedProduct('Top-up eWallet');
PosLoyalty.check.orderTotalIs('50.00');
ProductScreen.do.clickPayButton(false);
// If there's no partner, we asked to redirect to the partner list screen.
Chrome.do.confirmPopup();
PartnerListScreen.check.isShown();
PartnerListScreen.do.clickPartner('AAAAAAA');
PosLoyalty.exec.finalizeOrder('Cash', '50');

// Topup 10$ for partner_bbb
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('BBBBBBB');
ProductScreen.exec.addOrderline('Top-up eWallet', '1', '10');
PosLoyalty.check.orderTotalIs('10.00');
PosLoyalty.exec.finalizeOrder('Cash', '10');

Tour.register('EWalletProgramTour1', { test: true, url: '/pos/web' }, getSteps());

//#endregion

//#region EWalletProgramTour2

const getEWalletText = (suffix) => 'eWallet' + (suffix !== '' ? ` ${suffix}` : '');

startSteps();
ProductScreen.do.clickHomeCategory();
ProductScreen.exec.addOrderline('Whiteboard Pen', '2', '6', '12.00');
PosLoyalty.check.eWalletButtonState({ highlighted: false });
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('AAAAAAA');
PosLoyalty.check.eWalletButtonState({ highlighted: true, text: getEWalletText('Pay') });
PosLoyalty.do.clickEWalletButton(getEWalletText('Pay'));
PosLoyalty.check.orderTotalIs('0.00');
PosLoyalty.exec.finalizeOrder('Cash', '0');

// Consume partner_bbb's full eWallet.
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('BBBBBBB');
PosLoyalty.check.eWalletButtonState({ highlighted: false });
ProductScreen.exec.addOrderline('Desk Pad', '6', '6', '36.00');
PosLoyalty.check.eWalletButtonState({ highlighted: true, text: getEWalletText('Pay') });
PosLoyalty.do.clickEWalletButton(getEWalletText('Pay'));
PosLoyalty.check.orderTotalIs('26.00');
PosLoyalty.exec.finalizeOrder('Cash', '26');

// Switching partners should work.
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('BBBBBBB');
ProductScreen.exec.addOrderline('Desk Pad', '2', '19', '38.00');
PosLoyalty.check.eWalletButtonState({ highlighted: false });
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('AAAAAAA');
PosLoyalty.check.eWalletButtonState({ highlighted: true, text: getEWalletText('Pay') });
PosLoyalty.do.clickEWalletButton(getEWalletText('Pay'));
PosLoyalty.check.orderTotalIs('0.00');
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('BBBBBBB');
PosLoyalty.check.eWalletButtonState({ highlighted: false });
PosLoyalty.check.orderTotalIs('38.00');
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('AAAAAAA');
PosLoyalty.check.eWalletButtonState({ highlighted: true, text: getEWalletText('Pay') });
PosLoyalty.do.clickEWalletButton(getEWalletText('Pay'));
PosLoyalty.check.orderTotalIs('0.00');
PosLoyalty.exec.finalizeOrder('Cash', '0');

// Refund with eWallet.
// - Make an order to refund.
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('BBBBBBB');
ProductScreen.exec.addOrderline('Whiteboard Pen', '1', '20', '20.00');
PosLoyalty.check.orderTotalIs('20.00');
PosLoyalty.exec.finalizeOrder('Cash', '20');
// - Refund order.
ProductScreen.do.clickRefund();
TicketScreen.check.filterIs('Paid');
TicketScreen.do.selectOrder('-0004');
TicketScreen.check.partnerIs('BBBBBBB');
TicketScreen.do.confirmRefund();
ProductScreen.check.isShown();
PosLoyalty.check.eWalletButtonState({ highlighted: true, text: getEWalletText('Refund') });
PosLoyalty.do.clickEWalletButton(getEWalletText('Refund'));
PosLoyalty.check.orderTotalIs('0.00');
PosLoyalty.exec.finalizeOrder('Cash', '0');

Tour.register('EWalletProgramTour2', { test: true, url: '/pos/web' }, getSteps());

//#endregion

//#region ExpiredEWalletProgramTour

startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('AAAA');
ProductScreen.exec.addOrderline('Whiteboard Pen', '2', '6', '12.00');
PosLoyalty.check.eWalletButtonState({ highlighted: false });
PosLoyalty.do.clickEWalletButton();
ErrorPopup.check.isShown();
ErrorPopup.do.clickConfirm();

Tour.register('ExpiredEWalletProgramTour', { test: true, url: '/pos/web' }, getSteps());

//#endregion
