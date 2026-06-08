import { LONG_PRESS_DURATION, TOUCH_DELAY } from "@point_of_sale/utils";

export function useLongPress(callback, delay = LONG_PRESS_DURATION) {
    let timer = null;

    function startLongPress(params, offset = 0) {
        timer = setTimeout(() => {
            callback(params);
        }, delay + offset);
    }

    function cancelLongPress() {
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
    }

    return {
        onMouseDown(event, params) {
            if (event.button === 0) {
                startLongPress(params);
            }
        },
        onMouseUp: cancelLongPress,
        onTouchStart(params) {
            startLongPress(params, TOUCH_DELAY);
        },
        onTouchEnd: cancelLongPress,
        onScroll: cancelLongPress,
    };
}
