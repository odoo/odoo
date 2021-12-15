/** @odoo-module alias=web.jquery_visibility_tests **/
'use strict';

const html = `
<div id="o_test_container_hidden" style="visibility: hidden;">
    <div style="visibility: visible;"></div>
</div>
<div id="o_test_container_none" style="display: none;">
    <div style="visibility: visible;"></div>
</div>`;

QUnit.module('JQuery Visibility Selectors', {
}, function () {
    QUnit.test("Should consider nested visible elements as having visibility", async function (assert) {
        $('body').append(html);

        const $hidden = $('body #o_test_container_hidden');
        const $none = $('body #o_test_container_none');

        assert.equal($hidden.find(':hasVisibility').length, 1);
        assert.equal($hidden.find(':visible:hasVisibility').length, 1);
        assert.equal($none.find(':hasVisibility').length, 1);
        assert.equal($none.find(':visible:hasVisibility').length, 0);

        $hidden.remove();
        $none.remove();
    });
});
