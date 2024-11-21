import { ratingModels } from "@rating/../tests/rating_test_helpers";
import { MailTestRating } from "@test_mail_full/../tests/mock_server/models/mail_test_rating";
import { defineModels } from "@web/../tests/web_test_helpers";

export const testMailFullModels = { ...ratingModels, MailTestRating };

export function defineTestMailFullModels() {
    defineModels(testMailFullModels);
}
