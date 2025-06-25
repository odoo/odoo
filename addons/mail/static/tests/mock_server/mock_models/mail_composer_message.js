import { models } from "@web/../tests/web_test_helpers";
import { DEFAULT_MAIL_VIEW_ID } from "./constants";

export class MailComposeMessage extends models.ServerModel {
    _name = "mail.compose.message";
    _views = {
        [`form,${DEFAULT_MAIL_VIEW_ID}`]: `<form/>`,
    };
}
