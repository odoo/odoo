import { contains, mailModels } from "@mail/../tests/mail_test_helpers";
import { MailTestActivity } from "@test_mail/../tests/mock_server/models/mail_test_activity";
import { MailTestMultiCompany } from "@test_mail/../tests/mock_server/models/mail_test_multi_company";
import { MailTestMultiCompanyRead } from "@test_mail/../tests/mock_server/models/mail_test_multi_company_read";
import { MailTestProperties } from "@test_mail/../tests/mock_server/models/mail_test_properties";
import { MailTestSimple } from "@test_mail/../tests/mock_server/models/mail_test_simple";
import { MailTestTrackAll } from "@test_mail/../tests/mock_server/models/mail_test_track_all";
import { defineModels } from "@web/../tests/web_test_helpers";

const testMailModels = {
    ...mailModels,
    MailTestActivity,
    MailTestMultiCompany,
    MailTestMultiCompanyRead,
    MailTestProperties,
    MailTestSimple,
    MailTestTrackAll,
};

export function defineTestMailModels() {
    defineModels(testMailModels);
}

export async function editSelect(selector, value) {
    await contains(selector);
    const el = document.querySelector(selector);
    el.value = value;
    el.dispatchEvent(new Event("change"));
}
