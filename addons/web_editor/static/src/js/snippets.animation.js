odoo.define('web_editor.snippets.animation', function (require) {
'use strict';

var Class = require('web.Class');
var base = require('web_editor.base');

var registry = {};
var ready = [];

/**
 * The Animation class provides a way for executing code once a website DOM element is loaded in the dom
 * and handle the case where the website edit mode is triggered.
 */
var Animation = Class.extend({
    /**
     * The selector attribute, if defined, allows to automatically create an instance of this animation on
     * page load for each DOM element which matches this selector. The Animation $target element will then
     * be that particular DOM element. This should be the main way of instantiating Animation elements.
     */
    selector: false,
    /**
     * The $ method is a helper to search for DOM elements inside the animation DOM element target.
     * @param selector of the element to search in the DOM element target
     */
    $: function () {
        return this.$el.find.apply(this.$el, arguments);
    },
    /**
     * The init method starts the animation, waiting for its dependencies to be initialized.
     * The init method is called when instantiating the Animation thanks to the "new" keyword.
     * @param dom - the DOM element the animation is targeting
     * @param editable_mode - A boolean which is true if the page is in edition mode
     */
    init: function (dom, editable_mode) {
        this.$el = this.$target = $(dom);
        this._start(editable_mode);
    },
    /**
     * The willStart method initializes the resources the start method will need to properly work.
     * @param editable_mode - A boolean which is true if the page is in edition mode
     * @return A deferred which is resolved once all the resources are loaded
     */
    willStart: function (editable_mode) {
        return $.when();
    },
    /**
     * The abstract start method is intended to initialize the animation.
     * The method should not be called directly as called automatically on animation initialization and
     * on restart (@see Animation.init, @see Animation.restart).
     * @param editable_mode - A boolean which is true if the page is in edition mode
     * @param next argument will be the resources given by the willStart deferred (@see Animation.willStart)
     */
    start: function (editable_mode) {},
    /**
     * The abstract stop method is intended to destroy the animation and should basically restore the
     * target to the way it was before the start method was called.
     * Note: this method should be callable even if the start method was not called earlier.
     */
    stop: function () {},
    /**
     * The restart method stops the animation then starts it again, waiting for the eventual willStart
     * deferred.
     * @param editable_mode - A boolean which is true if the page is in edition mode
     * @return A deferred which is resolved once the Animation resources/elements are (re)loaded/(re)initialized.
     */
    restart: function (editable_mode) {
        return $.when(this.stop()).then(this._start.bind(this, editable_mode));
    },
    /**
     * The private _start method basically calls the start method after waiting for the end
     * of the willStart method.
     * @param editable_mode - A boolean which is true if the page is in edition mode
     * @return A deferred which is resolved once the Animation resources/elements are loaded/initialized.
     */
    _start: function (editable_mode) {
        return this.willStart(editable_mode).then(this.start.bind(this, editable_mode));
    },
});

/**
 * Start animations when the website loading is finished
 */
base.ready().always(function () {
    _.defer(start);
});

return {
    Class: Animation,
    registry: registry,
    start: start,
};

/**
 * The start function allows to create an Animation instance for each registered one for each DOM element
 * which matches the "selector" key of these registered animations (@see Animation.selector).
 * @param editable_mode - A boolean which is true if the page is in edition mode
 * @param $init_target (optional) - a jQuery DOM element ; if given, only initialize the animations whose
 *                                  "selector" matches it
 */
function start(editable_mode, $init_target) {
    _.each(registry, function (Animation) {
        var selector = Animation.prototype.selector || "";
        var $target = $init_target ? $init_target.filter(selector) : $(selector);

        $target.each(function () {
            var $snippet = $(this);
            var animation = $snippet.data("snippet-view");
            if (!$snippet.parents("#oe_snippets").length
                && !$snippet.parent("body").length
                && !animation) {
                ready.push($snippet);
                $snippet.data("snippet-view", new Animation($snippet, editable_mode));
            } else if (animation) {
                animation.restart(editable_mode);
            }
        });
    });
}
});
