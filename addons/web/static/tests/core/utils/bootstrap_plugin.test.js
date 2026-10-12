import { after, describe, expect, test } from "@odoo/hoot";
import { usePlugin } from "@odoo/owl";
import { startInteraction } from "@web/../tests/public/helpers";
import { Interaction } from "@web/public/interaction";
import { patch } from "@web/core/utils/patch";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

// `disposeBootstrapInstance` is meant to be called as
// `this.bootstrap.disposeBootstrapInstance(...)` from Interactions/Components
// via `usePlugin`, but tolerates a missing `this.cleanups` (no owner scope),
// only skipping the ref-count release step. Calling it via the prototype lets
// these standalone tests exercise the untracked-instance case without needing
// a real scope.
const disposeBootstrapInstance = (instance) =>
    BootstrapInstance.prototype.disposeBootstrapInstance(instance);

/**
 * Counts calls to `BsClass.prototype.dispose()` without altering its real
 * behavior, so these tests exercise the actual Bootstrap 5 dispose()/Data-map
 * semantics (e.g. a disposed instance is really removed from `BsClass.
 * getInstance(el)`) instead of a hand-rolled stand-in that could get that
 * subtly wrong.
 */
function trackDisposals(BsClass) {
    let count = 0;
    after(
        patch(BsClass.prototype, {
            dispose() {
                count++;
                super.dispose();
            },
        })
    );
    return () => count;
}

describe("BootstrapInstance plugin (usePlugin)", () => {
    test("creates and reuses the same instance for the same element", async () => {
        let instance1, instance2;
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.bootstrap = usePlugin(BootstrapInstance);
            }
            start() {
                instance1 = this.bootstrap.getOrCreateInstance(window.Carousel, this.el);
                instance2 = this.bootstrap.getOrCreateInstance(window.Carousel, this.el);
            }
        }

        await startInteraction(Test, `<div class="test carousel"></div>`);

        expect(instance1).toBe(instance2);
    });

    test("disposes the instance when the owner (Interaction) is destroyed", async () => {
        let el;
        const disposeCount = trackDisposals(window.Carousel);
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.bootstrap = usePlugin(BootstrapInstance);
            }
            start() {
                el = this.el;
                this.bootstrap.getOrCreateInstance(window.Carousel, this.el);
            }
        }

        const { core } = await startInteraction(Test, `<div class="test carousel"></div>`);
        expect(disposeCount()).toBe(0);

        core.stopInteractions();
        expect(disposeCount()).toBe(1);
        expect(window.Carousel.getInstance(el)).toBe(null);
    });

    test("keeps the instance alive for a second owner after the first owner is destroyed", async () => {
        // Regression test: the same DOM element (and Bootstrap instance) can
        // outlive a single owner, e.g. a popup surviving a builder
        // re-render. An owner destroyed early must not dispose an instance a
        // longer-lived owner obtained afterwards and is still using.
        let sharedEl;
        let instanceA, instanceB;
        const disposeCount = trackDisposals(window.Carousel);
        class OwnerA extends Interaction {
            static selector = ".owner-a";
            setup() {
                this.bootstrap = usePlugin(BootstrapInstance);
            }
            start() {
                sharedEl = this.el.querySelector(".shared");
                instanceA = this.bootstrap.getOrCreateInstance(window.Carousel, sharedEl);
            }
        }
        class OwnerB extends Interaction {
            static selector = ".owner-b";
            setup() {
                this.bootstrap = usePlugin(BootstrapInstance);
            }
            start() {
                instanceB = this.bootstrap.getOrCreateInstance(window.Carousel, sharedEl);
            }
        }

        const { core } = await startInteraction(
            [OwnerA, OwnerB],
            `<div class="owner-a"><div class="shared carousel"></div></div><div class="owner-b"></div>`
        );
        expect(instanceA).toBe(instanceB);

        core.stopInteractions(document.querySelector(".owner-a"));
        expect(disposeCount()).toBe(0);

        core.stopInteractions(document.querySelector(".owner-b"));
        expect(disposeCount()).toBe(1);
    });

    test("{ force: true } disposes right away even if another owner still holds a reference, so a fresh instance can be created with new options", async () => {
        // Regression test: two Interactions on the same element (e.g.
        // CarouselBootstrapUpgradeFix and CarouselSlider, both on the same
        // `.carousel`) each hold a reference to the same instance. When one
        // of them needs to *reconfigure* it (e.g. toggling pause/ride on
        // click), a plain release isn't enough: as long as the other owner
        // hasn't released its own reference, `BsClass.getOrCreateInstance`
        // would just hand back the still-alive old instance, silently
        // ignoring the new config. `{ force: true }` disposes it regardless,
        // so `getOrCreateInstance` creates a genuinely fresh one.
        let sharedEl;
        let instanceA;
        let ownerBBootstrap;
        class OwnerA extends Interaction {
            static selector = ".owner-a";
            setup() {
                this.bootstrap = usePlugin(BootstrapInstance);
            }
            start() {
                sharedEl = this.el.querySelector(".shared");
                instanceA = this.bootstrap.getOrCreateInstance(window.Carousel, sharedEl);
            }
        }
        class OwnerB extends Interaction {
            static selector = ".owner-b";
            setup() {
                this.bootstrap = usePlugin(BootstrapInstance);
                ownerBBootstrap = this.bootstrap;
            }
            start() {
                this.bootstrap.getOrCreateInstance(window.Carousel, sharedEl);
            }
        }

        await startInteraction(
            [OwnerA, OwnerB],
            `<div class="owner-a"><div class="shared carousel"></div></div><div class="owner-b"></div>`
        );

        const oldInstance = instanceA;
        ownerBBootstrap.disposeBootstrapInstance(oldInstance, { force: true });
        // OwnerA never released its own reference: without `force`, Bootstrap's
        // own Data map would still point to `oldInstance` here.
        expect(window.Carousel.getInstance(sharedEl)).toBe(null);

        const freshInstance = ownerBBootstrap.getOrCreateInstance(window.Carousel, sharedEl, {
            pause: true,
            ride: false,
        });
        expect(freshInstance).not.toBe(oldInstance);
    });

    test("shares ref-counting with a second, independent copy of the plugin (e.g. the website builder's preview iframe, which loads its own JS bundle and therefore its own copy of this module)", async () => {
        // Regression test: a class field on `BootstrapInstance` itself would
        // NOT be shared between two separate bundles both containing this
        // module (each gets its own copy of the class, hence its own static
        // fields), even though both may obtain the very same Bootstrap
        // instance for a DOM element shared across the iframe boundary (e.g.
        // `this.window.Modal.getOrCreateInstance(popupEl)` from the builder,
        // where `this.window` is the iframe's window). Simulate that second
        // copy by hand, without importing anything from bootstrap_plugin.js:
        // it must still interoperate correctly since it uses the same
        // `Symbol.for(...)` keys, shared across same-origin realms.
        const REF_COUNT = Symbol.for("web.core.utils.bootstrap_plugin.refCount");
        const DISPOSED = Symbol.for("web.core.utils.bootstrap_plugin.disposed");
        function makeOtherBundleCopy() {
            return {
                cleanups: new Map(),
                getOrCreateInstance(BsClass, el, config) {
                    const instance = BsClass.getOrCreateInstance(el, config);
                    if (!this.cleanups.has(instance)) {
                        instance[REF_COUNT] = (instance[REF_COUNT] ?? 0) + 1;
                        this.cleanups.set(instance, () => this.disposeBootstrapInstance(instance));
                    }
                    return instance;
                },
                disposeBootstrapInstance(instance) {
                    if (!instance || instance[DISPOSED]) {
                        return;
                    }
                    this.cleanups.delete(instance);
                    const count = (instance[REF_COUNT] ?? 1) - 1;
                    if (count > 0) {
                        instance[REF_COUNT] = count;
                        return;
                    }
                    instance[DISPOSED] = true;
                    instance.dispose();
                },
            };
        }

        const el = Object.assign(document.createElement("div"), { className: "carousel" });
        const disposeCount = trackDisposals(window.Carousel);
        let instanceA;
        class OwnerA extends Interaction {
            static selector = ".owner-a";
            setup() {
                this.bootstrap = usePlugin(BootstrapInstance);
            }
            start() {
                instanceA = this.bootstrap.getOrCreateInstance(window.Carousel, el);
            }
        }

        const { core } = await startInteraction(OwnerA, `<div class="owner-a"></div>`);

        const otherBundle = makeOtherBundleCopy();
        const instanceB = otherBundle.getOrCreateInstance(window.Carousel, el);
        expect(instanceA).toBe(instanceB);

        // The "other bundle" owner (e.g. the builder) releases its reference
        // first: since it doesn't know about OwnerA's reference (and vice
        // versa), the instance must survive.
        otherBundle.disposeBootstrapInstance(instanceB);
        expect(disposeCount()).toBe(0);

        // OwnerA's own teardown releases the last reference: only now is the
        // instance actually disposed, exactly once.
        core.stopInteractions();
        expect(disposeCount()).toBe(1);
    });

    test("does not queue a duplicate dispose() when called several times for the same instance", async () => {
        // Regression test: toggling a Bootstrap component (e.g. show/hide a
        // Modal) repeatedly used to call getOrCreateInstance once per
        // toggle, queuing one dispose() per call for the same instance. Some
        // Bootstrap components (e.g. Modal) are not safe to dispose() more
        // than once, so the instance must only be disposed once.
        const disposeCount = trackDisposals(window.Carousel);
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.bootstrap = usePlugin(BootstrapInstance);
            }
            start() {
                this.bootstrap.getOrCreateInstance(window.Carousel, this.el);
                this.bootstrap.getOrCreateInstance(window.Carousel, this.el);
                this.bootstrap.getOrCreateInstance(window.Carousel, this.el);
            }
        }

        const { core } = await startInteraction(Test, `<div class="test carousel"></div>`);
        core.stopInteractions();

        expect(disposeCount()).toBe(1);
    });
});

describe("disposeBootstrapInstance", () => {
    test("disposes the instance immediately", () => {
        const disposeCount = trackDisposals(window.Carousel);
        const el = Object.assign(document.createElement("div"), { className: "carousel" });
        const instance = window.Carousel.getOrCreateInstance(el);

        disposeBootstrapInstance(instance);

        expect(disposeCount()).toBe(1);
    });

    test("does not dispose an instance twice, even across the BootstrapInstance plugin", async () => {
        // Regression test: an owner's `hidden.bs.modal`-style handler may
        // dispose an instance right away, while some other owner already
        // holds a deferred dispose() for that same instance (registered via
        // the `BootstrapInstance` plugin). Whichever claims it first must be
        // the only one to actually call dispose().
        const disposeCount = trackDisposals(window.Carousel);
        let instance;
        class Test extends Interaction {
            static selector = ".test";
            setup() {
                this.bootstrap = usePlugin(BootstrapInstance);
            }
            start() {
                instance = this.bootstrap.getOrCreateInstance(window.Carousel, this.el);
            }
        }

        const { core } = await startInteraction(Test, `<div class="test carousel"></div>`);
        disposeBootstrapInstance(instance);
        expect(disposeCount()).toBe(1);

        // the interaction's teardown fires later: the instance is already gone.
        core.stopInteractions();
        expect(disposeCount()).toBe(1);
    });

    test("is a no-op the second time it is called for the same instance", () => {
        const disposeCount = trackDisposals(window.Carousel);
        const el = Object.assign(document.createElement("div"), { className: "carousel" });
        const instance = window.Carousel.getOrCreateInstance(el);

        disposeBootstrapInstance(instance);
        disposeBootstrapInstance(instance);

        expect(disposeCount()).toBe(1);
    });

    test("is a no-op when given a null or undefined instance", () => {
        // Callers typically pass the (possibly null) result of
        // `BsClass.getInstance(el)`, e.g. from a `hidden.bs.modal` handler
        // when no instance was ever created for that element.
        expect(() => disposeBootstrapInstance(null)).not.toThrow();
        expect(() => disposeBootstrapInstance(undefined)).not.toThrow();
    });
});
