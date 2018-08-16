odoo.define('web.RainbowMan_tests', function (require) {
"use strict";

var RainbowMan = require('web.RainbowMan');

QUnit.module('widgets', {}, function () {

QUnit.module('RainbowMan', {
    beforeEach: function () {
        this.data = {
            message: 'Congrats!',
        };
    },
}, function () {

    QUnit.test("rendering a rainbowman", function (assert) {
        var done = assert.async();
        assert.expect(2);

        var $target = $("#qunit-fixture");

        // Create and display rainbowman
        var rainbowman = new RainbowMan(this.data);
        rainbowman.appendTo($target).then(function () {
            var $rainbow = rainbowman.$(".o_reward_rainbow");
            assert.strictEqual($rainbow.length, 1,
                "Should have displayed rainbow effect");

            assert.ok(rainbowman.$('.o_reward_msg_content').html() === 'Congrats!',
                "Card on the rainbowman should display 'Congrats!' message");

            rainbowman.destroy();
            done();
        });

    });
});
});
});
