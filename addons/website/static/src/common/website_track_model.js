import { fields, Record } from "@mail/model/export";

export class WebsiteTrack extends Record {
    static _name = "website.track";
    static id = "id";

    page_id = fields.One("website.page");
    visit_datetime = fields.Datetime();
}

WebsiteTrack.register();
