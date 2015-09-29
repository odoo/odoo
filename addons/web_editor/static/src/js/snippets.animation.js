odoo.define('web_editor.snippets.animation', function (require) {
'use strict';

var Class = require('web.Class');
var base = require('web_editor.base');

var registry = {};
var ready = [];

var Animation = Class.extend({
    selector: false,
    $: function () {
        return this.$el.find.apply(this.$el, arguments);
    },
    init: function (dom, editable_mode) {
        this.$el = this.$target = $(dom);
        this.start(editable_mode);
    },
    /*
    *  start
    *  This method is called after init
    */
    start: function (editable_mode) {
    },
    /*
    *  stop
    *  This method is called to stop the animation (e.g.: when rte is launch)
    */
    stop: function () {
    },
});

var start = function (editable_mode, $target) {
    for (var k in registry) {
        var Animation = registry[k];
        var selector = "";
        if (Animation.prototype.selector) {
            if (selector != "") selector += ", " 
            selector += Animation.prototype.selector;
        }
        if ($target) {
            if ($target.is(selector)) selector = $target;
            else continue;
        }

        $(selector).each(function() {
            var $snipped_id = $(this);
            if (    !$snipped_id.parents("#oe_snippets").length &&
                    !$snipped_id.parent("body").length &&
                    !$snipped_id.data("snippet-view")) {
                ready.push($snipped_id);
                $snipped_id.data("snippet-view", new Animation($snipped_id, editable_mode));
            } else if ($snipped_id.data("snippet-view")) {
                $snipped_id.data("snippet-view").start(editable_mode);
            }
        });
    }
};

var stop = function () {
    $(ready).each(function() {
        var $snipped_id = $(this);
        if ($snipped_id.data("snippet-view")) {
            $snipped_id.data("snippet-view").stop();
        }
    });
};

base.ready().always(function () {
    setTimeout(function () {
        start();
    },0);
});

return {
    'Class': Animation,
    'registry': registry,
    'start': start,
    'stop': stop
};

});