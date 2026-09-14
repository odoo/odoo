/** @odoo-module native */
import { onWillDestroy } from "@odoo/owl";
import { LONG_PRESS_DURATION } from "@point_of_sale/utils";
import { makeLogger } from "@web/core/debug/debug_logger";
const log = makeLogger("pos.press.long");

export function useLongPress(callback, delay = LONG_PRESS_DURATION) {
    let timer = null;

    function startLongPress(params) {
        cancelLongPress();
        timer = setTimeout(() => {
            timer = null;
            log.logic("long press fired", () => ({
                delay,
                params: params?.id ?? params,
            }));
            callback(params);
        }, delay);
    }

    function cancelLongPress() {
        if (timer !== null) {
            log.lifecycle("long press canceled");
            clearTimeout(timer);
            timer = null;
        }
    }

    onWillDestroy(cancelLongPress);

    return {
        onMouseDown(event, params) {
            if (event.button === 0) {
                startLongPress(params);
            }
        },
        onMouseUp: cancelLongPress,
        onMouseLeave: cancelLongPress,
        onTouchStart(params) {
            startLongPress(params);
        },
        onTouchEnd: cancelLongPress,
        onTouchCancel: cancelLongPress,
        onScroll: cancelLongPress,
    };
}
