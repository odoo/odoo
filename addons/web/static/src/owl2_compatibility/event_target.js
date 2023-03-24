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
                this.targetsCallbacks.set(target, {});
            }
            callback = wrapCallback(target, callback);
            const listeners = this.targetsCallbacks.get(target);
            if (!listeners[type]) {
                listeners[type] = new Set();
            }
            listeners[type].add(callback);
            return this.addEventListener(type, callback);
        }
        off(type, target) {
            const listeners = this.targetsCallbacks.get(target);
            if (!listeners || !Object.hasOwnProperty.call(listeners, type)) {
                return;
            }
            const cbs = listeners[type];
            for (const callback of cbs) {
                this.removeEventListener(type, callback);
            }
            delete cbs[type];
            if (Object.keys(cbs).length === 0) {
                this.targetsCallbacks.delete(target);
            }
        }
    };
})();
