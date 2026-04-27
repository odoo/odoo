import { defineModels } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { ApprovalRequest } from "@approvals/../tests/mock_server/mock_models/approval_request";
import { ApprovalApprover } from "@approvals/../tests/mock_server/mock_models/approval_approver";
import { MailActivity } from "@approvals/../tests/mock_server/mock_models/mail_activity";

export function defineApprovalsModels() {
    return defineModels(approvalsModels);
}

export const approvalsModels = {
    ...mailModels,
    ApprovalRequest,
    ApprovalApprover,
    MailActivity
};
