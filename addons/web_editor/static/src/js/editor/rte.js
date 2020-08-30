odoo.define('web_editor.rte', function (require) {
'use strict';

var fonts = require('wysiwyg.fonts');
var concurrency = require('web.concurrency');
var core = require('web.core');
var Widget = require('web.Widget');
var weContext = require('web_editor.context');
var summernote = require('web_editor.summernote');
var summernoteCustomColors = require('web_editor.rte.summernote_custom_colors');

var _t = core._t;

// Summernote Lib (neek change to make accessible: method and object)
var dom = summernote.core.dom;
var range = summernote.core.range;

// Change History to have a global History for all summernote instances
var History = function History($editable) {
    var aUndo = [];
    var pos = 0;
    var toSnap;

    this.makeSnap = function (event, rng) {
        rng = rng || range.create();
        var elEditable = $(rng && rng.sc).closest('.o_editable')[0];
        if (!elEditable) {
            return false;
        }
        return {
            event: event,
            editable: elEditable,
            contents: elEditable.innerHTML,
            bookmark: rng && rng.bookmark(elEditable),
            scrollTop: $(elEditable).scrollTop()
        };
    };

    this.applySnap = function (oSnap) {
        var $editable = $(oSnap.editable);

        if (document.documentMode) {
            $editable.removeAttr('contentEditable').removeProp('contentEditable');
        }

        $editable.trigger('content_will_be_destroyed');
        var $tempDiv = $('<div/>', {html: oSnap.contents});
        _.each($tempDiv.find('.o_temp_auto_element'), function (el) {
            var $el = $(el);
            var originalContent = $el.attr('data-temp-auto-element-original-content');
            if (originalContent) {
                $el.after(originalContent);
            }
            $el.remove();
        });
        $editable.html($tempDiv.html()).scrollTop(oSnap.scrollTop);
        $editable.trigger('content_was_recreated');

        $('.oe_overlay').remove();
        $('.note-control-selection').hide();

        $editable.trigger('content_changed');

        try {
            var r = oSnap.editable.innerHTML === '' ? range.create(oSnap.editable, 0) : range.createFromBookmark(oSnap.editable, oSnap.bookmark);
            r.select();
        } catch (e) {
            console.error(e);
            return;
        }

        $(document).trigger('click');
        $('.o_editable *').filter(function () {
            var $el = $(this);
            if ($el.data('snippet-editor')) {
                $el.removeData();
            }
        });


        _.defer(function () {
            var target = dom.isBR(r.sc) ? r.sc.parentNode : dom.node(r.sc);
            if (!target) {
                return;
            }

            $editable.trigger('applySnap');

            var evt = document.createEvent('MouseEvents');
            evt.initMouseEvent('click', true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, target);
            target.dispatchEvent(evt);

            $editable.trigger('keyup');
        });
    };

    this.undo = function () {
        if (!pos) { return; }
        var _toSnap = toSnap;
        if (_toSnap) {
            this.saveSnap();
        }
        if (!aUndo[pos] && (!aUndo[pos] || aUndo[pos].event !== 'undo')) {
            var temp = this.makeSnap('undo');
            if (temp && (!pos || temp.contents !== aUndo[pos-1].contents)) {
                aUndo[pos] = temp;
            } else {
               pos--;
            }
        } else if (_toSnap) {
            pos--;
        }
        this.applySnap(aUndo[Math.max(--pos,0)]);
        while (pos && (aUndo[pos].event === 'blur' || (aUndo[pos+1].editable ===  aUndo[pos].editable && aUndo[pos+1].contents ===  aUndo[pos].contents))) {
            this.applySnap(aUndo[--pos]);
        }
    };

    this.hasUndo = function () {
        return (toSnap && (toSnap.event !== 'blur' && toSnap.event !== 'activate' && toSnap.event !== 'undo')) ||
            !!_.find(aUndo.slice(0, pos+1), function (undo) {
                return undo.event !== 'blur' && undo.event !== 'activate' && undo.event !== 'undo';
            });
    };

    this.getEditableHasUndo = function () {
        var editable = [];
        if ((toSnap && (toSnap.event !== 'blur' && toSnap.event !== 'activate' && toSnap.event !== 'undo'))) {
            editable.push(toSnap.editable);
        }
        _.each(aUndo.slice(0, pos+1), function (undo) {
            if (undo.event !== 'blur' && undo.event !== 'activate' && undo.event !== 'undo') {
                editable.push(undo.editable);
            }
        });
        return _.uniq(editable);
    };

    this.redo = function () {
        if (!aUndo[pos+1]) { return; }
        this.applySnap(aUndo[++pos]);
        while (aUndo[pos+1] && aUndo[pos].event === 'active') {
            this.applySnap(aUndo[pos++]);
        }
    };

    this.hasRedo = function () {
        return aUndo.length > pos+1;
    };

    this.recordUndo = function ($editable, event, internal_history) {
        var self = this;
        if (!$editable) {
            var rng = range.create();
            if (!rng) return;
            $editable = $(rng.sc).closest('.o_editable');
        }

        if (aUndo[pos] && (event === 'applySnap' || event === 'activate')) {
            return;
        }

        if (!internal_history) {
            if (!event || !toSnap || !aUndo[pos-1] || toSnap.event === 'activate') { // don't trigger change for all keypress
                setTimeout(function () {
                    $editable.trigger('content_changed');
                },0);
            }
        }

        if (aUndo[pos]) {
            pos = Math.min(pos, aUndo.length);
            aUndo.splice(pos, aUndo.length);
        }

        // => make a snap when the user change editable zone (because: don't make snap for each keydown)
        if (toSnap && (toSnap.split || !event || toSnap.event !== event || toSnap.editable !== $editable[0])) {
            this.saveSnap();
        }

        if (pos && aUndo[pos-1].editable !== $editable[0]) {
            var snap = this.makeSnap('blur', range.create(aUndo[pos-1].editable, 0));
            pos++;
            aUndo.push(snap);
        }

        if (range.create()) {
            toSnap = self.makeSnap(event);
        } else {
            toSnap = false;
        }
    };

    this.splitNext = function () {
        if (toSnap) {
            toSnap.split = true;
        }
    };

    this.saveSnap = function () {
        if (toSnap) {
            if (!aUndo[pos]) {
                pos++;
            }
            aUndo.push(toSnap);
            delete toSnap.split;
            toSnap = null;
        }
    };
};
var history = new History();

// jQuery extensions
$.extend($.expr[':'], {
    o_editable: function (node, i, m) {
        while (node) {
            if (node.className && _.isString(node.className)) {
                if (node.className.indexOf('o_not_editable')!==-1 ) {
                    return false;
                }
                if (node.className.indexOf('o_editable')!==-1 ) {
                    return true;
                }
            }
            node = node.parentNode;
        }
        return false;
    },
});
$.fn.extend({
    focusIn: function () {
        if (this.length) {
            range.create(dom.firstChild(this[0]), 0).select();
        }
        return this;
    },
    focusInEnd: function () {
        if (this.length) {
            var last = dom.lastChild(this[0]);
            range.create(last, dom.nodeLength(last)).select();
        }
        return this;
    },
    selectContent: function () {
        if (this.length) {
            var next = dom.lastChild(this[0]);
            range.create(dom.firstChild(this[0]), 0, next, next.textContent.length).select();
        }
        return this;
    },
});

// RTE
var RTEWidget = Widget.extend({
    /**
     * @constructor
     */
    init: function (parent, params) {
        var self = this;
        this._super.apply(this, arguments);

        this.init_bootstrap_carousel = $.fn.carousel;
        this.edit_bootstrap_carousel = function () {
            var res = self.init_bootstrap_carousel.apply(this, arguments);
            // off bootstrap keydown event to remove event.preventDefault()
            // and allow to change cursor position
            $(this).off('keydown.bs.carousel');
            return res;
        };

        this._getConfig = params && params.getConfig || this._getDefaultConfig;
        this._saveElement = params && params.saveElement || this._saveElement;

        fonts.computeFonts();
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        this.saving_mutex = new concurrency.Mutex();

        $.fn.carousel = this.edit_bootstrap_carousel;

        $(document).on('click.rte keyup.rte', function () {
            var current_range = {};
            try {
                current_range = range.create() || {};
            } catch (e) {
                // if range is on Restricted element ignore error
            }
            var $popover = $(current_range.sc).closest('[contenteditable]');
            var popover_history = ($popover.data()||{}).NoteHistory;
            if (!popover_history || popover_history === history) return;
            var editor = $popover.parent('.note-editor');
            $('button[data-event="undo"]', editor).attr('disabled', !popover_history.hasUndo());
            $('button[data-event="redo"]', editor).attr('disabled', !popover_history.hasRedo());
        });
        $(document).on('mousedown.rte activate.rte', this, this._onMousedown.bind(this));
        $(document).on('mouseup.rte', this, this._onMouseup.bind(this));

        $('.o_not_editable').attr('contentEditable', false);

        var $editable = this.editable();

        // When a undo/redo is performed, the whole DOM is changed so we have
        // to prepare for it (website will restart animations for example)
        // TODO should be better handled
        $editable.on('content_will_be_destroyed', function (ev) {
            self.trigger_up('content_will_be_destroyed', {
                $target: $(ev.currentTarget),
            });
        });
        $editable.on('content_was_recreated', function (ev) {
            self.trigger_up('content_was_recreated', {
                $target: $(ev.currentTarget),
            });
        });

        $editable.addClass('o_editable')
        .data('rte', this)
        .each(function () {
            var $node = $(this);

            // fallback for firefox iframe display:none see https://github.com/odoo/odoo/pull/22610
            var computedStyles = window.getComputedStyle(this) || window.parent.getComputedStyle(this);
            // add class to display inline-block for empty t-field
            if (computedStyles.display === 'inline' && $node.data('oe-type') !== 'image') {
                $node.addClass('o_is_inline_editable');
            }
        });

        // start element observation
        $(document).on('content_changed', function (ev) {
            self.trigger_up('rte_change', {target: ev.target});

            // Add the dirty flag to the element that changed by either adding
            // it on the highest editable ancestor or, if there is no editable
            // ancestor, on the element itself (that element may not be editable
            // but if it received a content_changed event, it should be marked
            // as dirty to allow for custom savings).
            if (!ev.__isDirtyHandled) {
                ev.__isDirtyHandled = true;

                var el = ev.target;
                var dirty = el.closest('.o_editable') || el;
                dirty.classList.add('o_dirty');
            }
        });

        $('#wrapwrap, .o_editable').on('click.rte', '*', this, this._onClick.bind(this));

        $('body').addClass('editor_enable');

        $(document.body)
            .tooltip({
                selector: '[data-oe-readonly]',
                container: 'body',
                trigger: 'hover',
                delay: { 'show': 1000, 'hide': 100 },
                placement: 'bottom',
                title: _t("Readonly field")
            })
            .on('click', function () {
                $(this).tooltip('hide');
            });

        $(document).trigger('mousedown');
        this.trigger('rte:start');

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this.cancel();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Stops the RTE.
     */
    cancel: function () {
        if (this.$last) {
            this.$last.destroy();
            this.$last = null;
        }

        $.fn.carousel = this.init_bootstrap_carousel;

        $(document).off('.rte');
        $('#wrapwrap, .o_editable').off('.rte');

        $('.o_not_editable').removeAttr('contentEditable');

        $(document).off('click.rte keyup.rte mousedown.rte activate.rte mouseup.rte');
        $(document).off('content_changed').removeClass('o_is_inline_editable').removeData('rte');
        $(document).tooltip('dispose');
        $('body').removeClass('editor_enable');
        this.trigger('rte:stop');
    },
    /**
     * Returns the editable areas on the page.
     *
     * @returns {jQuery}
     */
    editable: function () {
        return $('#wrapwrap [data-oe-model]')
            .not('.o_not_editable')
            .filter(function () {
                return !$(this).closest('.o_not_editable').length;
            })
            .not('link, script')
            .not('[data-oe-readonly]')
            .not('img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]')
            .not('.oe_snippet_editor')
            .add('.o_editable');
    },
    /**
     * Records the current state of the given $target to be able to undo future
     * changes.
     *
     * @see History.recordUndo
     * @param {jQuery} $target
     * @param {string} event
     * @param {boolean} internal_history
     */
    historyRecordUndo: function ($target, event, internal_history) {
        const initialActiveElement = document.activeElement;
        const initialSelectionStart = initialActiveElement && initialActiveElement.selectionStart;
        const initialSelectionEnd = initialActiveElement && initialActiveElement.selectionEnd;

        $target = $($target);
        var rng = range.create();
        var $editable = $(rng && rng.sc).closest('.o_editable');
        if (!rng || !$editable.length) {
            $editable = $target.closest('.o_editable');
            rng = range.create($target.closest('*')[0],0);
        } else {
            rng = $editable.data('range') || rng;
        }
        try {
            // TODO this line might break for unknown reasons. I suppose that
            // the created range is an invalid one. As it might be tricky to
            // adapt that line and that it is not a critical one, temporary fix
            // is to ignore the errors that this generates.
            rng.select();
        } catch (e) {
            console.log('error', e);
        }
        history.recordUndo($editable, event, internal_history);

        if (initialActiveElement && initialActiveElement !== document.activeElement) {
            initialActiveElement.focus();
            // Range inputs don't support selection
            if (initialActiveElement.matches('input[type=range]')) {
                return;
            }
            try {
                initialActiveElement.selectionStart = initialSelectionStart;
                initialActiveElement.selectionEnd = initialSelectionEnd;
            } catch (e) {
                // The active element might be of a type that
                // does not support selection.
                console.log('error', e);
            }
        }
    },
    /**
     * Searches all the dirty element on the page and saves them one by one. If
     * one cannot be saved, this notifies it to the user and restarts rte
     * edition.
     *
     * @param {Object} [context] - the context to use for saving rpc, default to
     *                           the editor context found on the page
     * @return {Promise} rejected if the save cannot be done
     */
    save: function (context) {
        var self = this;

        $('.o_editable')
            .destroy()
            .removeClass('o_editable o_is_inline_editable o_editable_date_field_linked o_editable_date_field_format_changed');

        var $dirty = $('.o_dirty');
        $dirty
            .removeAttr('contentEditable')
            .removeClass('o_dirty oe_carlos_danger o_is_inline_editable');
        var defs = _.map($dirty, function (el) {
            var $el = $(el);

            $el.find('[class]').filter(function () {
                if (!this.getAttribute('class').match(/\S/)) {
                    this.removeAttribute('class');
                }
            });

            // TODO: Add a queue with concurrency limit in webclient
            // https://github.com/medikoo/deferred/blob/master/lib/ext/function/gate.js
            return self.saving_mutex.exec(function () {
                return self._saveElement($el, context || weContext.get())
                .then(function () {
                    $el.removeClass('o_dirty');
                }).guardedCatch(function (response) {
                    // because ckeditor regenerates all the dom, we can't just
                    // setup the popover here as everything will be destroyed by
                    // the DOM regeneration. Add markings instead, and returns a
                    // new rejection with all relevant info
                    var id = _.uniqueId('carlos_danger_');
                    $el.addClass('o_dirty oe_carlos_danger ' + id);
                    $('.o_editable.' + id)
                        .removeClass(id)
                        .popover({
                            trigger: 'hover',
                            content: response.message.data.message || '',
                            placement: 'auto top',
                        })
                        .popover('show');
                });
            });
        });

        return Promise.all(defs).then(function () {
            window.onbeforeunload = null;
        }).guardedCatch(function (failed) {
            // If there were errors, re-enable edition
            self.cancel();
            self.start();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * When the users clicks on an editable element, this function allows to add
     * external behaviors.
     *
     * @private
     * @param {jQuery} $editable
     */
    _enableEditableArea: function ($editable) {
        if ($editable.data('oe-type') === "datetime" || $editable.data('oe-type') === "date") {
            var selector = '[data-oe-id="' + $editable.data('oe-id') + '"]';
            selector += '[data-oe-field="' + $editable.data('oe-field') + '"]';
            selector += '[data-oe-model="' + $editable.data('oe-model') + '"]';
            var $linkedFieldNodes = this.editable().find(selector).addBack(selector);
            $linkedFieldNodes.not($editable).addClass('o_editable_date_field_linked');
            if (!$editable.hasClass('o_editable_date_field_format_changed')) {
                $linkedFieldNodes.html($editable.data('oe-original-with-format'));
                $linkedFieldNodes.addClass('o_editable_date_field_format_changed');
            }
        }
        if ($editable.data('oe-type') === "monetary") {
            $editable.attr('contenteditable', false);
            $editable.find('.oe_currency_value').attr('contenteditable', true);
        }
        if ($editable.is('[data-oe-model]') && !$editable.is('[data-oe-model="ir.ui.view"]') && !$editable.is('[data-oe-type="html"]')) {
            $editable.data('layoutInfo').popover().find('.btn-group:not(.note-history)').remove();
        }
    },
    /**
     * When an element enters edition, summernote is initialized on it. This
     * function returns the default configuration for the summernote instance.
     *
     * @see _getConfig
     * @private
     * @param {jQuery} $editable
     * @returns {Object}
     */
    _getDefaultConfig: function ($editable) {
        return {
            'airMode' : true,
            'focus': false,
            'airPopover': [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['insert', ['link', 'picture']],
                ['history', ['undo', 'redo']],
            ],
            'styleWithSpan': false,
            'inlinemedia' : ['p'],
            'lang': 'odoo',
            'onChange': function (html, $editable) {
                $editable.trigger('content_changed');
            },
            'colors': summernoteCustomColors,
        };
    },
    /**
     * Gets jQuery cloned element with internal text nodes escaped for XML
     * storage.
     *
     * @private
     * @param {jQuery} $el
     * @return {jQuery}
     */
    _getEscapedElement: function ($el) {
        var escaped_el = $el.clone();
        var to_escape = escaped_el.find('*').addBack();
        to_escape = to_escape.not(to_escape.filter('object,iframe,script,style,[data-oe-model][data-oe-model!="ir.ui.view"]').find('*').addBack());
        to_escape.contents().each(function () {
            if (this.nodeType === 3) {
                this.nodeValue = $('<div />').text(this.nodeValue).html();
            }
        });
        return escaped_el;
    },
    /**
     * Saves one (dirty) element of the page.
     *
     * @private
     * @param {jQuery} $el - the element to save
     * @param {Object} context - the context to use for the saving rpc
     * @param {boolean} [withLang=false]
     *        false if the lang must be omitted in the context (saving "master"
     *        page element)
     */
    _saveElement: function ($el, context, withLang) {
        var viewID = $el.data('oe-id');
        if (!viewID) {
            return Promise.resolve();
        }

        return this._rpc({
            model: 'ir.ui.view',
            method: 'save',
            args: [
                viewID,
                this._getEscapedElement($el).prop('outerHTML'),
                $el.data('oe-xpath') || null,
            ],
            context: context,
        }, withLang ? undefined : {
            noContextKeys: 'lang',
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when any editable element is clicked -> Prevents default browser
     * action for the element.
     *
     * @private
     * @param {Event} e
     */
    _onClick: function (e) {
        e.preventDefault();
    },
    /**
     * Called when the mouse is pressed on the document -> activate element
     * edition.
     *
     * @private
     * @param {Event} ev
     */
    _onMousedown: function (ev) {
        var $target = $(ev.target);
        var $editable = $target.closest('.o_editable');
        var isLink = $target.is('a');

        if (this && this.$last && this.$last.length && this.$last[0] !== $target[0]) {
            $('.o_editable_date_field_linked').removeClass('o_editable_date_field_linked');
        }
        if (!$editable.length || (!isLink && $.summernote.core.dom.isContentEditableFalse($target))) {
            return;
        }

        // Removes strange _moz_abspos attribute when it appears. Cannot
        // find another solution which works in all cases. A grabber still
        // appears at the same time which I did not manage to remove.
        // TODO find a complete and better solution
        _.defer(function () {
            $editable.find('[_moz_abspos]').removeAttr('_moz_abspos');
        });

        if (isLink) {
            /**
             * Remove content editable everywhere and add it on the link only so that characters can be added
             * and removed at the start and at the end of it.
             */
            let hasContentEditable = $target.attr('contenteditable');
            $target.attr('contenteditable', true);
            _.defer(function () {
                $editable.not($target).attr('contenteditable', false);
                $target.focus();
            });

            // Once clicked outside, remove contenteditable on link and reactive all
            $(document).on('mousedown.reactivate_contenteditable', function (e) {
                if ($target.is(e.target)) return;
                if (!hasContentEditable) {
                    $target.removeAttr('contenteditable');
                }
                $editable.attr('contenteditable', true);
                $(document).off('mousedown.reactivate_contenteditable');
            });
        }

        if (this && this.$last && (!$editable.length || this.$last[0] !== $editable[0])) {
            var $destroy = this.$last;
            history.splitNext();
            // In some special cases, we need to clear the timeout.
            var lastTimerId = _.delay(function () {
                var id = $destroy.data('note-id');
                $destroy.destroy().removeData('note-id').removeAttr('data-note-id');
                $('#note-popover-'+id+', #note-handle-'+id+', #note-dialog-'+id+'').remove();
            }, 150); // setTimeout to remove flickering when change to editable zone (re-create an editor)
            this.$last = null;
            // for modal dialogs (eg newsletter popup), when we close the dialog, the modal is
            // destroyed immediately and so after the delayed execution due to timeout, dialog will
            // not be available, leading to trace-back, so we need to clearTimeout for the dialogs.
            if ($destroy.hasClass('modal-body')) {
                clearTimeout(lastTimerId);
            }
        }

        if ($editable.length && (!this.$last || this.$last[0] !== $editable[0])) {
            $editable.summernote(this._getConfig($editable));

            $editable.data('NoteHistory', history);
            this.$last = $editable;

            // firefox & IE fix
            try {
                document.execCommand('enableObjectResizing', false, false);
                document.execCommand('enableInlineTableEditing', false, false);
                document.execCommand('2D-position', false, false);
            } catch (e) { /* */ }
            document.body.addEventListener('resizestart', function (evt) {evt.preventDefault(); return false;});
            document.body.addEventListener('movestart', function (evt) {evt.preventDefault(); return false;});
            document.body.addEventListener('dragstart', function (evt) {evt.preventDefault(); return false;});

            if (!range.create()) {
                $editable.focusIn();
            }

            if (dom.isImg($target[0])) {
                $target.trigger('mousedown'); // for activate selection on picture
            }

            this._enableEditableArea($editable);
        }
    },
    /**
     * Called when the mouse is unpressed on the document.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseup: function (ev) {
        var $target = $(ev.target);
        var $editable = $target.closest('.o_editable');

        if (!$editable.length) {
            return;
        }

        var self = this;
        _.defer(function () {
            self.historyRecordUndo($target, 'activate',  true);
        });

        // Browsers select different content from one to another after a
        // triple click (especially: if triple-clicking on a paragraph on
        // Chrome, blank characters of the element following the paragraph are
        // selected too)
        //
        // The triple click behavior is reimplemented for all browsers here
        if (ev.originalEvent && ev.originalEvent.detail === 3) {
            // Select the whole content inside the deepest DOM element that was
            // triple-clicked
            range.create(ev.target, 0, ev.target, ev.target.childNodes.length).select();
        }
    },
});

return {
    Class: RTEWidget,
    history: history,
};
});

odoo.define('web_editor.rte.summernote_custom_colors', function (require) {
'use strict';

// These colors are already normalized as per normalizeCSSColor in web.Colorpicker
return [
    ['#000000', '#424242', '#636363', '#9C9C94', '#CEC6CE', '#EFEFEF', '#F7F7F7', '#FFFFFF'],
    ['#FF0000', '#FF9C00', '#FFFF00', '#00FF00', '#00FFFF', '#0000FF', '#9C00FF', '#FF00FF'],
    ['#F7C6CE', '#FFE7CE', '#FFEFC6', '#D6EFD6', '#CEDEE7', '#CEE7F7', '#D6D6E7', '#E7D6DE'],
    ['#E79C9C', '#FFC69C', '#FFE79C', '#B5D6A5', '#A5C6CE', '#9CC6EF', '#B5A5D6', '#D6A5BD'],
    ['#E76363', '#F7AD6B', '#FFD663', '#94BD7B', '#73A5AD', '#6BADDE', '#8C7BC6', '#C67BA5'],
    ['#CE0000', '#E79439', '#EFC631', '#6BA54A', '#4A7B8C', '#3984C6', '#634AA5', '#A54A7B'],
    ['#9C0000', '#B56308', '#BD9400', '#397B21', '#104A5A', '#085294', '#311873', '#731842'],
    ['#630000', '#7B3900', '#846300', '#295218', '#083139', '#003163', '#21104A', '#4A1031']
];
});
