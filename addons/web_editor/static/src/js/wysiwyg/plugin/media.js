odoo.define('web_editor.wysiwyg.plugin.media', function (require) {
'use strict';

var core = require('web.core');
var weWidgets = require('wysiwyg.widgets');
var AbstractPlugin = require('web_editor.wysiwyg.plugin.abstract');
var registry = require('web_editor.wysiwyg.plugin.registry');
var Plugins = require('web_editor.wysiwyg.plugins');
var wysiwygTranslation = require('web_editor.wysiwyg.translation');
var wysiwygOptions = require('web_editor.wysiwyg.options');
var fonts = require('wysiwyg.fonts');

var _t = core._t;

var dom = $.summernote.dom;
var ui = $.summernote.ui;

//--------------------------------------------------------------------------
// Media (for image, video, icon, document)
//--------------------------------------------------------------------------

/**
 * Return true if the node is a media (image, icon, document or video).
 *
 * @param {Node} node
 * @returns {Boolean}
 */
dom.isMedia = function (node) {
    return dom.isImg(node) ||
        dom.isIcon(node) ||
        dom.isDocument(node) ||
        dom.isVideo(node);
};

var MediaPlugin = AbstractPlugin.extend({
    events: {
        'summernote.mousedown': '_onMouseDown',
        'summernote.keydown': '_onKeydown',
        'summernote.keyup': '_onKeyup',
        'summernote.scroll': '_onScroll',
        'summernote.disable': '_onDisable',
        'summernote.change': '_onChange',
        'summernote.codeview.toggled': '_onToggled',
        'dblclick .note-editable': '_onDblclick',
    },

    mousePosition: {},
    _modalOpen: false,

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Open the image dialog and listen to its saved/closed events.
     */
    showImageDialog: function () {
        if (this._modalOpen) {
            return;
        }
        this._modalOpen = true;
        this.context.invoke('editor.saveRange');
        var media = this.context.invoke('editor.restoreTarget');

        var $mediaParent = $(media).parent();
        if ($mediaParent.hasClass('media_iframe_video')) {
            media = $mediaParent[0];
            $mediaParent = $mediaParent.parent();
        }
        var mediaDialog = new weWidgets.MediaDialog(this.options.parent, {
            onlyImages: $mediaParent.data('oeField') === 'image' || $mediaParent.data('oeType') === 'image',
        },
            $(media).clone(true, true).removeData('snippetEditor')[0]
        );

        mediaDialog.on('saved', this, function (data) {
            this.insertMedia(media, data);
        });
        mediaDialog.on('closed', this, function () {
            this.context.invoke('editor.restoreRange');
            this._modalOpen = false;
        });
        mediaDialog.open();
    },
    /**
     * Remove the current target media and hide its popover.
     */
    removeMedia: function () {
        this.context.invoke('editor.beforeCommand');
        var target = this.context.invoke('editor.restoreTarget');
        var point = this.context.invoke('HelperPlugin.removeBlockNode', target);
        var rng = this.context.invoke('editor.setRange', point.node, point.offset);
        rng.normalize().select();
        this.context.invoke('editor.saveRange');
        this.context.invoke('editor.clearTarget');
        this.hidePopovers();
        this.context.invoke('editor.afterCommand');
    },
    /**
     * Update the target media and its popover.
     *
     * @param {Node} target
     */
    update: function (target) {
        if (!target || !dom.isMedia(target)) {
            return;
        }
        if (!this.options.displayPopover(target)) {
            if (dom.isImg(target)) {
                this.context.invoke('HandlePlugin.update', target);
            }
            return;
        }

        this.lastPos = this.context.invoke('HelperPlugin.makePoint', target, $(target).offset());

        this.context.triggerEvent('focusnode', target);

        if (!dom.isMedia(target)) {
            return;
        }

        this.context.invoke('editor.saveTarget', target);

        var $target = $(target);
        if (!$target.data('show_tooltip') && this.context.options.tooltip) {
            $target.data('show_tooltip', true);
            setTimeout(function () {
                $target.tooltip({
                    title: _t('Double-click to edit'),
                    trigger: 'manual',
                    container: this.document.body,
                }).tooltip('show');
                setTimeout(function () {
                    $target.tooltip('dispose');
                }, 2000);
            }, 400);
        }

        if (dom.isImg(target)) {
            this.context.invoke('ImagePlugin.show', target, this.mousePosition);
        } else if (dom.isIcon(target)) {
            this.context.invoke('IconPlugin.show', target, this.mousePosition);
        } else if (dom.isVideo(target)) {
            this.context.invoke('VideoPlugin.show', target, this.mousePosition);
        } else if (dom.isDocument(target)) {
            this.context.invoke('DocumentPlugin.show', target, this.mousePosition);
        }
    },
    /**
     * Hide all open popovers.
     * Warning: removes the saved target.
     */
    hidePopovers: function () {
        var media = this.context.invoke('editor.restoreTarget');
        this.context.invoke('HandlePlugin.hide');
        this.context.invoke('ImagePlugin.hide');
        this.context.invoke('IconPlugin.hide');
        this.context.invoke('VideoPlugin.hide');
        this.context.invoke('DocumentPlugin.hide');
        this.context.invoke('editor.saveTarget', media);
    },
    /**
     * Insert or replace a media.
     *
     * @param {Node} previous the media to replace, if any
     * @param {Object} data contains the media to insert
     */
    insertMedia: function (previous, data) {
        if (!data.media) {
            return;
        }
        var newMedia = data.media;
        this._wrapCommand(function () {
            this.$editable.focus();
            var rng = this.context.invoke('editor.createRange');
            var point;

            if (newMedia.tagName === "IMG") {
                $(newMedia).one('load error abort', this.updatePopoverAfterEdit.bind(this, newMedia));
            }

            if (previous) {
                this.context.invoke('editor.clearTarget');
                var start = previous.parentNode;
                rng = this.context.invoke('editor.setRange', start, _.indexOf(start.childNodes, previous));
                if (previous.tagName === newMedia.tagName) {
                    // Eg: replace an image with an image -> reapply classes removed by `clear` except previous icon
                    var faIcons = _.flatten(_.map(fonts.fontIcons, function (icon) {
                        return icon.alias;
                    }));
                    var oldClasses = _.difference(_.toArray(previous.classList), faIcons);
                    newMedia.className = _.union(_.toArray(newMedia.classList), oldClasses).join(' ');
                }

                if (dom.isVideo(previous) || dom.isVideo(newMedia)) {
                    var doNotInsertP = previous.tagName === newMedia.tagName;
                    point = this.context.invoke('HelperPlugin.removeBlockNode', previous, doNotInsertP);
                    if (!rng.sc.parentNode || !rng.sc.childNodes[rng.so]) {
                        rng = this.context.invoke('editor.setRange', point.node, point.offset);
                    }
                    previous = null;
                }
                rng.select();
                this.hidePopovers();
            }

            if (dom.isVideo(newMedia)) {
                this.context.invoke('HelperPlugin.insertBlockNode', newMedia);
            } else {
                rng = this.context.invoke('editor.createRange');
                point = rng.getStartPoint();
                if (!rng.isCollapsed()) {
                    point = this.context.invoke('HelperPlugin.deleteBetween', point, rng.getEndPoint());
                }

                if (point.node.tagName) {
                    if (previous) {
                        $(previous).replaceWith(newMedia);
                    } else if (dom.isVoid(point.node)) {
                        point.node.parentNode.insertBefore(newMedia, point.node);
                    } else {
                        var node = point.node.childNodes[point.offset];
                        if (point.node.tagName === 'BR') {
                            $(point.node).replaceWith(newMedia);
                        } else if (node && node.tagName === 'BR') {
                            $(node).replaceWith(newMedia);
                        } else {
                            point.node.insertBefore(newMedia, node || null);
                        }
                    }
                    if (!this._isFakeNotEditable(newMedia)) {
                        if (!newMedia.previousSibling) {
                            $(newMedia).before(this.document.createTextNode('\u200B'), newMedia);
                        }
                        if (!newMedia.nextSibling) {
                            $(newMedia).after(this.document.createTextNode('\u200B'), newMedia);
                        }
                    }
                } else {
                    var next = this.document.createTextNode(point.node.textContent.slice(point.offset));
                    point.node.textContent = point.node.textContent.slice(0, point.offset);

                    $(point.node).after(next).after(newMedia);
                    point.node.parentNode.normalize();
                    if (!this._isFakeNotEditable(newMedia)) {
                        if (!newMedia.previousSibling) {
                            $(newMedia).before(this.document.createTextNode('\u200B'), newMedia);
                        }
                        if (!newMedia.nextSibling) {
                            $(newMedia).after(this.document.createTextNode('\u200B'), newMedia);
                        }
                    }
                    rng = this.context.invoke('editor.setRange', newMedia.nextSibling || newMedia, 0);
                    rng.normalize().select();
                }
            }
            this.context.invoke('editor.saveRange');
            this.context.invoke('editor.saveTarget', newMedia);
            this.context.triggerEvent('focusnode', newMedia);
            this.context.invoke('UnbreakablePlugin.secureArea', newMedia);

            this.updatePopoverAfterEdit(newMedia);
        })();
    },
    /**
     * Update the media's popover and its position after editing the media.
     *
     * @param {Node} media
     */
    updatePopoverAfterEdit: function (media) {
        this.mousePosition = {
            pageX: $(media).offset().left + $(media).width() / 2,
            pageY: $(media).offset().top + $(media).height() / 2,
        };
        $(media).trigger('mousedown').trigger('mouseup');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add the media popovers' buttons:
     * - Replacement
     * - Removal
     * - Alignment
     * - Padding
     *
     * @override
     */
    _addButtons: function () {
        var self = this;
        this._super();

        this.context.memo('button.mediaPlugin', function () {
            return self.context.invoke('buttons.button', {
                contents: self.ui.icon(self.options.icons.picture),
                tooltip: self.lang.image.image,
                click: self.context.createInvokeHandler('MediaPlugin.showImageDialog')
            }).render();
        });

        this.context.memo('button.removePluginMedia', function () {
            return self.context.invoke('buttons.button', {
                contents: self.ui.icon(self.options.icons.trash),
                tooltip: self.lang.image.remove,
                click: self._wrapCommand(function () {
                    this.context.invoke('MediaPlugin.removeMedia');
                })
            }).render();
        });

        _.each(['left', 'center', 'right', 'none'], function (align) {
            var alignName = _.str.camelize('align_' + align);
            self._createButton(alignName, self.options.icons[alignName], self.lang.image[alignName], function () {
                var $target = $(self.context.invoke('editor.restoreTarget'));
                $target.css('float', '').removeClass('mx-auto pull-right pull-left');
                if (align === 'center') {
                    $target.addClass('mx-auto');
                } else if (align !== 'none') {
                    $target.addClass('pull-' + align);
                }
            });
        });

        var padding = [null, 'padding-small', 'padding-medium', 'padding-large', 'padding-xl'];
        var zipped = _.zip(padding, this.lang.image.paddingList);
        var values = _.map(zipped, function (z) {
            return {
                value: z[0],
                string: z[1],
            };
        });
        this._createDropdownButton('padding', this.options.icons.padding, this.lang.image.padding, values);
    },
    /**
     * Return true if the node is a fake not-editable.
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    _isFakeNotEditable: function (node) {
        var contentEditableAncestor = dom.ancestor(node, function (n) {
            return !!n.contentEditable && n.contentEditable !== 'inherit';
        });
        return !!contentEditableAncestor && contentEditableAncestor.contentEditable === 'false';
    },
    /**
     * Select the target media based on the
     * currently saved target or on the current range.
     *
     * @private
     * @param {Node} [target] optional
     * @returns {Node} target
     */
    _selectTarget: function (target) {
        if (!target) {
            target = this.context.invoke('editor.restoreTarget');
        }

        if (this.context.isDisabled()) {
            this.hidePopovers();
            this.context.invoke('editor.clearTarget');
            return target;
        }
        var range = this.context.invoke('editor.createRange');
        if (!target && range.isCollapsed()) {
            target = range.sc.childNodes[range.so] || range.sc;
        }
        if (!target || !dom.isMedia(target)) {
            this.hidePopovers();
            this.context.invoke('editor.clearTarget');
            return target;
        }

        while (target.parentNode && dom.isMedia(target.parentNode)) {
            target = target.parentNode;
        }

        if (!this.options.isEditableNode(target)) {
            if (!target.parentNode) {
                target = this.editable;
            }
            this.hidePopovers();
            this.context.invoke('editor.clearTarget');
            return target;
        }

        this.context.invoke('editor.saveTarget', target);
        this.context.triggerEvent('focusnode', target);

        return target;
    },
    /**
     * Select the target media on the right (or left)
     * of the currently selected target media.
     *
     * @private
     * @param {Node} target
     * @param {Boolean} left
     */
    _moveTargetSelection: function (target, left) {
        if (!target || !dom.isMedia(target)) {
            return;
        }
        var range = this.context.invoke('editor.createRange');
        var $contentEditable;

        if (
            range.sc.tagName && $.contains(target, range.sc) &&
            $(range.sc).hasClass('o_fake_editable') &&
            left === !range.sc.previousElementSibling
        ) {
            $contentEditable = $(range.sc).closest('[contentEditable]');
            if ($(target).closest('[contentEditable]')[0] !== $contentEditable[0]) {
                $contentEditable.focus();
            }
            this.context.invoke('editor.saveRange');
            return;
        }

        var next = this.context.invoke('HelperPlugin.makePoint', target, 0);
        if (left) {
            if (dom.isVideo(target)) {
                next = this.context.invoke('HelperPlugin.makePoint', target.firstElementChild, 0);
            } else {
                next = dom.prevPointUntil(next, function (point) {
                    return point.node !== target && !$.contains(target, point.node);
                }) || next;
            }
        } else {
            if (dom.isVideo(target)) {
                next = this.context.invoke('HelperPlugin.makePoint', target.lastElementChild, 0);
            } else {
                next = dom.nextPointUntil(next, function (point) {
                    return point.node !== target && !$.contains(target, point.node);
                }) || next;
            }
        }

        $contentEditable = $(next.node).closest('[contentEditable]');
        if ($(target).closest('[contentEditable]')[0] !== $contentEditable[0]) {
            // move the focus only if the new contentEditable is not the same (avoid scroll up)
            // (like in the case of a video, which uses two contentEditable in the media, so as to write text)
            $contentEditable.focus();
        }

        range = this.context.invoke('editor.setRange', next.node, next.offset);
        range.select();

        this.context.invoke('editor.saveRange');
    },

    //--------------------------------------------------------------------------
    // handle
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onDisable: function () {
        this.hidePopovers();
        this.context.invoke('editor.clearTarget');
    },
    /**
     * @private
     * @param {jQueryEvent} e
     */
    _onDblclick: function (e) {
        if (dom.isMedia(e.target)) {
            var target = this._selectTarget(e.target);
            this._moveTargetSelection(target);
            this.showImageDialog();
        }
    },
    /**
     * @private
     **/
    _onKeydown: function () {
        this.context.invoke('editor.clearTarget');
    },
    /**
     * @private
     * @param {SummernoteEvent} se
     * @param {jQueryEvent} e
     */
    _onKeyup: function (se, e) {
        var target = this._selectTarget();
        var range = this.context.invoke('editor.createRange');
        if (e.keyCode === 37) {
            var point = dom.prevPoint(range.getStartPoint());
            if (dom.isMedia(point.node)) {
                target = point.node;
            }
        }
        this._moveTargetSelection(target, e.keyCode === 37);
        return this.update(target);
    },
    /**
     * @private
     */
    _onScroll: function () {
        var target = this._selectTarget();
        if (this.lastPos && this.lastPos.target === target && $(target).offset()) {
            var newTop = $(target).offset().top;
            var movement = this.lastPos.offset.top - newTop;
            if (movement && this.mousePosition) {
                this.mousePosition.pageY -= movement;
            }
        }
        return this.update(target);
    },
    /**
     * @private
     */
    _onChange: function () {
        var target = this._selectTarget();
        this._moveTargetSelection(target);
        if (!this.$editable.has(target).length) {
            return;
        }
        return this.update(target);
    },
    /**
     * @private
     * @param {SummernoteEvent} se
     * @param {jQueryEvent} e
     */
    _onMouseDown: function (se, e) {
        var target = this._selectTarget(e.target);
        if (target && dom.isMedia(target)) {
            var pos = $(target).offset();

            if (e.pageX) {
                this.mousePosition = {
                    pageX: e.pageX,
                    pageY: e.pageY,
                };
            } else {
                // for testing triggers
                this.mousePosition = {
                    pageX: pos.left,
                    pageY: pos.top,
                };
            }

            var width = $(target).width();
            // we put the cursor to the left if we click in the first tier of the media
            var left = this.mousePosition.pageX < (pos.left + width / 3);
            this._moveTargetSelection(target, left);

            this.update(target);
            e.preventDefault();
        } else {
            this.mousePosition = {};
        }
    },
    /**
     * @private
     */
    _onToggled: function () {
        this.update();
    },
});

_.extend(wysiwygOptions.icons, {
    alignCenter: 'note-icon-align-center',
    alignNone: wysiwygOptions.icons.alignJustify,
    picture: 'fa fa-file-image-o',
});
_.extend(wysiwygTranslation.image, {
    alignRight: wysiwygTranslation.image.floatRight,
    alignCenter: _t('Align center'),
    alignLeft: wysiwygTranslation.image.floatLeft,
    alignNone: wysiwygTranslation.image.floatNone,
});

//--------------------------------------------------------------------------
// Abstract
//--------------------------------------------------------------------------

var AbstractMediaPlugin = AbstractPlugin.extend({
    targetType: null,
    initialize: function () {
        this._super.apply(this, arguments);
        this.$popover = this.ui.popover({
                className: 'note-' + this.targetType + '-popover',
            })
            .render().appendTo(this.options.container);
        var $content = this.$popover.find('.popover-content, .note-popover-content');
        this.context.invoke('buttons.build', $content, this.options.popover[this.targetType]);
        this.options.POPOVER_MARGIN = 15;
    },
    destroy: function () {
        this.$popover.remove();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Hide this popover.
     */
    hide: function () {
        this.$popover.hide();
    },
    /**
     * Show this popover.
     *
     * @param {Node} target
     * @param {Object} mousePosition {pageX: Number, pageY: Number}
     */
    show: function (target, mousePosition) {
        this._popoverPosition(target, mousePosition);
        ui.toggleBtnActive(this.$popover.find('a, button'), false);
        var $target = $(target);

        var float = $target.css('float');
        if (float === 'none' && $target.hasClass('mx-auto')) {
            float = 'center';
        }
        var floatIcon = this.options.icons[_.str.camelize('align_' + (float !== 'none' ? float : 'justify'))];
        ui.toggleBtnActive(this.$popover.find('.note-float button:has(.' + floatIcon + ')'), true);

        var padding = (($target.attr('class') || '').match(/(^| )(padding-[^\s]+)( |$)/) || ['fa-1x'])[2];
        ui.toggleBtnActive(this.$popover.find('.note-padding a:has(li[data-value="' + padding + '"])'), true);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Takes the left and top position of the popover and an optional margin
     * and returns updated positions to force the popover to fit the editor container.
     *
     * @private
     * @param {Number} left
     * @param {Number} top
     * @param {Number} [margin] optional
     * @returns {Object} {left: Number, top: Number}
     */
    _popoverFitEditor: function (left, top, margin) {
        margin = margin || this.options.POPOVER_MARGIN;

        var $container = $(this.options.container);
        var containerWidth = $container.width();
        var containerHeight = $container.height();

        var popoverWidth = this.$popover.width();
        var popoverHeight = this.$popover.height();

        var isBeyondXBounds = left + popoverWidth >= containerWidth - margin;
        var isBeyondYBounds = top + popoverHeight >= containerHeight - margin;
        return {
            left: isBeyondXBounds ? containerWidth - popoverWidth - margin : left,
            top: isBeyondYBounds ? top = containerHeight - popoverHeight - margin : (top > 0 ? top : margin),
        };
    },
    /**
     * Update the position of the popover in CSS.
     *
     * @private
     * @param {Node} target
     * @param {Object} mousePosition {pageX: Number, pageY: Number}
     */
    _popoverPosition: function (target, mousePosition) {
        var pos = $(this.options.container).offset();
        pos.left = mousePosition.pageX - pos.left + this.options.POPOVER_MARGIN;
        pos.top = mousePosition.pageY - pos.top + this.options.POPOVER_MARGIN;

        var popoverPos = this._popoverFitEditor(pos.left, pos.top);
        this.$popover.css({
            display: 'block',
            left: popoverPos.left,
            top: popoverPos.top,
        });
    },
    /**
     * Override to return whether the target is a media (specific to its class) or not.
     *
     * @private
     * @param {Node} target
     */
    _isMedia: function (target) {},
});

//--------------------------------------------------------------------------
// Image
//--------------------------------------------------------------------------

var ImagePlugin = AbstractMediaPlugin.extend({
    targetType: 'image',

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Open the crop image dialog and listen to its saved/closed events.
     */
    cropImageDialog: function () {
        this.context.invoke('editor.saveRange');

        var media = this.context.invoke('editor.restoreTarget');
        var cropImageDialog = new weWidgets.CropImageDialog(this.options.parent, {},
            $(media).clone(true, true)
        );
        cropImageDialog.on('saved', this, function (data) {
            this.context.invoke('MediaPlugin.insertMedia', media, data);
        });
        cropImageDialog.on('closed', this, function () {
            this.context.invoke('editor.restoreRange');
        });

        cropImageDialog.open();
    },
    /**
     * Open the alt dialog (change image title and alt) and listen to its saved/closed events.
     */
    altDialg: function () {
        this.context.invoke('editor.saveRange');

        var media = this.context.invoke('editor.restoreTarget');
        var altDialog = new weWidgets.AltDialog(this.options.parent, {},
            $(media).clone(true, true)
        );
        altDialog.on('saved', this, this._wrapCommand(function (data) {
            $(media).attr('alt', $(data.media).attr('alt'))
                .attr('title', $(data.media).attr('title'))
                .trigger('content_changed');
        }));
        altDialog.on('closed', this, function () {
            this.context.invoke('editor.restoreRange');
        });

        altDialog.open();
    },
    /**
     * Show the image target's popover.
     *
     * @override
     * @param {Node} target
     * @param {Object} mousePosition {pageX: Number, pageY: Number}
     */
    show: function (target, mousePosition) {
        var self = this;
        this._super.apply(this, arguments);
        var $target = $(target);

        this.context.invoke('HandlePlugin.update', target);

        _.each(this.options.icons.imageShape, function (icon, className) {
            var thisIconSel = '.note-imageShape button:has(.' +
                icon.replace(self.context.invoke('HelperPlugin.getRegex', 'space', 'g'), '.') +
                ')';
            ui.toggleBtnActive(self.$popover.find(thisIconSel), $target.hasClass(className));
        });

        var size = (($target.attr('style') || '').match(/width:\s*([0-9]+)%/i) || [])[1];
        ui.toggleBtnActive(this.$popover.find('.note-imagesize button:contains(' + (size ? size + '%' : this.lang.image.imageSizeAuto) + ')'), true);

        ui.toggleBtnActive(this.$popover.find('.note-cropImage button'), $target.hasClass('o_cropped_img_to_save'));

        // update alt button in popover
        if ($target.attr('alt')) {
            var $altLabel = $(this.altBtnPrefix).text(function (i, v) {
                var newText = v + '\u00A0' + $target.attr('alt');
                return $.trim(newText).substring(0, 30).trim(this) + "...";
            });
            this.$popover.find('.note-alt button').contents().replaceWith($altLabel);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Save cropped images.
     *
     * @private
     * @returns {Promise}
     */
    _saveCroppedImages: function () {
        var self = this;
        var defs = this.$editables.find('.o_cropped_img_to_save').map(function () {
            var $croppedImg = $(this);
            $croppedImg.removeClass('o_cropped_img_to_save');
            var resModel = $croppedImg.data('crop:resModel');
            var resID = $croppedImg.data('crop:resID');
            var cropID = $croppedImg.data('crop:id');
            var mimetype = $croppedImg.data('crop:mimetype');
            var originalSrc = $croppedImg.data('crop:originalSrc');
            var datas = $croppedImg.attr('src').split(',')[1];
            var def;
            if (!cropID) {
                var name = originalSrc + '.crop';
                def = self._rpc({
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
                });
            } else {
                def = self._rpc({
                    model: 'ir.attachment',
                    method: 'write',
                    args: [
                        [cropID], {
                            datas: datas,
                        },
                    ],
                }).then(function () {
                    return cropID;
                });
            }
            return def.then(function (attachmentID) {
                return self._rpc({
                    model: 'ir.attachment',
                    method: 'generate_access_token',
                    args: [
                        [attachmentID],
                    ],
                }).then(function (access_token) {
                    $croppedImg.attr('src', '/web/image/' + attachmentID + '?access_token=' + access_token[0]);
                });
            });
        }).get();
        return Promise.all(defs);
    },
    /**
     * Add the image popovers' buttons:
     * From _super:
     * - Replacement
     * - Removal
     * - Alignment
     * - Padding
     * From this override:
     * - Shape
     * - Crop
     * - Alt
     * - Size
     *
     * @private
     */
    _addButtons: function () {
        var self = this;
        this._super();
        // add all shape buttons if this option is active
        this.context.memo('button.imageShape', function () {
            var $el = $();
            _.each(['rounded', 'rounded-circle', 'shadow', 'img-thumbnail'], function (shape) {
                $el = $el.add(self._createToggleButton(null, self.options.icons.imageShape[shape], self.lang.image.imageShape[shape], shape));
            });
            return $el;
        });
        this.context.memo('button.cropImage', function () {
            return self.context.invoke('buttons.button', {
                contents: self.ui.icon(self.options.icons.cropImage),
                tooltip: self.lang.image.cropImage,
                click: self.context.createInvokeHandler('ImagePlugin.cropImageDialog')
            }).render();
        });
        this.altBtnPrefix = '<b>' + self.lang.image.alt + '</b>';
        this.context.memo('button.alt', function () {
            return self.context.invoke('buttons.button', {
                contents: self.altBtnPrefix,
                click: self.context.createInvokeHandler('ImagePlugin.altDialg')
            }).render();
        });
        this.context.memo('button.imageSizeAuto', function () {
            return self.context.invoke('buttons.button', {
                contents: '<span class="note-iconsize-10">' + self.lang.image.imageSizeAuto + '</span>',
                click: self._wrapCommand(function () {
                    var target = this.context.invoke('editor.restoreTarget');
                    $(target).css({
                        width: '',
                        height: ''
                    });
                })
            }).render();
        });
    },
    /**
     * Return true if the target is an image.
     *
     * @override
     * @param {Node} target
     * @returns {Boolean} true if the target is an image
     */
    _isMedia: function (target) {
        return dom.isImg(target);
    },
});

_.extend(wysiwygOptions.icons, {
    padding: 'fa fa-plus-square-o',
    cropImage: 'fa fa-crop',
    imageShape: {
        rounded: 'fa fa-square',
        'rounded-circle': 'fa fa-circle-o',
        shadow: 'fa fa-sun-o',
        'img-thumbnail': 'fa fa-picture-o',
    },
});
_.extend(wysiwygTranslation.image, {
    padding: _t('Padding'),
    paddingList: [_t('None'), _t('Small'), _t('Medium'), _t('Large'), _t('Xl')],
    imageSizeAuto: _t('Auto'),
    cropImage: _t('Crop image'),
    imageShape: {
        rounded: _t('Shape: Rounded'),
        'rounded-circle': _t('Shape: Circle'),
        shadow: _t('Shape: Shadow'),
        'img-thumbnail': _t('Shape: Thumbnail'),
    },
    alt: _t('Description:'),
});

//--------------------------------------------------------------------------
// Video
//--------------------------------------------------------------------------

/**
 * Return true if the node is a video.
 *
 * @param {Node} node
 * @returns {Boolean}
 */
dom.isVideo = function (node) {
    node = node && !node.tagName ? node.parentNode : node;
    return (node.tagName === "IFRAME" || node.tagName === "DIV") &&
        (node.parentNode && node.parentNode.className && node.parentNode.className.indexOf('media_iframe_video') !== -1 ||
            node.className.indexOf('media_iframe_video') !== -1);
};

var VideoPlugin = AbstractMediaPlugin.extend({
    targetType: 'video',

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Show the video target's popover.
     *
     * @override
     * @param {Node} target
     * @param {Object} mousePosition {pageX: Number, pageY: Number}
     */
    show: function (target, mousePosition) {
        if (target.tagName === "DIV" && target.className.indexOf('css_editable_mode_display') !== -1) {
            target = target.parentNode;
            this.context.invoke('editor.saveTarget', target);
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return true if the target is a video.
     *
     * @override
     * @param {Node} target
     */
    _isMedia: function (target) {
        return dom.isVideo(target);
    },
});

//--------------------------------------------------------------------------
// Icons: Icon Awsome (and other with themes)
//--------------------------------------------------------------------------

/**
 * Return true if the node is an icon.
 *
 * @param {Node} node
 * @returns {Boolean}
 */
dom.isIcon = function (node) {
    node = node && !node.tagName ? node.parentNode : node;
    return node && node.className && node.className.indexOf(' fa-') !== -1;
};

var IconPlugin = AbstractMediaPlugin.extend({
    targetType: 'icon',

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Hide this icon's popover.
     *
     * @override
     */
    hide: function () {
        this._super();
        this.removeSelectedClass(this.lastIcon);
    },
    /**
     * Show the icon target's popover.
     *
     * @override
     * @param {Node} target
     */
    show: function (target) {
        this.removeSelectedClass(this.lastIcon);
        this.lastIcon = target;

        this._super.apply(this, arguments);

        var $target = $(target);
        ui.toggleBtnActive(this.$popover.find('.note-faSpin button'), $target.hasClass('fa-spin'));
        var faSize = parseInt((($target.attr('style') || '').match(/font-size:\s*([0-9](em|px))(;|$)/) || [])[1] || 0);
        if (!faSize) {
            faSize = (($target.attr('class') || '').match(/(^| )fa-([0-9])x( |$)/) || [])[2];
        }
        ui.toggleBtnActive(this.$popover.find('.note-faSize a[data-value="fa-' + faSize + 'x"]'), true);
        this.addSelectedClass(target);
    },
    /**
     * Add a class to the current target so as to show it's selected.
     *
     * @param {Node} target
     */
    addSelectedClass: function (target) {
        if (target) {
            $(target).addClass('o_we_selected_image');
        }
    },
    /**
     * Remove a class to the current target so as to show it's not selected.
     *
     * @param {Node} target
     */
    removeSelectedClass: function (target) {
        if (target) {
            $(target).removeClass('o_we_selected_image');
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add the icon popovers' buttons:
     * From _super:
     * - Replacement
     * - Removal
     * - Alignment
     * - Padding
     * From this override:
     * - Size
     * - Spin
     *
     * @private
     */
    _addButtons: function () {
        var self = this;
        this._super();
        var values = [{
                value: '',
                string: '1x',
            },
            {
                value: 'fa-2x',
                string: '2x',
            },
            {
                value: 'fa-3x',
                string: '3x',
            },
            {
                value: 'fa-4x',
                string: '4x',
            },
            {
                value: 'fa-5x',
                string: '5x',
            },
        ];
        var onFaSize = function (e) {
            var classNames = _.map(values, function (item) {
                return item.value;
            }).join(' ');
            var $target = $(self.context.invoke('editor.restoreTarget'));
            $target.removeClass(classNames);
            if ($(e.target).data('value')) {
                $target.addClass($(e.target).data('value'));
                $target.css('fontSize', '');
            }
        };
        this._createDropdownButton('faSize', this.options.icons.faSize, this.lang.image.faSize, values, onFaSize);
        this._createToggleButton('faSpin', this.options.icons.faSpin, this.lang.image.faSpin, 'fa-spin');
    },
    /**
     * Return true if the target is an icon.
     *
     * @override
     * @param {Node} target
     */
    _isMedia: function (target) {
        return dom.isIcon(target);
    },
    /**
     * Update the position of the popover in CSS.
     *
     * @override
     * @param {Node} target
     * @param {Object} mousePosition {pageX: Number, pageY: Number}
     */
    _popoverPosition: function (target, mousePosition) {
        var pos = $(target).offset();
        var posContainer = $(this.options.container).offset();
        pos.left = pos.left - posContainer.left + this.options.POPOVER_MARGIN + parseInt($(target).css('font-size')) + 10;
        pos.top = pos.top - posContainer.top + this.options.POPOVER_MARGIN;

        var popoverPos = this._popoverFitEditor(pos.left + 10, pos.top - 15);
        this.$popover.css({
            display: 'block',
            left: popoverPos.left,
            top: popoverPos.top,
        });
    },
});
_.extend(wysiwygOptions.icons, {
    faSize: 'fa fa-expand',
    faSpin: 'fa fa-refresh',
});
_.extend(wysiwygTranslation.image, {
    faSize: _t('Icon size'),
    faSpin: _t('Spin'),
});

//--------------------------------------------------------------------------
// Media Document
//--------------------------------------------------------------------------

/**
 * Return true is the node is a document.
 * @param {Node} node
 * @returns {Boolean}
 */
dom.isDocument = function (node) {
    node = node && !node.tagName ? node.parentNode : node;
    return node && (node.tagName === "A" && node.className.indexOf('o_image') !== -1);
};

var DocumentPlugin = AbstractMediaPlugin.extend({
    targetType: 'document',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return true if the target is an icon.
     *
     * @override
     * @param {Node} target
     */
    _isMedia: function (target) {
        return dom.isDocument(target);
    },
    /**
     * Update the position of the popover in CSS.
     *
     * @override
     * @param {Node} target
     * @param {Object} mousePosition {pageX: Number, pageY: Number}
     */
    _popoverPosition: function (target, mousePosition) {
        var pos = $(target).offset();
        var posContainer = $(this.options.container).offset();
        pos.left = pos.left - posContainer.left + this.options.POPOVER_MARGIN;
        pos.top = pos.top - posContainer.top + this.options.POPOVER_MARGIN;

        var popoverPos = this._popoverFitEditor(pos.left + 10, pos.top - 15);
        this.$popover.css({
            display: 'block',
            left: popoverPos.left,
            top: popoverPos.top,
        });
    },
});

//--------------------------------------------------------------------------
// Handle (hover image)
//--------------------------------------------------------------------------

var HandlePlugin = Plugins.handle.extend({
    /**
     * Update the handle.
     *
     * @param {Node} target
     * @returns {Boolean}
     */
    update: function (target) {
        if (this.context.isDisabled()) {
            return false;
        }
        var isImage = dom.isImg(target);
        var $selection = this.$handle.find('.note-control-selection');
        this.context.invoke('imagePopover.update', target);
        if (!isImage) {
            return isImage;
        }

        var $target = $(target);
        var pos = $target.offset();
        var posContainer = $selection.closest('.note-handle').offset();

        // exclude margin
        var imageSize = {
            w: $target.outerWidth(false),
            h: $target.outerHeight(false)
        };

        $selection.css({
            display: 'block',
            left: pos.left - posContainer.left,
            top: pos.top - posContainer.top,
            width: imageSize.w,
            height: imageSize.h,
        }).data('target', $target); // save current target element.

        var src = $target.attr('src');
        var displayInfo = imageSize.w >= 170 || (imageSize.w >= 120 && imageSize.h >= 58) || (imageSize.w >= 80 && imageSize.h >= 76);

        var sizingText = '';
        if (displayInfo) {
            sizingText = imageSize.w + 'x' + imageSize.h;
            sizingText += ' (' + this.lang.image.original + ': ';
        } else if (src && imageSize.w >= 80 && imageSize.h >= 32) {
            displayInfo = true;
            sizingText = '(';
        }

        if (src) {
            var origImageObj = new Image();
            origImageObj.src = src;
            sizingText += origImageObj.width + 'x' + origImageObj.height + ')';
        }

        $selection.find('.note-control-selection-info').text(sizingText);
        this.context.invoke('editor.saveTarget', target);

        return isImage;
    },
});

//--------------------------------------------------------------------------
// add to registry
//--------------------------------------------------------------------------

registry.add('MediaPlugin', MediaPlugin)
    .add('ImagePlugin', ImagePlugin)
    .add('VideoPlugin', VideoPlugin)
    .add('IconPlugin', IconPlugin)
    .add('DocumentPlugin', DocumentPlugin)
    .add('HandlePlugin', HandlePlugin);

// modules to remove from summernote
registry.add('imagePopover', null)
    .add('handle', null);

return {
    MediaPlugin: MediaPlugin,
    ImagePlugin: ImagePlugin,
    VideoPlugin: VideoPlugin,
    IconPlugin: IconPlugin,
    DocumentPlugin: DocumentPlugin,
};

});
