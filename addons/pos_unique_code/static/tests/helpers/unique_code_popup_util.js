const POPUP = ".modal .pos-unique-code-popup";

// Scoped to the popup: the screen behind it has a numpad of its own.
export function enterCode(code) {
    return code.split("").map((digit) => ({
        content: `click code digit: ${digit}`,
        trigger: `${POPUP} div.numpad button:contains(/^${digit}$/)`,
        run: "click",
    }));
}

// The code is typed on a keyboard instead of tapped on the numpad.
export function typeCode(code) {
    return {
        content: `type code: ${code}`,
        trigger: `${POPUP} .unique-code-field`,
        run: `edit ${code}`,
    };
}

export function codeIs(code) {
    return code.split("").map((digit, index) => ({
        content: `code box ${index} shows ${digit}`,
        trigger: `${POPUP} .unique-code-digit:eq(${index}):contains(/^${digit}$/)`,
    }));
}

export function confirm() {
    return {
        content: "confirm the order code",
        trigger: `${POPUP} .unique-code-confirm:enabled`,
        run: "click",
    };
}

export function forceValidate() {
    return {
        content: "validate without an order code",
        trigger: `${POPUP} .unique-code-force`,
        run: "click",
    };
}

// A refused code stays on screen, turns red and is explained in place -- no notification.
export function isRejected(message) {
    return [
        {
            content: `the code is refused: ${message}`,
            trigger: `${POPUP} .unique-code-error:contains('${message}')`,
        },
        {
            content: "the code boxes are red",
            trigger: `${POPUP} .unique-code-digit.border-danger`,
        },
    ];
}
