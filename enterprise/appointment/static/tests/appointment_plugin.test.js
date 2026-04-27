import { getContent, setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { HtmlField } from "@html_editor/fields/html_field";
import { beforeEach, expect, test } from "@odoo/hoot";
import { press, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { defineAppointmentModels } from "./appointment_tests_common";

const linkUrl = window.location.origin + "/book/123";

defineAppointmentModels();

class Note extends models.Model {
    _name = "note";
    body = fields.Html({ trim: true });

    _records = [
        {
            id: 1,
            body: "<p></p>",
        },
        {
            id: 2,
            body: '<p><a href="http://odoo.com">Existing link</a></p>',
        },
    ];
}
defineModels([Note]);

let htmlEditor;
beforeEach(() => {
    patchWithCleanup(HtmlField.prototype, {
        onEditorLoad(editor) {
            htmlEditor = editor;
            return super.onEditorLoad(...arguments);
        },
    });
});

beforeEach(() => {
    mockService("dialog", {
        add(dialogClass, props) {
            return props.insertLink(linkUrl);
        },
    });
});

test("insert link with /Appointment", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "note",
        arch: `
            <form>
                <field name="body" widget="html" style="height: 100px"/>
            </form>`,
    });
    const paragraph = queryOne(".odoo-editor-editable p");
    setSelection({ anchorNode: paragraph, anchorOffset: 0 });
    await insertText(htmlEditor, "/Appointment");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    await press("Enter");
    await animationFrame();
    expect(getContent(queryOne(".odoo-editor-editable"))).toBe(
        `<p>\ufeff<a href="${linkUrl}">\ufeffSchedule an Appointment\ufeff</a>[]\ufeff</p>`
    );
});

test("Replace existing link with '/Appointment' link", async () => {
    await mountView({
        type: "form",
        resId: 2,
        resModel: "note",
        arch: `
            <form>
                <field name="body" widget="html" style="height: 100px"/>
            </form>`,
    });

    const paragraph = queryOne(".odoo-editor-editable p");
    expect(paragraph.outerHTML).toBe(
        `<p>\ufeff<a href="http://odoo.com">\ufeffExisting link\ufeff</a>\ufeff</p>`
    );

    setSelection({
        anchorNode: paragraph.firstChild.nextSibling.firstChild.nextSibling,
        anchorOffset: 0,
    });
    await insertText(htmlEditor, "/Appointment");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    await press("Enter");
    await animationFrame();
    expect(getContent(queryOne(".odoo-editor-editable"))).toBe(
        `<p>\ufeff<a href="${linkUrl}">\ufeffSchedule an Appointment\ufeff</a>[]\ufeff</p>`
    );
});
