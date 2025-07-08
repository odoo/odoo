/** @odoo-module **/

import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { _t } from "@web/core/l10n/translation";
import { debounce } from "@web/core/utils/timing";
import { uuidv4 } from "@point_of_sale/utils";

export class PaymentAlipay extends PaymentInterface {
  setup() {
    super.setup(...arguments);
  }

  send_payment_request(cid) {
    super.send_payment_request(cid);
    return this._alipayPay(cid);
  }

  send_payment_cancel(order, cid) {
    super.send_payment_cancel(order, cid);
    clearTimeout(this.webhookTimeout);
    return this._alipayCancel();
  }

  close() {
    this.env.services.barcode_reader.bypassQR = false;
    super.close();
  }

  async _alipayPay(cid) {
    this.env.services.barcode_reader.bypassQR = true;
    const order = this.pos.get_order();
    const line = order.paymentlines.find(
      (paymentLine) => paymentLine.cid === cid
    );
    if (line.amount < 0) {
      this._showError(_t("Cannot process transactions with negative amount."));
      return false;
    }
    const data = this._alipayPayData();

    line.set_payment_status("waitingQr");
    const barcode = await this._pauseExecutionForQrScan();
    line.set_payment_status("waiting");
    data.paymentMethod.paymentMethodId = barcode;
    const res = await this._callAlipay(data, "pay");
    const onSuccess = async () => {
      line.set_payment_status("done");
      this.env.services.barcode_reader.bypassQR = false;
      return true;
    };
    const onUnknownError = async () => {
      return await this._alipayProcessingPayment();
    };
    return await this._alipayHandleResponse(res, onSuccess, onUnknownError);
  }

  _alipayPayData() {
    const order = this.pos.get_order();
    const line = order.selected_paymentline;
    line.paymentRequestId = `${order.uid}_${order.pos_session_id}_${
      line.payment_method.id
    }_${uuidv4()}`;

    const amount = (
      line.amount * Math.pow(10, this.pos.currency.decimal_places)
    ).toString();
    const currency = this.pos.currency.name;
    const { email: referenceMerchantId, name: merchantName } = this.pos.company;
    const { id: referenceStoreId, name: storeName } = this.pos.config;

    return {
      productCode: "IN_STORE_PAYMENT",
      paymentNotifyUrl:
        "https://26fb04f0966d-350717449223244319.ngrok-free.app/pos_alipay/notify",
      paymentRequestId: line.paymentRequestId,
      order: {
        referenceOrderId: order.uid,
        orderAmount: {
          currency,
          value: amount,
        },
        orderDescription: order.name,
        merchant: {
          referenceMerchantId,
          merchantName,
          store: {
            referenceStoreId: referenceStoreId.toString(),
            storeName,
          },
        },
      },
      paymentAmount: {
        currency,
        value: amount,
      },
      paymentMethod: {
        paymentMethodType: "CONNECT_WALLET",
        paymentMethodId: "",
      },
      paymentFactor: {
        inStorePaymentScenario: "PaymentCode",
      },
    };
  }

  async _pauseExecutionForQrScan() {
    const barcode = await new Promise((resolve) => {
      this.env.services.barcode.bus.addEventListener(
        "barcode_scanned",
        debounce(async (ev) => {
          resolve(ev.detail.barcode);
        }),
        1000
      );
    });
    return barcode;
  }

  async _alipayProcessingPayment() {
    const notification = await this._pauseExecutionFoWebhook();
    if (notification) {
      return notification;
    }
    const inquiry = await this._pauseExecutionForInquiryPayment();
    if (inquiry) {
      return inquiry;
    }
    const cancelResponse = await this._alipayCancel();
    if (cancelResponse) return false;

    const refundResponse = await this._alipayRefund(cancelResponse.paymentId);
    if (refundResponse) return false;

    this._showError(
      _t("Cancelling the payment failed. Please cancel it manually.")
    );
    return false;
  }

  async _pauseExecutionForInquiryPayment() {
    const payment = await this._alipayInquiryPayment();
    if (payment) return payment.paymentStatus === "SUCCESS";
    return false;
  }

  async _pauseExecutionFoWebhook() {
    const timeout = 5000;
    const data = await new Promise((resolve) => {
      this.webhookResolve = resolve;
      this.webhookTimeout = setTimeout(resolve, timeout);
    });
    return data
  }

  async alipayHandleNotification() {
    try {
      const data = await this.env.services.orm.silent.call(
        "pos.payment.method",
        "get_latest_alipay_status",
        [[this.payment_method.id]]
        );
        this.webhookResolve?.(data);
    } catch (_) {
      this.webhookResolve?.(false);
    }
  }

  async _alipayInquiryPayment() {
    const line = this._pendingAlipayLine();
    const queryData = {
      paymentRequestId: line.paymentRequestId,
    };
    const _inquiryPaymentPromise = async () => {
      const res = await this._callAlipay(queryData, "query", true);
      const onSuccess = async () => {
        if (res.paymentStatus === "SUCCESS") {
          line.set_payment_status("done");
          this.env.services.barcode_reader.bypassQR = false;
        } else if (["FAIL", "CANCELLED"].includes(res.paymentStatus)) {
          line.set_payment_status("retry");
        } else if (res.paymentStatus === "PROCESSING") {
          return false;
        }
        return res;
      };
      const onUnknownError = async () => false;
      const payment = await this._alipayHandleResponse(
        res,
        onSuccess,
        onUnknownError
      );
      return payment;
    };
    let payment = false;
    for (let i = 0; i < 25; i++) {
      payment = await Promise.all([
        _inquiryPaymentPromise(),
        new Promise((resolve) => setTimeout(resolve, 3000)),
      ]);
      payment = payment[0];
      if (payment) break;
    }
    return payment;
  }

  async _alipayCancel() {
    const line = this._pendingAlipayLine();
    if (!line) return false;

    line.set_payment_status("waitingCancel");
    const data = {
      paymentRequestId: line.paymentRequestId,
    };
    for (let i = 0; i < 3; i++) {
      const res = await this._callAlipay(data, "cancel");
      const onSuccess = async () => res;
      const onUnknownError = async () => false;
      const cancelResponse = await this._alipayHandleResponse(
        res,
        onSuccess,
        onUnknownError
      );
      if (cancelResponse) return cancelResponse;
      await new Promise((resolve) => setTimeout(resolve, 5000));
    }
    return false;
  }

  async _alipayRefund(paymentId) {
    const line = this._pendingAlipayLine();
    const data = {
      refundRequestId: `${line.paymentRequestId}_refund`,
      paymentId,
      refundAmount: {
        currency: this.pos.currency.name,
        value: line.amount,
      },
    };
    for (let i = 0; i < 3; i++) {
      const res = await this._callAlipay(data, "refund");
      const onSuccess = async () => res;
      const onUnknownError = async () => false;
      const refundResponse = await this._alipayHandleResponse(
        res,
        onSuccess,
        onUnknownError
      );
      if (refundResponse) return refundResponse;
      await new Promise((resolve) => setTimeout(resolve, 5000));
    }
    return false;
  }

  _pendingAlipayLine() {
    return this.pos.getPendingPaymentLine("alipay");
  }

  _callAlipay(data, operation = false, ignoreError = false) {
    return this.env.services.orm.silent
      .call("pos.payment.method", "proxy_alipay_request", [
        [this.payment_method.id],
        data,
        operation,
      ])
      .catch((error) => {
        if (ignoreError) return false;
        return this._handleOdooConnectionFailure(error);
      });
  }

  _handleOdooConnectionFailure(data = {}) {
    this._pendingAlipayLine()?.set_payment_status("retry");
    this._showError(
      _t(
        "Could not connect to the Odoo server, please check your internet connection and try again."
      )
    );

    return Promise.reject(data);
  }

  _showError(msg, title = _t("Alipay Error")) {
    this.pos.env.services.popup.add(ErrorPopup, {
      title: title,
      body: msg,
    });
  }

  async _alipayHandleResponse(res, onSuccess, onUnknownError) {
    if (!res || !res.result || res.result.resultStatus === "F") {
      const line = this._pendingAlipayLine();
      line.set_payment_status("retry");
      if (res && res.result && res.result.resultStatus === "F") {
        this._showError(
          _t(
            "An unexpected error occurred. Message from Alipay: %s",
            res.result.resultMessage
          )
        );
      }
      return false;
    }

    if (res.result.resultStatus === "S") {
      return await onSuccess();
    } else if (res.result.resultStatus === "U") {
      return await onUnknownError();
    }
  }
}
