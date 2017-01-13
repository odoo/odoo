odoo.define('web_editor.snippets.animation', function (require) {
'use strict';

var Class = require('web.Class');
var base = require('web_editor.base');

var registry = {};
var ready = [];

/**
 * The Animation class provides a way for executing code once a website snippet is loaded in the dom
 * and handle the case where the website edit mode is triggered.
 */
var Animation = Class.extend({
    selector: false,
    $: function () {
        return this.$el.find.apply(this.$el, arguments);
    },
    init: function (dom, editable_mode) {
        this.$el = this.$target = $(dom);
        this.start(editable_mode);
    },
    /**
     * start
     * This method is called after init
     * @param editable_mode
     */
    start: function () {},
    /**
     * stop
     * This method is called to stop the animation (e.g.: when rte is launch)
     */
    stop: function () {},
});

/**
 * Start animations when loading the website is finished and stop/restart them
 * once we enter in edit mode.
 */
base.ready().always(function () {
    _.defer(start);
});

return {
    Class: Animation,
    registry: registry,
    start: start,
    stop: stop
};

function start(editable_mode, $init_target) {
    for (var k in registry) {
        var Animation = registry[k];
        var selector = Animation.prototype.selector || "";
        var $target = $init_target ? $init_target.filter(selector) : $(selector);

        $target.each(function () {
            var $snippet = $(this);
            var animation = $snippet.data("snippet-view");
            if (!$snippet.parents("#oe_snippets").length &&
                !$snippet.parent("body").length &&
                !animation) {
                ready.push($snippet);
                $snippet.data("snippet-view", new Animation($snippet, editable_mode));
            } else if (animation) {
                animation.start(editable_mode);
            }
        });
    }
}

function stop() {
    _.each(ready, function ($snippet) {
        var animation = $snippet.data("snippet-view");
        if (animation) {
            animation.stop();
        }
    });
}
});
