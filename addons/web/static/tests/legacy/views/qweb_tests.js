odoo.define('web.qweb_view_tests', function (require) {
"use strict";

const utils = require('web.test_utils');
const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');

QUnit.module("Views", {

}, function () {
    QUnit.module("QWeb");
    QUnit.test("basic", async function (assert) {
        assert.expect(14);

        const serverData = {
            models: {
                test: {
                    fields: {},
                    records: [],
                }
            },
            views: {
                'test,5,qweb': '<div id="xxx"><t t-esc="ok"/></div>',
                'test,false,search': '<search/>'
            },
        };

        const mockRPC = (route, args) => {
            if (/^\/web\/dataset\/call_kw/.test(route)) {
                switch (_.str.sprintf('%(model)s.%(method)s', args)) {
                    case 'test.qweb_render_view':
                        assert.step('fetch');
                        assert.equal(args.kwargs.view_id, 5);
                        return Promise.resolve(
                            '<div>foo' +
                            '<div data-model="test" data-method="wheee" data-id="42" data-other="5">' +
                            '<a type="toggle" class="fa fa-caret-right">Unfold</a>' +
                            '</div>' +
                            '</div>'
                        );
                    case 'test.wheee':
                        assert.step('unfold');
                        assert.deepEqual(args.args, [42]);
                        assert.deepEqual(args.kwargs, { other: 5, context: {} });
                        return Promise.resolve('<div id="sub">ok</div>');
                }
            }
        };

        const webClient = await createWebClient({serverData, mockRPC});

        let resolved = false;
        const doActionProm = doAction(webClient, {
            type: 'ir.actions.act_window',
            views: [[false, 'qweb']],
            res_model: 'test',
        }).then(function () { resolved = true; });
        assert.ok(!resolved, "Action cannot be resolved synchronously");

        await doActionProm;
        assert.ok(resolved, "Action is resolved asynchronously");

        const content = webClient.el.querySelector('.o_content');
        assert.ok(/^\s*foo/.test(content.textContent));
        await utils.dom.click(content.querySelector('[type=toggle]'));
        assert.equal(content.querySelector('div#sub').textContent, 'ok', 'should have unfolded the sub-item');
        await utils.dom.click(content.querySelector('[type=toggle]'));
        assert.containsNone(content, "div#sub");
        await utils.dom.click(content.querySelector('[type=toggle]'));

        assert.verifySteps(['fetch', 'unfold', 'unfold']);
    });
});
});
