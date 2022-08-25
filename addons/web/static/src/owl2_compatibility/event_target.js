(function () {
    const { EventBus } = owl;

    function wrapCallback(owner, callback) {
        return (ev) => {
            callback.call(owner, ev.detail);
        };
    }

    owl.EventBus = class extends EventBus {
        constructor(...args) {
            super(...args);
            this.targetsCallbacks = new Map();
        }
        on(type, target, callback) {
            if (!this.targetsCallbacks.has(target)) {
                this.targetsCallbacks.set(target, []);
            }
            callback = wrapCallback(target, callback);
            this.targetsCallbacks.get(target).push(callback);
            return this.addEventListener(type, callback);
        }
        off(type, target) {
            const cbs = this.targetsCallbacks.get(target);
            if (!cbs) {
                return;
            }
            for (const callback of cbs) {
                this.removeEventListener(type, callback);
            }
        }
    };
})();
