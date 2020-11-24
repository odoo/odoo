odoo.define('l10n_de_pos_cert.utils', function(require) {
    'use strict';

    /*
     * comes from o_spreadsheet.js
     * https://stackoverflow.com/questions/105034/create-guid-uuid-in-javascript
     * */
    function uuidv4() {
        if (window.crypto && window.crypto.getRandomValues) {
            //@ts-ignore
            return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, (c) => (c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4)))).toString(16));
        }
        else {
            // mainly for jest and other browsers that do not have the crypto functionality
            return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
                let r = (Math.random() * 16) | 0, v = c == "x" ? r : (r & 0x3) | 0x8;
                return v.toString(16);
            });
        }
    };

    /*
     *  Convert a timestamp measured in seconds since the Unix epoch. String format returned YYYY-MM-DDThh:mm:ss
     */

    function convertFromEpoch(seconds) {
        return new Date(seconds * 1000).toISOString().substring(0,19).replace('T',' ');
    };

    return { uuidv4, convertFromEpoch };
});