import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, mockService } from "@web/../tests/web_test_helpers";

import { MailActivity } from "./mock_server/mock_models/mail_activity";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { VoipCall } from "./mock_server/mock_models/voip_call";
import { VoipProvider } from "./mock_server/mock_models/voip_provider";

export function setupVoipTests() {
    const ringtones = {
        dial: {},
        incoming: {},
        ringback: {},
    };
    Object.values(ringtones).forEach((r) => Object.assign(r, { play: () => {} }));
    mockService("voip.ringtone", {
        ...ringtones,
        stopPlaying() {},
    });
    defineModels(voipModels);
}

export const voipModels = {
    ...mailModels,
    MailActivity,
    ResPartner,
    ResUsers,
    VoipCall,
    VoipProvider,
};
