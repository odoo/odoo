import { expect, test } from "@odoo/hoot";
import { mountWithCleanup, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("TicketBAI reprinted receipt QR encodes the url", async () => {
    const url = "https://tbai-receipt-url/1234";
    onRpc("pos.order", "get_l10n_es_pos_tbai_qrurl", () => url);
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await store.syncAllOrders();
    patchWithCleanup(store.ticketPrinter, { printOrderReceipt() {} });
    const ticketScreen = await mountWithCleanup(TicketScreen);
    await ticketScreen.print(order);
    const receipt = store.ticketPrinter.getOrderReceiptData(order);
    expect(order.uiState.l10n_es_pos_tbai_qrsrc).toBe(url);
    expect(receipt.image.l10n_es_pos_tbai_qrsrc).toBe(generateQRCodeDataUrl(url));
});
