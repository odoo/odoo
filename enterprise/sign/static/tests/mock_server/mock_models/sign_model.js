import { models } from "@web/../tests/web_test_helpers";

export class SignTemplate extends models.ServerModel {
    _name = "sign.template";

    _records = [
        {
            id: 1,
            display_name: "yop.pdf",
            tag_ids: [1, 2],
            color: 1,
            active: true,
        },
    ];
}

export class SignTemplateTag extends models.ServerModel {
    _name = "sign.template.tag";

    _records = [
        {
            id: 1,
            name: "New",
            color: 1,
        },
        {
            id: 2,
            name: "Draft",
            color: 2,
        },
    ];
}
