export function fail(errorMessage) {
    throw new Error(errorMessage);
}

export function assert(current, expected, info) {
    if (current !== expected) {
        fail(`${info}: "${current}" instead of "${expected}".`);
    }
}

export function freezeDateTime(date, format = "yyyy-MM-dd HH:mm:ss") {
    return [
        {
            trigger: "body",
            run: () => {
                luxon.DateTime.now = () => luxon.DateTime.fromFormat(date, format);
            },
        },
    ];
}
