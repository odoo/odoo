import { registry } from "@web/core/registry";

registry.category("formatters").add("im_livechat.rating_percentage", (value) => {
    const percentage = (Math.max(value - 1, 0) * 100) / 4;
    return Math.round((percentage + Number.EPSILON) * 10) / 10;
});
