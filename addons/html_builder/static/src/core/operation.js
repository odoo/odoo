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
 * @property {Boolean} [canTimeout=true]
 * @property {Number} [timeout=10000]
 */

export class OperationMutex extends Mutex {
    constructor() {
        super();
        this._skipUntilEmpty = false;
    }

    clearQueue() {
        this._skipUntilEmpty = this._queueSize > 0;
        if (this._skipUntilEmpty) {
            this.getUnlockedDef().then(() => {
                this._skipUntilEmpty = false;
            });
        }
    }

    async exec(action) {
        return super.exec(() => {
            if (this._skipUntilEmpty) {
                return;
            }
            return action();
        });
    }
}

export class Operation {
    constructor(editableDocument = document) {
        this.mutex = new OperationMutex();
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
            canTimeout = true,
            timeout = 10000,
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

        let hasTimedOut = false;
        return this.mutex.exec(async () => {
            if (isCancel) {
                return;
            }
            let cancelTimeoutPromise;
            if (canTimeout) {
                cancelTimeoutPromise = new Promise((resolve) => {
                    setTimeout(() => {
                        hasTimedOut = true;
                        resolve();
                    }, timeout);
                });
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
                const promises = [
                    Promise.all([cancelLoadPromise, cancelTimePromise]),
                    applyOperation(),
                ];
                if (cancelTimeoutPromise) {
                    promises.push(cancelTimeoutPromise);
                }
                await Promise.race(promises);
            } finally {
                if (hasTimedOut) {
                    this.mutex.clearQueue();
                }
                removeLoadingElement();
            }
            return { hasFailed: hasTimedOut };
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
