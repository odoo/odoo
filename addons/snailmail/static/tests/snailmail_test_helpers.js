import { defineModels } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { IapAccount } from "@snailmail/../tests/mock_server/mock_model/iap_account";
import { SnailmailLetter } from "@snailmail/../tests/mock_server/mock_model/snailmail_letter";

export function defineSnailmailModels() {
    return defineModels(snailmailModels);
}

export const snailmailModels = { ...mailModels, IapAccount, SnailmailLetter };
