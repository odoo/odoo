import { fields, Record } from "@mail/model/export";

export class WebsiteTrack extends Record {
    static _name = "website.track";

    page_id = fields.One("website.page");
    /** @type {string} */
    url;
    visit_datetime = fields.Datetime();
}

WebsiteTrack.register();
