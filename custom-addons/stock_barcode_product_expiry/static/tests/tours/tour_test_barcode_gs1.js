/** @odoo-module **/

import helper from '@stock_barcode/../tests/tours/tour_helper_stock_barcode';
import { registry } from "@web/core/registry";
import { stepUtils } from '@stock_barcode/../tests/tours/tour_step_utils';


registry.category("web_tour.tours").add('test_gs1_receipt_expiration_date', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(1);
            const line = helper.getLine({ barcode: "76543210" });
            helper.assertLineIsHighlighted(line, false);
            helper.assertLineQty(line, "0 / 20");
        }
    },
    // The following scanned barcode should be decomposed like that:
    //      - (01)00000076543210    > product barcode (76543210)
    //      - (10)b1-b001           > lot (b1-b001)
    //      - (30)00000008          > quantity (8)
    //      - (17)220520            > expiration date (5/20/2022)
    {
        trigger: '.o_barcode_client_action',
        run: 'scan 010000007654321010b1-b001\x1D300000000817220520',
    },
    {
        trigger: '.o_barcode_line:contains("b1-b001")',
        run: function () {
            helper.assertLinesCount(1);
            const line = helper.getLine({ barcode: "76543210" });
            const lot_with_date = line.querySelector('div[name="lot"]').innerText;
            const date = new Date('2022-05-20').toLocaleDateString();
            helper.assert(lot_with_date, `b1-b001 (${date})`, 'lot line');
            helper.assertLineIsHighlighted(line, true);
            helper.assertLineQty(line, "8 / 20");
        }
    },
    // The following scanned barcode should be decomposed like that:
    //      - (01)00000076543210    > product barcode (76543210)
    //      - (10)b1-b002           > lot (b1-b002)
    //      - (30)00000004          > quantity (4)
    //      - (15)220520            > best before date (5/20/2022) -> expiration date (5/21/2022)
    {
        trigger: '.o_barcode_client_action',
        run: 'scan 010000007654321010b1-b002\x1D300000000415220520',
    },
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },
    {
        trigger: '.o_barcode_line:contains("b1-b002")',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertSublinesCount(2);
            const parentLine = helper.getLine({ barcode: "76543210" });
            const [line1, line2] = helper.getSublines();
            helper.assertLineQty(parentLine, "12 / 20");
            helper.assertLineQty(line1, "8 / 20");
            helper.assertLineQty(line2, "4");
            helper.assertLineIsHighlighted(line1, false);
            helper.assertLineIsHighlighted(line2, true);
            const lot_with_date_1 = line1.querySelector('div[name="lot"]').innerText;
            const lot_with_date_2 = line2.querySelector('div[name="lot"]').innerText;
            const date1 = new Date('2022-05-20').toLocaleDateString();
            const date2 = new Date('2022-05-21').toLocaleDateString();
            helper.assert(lot_with_date_1, `b1-b001 (${date1})`, 'lot line');
            helper.assert(lot_with_date_2, `b1-b002 (${date2})`, 'lot line');
        }
    },
    // The following scanned barcode should be decomposed like that:
    //      - (01)00000076543210    > product barcode (76543210)
    //      - (10)b1-b003           > lot (b1-b003)
    //      - (30)00000008          > quantity (8)
    //      - (15)220520            > best before date (5/20/2022)  not used
    //      - (17)220522            > expiration date (5/22/2022)   used
    {
        trigger: '.o_barcode_client_action',
        run: 'scan 010000007654321010b1-b003\x1D30000000081522052017220522',
    },
    {
        trigger: '.o_barcode_line:contains("b1-b003")',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertSublinesCount(3);
            const parentLine = helper.getLine({ barcode: "76543210" });
            const [line1, line2, line3] = helper.getSublines();
            helper.assertLineQty(parentLine, "20 / 20");
            helper.assertLineQty(line1, "8 / 20");
            helper.assertLineQty(line2, "4");
            helper.assertLineQty(line3, "8");
            helper.assertLineIsHighlighted(line1, false);
            helper.assertLineIsHighlighted(line2, false);
            helper.assertLineIsHighlighted(line3, true);
            const lot_with_date_1 = line1.querySelector('div[name="lot"]').innerText;
            const lot_with_date_2 = line2.querySelector('div[name="lot"]').innerText;
            const lot_with_date_3 = line3.querySelector('div[name="lot"]').innerText;
            const date1 = new Date('2022-05-20').toLocaleDateString();
            const date2 = new Date('2022-05-21').toLocaleDateString();
            const date3 = new Date('2022-05-22').toLocaleDateString();
            helper.assert(lot_with_date_1, `b1-b001 (${date1})`, 'lot line');
            helper.assert(lot_with_date_2, `b1-b002 (${date2})`, 'lot line');
            helper.assert(lot_with_date_3, `b1-b003 (${date3})`, 'lot line');
        }
    },
    ...stepUtils.validateBarcodeOperation(".o_validate_page"),
]});
