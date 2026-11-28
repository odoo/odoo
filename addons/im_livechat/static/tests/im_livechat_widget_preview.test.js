import { defineLivechatModels } from "./livechat_test_helpers";
import { openFormView, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("editing colors and welcome message updates the widget preview", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        name: "Support",
        default_message: "Hello there",
    });
    await start();
    await openFormView("im_livechat.channel", livechatChannelId, {
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="widget_background_color" widget="color"/>
                        <field name="widget_text_color" widget="color"/>
                        <field name="default_message"/>
                    </group>
                    <widget name="im_livechat_widget_preview"/>
                </sheet>
            </form>`,
    });
    await waitFor(".o_im_livechat_preview .o-mail-Message-content:text(Hello there)");
    expect(".o_im_livechat_preview .o-mail-ChatWindow-header").toHaveStyle({
        backgroundColor: "rgb(135, 90, 123)",
        color: "rgb(255, 255, 255)",
    });
    expect(".o_im_livechat_preview .o-livechat-LivechatButton").toHaveStyle({
        backgroundColor: "rgb(135, 90, 123)",
        color: "rgb(255, 255, 255)",
    });
    await contains(".o_field_widget[name='widget_background_color'] input", {
        visible: false,
    }).edit("#ff0000");
    await contains(".o_field_widget[name='widget_text_color'] input", {
        visible: false,
    }).edit("#00ff00");
    expect(".o_im_livechat_preview .o-mail-ChatWindow-header").toHaveStyle({
        backgroundColor: "rgb(255, 0, 0)",
        color: "rgb(0, 255, 0)",
    });
    expect(".o_im_livechat_preview .o-livechat-LivechatButton").toHaveStyle({
        backgroundColor: "rgb(255, 0, 0)",
        color: "rgb(0, 255, 0)",
    });
    await contains(".o_field_widget[name='default_message'] input").edit("Welcome aboard");
    await waitFor(".o_im_livechat_preview .o-mail-Message-content:text(Welcome aboard)");
});
