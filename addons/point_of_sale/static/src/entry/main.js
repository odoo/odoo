/** @odoo-module */

import { startWebClient } from "@web/start";
import { Chrome } from "@point_of_sale/js/Chrome";
import { Loader } from "@point_of_sale/app/loader/loader";
import { templates } from "@web/core/assets";
import { mount, reactive, whenReady } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

const loader = reactive({ isShown: true });
whenReady(() => {
    // Show loader as soon as the page is ready, do not wait for services to be started
    // as some services load data over RPC and this is why we want to show a loader.
    mount(Loader, document.body, { templates, translateFn: _t, props: { loader } });
});
// FIXME POSREF stop using startWebclient?: this is not a web client.
startWebClient(Chrome, { disableLoader: () => (loader.isShown = false) });
