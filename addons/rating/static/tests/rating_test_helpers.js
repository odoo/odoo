import { mailModels } from "@mail/../tests/mail_test_helpers";
import { MailMessage } from "@rating/../tests/mock_server/models/mail_message";
import { RatingRating } from "@rating/../tests/mock_server/models/rating_rating";

export const ratingModels = { ...mailModels, MailMessage, RatingRating };
