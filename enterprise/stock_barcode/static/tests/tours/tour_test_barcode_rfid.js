/** @odoo-module */

import * as helper from "./tour_helper_stock_barcode";
import { registry } from "@web/core/registry";
import { stepUtils } from "./tour_step_utils";

registry.category("web_tour.tours").add("test_rfid_inventory_scan_sgtin", { steps: () => [
    { trigger: ".o_button_inventory", run: "click" },
    // Scan a first batch of RFID (51), should causes a RPC.
    {
        trigger: ".o_barcode_client_action",
        run: "scanRFID " + [
            // 20 French wine RFID.
            "urn:epc:id:sgtin:230000.0100008.20",
            "urn:epc:id:sgtin:230000.0100008.0",
            "urn:epc:id:sgtin:230000.0100008.12",
            "urn:epc:id:sgtin:230000.0100008.21",
            "urn:epc:id:sgtin:230000.0100008.9",
            "urn:epc:id:sgtin:230000.0100008.14",
            "urn:epc:id:sgtin:230000.0100008.13",
            "urn:epc:id:sgtin:230000.0100008.3",
            "urn:epc:id:sgtin:230000.0100008.16",
            "urn:epc:id:sgtin:230000.0100008.1",
            "urn:epc:id:sgtin:230000.0100008.18",
            "urn:epc:id:sgtin:230000.0100008.6",
            "urn:epc:id:sgtin:230000.0100008.11",
            "urn:epc:id:sgtin:230000.0100008.5",
            "urn:epc:id:sgtin:230000.0100008.22",
            "urn:epc:id:sgtin:230000.0100008.17",
            "urn:epc:id:sgtin:230000.0100008.4",
            "urn:epc:id:sgtin:230000.0100008.8",
            "urn:epc:id:sgtin:230000.0100008.19",
            "urn:epc:id:sgtin:230000.0100008.10",
            // 2 Lunch box RFID.
            "urn:epc:id:sgtin:230000.0100001.1",
            "urn:epc:id:sgtin:230000.0100001.2",
            // 4 Japanese wine RFID.
            "urn:epc:id:sgtin:230000.0100012.1",
            "urn:epc:id:sgtin:230000.0100012.7",
            "urn:epc:id:sgtin:230000.0100012.4",
            "urn:epc:id:sgtin:230000.0100012.2",
            // 10 Large plate RFID.
            "urn:epc:id:sgtin:546812.0300123.29",
            "urn:epc:id:sgtin:546812.0300123.22",
            "urn:epc:id:sgtin:546812.0300123.2",
            "urn:epc:id:sgtin:546812.0300123.11",
            "urn:epc:id:sgtin:546812.0300123.18",
            "urn:epc:id:sgtin:546812.0300123.24",
            "urn:epc:id:sgtin:546812.0300123.8",
            "urn:epc:id:sgtin:546812.0300123.10",
            "urn:epc:id:sgtin:546812.0300123.19",
            "urn:epc:id:sgtin:546812.0300123.12",
            // 8 Inox knife RFID.
            "urn:epc:id:sgtin:546812.0300246.4",
            "urn:epc:id:sgtin:546812.0300246.7",
            "urn:epc:id:sgtin:546812.0300246.2",
            "urn:epc:id:sgtin:546812.0300246.5",
            "urn:epc:id:sgtin:546812.0300246.6",
            "urn:epc:id:sgtin:546812.0300246.0",
            "urn:epc:id:sgtin:546812.0300246.1",
            "urn:epc:id:sgtin:546812.0300246.3",
            // 3 Handmade argyle plate RFID.
            "urn:epc:id:sgtin:876543.0210000.00128",
            "urn:epc:id:sgtin:876543.0210000.00129",
            "urn:epc:id:sgtin:876543.0210000.00130",
            // 4 Chief suit RFID.
            "urn:epc:id:sgtin:876543.0230004.12",
            "urn:epc:id:sgtin:876543.0230004.9",
            "urn:epc:id:sgtin:876543.0230004.15",
            "urn:epc:id:sgtin:876543.0230004.11",
        ],
    },
    ...stepUtils.countUniqRFID(51),
    ...stepUtils.countTotalRFID(51),
    ...stepUtils.closeCountRFID(),
    {
        trigger: ".o_barcode_line .qty-done:contains(20)",
        run: () => {
            helper.assertLinesCount(7);
            helper.assertLineProduct(0, "French wine");
            helper.assertLineQty(0, "20");
            helper.assertLineProduct(1, "Lunch box");
            helper.assertLineQty(1, "2/12");
            helper.assertLineProduct(2, "Japanese wine");
            helper.assertLineQty(2, "4");
            helper.assertLineProduct(3, "Large plate");
            helper.assertLineQty(3, "10/35");
            helper.assertLineProduct(4, "Inox knife");
            helper.assertLineQty(4, "8/11");
            helper.assertLineProduct(5, "Handmade argyle plate");
            helper.assertLineQty(5, "3/3");
            helper.assertLineProduct(6, "Chief suit");
            helper.assertLineQty(6, "4/3");
        },
    },
    // Scan a second batch of RFID. A RPC is done for missing SN.
    // TODO: Ideally, once product's quants were fetched, no more RPC are needed
    // for this product and product's LN/SN. Need to find a way to not fetch
    // data for missing SN when quants already fetched.
    {
        trigger: ".o_barcode_client_action",
        run: "scanRFID " + [
            // 4 French wine RFID.
            "urn:epc:id:sgtin:230000.0100008.23",
            "urn:epc:id:sgtin:230000.0100008.2",
            "urn:epc:id:sgtin:230000.0100008.7",
            "urn:epc:id:sgtin:230000.0100008.15",
            // 8 Lunch box RFID.
            "urn:epc:id:sgtin:230000.0100001.3",
            "urn:epc:id:sgtin:230000.0100001.4",
            "urn:epc:id:sgtin:230000.0100001.5",
            "urn:epc:id:sgtin:230000.0100001.6",
            "urn:epc:id:sgtin:230000.0100001.7",
            "urn:epc:id:sgtin:230000.0100001.8",
            "urn:epc:id:sgtin:230000.0100001.9",
            "urn:epc:id:sgtin:230000.0100001.10",
            // 4 Japanese wine RFID.
            "urn:epc:id:sgtin:230000.0100012.3",
            "urn:epc:id:sgtin:230000.0100012.5",
            "urn:epc:id:sgtin:230000.0100012.6",
            "urn:epc:id:sgtin:230000.0100012.0",
            // 25 Large plate RFID.
            "urn:epc:id:sgtin:546812.0300123.34",
            "urn:epc:id:sgtin:546812.0300123.31",
            "urn:epc:id:sgtin:546812.0300123.28",
            "urn:epc:id:sgtin:546812.0300123.3",
            "urn:epc:id:sgtin:546812.0300123.23",
            "urn:epc:id:sgtin:546812.0300123.14",
            "urn:epc:id:sgtin:546812.0300123.4",
            "urn:epc:id:sgtin:546812.0300123.33",
            "urn:epc:id:sgtin:546812.0300123.21",
            "urn:epc:id:sgtin:546812.0300123.5",
            "urn:epc:id:sgtin:546812.0300123.1",
            "urn:epc:id:sgtin:546812.0300123.13",
            "urn:epc:id:sgtin:546812.0300123.0",
            "urn:epc:id:sgtin:546812.0300123.25",
            "urn:epc:id:sgtin:546812.0300123.26",
            "urn:epc:id:sgtin:546812.0300123.6",
            "urn:epc:id:sgtin:546812.0300123.30",
            "urn:epc:id:sgtin:546812.0300123.20",
            "urn:epc:id:sgtin:546812.0300123.27",
            "urn:epc:id:sgtin:546812.0300123.15",
            "urn:epc:id:sgtin:546812.0300123.16",
            "urn:epc:id:sgtin:546812.0300123.7",
            "urn:epc:id:sgtin:546812.0300123.9",
            "urn:epc:id:sgtin:546812.0300123.17",
            "urn:epc:id:sgtin:546812.0300123.32",
            // 2 Handmade argyle plate RFID.
            "urn:epc:id:sgtin:876543.0210000.00131",
            "urn:epc:id:sgtin:876543.0210000.00132",
            // 3 Chief suit RFID.
            "urn:epc:id:sgtin:876543.0230004.10",
            "urn:epc:id:sgtin:876543.0230004.16",
            "urn:epc:id:sgtin:876543.0230004.7",
        ],
    },
    ...stepUtils.countUniqRFID(97),
    ...stepUtils.countTotalRFID(97),
    ...stepUtils.closeCountRFID(),
    {
        trigger: ".o_barcode_line .qty-done:contains(24)",
        run: () => {
            helper.assertLinesCount(7);
            helper.assertLineProduct(0, "French wine");
            helper.assertLineQty(0, "24");
            helper.assertLineProduct(1, "Lunch box");
            helper.assertLineQty(1, "10/12");
            helper.assertLineProduct(2, "Japanese wine");
            helper.assertLineQty(2, "8");
            helper.assertLineProduct(3, "Large plate");
            helper.assertLineQty(3, "35/35");
            helper.assertLineProduct(4, "Inox knife");
            helper.assertLineQty(4, "8/11");
            helper.assertLineProduct(5, "Handmade argyle plate");
            helper.assertLineQty(5, "5/5");
            helper.assertLineProduct(6, "Chief suit");
            helper.assertLineQty(6, "7/5");
        },
    },
]});
