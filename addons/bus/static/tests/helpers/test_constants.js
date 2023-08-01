/** @odoo-module **/

export const TEST_GROUP_IDS = {
    groupUserId: 11,
};

export const TEST_USER_IDS = {
    odoobotId: 2,
    adminPartnerId: 3,
    adminUserId: 2,
    publicPartnerId: 4,
    publicUserId: 3,
};
Object.assign(TEST_USER_IDS, {
    currentPartnerId: TEST_USER_IDS.adminPartnerId,
    currentUserId: TEST_USER_IDS.adminUserId,
});
