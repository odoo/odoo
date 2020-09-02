odoo.define('web.RainbowMan_tests', function (require) {
"use strict";

const RainbowMan = require('web.RainbowMan');
const testUtils = require("web.test_utils");

const { createComponent } = testUtils;

QUnit.module('widgets', {}, function () {

QUnit.module('RainbowMan', {
    beforeEach: function () {
        this.data = {
            message: 'Congrats!',
        };
    },
}, function () {

    QUnit.test("rendering a rainbowman", async function (assert) {
        assert.expect(2);

        const target = document.querySelector("#qunit-fixture");

        // Create and display rainbowman
        const rainbowman = await createComponent(RainbowMan, {
            props: this.data
        });
        await rainbowman.mount(target);
        const rainbow = rainbowman.el.querySelectorAll(".o_reward_rainbow");
        assert.strictEqual(rainbow.length, 1,
            "Should have displayed rainbow effect");

        assert.ok(rainbowman.el.querySelector('.o_reward_msg_content').innerText === 'Congrats!',
            "Card on the rainbowman should display 'Congrats!' message");

        rainbowman.destroy();
    });
});
});
});
