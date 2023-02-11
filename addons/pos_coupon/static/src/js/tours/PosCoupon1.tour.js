odoo.define('pos_coupon.tour.pos_coupon1', function (require) {
    'use strict';

    // --- PoS Coupon Tour Basic Part 1 ---
    // Generate coupons for PosCouponTour2.

    const { PosCoupon } = require('pos_coupon.tour.PosCouponTourMethods');
    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    ProductScreen.do.confirmOpeningPopup();
    ProductScreen.do.clickHomeCategory();

    // basic order
    // just accept the automatically applied promo program
    // applied programs:
    //   - on cheapest product
    ProductScreen.exec.addOrderline('Whiteboard Pen', '5');
    PosCoupon.check.hasRewardLine('90.0% discount on cheapest product', '-2.88');
    PosCoupon.do.selectRewardLine('on cheapest product');
    PosCoupon.check.orderTotalIs('13.12');
    PosCoupon.exec.finalizeOrder('Cash', '20');

    // remove the reward from auto promo program
    // no applied programs
    ProductScreen.exec.addOrderline('Whiteboard Pen', '6');
    PosCoupon.check.hasRewardLine('on cheapest product', '-2.88');
    PosCoupon.check.orderTotalIs('16.32');
    PosCoupon.exec.removeRewardLine('90.0% discount on cheapest product');
    PosCoupon.check.orderTotalIs('19.2');
    PosCoupon.exec.finalizeOrder('Cash', '20');

    // order with coupon code from coupon program
    // applied programs:
    //   - coupon program
    ProductScreen.exec.addOrderline('Desk Organizer', '9');
    PosCoupon.check.hasRewardLine('on cheapest product', '-4.59');
    PosCoupon.exec.removeRewardLine('90.0% discount on cheapest product');
    PosCoupon.check.orderTotalIs('45.90');
    PosCoupon.do.enterCode('invalid_code');
    PosCoupon.do.enterCode('1234');
    PosCoupon.check.hasRewardLine('Free Product - Desk Organizer', '-15.30');
    PosCoupon.exec.finalizeOrder('Cash', '50');

    // Use coupon but eventually remove the reward
    // applied programs:
    //   - on cheapest product
    ProductScreen.exec.addOrderline('Letter Tray', '4');
    ProductScreen.exec.addOrderline('Desk Organizer', '9');
    PosCoupon.check.hasRewardLine('90.0% discount on cheapest product', '-4.32');
    PosCoupon.check.orderTotalIs('62.27');
    PosCoupon.do.enterCode('5678');
    PosCoupon.check.hasRewardLine('Free Product - Desk Organizer', '-15.30');
    PosCoupon.check.orderTotalIs('46.97');
    PosCoupon.exec.removeRewardLine('Free Product - Desk Organizer');
    PosCoupon.check.orderTotalIs('62.27');
    PosCoupon.exec.finalizeOrder('Cash', '90');

    // specific product discount
    // applied programs:
    //   - on cheapest product
    //   - on specific products
    ProductScreen.exec.addOrderline('Magnetic Board', '10') // 1.98
    ProductScreen.exec.addOrderline('Desk Organizer', '3') // 5.1
    ProductScreen.exec.addOrderline('Letter Tray', '4') // 4.8 tax 10%
    PosCoupon.check.hasRewardLine('90.0% discount on cheapest product', '-1.78')
    PosCoupon.check.orderTotalIs('54.44')
    PosCoupon.do.enterCode('promocode')
    PosCoupon.check.hasRewardLine('50.0% discount on products', '-17.55')
    PosCoupon.check.orderTotalIs('36.89')
    PosCoupon.exec.finalizeOrder('Cash', '50')

    // code_promo_program_free_product
    // applied programs:
    //   - on cheapest product
    //   - free product different from criterion product
    //      (Buy 3 Whiteboard Pen, Take 1 Magnetic Board)
    PosCoupon.do.enterCode('board')
    ProductScreen.exec.addOrderline('Whiteboard Pen', '5') // 3.20 each
    // User should manually add the free product to get the reward.
    ProductScreen.exec.addOrderline('Magnetic Board', '1') // 1.98
    PosCoupon.check.hasRewardLine('Free Product - Magnetic Board', '-1.98') // meaning 1 item
    // cheapest product should point to Whiteboard Pen and not the added Magnetic Board
    // even though Whiteboard Pen ($3.20) costs more than Magnetic Board ($1.98).
    PosCoupon.check.hasRewardLine('90.0% discount on cheapest product', '-2.88')
    PosCoupon.check.orderTotalIs('13.12')
    PosCoupon.exec.finalizeOrder('Cash', '20')

    Tour.register('PosCouponTour1', { test: true, url: '/pos/web' }, getSteps());
});
