import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { EMBEDDED_COMPONENT_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import {
    animationFrame,
    beforeEach,
    describe,
    edit,
    expect,
    mockDate,
    mockTimeZone,
    press,
    test,
} from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import {
    insertText,
    undo,
    simulateArrowKeyPress,
    bold,
    italic,
    underline,
    strikeThrough,
    setColor,
} from "./_helpers/user_actions";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import { expectElementCount } from "./_helpers/ui_expectations";
import { getContent } from "./_helpers/selection";
import { execCommand } from "./_helpers/userCommands";

const { DateTime } = luxon;

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
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/today");
        await expectElementCount(".o-we-powerbox .o-we-command-name:contains('Today')", 1);
        await press("Enter");
        expect('[data-embedded="date"]').toHaveCount(1);
        await animationFrame();
        expect('[data-embedded="date"] span').toHaveText("April 5, 2026");
    });

    test.tags("desktop");
    test('"/hour" command inserts the current time', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/hour");
        await expectElementCount(".o-we-powerbox .o-we-command-name:contains('Hour')", 1);
        await press("Enter");
        expect('[data-embedded="date"]').toHaveCount(1);
        await animationFrame();
        expect('[data-embedded="date"] span').toHaveText("4:00 PM");

        // Edit inserted time
        await contains('[data-embedded="date"] span').click();
        await expectElementCount(".o_time_picker", 1);
        await contains(".o_time_picker input").click();
        await contains(".o_time_picker_option:contains(15:00)").click();
        await expectElementCount(".o_time_picker", 0);
        expect('[data-embedded="date"] span').toHaveText("3:00 PM");

        // Undo
        undo(editor);
        await animationFrame();
        expect('[data-embedded="date"] span').toHaveText("4:00 PM");
    });

    test.tags("mobile");
    test("should be able to edit time using timepicker", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/hour");
        await expectElementCount(".o-we-powerbox .o-we-command-name:contains('Hour')", 1);
        await press("Enter");
        expect('[data-embedded="date"]').toHaveCount(1);
        await animationFrame();
        expect('[data-embedded="date"] span').toHaveText("4:00 PM");

        // Edit inserted time
        await contains('[data-embedded="date"] span').click();
        await expectElementCount(".o_time_picker", 1);
        await edit("15:00");
        await expectElementCount(".o_time_picker", 0);
        expect('[data-embedded="date"] span').toHaveText("3:00 PM");
    });
    test('"/date" command opens a date picker', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
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
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/datetime");
        await expectElementCount(".o-we-powerbox .o-we-command-name:contains('Date and Time')", 1);
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        expect(".o_datetime_picker button[title='Clear']").toHaveCount(0);
        expect(".o_time_picker").toHaveCount(1);
        await contains(".o_date_item_cell:contains('7')").click();
        await contains(".o_time_picker input").click();
        await contains(".o_time_picker_option:contains(10:30)").click();
        await contains(".o_datetime_buttons button").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("Apr 7, 2026, 10:30 AM");

        // Edit inserted date
        await contains('[data-embedded="date"] span').click();
        await expectElementCount(".o_datetime_picker", 1);
        await contains(".o_date_item_cell:contains('6')").click();
        await contains(".o_time_picker input").click();
        await contains(".o_time_picker_option:contains(16:30)").click();
        await contains(".o_datetime_buttons button").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"] span').toHaveText("Apr 6, 2026, 4:30 PM");
    });

    test.tags("mobile");
    test('"/datetime" command opens a datetime picker in mobile', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/datetime");
        await animationFrame();
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        expect(".o_time_picker").toHaveCount(1);
        await contains(".o_date_item_cell:contains('7')").click();
        await contains(".o_time_picker input").click();
        await edit("10:30");
        await contains(".o_datetime_buttons button").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("Apr 7, 2026, 10:30 AM");
    });
    test("date should get updated according to the timezone", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/datetime");
        await animationFrame();
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        expect(".o_time_picker").toHaveCount(1);
        await contains(".o_datetime_buttons button").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("Apr 5, 2026, 4:00 PM");
        await press("Backspace");

        // Change timezone
        mockTimeZone("Europe/Brussels");
        await insertText(editor, "/datetime");
        await animationFrame();
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        expect(".o_time_picker").toHaveCount(1);
        await contains(".o_datetime_buttons button").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("Apr 5, 2026, 12:30 PM");
    });
    test("Embedded date component should work in readonly mode", async () => {
        class Test extends models.Model {
            name = fields.Char();
            txt = fields.Html();
            _records = [
                {
                    id: 1,
                    name: "Test",
                    txt: `<div class="o-paragraph"><span data-embedded="date" data-embedded-props='{"date":"${DateTime.now()
                        .toUTC()
                        .toISO()}","type":"date"}' data-oe-protected="true" contenteditable="false"></div>`,
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
            `<span>April 5, 2026</span>`
        );
    });
    test("should navigate correctly around embedded date components", async () => {
        const dateUTC = DateTime.now().toUTC().toISO();
        const { el, editor } = await setupEditor(
            `<p>abc</p><p><span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}'></span></p><p>def<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}'></span>[]</p>`,
            {
                config: configWithEmbeddings,
            }
        );
        const embeddedDate = `<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}' data-oe-protected="true" contenteditable="false"><span class="cursor-pointer">April 5, 2026</span></span>`;
        expect(getContent(el)).toBe(
            `<p>abc</p><p>\uFEFF${embeddedDate}\uFEFF</p><p>def\uFEFF${embeddedDate}\uFEFF[]</p>`
        );

        await simulateArrowKeyPress(editor, "ArrowUp");
        expect(getContent(el)).toBe(
            `<p>abc</p><p>\uFEFF${embeddedDate}\uFEFF[]</p><p>def\uFEFF${embeddedDate}\uFEFF</p>`
        );

        await simulateArrowKeyPress(editor, "ArrowUp");
        expect(getContent(el)).toBe(
            `<p>abc[]</p><p>\uFEFF${embeddedDate}\uFEFF</p><p>def\uFEFF${embeddedDate}\uFEFF</p>`
        );

        await simulateArrowKeyPress(editor, "ArrowDown");
        expect(getContent(el)).toBe(
            `<p>abc</p><p>\uFEFF${embeddedDate}\uFEFF[]</p><p>def\uFEFF${embeddedDate}\uFEFF</p>`
        );

        await simulateArrowKeyPress(editor, "ArrowDown");
        expect(getContent(el)).toBe(
            `<p>abc</p><p>\uFEFF${embeddedDate}\uFEFF</p><p>def\uFEFF${embeddedDate}[]\uFEFF</p>`
        );
    });
    test("editable should not be focused when opening datepicker", async () => {
        const { el, editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/datetime");
        await expectElementCount(".o-we-powerbox .o-we-command-name:contains('Date and Time')", 1);
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        expect(document.activeElement).not.toBe(el);
    });
    describe("formattings", () => {
        const dateUTC = DateTime.now().toUTC().toISO();
        test("should be able to apply and remove formattings on date nodes", async () => {
            const { el, editor } = await setupEditor(
                `<p>[<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}'></span>]</p>`,
                {
                    config: configWithEmbeddings,
                }
            );
            bold(editor);
            italic(editor);
            underline(editor);
            strikeThrough(editor);
            expect(getContent(el)).toBe(
                `<p>\ufeff[<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}' data-oe-protected="true" contenteditable="false" style="font-weight: bolder; font-style: italic; text-decoration-line: underline line-through;"><span class="cursor-pointer">March 11, 2019</span></span>\ufeff]</p>`
            );
            execCommand(editor, "removeFormat");
            expect(getContent(el)).toBe(
                `<p>\ufeff[<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}' data-oe-protected="true" contenteditable="false"><span class="cursor-pointer">March 11, 2019</span></span>\ufeff]</p>`
            );
        });
        test("should be able to apply and remove colors on date nodes", async () => {
            const { el, editor } = await setupEditor(
                `<p>[<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}'></span>]</p>`,
                {
                    config: configWithEmbeddings,
                }
            );
            setColor("rgb(206, 198, 206)", "color")(editor);
            setColor("rgb(255, 0, 0)", "backgroundColor")(editor);
            expect(getContent(el)).toBe(
                `<p>\ufeff[<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}' data-oe-protected="true" contenteditable="false" style="color: rgb(206, 198, 206); background-color: rgb(255, 0, 0);"><span class="cursor-pointer">March 11, 2019</span></span>\ufeff]</p>`
            );
            execCommand(editor, "removeFormat");
            expect(getContent(el)).toBe(
                `<p>\ufeff[<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}' data-oe-protected="true" contenteditable="false"><span class="cursor-pointer">March 11, 2019</span></span>\ufeff]</p>`
            );
        });
    });
});
