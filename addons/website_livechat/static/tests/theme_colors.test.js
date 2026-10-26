import {
    click,
    contains,
    insertText,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { defineModels, fields, models, onRpc, serverState } from "@web/../tests/web_test_helpers";
import { defineWebsiteLivechatModels } from "./website_livechat_test_helpers";

describe.current.tags("desktop");
defineWebsiteLivechatModels();

// Extends the im_livechat mock model, merged by name.
class ThemeLivechatChannel extends models.ServerModel {
    _name = "im_livechat.channel";

    button_text = fields.Char();
    primary_color = fields.Char();
    secondary_color = fields.Char();
    default_colors = fields.Json();
    website_theme_sync_url = fields.Char();
    theme_colors_synced = fields.Boolean();

    _views = {
        form: `
            <form>
                <field name="button_text"/>
                <field name="default_colors" invisible="1"/>
                <field name="website_theme_sync_url" invisible="1"/>
                <field name="theme_colors_synced" invisible="1"/>
                <widget name="colors_reset_button"/>
                <field name="primary_color"/>
                <field name="secondary_color"/>
                <widget name="theme_colors_live_sync"/>
            </form>
        `,
    };

    get_website_theme_colors() {
        return { primary_color: "#112233", secondary_color: "#445566" };
    }
}
defineModels([ThemeLivechatChannel]);

async function setupChannel() {
    const pyEnv = await startServer();
    const channelId = pyEnv["im_livechat.channel"].create({
        name: "Website channel",
        button_text: "Chat with us",
        primary_color: "#000000",
        secondary_color: "#ffffff",
        website_theme_sync_url: "https://example.com",
    });
    await start();
    await openFormView("im_livechat.channel", channelId);
    return { pyEnv, channelId };
}

test("restoring website styles fills the colors without saving", async () => {
    await setupChannel();
    onRpc("im_livechat.channel", "web_save", () => expect.step("web_save"));
    await click("button:text('Restore website styles')");
    await contains(".o_field_widget[name=primary_color] input", { value: "#112233" });
    await contains(".o_field_widget[name=secondary_color] input", { value: "#445566" });
    await contains(".o_form_status_indicator_buttons:not(.invisible)");
    expect.verifySteps([]);
});

test("theme sync notification keeps pending edits", async () => {
    const { pyEnv, channelId } = await setupChannel();
    await insertText(".o_field_widget[name=button_text] input", " now", { replace: false });
    pyEnv["im_livechat.channel"].write([channelId], {
        primary_color: "#112233",
        secondary_color: "#445566",
    });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "im_livechat.channel/theme_colors_synced", {
        id: channelId,
    });
    await contains(".o_field_widget[name=primary_color] input", { value: "#112233" });
    await contains(".o_field_widget[name=secondary_color] input", { value: "#445566" });
    await contains(".o_field_widget[name=button_text] input", { value: "Chat with us now" });
});

test("theme sync notification reloads a clean form", async () => {
    const { pyEnv, channelId } = await setupChannel();
    pyEnv["im_livechat.channel"].write([channelId], { primary_color: "#112233" });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "im_livechat.channel/theme_colors_synced", {
        id: channelId,
    });
    await contains(".o_field_widget[name=primary_color] input", { value: "#112233" });
    await contains(".o_form_status_indicator_buttons.invisible");
});
