/** @odoo-module **/

import { PosLoyalty } from 'pos_loyalty.tour.PosCouponTourMethods';
import { ProductScreen } from 'point_of_sale.tour.ProductScreenTourMethods';
import { SelectionPopup } from 'point_of_sale.tour.SelectionPopupTourMethods';
import { getSteps, startSteps } from 'point_of_sale.tour.utils';
import Tour from 'web_tour.tour';

const getEWalletText = (suffix) => 'eWallet' + (suffix !== '' ? ` ${suffix}` : '');

startSteps();
// One card for gift_card_1.
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct('Gift Card');
SelectionPopup.check.hasSelectionItem('gift_card_1');
SelectionPopup.check.hasSelectionItem('gift_card_2');
SelectionPopup.do.clickItem('gift_card_1');
ProductScreen.do.pressNumpad('Price');
ProductScreen.do.pressNumpad('1 0');
PosLoyalty.check.orderTotalIs('10.00');
PosLoyalty.exec.finalizeOrder('Cash', '10');
// One card for gift_card_1.
ProductScreen.do.clickDisplayedProduct('Gift Card');
SelectionPopup.do.clickItem('gift_card_2');
ProductScreen.do.pressNumpad('Price');
ProductScreen.do.pressNumpad('2 0');
PosLoyalty.check.orderTotalIs('20.00');
PosLoyalty.exec.finalizeOrder('Cash', '20');
// Top up ewallet_1 for AAAAAAA.
ProductScreen.do.clickDisplayedProduct('Top-up eWallet');
SelectionPopup.check.hasSelectionItem('ewallet_1');
SelectionPopup.check.hasSelectionItem('ewallet_2');
SelectionPopup.do.clickItem('ewallet_1');
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('AAAAAAA');
ProductScreen.do.pressNumpad('Price');
ProductScreen.do.pressNumpad('3 0');
PosLoyalty.check.orderTotalIs('30.00');
PosLoyalty.exec.finalizeOrder('Cash', '30');
// Top up ewallet_2 for AAAAAAA.
ProductScreen.do.clickDisplayedProduct('Top-up eWallet');
SelectionPopup.do.clickItem('ewallet_2');
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('AAAAAAA');
ProductScreen.do.pressNumpad('Price');
ProductScreen.do.pressNumpad('4 0');
PosLoyalty.check.orderTotalIs('40.00');
PosLoyalty.exec.finalizeOrder('Cash', '40');
// Top up ewallet_1 for BBBBBBB.
ProductScreen.do.clickDisplayedProduct('Top-up eWallet');
SelectionPopup.do.clickItem('ewallet_1');
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('BBBBBBB');
PosLoyalty.check.orderTotalIs('50.00');
PosLoyalty.exec.finalizeOrder('Cash', '50');
// Consume 12$ from ewallet_1 of AAAAAAA.
ProductScreen.exec.addOrderline('Whiteboard Pen', '2', '6', '12.00');
PosLoyalty.check.eWalletButtonState({ highlighted: false });
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer('AAAAAAA');
PosLoyalty.check.eWalletButtonState({ highlighted: true, text: getEWalletText('Pay') });
PosLoyalty.do.clickEWalletButton(getEWalletText('Pay'));
SelectionPopup.check.hasSelectionItem('ewallet_1');
SelectionPopup.check.hasSelectionItem('ewallet_2');
SelectionPopup.do.clickItem('ewallet_1');
PosLoyalty.check.orderTotalIs('0.00');
PosLoyalty.exec.finalizeOrder('Cash', '0');

Tour.register('MultipleGiftWalletProgramsTour', { test: true, url: '/pos/web' }, getSteps());
