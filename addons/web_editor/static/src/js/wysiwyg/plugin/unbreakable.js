odoo.define('web_editor.wysiwyg.plugin.unbreakable', function (require) {
'use strict';

var AbstractPlugin = require('web_editor.wysiwyg.plugin.abstract');
var registry = require('web_editor.wysiwyg.plugin.registry');

var dom = $.summernote.dom;

//--------------------------------------------------------------------------
// unbreakable node preventing editing
//--------------------------------------------------------------------------

var Unbreakable = AbstractPlugin.extend({
    events: {
        'wysiwyg.range .note-editable': '_onRange',
        'summernote.mouseup': '_onMouseUp',
        'summernote.keyup': '_onKeyup',
        'summernote.keydown': '_onKeydown',
        // 'summernote.focusnode': '_onFocusnode', => add this event to summernote.
    },

    initialize: function () {
        var self = this;
        this._super.apply(this, arguments);
        setTimeout(function () {
            self.secureArea();
            self.context.invoke('HistoryPlugin.clear');
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Change the selection if it breaks an unbreakable node.
     *
        <unbreakable id="a">
            content_1
            <unbreakable id="b">content_2</unbreakable>
            <allow id="c">
                content_3
                <unbreakable id="d">content_4</unbreakable>
                <unbreakable id="e">
                    content_5
                    <allow id="f">content_6</allow>
                    content_7
                </unbreakable>
                content_8
            </allow>
            <unbreakable id="f">content_9</unbreakable>
            <allow id="g">
                content_10
                <unbreakable id="h">content_11</unbreakable>
                content_12
            </allow>
        </unbreakable>

        START            END            RESIZE START     RESIZE END

        content_1       content_1       content_3       content_3   (find the first allowed node)
        content_1       content_2       content_3       content_3
        content_1       content_3       content_3       -
        content_3       content_3       -               -           (nothing to do)
        content_3       content_8       -               -           (can remove unbreakable node)
        content_3       content_4       -               content_3
        content_3       content_5       -               #d          (can select the entire unbreakable node)
        content_5       content_8       content_6       content_6
        content_5       content_7       #e              #e          (select the entire unbreakable node)
        content_6       content_8       -               content_6
        content_7       content_8       -               content_8
        content_9       content_12      content_10      -
        *
        * @returns {WrappedRange}
        */
    secureRange: function () {
        var self = this;
        var range = this.context.invoke('editor.createRange');
        var isCollapsed = range.isCollapsed();
        var needReselect = false;
        var startPoint = range.getStartPoint();
        var endPoint = range.getEndPoint();

        // don't change the selection if the carret is just after a media in editable area
        var prev;
        if (
            isCollapsed && startPoint.node.tagName && startPoint.node.childNodes[startPoint.offset] &&
            (prev = dom.prevPoint(startPoint)) && dom.isMedia(prev.node) &&
            this.options.isEditableNode(prev.node.parentNode)
        ) {
            return range;
        }

        // move the start selection to an allowed node
        var target = startPoint.node.childNodes[startPoint.offset] || startPoint.node;
        if (startPoint.offset && startPoint.offset === dom.nodeLength(startPoint.node)) {
            startPoint.node = this.context.invoke('HelperPlugin.lastLeaf', startPoint.node);
            startPoint.offset = dom.nodeLength(startPoint.node);
        }
        if (!dom.isMedia(target) || !this.options.isEditableNode(target)) {
            var afterEnd = false;
            startPoint = dom.nextPointUntil(startPoint, function (point) {
                if (point.node === endPoint.node && point.offset === endPoint.offset) {
                    afterEnd = true;
                }
                return self.options.isEditableNode(point.node) && dom.isVisiblePoint(point) || !point.node;
            });
            if (!startPoint || !startPoint.node) { // no allowed node, search the other way
                afterEnd = false;
                startPoint = dom.prevPointUntil(range.getStartPoint(), function (point) {
                    return self.options.isEditableNode(point.node) && dom.isVisiblePoint(point) || !point.node;
                });
            }
            if (startPoint && !startPoint.node) {
                startPoint = null;
            }
            if (afterEnd) {
                isCollapsed = true;
            }
        }

        if (startPoint && (startPoint.node !== range.sc || startPoint.offset !== range.so)) {
            needReselect = true;
            range.sc = startPoint.node;
            range.so = startPoint.offset;
            if (isCollapsed) {
                range.ec = range.sc;
                range.eo = range.so;
            }
        }

        if (startPoint && !isCollapsed) { // mouse selection or key selection with shiftKey
            var point = endPoint;
            endPoint = false;

            // if the start point was moved after the end point
            var toCollapse = !dom.prevPointUntil(point, function (point) {
                return point.node === range.sc && point.offset === range.so;
            });

            if (!toCollapse) {
                // find the first allowed ancestor
                var commonUnbreakableParent = dom.ancestor(range.sc, function (node) {
                    return !dom.isMedia(node) && self.options.isUnbreakableNode(node);
                });
                if (!commonUnbreakableParent) {
                    commonUnbreakableParent = this.editable;
                }

                var lastCheckedNode;
                if (point.offset === dom.nodeLength(point.node)) {
                    point = dom.nextPoint(point);
                }

                // move the end selection to an allowed node in the first allowed ancestor
                endPoint = dom.prevPointUntil(point, function (point) {
                    if (point.node === range.sc && point.offset === range.so) {
                        return true;
                    }
                    if (lastCheckedNode === point.node) {
                        return false;
                    }

                    // select the entirety of the unbreakable node
                    if (
                        point.node.tagName && point.offset &&
                        $.contains(commonUnbreakableParent, point.node) &&
                        self.options.isUnbreakableNode(point.node)
                    ) {
                        return true;
                    }

                    var unbreakableParent = dom.ancestor(point.node, function (node) {
                        return !dom.isMedia(node) && self.options.isUnbreakableNode(node);
                    });
                    if (!unbreakableParent) {
                        unbreakableParent = self.editable;
                    }

                    if (commonUnbreakableParent !== unbreakableParent) {
                        lastCheckedNode = point.node;
                        return false;
                    }
                    lastCheckedNode = point.node;
                    if (!self.options.isEditableNode(point.node)) {
                        return false;
                    }
                    if (
                        (/\S|\u200B|\u00A0/.test(point.node.textContent) ||
                            dom.isMedia(point.node)) &&
                        dom.isVisiblePoint(point)
                    ) {
                        return true;
                    }
                    if (dom.isText(point.node)) {
                        lastCheckedNode = point.node;
                    }
                    return false;
                });
            }

            if (!endPoint) {
                endPoint = range.getStartPoint();
            }

            if (endPoint.node !== range.ec || endPoint.offset !== range.eo) {
                needReselect = true;
                range.ec = endPoint.node;
                range.eo = endPoint.offset;
            }
        }

        if (needReselect) {
            range = range.select();
            this.context.invoke('editor.saveRange');
        }
        return range;
    },
    /**
     * Apply contentEditable false on all media.
     *
     * @param {DOM} [node] default is editable area
     */
    secureArea: function (node) {
        this.$editable.find('o_not_editable').attr('contentEditable', 'false');

        var medias = (function findMedia(node) {
            var medias = [];
            if (node.tagName !== 'IMG' && dom.isMedia(node)) {
                medias.push(node);
            } else {
                $(node.childNodes).each(function () {
                    if (this.tagName) {
                        medias.push.apply(medias, findMedia(this));
                    }
                });
            }
            return medias;
        })(node || this.editable);
        $(medias).addClass('o_fake_not_editable').attr('contentEditable', 'false');

        $(medias).each(function () {
            if (dom.isVideo(this) && !$(this).children('.o_fake_editable').length) {
                // allow char insertion
                $(this).prepend('<div class="o_fake_editable o_wysiwyg_to_remove" style="position: absolute;" contentEditable="true"/>');
                $(this).append('<div class="o_fake_editable o_wysiwyg_to_remove" style="position: absolute;" contentEditable="true"/>');
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Trigger a focusnode event when the focus enters another node.
     *
     * @param {DOM} node
     */
    _focusNode: function (node) {
        if (!node.tagName) {
            node = node.parentNode;
        }
        if (this._focusedNode !== node) {
            this._focusedNode = node;
            this.context.triggerEvent('focusnode', node);
        }
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Method called on wysiwyg.range event on the editable: secures the range, refocuses.
     */
    _onRange: function () {
        var range = this.secureRange();
        this._focusNode(range.sc);
    },
    /**
     * Method called on mouseup event: secures the range, refocuses.
     */
    _onMouseUp: function () {
        var range = this.secureRange();
        this._focusNode(range.ec);
    },
    /**
     * Method called on keydown event: prevents changes to unbreakable nodes.
     *
     * @param {SummernoteEvent} se
     * @param {jQueryEvent} e
     */
    _onKeydown: function (se, e) {
        if (!e.key || (e.key.length !== 1 && e.keyCode !== 8 && e.keyCode !== 46)) {
            return;
        }
        var range;
        // for test tour, to trigger Keydown on target (instead of use Wysiwyg.setRange)
        if (
            e.target !== this._focusedNode &&
            (this.editable === e.target || $.contains(this.editable, e.target))
        ) {
            range = this.context.invoke('editor.createRange');
            if (!$.contains(e.target, range.sc) && !$.contains(e.target, range.ec)) {
                range = this.context.invoke('editor.setRange', e.target, 0);
                range = range.normalize().select();
                this.context.invoke('editor.saveRange');
                this._focusNode(range.ec);
            }
        }

        // rerange to prevent some edition.
        // eg: if the user select with arraw and shifKey and keypress an other char
        range = this.secureRange();
        var target = range.getStartPoint();

        if (e.keyCode === 8) { // backspace
            if (!target || this.options.isUnbreakableNode(target.node)) {
                e.preventDefault();
            }
        } else if (e.keyCode === 46) { // delete
            target = dom.nextPointUntil(dom.nextPoint(target), dom.isVisiblePoint);
            if (!target || this.options.isUnbreakableNode(target.node)) {
                e.preventDefault();
            }
        }
    },
    /**
     * Method called on keyup event: prevents selection of unbreakable nodes.
     *
     * @param {SummernoteEvent} se
     * @param {jQueryEvent} se
     */
    _onKeyup: function (se, e) {
        if (e.keyCode < 37 || e.keyCode > 40) {
            return;
        }
        var range;
        if (e.keyCode === 37) { // left
            range = this.secureRange();
            this._focusNode(range.sc);
        } else if (e.keyCode === 39) { // right
            range = this.secureRange();
            this._focusNode(range.ec);
        } else if (e.keyCode === 38) { // up
            range = this.secureRange();
            this._focusNode(range.sc);
        } else { // down
            range = this.secureRange();
            this._focusNode(range.ec);
        }
    },
});

registry.add('UnbreakablePlugin', Unbreakable);

return Unbreakable;

});
