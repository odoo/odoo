import { beforeEach, describe, test } from "@odoo/hoot";
import { defineTestDiscussFullModels } from "@test_discuss_full/../tests/test_discuss_full_test_helpers";
import { HrEmployee } from "@hr/../tests/mock_server/mock_models/hr_employee";
import { serverState } from "@web/../tests/web_test_helpers";
import { openClosePersistedChannel } from "@im_livechat/../tests/embed/im_livechat_embed_shared_tests";

describe.current.tags("desktop");
defineTestDiscussFullModels();

beforeEach(() => {
    HrEmployee._records = [
        {
            id: 1,
            name: "Test Employee",
            user_id: serverState.userId,
        },
    ];
});

test("open/close persisted channel", openClosePersistedChannel);
