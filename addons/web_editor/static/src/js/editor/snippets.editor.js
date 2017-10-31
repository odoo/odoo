odoo.define('web_editor.snippet.editor', function (require) {
'use strict';

var core = require('web.core');
var dom = require('web.dom');
var Widget = require('web.Widget');
var options = require('web_editor.snippets.options');

var _t = core._t;

var globalSelector = {
    closest: function () { return $(); },
    all: function () { return $(); },
    is: function () { return false; },
};

/**
 * Management of the overlay and option list for a snippet.
 */
var SnippetEditor = Widget.extend({
    template: 'web_editor.snippet_overlay',
    xmlDependencies: ['/web_editor/static/src/xml/snippets.xml'],
    events: {
        'click .oe_snippet_parent': '_onParentButtonClick',
        'click .oe_snippet_clone': '_onCloneClick',
        'click .oe_snippet_remove': '_onRemoveClick',
    },
    custom_events: {
        cover_update: '_onCoverUpdate',
        option_update: '_onOptionUpdate',
    },

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Element} target
     * @param templateOptions
     */
    init: function (parent, target, templateOptions) {
        this._super.apply(this, arguments);
        this.$target = $(target);
        this.$target.data('snippet-editor', this);
        this.templateOptions = templateOptions;
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];

        // Hide parent button if no parent
        var $parent = globalSelector.closest(this.$target.parent());
        if (!$parent.length) {
            this.$('.oe_snippet_parent').remove();
        }

        // Initialize the associated options (see snippets.options.js)
        defs.push(this._initializeOptions());

        // Initialize move/clone/remove buttons
        if (!this.$target.parent().is(':o_editable')) {
            this.$el.find('.oe_snippet_move, .oe_snippet_clone, .oe_snippet_remove').remove();
        } else {
            this.dropped = false;
            this.$el.draggable({
                greedy: true,
                appendTo: 'body',
                cursor: 'move',
                handle: '.oe_snippet_move',
                cursorAt: {
                    left: 18,
                    top: 14
                },
                helper: function () {
                    var $clone = $(this).clone().css({width: '24px', height: '24px', border: 0});
                    $clone.find('.oe_overlay_options >:not(:contains(.oe_snippet_move)), .o_handle').remove();
                    $clone.find(':not(.glyphicon)').css({position: 'absolute', top: 0, left: 0});
                    $clone.appendTo('body').removeClass('hidden');
                    return $clone;
                },
                start: _.bind(self._onDragAndDropStart, self),
                stop: _.bind(self._onDragAndDropStop, self)
            });
        }

        return $.when.apply($, defs);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$target.removeData('snippet-editor');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Notifies all the associated snippet options that the snippet has just
     * been dropped in the page.
     */
    buildSnippet: function () {
        for (var i in this.styles) {
            this.styles[i].onBuilt();
        }
    },
    /**
     * Notifies all the associated snippet options that the template which
     * contains the snippet is about to be saved.
     */
    cleanForSave: function () {
        if (this.isDestroyed()) {
            return;
        }
        _.each(this.styles, function (option) {
            option.cleanForSave();
        });
    },
    /**
     * Makes the editor overlay cover the associated snippet.
     */
    cover: function () {
        var offset = this.$target.offset();
        var manipulatorOffset = this.$el.parent().offset();
        offset.top -= manipulatorOffset.top;
        offset.left -= manipulatorOffset.left;
        this.$el.css({
            width: this.$target.outerWidth(),
            left: offset.left,
            top: offset.top,
        });
        this.$('.o_handles').css('height', this.$target.outerHeight());
        this.$el.toggleClass('o_top_cover', offset.top < 15);
    },
    /**
     * Displays/Hides the editor overlay and notifies the associated snippet
     * options. Note: when it is displayed, this is here that the parent
     * snippet options are moved to the editor overlay.
     *
     * @param {boolean} focus - true to display, false to hide
     */
    toggleFocus: function (focus) {
        var do_action = (focus ? _do_action_focus : _do_action_blur);

        // Attach own and parent options on the current overlay
        var $style_button = this.$el.find('.oe_options');
        var $ul = $style_button.find('ul:first');
        var $headers = $ul.find('.dropdown-header:data(editor)');
        _.each($headers, (function (el) {
            var $el = $(el);
            var styles = _.values($el.data('editor').styles);
            if ($el.data('editor') !== this) {
                styles = _.filter(styles, function (option) { return !option.preventChildPropagation; });
            }

            var count = 0;
            _.each(_.sortBy(styles, '__order').reverse(), function (style) {
                if (do_action(style, $el)) {
                    count++;
                }
            });
            $el.toggleClass('hidden', count === 0);
        }).bind(this));

        // Activate the overlay
        $style_button.toggleClass('hidden', $ul.children(':not(.o_main_header):not(.divider):not(.hidden)').length === 0);
        this.cover();
        this.$el.toggleClass('oe_active', !!focus);

        function _do_action_focus(style, $dest) {
            style.$el.insertAfter($dest);
            style.onFocus();
            return (style.$el.length > 0);
        }
        function _do_action_blur(style, $dest) {
            style.$el.detach();
            style.onBlur();
            return false;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * DOMElements have a default name which appears in the overlay when they
     * are being edited. This method retrieves this name; it can be defined
     * directly in the DOM thanks to the `data-name` attribute.
     *
     * @private
     */
    _getName: function () {
        if (this.$target.data('name') !== undefined) {
            return this.$target.data('name');
        }
        if (this.$target.parent('.row').length) {
            return _t("Column");
        }
        return _t("Block");
    },
    /**
     * Instantiates the snippet's options.
     *
     * @private
     */
    _initializeOptions: function () {
        var self = this;
        var $styles = this.$el.find('.oe_options');
        var $ul = $styles.find('ul:first');
        this.styles = {};
        this.selectorSiblings = [];
        this.selectorChildren = [];

        var i = 0;
        $ul.append($('<li/>', {class: 'dropdown-header o_main_header', text: this._getName()}).data('editor', this));
        var defs = _.map(this.templateOptions, function (val, option_id) {
            if (!val.selector.is(self.$target)) {
                return;
            }
            if (val['drop-near']) self.selectorSiblings.push(val['drop-near']);
            if (val['drop-in']) self.selectorChildren.push(val['drop-in']);

            var optionName = val.option;
            var $el = val.$el.children('li').clone(true).addClass('snippet-option-' + optionName);
            var option = new (options.registry[optionName] || options.Class)(
                self,
                val.base_target ? self.$target.find(val.base_target).eq(0) : self.$target,
                self.$el,
                val.data
            );
            self.styles[optionName || _.uniqueId('option')] = option;
            option.__order = i++;
            return option.attachTo($el);
        });
        $ul.append($('<li/>', {class: 'divider'}));

        var $parents = this.$target.parents();
        _.each($parents, function (parent) {
            var parentEditor = $(parent).data('snippet-editor');
            if (parentEditor) {
                for (var styleName in parentEditor.styles) {
                    if (!parentEditor.styles[styleName].preventChildPropagation) {
                        $ul.append($('<li/>', {class: 'dropdown-header o_parent_editor_header', text: parentEditor._getName()}).data('editor', parentEditor));
                        break;
                    }
                }
            }
        });

        if (!this.selectorSiblings.length && !this.selectorChildren.length) {
            this.$el.find('.oe_snippet_move, .oe_snippet_clone').addClass('hidden');
        }

        this.$el.find('[data-toggle="dropdown"]').dropdown();

        return $.when.apply($, defs);
    },
    /**
     * Removes the associated snippet from the DOM and destroys the associated
     * editor (itself).
     *
     * @private
     */
    _removeSnippet: function () {
        this.toggleFocus(false);

        this.trigger_up('call_for_each_child_snippet', {
            $snippet: this.$target,
            callback: function (editor, $snippet) {
                for (var i in editor.styles) {
                    editor.styles[i].onRemove();
                }
            },
        });

        var $parent = this.$target.parent();
        this.$target.find('*').andSelf().tooltip('destroy');
        this.$target.remove();
        this.$el.remove();

        var node = $parent[0];
        if (node && node.firstChild) {
            $.summernote.core.dom.removeSpace(node, node.firstChild, 0, node.lastChild, 1);
            if (!node.firstChild.tagName && node.firstChild.textContent === ' ') {
                node.removeChild(node.firstChild);
            }
        }

        if ($parent.closest(':data("snippet-editor")').length) {
            while (!$parent.data('snippet-editor')) {
                var $nextParent = $parent.parent();
                if ($parent.children().length === 0 && $parent.text().trim() === '' && !$parent.hasClass('oe_structure')) {
                    $parent.remove();
                }
                $parent = $nextParent;
            }
            if ($parent.children().length === 0 && $parent.text().trim() === '' && !$parent.hasClass('oe_structure')) {
                _.defer(function () {
                    $parent.data('snippet-editor')._removeSnippet();
                });
            }
        }

        // clean editor if they are image or table in deleted content
        $('.note-control-selection').hide();
        $('.o_table_handler').remove();

        this.trigger_up('snippet_removed');
        this.destroy();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the 'clone' button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onCloneClick: function (ev) {
        ev.preventDefault();
        var $clone = this.$target.clone(false);

        this.trigger_up('request_history_undo_record', {$target: this.$target});

        this.$target.after($clone);
        this.trigger_up('call_for_each_child_snippet', {
            $snippet: $clone,
            callback: function (editor, $snippet) {
                for (var i in editor.styles) {
                    editor.styles[i].onClone({
                        isCurrent: ($snippet.is($clone)),
                    });
                }
            },
        });
    },
    /**
     * Called when the overlay dimensions/positions should be recomputed.
     *
     * @private
     */
    _onCoverUpdate: function () {
        this.cover();
    },
    /**
     * Called when the snippet is starting to be dragged thanks to the 'move'
     * button.
     *
     * @private
     */
    _onDragAndDropStart: function () {
        var self = this;
        self.size = {
            width: self.$target.width(),
            height: self.$target.height()
        };
        self.$target.after('<div class="oe_drop_clone" style="display: none;"/>');
        self.$target.detach();
        self.$el.addClass('hidden');

        var $selectorSiblings;
        for (var i = 0 ; i < self.selectorSiblings.length ; i++) {
            if (!$selectorSiblings) $selectorSiblings = self.selectorSiblings[i].all();
            else $selectorSiblings = $selectorSiblings.add(self.selectorSiblings[i].all());
        }
        var $selectorChildren;
        for (i = 0 ; i < self.selectorChildren.length ; i++) {
            if (!$selectorChildren) $selectorChildren = self.selectorChildren[i].all();
            else $selectorChildren = $selectorChildren.add(self.selectorChildren[i].all());
        }

        this.trigger_up('go_to_parent', {$snippet: this.$target});
        this.trigger_up('activate_insertion_zones', {
            $selectorSiblings: $selectorSiblings,
            $selectorChildren: $selectorChildren,
        });

        $('body').addClass('move-important');

        $('.oe_drop_zone').droppable({
            over: function () {
                $('.oe_drop_zone.hide').removeClass('hide');
                $(this).addClass('hide').first().after(self.$target);
                self.dropped = true;
            },
            out: function () {
                $(this).removeClass('hide');
                self.$target.detach();
                self.dropped = false;
            },
        });
    },
    /**
     * Called when the snippet is dropped after being dragged thanks to the
     * 'move' button.
     *
     * @private
     */
    _onDragAndDropStop: function () {
        var self = this;

        $('.oe_drop_zone').droppable('destroy').remove();

        var prev = this.$target.first()[0].previousSibling;
        var next = this.$target.last()[0].nextSibling;
        var $parent = this.$target.parent();

        var $clone = $('.oe_drop_clone');
        if (prev === $clone[0]) {
            prev = $clone[0].previousSibling;
        } else if (next === $clone[0]) {
            next = $clone[0].nextSibling;
        }
        $clone.after(this.$target);

        this.$el.removeClass('hidden');
        $('body').removeClass('move-important');
        $clone.remove();

        if (this.dropped) {
            this.trigger_up('request_history_undo_record', {$target: this.$target});

            if (prev) {
                this.$target.insertAfter(prev);
            } else if (next) {
                this.$target.insertBefore(next);
            } else {
                $parent.prepend(this.$target);
            }

            for (var i in this.styles) {
                this.styles[i].onMove();
            }
        }

        self.trigger_up('drag_and_drop_stop', {
            $snippet: self.$target,
        });
    },
    /**
     * Called when a child editor/option asks for another option to perform a
     * specific action/react to a specific event.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onOptionUpdate: function (ev) {
        // If multiple option names are given, we suppose it should not be
        // propagated to parent editor
        if (ev.data.optionNames) {
            ev.stopPropagation();
            var self = this;
            _.each(ev.data.optionNames, function (name) {
                var option = self.styles[name];
                if (option) {
                    option.notify(ev.data.name, ev.data.data);
                }
            });
        }
        // If one option name is given, we suppose it should be handle by the
        // first parent editor which can do it
        if (ev.data.optionName) {
            var option = this.styles[ev.data.optionName];
            if (option) {
                ev.stopPropagation();
                option.notify(ev.data.name, ev.data.data);
            }
        }
    },
    /**
     * Called when the 'parent' button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onParentButtonClick: function (ev) {
        ev.preventDefault();
        this.trigger_up('go_to_parent', {
            $snippet: this.$target,
        });
    },
    /**
     * Called when the 'remove' button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onRemoveClick: function (ev) {
        ev.preventDefault();
        this.trigger_up('request_history_undo_record', {$target: this.$target});
        this._removeSnippet();
    },
});

/**
 * Management of drag&drop menu and snippet related behaviors in the page.
 */
var SnippetsMenu = Widget.extend({
    id: 'oe_snippets',
    activeSnippets: [],
    custom_events: {
        activate_insertion_zones: '_onActivateInsertionZones',
        call_for_each_child_snippet: '_onCallForEachChildSnippet',
        deactivate_snippet: '_onDeactivateSnippet',
        drag_and_drop_stop: '_onDragAndDropStop',
        go_to_parent: '_onGoToParent',
        snippet_removed: '_onSnippetRemoved',
    },

    /**
     * @constructor
     */
    init: function (parent, $editable) {
        this._super.apply(this, arguments);

        this.$editable = $editable;
        this.$activeSnippet = false;
        this.snippetEditors = [];
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        var $document = $(document);
        var $window = $(window);

        // Fetch snippet templates and compute it
        var url = this._getSnippetURL();
        defs.push(this._rpc({route: url}).then(function (html) {
            return self._computeSnippetTemplates(html);
        }));

        // Prepare snippets editor environment
        this.$snippetEditorArea = $('<div/>', {
            id: 'oe_manipulators',
        }).insertAfter(this.$el);

        // Active snippet editor on click in the page
        var lastClickedElement;
        $document.on('click.snippets_menu', '*', function (ev) {
            var srcElement = ev.srcElement || (ev.originalEvent && (ev.originalEvent.originalTarget || ev.originalEvent.target) || ev.target);
            if (lastClickedElement === srcElement || !srcElement) {
                return;
            }
            lastClickedElement = srcElement;
            _.defer(function () {
                lastClickedElement = false;
            });

            var $target = $(srcElement);
            if ($target.closest('.oe_overlay, .note-popover').length) {
                return;
            }
            self._activateSnippet($target);
        });

        core.bus.on('deactivate_snippet', this, this._onDeactivateSnippet);
        core.bus.on('snippet_editor_clean_for_save', this, this._onCleanForSaveDemand);

        // Some summernote customization
        var _isNotBreakable = $.summernote.core.dom.isNotBreakable;
        $.summernote.core.dom.isNotBreakable = function (node) {
            return _isNotBreakable(node) || $(node).is('div') || globalSelector.is($(node));
        };

        // Adapt overlay covering when the window is resized / content changes
        var debouncedCoverUpdate = _.debounce(function () {
            self._updateCurrentSnippetEditorOverlay();
        }, 200);
        $window.on('resize.snippets_menu', debouncedCoverUpdate);
        $window.on('content_changed.snippets_menu', debouncedCoverUpdate);

        // On keydown add a class on the active overlay to hide it and show it
        // again when the mouse moves
        $document.on('keydown.snippets_menu', function () {
            if (self.$activeSnippet && self.$activeSnippet.data('snippet-editor')) {
                self.$activeSnippet.data('snippet-editor').$el.addClass('o_keypress');
            }
        });
        $document.on('mousemove.snippets_menu', function () {
            if (self.$activeSnippet && self.$activeSnippet.data('snippet-editor')) {
                self.$activeSnippet.data('snippet-editor').$el.removeClass('o_keypress');
            }
        });

        // Auto-selects text elements with a specific class and remove this
        // on text changes
        $document.on('click.snippets_menu', '.o_default_snippet_text', function (ev) {
            $(ev.target).selectContent();
        });
        $document.on('keyup.snippets_menu', function () {
            var r = $.summernote.core.range.create();
            $(r && r.sc).closest('.o_default_snippet_text').removeClass('o_default_snippet_text');
        });

        return $.when.apply($, defs).then(function () {
            // Trigger a resize event once entering edit mode as the snippets
            // menu will take part of the screen width (delayed because of
            // animation). (TODO wait for real animation end)
            setTimeout(function () {
                $window.trigger('resize');
            }, 1000);
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$snippetEditorArea.remove();
        $(window).off('.snippets_menu');
        $(document).off('.snippets_menu');
        core.bus.off('deactivate_snippet', this, this._onDeactivateSnippet);
        core.bus.off('snippet_editor_clean_for_save', this, this._onCleanForSaveDemand);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Prepares the page so that it may be saved:
     * - Asks the snippet editors to clean their associated snippet
     * - Remove the 'contentEditable' attributes
     */
    cleanForSave: function () {
        this.trigger_up('ready_to_clean_for_save');
        _.each(this.snippetEditors, function (snippetEditor) {
            snippetEditor.cleanForSave();
        });
        this.$editable.find('[contentEditable]')
            .removeAttr('contentEditable')
            .removeProp('contentEditable');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Creates drop zones in the DOM (locations where snippets may be dropped).
     * Those locations are determined thanks to the two types of given DOM.
     *
     * @private
     * @param {jQuery} [$selectorSiblings]
     *        elements which must have siblings drop zones
     * @param {jQuery} [$selectorChildren]
     *        elements which must have child drop zones between each of existing
     *        child
     */
    _activateInsertionZones: function ($selectorSiblings, $selectorChildren) {
        var zone_template = $('<div/>', {
            class: 'oe_drop_zone oe_insert',
        });

        if ($selectorChildren) {
            $selectorChildren.each(function () {
                var $zone = $(this);
                var css = window.getComputedStyle(this);
                var float = css.float || css.cssFloat;
                var $drop = zone_template.clone();

                $zone.append($drop);
                var node = $drop[0].previousSibling;
                var test = !!(node && ((!node.tagName && node.textContent.match(/\S/)) ||  node.tagName === 'BR'));
                if (test) {
                    $drop.addClass('oe_vertical').css({
                        height: parseInt(window.getComputedStyle($zone[0]).lineHeight),
                        float: 'none',
                        display: 'inline-block',
                    });
                } else if (float === 'left' || float === 'right') {
                    $drop.addClass('oe_vertical').css('height', Math.max(Math.min($zone.outerHeight(), $zone.children().last().outerHeight()), 30));
                }

                $drop = $drop.clone();

                $zone.prepend($drop);
                node = $drop[0].nextSibling;
                test = !!(node && ((!node.tagName && node.textContent.match(/\S/)) ||  node.tagName === 'BR'));
                if (test) {
                    $drop.addClass('oe_vertical').css({
                        height: parseInt(window.getComputedStyle($zone[0]).lineHeight),
                        float: 'none',
                        display: 'inline-block'
                    });
                } else if (float === 'left' || float === 'right') {
                    $drop.addClass('oe_vertical').css('height', Math.max(Math.min($zone.outerHeight(), $zone.children().first().outerHeight()), 30));
                }
                if (test) {
                    $drop.css({'float': 'none', 'display': 'inline-block'});
                }
            });

            // add children near drop zone
            $selectorSiblings = $(_.uniq(($selectorSiblings || $()).add($selectorChildren.children()).get()));
        }

        if ($selectorSiblings) {
            $selectorSiblings.filter(':not(.oe_drop_zone):not(.oe_drop_clone)').each(function () {
                var $zone = $(this);
                var $drop;
                var css = window.getComputedStyle(this);
                var float = css.float || css.cssFloat;

                if ($zone.prev('.oe_drop_zone:visible').length === 0) {
                    $drop = zone_template.clone();
                    if (float === 'left' || float === 'right') {
                        $drop.addClass('oe_vertical').css('height', Math.max(Math.min($zone.outerHeight(), $zone.prev().outerHeight() || Infinity), 30));
                    }
                    $zone.before($drop);
                }
                if ($zone.next('.oe_drop_zone:visible').length === 0) {
                    $drop = zone_template.clone();
                    if (float === 'left' || float === 'right') {
                        $drop.addClass('oe_vertical').css('height', Math.max(Math.min($zone.outerHeight(), $zone.next().outerHeight() || Infinity), 30));
                    }
                    $zone.after($drop);
                }
            });
        }

        var count;
        var $zones;
        do {
            count = 0;
            $zones = this.$editable.find('.oe_drop_zone > .oe_drop_zone').remove(); // no recursive zones
            count += $zones.length;
            $zones.remove();
        } while (count > 0);

        // Cleaning consecutive zone and up zones placed between floating or
        // inline elements. We do not like these kind of zones.
        $zones = this.$editable.find('.oe_drop_zone:not(.oe_vertical)');
        $zones.each(function () {
            var zone = $(this);
            var prev = zone.prev();
            var next = zone.next();
            // remove consecutive zone
            if (prev.is('.oe_drop_zone') || next.is('.oe_drop_zone')) {
                zone.remove();
                return;
            }
            var float_prev = prev.css('float')   || 'none';
            var float_next = next.css('float')   || 'none';
            var disp_prev  = prev.css('display') ||  null;
            var disp_next  = next.css('display') ||  null;
            if ((float_prev === 'left' || float_prev === 'right')
             && (float_next === 'left' || float_next === 'right')) {
                zone.remove();
            } else if (disp_prev !== null && disp_next !== null
             && disp_prev !== 'block' && disp_next !== 'block') {
                zone.remove();
            }
        });
    },
    /**
     * Disable the overlay editor of the active snippet and activate the new one
     * if given.
     * Note 1: if the snippet editor associated to the given snippet is not
     *         created yet, this method will create it.
     * Note 2: if the given DOM element is not a snippet (no editor option), the
     *         first parent which is one is used instead.
     *
     * @param {jQuery|false} $snippet
     *        The DOM element whose editor need to be enabled. Only disable the
     *        current one if false is given.
     * @returns {Deferred} (might be async when an editor must be created)
     */
    _activateSnippet: function ($snippet) {
        if ($snippet) {
            if (!globalSelector.is($snippet)) {
                $snippet = globalSelector.closest($snippet);
            }
            if (this.$activeSnippet && this.$activeSnippet[0] === $snippet[0]) {
                return $.when();
            }
        }
        if (this.$activeSnippet) {
            if (this.$activeSnippet.data('snippet-editor')) {
                this.$activeSnippet.data('snippet-editor').toggleFocus(false);
            }
            this.$activeSnippet = false;
        }
        if ($snippet && $snippet.length) {
            var self = this;
            return this._createSnippetEditor($snippet).then(function () {
                self.$activeSnippet = $snippet;
                if (self.$activeSnippet.data('snippet-editor')) {
                    self.$activeSnippet.data('snippet-editor').toggleFocus(true);
                }
            });
        }
        return $.when();
    },
    /**
     * Updates the cover dimensions of the current snippet editor.
     *
     * @private
     */
    _updateCurrentSnippetEditorOverlay: function () {
        if (this.$activeSnippet && this.$activeSnippet.data('snippet-editor')) {
            this.$activeSnippet.data('snippet-editor').cover();
        }
    },
    /**
     * Calls a given callback 'on' the given snippet and all its child ones if
     * any (DOM element with options).
     *
     * Note: the method creates the snippet editors if they do not exist yet.
     *
     * @private
     * @param {jQuery} $snippet
     * @param {function} callback
     *        Given two arguments: the snippet editor associated to the snippet
     *        being managed and the DOM element of this snippet.
     * @returns {Deferred} (might be async if snippet editors need to be created
     *                     and/or the callback is async)
     */
    _callForEachChildSnippet: function ($snippet, callback) {
        var self = this;
        var defs = _.map($snippet.add(globalSelector.all($snippet)), function (el) {
            var $snippet = $(el);
            return self._createSnippetEditor($snippet).then(function (editor) {
                if (editor) {
                    return callback.call(self, editor, $snippet);
                }
            });
        });
        return $.when.apply($, defs);
    },
    /**
     * Creates and returns a set of helper functions which can help finding
     * snippets in the DOM which match some parameters (typically parameters
     * given by a snippet option). The functions are:
     *
     * - `is`: to determine if a given DOM is a snippet that matches the
     *         parameters
     *
     * - `closest`: find closest parent (or itself) of a given DOM which is a
     *              snippet that matches the parameters
     *
     * - `all`: find all snippets in the DOM that match the parameters
     *
     * See implementation for function details.
     *
     * @private
     * @param {string} include
     *        jQuery selector that DOM elements must match to be considered as
     *        potential snippet.
     * @param {string} exclude
     *        jQuery selector that DOM elements must *not* match the be
     *        considered as potential snippet.
     * @param {string|false} target
     *        jQuery selector that at least one child of a DOM element must
     *        match to that DOM element be considered as a potential snippet.
     * @param {boolean} noCheck
     *        true if DOM elements which are technically not in an editable
     *        environment may be considered.
     * @param {boolean} isChildren
     *        when the DOM elements must be in an editable environment to be
     *        considered (@see noCheck), this is true if the DOM elements'
     *        parent must also be in an editable environment to be considered.
     */
    _computeSelectorFunctions : function (include, exclude, target, noCheck, isChildren) {
        var self = this;

        // Convert the selector for elements to include into a list
        var selectorList = _.compact(include.split(/\s*,\s*/));

        // Convert the selector for elements to exclude into a list
        var excludeList = _.compact(exclude.split(/\s*,\s*/));
        excludeList.push('.o_snippet_not_selectable');

        // Prepare the condition that will be added to each subselector for
        // elements to include: 'not the elements to exclude and only the
        // editable ones if needed'
        var selectorConditions = _.map(excludeList, function (exc) {
            return ':not(' + exc + ')';
        }).join('');
        if (target) {
            selectorConditions += ':has(' + target + ')';
        }
        if (!noCheck) {
            selectorConditions = ':o_editable' + selectorConditions;
        }

        // (Re)join the subselectors
        var selector =_.map(selectorList, function (s) {
            return s + selectorConditions;
        }).join(', ');

        // Prepare the functions
        var functions = {
            is: function ($from) {
                return $from.is(selector);
            },
        };
        if (noCheck) {
            functions.closest = function ($from, parentNode) {
                return $from.closest(selector, parentNode);
            };
            functions.all = function ($from) {
                return $from ? dom.cssFind($from, selector) : $(selector);
            };
        } else {
            functions.closest = function ($from, parentNode) {
                var parents = self.$editable.get();
                return $from.closest(selector, parentNode).filter(function () {
                    var node = this;
                    while (node.parentNode) {
                        if (parents.indexOf(node)!==-1) {
                            return true;
                        }
                        node = node.parentNode;
                    }
                    return false;
                });
            };
            functions.all = isChildren ? function ($from) {
                return dom.cssFind($from || self.$editable, selector);
            } : function ($from) {
                $from = $from || self.$editable;
                return $from.filter(selector).add(dom.cssFind($from, selector));
            };
        }
        return functions;
    },
    /**
     * Processes the given snippet template to register snippet options, creates
     * draggable thumbnail, etc.
     *
     * @private
     * @param {string} html
     */
    _computeSnippetTemplates: function (html) {
        var self = this;
        var $html = $(html);
        var $scroll = $html.siblings('#o_scroll');

        $html.find('[data-oe-type="snippet"]').each(function () {
            $(this).children()
                .attr('data-oe-type', 'snippet')
                .attr('data-oe-thumbnail', $(this).data('oe-thumbnail'));
        });

        this.templateOptions = [];
        var selectors = [];
        var $styles = $html.find('[data-selector]');
        $styles.each(function () {
            var $style = $(this);
            var selector = $style.data('selector');
            var exclude = $style.data('exclude') || '';
            var target = $style.data('target');
            var noCheck = $style.data('no-check');
            var option_id = $style.data('js');
            var option = {
                'option': option_id,
                'base_selector': selector,
                'base_exclude': exclude,
                'base_target': target,
                'selector': self._computeSelectorFunctions(selector, exclude, target, noCheck),
                '$el': $style,
                'drop-near': $style.data('drop-near') && self._computeSelectorFunctions($style.data('drop-near'), '', false, noCheck, true),
                'drop-in': $style.data('drop-in') && self._computeSelectorFunctions($style.data('drop-in'), '', false, noCheck),
                'data': $style.data(),
            };
            self.templateOptions.push(option);
            selectors.push(option.selector);
        });
        $styles.addClass('hidden');

        globalSelector.closest = function ($from) {
            var $temp;
            var $target;
            for (var i = 0, len = selectors.length ; i < len ; i++) {
                $temp = selectors[i].closest($from, $target && $target[0]);
                if ($temp.length) {
                    $target = $temp;
                }
            }
            return $target || $();
        };
        globalSelector.all = function ($from) {
            var $target = $();
            for (var i = 0, len = selectors.length ; i < len ; i++) {
                $target = $target.add(selectors[i].all($from));
            }
            return $target;
        };
        globalSelector.is = function ($from) {
            for (var i = 0, len = selectors.length ; i < len ; i++) {
                if (selectors[i].is($from)) {
                    return true;
                }
            }
            return false;
        };

        this.$snippets = $scroll.find('.o_panel_body').children()
            .addClass('oe_snippet')
            .each(function () {
                var $snippet = $(this);
                var name = $snippet.attr('name');
                var $sbody = $snippet.children(':not(.oe_snippet_thumbnail)').addClass('oe_snippet_body');

                // Associate in-page snippets to their name
                if ($sbody.length) {
                    var snippetClasses = $sbody.attr('class').match(/s_[^ ]+/g);
                    if (snippetClasses && snippetClasses.length) {
                        snippetClasses = '.' + snippetClasses.join('.');
                    }
                    $(snippetClasses).data('name', name);
                    $sbody.data('name', name);
                }

                // Create the thumbnail
                if ($snippet.find('.oe_snippet_thumbnail').length) {
                    return; // Compatibility with elements which do not use 't-snippet'
                }
                var $thumbnail = $(_.str.sprintf(
                    '<div class="oe_snippet_thumbnail">'+
                        '<div class="oe_snippet_thumbnail_img" style="background-image: url(%s);"/>'+
                        '<span class="oe_snippet_thumbnail_title">%s</span>'+
                    '</div>',
                    $snippet.find('[data-oe-thumbnail]').data('oeThumbnail'),
                    name
                ));
                $snippet.prepend($thumbnail);

                // Create the install button (t-install feature) if necessary
                var moduleID = $snippet.data('moduleId');
                if (moduleID) {
                    $snippet.addClass('o_snippet_install');
                    var $installBtn = $('<a/>', {
                        class: 'btn btn-primary btn-sm o_install_btn',
                        target: '_blank',
                        href: '/web#id=' + moduleID + '&view_type=form&model=ir.module.module&action=base.open_module_tree',
                        text: _t("Install"),
                    });
                    $thumbnail.append($installBtn);
                }
            })
            .not('[data-module-id]');

        // Hide scroll if no snippets defined
        if (!this.$snippets.length) {
            this.$el.detach();
        }
        $('body').toggleClass('editor_has_snippets', this.$snippets.length > 0);

        // Register the text nodes that needs to be auto-selected on click
        this._registerDefaultTexts();

        // Remove branding from template
        _.each($html.find('[data-oe-model], [data-oe-type]'), function (el) {
            for (var k = 0 ; k < el.attributes.length ; k++) {
                if (el.attributes[k].name.indexOf('data-oe-') === 0) {
                    $(el).removeAttr(el.attributes[k].name);
                    k--;
                }
            }
        });

        // Force non editable part to contentEditable=false
        $html.find('.o_not_editable').attr('contentEditable', false);

        // Add the computed template and make elements draggable
        this.$el.html($html);
        this._makeSnippetDraggable(this.$snippets);
        this._disableUndroppableSnippets();
    },
    /**
     * Creates a snippet editor to associated to the given snippet. If the given
     * snippet already has a linked snippet editor, the function only returns
     * that one.
     * The function also instantiates a snippet editor for all snippet parents
     * as a snippet editor must be able to display the parent snippet options.
     *
     * @private
     * @param {jQuery} $snippet
     * @returns {Deferred<SnippetEditor>}
     */
    _createSnippetEditor: function ($snippet) {
        var self = this;
        var snippetEditor = $snippet.data('snippet-editor');
        if (snippetEditor) {
            return $.when(snippetEditor);
        }

        var def;
        var $parent = globalSelector.closest($snippet.parent());
        if ($parent.length) {
            def = this._createSnippetEditor($parent);
        }

        return $.when(def).then(function (parentEditor) {
            snippetEditor = new SnippetEditor(parentEditor || self, $snippet, self.templateOptions);
            self.snippetEditors.push(snippetEditor);
            return snippetEditor.appendTo(self.$snippetEditorArea);
        }).then(function () {
            return snippetEditor;
        });
    },
    /**
     * There may be no location where some snippets might be dropped. This mades
     * them appear disabled in the menu.
     *
     * @todo make them undraggable
     * @private
     */
    _disableUndroppableSnippets: function () {
        var self = this;
        var cache = {};
        this.$snippets.each(function () {
            var $snippet = $(this);
            var $snippet_body = $snippet.find('.oe_snippet_body');

            var check = false;
            _.each(self.templateOptions, function (option, k) {
                if (check || !($snippet_body.is(option.base_selector) && !$snippet_body.is(option.base_exclude))) return;

                cache[k] = cache[k] || {
                    'drop-near': option['drop-near'] ? option['drop-near'].all().length : 0,
                    'drop-in': option['drop-in'] ? option['drop-in'].all().length : 0
                };
                check = (cache[k]['drop-near'] || cache[k]['drop-in']);
            });

            $snippet.toggleClass('o_disabled', !check);
        });
    },
    /**
     * Returns the URL where to find the snippets template. This URL might have
     * been set in the global 'snippetsURL' variable, otherwise this function
     * returns a default one.
     *
     * @private
     * @returns {string}
     */
    _getSnippetURL: function () {
        return odoo.snippetsURL || '/web_editor/snippets';
    },
    /**
     * Make given snippets be draggable/droppable thanks to their thumbnail.
     *
     * @private
     * @param {jQuery} $snippets
     */
    _makeSnippetDraggable: function ($snippets) {
        var self = this;
        var $tumb = $snippets.find('.oe_snippet_thumbnail_img:first');
        var left = $tumb.outerWidth()/2;
        var top = $tumb.outerHeight()/2;
        var $toInsert, dropped, $snippet;

        $snippets.draggable({
            greedy: true,
            helper: 'clone',
            zIndex: '1000',
            appendTo: 'body',
            cursor: 'move',
            handle: '.oe_snippet_thumbnail',
            distance: 30,
            cursorAt: {
                left: left,
                top: top,
            },
            start: function () {
                dropped = false;
                $snippet = $(this);
                var $base_body = $snippet.find('.oe_snippet_body');
                var $selectorSiblings = $();
                var $selectorChildren = $();
                var temp = self.templateOptions;
                for (var k in temp) {
                    if ($base_body.is(temp[k].base_selector) && !$base_body.is(temp[k].base_exclude)) {
                        if (temp[k]['drop-near']) {
                            if (!$selectorSiblings) $selectorSiblings = temp[k]['drop-near'].all();
                            else $selectorSiblings = $selectorSiblings.add(temp[k]['drop-near'].all());
                        }
                        if (temp[k]['drop-in']) {
                            if (!$selectorChildren) $selectorChildren = temp[k]['drop-in'].all();
                            else $selectorChildren = $selectorChildren.add(temp[k]['drop-in'].all());
                        }
                    }
                }

                $toInsert = $base_body.clone().data('name', $base_body.data('name'));

                if (!$selectorSiblings.length && !$selectorChildren.length) {
                    console.warn($snippet.find('.oe_snippet_thumbnail_title').text() + " have not insert action: data-drop-near or data-drop-in");
                    return;
                }

                self._activateSnippet(false);
                self._activateInsertionZones($selectorSiblings, $selectorChildren);

                $('.oe_drop_zone').droppable({
                    over: function () {
                        dropped = true;
                        $(this).first().after($toInsert).addClass('hidden');
                    },
                    out: function () {
                        var prev = $toInsert.prev();
                        if (this === prev[0]) {
                            dropped = false;
                            $toInsert.detach();
                            $(this).removeClass('hidden');
                        }
                    },
                });
            },
            stop: function (ev, ui) {
                $toInsert.removeClass('oe_snippet_body');

                if (! dropped && self.$editable.find('.oe_drop_zone') && ui.position.top > 3 && ui.position.left + 50 > self.$el.outerWidth()) {
                    var el = self.$editable.find('.oe_drop_zone').nearest({x: ui.position.left, y: ui.position.top}).first();
                    if (el.length) {
                        el.after($toInsert);
                        dropped = true;
                    }
                }

                self.$editable.find('.oe_drop_zone').droppable('destroy').remove();

                if (dropped) {
                    var prev = $toInsert.first()[0].previousSibling;
                    var next = $toInsert.last()[0].nextSibling;

                    if (prev) {
                        $toInsert.detach();
                        self.trigger_up('request_history_undo_record', {$target: $(prev)});
                        $toInsert.insertAfter(prev);
                    } else if (next) {
                        $toInsert.detach();
                        self.trigger_up('request_history_undo_record', {$target: $(next)});
                        $toInsert.insertBefore(next);
                    } else {
                        var $parent = $toInsert.parent();
                        $toInsert.detach();
                        self.trigger_up('request_history_undo_record', {$target: $parent});
                        $parent.prepend($toInsert);
                    }

                    $toInsert.closest('.o_editable').trigger('content_changed');

                    var $target = $toInsert;

                    _.defer(function () {
                        self.trigger_up('snippet_dropped', {$target: $target});
                        self._disableUndroppableSnippets();

                        self._callForEachChildSnippet($target, function (editor, $snippet) {
                            _.defer(function () {
                                editor.buildSnippet();
                            });
                        }).then(function () {
                            $target.closest('.o_editable').trigger('content_changed');
                            self._activateSnippet($target);
                        });
                    });
                } else {
                    $toInsert.remove();
                }
            },
        });
    },
    /**
     * Adds the 'o_default_snippet_text' class on nodes which contain only
     * non-empty text nodes. Those nodes are then auto-selected by the editor
     * when they are clicked.
     *
     * @private
     * @param {jQuery} [$in] - the element in which to search, default to the
     *                       snippet bodies in the menu
     */
    _registerDefaultTexts: function ($in) {
        if ($in === undefined) {
            $in = this.$snippets.find('.oe_snippet_body');
        }

        $in.find('*').addBack()
            .contents()
            .filter(function () {
                return this.nodeType === 3 && this.textContent.match(/\S/);
            }).parent().addClass('o_default_snippet_text');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a child editor asks for insertion zones to be enabled.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onActivateInsertionZones: function (ev) {
        this._activateInsertionZones(ev.data.$selectorSiblings, ev.data.$selectorChildren);
    },
    /**
     * Called when a child editor asks to operate some operation on all child
     * snippet of a DOM element.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCallForEachChildSnippet: function (ev) {
        this._callForEachChildSnippet(ev.data.$snippet, ev.data.callback);
    },
    /**
     * Called when asked to clean the DOM for save. Should technically not be
     * used but used by tests.
     *
     * @private
     */
    _onCleanForSaveDemand: function (ev) {
        this.cleanForSave();
    },
    /**
     * Called when a child editor asks to deactivate the current snippet
     * overlay.
     *
     * @private
     */
    _onDeactivateSnippet: function () {
        this._activateSnippet(false);
    },
    /**
     * Called when a snippet has moved in the page.
     *
     * @todo technically, as a snippet has been moved, all editors should be
     * destroyed as their snippet options may not correspond to their
     * selector anymore. However this should rarely (maybe never ?) be the case,
     * so we might not want to do this as it would slow the editor.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onDragAndDropStop: function (ev) {
        this._activateSnippet(ev.data.$snippet);
    },
    /**
     * Called when a snippet editor asked to disable itself and to enable its
     * parent instead.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onGoToParent: function (ev) {
        ev.stopPropagation();
        this._activateSnippet(ev.data.$snippet.parent());
    },
    /**
     * Called when a snippet is removed -> checks if there is draggable snippets
     * to enable/disable as the DOM changed.
     *
     * @private
     */
    _onSnippetRemoved: function () {
        this._disableUndroppableSnippets();
    },
});

return {
    Class: SnippetsMenu,
    Editor: SnippetEditor,
    globalSelector: globalSelector,
};
});
