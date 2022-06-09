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
            this.targetsCallbacks = new WeakMap();
        }
        on(type, target, callback) {
            const _callback = wrapCallback(target, callback);
            if (!target) {
                return this.addEventListener(type, _callback);
            }
            if (!this.targetsCallbacks.has(target)) {
                this.targetsCallbacks.set(target, []);
            }
            this.targetsCallbacks.get(target).push({ type, callback: _callback });
            return this.addEventListener(type, callback);
        }
        off(type, target) {
            if (!target) {
                console.warn("unable to remove handlers: invalid target");
                return;
            }
            const cbs = this.targetsCallbacks.get(target);
            if (!cbs) {
                return;
            }
            const newCbs = cbs.filter((cb) => {
                if (cb.type === type) {
                    this.removeEventListener(cb.type, cb.callback);
                    return false;
                }
                return true;
            });
            if (newCbs.length) {
                this.targetsCallbacks.set(target, newCbs);
            } else {
                this.targetsCallbacks.delete(target);
            }
        }
    };
})();
