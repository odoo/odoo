/** @odoo-module **/

import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { click, queryAll, queryFirst, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { WebClient } from "@web/webclient/webclient";

const campaignTemplatesGroups = {
    misc: {
        label: "Misc",
        templates: {
            start_from_scratch: {
                title: "Start from scratch",
                description: "'average person eats 3 spiders a year' factoid actualy",
            },
            hot_contacts: {
                title: "Tag Hot Contacts",
                description: "just statistical error. average person eats 0 spiders per year.",
                function: 1,
            },
        },
    },
    marketing: {
        label: "Marketing",
        templates: {
            welcome: {
                title: "Welcome Flow",
                description: "Spiders Georg, who lives in cave & eats over 10,000 each day,",
                function: 1,
            },
            double_opt_in: {
                title: "Double Opt-in",
                description: "is an outlier adn should not have been counted",
                function: 1,
            },
        },
    },
};

const marketingCampaignViews = {
    kanban: `
        <kanban string="Campaigns" js_class="marketing_campaign_kanban_view">
            <templates>
                <t t-name="card">
                    <field name="name"/>
                </t>
            </templates>
        </kanban>
    `,
    list: `
        <list string="Campaigns" js_class="marketing_campaign_list_view">
            <field name="name"/>
        </list>
    `,
    form: `
        <form js_class="marketing_campaign_form_view">
            <field name="name"/>
        </form>
        `,
};

class MarketingCampaign extends models.Model {
    name = fields.Char();
    _name = "marketing.campaign";
    _records = [
        {
            id: 1,
            name: "welcome",
        },
    ];

    _views = Object.assign({}, marketingCampaignViews);
}

defineModels([MarketingCampaign]);
defineMailModels();

defineActions([
    {
        id: 99,
        xml_id: "marketing_campaign_action_view",
        name: "Campaign View",
        res_model: "marketing.campaign",
        views: [
            [false, "kanban"],
            [false, "list"],
            [false, "form"],
        ],
    },
]);

onRpc("get_campaign_templates_info", () => {
    return campaignTemplatesGroups;
});

onRpc("has_group", () => {
    return true;
});

onRpc("get_action_marketing_campaign_from_template", (request) => {
    expect.step("get_template");

    // ensure that the passed argument is the expected template
    expect(request.args[0]).toBe("welcome");

    // return an action (which is expected by the tested component)
    return {
        name: "marketing_campaign_action_view",
        type: "ir.actions.act_window",
        view_mode: "form",
        res_id: 1,
        res_model: "marketing.campaign",
        views: [[false, "form"]],
    };
});

/**
 * Check that the modal opens for the kanban view
 */
test("Marketing Campaign Template Picker - Kanban override", async function () {
    // Check that the controller is overriden for the kanban view
    await mountView({
        resModel: "marketing.campaign",
        type: "kanban",
        arch: marketingCampaignViews.kanban,
    });
    await click("button.o-kanban-button-new");
    await animationFrame();
    queryOne("div.modal.o_technical_modal"); // ensure modal has been opened
    await click(queryOne("button.o_ma_campaign_picker_discard")); // close modal
    await animationFrame();
    expect("div.modal.o_technical_modal").toHaveCount(0); // ensure modal has been closed
});

/**
 * Check that the modal opens for the list view
 */
test("Marketing Campaign Template Picker - List override", async function () {
    // Check that the controller is overriden for the list view
    await mountView({
        resModel: "marketing.campaign",
        type: "list",
        arch: marketingCampaignViews.list,
    });
    await click("button.o_list_button_add");
    await animationFrame();
    queryOne("div.modal.o_technical_modal"); // ensure modal has been opened
    await click(queryOne("button.o_ma_campaign_picker_discard")); // close modal
    await animationFrame();
    expect("div.modal.o_technical_modal").toHaveCount(0); // ensure modal has been closed
});

/**
 * Check that the modal opens for the form view
 */
test("Marketing Campaign Template Picker - Form override", async function () {
    await mountView({
        resModel: "marketing.campaign",
        type: "form",
        arch: marketingCampaignViews.form,
    });
    await click("button.o_form_button_create");
    await animationFrame();
    queryOne("div.modal.o_technical_modal"); // ensure modal has been opened
    await click(queryOne("button.o_ma_campaign_picker_discard")); // close modal
    await animationFrame();
    expect("div.modal.o_technical_modal").toHaveCount(0); // ensure modal has been closed
});

/**
 * Check that the modal functions as expected
 */
test("Marketing Campaign Template Picker - Template picker", async function () {
    // Mount web client (displayed view must not be a form) and open the modal
    await mountWithCleanup(WebClient);
    await animationFrame();
    await getService("action").doAction("marketing_campaign_action_view");
    expect("button.o_form_button_create").toHaveCount(0);
    await click("button.o-kanban-button-new");
    await animationFrame();
    // modal is open

    // check that template cards have content
    expect(".o_ma_campaign_picker_active h3.card-title:contains('Start from scratch')").toHaveCount(
        1
    );
    expect(
        ".o_ma_campaign_picker_active p.card-text:contains('average person eats 3')"
    ).toHaveCount(1);

    // check that there can be only one "active card"
    const [card_from_scratch, card_hot_contacts] = queryAll("div.card.o_ma_campaign_picker_card");
    expect(card_from_scratch).toHaveClass("o_ma_campaign_picker_active");
    await click(card_hot_contacts);
    await animationFrame();
    expect(card_from_scratch).not.toHaveClass("o_ma_campaign_picker_active");
    expect(card_hot_contacts).toHaveClass("o_ma_campaign_picker_active");
    // get to the next page
    await click(queryAll(".o_ma_campaign_template_picker_dialog a.nav-link")[1]);
    await animationFrame();
    const card_welcome_flow = queryFirst("div.card.o_ma_campaign_picker_card");
    await click(card_welcome_flow);
    await animationFrame();
    expect(card_welcome_flow).toHaveClass("o_ma_campaign_picker_active");

    // go back to the first page and ensure all cards are unselected
    await click(queryAll(".o_ma_campaign_template_picker_dialog a.nav-link")[0]);
    await animationFrame();
    for (const templateCard of queryAll("div.card.o_ma_campaign_picker_card")) {
        expect(templateCard).not.toHaveClass("o_ma_campaign_picker_active");
    }

    // load the template
    expect.verifySteps([]);
    await click(queryOne("button.o_ma_campaign_picker_create"));
    await animationFrame();
    // check that the template is loaded
    expect.verifySteps(["get_template"]);

    // we should now be in a form view
    expect("button.o_form_button_create").not.toHaveCount(0);
    await animationFrame();
});
