import { Plugin, t, useConfig } from "@odoo/owl";

export class StylesheetsPlugin extends Plugin {
    iframePromise = useConfig("iframePromise", t.promise());
    cardPromise = useConfig("cardPromise", t.promise());
}
