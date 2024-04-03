/** @odoo-module **/

import { PaymentScreen } from 'point_of_sale.tour.PaymentScreenTourMethods';
import { ProductScreen } from 'pos_sale.tour.ProductScreenTourMethods';
import { ReceiptScreen } from 'point_of_sale.tour.ReceiptScreenTourMethods';
import { getSteps, startSteps } from 'point_of_sale.tour.utils';
import Tour from 'web_tour.tour';

// First tour should not get any automatic rewards
startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickQuotationButton();
ProductScreen.do.selectFirstOrder();
ProductScreen.do.clickDisplayedProduct('Desk Pad');
ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod('Bank');
PaymentScreen.do.clickValidate();
ReceiptScreen.check.isShown();

Tour.register('PosSaleLoyaltyTour1', { test: true, url: '/pos/web' }, getSteps());
