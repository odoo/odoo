import { Record } from "@mail/model/export";
import { convertLineBreakToBr } from "@mail/utils/common/format";

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
    /** @type {string} */
    feedback;

    /** @returns {markup} */
    get markupFeedback() {
        return convertLineBreakToBr(this.feedback);
    }
}
Rating.register();
