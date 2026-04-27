import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

import { HelpdeskTeam } from "./mock_server/mock_models/helpdesk_team";
import { HelpdeskStage } from "./mock_server/mock_models/helpdesk_stage";
import { HelpdeskTicket } from "./mock_server/mock_models/helpdesk_ticket";
import { HelpdeskSla } from "./mock_server/mock_models/helpdesk_sla";
import { HelpdeskSlaStatus } from "./mock_server/mock_models/helpdesk_sla_status";

export function defineHelpdeskModels() {
    defineModels(helpdeskModels);
}

export const helpdeskModels = {
    ...mailModels,
    HelpdeskStage,
    HelpdeskSla,
    HelpdeskSlaStatus,
    HelpdeskTeam,
    HelpdeskTicket,
};
