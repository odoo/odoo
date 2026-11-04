import { describe, expect, test } from "@odoo/hoot";
import { computeSAQRCode, renderQRCodeDataURL } from "@l10n_sa_pos/app/utils/qr";

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

    /**
     * Measure, in rendered pixels, the QR code a company of that name gets on its
     * receipt: the module pitch, the margin left around the code and the code itself.
     */
    function measureQRCode(companyName, size) {
        const values = computeSAQRCode(
            companyName,
            "311111111111113",
            "2025-03-07 10:15:17",
            100.0,
            15.0
        );
        const svg = new DOMParser().parseFromString(
            atob(renderQRCodeDataURL(values, size).split(",")[1]),
            "image/svg+xml"
        ).documentElement;
        // Without a viewBox the SVG units are already rendered pixels.
        const viewBox = svg.getAttribute("viewBox");
        const scale = viewBox
            ? parseFloat(svg.getAttribute("width")) / parseFloat(viewBox.split(" ")[2])
            : 1;
        const rects = [...svg.querySelectorAll("rect")];
        const pitch = parseFloat(rects[0].getAttribute("width"));
        const xs = rects.map((rect) => parseFloat(rect.getAttribute("x")));
        const margin = Math.min(...xs);
        return {
            pitch: pitch * scale,
            margin: margin * scale,
            code: (Math.max(...xs) + pitch - margin) * scale,
        };
    }

    // The ZATCA payload embeds the seller name, so a company with a long name needs a
    // bigger QR version. The code must still be drawn at the same size on the receipt.
    test("QR code size does not depend on the company name length", () => {
        const shortName = "Nadeem Cafe";
        const longName = "Golden Oasis Trading and Contracting Company Limited";
        // 150px on the receipt header, 200px on the printed receipt.
        for (const size of [150, 200]) {
            // Both names must leave exactly the 4-module quiet zone the QR spec
            // mandates, and nothing more: extra margin is the code shrinking in its box.
            for (const name of [shortName, longName]) {
                const { pitch, margin, code } = measureQRCode(name, size);
                expect(margin).toBe(4 * pitch, {
                    message: `"${name}" at ${size}px: expected a 4-module quiet zone of ${
                        4 * pitch
                    }px, got ${margin}px of margin`,
                });
                expect(code + 2 * margin).toBe(size, {
                    message: `"${name}" at ${size}px: the code and its quiet zone should fill the box`,
                });
            }
            // The longer payload needs more modules, so its code can only be bigger.
            expect(measureQRCode(longName, size).code).toBeGreaterThan(
                measureQRCode(shortName, size).code,
                { message: `at ${size}px: a longer company name shrank the printed QR code` }
            );
        }
    });
});
