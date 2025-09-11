import { Deferred, delay, Mutex } from "@web/core/utils/concurrency";

// TODO when making apply async:
// - check `isDestroyed` instead of `this.editableDocument.defaultView`

/**
 * @typedef OperationParams
 * @property {Function?} load an async function called before taking the mutex,
 *   whose result is given to the operation's main function
 * @property {Function?} cancel the function to run when cancelling. If truthy,
 *   the operation is cancellable, and `fn` and `load` may not be called if the
 *   operation is cancelled (which happens when another operation is scheduled)
 * @property {Number} [loadCost=50] the number of millisecond to delay the
 *   cancel of a load (if the load does not finish). This avoids starting too
 *   many concurrent loads
 * @property {Boolean} [withLoadingEffect=true] specifies if a spinner should
 *   appear on the editable during the operation
 * @property {Number} [loadingEffectDelay=500] the delay after which the
 *   spinner should appear
 * @property {Boolean} [shouldInterceptClick=false] whether clicking while the
 *   loading screen is present should retarget the click at the end of the
 *   loading time.
 */

export class Operation {
    constructor(editableDocument = document) {
        this.mutex = new Mutex();
        this.editableDocument = editableDocument;
        this.cancellableLoadLimiter = new Mutex();
    }

    /**
     * Allows to execute a function in the mutex.
     *
     * @param {Function} fn the function
     * @param {OperationParams} params
     * @returns {Promise<void>}
     */
    next(
        fn,
        {
            load,
            cancel,
            loadCost = 50,
            withLoadingEffect = true,
            loadingEffectDelay = 500,
            shouldInterceptClick = false,
        } = {}
    ) {
        this.stopPrevious?.resolve();

        const cancelPrevious = this.cancelPrevious ?? (() => Promise.resolve());
        const stopPromise = new Deferred();
        let stopped = false;

        let loadPromise;
        if (cancel) {
            stopPromise.then(() => (stopped = true));
            this.stopPrevious = stopPromise;

            let cancelled = false;
            this.cancelPrevious = async () => {
                if (!cancelled) {
                    cancelled = true;
                    await cancelPrevious().catch(() => {});
                    await cancel();
                }
            };

            loadPromise = load
                ? this.cancellableLoadLimiter.exec(
                      () =>
                          stopped ||
                          Promise.race([Promise.all([stopPromise, delay(loadCost)]), load()])
                  )
                : Promise.resolve();
        } else {
            delete this.stopPrevious;
            delete this.cancelPrevious;
            loadPromise = load?.();
        }

        const work = this.mutex.exec(async () => {
            if (stopped) {
                return;
            }
            const removeLoadingElement = this.addLoadingElement(
                withLoadingEffect,
                loadingEffectDelay,
                shouldInterceptClick
            );
            try {
                const loadResult = await Promise.race([stopPromise, loadPromise]);
                if (stopped) {
                    return;
                }

                await cancelPrevious().catch(() => {});

                // Cancel the operation if the iframe has been reloaded
                // and does not have a browsing context anymore.
                if (!this.editableDocument.defaultView) {
                    return;
                }

                await fn?.(loadResult);
            } finally {
                removeLoadingElement();
            }
        });
        return Promise.race([stopPromise, work]);
    }

    /**
     * Adds a transparent loading screen above the editable to prevent modifying
     * its content during an ongoing operation. Returns a callback to remove
     * the loading screen.
     *
     * @param {Boolean} withLoadingEffect if true, adds a loading effect
     * @param {Number} loadingEffectDelay delay after which the loading effect
     *   should appear
     * @param {Boolean} shouldInterceptClick - whether to redispatch the click
     *   under the loading element after the end of the current operation
     * @returns {Function}
     */
    addLoadingElement(withLoadingEffect, loadingEffectDelay, shouldInterceptClick) {
        const loadingScreenEl = document.createElement("div");
        loadingScreenEl.classList.add(
            ...["o_loading_screen", "d-flex", "justify-content-center", "align-items-center"]
        );
        const spinnerEl = document.createElement("img");
        spinnerEl.setAttribute("src", "/web/static/img/spin.svg");
        loadingScreenEl.appendChild(spinnerEl);

        let removeClickListener = () => {};
        if (shouldInterceptClick) {
            const onClick = (ev) => {
                const trueTargetEls = this.editableDocument.elementsFromPoint(
                    ev.clientX,
                    ev.clientY
                );
                this.next(() => {
                    for (const trueTargetEl of trueTargetEls) {
                        if (trueTargetEl.isConnected) {
                            trueTargetEl.click();
                            break;
                        }
                    }
                });
            };
            this.editableDocument.addEventListener("click", onClick);
            removeClickListener = () => this.editableDocument.removeEventListener("click", onClick);
        }

        this.editableDocument.body.appendChild(loadingScreenEl);

        // If specified, add a loading effect on that element after a delay.
        let loadingTimeout;
        if (withLoadingEffect) {
            loadingTimeout = setTimeout(
                () => loadingScreenEl.classList.add("o_we_ui_loading"),
                loadingEffectDelay
            );
        }

        return () => {
            if (loadingTimeout) {
                clearTimeout(loadingTimeout);
            }
            removeClickListener();
            loadingScreenEl.remove();
        };
    }
}
