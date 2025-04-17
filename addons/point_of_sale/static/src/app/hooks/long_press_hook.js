export function useLongPress(callback, delay = 1000) {
    let timer = null;

    function startLongPress(params) {
        timer = setTimeout(() => {
            callback(params);
        }, delay);
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
            startLongPress(params);
        },
        onTouchEnd: cancelLongPress,
        onScroll: cancelLongPress,
    };
}
