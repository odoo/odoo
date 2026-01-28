import { Record } from "@mail/model/export";

export class Rating extends Record {
    static _name = "rating.rating";

    /** @type {number} */
    id;
    /** @type {number} */
    rating;
    /** @type {string} */
    rating_image_url;
    /** @type {string} */
    rating_text;
}
Rating.register();
