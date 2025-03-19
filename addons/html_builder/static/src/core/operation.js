import { Mutex } from "@web/core/utils/concurrency";

export class Operation {
    constructor() {
        this.mutex = new Mutex();
    }
    next(
        fn,
        { load = () => Promise.resolve(), cancellable, cancelPrevious, cancelTime = 50 } = {}
    ) {
        this.cancelPrevious?.();
        let isCancel = false;
        let cancelResolve;
        this.cancelPrevious =
            cancellable &&
            (() => {
                this.cancelPrevious = null;
                isCancel = true;
                cancelPrevious?.();
                cancelResolve?.();
            });

        const cancelTimePromise = new Promise((resolve) => setTimeout(resolve, cancelTime));
        const cancelLoadPromise = new Promise((resolve) => {
            cancelResolve = resolve;
        });

        return this.mutex.exec(async () => {
            if (isCancel) {
                return;
            }
            return Promise.race([
                Promise.all([cancelLoadPromise, cancelTimePromise]),
                load().then((loadResult) => {
                    if (isCancel) {
                        return;
                    }
                    this.previousLoadResolve = null;
                    fn?.(loadResult);
                }),
            ]);
        });
    }
}
