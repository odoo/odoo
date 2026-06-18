import { fields, Record } from "@mail/model/export";

export class WebsiteTrack extends Record {
    static _name = "website.track";

    res_model = fields.Attr();
    res_id = fields.Attr();
    visit_datetime = fields.Datetime();

    /** @returns {string} */
    get resRecord() {
        if (!this.res_model || !this.res_id) {
            return undefined;
        }
        return this.store[this.res_model]?.get(this.res_id);
    }
}

WebsiteTrack.register();
