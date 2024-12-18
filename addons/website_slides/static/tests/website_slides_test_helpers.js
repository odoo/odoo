import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { SlideChannel } from "@website_slides/../tests/mock_server/models/slide_channel";
import { MailActivity } from "@website_slides/../tests/mock_server/models/mail_activity";

export const websiteSlidesModels = {
    ...mailModels,
    SlideChannel,
    MailActivity,
};

export function defineWebsiteSlidesModels() {
    defineModels(websiteSlidesModels);
}
