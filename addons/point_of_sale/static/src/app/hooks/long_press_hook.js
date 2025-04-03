import { useState } from "@odoo/owl";

export function useLongPress(callback, delay = 1000) {
    const state = useState({
        timer: null,
    });

    function startLongPress(params) {
        state.timer = setTimeout(() => {
            callback(params);
        }, delay);
    }

    function cancelLongPress() {
        if (state.timer) {
            clearTimeout(state.timer);
            state.timer = null;
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
            startLongPress(params);
        },
        onTouchEnd: cancelLongPress,
        onScroll: cancelLongPress,
    };
}
