odoo.define('web.keyboard_navigation_tests', function (require) {
"use strict";

const KeyboardNavigation = require('web.KeyboardNavigation');
const testUtils = require('web.test_utils');

QUnit.module('KeyboardNavigation', function () {
    QUnit.test('aria-keyshortcuts is added on elements with accesskey', async function (assert) {
        assert.expect(1);

        class KeyboardComp extends KeyboardNavigation {}
        KeyboardComp.template = owl.tags.xml`<button accesskey="o">Click Me!</button>`;
        const comp = await testUtils.createComponent(KeyboardComp, {});

        // minimum set of attribute to generate a native event that works with the mixin
        const e = new Event("keydown");
        e.key = '';
        e.altKey = true;
        comp.el.dispatchEvent(e);

        assert.ok(comp.el.hasAttribute('aria-keyshortcuts'), 'the aria-keyshortcuts is set on the button');
        comp.destroy();
    });

    QUnit.test('keep CSS position absolute for parent of overlay', async function (assert) {
        // If we change the CSS position of an 'absolute' element to 'relative',
        // we may likely change its position on the document. Since the overlay
        // CSS position is 'absolute', it will match the size and cover the
        // parent with 'absolute' > 'absolute', without altering the position
        // of the parent on the document.
        assert.expect(1);

        class KeyboardComp extends KeyboardNavigation {}
        KeyboardComp.template = owl.tags.xml`
            <button accesskey="o" style="position:absolute" t-ref="btn">Click Me!</button>
        `;
        const comp = await testUtils.createComponent(KeyboardComp, {});

        // minimum set of attribute to generate a native event that works with the mixin
        const e = new Event("keydown");
        e.key = '';
        e.altKey = true;
        comp.el.dispatchEvent(e);

        const button = comp.el;
        const btnStyle = window.getComputedStyle(button);

        assert.strictEqual(btnStyle.position, 'absolute',
            "should not have kept the CSS position of the button");

        comp.destroy();
    });
});
});
