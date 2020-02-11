odoo.define('point_of_sale.utils', function(require) {
    'use strict';

    function getFileAsText(file) {
        return new Promise((resolve, reject) => {
            if (!file) {
                reject();
            } else {
                const reader = new FileReader();
                reader.addEventListener('load', function() {
                    resolve(reader.result);
                });
                reader.addEventListener('abort', reject);
                reader.addEventListener('error', reject);
                reader.readAsText(file);
            }
        });
    }

    function until(pred) {
        const poll = resolve => {
            if (pred()) resolve();
            else setTimeout(_ => poll(resolve), 70);
        };
        return new Promise(poll);
    }

    return { getFileAsText, until };
});
