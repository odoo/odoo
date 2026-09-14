import { defineModels } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";

import { TeamTeam } from "./mock_server/mock_models/team_team.js";

export function defineTeamModels() {
    return defineModels({ TeamTeam, ...mailModels });
}
