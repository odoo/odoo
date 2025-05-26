import { models, fields, getKwArgs } from "@web/../tests/web_test_helpers";

export class HrWorkLocation extends models.ServerModel {
    _name = "hr.work.location";

    name = fields.Char();
    location_type = fields.Selection({
        selection: [
            ["office", "Office"],
            ["home", "Home"],
            ["other", "Other"],
        ],
    });

    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "id", "store", "fields", "extra_fields");
        fields = kwargs.fields;
        for (const workLocation of this.browse(ids)) {
            const [data] = this._read_format(workLocation.id, fields);
            store.add(this.browse(workLocation.id), data);
        }
    }

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };
}
