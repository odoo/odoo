import { fields, Record } from "@mail/model/export";

export class Rating extends Record {
    static _name = "rating.rating";

    /** @type {number} */
    id;
    message_id = fields.One("mail.message", { inverse: "rating_id" });
    /** @type {number} */
    rating;
    /** @type {string} */
    rating_image_url;
    /** @type {string} */
    rating_text;
}
Rating.register();
