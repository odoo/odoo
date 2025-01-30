/* global posmodel */
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";
const response_from_adyen_on_pos_webhook = (session, ServiceID) => ({
    SaleToPOIResponse: {
        MessageHeader: {
            MessageCategory: "Payment",
            MessageClass: "Service",
            MessageType: "Response",
            POIID: "my_adyen_terminal",
            ProtocolVersion: "3.0",
            SaleID: "Furniture Shop (ID: 1)",
            ServiceID,
        },
        PaymentResponse: {
            POIData: {
                POIReconciliationID: "1000",
                POITransactionID: {
                    TimeStamp: "2024-10-24T11:24:30.020Z",
                    TransactionID: "4eU8001729769070017.SD3Q9TMJJTSSM475",
                },
            },
            PaymentReceipt: [],
            PaymentResult: {
                AmountsResp: {
                    AuthorizedAmount: 1.04,
                    Currency: "USD",
                },
                CustomerLanguage: "en",
                OnlineFlag: true,
                PaymentAcquirerData: {
                    AcquirerPOIID: "P400Plus-275319618",
                    AcquirerTransactionID: {
                        TimeStamp: "2024-10-24T11:24:30.020Z",
                        TransactionID: "SD3Q9TMJJTSSM475",
                    },
                    ApprovalCode: "123456",
                    MerchantID: "OdooMP_POS",
                },
                PaymentInstrumentData: {
                    CardData: {
                        CardCountryCode: "826",
                        EntryMode: ["Contactless"],
                        MaskedPan: "541333 **** 9999",
                        PaymentBrand: "mc",
                        SensitiveCardData: {
                            CardSeqNumb: "33",
                            ExpiryDate: "0228",
                        },
                    },
                    PaymentInstrumentType: "Card",
                },
            },
            Response: {
                AdditionalResponse:
                    "useless=true&metadata.pos_hmac=ba6c62413839eb32030a3ee6400af4d367b8fb889b54ea85dffcb5a13625c318",
                Result: "Success",
            },
            SaleData: {
                SaleTransactionID: {
                    TimeStamp: "2024-10-24T11:24:29.000Z",
                    TransactionID: `921e7aa8-36b3-400c-a416-2b9a1eaf1283--${session}`,
                },
            },
        },
    },
});

registry.category("web_tour.tours").add("PosAdyenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Adyen"),
            {
                content: "Waiting for Adyen payment to be processed",
                trigger: ".electronic_status:contains('Waiting for card')",
                run: async function () {
                    const payment_terminal =
                        posmodel.getPendingPaymentLine("adyen").payment_method_id.payment_terminal;
                    // The fact that we are shown the `Waiting for card` status means that the
                    // request for payment has been sent to the adyen server ( in this case the mocked server )
                    // and the server replied with an `ok` response.
                    // As such, this is the time when we wait to receive the notification from adyen on the webhook
                    // The simplest way to mock this notification is to send it ourselves here.

                    // ==> pretend to be adyen and send the notification to the POS
                    const resp = await fetch("/pos_adyen/notification", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify(
                            response_from_adyen_on_pos_webhook(
                                posmodel.config.current_session_id.id,
                                payment_terminal.most_recent_service_id
                            )
                        ),
                    });
                    if (!resp.ok) {
                        throw new Error("Failed to notify Adyen webhook");
                    }
                },
            },

            ReceiptScreen.isShown(),
        ].flat(),
});
