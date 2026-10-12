import { Plugin } from "@odoo/owl";
import { services } from "@web/core/services";

/**
 * OWL-native Plugin exposing Bootstrap 5's `getOrCreateInstance` as a shared,
 * ref-counted dependency (`usePlugin(BootstrapInstance)`): the same DOM
 * element can outlive a single owner (e.g. a popup surviving a builder
 * re-render), so a second, unrelated owner may obtain the same still-alive
 * instance before the first owner's teardown disposes it. `.dispose()` only
 * runs once every owner that obtained the instance has released its own
 * reference.
 */
export class BootstrapInstance extends Plugin {
    static id = "bootstrap";

    // Symbols (not plain static fields) so ref-count state is shared across
    // separate JS bundles that both load this module (e.g. the website
    // builder's iframe vs. the builder app itself) for the same Bootstrap
    // instance. Bootstrap's own `dispose()` nulls out own properties via
    // `Object.getOwnPropertyNames`, which ignores symbol keys, so this state
    // survives that too.
    static REF_COUNT = Symbol.for("web.core.utils.bootstrap_plugin.refCount");
    static DISPOSED = Symbol.for("web.core.utils.bootstrap_plugin.disposed");

    static scoped(self, scope) {
        const scoped = Object.create(self);
        scoped.cleanups = new Map();
        scoped.getOrCreateInstance = self.getOrCreateInstance.bind(scoped);
        scope.onDestroy(() => {
            for (const cleanup of [...scoped.cleanups.values()]) {
                cleanup();
            }
        });
        return scoped;
    }

    getOrCreateInstance(BsClass, el, config) {
        const instance = BsClass.getOrCreateInstance(el, config);
        if (!this.cleanups.has(instance)) {
            instance[BootstrapInstance.REF_COUNT] =
                (instance[BootstrapInstance.REF_COUNT] ?? 0) + 1;
            this.cleanups.set(instance, () => this.disposeBootstrapInstance(instance));
        }
        return instance;
    }

    getInstance(BsClass, el) {
        return BsClass.getInstance(el);
    }

    /**
     * Releases this owner's reference, disposing `instance` for real only
     * once every owner has released its own. Safe to call more than once, or
     * with an instance never obtained through `getOrCreateInstance` (disposed
     * right away, e.g. the result of `BsClass.getInstance(el)`).
     *
     * @param {Object} [instance] a Bootstrap 5 component instance
     * @param {Object} [options={}]
     * @param {boolean} [options.force=false] Dispose right now regardless of
     *     other owners still holding a reference — use when reconfiguring
     *     (e.g. a Carousel's `ride`/`pause`), since `getOrCreateInstance`
     *     would otherwise just hand back the still-alive old instance.
     */
    disposeBootstrapInstance(instance, { force = false } = {}) {
        if (!instance || instance[BootstrapInstance.DISPOSED]) {
            return;
        }
        this.cleanups?.delete(instance);
        if (!force) {
            const count = (instance[BootstrapInstance.REF_COUNT] ?? 1) - 1;
            if (count > 0) {
                instance[BootstrapInstance.REF_COUNT] = count;
                return;
            }
        }
        instance[BootstrapInstance.DISPOSED] = true;
        instance.dispose();
    }
}

services.add(BootstrapInstance);
