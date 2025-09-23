import { describe, expect, test } from "@odoo/hoot";
import { computeSAQRCode } from "@l10n_sa_pos/app/utils/qr";

describe("SA QR Code", () => {
    test("check QR format", () => {
        const qrEncoded = computeSAQRCode(
            "SA Company",
            "123456789012345",
            "2025-03-07 10:15:17",
            100.0,
            0
        );
        const expected =
            "AQpTQSBDb21wYW55Ag8xMjM0NTY3ODkwMTIzNDUDFDAzLzA3LzIwMjUsIDEzOjE1OjE3BAMxMDAFATA=";

        expect(qrEncoded).toBe(expected, {
            message: `QR code mismatch: expected "${expected}", got "${qrEncoded}", make sure the timezone is respected`,
        });
    });
});
