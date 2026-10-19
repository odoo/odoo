import { Store } from "@mail/../tests/mock_server/store";

import { fields, getKwArgs, makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class MailCannedResponse extends models.ServerModel {
    _name = "mail.canned.response";

    group_ids = fields.Many2many({
        relation: "res.groups",
        falsy_value_label: "🔒 Private",
    });

    _views = {
        list: `
            <list>
                <field name="source" widget="shortcut"/>
                <field name="group_ids" widget="many2many_falsy_value_label"/>
            </list>
        `,
        form: `
            <form>
                <field name="source" widget="shortcut"/>
                <field name="group_ids" widget="many2many_falsy_value_label"/>
            </form>
        `,
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="source" widget="shortcut"/>
                        <field name="group_ids" widget="many2many_falsy_value_label"/>
                    </t>
                </templates>
            </kanban>
        `,
    };

    create() {
        const cannedReponseIds = super.create(...arguments);
        this._broadcast(cannedReponseIds);
        return cannedReponseIds;
    }

    write(ids) {
        const res = super.write(...arguments);
        this._broadcast(ids);
        return res;
    }

    unlink(ids) {
        this._broadcast(ids, makeKwArgs({ delete: true }));
        return super.unlink(...arguments);
    }

    _broadcast(ids, _delete) {
        const kwargs = getKwArgs(arguments, "ids", "delete");
        _delete = kwargs.delete;
        const notifications = [];
        const [partner] = this.env["res.partner"].read(this.env.user.partner_id);
        for (const cannedResponse of this.browse(ids)) {
            const store = new Store();
            if (_delete) {
                store.delete(this.browse(cannedResponse.id));
            } else {
                store.add(this.browse(cannedResponse.id), "_store_canned_response_fields");
            }
            notifications.push([partner, "mail.record/insert", store.as_dict()]);
        }
        if (notifications.length) {
            this.env["bus.bus"]._sendmany(notifications);
        }
    }

    _store_canned_response_fields(res) {
        res.extend(["source", "substitution"]);
    }
}
