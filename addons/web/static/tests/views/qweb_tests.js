odoo.define('web.qweb_view_tests', function (require) {
"use strict";

var qweb = require('web.qweb');
var utils = require('web.test_utils');

QUnit.module("Views", {

}, function () {
    QUnit.module("QWeb");
    QUnit.test("basic", function (assert) {
        assert.expect(13);
        var am = utils.createActionManager({
            data: {
                test: {
                    fields: {},
                    records: [],
                }
            },
            archs: {
                'test,5,qweb': '<div id="xxx"><t t-esc="ok"/></div>',
                'test,false,search': '<search/>'
            },
            mockRPC: function (route, args) {
                if (/^\/web\/dataset\/call_kw/.test(route)) {
                    switch (_.str.sprintf('%(model)s.%(method)s', args)) {
                    case 'test.qweb_render_view':
                        assert.step('fetch');
                        assert.equal(args.kwargs.view_id, 5);
                        return $.when(
                            '<div>foo' +
                                '<div data-model="test" data-method="wheee" data-id="42" data-other="5">' +
                                    '<a type="toggle" class="fa fa-caret-right">Unfold</a>' +
                                '</div>' +
                            '</div>'
                        );
                    case 'test.wheee':
                        assert.step('unfold');
                        assert.deepEqual(args.args, [42]);
                        assert.deepEqual(args.kwargs, {other: 5});
                        return $.when('<div id="sub">ok</div>');
                    }
                }
                return this._super.apply(this, arguments);
            }
        });
        try {
            var resolved = false;
            am.doAction({
                type: 'ir.actions.act_window',
                views: [[false, 'qweb']],
                res_model: 'test',
            }).then(function () { resolved = true; });
            assert.ok(resolved, "Action should have resolved synchronously");

            var $content = am.$('.o_content');
            assert.ok(/^\s*foo/.test($content.text()));
            utils.dom.click($content.find('[type=toggle]'));
            assert.equal($content.find('div#sub').text(), 'ok', 'should have unfolded the sub-item');
            utils.dom.click($content.find('[type=toggle]'));
            assert.equal($content.find('div#sub').length, 0, "should have removed the sub-item");
            utils.dom.click($content.find('[type=toggle]'));

            assert.verifySteps(['fetch', 'unfold', 'unfold']);
        } finally {
            am.destroy();
        }
    });
});
});
