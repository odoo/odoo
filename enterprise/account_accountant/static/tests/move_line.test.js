import { beforeEach, test } from "@odoo/hoot";
import { defineAccountModels } from "@account/../tests/account_test_helpers";
import {
    assertSteps,
    click,
    contains,
    onRpcBefore,
    openListView,
    patchUiSize,
    SIZES,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { onRpc, serverState } from "@web/../tests/web_test_helpers";
import { getOrigin } from "@web/core/utils/urls";

const ROUTES_TO_IGNORE = [
    "/bus/im_status",
    "/web/dataset/call_kw/account.move.line/get_views",
    "/web/webclient/load_menus",
    "/web/dataset/call_kw/res.users/load_views",
    "/hr_attendance/attendance_user_data",
    "/web/dataset/call_kw/res.users/has_group",
];
const openPreparedView = async (size) => {
    patchUiSize({ size: size });
    onRpcBefore((route, args) => {
        if (
            ROUTES_TO_IGNORE.includes(route) ||
            route.includes("/web/static/lib/pdfjs/web/viewer.html")
        ) {
            return;
        }
        step(`${route} - ${JSON.stringify(args)}`);
    });
    onRpc(({ method, model, args, kwargs }) => {
        const route = `/web/dataset/call_kw/${model}/${method}`;
        if (ROUTES_TO_IGNORE.includes(route)) {
            return;
        }
        step(`${route} - {"kwargs":${JSON.stringify(kwargs)}}`);
    });
    await start();
    await assertSteps([
        `/mail/data - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    await openListView("account.move.line", {
        context: { group_by: ["move_id"] },
        arch: `
        <list editable='bottom' js_class='account_move_line_list'>
            <field name='id'/>
            <field name='name'/>
            <field name='move_id'/>
        </list>`,
    });
};

defineAccountModels();

beforeEach(async () => {
    const pyEnv = await startServer();
    const accountMoveLineIds = pyEnv["account.move.line"].create([
        { name: "line0" },
        { name: "line1" },
        { name: "line2" },
        { name: "line3" },
        { name: "line4" },
        { name: "line5" },
    ]);
    const accountMove = pyEnv["account.move"].create([
        { name: "move0", invoice_line_ids: [accountMoveLineIds[0], accountMoveLineIds[1]] },
        { name: "move1", invoice_line_ids: [accountMoveLineIds[2], accountMoveLineIds[3]] },
        { name: "move2", invoice_line_ids: [accountMoveLineIds[4], accountMoveLineIds[5]] },
    ]);
    const attachmentIds = pyEnv["ir.attachment"].create([
        { res_id: accountMove[1], res_model: "account.move", mimetype: "application/pdf" },
        { res_id: accountMove[2], res_model: "account.move", mimetype: "application/pdf" },
    ]);
    pyEnv["account.move"].write([accountMove[1]], { attachment_ids: [attachmentIds[0]] });
    pyEnv["account.move.line"].write([accountMoveLineIds[0]], { move_id: accountMove[0] });
    pyEnv["account.move.line"].write([accountMoveLineIds[1]], { move_id: accountMove[0] });
    pyEnv["account.move.line"].write([accountMoveLineIds[2]], {
        move_id: accountMove[1],
        move_attachment_ids: [attachmentIds[0]],
    });
    pyEnv["account.move.line"].write([accountMoveLineIds[3]], {
        move_id: accountMove[1],
        move_attachment_ids: [attachmentIds[0]],
    });
    pyEnv["account.move.line"].write([accountMoveLineIds[4]], {
        move_id: accountMove[2],
        move_attachment_ids: [attachmentIds[1]],
    });
    pyEnv["account.move.line"].write([accountMoveLineIds[5]], {
        move_id: accountMove[2],
        move_attachment_ids: [attachmentIds[1]],
    });
});

test("No preview on small devices", async () => {
    await openPreparedView(SIZES.XL);
    await contains(".o_move_line_list_view");
    await assertSteps([
        `/web/dataset/call_kw/account.move.line/web_read_group - ${JSON.stringify({
            kwargs: {
                orderby: "",
                lazy: true,
                offset: 0,
                limit: 80,
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                    group_by: ["move_id"],
                },
                groupby: ["move_id"],
                domain: [],
                fields: ["id:sum"],
            },
        })}`,
    ]);
    // weak test, no guarantee to wait long enough for the potential attachment preview to show
    await contains(".o_attachment_preview", { count: 0 }); // The preview component shouldn't be mounted for small screens
    await click(":nth-child(1 of .o_group_header)");
    await contains(".o_data_row", { count: 2 });
    await assertSteps([
        `/web/dataset/call_kw/account.move.line/web_search_read - ${JSON.stringify({
            kwargs: {
                specification: {
                    id: {},
                    name: {},
                    move_id: { fields: { display_name: {} } },
                    move_attachment_ids: { fields: { mimetype: {} } },
                },
                offset: 0,
                order: "",
                limit: 80,
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                    bin_size: true,
                    group_by: ["move_id"],
                    default_move_id: 1,
                },
                count_limit: 10001,
                domain: [["move_id", "=", 1]],
            },
        })}`,
    ]);
    await click(":nth-child(1 of .o_data_row) :nth-child(2 of .o_data_cell)");
    await contains(":nth-child(1 of .o_data_row) :nth-child(2 of .o_data_cell) input");
    // weak test, no guarantee to wait long enough for the potential attachment preview to show
    await contains(".o_attachment_preview", { count: 0 }); // The preview component shouldn't be mounted for small screens even when clicking on a line without attachment
    await click(":nth-child(2 of .o_group_header)");
    await contains(".o_data_row", { count: 4 });
    await assertSteps([
        `/web/dataset/call_kw/account.move.line/web_search_read - ${JSON.stringify({
            kwargs: {
                specification: {
                    id: {},
                    name: {},
                    move_id: { fields: { display_name: {} } },
                    move_attachment_ids: { fields: { mimetype: {} } },
                },
                offset: 0,
                order: "",
                limit: 80,
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                    bin_size: true,
                    group_by: ["move_id"],
                    default_move_id: 2,
                },
                count_limit: 10001,
                domain: [["move_id", "=", 2]],
            },
        })}`,
    ]);
    await click(":nth-child(4 of .o_data_row) :nth-child(2 of .o_data_cell)");
    await contains(":nth-child(4 of .o_data_row) :nth-child(2 of .o_data_cell) input");
    // weak test, no guarantee to wait long enough for the potential attachment preview to show
    await contains(".o_attachment_preview", { count: 0 }); // The preview component shouldn't be mounted for small screens even when clicking on a line with attachment
    await assertSteps([], { message: "no extra rpc should be done" });
});

test("Fetch and preview of attachments on big devices", async () => {
    await openPreparedView(SIZES.XXL);
    await contains(".o_move_line_list_view");
    await assertSteps([
        `/web/dataset/call_kw/account.move.line/web_read_group - ${JSON.stringify({
            kwargs: {
                orderby: "",
                lazy: true,
                offset: 0,
                limit: 80,
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                    group_by: ["move_id"],
                },
                groupby: ["move_id"],
                domain: [],
                fields: ["id:sum"],
            },
        })}`,
    ]);
    await contains(".o_attachment_preview");
    await contains(".o_attachment_preview p", {
        text: "Choose a line to preview its attachments.",
    });
    await contains(".o_attachment_preview iframe", { count: 0 });
    await click(":nth-child(1 of .o_group_header)");
    await contains(".o_data_row", { count: 2 });
    await assertSteps([
        `/web/dataset/call_kw/account.move.line/web_search_read - ${JSON.stringify({
            kwargs: {
                specification: {
                    id: {},
                    name: {},
                    move_id: { fields: { display_name: {} } },
                    move_attachment_ids: { fields: { mimetype: {} } },
                },
                offset: 0,
                order: "",
                limit: 80,
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                    bin_size: true,
                    group_by: ["move_id"],
                    default_move_id: 1,
                },
                count_limit: 10001,
                domain: [["move_id", "=", 1]],
            },
        })}`,
    ]);
    await click(":nth-child(1 of .o_data_row) :nth-child(2 of .o_data_cell)");
    await contains(".o_attachment_preview iframe", { count: 0 });
    await contains(".o_attachment_preview p", { text: "No attachments linked." });
    await click(":nth-child(2 of .o_group_header)");
    await contains(".o_data_row", { count: 4 });
    await contains(".o_attachment_preview p", { text: "No attachments linked." });
    await assertSteps([
        `/web/dataset/call_kw/account.move.line/web_search_read - ${JSON.stringify({
            kwargs: {
                specification: {
                    id: {},
                    name: {},
                    move_id: { fields: { display_name: {} } },
                    move_attachment_ids: { fields: { mimetype: {} } },
                },
                offset: 0,
                order: "",
                limit: 80,
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                    bin_size: true,
                    group_by: ["move_id"],
                    default_move_id: 2,
                },
                count_limit: 10001,
                domain: [["move_id", "=", 2]],
            },
        })}`,
    ]);
    await click(":nth-child(4 of .o_data_row) :nth-child(2 of .o_data_cell)");
    await contains(".o_attachment_preview p", { count: 0 });
    await contains(
        `.o_attachment_preview iframe[data-src='/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
            getOrigin() + "/web/content/1"
        )}#pagemode=none']`
    );
    await assertSteps([], { message: "no extra rpc should be done" });
    await click(":nth-child(3 of .o_group_header)");
    await contains(".o_data_row", { count: 6 });
    // weak test, no guarantee to wait long enough for the potential attachment to change
    await contains(
        `.o_attachment_preview iframe[data-src='/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
            getOrigin() + "/web/content/1"
        )}#pagemode=none']`
    ); // The previewer content shouldn't change without clicking on another line from another account.move
    await assertSteps([
        `/web/dataset/call_kw/account.move.line/web_search_read - ${JSON.stringify({
            kwargs: {
                specification: {
                    id: {},
                    name: {},
                    move_id: { fields: { display_name: {} } },
                    move_attachment_ids: { fields: { mimetype: {} } },
                },
                offset: 0,
                order: "",
                limit: 80,
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                    bin_size: true,
                    group_by: ["move_id"],
                    default_move_id: 3,
                },
                count_limit: 10001,
                domain: [["move_id", "=", 3]],
            },
        })}`,
    ]);
    await click(":nth-child(5 of .o_data_row) :nth-child(2 of .o_data_cell)");
    await contains(":nth-child(5 of .o_data_row) :nth-child(2 of .o_data_cell) input");
    await contains(
        `.o_attachment_preview iframe[data-src='/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
            getOrigin() + "/web/content/2"
        )}#pagemode=none']`
    );
    await assertSteps([]);
    await click(":nth-child(1 of .o_data_row) :nth-child(2 of .o_data_cell)");
    await contains(".o_attachment_preview iframe", { count: 0 });
    await contains(".o_attachment_preview p");
    await assertSteps([]);
});
