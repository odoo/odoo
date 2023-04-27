odoo.define('point_of_sale.utils', function (require) {
    'use strict';

    const { EventBus } = owl.core;

    function getFileAsText(file) {
        return new Promise((resolve, reject) => {
            if (!file) {
                reject();
            } else {
                const reader = new FileReader();
                reader.addEventListener('load', function () {
                    resolve(reader.result);
                });
                reader.addEventListener('abort', reject);
                reader.addEventListener('error', reject);
                reader.readAsText(file);
            }
        });
    }

    /**
     * This global variable is used by nextFrame to store the timer and
     * be able to cancel it before another request for animation frame.
     */
    let timer = null;

    /**
     * Wait for the next animation frame to finish.
     */
    const nextFrame = () => {
        return new Promise((resolve) => {
            cancelAnimationFrame(timer);
            timer = requestAnimationFrame(() => {
                resolve();
            });
        });
    };

    function isRpcError(error) {
        return (
            !(error instanceof Error) &&
            error.message &&
            [100, 200, 404, -32098].includes(error.message.code)
        );
    }

    return { getFileAsText, nextFrame, isRpcError, posbus: new EventBus() };
});
