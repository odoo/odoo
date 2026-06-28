import { beforeEach, expect, test, waitFor } from "@odoo/hoot";
import { Component, onMounted, xml } from "@odoo/owl";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    defineActions,
    defineModels,
    getService,
    models,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";

const actionRegistry = registry.category("actions");

class TestClientAction extends Component {
    static template = xml`
        <div class="test_client_action">
            ClientAction_<t t-out="this.props.action.params?.description"/>
        </div>`;
    static props = ["*"];
    setup() {
        onMounted(() => this.env.config.setDisplayName(`Client action ${this.props.action.id}`));
    }
}

class Partner extends models.Model {
    _rec_name = "display_name";

    _records = [
        { id: 1, display_name: "First record" },
        { id: 2, display_name: "Second record" },
    ];
    _views = {
        "kanban,1": /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>
        `,
    };
}

defineModels([Partner]);
defineMailModels();

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        views: [[1, "kanban"]],
    },
]);

beforeEach(() => {
    actionRegistry.add("__test__client__action__", TestClientAction);
});

test("test display_notification client action with newlines", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);

    await getService("action").doAction({
        type: "ir.actions.client",
        tag: "res_partner_to_list_results",
        params: {
            notification: {
                message: "Item 1%(NOTIF_NEWLINE)sItem 2",
                button: { name:"View", action: {} },
                type: "success"
            },
        },
    });
    await waitFor(".o_notification_manager .o_notification");
    expect(".o_notification_manager .o_notification .o_notification_content").toHaveText(
        "Item 1\nItem 2"
    );
    expect(".o_notification_manager .o_notification .o_notification_content").toHaveStyle({
        "-webkit-line-clamp": 3,
    });
});
