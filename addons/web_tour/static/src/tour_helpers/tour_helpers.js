export class TourHelpers {
    constructor(anchor) {
        this.anchor = anchor;
        this.delay = 20;
        return new Proxy(this, {
            get(target, prop, receiver) {
                const value = Reflect.get(target, prop, receiver);
                if (typeof value === "function" && prop !== "constructor") {
                    return value.bind(target);
                }
                return value;
            },
        });
    }
}
