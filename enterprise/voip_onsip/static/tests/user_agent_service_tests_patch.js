import {
    expectedValues,
    settingsData,
} from "@voip/../tests/legacy/user_agent/user_agent_service_tests";

settingsData.onsip_auth_username = "voip_onsip override";
expectedValues.authorizationUsername = settingsData.onsip_auth_username;
