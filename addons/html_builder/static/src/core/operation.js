import { Mutex } from "@web/core/utils/concurrency";

// TODO when making apply async:
// - check `isDestroyed` instead of `this.editableDocument.defaultView`

/**
 * @typedef OperationParams
 * @property {Function} load an async function for which the mutex should wait
 *   before executing the main function
 * @property {Boolean} cancellable tells if the operation is cancellable (if it
 *   is a preview for example)
 * @property {Function} cancelPrevious the function to run when cancelling
 * @property {Number} [cancelTime=50] TODO
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
    }

    /**
     * Allows to execute a function in the mutex.
     * See `OperationParams.load` to make it async.
     *
     * @param {Function} fn the function
     * @param {OperationParams} params
     * @returns {Promise<void>}
     */
    next(
        fn,
        {
            load = () => Promise.resolve(),
            cancellable,
            cancelPrevious,
            cancelTime = 50,
            withLoadingEffect = true,
            loadingEffectDelay = 500,
            shouldInterceptClick = false,
        } = {}
    ) {
        this.cancelPrevious?.();
        let isCancel = false;
        let cancelResolve;
        this.cancelPrevious =
            cancellable &&
            (() => {
                this.cancelPrevious = null;
                isCancel = true;
                cancelResolve?.();
                // Cancel in the mutex to wait for the revert before the next
                // apply.
                this.mutex.exec(async () => {
                    await cancelPrevious?.();
                });
            });

        const cancelTimePromise = new Promise((resolve) => setTimeout(resolve, cancelTime));
        const cancelLoadPromise = new Promise((resolve) => {
            cancelResolve = resolve;
        });

        return this.mutex.exec(async () => {
            if (isCancel) {
                return;
            }

            const removeLoadingElement = this.addLoadingElement(
                withLoadingEffect,
                loadingEffectDelay,
                shouldInterceptClick
            );
            const applyOperation = async () => {
                const loadResult = await load();

                if (isCancel) {
                    return;
                }
                this.previousLoadResolve = null;

                // Cancel the operation if the iframe has been reloaded
                // and does not have a browsing context anymore.
                if (!this.editableDocument.defaultView) {
                    return;
                }

                await fn?.(loadResult);
            };

            try {
                await Promise.race([
                    Promise.all([cancelLoadPromise, cancelTimePromise]),
                    applyOperation(),
                ]);
            } finally {
                removeLoadingElement();
            }
        });
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
