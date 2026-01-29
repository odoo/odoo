// @odoo-module ignore
if (!Promise.withResolvers) {
    Promise.withResolvers = function withResolvers() {
        let resolve, reject;
        const promise = new Promise((res, rej) => {
            resolve = res;
            reject = rej;
        });
        return { promise, resolve, reject };
    };
}
