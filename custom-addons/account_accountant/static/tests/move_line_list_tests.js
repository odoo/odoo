/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { getOrigin } from "@web/core/utils/urls";
import { click, contains } from "@web/../tests/utils";

import { start } from "@mail/../tests/helpers/test_utils";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { ROUTES_TO_IGNORE as MAIL_ROUTES_TO_IGNORE } from "@mail/../tests/helpers/webclient_setup";

const ROUTES_TO_IGNORE = [
    "/bus/im_status",
    "/mail/init_messaging",
    "/mail/load_message_failures",
    "/web/dataset/call_kw/account.move.line/get_views",
    ...MAIL_ROUTES_TO_IGNORE,
];

QUnit.module("Views", {}, function () {
    QUnit.module("MoveLineListView", {
        beforeEach: async () => {
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
        },
    });

    const OpenPreparedView = async (assert, size) => {
        const views = {
            "account.move.line,false,list": `<tree editable='bottom' js_class='account_move_line_list'>
                         <field name='id'/>
                         <field name='name'/>
                         <field name='move_id'/>
                     </tree>`,
        };
        patchUiSize({ size: size });
        const { openView } = await start({
            serverData: { views },
            mockRPC: function (route, args) {
                if (ROUTES_TO_IGNORE.includes(route)) {
                    return;
                }
                if (route.includes("/web/static/lib/pdfjs/web/viewer.html")) {
                    return Promise.resolve();
                }
                const method = args.method || route;
                assert.step(method + "/" + args.model);
            },
        });
        await openView({
            context: {
                group_by: ["move_id"],
            },
            res_model: "account.move.line",
            views: [[false, "list"]],
        });
    };

    QUnit.test("No preview on small devices", async (assert) => {
        await OpenPreparedView(assert, SIZES.XL);
        await contains(".o_move_line_list_view");
        assert.verifySteps(["web_read_group/account.move.line"]);
        // weak test, no guarantee to wait long enough for the potential attachment preview to show
        await contains(".o_attachment_preview", { count: 0 }); // The preview component shouldn't be mounted for small screens
        await click(":nth-child(1 of .o_group_header)");
        await contains(".o_data_row", { count: 2 });
        assert.verifySteps(["web_search_read/account.move.line"]);
        await click(":nth-child(1 of .o_data_row) :nth-child(2 of .o_data_cell)");
        await contains(":nth-child(1 of .o_data_row) :nth-child(2 of .o_data_cell) input");
        // weak test, no guarantee to wait long enough for the potential attachment preview to show
        await contains(".o_attachment_preview", { count: 0 }); // The preview component shouldn't be mounted for small screens even when clicking on a line without attachment
        await click(":nth-child(2 of .o_group_header)");
        await contains(".o_data_row", { count: 4 });
        assert.verifySteps(["web_search_read/account.move.line"]);
        await click(":nth-child(4 of .o_data_row) :nth-child(2 of .o_data_cell)");
        await contains(":nth-child(4 of .o_data_row) :nth-child(2 of .o_data_cell) input");
        // weak test, no guarantee to wait long enough for the potential attachment preview to show
        await contains(".o_attachment_preview", { count: 0 }); // The preview component shouldn't be mounted for small screens even when clicking on a line with attachment
        assert.verifySteps([], "no extra rpc should be done");
    });

    QUnit.test("Fetch and preview of attachments on big devices", async (assert) => {
        await OpenPreparedView(assert, SIZES.XXL);
        await contains(".o_move_line_list_view");
        assert.verifySteps(["web_read_group/account.move.line"]);
        await contains(".o_attachment_preview");
        await contains(".o_attachment_preview p", {
            text: "Choose a line to preview its attachments.",
        });
        await contains(".o_attachment_preview iframe", { count: 0 });
        await click(":nth-child(1 of .o_group_header)");
        await contains(".o_data_row", { count: 2 });
        assert.verifySteps(["web_search_read/account.move.line"]);
        await click(":nth-child(1 of .o_data_row) :nth-child(2 of .o_data_cell)");
        await contains(".o_attachment_preview iframe", { count: 0 });
        await contains(".o_attachment_preview p", { text: "No attachments linked." });
        await click(":nth-child(2 of .o_group_header)");
        await contains(".o_data_row", { count: 4 });
        await contains(".o_attachment_preview p", { text: "No attachments linked." });
        assert.verifySteps(["web_search_read/account.move.line"]);
        await click(":nth-child(4 of .o_data_row) :nth-child(2 of .o_data_cell)");
        await contains(".o_attachment_preview p", { count: 0 });
        await contains(
            `.o_attachment_preview iframe[data-src='/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
                getOrigin() + "/web/content/1"
            )}#pagemode=none']`
        );
        assert.verifySteps([], "no extra rpc should be done");
        await click(":nth-child(3 of .o_group_header)");
        await contains(".o_data_row", { count: 6 });
        // weak test, no guarantee to wait long enough for the potential attachment to change
        await contains(
            `.o_attachment_preview iframe[data-src='/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
                getOrigin() + "/web/content/1"
            )}#pagemode=none']`
        ); // The previewer content shouldn't change without clicking on another line from another account.move
        assert.verifySteps(["web_search_read/account.move.line"]);
        await click(":nth-child(5 of .o_data_row) :nth-child(2 of .o_data_cell)");
        await contains(":nth-child(5 of .o_data_row) :nth-child(2 of .o_data_cell) input");
        await contains(
            `.o_attachment_preview iframe[data-src='/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
                getOrigin() + "/web/content/2"
            )}#pagemode=none']`
        );
        assert.verifySteps([], "no extra rpc should be done");
        await click(":nth-child(1 of .o_data_row) :nth-child(2 of .o_data_cell)");
        await contains(".o_attachment_preview iframe", { count: 0 });
        await contains(".o_attachment_preview p");
        assert.verifySteps([], "no extra rpc should be done");
    });
});
