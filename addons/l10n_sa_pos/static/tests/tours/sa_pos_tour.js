/* global posmodel */

import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

// TODO replace by a Unit test once available
registry.category("web_tour.tours").add("test_sa_qr_in_right_timezone", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                content: "Test that the value given to the QR code contains the right timezone",
                trigger: "body",
                run: function () {
                    const qrEncoded = posmodel
                        .get_order()
                        .compute_sa_qr_code(
                            "SA Company",
                            "123456789012345",
                            "2025-03-07T10:15:17",
                            100.0,
                            0
                        );
                    const expected =
                        "AQpTQSBDb21wYW55Ag8xMjM0NTY3ODkwMTIzNDUDFDAzLzA3LzIwMjUsIDEzOjE1OjE3BAMxMDAFATA=";
                    if (qrEncoded !== expected) {
                        throw new Error(`
                            QR code mismatch: expected "${expected}", got "${qrEncoded}", make sure the timezone is respected`);
                    }
                },
            },
        ].flat(),
});
