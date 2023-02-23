/** @odoo-module **/

import { click, editInput, getFixture, makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

import weTestUtils from 'web_editor.test_utils';
import snippetsEditor from 'web_editor.snippet.editor';

QUnit.module("WebEditor.HtmlField", ({ beforeEach }) => {
    let serverData;
    let target;

    beforeEach(async () => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        txt: { string: "txt", type: "html", trim: true },
                    },
                    records: [{ id: 1, txt: 'Hello'}],
                },
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("fold and unfold snippets menu", async (assert) => {
        //let setFoldedHandle = null;
        //patchWithCleanup(snippetsEditor.SnippetsMenu.prototype, {
        //    init: function () {
        //        this._super(...arguments);
        //        setFoldedHandle = this.setFolded.bind(this);
        //    }
        //});
        await makeView({
            legacyParams: { withLegacyMockServer: true },
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form string="Partner">
                    <field name="txt" options="{ 'snippets': 'web_editor.snippets' }"/>
                </form>`,
            mockRPC: function (route, args) {
                // needs to be mockRPC because _performRPC has a hardcoded route for this
                if (args.model === 'ir.ui.view' && args.method === 'render_public_asset') {
                    if (args.args[0] === 'web_editor.snippets') {
                        return Promise.resolve(weTestUtils.SNIPPETS_TEMPLATE);
                    }
                }
            }
        });
        assert.ok(false);
    });
});
