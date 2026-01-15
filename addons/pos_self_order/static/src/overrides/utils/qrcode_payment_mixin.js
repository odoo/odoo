import { _t } from "@web/core/l10n/translation";

import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";

export function useQrcodePayment({ exclusive, onScan } = { onScan: () => {}, exclusive: false }) {
    const pos = usePos();
    const notification = useService("notification");
    const sound = useService("mail.sound_effects");

    useBarcodeReader(
        {
            order: async (code) => _barcodeOrderAction(code.uuid),
        },
        exclusive
    );

    async function _getOrderByUuid(code) {
        return pos.models["pos.order"].getBy("uuid", code);
    }

    async function _barcodeOrderAction(uuid) {
        const order = await _getOrderByUuid(uuid);
        if (!order) {
            sound.play("error");
            notification.add(
                _t("The Point of Sale could not find any order associated with the scanned order."),
                {
                    type: "warning",
                    title: _t(`Unknown Order`) + " " + uuid,
                }
            );
            return;
        }
        if (order.state !== "draft") {
            notification.add(
                _t("This order is already finalized. You cannot add it to the current order."),
                {
                    type: "warning",
                    title: _t(`Order Finalized`) + " " + uuid,
                }
            );
            return;
        }

        pos.setOrder(order);
        pos.pay();
    }
}
