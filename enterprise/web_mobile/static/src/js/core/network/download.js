/** @odoo-module **/

import mobile from "@web_mobile/js/services/core";
import { download } from "@web/core/network/download";

const _download = download._download;

download._download = async function (options) {
    if (mobile.methods.downloadFile) {
        if (odoo.csrf_token) {
            options.csrf_token = odoo.csrf_token;
        }
        mobile.methods.downloadFile(options);
        // There is no need to wait downloadFile because we delegate this to
        // Download Manager Service where error handling will be handled correclty.
        // On our side, we do not want to block the UI and consider the request
        // as success.
        return Promise.resolve();
    } else {
        return _download.apply(this, arguments);
    }
};
