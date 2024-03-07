import { defineModels, fields, models } from "@web/../tests/web_test_helpers";

export class Foo extends models.Model {
    bar = fields.Many2one({ relation: "partner" });
    foo = fields.Char({ store: true, sortable: true, groupable: true });
    birthday = fields.Date({ store: true, sortable: true, groupable: true });
    date_field = fields.Date({ string: "Date", store: true, sortable: true, groupable: true });
    parent_id = fields.Many2one({ string: "Parent", relation: "parent.model" });
    properties = fields.Properties({
        definition_record: "parent_id",
        definition_record_field: "properties_definition",
    });

    _views = {
        search: `
            <search>
                <filter name="birthday" date="birthday"/>
                <filter name="date_field" date="date_field"/>
            </search>
        `,
    };
}

export class Partner extends models.Model {
    name = fields.Char();
}

export class ParentModel extends models.Model {
    _name = "parent.model";

    name = fields.Char();
    properties_definition = fields.PropertiesDefinition();
}

export function defineSearchBarModels() {
    defineModels([Foo, Partner, ParentModel]);
}
