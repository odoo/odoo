import { Record } from "@mail/model/export";

export class WebsitePage extends Record {
    static _name = "website.page";

    /** @type {string} */
    name;
    /** @type {string} */
    url;
}

WebsitePage.register();
