export function throttle(fn, delay) {
    let timeout = null;

    return function (...args) {
        if (timeout === null) {
            fn(...args);
            timeout = setTimeout(() => {
                timeout = null;
            }, delay);
        }
    };
}
