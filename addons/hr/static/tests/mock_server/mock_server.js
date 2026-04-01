import { onRpc } from "@web/../tests/web_test_helpers";

onRpc("get_avatar_card_data", function getAvatarCardData({ args }) {
    const resourceId = args[0][0];
    const resources = this.env["hr.employee.public"].search_read([["id", "=", resourceId]]);
    return resources.map((resource) => ({
        name: resource.name,
        work_email: resource.work_email,
        phone: resource.phone,
        user_id: resource.user_id,
    }));
});
