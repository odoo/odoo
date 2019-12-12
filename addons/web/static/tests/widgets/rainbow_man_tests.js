odoo.define('web.RainbowMan_tests', function (require) {
"use strict";

const RainbowMan = require('web.RainbowMan');
const testUtils = require('web.test_utils');

QUnit.module('widgets', {}, function () {

QUnit.module('RainbowMan', {
    beforeEach: function () {
        this.data = {
            message: '<div>Congrats!</div>',
            fadeout: 'nextTick',
        };
    },
}, function () {

    QUnit.test("rendering a rainbowman destroy after animation", async function (assert) {
        assert.expect(4);

        const target = document.getElementById("qunit-fixture");
        const _delays = RainbowMan.rainbowDelay;
        RainbowMan.rainbowDelay = {nextTick: 0};

        const rainbowman = await RainbowMan.display(this.data, { target });
        assert.containsOnce(target, '.o_reward');
        assert.containsOnce(rainbowman, '.o_reward_rainbow');

        assert.strictEqual(rainbowman.el.querySelector('.o_reward_msg_content').innerHTML, '<div>Congrats!</div>');
        await testUtils.nextTick();
        const ev = new AnimationEvent('animationend', {animationName: 'reward-fading-reverse'});
        rainbowman.el.dispatchEvent(ev);
        assert.containsNone(target, '.o_reward');

        RainbowMan.rainbowDelay = _delays;
        rainbowman.destroy();
    });
    QUnit.test("rendering a rainbowman destroy on click", async function (assert) {
        assert.expect(3);

        const target = document.getElementById("qunit-fixture");
        this.data.fadeout = 'no';
        const rainbowman = await RainbowMan.display(this.data, { target });

        assert.containsOnce(target, '.o_reward');
        assert.containsOnce(rainbowman, '.o_reward_rainbow');

        await testUtils.dom.click(target);
        assert.containsNone(target, '.o_reward');

        rainbowman.destroy();
    });
});
});
});
