/** @odoo-module **/

import { patchUserWithCleanup } from "@web/../tests/helpers/mock_services";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { ListRenderer } from "@web/views/list/list_renderer";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { patchListRendererDesktop } from "@web_enterprise/views/list/list_renderer_desktop";
import { registerStudioDependencies } from "@web_studio/../tests/legacy/helpers";
import { patchListRendererStudio } from "@web_studio/views/list/list_renderer";

let serverData;
let target;

QUnit.module("Studio", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        registerStudioDependencies();
        patchUserWithCleanup({ isSystem: true });
        target = getFixture();
        patchWithCleanup(ListRenderer.prototype, patchListRendererDesktop());
        patchWithCleanup(ListRenderer.prototype, patchListRendererStudio());
    });

    QUnit.module("ListView");

    QUnit.test("add custom field button with other optional columns", async function (assert) {
        serverData.views["partner,false,list"] = `
            <list>
                <field name="foo"/>
                <field name="bar" optional="hide"/>
            </list>`;

        const webClient = await createEnterpriseWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");
        assert.containsOnce(target, ".o_list_view .o_optional_columns_dropdown_toggle");

        await click(target.querySelector(".o_optional_columns_dropdown_toggle"));
        assert.containsN(target, ".o-dropdown--menu .dropdown-item", 2);
        assert.containsOnce(target, ".o-dropdown--menu .dropdown-item-studio");

        await click(target.querySelector(".o-dropdown--menu .dropdown-item-studio"));
        assert.containsNone(target, ".modal-studio");
        assert.containsOnce(
            target,
            ".o_studio .o_web_studio_editor .o_web_studio_list_view_editor"
        );
    });

    QUnit.test("add custom field button without other optional columns", async function (assert) {
        // by default, the list in serverData doesn't contain optional fields
        const webClient = await createEnterpriseWebClient({ serverData });
        await doAction(webClient, 3);

        assert.containsOnce(target, ".o_list_view");
        assert.containsOnce(target, ".o_list_view .o_optional_columns_dropdown_toggle");
        await click(target.querySelector(".o_optional_columns_dropdown_toggle"));

        assert.containsOnce(target, ".o-dropdown--menu .dropdown-item");
        assert.containsOnce(target, ".o-dropdown--menu .dropdown-item-studio");

        await click(target.querySelector(".o-dropdown--menu .dropdown-item-studio"));
        assert.containsNone(target, ".modal-studio");
        assert.containsOnce(
            target,
            ".o_studio .o_web_studio_editor .o_web_studio_list_view_editor"
        );
    });

    QUnit.test("should render the no content helper of studio actions", async function (assert) {
        serverData.views["base.automation,false,kanban"] =
            '<kanban><t t-name="card"><field name="name"/></t></kanban>';
        serverData.views["base.automation,false,list"] = '<list><field name="name"/></list>';
        serverData.views["base.automation,false,form"] = '<form><field name="name"/></form>';
        serverData.views["base.automation,false,search"] = "<search></search>";
        serverData.models["base.automation"] = {
            fields: {
                id: { string: "Id", type: "integer" },
                name: { string: "Name", type: "char" },
            },
            records: [],
        };
        const webClient = await createEnterpriseWebClient({ serverData });
        await doAction(webClient, 3);
        await click(target.querySelector(".o_web_studio_navbar_item button"));
        const automationsLink = [...target.querySelectorAll(".o_menu_sections a")].find(
            (link) => link.textContent === "Automations"
        );
        await click(automationsLink);
        assert.containsOnce(target, ".no_content_helper_class");
    });
});
