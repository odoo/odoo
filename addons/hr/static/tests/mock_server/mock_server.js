import { registry } from "@web/core/registry";

function _mockGetAvatarCardData({ args }) {
    const resourceId = args[0][0];
    const resources = this.env["hr.employee.public"].search_read([["id", "=", resourceId]]);
    return resources.map((resource) => ({
        name: resource.name,
        work_email: resource.work_email,
        phone: resource.phone,
        user_id: resource.user_id,
    }));
}

registry.category("mock_rpc").add("get_avatar_card_data", _mockGetAvatarCardData);
