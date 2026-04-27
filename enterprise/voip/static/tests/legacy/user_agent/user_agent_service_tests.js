// allow test data to be overridden in other modules
export const settingsData = {
    voip_secret: "super secret password",
    voip_username: "1337",
};
export const expectedValues = {
    authorizationUsername: settingsData.voip_username,
};
