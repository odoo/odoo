import { models } from "@web/../tests/web_test_helpers";

export class DiscussCategory extends models.ServerModel {
    _name = "discuss.category";

    _store_category_fields(res) {
        res.attr("name");
        res.attr("sequence");
        res.attr("bus_channel_access_token", (category) => category.id); // mock: token is the record id
    }
}
