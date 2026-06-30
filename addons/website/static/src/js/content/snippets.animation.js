/**
 * Provides a way to start JS code for snippets' initialization and animations.
 */

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Add the notion of edit mode to public widgets.
 */
publicWidget.Widget.include({
    /**
     * Indicates if the widget should not be instantiated in edit. The default
     * is true, indeed most (all?) defined widgets only want to initialize
     * events and states which should not be active in edit mode (this is
     * especially true for non-website widgets).
     *
     * @type {boolean}
     */
    disabledInEditableMode: true,
    /**
     * Acts as @see Widget.events except that the events are only binded if the
     * Widget instance is instanciated in edit mode. The property is not
     * considered if @see disabledInEditableMode is false.
     */
    edit_events: null,
    /**
     * Acts as @see Widget.events except that the events are only binded if the
     * Widget instance is instanciated in readonly mode. The property only
     * makes sense if @see disabledInEditableMode is false, you should simply
     * use @see Widget.events otherwise.
     */
    read_events: null,

    /**
     * Initializes the events that will need to be binded according to the
     * given mode.
     *
     * @constructor
     * @param {Object} parent
     * @param {Object} [options]
     * @param {boolean} [options.editableMode=false]
     *        true if the page is in edition mode
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.editableMode = this.options.editableMode || false;
        var extraEvents = this.editableMode ? this.edit_events : this.read_events;
        if (extraEvents) {
            this.events = Object.assign({}, this.events || {}, extraEvents);
        }
    },
});

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

var registry = publicWidget.registry;

// TODO Let's keep this here for now: will have to move an edit mode related
// location.
// FIXME temporary hack: during edit mode, the carousel crashes sometimes when
// we hover option during a carousel cycle. This patches Bootstrap to prevent
// the crash.
const baseSelectorEngineFind = window.SelectorEngine.find;
window.SelectorEngine.find = function (...args) {
    try {
        return baseSelectorEngineFind.call(this, ...args);
    } catch {
        return [document.createElement("div")];
    }
};

export default {
    Widget: publicWidget.Widget,
    registry: registry,
};
