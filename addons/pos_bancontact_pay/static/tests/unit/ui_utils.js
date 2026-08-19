import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { makeServerError, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import {
    clickDisplayedProduct,
    clickNumpad,
    clickPayButton,
    sendBufferKeys,
} from "@point_of_sale/../tests/unit/ui_utils";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";
import { PosPayment } from "@point_of_sale/../tests/unit/data/pos_payment.data";

export const DISPLAY = "Bancontact Display";
export const STICKER_1 = "Bancontact Sticker 1";
export const STICKER_2 = "Bancontact Sticker 2";

const BANCONTACT_METHOD_IDS = [4, 5, 6];
const QR_CODE = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==";
const HTTP_ERRORS = {
    401: ["Authentication with Bancontact failed. Please verify your API key.", "AccessDenied"],
    422: [
        "Unable to cancel payment. The payment may not be in a cancellable state.",
        "ValidationError",
    ],
    429: ["Rate limit reached with Bancontact. Please wait and try again.", "AccessDenied"],
};

function bancontactError(statusCode) {
    const [message, type] = HTTP_ERRORS[statusCode];
    return makeServerError({ message: `${message} (ERR: ${statusCode})`, type });
}

function isSuccess(statusCode) {
    return statusCode >= 200 && statusCode < 300;
}

function withoutNull(values) {
    if (Array.isArray(values)) {
        return values.map(withoutNull);
    }
    return Object.fromEntries(
        Object.entries(values).map(([key, value]) => [key, value === null ? false : value])
    );
}

function acceptClearedCharFields() {
    patchWithCleanup(PosPayment.prototype, {
        create(values, ...args) {
            return super.create(withoutNull(values), ...args);
        },
        write(ids, values, ...args) {
            return super.write(ids, withoutNull(values), ...args);
        },
    });
}

export function mockBancontactCall({
    prefix = "bancontact_",
    postStatusCode = 200,
    deleteStatusCode = 200,
} = {}) {
    let counter = -1;
    patchWithCleanup(PosPaymentMethod.prototype, {
        create_bancontact_payment() {
            counter++;
            if (!isSuccess(postStatusCode)) {
                throw bancontactError(postStatusCode);
            }
            return { bancontact_id: `${prefix}${counter}`, qr_code: QR_CODE };
        },
        cancel_bancontact_payment() {
            if (!isSuccess(deleteStatusCode)) {
                throw bancontactError(deleteStatusCode);
            }
        },
    });
}

export async function mockCallbackBancontactPay(store, bancontactId, status) {
    await store.handleBancontactPayNotification({
        bancontact_id: bancontactId,
        bancontact_status: status,
    });
    await animationFrame();
    await animationFrame();
}

export async function setupBancontactPos(mockOptions = {}) {
    const store = await setupAndMountPosApp({
        module_pos_restaurant: false,
        set_tip_after_payment: false,
        available_preset_ids: [],
        fast_payment_method_ids: [],
    });
    store.config.payment_method_ids = BANCONTACT_METHOD_IDS.map((id) =>
        store.models["pos.payment.method"].get(id)
    );
    store.models["product.template"].get(5).taxes_id = [];
    acceptClearedCharFields();
    mockBancontactCall(mockOptions);
    return store;
}

export async function initOrder() {
    await clickDisplayedProduct("TEST");
    await clickNumpad("Price");
    await sendBufferKeys("1", "0");
    await clickPayButton();
    await waitFor(".payment-screen");
}
