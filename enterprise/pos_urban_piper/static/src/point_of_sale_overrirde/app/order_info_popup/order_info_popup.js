import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { getTime } from "@pos_urban_piper/utils";

export class orderInfoPopup extends Component {
    static components = { Dialog };
    static template = "pos_urban_piper.orderInfoPopup";
    static props = {
        order: Object,
        order_status: Object,
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.deliveryJson = JSON.parse(this.props.order.delivery_json || "{}");
        this.extPlatform = this.deliveryJson?.order?.details?.ext_platforms?.[0];
        this.store = this.deliveryJson?.order?.store;
        this.deliveryRiderJson = JSON.parse(this.props.order.delivery_rider_json || "{}");
        this.payment_option_display = {
            prepaid: _t("Prepaid"),
            payment_gateway: _t("Payment Gateway"),
            cash: _t("Cash"),
            card_on_delivery: _t("Card on Delivery"),
            paytm: _t("Paytm"),
            wallet_credit: _t("Wallet Credit"),
            simpl: _t("Simpl (Deferred Payment)"),
            aggregator: _t("Aggregator (Handled by Platform)"),
        };
        this.cardsData = [
            {
                title: _t("Delivery Person"),
                icon: "fa-motorcycle",
                visible: Boolean(this.props.order.delivery_rider_json),
                fields: [
                    {
                        label: _t("Name"),
                        value: this.deliveryRiderJson?.delivery_person_details?.name,
                    },
                    {
                        label: _t("Phone"),
                        value: this.deliveryRiderJson?.delivery_person_details?.phone,
                        link: `tel:${this.deliveryRiderJson?.delivery_person_details?.phone}`,
                    },
                    {
                        label: _t("Status"),
                        value: this.deliveryRiderJson?.status_updates?.[
                            this.deliveryRiderJson?.status_updates.length - 1
                        ]?.status,
                    },
                ],
            },
            {
                title: _t("Order Info"),
                icon: "fa-bookmark",
                visible: true,
                fields: [
                    {
                        label: _t("Status"),
                        value: this.props.order_status[this.props.order.delivery_status],
                    },
                    { label: _t("Fulfilment Mode"), value: this.getOrderDetails().fulfilmentMode },
                    {
                        label: _t("Channel"),
                        value: `${this.props.order.delivery_provider_id?.name} - ${
                            this.getOrderDetails().channelOtp
                        }`,
                    },
                    { label: _t("Outlet"), value: this.getOrderDetails().outletName },
                    { label: _t("Payment Mode"), value: this.getOrderDetails().paymentMode },
                    {
                        label: _t("Order Time"),
                        value: getTime(this.deliveryJson?.order?.details?.created),
                    },
                    {
                        label: _t("Delivery Time/Time-Slot"),
                        value: getTime(this.deliveryJson?.order?.details?.delivery_datetime),
                    },
                    ...(this.getOrderDetails().talabatCode
                        ? [{ label: _t("Talabat Code"), value: this.getOrderDetails().talabatCode }]
                        : []),
                    ...(this.getOrderDetails().talabatShortCode
                        ? [
                              {
                                  label: _t("Talabat Short Code"),
                                  value: this.getOrderDetails().talabatShortCode,
                              },
                          ]
                        : []),
                    ...(this.getOrderDetails().hungerstationCode
                        ? [
                              {
                                  label: _t("HungerStation Code"),
                                  value: this.getOrderDetails().hungerstationCode,
                              },
                          ]
                        : []),
                    { label: _t("Order ID"), value: this.props.order.delivery_identifier },
                    ...(this.getOrderDetails().orderOtp
                        ? [{ label: _t("Order OTP"), value: this.getOrderDetails().orderOtp }]
                        : []),
                ],
            },
            {
                title: _t("Customer Info"),
                icon: "fa-user",
                visible: true,
                fields: [
                    { label: _t("Customer Name"), value: this.props.order.partner_id.name },
                    {
                        label: _t("Delivery Address"),
                        value: `${this.props.order.partner_id.street || ""} ${
                            this.props.order.partner_id.city || ""
                        }`.trim(),
                    },
                    {
                        label: _t("Customer Phone"),
                        value: this.props.order.partner_id.phone,
                        link: `tel:${this.props.order.partner_id.phone}`,
                    },
                    {
                        label: _t("Customer Email"),
                        value: this.props.order.partner_id.email,
                        link: `mailto:${this.props.order.partner_id.email}`,
                    },
                ],
            },
        ];
    }

    onClose() {
        this.props.close();
    }

    getOrderDetails() {
        const orderDetails = {
            channelOtp: this.extPlatform?.id,
            orderOtp: this.extPlatform?.extras?.order_otp,
            fulfilmentMode: this.extPlatform?.delivery_type,
            outletName: this.store?.name,
            paymentMode:
                this.deliveryJson?.order?.payment
                    ?.map(
                        (payment) => this.payment_option_display[payment.option] || payment.option
                    )
                    ?.join(", ") || _t("Not Specified"),
        };
        const deliveryProvider = this.props?.order?.delivery_provider_id?.technical_name;
        if (deliveryProvider === "talabat") {
            orderDetails["talabatCode"] = this.extPlatform?.extras?.talabat_code;
            orderDetails["talabatShortCode"] = this.extPlatform?.extras?.talabat_shortcode;
        }
        if (deliveryProvider === "hungerstation") {
            orderDetails["hungerstationCode"] = this.extPlatform?.extras?.hungerstation_code;
        }
        return orderDetails;
    }
}
