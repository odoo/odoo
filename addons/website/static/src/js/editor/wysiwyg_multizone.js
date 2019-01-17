odoo.define('web_editor.wysiwyg.multizone', function (require) {
'use strict';
var concurrency = require('web.concurrency');
var core = require('web.core');
var DropzonePlugin = require('web_editor.wysiwyg.plugin.dropzone');
var HelperPlugin = require('web_editor.wysiwyg.plugin.helper');
var TextPlugin = require('web_editor.wysiwyg.plugin.text');
var HistoryPlugin = require('web_editor.wysiwyg.plugin.history');
var Wysiwyg = require('web_editor.wysiwyg');

var _t = core._t;

HistoryPlugin.include({
    /**
     * @override
     */
    applySnapshot: function () {
        this.trigger_up('content_will_be_destroyed', {
            $target: this.$editable,
        });
        this._super.apply(this, arguments);
        this.trigger_up('content_was_recreated', {
            $target: this.$editable,
        });
        $('.oe_overlay').remove();
        $('.note-control-selection').hide();
        this.$editable.trigger('content_changed');
    },
});

HelperPlugin.include({
    /**
     * Returns true if range is on or within a field that is not of type 'html'.
     *
     * @returns {Boolean}
     */
    isOnNonHTMLField: function () {
        var range = this.context.invoke('editor.createRange');
        return !!$.summernote.dom.ancestor(range.sc, function (node) {
            return $(node).data('oe-type') && $(node).data('oe-type') !== 'html';
        });
    },
});

TextPlugin.include({
    /**
     * Paste text only if on non-HTML field.
     *
     * @override
     */
    pasteNodes: function (nodes, textOnly) {
        textOnly = textOnly || this.context.invoke('HelperPlugin.isOnNonHTMLField');
        this._super.apply(this, [nodes, textOnly]);
    },
});

DropzonePlugin.include({
    /**
     * Prevent dropping images in non-HTML fields.
     *
     * @override
     */
    _canDropHere: function (dataTransfer) {
        if (this.context.invoke('HelperPlugin.isOnNonHTMLField') && dataTransfer.files.length) {
            return false;
        }
        return this._super();
    },
});





/**
 * HtmlEditor
 * Intended to edit HTML content. This widget uses the Wysiwyg editor
 * improved by odoo.
 *
 * class editable: o_editable
 * class non editable: o_not_editable
 *
 */
var WysiwygMultizone = Wysiwyg.extend({
    events: _.extend({}, Wysiwyg.prototype.events, {
        'keyup *': function (ev) {
            if ((ev.keyCode === 8 || ev.keyCode === 46)) {
                var $target = $(ev.target).closest('.o_editable');
                if (!$target.is(':has(*:not(p):not(br))') && !$target.text().match(/\S/)) {
                    $target.empty();
                }
            }
            if (ev.key.length === 1) {
                this._onChange();
            }
        },
        'click .note-editable': function (ev) {
            ev.preventDefault();
        },
        'submit .note-editable form .btn': function (ev) {
            ev.preventDefault(); // Disable form submition in editable mode
        },
        'hide.bs.dropdown .dropdown': function (ev) {
            // Prevent dropdown closing when a contenteditable children is focused
            if (ev.originalEvent &&
                    $(ev.target).has(ev.originalEvent.target).length &&
                    $(ev.originalEvent.target).is('[contenteditable]')) {
                ev.preventDefault();
            }
        },
    }),
    custom_events: _.extend({}, Wysiwyg.prototype.custom_events, {
        activate_snippet:  '_onActivateSnippet',
        drop_images: '_onDropImages',
    }),
    /**
     * @override
     * @param {Object} options.context - the context to use for the saving rpc
     * @param {boolean} [options.withLang=false]
     *        false if the lang must be omitted in the context (saving "master"
     *        page element)
     */
    init: function (parent, options) {
        options = options || {};
        options.addDropSelector = ':o_editable';
        this.savingMutex = new concurrency.Mutex();
        this._super(parent, options);
    },
    /**
     * Prevent some default features for the editable area.
     *
     * @override
     */
    start: function () {
        var self = this;
        return this._super().then(function () {
            // Unload preserve
            var flag = false;
            window.onbeforeunload = function (event) {
                if (self.isDirty() && !flag) {
                    flag = true;
                    _.defer(function () {
                        flag = false;
                    });
                    return _t('Changes you made may not be saved.');
                }
            };
            // firefox & IE fix
            try {
                document.execCommand('enableObjectResizing', false, false);
                document.execCommand('enableInlineTableEditing', false, false);
                document.execCommand('2D-position', false, false);
            } catch (e) { /* */ }
            document.body.addEventListener('resizestart', function (evt) {
                evt.preventDefault();
                return false;
            });
            document.body.addEventListener('movestart', function (evt) {
                evt.preventDefault();
                return false;
            });
            document.body.addEventListener('dragstart', function (evt) {
                evt.preventDefault();
                return false;
            });
            // BOOTSTRAP preserve
            self.init_bootstrap_carousel = $.fn.carousel;
            $.fn.carousel = function () {
                var res = self.init_bootstrap_carousel.apply(this, arguments);
                // off bootstrap keydown event to remove event.preventDefault()
                // and allow to change cursor position
                $(this).off('keydown.bs.carousel');
                return res;
            };
            self.$('.dropdown-toggle').dropdown();
            self.$el
                .tooltip({
                    selector: '[data-oe-readonly]',
                    container: 'body',
                    trigger: 'hover',
                    delay: {
                        'show': 1000,
                        'hide': 100,
                    },
                    placement: 'bottom',
                    title: _t("Readonly field")
                })
                .on('click', function () {
                    $(this).tooltip('hide');
                });
            $('body').addClass('editor_enable');
            $('.note-editor, .note-popover').filter('[data-wysiwyg-id="' + self.id + '"]').addClass('wysiwyg_multizone');
            $('.note-editable .note-editor, .note-editable .note-editable').attr('contenteditable', false);

            self._summernote.isDisabled = function () {
                return false;
            };

            self.$('.note-editable').addClass('o_not_editable').attr('contenteditable', false);
            self._getEditableArea().attr('contenteditable', true);
            self.$('[data-oe-readonly]').addClass('o_not_editable').attr('contenteditable', false);
            self.$('.oe_structure').attr('contenteditable', false).addClass('o_fake_not_editable');
            self.$('[data-oe-field][data-oe-type="image"]').attr('contenteditable', false).addClass('o_fake_not_editable');
            self.$('[data-oe-field]:not([contenteditable])').attr('contenteditable', true).addClass('o_fake_editable');
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super();
        this.$target.css('display', '');
        this.$target.find('[data-old-id]').add(this.$target).each(function () {
            var $node = $(this);
            $node.attr('id', $node.attr('data-old-id')).removeAttr('data-old-id');
        });
        $('body').removeClass('editor_enable');
        window.onbeforeunload = null;
        $.fn.carousel = this.init_bootstrap_carousel;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Boolean}
     */
    isDirty: function () {
        return !!this._getEditableArea().filter('.o_dirty').length;
    },
    /**
     * @override
     * @returns {$.Promise} resolve with true if the content was dirty
     */
    save: function () {
        var isDirty = this.isDirty();
        if (isDirty) {
            this.savingMutex.exec(this._saveCroppedImages.bind(this));
        }
        var _super = this._super.bind(this);
        return this.savingMutex.def.then(function () {
            return _super().then(function (_isDirty, html) {
                this._summernote.layoutInfo.editable.html(html);

                var $editable = this._getEditableArea();
                var $areaDirty = $editable.filter('.o_dirty');
                if (!$areaDirty.length) {
                    return false;
                }
                $areaDirty.each(function (index, editable) {
                    this.savingMutex.exec(this._saveEditable.bind(this, editable));
                }.bind(this));
                return this.savingMutex.def.then(function () {
                    return true;
                });
            }.bind(this));
        }.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return true if the editor is displaying the popover.
     *
     * @override
     * @returns {Boolean}
     */
    _isDisplayingPopover: function (node) {
        return this._super(node) && $(node).parent().closest('[data-oe-model="ir.ui.view"], [data-oe-type="html"]').length;
    },
    /**
     * @override
     * @returns {Object} the summernote configuration
     */
    _editorOptions: function () {
        var options = this._super();
        options.toolbar[8] = ['view', ['help']];

        // remove blockquote (it's a snippet)
        var blockquote = options.styleTags.indexOf('blockquote');
        if (blockquote !== -1) options.styleTags.splice(blockquote, 1);

        options.popover.image[4] = ['editImage', ['cropImage', 'transform']];
        return _.extend(options, {
            styleWithSpan: false,
            followingToolbar: false,
        });
    },
    /**
     * Escape internal text nodes for XML storage.
     *
     * @private
     * @param {jQuery} $el
     */
    _escapeElements: function ($el) {
        var toEscape = $el.find('*').addBack();
        toEscape = toEscape.not(toEscape.filter('object,iframe,script,style,[data-oe-model][data-oe-model!="ir.ui.view"]').find('*').addBack());
        toEscape.contents().each(function () {
            if (this.nodeType === 3) {
                this.nodeValue = $('<div />').text(this.nodeValue).html();
            }
        });
    },
    /**
     * Gets jQuery cloned element with clean for XML storage.
     *
     * @private
     * @param {jQuery} $el
     * @returns {jQuery}
     */
    _getCleanedHtml: function (editable) {
        var $el = $(editable).clone().removeClass('o_editable o_dirty');
        this._escapeElements($el);
        return $el;
    },
    /**
     * Return an object describing the linked record.
     *
     * @override
     * @param {Object} options
     * @returns {Object} {res_id, res_model, xpath}
     */
    _getRecordInfo: function (options) {
        options = options || {};
        var $editable = $(options.target).closest(this._getEditableArea());
        if (!$editable.length) {
            $editable = $(this._getFocusedEditable());
        }
        var data = this._super();
        var res_id = $editable.data('oe-id');
        var res_model = $editable.data('oe-model');
        if (!$editable.data('oe-model')) {
            var object = $('html').data('main-object');
            res_model = object.split('(')[0];
            res_id = +object.split('(')[1].split(',')[0];
        }
        var xpath = $editable.data('oe-xpath');

        if (options.type === 'media' && (res_model === 'website.page' || res_model === 'ir.ui.view')) {
            res_id = 0;
            res_model = 'ir.ui.view';
            xpath = null;
        }

        return _.extend(data, {
            res_id: res_id,
            res_model: res_model,
            xpath: xpath,
        });
    },
    /**
     * Return the focused editable area.
     *
     * @private
     * @returns {Node}
     */
    _getFocusedEditable: function () {
        var $focusedNode = $(this._focusedNode);
        var $editableArea = this._getEditableArea();
        return $focusedNode.closest($editableArea)[0] ||
               $focusedNode.find($editableArea)[0];
    },
    /**
     * Return the editable areas.
     *
     * @private
     * @returns {JQuery}
     */
    _getEditableArea: function () {
        if (!this._summernote) {
            return $();
        }
        return $(this.selectorEditableArea, this._summernote.layoutInfo.editable);
    },

    /**
     * @override
     * @returns {Promise}
     */
    _loadInstance: function () {
        return this._super().then(function () {
            var $target = this.$target;
            var id = $target.attr('id');
            var className = $target.attr('class');
            $target.off('.WysiwygFrontend');
            this.$target.find('[id]').add(this.$target).each(function () {
                var $node = $(this);
                $node.attr('data-old-id', $node.attr('id')).removeAttr('id');
            });
            this.$('.note-editable:first').attr('id', id).addClass(className);
            this.selectorEditableArea = '.o_editable';
        }.bind(this));
    },
    /**
     * @private
     * @returns {Promise}
     */
    _saveEditable: function (editable) {
        var self = this;
        var recordInfo = this._getRecordInfo({target: editable});
        var outerHTML = this._getCleanedHtml(editable).prop('outerHTML');
        var def = this._saveElement(outerHTML, recordInfo, editable);
        def.done(function () {
            self.trigger_up('saved', recordInfo);
        }).fail(function () {
            self.trigger_up('canceled', recordInfo);
        });
        return def;
    },
    /**
     * @private
     * @returns {$.Promise}
     */
    _saveCroppedImages: function () {
        var self = this;
        var $area = $(this.selectorEditableArea, this.$target);
        var defs = $area.find('.o_cropped_img_to_save').map(function () {
            var $croppedImg = $(this);
            $croppedImg.removeClass('o_cropped_img_to_save');
            var resModel = $croppedImg.data('crop:resModel');
            var resID = $croppedImg.data('crop:resID');
            var cropID = $croppedImg.data('crop:id');
            var mimetype = $croppedImg.data('crop:mimetype');
            var originalSrc = $croppedImg.data('crop:originalSrc');
            var datas = $croppedImg.attr('src').split(',')[1];
            if (!cropID) {
                var name = originalSrc + '.crop';
                return self._rpc({
                    model: 'ir.attachment',
                    method: 'create',
                    args: [{
                        res_model: resModel,
                        res_id: resID,
                        name: name,
                        datas_fname: name,
                        datas: datas,
                        mimetype: mimetype,
                        url: originalSrc, // To save the original image that was cropped
                    }],
                }).then(function (attachmentID) {
                    return self._rpc({
                        model: 'ir.attachment',
                        method: 'generate_access_token',
                        args: [[attachmentID]],
                    }).then(function (access_token) {
                        $croppedImg.attr('src', '/web/image/' + attachmentID + '?access_token=' + access_token[0]);
                    });
                });
            } else {
                return self._rpc({
                    model: 'ir.attachment',
                    method: 'write',
                    args: [[cropID], {datas: datas}],
                });
            }
        }).get();
        return $.when.apply($, defs);
    },
    /**
     * Saves one (dirty) element of the page.
     *
     * @private
     * @param {string} outerHTML
     * @param {Object} recordInfo
     * @returns {Promise}
     */
    _saveElement: function (outerHTML, recordInfo) {
        return this._rpc({
            model: 'ir.ui.view',
            method: 'save',
            args: [
                recordInfo.res_id,
                outerHTML,
                recordInfo.xpath,
            ],
            kwargs: {
                context: recordInfo.context,
            },
        });
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {OdooEvent} ev
     */
    _onActivateSnippet: function (ev) {
        if (!$.contains(ev.data[0], this._focusedNode)) {
            this._focusedNode = ev.data[0];
        }
        ev.data.closest('.oe_structure > *:not(.o_fake_editable)').addClass('o_fake_editable').attr('contenteditable', true);
    },
    /**
     * @override
     */
    _onChange: function () {
        var editable = this._getFocusedEditable();
        $(editable).addClass('o_dirty');
        this._super.apply(this, arguments);
    },
    /**
     * @override
     * @param {OdooEvent} ev
     */
    _onContentChange: function (ev) {
        this._focusedNode = ev.target;
        this._super.apply(this, arguments);
    },
    /**
     * Triggered when the user begin to drop iamges in the editor.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {Node[]} ev.data.spinners
     * @param {$.Promise} ev.data.promises
     */
    _onDropImages: function (ev) {
        if (!this.snippets) {
            return;
        }
        var gallerySelector = this.snippets.$('[data-js="gallery"]').data('selector');
        var $gallery = this.snippets.$activeSnippet && this.snippets.$activeSnippet.closest(gallerySelector) || $();

        if (!$gallery.length && ev.data.spinners.length >= 2) {
            $gallery = this.snippets.$snippets.filter(':has(' + gallerySelector + ')').first();
            var $drag = $gallery.find('.oe_snippet_thumbnail');
            var pos = $drag.offset();

            $gallery.find('section').attr('id', 'onDropImagesGallery');

            $drag.trigger($.Event("mousedown", {
                which: 1,
                pageX: pos.left,
                pageY: pos.top
            }));

            pos = $(ev.data.spinners[0]).offset();
            $drag.trigger($.Event("mousemove", {
                which: 1,
                pageX: pos.left,
                pageY: pos.top
            }));
            $drag.trigger($.Event("mouseup", {
                which: 1,
                pageX: pos.left,
                pageY: pos.top
            }));

            $gallery = $('#wrapwrap #onDropImagesGallery').removeAttr('id');
        }

        if (!$gallery.length) {
            return;
        }

        $(ev.data.spinners).remove();

        _.each(ev.data.promises, function (promise) {
            promise.then(function (image) {
                $gallery.find('.container:first').append(image);
            });
        });
    },
    /**
     * @override
     */
    _onFocusnode: function (node) {
        this._focusedNode = node;
        this._super.apply(this, arguments);
    },
});

return WysiwygMultizone;
});
