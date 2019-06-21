odoo.define('web_editor.wysiwyg.plugin.keyboard', function (require) {
'use strict';

var AbstractPlugin = require('web_editor.wysiwyg.plugin.abstract');
var registry = require('web_editor.wysiwyg.plugin.registry');

var dom = $.summernote.dom;
dom.isAnchor = function (node) {
    return (node.tagName === 'A' || node.tagName === 'BUTTON' || $(node).hasClass('btn')) &&
        !$(node).hasClass('fa') && !$(node).hasClass('o_image');
};

var KeyboardPlugin = AbstractPlugin.extend({
    events: {
        'summernote.keydown': '_onKeydown',
        'DOMNodeInserted .note-editable': '_removeGarbageSpans',
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------



    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Perform various DOM and range manipulations after a deletion:
     * - Rerange out of BR elements
     * - Clean the DOM at current range position
     *
     * @see _handleDeletion
     *
     * @private
     * @param {Object} range
     * @param {String('prev'|'next')} direction 'prev' to delete BEFORE the carret
     * @returns {Object} range
     */
    _afterDeletion: function (range, direction) {
        range = direction === 'prev' ? this._insertInvisibleCharAfterSingleBR(range) : range;
        range = this._rerangeOutOfBR(range, direction);
        range = this._cleanRangeAfterDeletion(range);
        return range;
    },
    /**
     * Perform operations that are necessary after the insertion of a visible character:
     * - Adapt range for the presence of zero-width characters
     * - Move out of media
     * - Rerange
     *
     * @private
     */
    _afterVisibleChar: function () {
        var range = this.context.invoke('editor.createRange');
        if (range.sc.tagName || dom.ancestor(range.sc, dom.isAnchor)) {
            return true;
        }
        var needReselect = false;
        var fake = range.sc.parentNode;
        if ((fake.className || '').indexOf('o_fake_editable') !== -1 && dom.isMedia(fake)) {
            var $media = $(fake.parentNode);
            $media[fake.previousElementSibling ? 'after' : 'before'](fake.firstChild);
            needReselect = true;
        }
        if (range.sc.textContent.slice(range.so - 2, range.so - 1) === '\u200B') {
            range.sc.textContent = range.sc.textContent.slice(0, range.so - 2) + range.sc.textContent.slice(range.so - 1);
            range.so = range.eo = range.so - 1;
            needReselect = true;
        }
        if (range.sc.textContent.slice(range.so, range.so + 1) === '\u200B') {
            range.sc.textContent = range.sc.textContent.slice(0, range.so) + range.sc.textContent.slice(range.so + 1);
            needReselect = true;
        }
        if (needReselect) {
            range.normalize().select();
        }
    },
    /**
     * Perform various DOM and range manipulations to prepare a deletion:
     * - Rerange within the element targeted by the range
     * - Slice the text content if necessary
     * - Move before an invisible BR if necessary
     * - Replace a media with an empty SPAN if necessary
     * - Change the direction of deletion if necessary
     * - Clean the DOM at range position if necessary
     *
     * @see _handleDeletion
     *
     * @private
     * @param {Object} range
     * @param {String('prev'|'next')} direction
     * @param {Boolean} didDeleteNodes true if nodes were already deleted prior to this call
     * @returns {Object} {didDeleteNodes: Boolean, range: Object, direction: String('prev'|next')}
     */
    _beforeDeletion: function (range, direction, didDeleteNodes) {
        var res = {
            range: range,
            direction: direction,
            didDeleteNodes: didDeleteNodes,
        };

        res.range = this._rerangeToOffsetChild(res.range, direction);
        res.range = this._sliceAndRerangeBeforeDeletion(res.range);
        res.range = direction === 'prev' ? this._moveBeforeInvisibleBR(res.range) : res.range;

        if (dom.isMedia(res.range.sc)) {
            var span = this._replaceMediaWithEmptySpan(res.range.sc);
            res.range = this.context.invoke('editor.setRange', span, 0);
            res.didDeleteNodes = true;
            return res;
        }

        if (res.didDeleteNodes) {
            res.direction = 'next';
            return res;
        }
        
        res.range = this._cleanRangeBeforeDeletion(res.range, direction);

        return res;
    },
    /**
     * Clean the DOM at range position after a deletion:
     * - Remove empty inline nodes
     * - Fill the current node if it's empty
     *
     * @private
     * @param {Object} range
     * @returns {Object} range
     */
    _cleanRangeAfterDeletion: function (range) {
        var point = range.getStartPoint();

        point = this.context.invoke('HelperPlugin.removeEmptyInlineNodes', point);
        point = this.context.invoke('HelperPlugin.fillEmptyNode', point);
        range = this.context.invoke('editor.setRange', point.node, point.offset);
        return range;
    },
    /**
     * Clean the DOM at range position:
     * - Remove all previous zero-width characters
     * - Remove leading/trailing breakable space
     *
     * @private
     * @param {Object} range
     * @param {String('prev'|'next')} direction
     * @returns {Object} range
     */
    _cleanRangeBeforeDeletion: function (range, direction) {
        if (direction === 'prev') {
            this._removeAllPreviousInvisibleChars(range);
        }
        range = this._removeExtremeBreakableSpaceAndRerange(range);
        return range;
    },
    /**
     * Get information on the range in order to perform a deletion:
     * - The point at which to delete, if any
     * - Whether the node contains a block
     * - The block to remove, if any
     *
     * @private
     * @param {Object} range
     * @param {String('prev'|'next')} direction
     * @param {Boolean} wasOnStartOfBR true if the requested deletion started at
     *                                 the beginning of a BR element
     * @returns {Object} {
     *      point: {false|Object},
     *      hasBlock: {Boolean},
     *      blockToRemove: {false|Node},
     * }
     */
    _getDeleteInfo: function (range, direction, wasOnStartOfBR) {
        var self = this;
        var hasBlock = false;
        var blockToRemove = false;
        var method = direction === 'prev' ? 'prevPointUntil' : 'nextPointUntil';

        var pt = range.getStartPoint();
        pt = dom[method](pt, function (point) {
            var isAtStartOfMedia = !point.offset && dom.isMedia(point.node);
            var isBRorHR = point.node.tagName === 'BR' || point.node.tagName === 'HR';
            var isRootBR = wasOnStartOfBR && point.node === range.sc;
            var isOnRange = range.ec === point.node && range.eo === point.offset;

            if (!point.offset && self.context.invoke('HelperPlugin.isNodeBlockType', point.node)) {
                hasBlock = true;
                if (blockToRemove) {
                    return true;
                }
            }

            if (!blockToRemove && (isAtStartOfMedia || isBRorHR && !isRootBR)) {
                blockToRemove = point.node;
                return false;
            }

            if (isOnRange) {
                return false;
            }

            return self._isDeletableNode(point.node);
        });

        return {
            point: pt || false,
            hasBlock: hasBlock,
            blockToRemove: blockToRemove,
        };
    },
    /**
     * Handle deletion (BACKSPACE / DELETE).
     *
     * @private
     * @param {String('prev'|'next')} direction 'prev' to delete BEFORE the carret
     * @returns {Boolean} true if case handled
     */
    _handleDeletion: function (direction) {
        var range = this.context.invoke('editor.createRange');
        range = direction === 'prev' && this._replaceEmptyParentWithEmptyP(range);
        if (range) {
            range = this._afterDeletion(range, direction);
            range.select();
            return true;
        }
        var didDeleteNodes = this.context.invoke('HelperPlugin.deleteSelection');
        range = this.context.invoke('editor.createRange');
        var wasOnStartOfBR = direction === 'prev' && !range.so && range.sc.tagName === 'BR';

        this._removeNextEmptyUnbreakable(range.sc);
        var temp = this._beforeDeletion(range, direction, didDeleteNodes);
        didDeleteNodes = temp.didDeleteNodes;
        range = temp.range;
        direction = temp.direction;

        if (!didDeleteNodes) {
            var newRange = this._performDeletion(range, direction, wasOnStartOfBR);
            didDeleteNodes = newRange.so !== range.so || newRange.sc !== range.sc;
            range = newRange;
        }

        range = this._afterDeletion(range, direction);

        range = range.collapse(direction === 'prev').select();
        this.editable.normalize();
        return didDeleteNodes;
    },
    /**
     * Handle ENTER.
     *
     * @private
     * @returns {Boolean} true if case handled
     */
    _handleEnter: function () {
        var self = this;
        var range = this.context.invoke('editor.createRange');

        var ancestor = dom.ancestor(range.sc, function (node) {
            return dom.isLi(node) || self.options.isUnbreakableNode(node.parentNode) && node.parentNode !== self.editable ||
                self.context.invoke('HelperPlugin.isNodeBlockType', node) && !dom.ancestor(node, dom.isLi);
        });

        if (
            dom.isLi(ancestor) && !$(ancestor.parentNode).hasClass('list-group') &&
            this.context.invoke('HelperPlugin.getRegexBlank', {
                space: true,
                newline: true,
            }).test(ancestor.textContent) &&
            $(ancestor).find('br').length <= 1 &&
            !$(ancestor).find('.fa, img').length
        ) {
            // double enter in a list make oudent
            this.context.invoke('BulletPlugin.outdent');
            return true;
        }

        var btn = dom.ancestor(range.sc, function (n) {
            return $(n).hasClass('btn');
        });

        var point = range.getStartPoint();

        if (!point.node.tagName && this.options.isUnbreakableNode(point.node.parentNode)) {
            return this._handleShiftEnter();
        }

        if (point.node.tagName && point.node.childNodes[point.offset] && point.node.childNodes[point.offset].tagName === "BR") {
            point = dom.nextPoint(point);
        }
        if (point.node.tagName === "BR") {
            point = dom.nextPoint(point);
        }

        var next = this.context.invoke('HelperPlugin.splitTree', ancestor, point, {
            isSkipPaddingBlankHTML: !this.context.invoke('HelperPlugin.isNodeBlockType', point.node.parentNode) && !!point.node.parentNode.nextSibling
        });
        $(next).removeClass('o_checked');
        while (next.firstChild) {
            next = next.firstChild;
        }

        // if there is no block in the split parents, then we add a br between the two node
        var hasSplitBlock = false;
        var node = next;
        var lastChecked = node;
        while (node && node !== ancestor && node !== this.editable) {
            if (this.context.invoke('HelperPlugin.isNodeBlockType', node)) {
                hasSplitBlock = true;
                break;
            }
            lastChecked = node;
            node = node.parentNode;
        }
        if (!hasSplitBlock && lastChecked.tagName) {
            $(lastChecked).before(this.document.createElement('br'));
        }

        if (!next.tagName) {
            this.context.invoke('HelperPlugin.secureExtremeSingleSpace', next);
        }
        if (next.tagName !== "BR" && next.innerHTML === "") {
            next.innerHTML = '\u200B';
        }
        if (ancestor) {
            var firstChild = this.context.invoke('HelperPlugin.firstLeaf', ancestor);
            var lastChild = this.context.invoke('HelperPlugin.lastLeaf', ancestor);
            if (this.context.invoke('HelperPlugin.isBlankNode', ancestor)) {
                firstChild = dom.isText(firstChild) ? firstChild.parentNode : firstChild;
                $(firstChild).contents().remove();
                $(firstChild).append(this.document.createElement('br'));
            }
            if (lastChild.tagName === 'BR' && lastChild.previousSibling) {
                $(lastChild).after(this.document.createTextNode('\u200B'));
            }
        }

        // move to next editable area
        point = this.context.invoke('HelperPlugin.makePoint', next, 0);
        if (
            (point.node.tagName && point.node.tagName !== 'BR') ||
            !this.context.invoke('HelperPlugin.isVisibleText', point.node.textContent)
        ) {
            point = dom.nextPointUntil(point, function (pt) {
                if (pt.node === point.node) {
                    return;
                }
                return (
                        pt.node.tagName === "BR" ||
                        self.context.invoke('HelperPlugin.isVisibleText', pt.node)
                    ) &&
                    self.options.isEditableNode(pt.node);
            });
            point = point || this.context.invoke('HelperPlugin.makePoint', next, 0);
            if (point.node.tagName === "BR") {
                point = dom.nextPoint(point);
            }
        }

        if (!hasSplitBlock && !point.node.tagName) {
            point.node.textContent = '\u200B' + point.node.textContent;
            point.offset = 1;
        }

        // if the left part of the split node ends with a space, replace that space with nbsp
        if (range.sc.textContent) {
            var endSpace = this.context.invoke('HelperPlugin.getRegex', 'endSpace');
            range.sc.textContent = range.sc.textContent.replace(endSpace,
                function (trailingSpaces) {
                    return Array(trailingSpaces.length + 1).join('\u00A0');
                }
            );
        }

        // On buttons, we want to split the button and move to the beginning of it
        if (btn) {
            next = dom.ancestor(point.node, function (n) {
                return $(n).hasClass('btn');
            });

            // Force content in empty buttons, the carret can be moved there
            this.context.invoke('LinkPopover.hide');
            this.context.invoke('LinkPopover.fillEmptyLink', next, true);
            this.context.invoke('LinkPopover.fillEmptyLink', btn, true);

            // Move carret to the new button
            range = this.context.invoke('editor.setRange', next.firstChild, 0);
            range.select();
        } else {
            range = this.context.invoke('editor.setRange', point.node, point.offset);
            range.normalize().select();
        }

        return true;
    },
    /**
     * Handle SHIFT+ENTER.
     * 
     * @private
     * @returns {Boolean} true if case handled
     */
    _handleShiftEnter: function () {
        var range = this.context.invoke('editor.createRange');
        var target = range.sc.childNodes[range.so] || range.sc;
        var before;
        if (target.tagName) {
            if (target.tagName === "BR") {
                before = target;
            } else if (target === range.sc) {
                if (range.so) {
                    before = range.sc.childNodes[range.so - 1];
                } else {
                    before = this.document.createTextNode('');
                    $(range.sc).append(before);
                }
            }
        } else {
            before = target;
            var after = target.splitText(target === range.sc ? range.so : 0);
            if (
                !after.nextSibling && after.textContent === '' &&
                this.context.invoke('HelperPlugin.isNodeBlockType', after.parentNode)
            ) {
                after.textContent = '\u200B';
            }
            if (!after.tagName && (!after.previousSibling || after.previousSibling.tagName === "BR")) {
                after.textContent = after.textContent.replace(startSpace, '\u00A0');
            }
        }

        if (!before) {
            return true;
        }

        var br = this.document.createElement('br');
        $(before).after(br);
        var next = this.context.invoke('HelperPlugin.makePoint', br, 0);
        var startSpace = this.context.invoke('HelperPlugin.getRegex', 'startSpace');

        if (!before.tagName) {
            next = dom.nextPoint(next);
            var nextNode = this.context.invoke('HelperPlugin.firstLeaf', next.node.childNodes[next.offset] || next.node);
            if (!nextNode.tagName) {
                next.node = nextNode;
                next.offset = 0;
            }
        }

        if (
            next.node.tagName === "BR" && next.node.nextSibling &&
            !next.node.nextSibling.tagName && !dom.ancestor(next.node, dom.isPre)
        ) {
            next.node.nextSibling.textContent = next.node.nextSibling.textContent.replace(startSpace, '\u00A0');
        }
        if (
            !next.node.tagName &&
            (!next.node.previousSibling || next.node.previousSibling.tagName === "BR") &&
            !dom.ancestor(next.node, dom.isPre)
        ) {
            next.node.textContent = next.node.textContent.replace(startSpace, '\u00A0');
        }

        range = this.context.invoke('editor.setRange', next.node, next.offset);
        range.select();

        return true;
    },
    /**
     * Insert a zero-width character after a BR if the range is
     * at the beginning of an invisible text node
     * and after said single BR element.
     *
     * @private
     * @param {Object} range
     * @returns {Object} range
     */
    _insertInvisibleCharAfterSingleBR: function (range) {
        if (this._isAtStartOfInvisibleText(range) && this._isAfterSingleBR(range.sc)) {
            var invisibleChar = this.document.createTextNode('\u200B');
            $(range.sc.previousSibling).after(invisibleChar);
            range = this.context.invoke('editor.setRange', invisibleChar, 1);
        }
        return range;
    },
    /**
     * Return true if the node comes after a BR element.
     *
     * @private
     * @param {Node} node
     * @returns {Boolean}
     */
    _isAfterBR: function (node) {
        return node.previousSibling && node.previousSibling.tagName === 'BR';
    },
    /**
     * Return true if the range if positioned after a BR element that doesn't visually
     * show a new line in the DOM: a BR in an element that has only a BR, or text then a BR.
     * eg: <p><br></p> or <p>text<br></p>
     *
     * @private
     * @param {Object} range
     * @returns {Boolean}
     */
    _isAfterInvisibleBR: function (range) {
        return this._isAfterOnlyBR(range) || this._isAfterOnlyTextThenBR(range);
    },
    /**
     * Return true if the range is positioned on a text node, after an zero-width character.
     *
     * @private
     * @param {Object} range
     * @returns {Boolean}
     */
    _isAfterInvisibleChar: function (range) {
        return !range.sc.tagName && range.so && range.sc.textContent[range.so - 1] === '\u200B';
    },
    /**
     * Return true if the range is positioned on a text node, after an leading zero-width character.
     *
     * @private
     * @param {Object} range
     * @returns {Boolean}
     */
    _isAfterLeadingInvisibleChar: function (range) {
        return !range.sc.tagName && range.so === 1 && range.sc.textContent[0] === '\u200B';
    },
    /**
     * Return true if the range if positioned after a BR element in a node that has only a BR.
     * eg: <p><br></p>
     *
     * @private
     * @param {Object} range
     * @returns {Boolean}
     */
    _isAfterOnlyBR: function (range) {
        return this._hasOnlyBR(range.sc) && range.so === 1;
    },
    /**
     * Return true if the node has for only element child a BR element.
     *
     * @private
     * @param {Node} node
     * @returns {Boolean}
     */
    _hasOnlyBR: function (node) {
        return node.childElementCount === 1 && node.firstChild.tagName === 'BR';
    },
    /**
     * Return true if the range if positioned after a BR element in a node that has only text
     * and ends with a BR.
     * eg: <p>text<br></p>
     *
     * @private
     * @param {Object} range
     * @returns {Boolean}
     */
    _isAfterOnlyTextThenBR: function (range) {
        var hasTrailingBR = range.sc.lastChild && range.sc.lastChild.tagName === 'BR';
        if (!hasTrailingBR) {
            return false;
        }
        var hasOnlyTextThenBR = _.all(range.sc.childNodes, function (n) {
            return dom.isText(n) || n === range.sc.lastChild;
        });
        var isAfterTrailingBR = range.so === dom.nodeLength(range.sc);
        return hasOnlyTextThenBR && isAfterTrailingBR;
    },
    /**
     * Return true if the node is after a single BR.
     *
     * @private
     * @param {Node} node
     * @returns {Boolean}
     */
    _isAfterSingleBR: function (node) {
        var isPreviousAfterBR = node.previousSibling && this._isAfterBR(node.previousSibling);
        return this._isAfterBR(node) && !isPreviousAfterBR;
    },
    /**
     * Return true if the node comes after two BR elements.
     *
     * @private
     * @param {Node} node
     * @returns {Boolean}
     */
    _isAfterTwoBRs: function (node) {
        var isAfterBR = this._isAfterBR(node);
        var isPreviousSiblingAfterBR = node.previousSibling && this._isAfterBR(node.previousSibling);
        return isAfterBR && isPreviousSiblingAfterBR;
    },
    /**
     * Return true if the range is positioned at the start of an invisible text node.
     *
     * @private
     * @param {Object} range
     * @returns {Boolean}
     */
    _isAtStartOfInvisibleText: function (range) {
        return !range.so && dom.isText(range.sc) && !this.context.invoke('HelperPlugin.isVisibleText', range.sc);
    },
    /**
     * Return true if the range is positioned on a text node, before a trailing zero-width character.
     *
     * @private
     * @param {Object} range
     * @returns {Boolean}
     */
    _isBeforeTrailingInvisibleChar: function (range) {
        var isBeforeLastCharOfText = !range.sc.tagName && range.so === dom.nodeLength(range.sc) - 1;
        var isLastCharInvisible = range.sc.textContent.slice(range.so) === '\u200B';
        return isBeforeLastCharOfText && isLastCharInvisible;
    },
    /**
     * Return true if the node is deletable.
     *
     * @private
     * @param {Node} node
     * @return {Boolean}
     */
    _isDeletableNode: function (node) {
        var isVisibleText = this.context.invoke('HelperPlugin.isVisibleText', node);
        var isMedia = dom.isMedia(node);
        var isBR = node.tagName === 'BR';
        var isEditable = this.options.isEditableNode(node);
        return isEditable && (isVisibleText || isMedia || isBR);
    },
    /**
     * Return true if the range is positioned on an edge to delete, depending on the given direction.
     *
     * @private
     * @param {Object} range
     * @param {String('prev'|'next')} direction
     */
    _isOnEdgeToDelete: function (range, direction) {
        var isOnBR = range.sc.tagName === 'BR';
        var parentHasOnlyBR = range.sc.parentNode && range.sc.parentNode.innerHTML.trim() === "<br>";
        var isOnDirEdge;
        if (direction === 'next') {
            isOnDirEdge = range.so === dom.nodeLength(range.sc);
        } else {
            isOnDirEdge = range.so === 0;
        }
        return (!isOnBR || parentHasOnlyBR) && isOnDirEdge;
    },
    /**
     * Move the range before a BR if that BR doesn't visually show a new line in the DOM.
     * Return the new range.
     *
     * @private
     * @param {Object} range
     * @returns {Object} range
     */
    _moveBeforeInvisibleBR: function (range) {
        if (this._isAfterInvisibleBR(range)) {
            range.so -= 1;
        }
        return range;
    },
    /**
     * Perform a deletion in the given direction.
     * Note: This is where the actual deletion takes place.
     *       It should be preceded by _beforeDeletion and
     *       followed by _afterDeletion.
     *
     * @see _handleDeletion
     *
     * @private
     * @param {Object} range
     * @param {String('prev'|'next')} direction 'prev' to delete BEFORE the carret
     * @param {Boolean} wasOnStartOfBR true if the requested deletion started at
     *                                 the beginning of a BR element
     * @returns {Object} range
     */
    _performDeletion: function (range, direction, wasOnStartOfBR) {
        var didDeleteNodes = false;
        if (this._isOnEdgeToDelete(range, direction)) {
            var rest = this.context.invoke('HelperPlugin.deleteEdge', range.sc, direction);
            didDeleteNodes = !!rest;
            if (didDeleteNodes) {
                range = this.context.invoke('editor.setRange', rest.node, rest.offset);
                return range;
            }
        }

        var deleteInfo = this._getDeleteInfo(range, direction, wasOnStartOfBR);

        if (!deleteInfo.point) {
            return range;
        }

        var point = deleteInfo.point;
        var blockToRemove = deleteInfo.blockToRemove;
        var hasBlock = deleteInfo.hasBlock;

        var isLonelyBR = blockToRemove && blockToRemove.tagName === 'BR' && this._hasOnlyBR(blockToRemove.parentNode);
        var isHR = blockToRemove && blockToRemove.tagName === "HR";

        if (blockToRemove && !isLonelyBR) {
            $(blockToRemove).remove();
            point = isHR ? this.context.invoke('HelperPlugin.deleteEdge', range.sc, direction) : point;
            didDeleteNodes = true;
        } else if (!hasBlock) {
            var isAtEndOfNode = point.offset === dom.nodeLength(point.node);
            var shouldMove = isAtEndOfNode || direction === 'next' && point.offset;

            point.offset = shouldMove ? point.offset - 1 : point.offset;
            point.node = this._removeCharAtOffset(point);
            didDeleteNodes = true;

            var isInPre = !!dom.ancestor(range.sc, dom.isPre);
            if (!isInPre) {
                this.context.invoke('HelperPlugin.secureExtremeSingleSpace', point.node);
            }

            if (direction === 'prev' && !point.offset && !this._isAfterBR(point.node)) {
                point.node = this._replaceLeadingSpaceWithSingleNBSP(point.node);
            }
        }

        if (didDeleteNodes) {
            range = this.context.invoke('editor.setRange', point.node, point.offset);
        }
        return range;
    },
    /**
     * Prevent the appearance of a text node with the editable DIV as direct parent:
     * wrap it in a p element.
     *
     * @private
     */
    _preventTextInEditableDiv: function () {
        var range = this.context.invoke('editor.createRange');
        while (
            dom.isText(this.editable.firstChild) &&
            !this.context.invoke('HelperPlugin.isVisibleText', this.editable.firstChild)
        ) {
            var node = this.editable.firstChild;
            if (node && node.parentNode) {
                node.parentNode.removeChild(node);
            }
        }
        var editableIsEmpty = !this.editable.childNodes.length;
        if (editableIsEmpty) {
            var p = this.document.createElement('p');
            p.innerHTML = '<br>';
            this.editable.appendChild(p);
            range = this.context.invoke('editor.setRange', p, 0);
        } else if (this.context.invoke('HelperPlugin.isBlankNode', this.editable.firstChild) && !range.sc.parentNode) {
            this.editable.firstChild.innerHTML = '<br/>';
            range = this.context.invoke('editor.setRange', this.editable.firstChild, 0);
        }

        range.select();
    },
    /**
     * Remove all invisible chars before the current range, that are adjacent to it,
     * then rerange.
     *
     * @private
     * @param {Object} range
     * @returns {Object} range
     */
    _removeAllPreviousInvisibleChars: function (range) {
        while (this._isAfterInvisibleChar(range)) {
            var text = range.sc.textContent;
            range.sc.textContent = text.slice(0, range.so - 1) + text.slice(range.so, text.length);
            range.so -= 1;
        }
        return range;
    },
    /**
     * Remove a char from a point's text node, at the point's offset.
     *
     * @private
     * @param {Object} point
     * @returns {Node}
     */
    _removeCharAtOffset: function (point) {
        var text = point.node.textContent;
        var startToOffset = text.slice(0, point.offset);
        var offsetToEnd = text.slice(point.offset + 1);
        point.node.textContent = startToOffset + offsetToEnd;
        return point.node;
    },
    /**
     * Remove any amount of leading/trailing breakable space at range position.
     * Then move the range and return it.
     *
     * @private
     * @param {Object} range
     * @returns {Object} range
     */
    _removeExtremeBreakableSpaceAndRerange: function (range) {
        var isInPre = !!dom.ancestor(range.sc, dom.isPre);
        if (!range.sc.tagName && !isInPre) {
            var changed = this.context.invoke('HelperPlugin.removeExtremeBreakableSpace', range.sc);
            range.so = range.eo = range.so > changed.start ? range.so - changed.start : 0;
            range.so = range.eo = range.so > dom.nodeLength(range.sc) ? dom.nodeLength(range.sc) : range.so;
            range.select();
            this.context.invoke('editor.saveRange');
        }
        return range;
    },
    /**
     * Patch for Google Chrome's contenteditable SPAN bug.
     *
     * @private
     * @param {jQueryEvent} e
     */
    _removeGarbageSpans: function (e) {
        if (e.target.className === "" && e.target.tagName == "SPAN" &&
            e.target.style.fontStyle === "inherit" &&
            e.target.style.fontVariantLigatures === "inherit" &&
            e.target.style.fontVariantCaps === "inherit") {
            var $span = $(e.target);
            $span.after($span.contents()).remove();
        }
    },
    /**
     * Remove the first unbreakable ancestor's next sibling if empty.
     *
     * @private
     * @param {Node} node
     */
    _removeNextEmptyUnbreakable: function (node) {
        var self = this;
        var unbreakable = dom.ancestor(node, this.options.isUnbreakableNode);
        if (unbreakable === this.editable) {
            return;
        }
        var nextUnbreakable = unbreakable && unbreakable.nextElementSibling;
        var isNextEmpty = nextUnbreakable && dom.isEmpty(nextUnbreakable) && !dom.isVoid(nextUnbreakable);
        var isNextContainsOnlyInvisibleText = nextUnbreakable && _.all($(nextUnbreakable).contents(), function (n) {
            return dom.isText(n) && !self.context.invoke('HelperPlugin.isVisibleText', n);
        });
        if (isNextEmpty || isNextContainsOnlyInvisibleText) {
            $(nextUnbreakable).remove();
        }
    },
    /**
     * If the range's start container is empty and constitutes the only contents of its parent,
     * replace it with an empty p, then rerange.
     *
     * @private
     * @param {Object} range
     * @returns {Object|undefined} range
     */
    _replaceEmptyParentWithEmptyP: function (range) {
        var node = range.sc.childElementCount === 1 && range.sc.firstChild.tagName === 'BR' ? range.sc.firstChild : range.sc;
        if (node === this.editable || !node.parentNode || node.parentNode === this.editable) {
            return;
        }
        if (
            dom.isEmpty(node) &&
            this.context.invoke('HelperPlugin.onlyContains', node.parentNode, node) &&
            ['LI', 'P'].indexOf(node.parentNode.tagName) === -1
        ) {
            var emptyP = this.document.createElement('p');
            var br = this.document.createElement('br');
            $(emptyP).append(br);
            $(node.parentNode).before(emptyP).remove();
            range.sc = range.ec = br;
            range.so = range.eo = 0;
            return range.collapse(true);
        }
        return;
    },
    /**
     * Replace all leading space from a text node with one non-breakable space.
     *
     * @param {Node} node
     * @returns {Node} node
     */
    _replaceLeadingSpaceWithSingleNBSP: function (node) {
        var startSpace = this.context.invoke('HelperPlugin.getRegex', 'startSpace');
        node.textContent = node.textContent.replace(startSpace, '\u00A0');
        return node;
    },
    /**
     * Replace a media node with an empty SPAN and return that SPAN.
     *
     * @param {Node} media
     * @returns {Node} span
     */
    _replaceMediaWithEmptySpan: function (media) {
        var span = this.document.createElement('span');
        media = dom.ancestor(media, function (n) {
            return !n.parentNode || !dom.isMedia(n.parentNode);
        });
        $(media).replaceWith(span);
        return span;
    },
    /**
     * Move the (collapsed) range to get out of BR elements.
     *
     * @private
     * @param {Object} range
     * @returns {Object} range
     */
    _rerangeOutOfBR: function (range, direction) {
        range = this._rerangeToFirstNonBRElementLeaf(range);
        range = this._rerangeToNextNonBR(range, direction === 'next');
        return range;
    },
    /**
     * Move the (collapsed) range to the first leaf that is not a BR element.
     *
     * @private
     * @param {Object} range
     * @returns {Object} range
     */
    _rerangeToFirstNonBRElementLeaf: function (range) {
        var leaf = this.context.invoke('HelperPlugin.firstNonBRElementLeaf', range.sc);
        if (leaf !== range.sc) {
            range = this.context.invoke('editor.setRange', leaf, 0);
        }
        return range;            
    },
    /**
     * Move the (collapsed) range to the next (or previous) node that is not a BR element.
     *
     * @private
     * @param {Object} range
     * @param {Boolean} previous true to move to the previous node
     * @returns {Object} range
     */
    _rerangeToNextNonBR: function (range, previous) {
        var point = range.getStartPoint();
        var method = previous ? 'prevPointUntil' : 'nextPointUntil';
        point = dom[method](point, function (pt) {
            return pt.node.tagName !== 'BR';
        });
        range = this.context.invoke('editor.setRange', point.node, point.offset);
        return range;
    },
    /**
     * Move the (collapsed) range to the child of the node at the current offset if possible.
     *
     * @private
     * @param {Object} range
     * @param {String('prev'|'next')} direction
     * @returns {Object} range
     */
    _rerangeToOffsetChild: function (range, direction) {
        if (range.sc.childNodes[range.so]) {
            var node;
            var offset;
            if (direction === 'prev' && range.so > 0) {
                node = range.sc.childNodes[range.so - 1];
                offset = dom.nodeLength(node);
                range = this.context.invoke('editor.setRange', node, offset);
            } else {
                node = range.sc.childNodes[range.so];
                offset = 0;
                range = this.context.invoke('editor.setRange', node, offset);
            }
        }
        return range;
    },
    /**
     * Select all the contents of the current unbreakable ancestor.
     */
    _selectAll: function () {
        var self = this;
        var range = this.context.invoke('editor.createRange');
        var unbreakable = dom.ancestor(range.sc, this.options.isUnbreakableNode);
        var $contents = $(unbreakable).contents();
        var startNode = $contents.length ? $contents[0] : unbreakable;
        var pointA = this.context.invoke('HelperPlugin.makePoint', startNode, 0);
        pointA = dom.nextPointUntil(pointA, function (point) {
            return self.context.invoke('HelperPlugin.isVisibleText', point.node);
        }) || pointA;
        var endNode = $contents.length ? $contents[$contents.length - 1] : unbreakable;
        var endOffset = $contents.length ? dom.nodeLength($contents[$contents.length - 1]) : 1;
        var pointB = this.context.invoke('HelperPlugin.makePoint', endNode, endOffset);
        pointB = dom.prevPointUntil(pointB, function (point) {
            return self.context.invoke('HelperPlugin.isVisibleText', point.node);
        }) || pointB;
        range.sc = pointA.node;
        range.so = pointA.offset;
        range.ec = pointB.node;
        range.eo = pointB.offset;
        range.select().normalize();
    },
    /**
     * Before a deletion, if necessary, slice the text content at range, then rerange.
     *
     * @param {Object} range
     * @returns {Object} range
     */
    _sliceAndRerangeBeforeDeletion: function (range) {
        if (this._isAfterLeadingInvisibleChar(range) && !this._isAfterTwoBRs(range.sc)) {
            range.sc.textContent = range.sc.textContent.slice(1);
            range.so = 0;
        }
        if (this._isBeforeTrailingInvisibleChar(range) && !this._isAfterBR(range.sc)) {
            range.sc.textContent = range.sc.textContent.slice(0, range.so);
        }
        return range;
    },


    //--------------------------------------------------------------------------
    // Handle
    //--------------------------------------------------------------------------

    /** 
     * Customize handling of certain keydown events.
     *
     * @private
     * @param {SummernoteEvent} se
     * @param {jQueryEvent} e
     * @returns {Boolean} true if case handled
     */
    _onKeydown: function (se, e) {
        var self = this;
        var handled = false;

        if (e.ctrlKey && e.key === 'a') {
            e.preventDefault();
            this._selectAll();
            return;
        }

        if (e.key &&
            (e.key.length === 1 || e.key === "Dead" || e.key === "Unidentified") &&
            !e.ctrlKey && !e.altKey && !e.metaKey) {

            if (e.key === "Dead" || e.key === "Unidentified") {
                this._accented = true;
            }

            // Record undo only if either:
            clearTimeout(this.lastCharIsVisibleTime);
            // e.key is punctuation or space
            var stopChars = [' ', ',', ';', ':', '?', '.', '!'];
            if (stopChars.indexOf(e.key) !== -1) {
                this.lastCharVisible = false;
            }
            // or not on top of history stack (record undo after undo)
            var history = this.context.invoke('HistoryPlugin.getHistoryStep');
            if (history && history.stack.length && history.stackOffset < history.stack.length - 1) {
                this.lastCharVisible = false;
            }
            // or no new char for 500ms
            this.lastCharIsVisibleTime = setTimeout(function () {
                self.lastCharIsVisible = false;
            }, 500);
            if (!this.lastCharIsVisible) {
                this.lastCharIsVisible = true;
                this.context.invoke('HistoryPlugin.recordUndo');
            }

            if (e.key !== "Dead") {
                this._onVisibleChar(e, this._accented);
            }
        } else {
            this.lastCharIsVisible = false;
            this.context.invoke('editor.clearTarget');
            this.context.invoke('MediaPlugin.hidePopovers');
            this.context.invoke('editor.beforeCommand');
            switch (e.keyCode) {
                case 8: // BACKSPACE
                    handled = this._onBackspace(e);
                    break;
                case 9: // TAB
                    handled = this._onTab(e);
                    break;
                case 13: // ENTER
                    handled = this._onEnter(e);
                    break;
                case 46: // DELETE
                    handled = this._onDelete(e);
                    break;
            }
            if (handled) {
                this._preventTextInEditableDiv();
                this.context.invoke('editor.saveRange');
                e.preventDefault();
                this.context.invoke('editor.afterCommand');
            }
        }
        if (e.key !== "Dead") {
            this._accented = false;
        }
    },
    /**
     * Handle BACKSPACE keydown event.
     *
     * @private
     * @param {jQueryEvent} e
     * @returns {Boolean} true if case is handled and event default must be prevented
     */
    _onBackspace: function (e) {
        var range = this.context.invoke('editor.createRange');
        var needOutdent = false;

        // Special cases
        if (range.isCollapsed()) {

            // Do nothing if on left edge of a table cell
            var point = range.getStartPoint();
            if (point.node.childNodes[point.offset]) {
                point.node = point.node.childNodes[point.offset];
                point.offset = dom.nodeLength(point.node);
            }
            if (this.context.invoke('HelperPlugin.isLeftEdgeOfTag', point, 'TD')) {
                return true;
            }

            // Outdent if on left edge of an indented block
            point = range.getStartPoint();
            var isIndented = !!dom.ancestor(point.node, function (n) {
                var style = dom.isCell(n) ? 'paddingLeft' : 'marginLeft';
                return n.tagName && !!parseFloat(n.style[style] || 0);
            });
            if (this.context.invoke('HelperPlugin.isLeftEdgeOfBlock', point)) {
                if (isIndented) {
                    this.context.invoke('BulletPlugin.outdent');
                    return true;
                }
                if (dom.ancestor(range.sc, dom.isLi)) {
                    needOutdent = true;
                }
            }
        }

        var flag = this._handleDeletion('prev');

        if (!flag && needOutdent) {
            range.select();
            this.context.invoke('BulletPlugin.outdent');
        }

        return true;
    },
    /**
     * Handle DELETE keydown event.
     *
     * @private
     * @param {jQueryEvent} e
     * @returns {Boolean} true if case is handled and event default must be prevented
     */
    _onDelete: function (e) {
        var range = this.context.invoke('editor.createRange');

        // Special case
        if (range.isCollapsed()) {
            // Do nothing if on left edge of a table cell
            if (this.context.invoke('HelperPlugin.isRightEdgeOfTag', range.getStartPoint(), 'TD')) {
                return true;
            }
        }

        this._handleDeletion('next');
        return true;
    },
    /**
     * Handle ENTER keydown event.
     *
     * @private
     * @param {jQueryEvent} e
     * @returns {Boolean} true if case is handled and event default must be prevented
     */
    _onEnter: function (e) {
        this.context.invoke('HelperPlugin.deleteSelection');
        if (e.shiftKey) {
            this._handleShiftEnter();
        } else if (e.ctrlKey) {
            this.context.invoke('TextPlugin.insertHR');
        } else {
            this._handleEnter();
        }
        return true;
    },
    /**
     * Handle TAB keydown event.
     *
     * @private
     * @param {jQueryEvent} e
     * @returns {Boolean} true if case is handled and event default must be prevented
     */
    _onTab: function (e) {
        // If TAB not handled, prevent default and do nothing
        if (!this.options.keyMap.pc.TAB) {
            this.trigger_up('wysiwyg_blur', {
                key: 'TAB',
                keyCode: 9,
                shiftKey: e.shiftKey,
            });
            return true;
        }
        var range = this.context.invoke('editor.createRange');
        var point = range.getStartPoint();
        var startSpace = this.context.invoke('HelperPlugin.getRegex', 'startSpace');

        if (!range.isOnCell()) {
            // If on left edge point: indent/outdent
            if (!point.node.tagName) { // Clean up start spaces on textNode
                point.node.textContent.replace(startSpace, function (startSpaces) {
                    point.offset = startSpaces.length === point.offset ? 0 : point.offset;
                    return '';
                });
            }
            if (this.context.invoke('HelperPlugin.isLeftEdgeOfBlock', point) || dom.isEmpty(point.node)) {
                if (e.shiftKey) {
                    this.context.invoke('BulletPlugin.outdent');
                } else {
                    this.context.invoke('BulletPlugin.indent');
                }
                this.context.invoke('HelperPlugin.normalize');
                return true;
            }
            // Otherwise insert a tab or do nothing
            if (!e.shiftKey) {
                this.context.invoke('TextPlugin.insertTab');
                this.context.invoke('HelperPlugin.normalize');
            }
            return true;
        }
        // In table, on tab switch to next cell
        return false;
    },
    /**
     * Handle visible char keydown event.
     *
     * @private
     * @param {jQueryEvent} e
     * @returns {Boolean} true if case is handled and event default must be prevented
     */
    _onVisibleChar: function (e, accented) {
        var self = this;
        e.preventDefault();
        if (accented) {
            this.editable.normalize();
            var baseRange = this.context.invoke('editor.createRange');

            var $parent = $(baseRange.sc.parentNode);
            var parentContenteditable = $parent.attr('contenteditable');
            $parent.attr('contenteditable', false);

            var accentPlaceholder = this.document.createElement('span');
            $(baseRange.sc).after(accentPlaceholder);
            $(accentPlaceholder).attr('contenteditable', true);

            var range = this.context.invoke('editor.setRange', accentPlaceholder, 0);
            range.select();

            setTimeout(function () {
                var accentedChar = accentPlaceholder.innerHTML;
                $(accentPlaceholder).remove();
                if (parentContenteditable) {
                    $parent.attr('contenteditable', parentContenteditable);
                } else {
                    $parent.removeAttr('contenteditable');
                }
                baseRange.select();
                self.context.invoke('HelperPlugin.insertTextInline', accentedChar);
            });
        } else {
            this.context.invoke('HelperPlugin.insertTextInline', e.key);
        }
        return true;
    },
});

registry.add('KeyboardPlugin', KeyboardPlugin);

return KeyboardPlugin;
});
