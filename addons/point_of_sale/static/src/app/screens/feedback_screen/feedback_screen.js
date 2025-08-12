import { registry } from "@web/core/registry";
import { Component, useRef, onMounted, useEffect, useState, onWillUnmount } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class FeedbackScreen extends Component {
    static template = "point_of_sale.FeedbackScreen";
    static storeOnOrder = false;
    static components = { PriceFormatter };
    static props = {
        orderUuid: String,
        waitFor: { type: Object, optional: true },
        paymentMethodId: { type: Number, optional: true, default: null },
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.notification = useService("notification");
        this.containerRef = useRef("feedback-screen");
        this.amountRef = useRef("amount");
        this.state = useState({
            loading: true,
        });

        onMounted(() => {
            this.scaleText();
        });

        useEffect(
            () => {
                const waiter = async () => {
                    try {
                        if (this.props.waitFor) {
                            await this.props.waitFor;
                        }
                    } finally {
                        this.state.loading = false;
                        this.timeout = setTimeout(() => {
                            this.goToNextScreen();
                        }, 5000);
                    }
                };

                waiter();
            },
            () => []
        );

        onWillUnmount(() => {
            clearTimeout(this.timeout);
        });
    }

    scaleText() {
        const containerWidth = this.containerRef.el.offsetWidth * 0.8; // 80% of the container width to have some space on the sides
        const textWidth = this.amountRef.el.scrollWidth;

        const scale = Math.min(1, containerWidth / textWidth);
        this.amountRef.el.style.transform = `scale(${scale})`;
    }

    goToNextScreen() {
        const nextPage = this.pos.defaultPage;
        this.pos.navigate(nextPage.page, nextPage.params);
    }

    get currentOrder() {
        return this.pos.models["pos.order"].getBy("uuid", this.props.orderUuid);
    }

    onClick() {
        if (this.state.loading) {
            this.notification.add(
                _t("A request is still being processed in the background. Please wait."),
                {
                    type: "warning",
                }
            );
            return;
        }
        clearTimeout(this.timeout);
        this.goToNextScreen();
    }
}

registry.category("pos_pages").add("FeedbackScreen", {
    name: "FeedbackScreen",
    component: FeedbackScreen,
    route: `/pos/ui/${odoo.pos_config_id}/resume/{string:orderUuid}`,
    params: {},
});
