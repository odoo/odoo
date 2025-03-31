import { Record } from "@mail/core/common/record";

export class Rating extends Record {
    static _name = "rating.rating";
    static id = "id";

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
