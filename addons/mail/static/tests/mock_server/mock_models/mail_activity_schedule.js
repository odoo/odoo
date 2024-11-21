import { models } from "@web/../tests/web_test_helpers";
import { DEFAULT_MAIL_SEARCH_ID, DEFAULT_MAIL_VIEW_ID } from "./constants";

export class MailActivitySchedule extends models.ServerModel {
    _name = "mail.activity.schedule";
    _views = {
        [`search, ${DEFAULT_MAIL_SEARCH_ID}`]: `<search/>`,
        [`form, ${DEFAULT_MAIL_VIEW_ID}`]: `<form/>`,
    };
}
