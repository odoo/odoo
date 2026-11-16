import { contains, mailModels } from "@mail/../tests/mail_test_helpers";
import { MailTestActivity } from "@test_mail/../tests/mock_server/models/mail_test_activity";
import { MailTestMultiCompany } from "@test_mail/../tests/mock_server/models/mail_test_multi_company";
import { MailTestMultiCompanyRead } from "@test_mail/../tests/mock_server/models/mail_test_multi_company_read";
import { MailTestProperties } from "@test_mail/../tests/mock_server/models/mail_test_properties";
import { MailTestRottingResource } from "@test_mail/../tests/mock_server/models/mail_test_rotting_resource";
import { MailTestRottingStage } from "@test_mail/../tests/mock_server/models/mail_test_rotting_stage";
import { MailTestSimpleMainAttachment } from "./mock_server/models/mail_test_simple_main_attachment";
import { MailTestSimple } from "@test_mail/../tests/mock_server/models/mail_test_simple";
import { MailTestTrackAll } from "@test_mail/../tests/mock_server/models/mail_test_track_all";
import { defineModels, defineParams } from "@web/../tests/web_test_helpers";

export const testMailModels = {
    ...mailModels,
    MailTestActivity,
    MailTestMultiCompany,
    MailTestMultiCompanyRead,
    MailTestProperties,
    MailTestRottingResource,
    MailTestRottingStage,
    MailTestSimpleMainAttachment,
    MailTestSimple,
    MailTestTrackAll,
};

export function defineTestMailModels() {
    defineParams({ suite: "test_mail" }, "replace");
    defineModels(testMailModels);
}

export async function editSelect(selector, value) {
    await contains(selector);
    const el = document.querySelector(selector);
    el.value = value;
    el.dispatchEvent(new Event("change"));
}
