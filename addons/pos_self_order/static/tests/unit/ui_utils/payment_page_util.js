import { waitFor } from "@odoo/hoot-dom";

export async function checkPaymentPage() {
    await waitFor(".payment-page");
}

export async function checkQRCodeGenerated() {
    await waitFor("h1:contains('Scan the QR code to pay')");
}
