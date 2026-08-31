import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { EMBEDDED_COMPONENT_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import {
    animationFrame,
    beforeEach,
    describe,
    expect,
    mockDate,
    mockTimeZone,
    press,
    test,
} from "@odoo/hoot";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

import { setupEditor } from "./_helpers/editor.js";
import { expectElementCount } from "./_helpers/ui_expectations.js";
import {
    insertText,
    setColor,
} from "./_helpers/user_actions.js";
import { DateTime } from "@web/core/l10n/luxon";

const configWithEmbeddings = {
    Plugins: [...MAIN_PLUGINS, ...EMBEDDED_COMPONENT_PLUGINS],
    resources: { embedded_components: MAIN_EMBEDDINGS },
};

beforeEach(() => {
    mockDate("2026-04-05T10:30:00Z");
    mockTimeZone("Asia/Kolkata");
});

describe("date command", () => {
    test('"/today" command inserts the current date', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", { config: configWithEmbeddings });
        await insertText(editor, "/today");
        await expectElementCount(".o-we-powerbox .o-we-command-name:contains('Today')", 1);
        await press("Enter");
        expect('[data-embedded="date"]').toHaveCount(1);
        await animationFrame();
        expect('[data-embedded="date"] span').toHaveText("April 5, 2026");
    });

    test('"/hour" command inserts the current time', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", { config: configWithEmbeddings });
        await insertText(editor, "/hour");
        await expectElementCount(".o-we-powerbox .o-we-command-name:contains('Hour')", 1);
        await press("Enter");
        expect('[data-embedded="date"]').toHaveCount(1);
        await animationFrame();
        expect('[data-embedded="date"] span').toHaveText("4:00 PM");
    });

    test.tags("desktop");
    test('"/date" command opens a date picker, and the chip reopens it', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", { config: configWithEmbeddings });
        await insertText(editor, "/insertdate");
        await expectElementCount(".o-we-powerbox .o-we-command-name:contains(/^Date$/)", 1);
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        await contains(".o_date_item_cell:contains('7')").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("April 7, 2026");

        // Edit inserted date
        await contains('[data-embedded="date"] span').click();
        await expectElementCount(".o_datetime_picker", 1);
        await contains(".o_date_item_cell:contains('6')").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("April 6, 2026");
    });

    test.tags("desktop");
    test('"/datetime" command opens a datetime picker', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", { config: configWithEmbeddings });
        await insertText(editor, "/datetime");
        await expectElementCount(
            ".o-we-powerbox .o-we-command-name:contains('Date and Time')",
            1,
        );
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        expect(".o_time_picker").toHaveCount(1);
        await contains(".o_date_item_cell:contains('7')").click();
        await contains(".o_datetime_buttons button.btn-primary").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("Apr 7, 2026, 4:00 PM");
    });

    const STORED_DATETIME = `<p><span data-embedded="date" data-embedded-props='{"date":"2026-04-05T10:30:00.000Z","type":"datetime"}'></span></p>`;

    test("the stored date renders in the reader's timezone", async () => {
        await setupEditor(STORED_DATETIME, { config: configWithEmbeddings });
        expect('[data-embedded="date"] span').toHaveText("Apr 5, 2026, 4:00 PM");
    });

    test("the same stored date renders differently in another timezone", async () => {
        mockTimeZone("Europe/Brussels");
        await setupEditor(STORED_DATETIME, { config: configWithEmbeddings });
        expect('[data-embedded="date"] span').toHaveText("Apr 5, 2026, 12:30 PM");
    });

    test("the date renders in readonly mode", async () => {
        class Test extends models.Model {
            name = fields.Char();
            txt = fields.Html();
            _records = [
                {
                    id: 1,
                    name: "Test",
                    txt: `<div class="o-paragraph"><span data-embedded="date" data-embedded-props='{"date":"${DateTime.now()
                        .toUTC()
                        .toISO()}","type":"date"}' data-oe-protected="true" contenteditable="false"></span></div>`,
                },
            ];
        }

        defineModels([Test]);
        await mountView({
            type: "form",
            resId: 1,
            resModel: "test",
            arch: `
                <form>
                    <field name="name"/>
                    <field name="txt" widget="html" readonly="1" options="{'embedded_components': True}"/>
                </form>`,
        });
        expect(`[name="txt"] .o_readonly`).toHaveCount(1);
        expect(`[name="txt"] .o_readonly [data-embedded="date"]`).toHaveInnerHTML(
            `<span>April 5, 2026</span>`,
        );
    });

    describe("colour", () => {
        const dateUTC = "2026-04-05T10:30:00.000Z";

        test("should be able to color a date node", async () => {
            const { el, editor } = await setupEditor(
                `<p>[<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}'></span>]</p>`,
                { config: configWithEmbeddings },
            );
            setColor("rgb(255, 0, 0)", "color")(editor);
            await animationFrame();
            expect(el.querySelector('[data-embedded="date"]').style.color).toBe(
                "rgb(255, 0, 0)",
            );
        });
    });
});
