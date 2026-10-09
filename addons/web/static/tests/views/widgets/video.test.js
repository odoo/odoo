import { expect, test } from "@odoo/hoot";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    display_name = fields.Char();
    _records = [{ id: 1, display_name: "first record" }];
}

class User extends models.Model {
    _name = "res.users";

    has_group() {
        return true;
    }
}

defineModels([Partner, User]);

test("video widget: displays the preview and opens the video in a dialog", async () => {
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `
            <form>
                <widget name="video" preview="/web/static/img/preview.png" url="https://www.youtube.com/embed/abc" title="Demo"/>
            </form>`,
    });
    // (hoot replaces the sources of images and iframes, so we don't check them)
    expect(".o_widget_video img").toHaveAttribute("alt", "Demo");
    expect(".o_dialog").toHaveCount(0);

    await contains(".o_widget_video .o_video_preview").click();
    expect(".o_dialog iframe").toHaveAttribute("title", "Demo");
});

test("video widget: in a help view (no record)", async () => {
    Partner._records = [];
    await mountView({
        resModel: "partner",
        type: "list",
        arch: `
            <list>
                <field name="display_name"/>
                <help>
                    <widget name="video" preview="/web/static/img/preview.png" url="https://www.youtube.com/embed/abc"/>
                </help>
            </list>`,
    });
    expect(".o_view_nocontent .o_widget_video img").toHaveAttribute("alt", "Video");
    await contains(".o_view_nocontent .o_video_preview").click();
    expect(".o_dialog iframe").toHaveAttribute("title", "Video");
});
