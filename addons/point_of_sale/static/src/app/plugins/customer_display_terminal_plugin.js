import { Plugin, signal, usePlugin } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";
import { rpc } from "@web/core/network/rpc";
import { formatCurrency } from "@web/core/currency";
import { getOnNotified, getColorScheme } from "@point_of_sale/utils";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

export const CONSOLE_COLOR = "#F5B427";
export const REGISTER_NOTIFICATION = "REGISTER_CUSTOMER_DISPLAY_DEVICE";

/**
 * Terminal half of the customer display: derives the payload from the current
 * order and dispatches it to the displays.
 *
 * Dispatching to nobody would cost a request per order change, so the terminal
 * keeps track of the displays that announced themselves and stays quiet while
 * none is connected. A display announces itself with `ADD` and leaves with
 * `REMOVE`; the terminal asks with `PING` when it starts, which every live
 * display answers with `ADD`, so a terminal that reloads still finds them.
 */
export class CustomerDisplayTerminalPlugin extends Plugin {
    /** Ids of the displays known to be listening. Empty means nobody is watching. */
    connectedDevices = signal.Set(new Set());

    orm = usePlugin(ORM);

    setup() {
        // Everything the terminal is given through `init`: the bus, the device
        // identifier, the models, the scale, the receipt data generator...
        // Kept in a single bag so new dependencies can be plugged in without
        // changing `init`'s signature.
        this.context = {};

        // Fallback communication channel used when the request fails (e.g. network loss).
        // NOTE: Works only between contexts within the same browser (tabs/windows sharing the same origin).
        this.channel = new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY");
    }

    /**
     * @param {Object} [context] - what this terminal talks with and for:
     *   `bus`, `identifier`, `configId`, `accessToken`, `models`, `scale`,
     *   `GeneratePrinterData` and `getQrData`. Called again to hand over late dependencies.
     */
    init(context = {}) {
        Object.assign(this.context, context);
        if (this.watching) {
            return;
        }
        this.watching = true;

        const { bus, accessToken, identifier } = this.context;
        getOnNotified(bus, accessToken)(
            `REGISTER_CUSTOMER_DISPLAY_DEVICE-${identifier}`,
            (message) => this.trackDevice(message)
        );
        // Displays opened before this terminal started have already announced
        // themselves; ask them to do it again.
        this.ping();
    }

    /**
     * Whether the terminal has everything it needs to derive a payload.
     */
    get isReady() {
        const { models, GeneratePrinterData } = this.context;
        return Boolean(models && GeneratePrinterData);
    }

    get hasConnectedDisplay() {
        return this.connectedDevices().size > 0;
    }

    /**
     * Handles an announcement coming from a display. Anything without a device
     * id is not a display talking (the terminal hears its own `PING` back).
     */
    trackDevice({ action, device_id }) {
        if (!device_id) {
            return;
        }
        if (action === "ADD") {
            this.connectedDevices().add(device_id);
        } else if (action === "REMOVE") {
            this.connectedDevices().delete(device_id);
        }
    }

    /**
     * Hook to extend the payload sent to the customer display.
     *
     * Override this method to customize the data derived from the order before
     * it is sent (e.g., add extra fields, metadata, or UI-specific flags).
     *
     * @param {Order} order - The current order instance.
     * @returns {Object} Data payload for the customer display.
     */
    _buildDisplayPayload(order) {
        const { models, GeneratePrinterData, getQrData } = this.context;
        const generator = new GeneratePrinterData({ models, order });
        const _formatCurrency = (amount) => formatCurrency(amount, order.currency.id);

        const orderData = generator.generateReceiptData();
        const scale = this.context.scale;

        return {
            ...orderData,
            qrData: getQrData?.() || null,
            displayScreenSaver: false,
            amountSettlements: order.remainingDueAmount !== order.totalDue && {
                label: order.remainingDueLabel,
                amount: _formatCurrency(Math.abs(order.remainingDueAmount)),
            },
            selectedLineUuid: order.uiState?.selected_orderline_uuid,
            displayTheme: getColorScheme(),
            scaleData: scale?.product && {
                productName: scale.product.name,
                unitPrice: scale.unitPriceString,
                totalPrice: scale.totalPriceString,
                netWeight: scale.netWeightString,
                grossWeight: scale.grossWeightString,
                tare: scale.tareWeightString,
                hardwareTare: scale.hardwareTare,
            },
        };
    }

    sendOrder(order) {
        if (!this.isReady || !this.hasConnectedDisplay) {
            return;
        }
        this.send(order ? this._buildDisplayPayload(order) : { clearData: true });
    }

    async send(payload) {
        // Checked here rather than in `sendOrder` so that every dispatch is
        // covered, including the screen saver and the validation flags which
        // are sent through `send` directly.
        if (!this.hasConnectedDisplay) {
            return;
        }
        const payloadStr = JSON.stringify(payload);
        try {
            await this.orm.call("pos.config", "update_customer_display", [
                [odoo.pos_config_id],
                payloadStr,
                this.context.identifier,
            ]);
        } catch (error) {
            logPosMessage(
                "CustomerDisplay",
                "dispatch",
                "Failed to update customer display",
                CONSOLE_COLOR,
                [error]
            );
            this.channel.postMessage(payloadStr);
        }
    }

    /**
     * Fallback discovery. An announcement can be missed: the display opened
     * while this terminal was offline, or its notification was lost. A new
     * order is a rare enough moment to ask again, so a connected display is
     * never left unnoticed for a whole session.
     */
    rediscoverDisplays() {
        if (!this.hasConnectedDisplay) {
            this.ping();
        }
    }

    /**
     * Asks the displays to announce themselves. The terminal is not a device,
     * so it sends no device id and ignores the echo of its own question.
     */
    ping() {
        const { configId, identifier, accessToken } = this.context;
        if (!configId || !identifier || !accessToken) {
            // The pos config is not loaded yet (booting on the login screen),
            // so there is no channel to ask on.
            return;
        }
        rpc("/pos_customer_display/register-device", {
            config_id: configId,
            identifier,
            access_token: accessToken,
            payload: { action: "PING" },
        }).catch((error) =>
            logPosMessage(
                "CustomerDisplay",
                "ping",
                "Failed to ask for connected customer displays",
                CONSOLE_COLOR,
                [error]
            )
        );
    }
}
