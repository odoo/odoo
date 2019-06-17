odoo.define('web_editor.wysiwyg.plugin.helper', function (require) {
'use strict';

var AbstractPlugin = require('web_editor.wysiwyg.plugin.abstract');
var Dialog = require('web.Dialog');
var registry = require('web_editor.wysiwyg.plugin.registry');

var dom = $.summernote.dom;


var HelperPlugin = AbstractPlugin.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This dictionary contains oft-used regular expressions,
     * for performance and readability purposes. It can be
     * accessed and extended by the getRegex() method.
     */
    regex: {
        char: {
            noflag: /\S|\u00A0|\u200B/,
        },
        emptyElemWithBR: {
            noflag: /^\s*<br\/?>\s*$/,
        },
        endInvisible: {
            noflag: /\u200B$/,
        },
        endNotChar: {
            noflag: /[^\S\u00A0\u200B]+$/,
        },
        endSingleSpace: {
            noflag: /[\S\u00A0\u200B]\s$/,
        },
        endSpace: {
            noflag: /\s+$/,
        },
        invisible: {
            noflag: /\u200B/,
        },
        jinja: {
            noflag: /(^|\n)\s*%\send|%\sset/,
        },
        notWhitespace: {
            noflag: /\S/,
        },
        onlyEmptySpace: {
            noflag: /^[\s\u00A0\u200B]*(<br>)?[\s\u00A0\u200B]*$/,
        },
        semicolon: {
            noflag: / ?; ?/,
        },
        space: {
            noflag: /\s+/,
            g: /\s+/g,
        },
        spaceOrNewline: {
            noflag: /[\s\n\r]+/,
            g: /[\s\n\r]+/g,
        },
        startAndEndInvisible: {
            noflag: /^\u200B|\u200B$/,
            g: /^\u200B|\u200B$/g,
        },
        startAndEndSpace: {
            noflag: /^\s+|\s+$/,
            g: /^\s+|\s+$/g,
        },
        startAndEndSemicolon: {
            noflag: /^ ?;? ?| ?;? ?$/,
        },
        startInvisible: {
            noflag: /^\u200B/,
        },
        startNotChar: {
            noflag: /^[^\S\u00A0\u200B]+/,
        },
        startSingleSpace: {
            noflag: /^\s[\S\u00A0\u200B]/,
        },
        startSpace: {
            noflag: /^\s+/,
        },
    },

    /**
     * Compares two nodes to see if they are similar.
     * "Similar" means that they have the same tag, styles, classes and attributes.
     *
     * @param {Node} node
     * @param {Node} otherNode
     * @returns {Boolean} true if the nodes are similar
     */
    compareNodes: function (node, otherNode) {
        if (!otherNode || !node) {
            return false;
        }
        if (node.tagName !== otherNode.tagName) {
            return false;
        }
        if (dom.isText(node)) {
            return true;
        }
        this.removeBlankAttrs(node);
        this.removeBlankAttrs(otherNode);
        this.orderClass(node);
        this.orderStyle(node);
        this.orderClass(otherNode);
        this.orderStyle(otherNode);
        var nodeAttributes = this._getAttrsNoID(node);
        var otherNodeAttributes = this._getAttrsNoID(otherNode);
        if (nodeAttributes.length !== otherNodeAttributes.length) {
            return false;
        }
        for (var i = 0; i < nodeAttributes.length; i++) {
            var attr = nodeAttributes[i];
            var otherAttr = otherNodeAttributes[i];
            if (attr.name !== otherAttr.name || attr.value !== otherAttr.value) {
                return false;
            }
        }
        return true;
    },
    /**
     * Returns the number of leading breakable space in the textNode.
     * Note: returns 0 if the node is not a textNode.
     *
     * @param {Node} node
     */
    countLeadingBreakableSpace: function (node) {
        if (!dom.isText(node)) {
            return 0;
        }
        var clone = $(node).clone()[0];
        var breakableSpace = this.removeExtremeBreakableSpace(clone, 0).start;
        return breakableSpace === 1 ? 0 : breakableSpace;
    },
    /**
     * Returns the number of trailing breakable space in the textNode.
     * Note: returns 0 if the node is not a textNode.
     *
     * @param {Node} node
     */
    countTrailingBreakableSpace: function (node) {
        if (!dom.isText(node)) {
            return 0;
        }
        var clone = $(node).clone()[0];
        var breakableSpace = this.removeExtremeBreakableSpace(clone, 0).end;
        return breakableSpace === 1 ? 0 : breakableSpace;
    },
    /**
     * Remove the dom between 2 points (respecting unbreakable rules).
     * Returns an object::
     *
     *     {
     *         node: pointA.node (updated if necessary),
     *         offset: pointA.offset (updated if necessary),
     *         changed: bool (whether changes were applied)
     *     }
     * 
     * @param {Object} pointA
     * @param {Node} pointA.node
     * @param {number} pointA.offset
     * @param {Object} pointB
     * @param {Node} pointB.node
     * @param {number} pointB.offset
     * @returns {Object} {node, offset, changed}
     */
    deleteBetween: function (pointA, pointB) {
        var self = this;
        if (pointB.node.childNodes[pointB.offset]) {
            var firstLeaf = this.firstLeaf(pointB.node.childNodes[pointB.offset]);
            pointB = this.makePoint(firstLeaf, 0);
        }
        if (pointB.node.tagName && pointB.node.tagName !== 'BR' && pointB.offset >= dom.nodeLength(pointB.node)) {
            pointB = dom.nextPoint(pointB);
        }
        var changed;
        var commonAncestor = dom.commonAncestor(pointA.node, pointB.node);

        var ecAncestor = dom.ancestor(pointB.node, function (node) {
            return node === commonAncestor || self.options.isUnbreakableNode(node.parentNode);
        });
        var next = this.splitTree(ecAncestor, pointB, {
            nextText: true,
        });

        var scAncestor = dom.ancestor(pointA.node, function (node) {
            return node === commonAncestor || self.options.isUnbreakableNode(node.parentNode);
        });
        if (dom.isIcon(pointA.node)) {
            pointA = dom.prevPoint(pointA);
        }
        this.splitTree(scAncestor, pointA, {
            nextText: true,
        });
        pointA.offset = dom.nodeLength(pointA.node);

        var nodes = [];
        dom.nextPointUntil(pointA, function (point) {
            if (point.node === next || !point.node) {
                return true;
            }
            if (dom.isText(point.node) && point.offset) {
                return;
            }
            var target = point.node.childNodes[point.offset] || point.node;
            if (target === pointA.node || $.contains(target, pointA.node) || target === next || $.contains(target, next)) {
                return;
            }
            if (
                nodes.indexOf(target) === -1 && !dom.ancestor(target, function (target) {
                    return nodes.indexOf(target) !== -1;
                })
            ) {
                nodes.push(target);
            }
        });
        $(nodes).remove();

        changed = !!nodes.length;
        var toMerge = changed && pointA.node.parentNode !== next.parentNode;


        var point = this.makePoint(this.firstLeaf(next), 0);
        if (nodes.length > 1 || nodes.length && !dom.isText(nodes[0])) {
            point = this.removeEmptyInlineNodes(point);
        }

        // Remove whole li/ul/ol if deleted all contents of li/ul/ol
        var ul = dom.ancestor(next, function (n) {
            return n.tagName === 'UL' || n.tagName === 'OL';
        });
        if (ul && next[dom.isText(next) ? 'textContent' : 'innerHTML'] === '' && pointA.node !== next.previousSibling) {
            var toRemove = next;
            while (
                toRemove !== ul && toRemove.parentNode &&
                !this.options.isUnbreakableNode(toRemove.parentNode) &&
                this.isBlankNode(toRemove.parentNode)
            ) {
                toRemove = toRemove.parentNode;
            }
            $(toRemove).remove();
        }
        if (!$.contains(this.editable, pointA.node)) {
            pointA = point;
        }

        if (toMerge) {
            pointA = this.deleteEdge(pointA.node, 'next') || pointA;
        }

        return {
            node: pointA.node,
            offset: pointA.offset,
            changed: changed,
        };
    },
    /**
     * Remove the edge between a node and its sibling
     * (= merge the nodes, respecting unbreakable rules).
     *
     * @param {Node} node
     * @param {String('next'|'prev')} direction
     * @param {Boolean} doNotTryNonSim true to not try merging non-similar nodes
     * @returns {Object} {node, offset}
     */
    deleteEdge: function (node, direction, doNotTryNonSim) {
        var prevOrNext = direction === 'prev' ? 'previousSibling' : 'nextSibling';
        var result = false;
        var startN = node;

        if (node.tagName === 'BR' && node.nextSibling && !(dom.isText(node.nextSibling) && !this.isVisibleText(node.nextSibling))) {
            node = node.nextSibling;
            node = this.firstLeaf(node);
        }

        var nodes = [];
        var next;
        while (node && node !== this.editable && !this.options.isUnbreakableNode(node)) {
            nodes.push(node);

            next = node[prevOrNext];
            while (next && !next.tagName) {
                if (!this.getRegex('char').test(next.textContent)) {
                    next = next[prevOrNext];
                    continue;
                }
                break;
            }

            if (next) {
                break;
            }
            node = node.parentNode;
        }

        if (next && next.tagName === 'TABLE') {
            return this.makePoint(node, 0);
        }

        var ifBrRemovedAndMerge = !_.filter(nodes, this.isNodeBlockType.bind(this)).length;
        var brRemoved = false;

        var range = this.context.invoke('editor.createRange');

        var spaceToRemove = [];
        var offset;
        while ((node = nodes.pop())) {
            next = node[prevOrNext];
            while (next && !next.tagName) {
                if (!this.getRegex('char').test(next.textContent)) {
                    spaceToRemove.push(next);
                    next = next[prevOrNext];
                    continue;
                }
                break;
            }

            // handle merge of text with p (useful in case of <li>text</li> with <li><p>text</p></li>)
            if (next && dom.isText(node) && this.isNodeBlockType(next)) {
                node = [next, next = node][0]; // swap node and next
                direction = direction === 'next' ? 'prev' : 'next'; // switch direction
            }
            if (next && dom.isText(next) && this.isNodeBlockType(node)) {
                if (this.isBlankNode(node, true)) {
                    $(node).empty();
                }
                $(node)[direction === 'next' ? 'append' : 'prepend'](next);
                offset = direction === 'next' ? 0 : dom.nodeLength(next);
                if (dom.isText(next[prevOrNext])) {
                    // merge text if needed
                    var sib = next[prevOrNext];
                    var firstText = (direction === 'next' ? sib : next).textContent;
                    var secondText = (direction === 'next' ? next : sib).textContent;
                    next.textContent = firstText + secondText;
                    $(sib).remove();
                    offset = firstText.length;
                }
                result = this.makePoint(next, offset);
                break;
            }

            if (
                !next ||
                !(node.tagName || next.tagName === 'BR') ||
                !next.tagName
            ) {
                continue;
            }

            if (!brRemoved && next.tagName === 'BR' && (!next[prevOrNext] || this.compareNodes(node, next[prevOrNext]))) {
                var newNext = next[prevOrNext];
                $(next).remove();
                next = newNext;
                offset = (next ? direction === 'prev' : direction === 'next') ? dom.nodeLength(next) : 0;
                result = this.makePoint(next || node, offset);
                if (!ifBrRemovedAndMerge) {
                    continue;
                }
                brRemoved = true;
                ifBrRemovedAndMerge = false;
            }

            if (!this.compareNodes(node, next)) {
                continue;
            }
            _.each(spaceToRemove, function (space) {
                $(space).remove();
            });
            spaceToRemove = [];
            next = node[prevOrNext];
            var $next = $(next);
            if (next.tagName) {
                var textNode;
                var nextTextNode;
                var deep;
                if (direction === 'prev') {
                    textNode = this.firstLeaf(node);
                    if (!textNode.tagName && !dom.ancestor(textNode, dom.isPre)) {
                        this.removeExtremeBreakableSpace(textNode);
                        range.so = range.eo = 0;
                        nextTextNode = this.lastLeaf(next);
                        if (!nextTextNode.tagName && !dom.ancestor(nextTextNode, dom.isPre)) {
                            this.removeExtremeBreakableSpace(nextTextNode);
                        }
                    }
                    deep = this.lastLeaf(next);
                    result = this.makePoint(deep, dom.nodeLength(deep));
                    if (
                        this.getRegex('char').test(node.textContent) || node.childElementCount > 1 ||
                        node.firstElementChild && node.firstElementChild.tagName !== "BR"
                    ) {
                        $next.append($(node).contents());
                    }
                    $(node).remove();
                } else {
                    nextTextNode = this.firstLeaf(next);
                    if (!nextTextNode.tagName && !dom.ancestor(nextTextNode, dom.isPre)) {
                        this.removeExtremeBreakableSpace(nextTextNode);
                        textNode = this.lastLeaf(node);
                        if (!textNode.tagName && !dom.ancestor(textNode, dom.isPre)) {
                            this.removeExtremeBreakableSpace(textNode);
                            range.so = range.eo = dom.nodeLength(node);
                        }
                    }
                    if (node.innerHTML.trim() === '<br>') {
                        $(node).contents().remove();
                    }
                    deep = this.lastLeaf(node);
                    result = this.makePoint(deep, dom.nodeLength(deep));
                    $(node).append($next.contents());
                    $next.remove();
                }
                continue;
            } else if (!this.getRegex('char').test(next.textContent)) {
                result = this.makePoint(node, direction === 'prev' ? 0 : dom.nodeLength(node));
                $next.remove();
                continue;
            }

            break;
        }

        if (!result && startN && !doNotTryNonSim) {
            result = this.deleteNonSimilarEdge(startN, direction);
        }

        return result;
    },
    /**
     * Find and delete the previous/next non-similar edge if possible.
     * "Similar" means that they have the same tag, styles, classes and attributes.
     *
     * @param {Node} node
     * @param {String} direction 'prev' or 'next'
     * @returns {false|Object} {node, offset}
     */
    deleteNonSimilarEdge: function (node, direction) {
        var next = node[direction === 'next' ? 'nextSibling' : 'previousSibling'];
        while (
            next && dom.isText(next) &&
            this.getRegexBlank({
                space: true,
                invisible: true,
            }).test(next.textContent)
        ) {
            next = next[direction === 'next' ? 'nextSibling' : 'previousSibling'];
        }

        if (next) {
            return;
        }

        node = this.firstBlockAncestor(node);

        if (this.options.isUnbreakableNode(node)) {
            return;
        }

        var point = this.makePoint(node, direction === 'prev' ? 0 : dom.nodeLength(node));
        var otherBlock = this.findNextBlockToMerge(point.node, direction);

        if (!otherBlock) {
            return;
        }

        var blockToMergeFrom = direction === 'next' ? otherBlock : point.node;
        var blockToMergeInto = direction === 'next' ? point.node : otherBlock;

        // empty tag are removed
        if (
            this.getRegexBlank({
                space: true,
                newline: true,
            }).test(blockToMergeInto.textContent) &&
            !$(blockToMergeInto).find('.fa').length && $(blockToMergeInto).find('br').length <= 1
        ) {
            $(blockToMergeInto).remove();
            return this.makePoint(this.firstLeaf(blockToMergeFrom), 0);
        }

        // UL/OL can only have LI, UL or OR as direct children
        if (dom.isList(blockToMergeInto) && !dom.isLi(blockToMergeFrom) && !dom.isList(blockToMergeFrom)) {
            return;
        }

        return this.mergeNonSimilarBlocks(blockToMergeFrom, blockToMergeInto);
    },
    /**
     * Deletes the contents of the selected DOM.
     *
     * @returns {Boolean} true if there was a selection to delete
     */
    deleteSelection: function () {
        var range = this.context.invoke('editor.createRange');
        if (range.isCollapsed()) {
            return false;
        }
        var point = this.deleteBetween(range.getStartPoint(), range.getEndPoint());
        point = this.fillEmptyNode(point);

        range = this.context.invoke('editor.setRange', point.node, point.offset);
        range = range.select();

        this.editable.normalize();
        this.context.invoke('editor.saveRange');

        // remove tooltip when remove DOM nodes
        $('body > .tooltip').tooltip('hide');

        return true;
    },
    /**
     * Fill up an empty node so as to allow the carret to go inside it.
     * A block node will be filled with a <br>, with the offset before it.
     * An inline node will be filled with two zero-width spaces, with the offset in between the two.
     * Returns the given point (with the completed node and the updated offset).
     *
     * @param {Object} point {node, offset}
     * @returns {Object} {node, offset}
     */
    fillEmptyNode: function (point) {
        if (
            !point.node.tagName && this.getRegexBlank({
                space: true,
                invisible: true,
                nbsp: true,
            }).test(point.node.parentNode.innerHTML)
        ) {
            point.node = point.node.parentNode;
            point.offset = 0;
        }
        if (
            point.node.tagName && point.node.tagName !== 'BR' &&
            this.getRegexBlank({
                space: true,
                invisible: true,
                nbsp: true,
            }).test(point.node.innerHTML)
        ) {
            var text = this.document.createTextNode('');
            point.node.innerHTML = '';
            point.node.appendChild(text);
            point.node = text;
            point.offset = 0;
        }
        if (point.node.parentNode.innerHTML === '') {
            if (this.isNodeBlockType(point.node.parentNode)) {
                var node = point.node.parentNode;
                node.innerHTML = '<br/>';
                point.node = node.firstChild;
                point.offset = 0;
            } else {
                point.node.textContent = '\u200B\u200B';
                point.offset = 1;
            }
        }
        return point;
    },
    /**
     * Get the "format" ancestors list of nodes.
     * In this context, a "format" node is understood as
     * an editable block or an editable element expecting text
     * (eg.: p, h1, span).
     *
     * @param {Node[]} nodes
     * @returns {Node[]}
     */
    filterFormatAncestors: function (nodes) {
        var self = this;
        var selectedNodes = [];
        _.each(this.filterLeafChildren(nodes), function (node) {
            var ancestor = dom.ancestor(node, function (node) {
                return dom.isCell(node) || (
                    !self.options.isUnbreakableNode(node) &&
                    (self.isFormatNode(node) || self.isNodeBlockType(node))
                ) && self.editable !== node;
            });
            if (!ancestor) {
                ancestor = node;
            }
            if (dom.isCell(ancestor)) {
                ancestor = node;
            }
            if (ancestor && selectedNodes.indexOf(ancestor) === -1) {
                selectedNodes.push(ancestor);
            }
        });
        return selectedNodes;
    },
    /**
     * Get the "leaf" children of a list of nodes.
     * In this context, a "leaf" is understood as
     * either a text node or a node that doesn't expect text contents.
     *
     * @param {Node[]} nodes
     * @returns {Node[]}
     */
    filterLeafChildren: function (nodes) {
        var self = this;
        return _.compact(_.map(nodes, function (node) {
            if (node.firstChild) {
                node = node.firstChild;
            }
            if (
                node.tagName === "BR" ||
                self.isVisibleText(node) ||
                dom.isFont(node) ||
                dom.isImg(node) ||
                dom.isDocument(node)
            ) {
                return node;
            }
        }));
    },
    /**
     * Find the previous/next non-similar block to merge with.
     * "Similar" means that they have the same tag, styles, classes and attributes.
     *
     * @param {Node} node
     * @param {String} direction 'prev' or 'next
     * @returns {false|Node}
     */
    findNextBlockToMerge: function (node, direction) {
        var self = this;
        var startNode = node;
        var mergeableTags = this.options.styleTags.join(', ') + ', li';
        var blockToMerge = false;

        var li = dom.ancestor(node, function (n) {
            return n !== node && self.isNodeBlockType(n) || dom.isLi(n);
        });
        var nextElementSibling = direction === 'next' ? 'nextElementSibling' : 'previousElementSibling';
        li = li && dom.isLi(li) ? li : undefined;
        if (li) {
            if (li[nextElementSibling]) {
                node = li;
            } else {
                node = dom.ancestor(node, function (n) {
                    return ((n.tagName === 'UL' || n.tagName === 'OL') && n[nextElementSibling] &&
                        (direction === 'next' || dom.isList(n[nextElementSibling])));
                });
            }
        }

        if (!node || !node[nextElementSibling]) {
            return false;
        }

        node = node[nextElementSibling];

        var ulFoldedSnippetNode = dom.ancestor(node, function (n) {
            return $(n).hasClass('o_ul_folded');
        });
        var ulFoldedSnippetStartNode = dom.ancestor(startNode, function (n) {
            return $(n).hasClass('o_ul_folded');
        });
        if (
            (this.options.isUnbreakableNode(node) && (!ulFoldedSnippetNode || ulFoldedSnippetNode === this.editable)) &&
            this.options.isUnbreakableNode(startNode) && (!ulFoldedSnippetStartNode || ulFoldedSnippetStartNode === this.editable)
        ) {
            return false;
        }

        node = this.firstBlockAncestor(node);

        li = dom.isList(node) ? undefined : dom.ancestor(node, function (n) {
            return n !== node && self.isNodeBlockType(n) || dom.isLi(n);
        });
        li = li && dom.isLi(li) ? li : undefined;
        node = li || node;

        if (node.tagName === 'UL' || node.tagName === 'OL') {
            node = node[direction === 'next' ? 'firstElementChild' : 'lastElementChild'];
        }

        if (this.options.isUnbreakableNode(node)) {
            return false;
        }

        if (node === startNode || $(node).has(startNode).length || $(startNode).has(node).length) {
            return false;
        }

        var $mergeable = $(node).find('*').addBack()
            .filter(mergeableTags)
            .filter(function (i, n) {
                if (!(n.tagName === 'LI' && $(n).find(mergeableTags).length)) {
                    return n;
                }
            });
        if ($mergeable.length) {
            blockToMerge = $mergeable[direction === 'next' ? 'first' : 'last']()[0] || false;
        }

        return blockToMerge;
    },
    /**
     * Get the first ancestor of a node, that is of block type (or itself).
     *
     * @param {Node} node
     * @returns {Node}
     */
    firstBlockAncestor: function (node) {
        var self = this;
        return dom.ancestor(node, function (n) {
            return self.isNodeBlockType(n);
        });
    },
    /**
     * Get the first leaf of a node, that is editable and not a media.
     * In this context, a leaf node is understood as a childless node.
     *
     * @param {Node} node
     * @returns {Node}
     */
    firstLeaf: function (node) {
        while (node.firstChild && !dom.isMedia(node) && this.options.isEditableNode(node)) {
            node = node.firstChild;
        }
        return node;
    },
    /**
     * Get the first leaf of a node, that is an element and not a BR.
     * In this context, a leaf node is understood as a childless node.
     *
     * @param {Node} node
     * @returns {Node} node
     */
    firstNonBRElementLeaf: function (node) {
        while (node.firstElementChild && node.firstElementChild.tagName !== 'BR') {
            node = node.firstElementChild;
        }
        return node;
    },
    /**
     * Returns the node targeted by a path
     *
     * @param {Object[]} path list of object (tagName, offset)
     * @returns {Node}
     */
    fromPath: function (path) {
        var node = this.editable;
        var to;
        path = path.slice();
        while ((to = path.shift())) {
            node = _.filter(node.childNodes, function (node) {
                return !to.tagName && node.tagName === 'BR' || node.tagName === to.tagName;
            })[to.offset];
        }
        return node;
    },
    /**
     * Returns (and creates if necessary) a regular expression.
     * If a regular expression with the given name exists, simply returns it.
     * Otherwise, creates a new one with the given name, exp and flag.
     *
     * @param {String} name
     * @param {String} [flag] optional
     * @param {String} [exp] optional
     * @returns {RegExp}
     */
    getRegex: function (name, flag, exp) {
        var flagName = flag || 'noflag';
        flag = flag || '';
        // If the regular expression exists, but not with this flag:
        // retrieve whichever version of it and apply the new flag to it,
        // then save that new version in the `regex` object.
        if (this.regex[name] && !this.regex[name][flagName]) {
            if (exp) {
                console.warn("A regular expression already exists with the name: " + name + ". The expression passed will be ignored.");
            }
            var firstVal = this.regex[name][Object.keys(this.regex[name])[0]];
            this.regex[name][flagName] = new RegExp(firstVal, flag);
        } else if (!this.regex[name]) {
            // If the regular expression does not exist:
            // save it into the `regex` object, with the name, expression
            // and flag passed as arguments (if any).
            if (!exp) {
                throw new Error("Cannot find a regular expression with the name " + name + ". Pass an expression to create it.");
            }
            this.regex[name] = {};
            this.regex[name][flagName] = new RegExp(exp, flag);
        }
        return this.regex[name][flagName];
    },
    /**
     * Returns (and creates if necessary) a regular expression
     * targetting a string made ONLY of some combination of the
     * characters enabled with options.
     * If a regular expression with the given options exists, simply returns it.
     * eg: getRegexBlank({space: true, nbsp: true}) => /^[\s\u00A0]*$/
     *
     * @param {Object} [options] optional
     * @param {Boolean} options.not ^ (not all that follows)
     * @param {Boolean} options.space \s (a whitespace)
     * @param {Boolean} options.notspace \S (not a whitespace)
     * @param {Boolean} options.nbsp \u00A0 (a non-breakable space)
     * @param {Boolean} options.invisible \u200B (a zero-width character)
     * @param {Boolean} options.newline \n|\r (a new line or a carriage return)
     * @param {Boolean} options.atLeastOne + (do not target blank strings)
     * @returns {RegExp}
     */
    getRegexBlank: function (options) {
        options = options || {};
        var charMap = {
            notspace: {
                name: 'NotSpace',
                exp: '\\S',
            },
            space: {
                name: 'Space',
                exp: '\\s',
            },
            nbsp: {
                name: 'Nbsp',
                exp: '\\u00A0',
            },
            invisible: {
                name: 'Invisible',
                exp: '\\u200B',
            },
            newline: {
                name: 'Newline', 
                exp: '\\n\\r',
            },
        };
        var name = 'only';
        var exp = '';
        var atLeastOne = options.atLeastOne;
        options.atLeastOne = false;

        // Build the expression and its name
        if (options.not) {
            name += 'Not';
            exp += '^';
            options.not = false;
        }
        _.each(options, function (value, key) {
            if (value && charMap[key]) {
                name += charMap[key].name;
                exp += charMap[key].exp;
            }
        });

        exp = '^[' + exp + ']' + (atLeastOne ? '+' : '*') + '$';
        name += atLeastOne ? 'One' : '';
        return this.getRegex(name, undefined, exp);
    },
    /**
     * Returns a list of all selected nodes in the range.
     *
     * @returns {Node []}
     */
    getSelectedNodes: function () {
        var range = this.context.invoke('editor.createRange');
        if (!range.isCollapsed()) {
            if (range.so && !range.sc.tagName) {
                if (range.sc === range.ec) {
                    range.sc = range.ec = range.sc.splitText(range.so);
                    range.eo -= range.so;
                } else {
                    range.sc = range.sc.splitText(range.so);
                }
                range.so = 0;
            }
            if (!range.ec.tagName && range.eo !== dom.nodeLength(range.ec) && !range.ec.tagName) {
                range.ec.splitText(range.eo);
            }
            range.select();
        }
        var res = [range.sc];
        var point = range.getStartPoint();
        var prevNode = range.sc;
        dom.nextPointUntil(point, function (pt) {
            if (pt.node !== prevNode) {
                var ok = true;
                // Return only the smallest traversed children
                _.each(res, function (n, i) {
                    // If pt.node is a child of res[i], replace it
                    if (dom.listAncestor(pt.node).indexOf(n) !== -1) {
                        res[i] = pt.node;
                        ok = false;
                    } else if (dom.listAncestor(n).indexOf(pt.node) !== -1) {
                        // Inversely, skip parents of res[i]
                        ok = false;
                    }
                });
                if (ok) {
                    res.push(pt.node);
                }
            }
            prevNode = pt.node;
            return pt.node === range.ec;
        });
        return _.uniq(res);
    },
    /**
     * Returns a list of all selected text nodes in the range.
     *
     * @returns {Node []}
     */
    getSelectedText: function () {
        var self = this;
        var selectedText = _.filter(this.getSelectedNodes(), function (node) {
            node = self.firstLeaf(node);
            return self.isVisibleText(node);
        });
        return _.uniq(selectedText);
    },
    /**
     * Returns true if the value contains jinja logic.
     *
     * @returns {Boolean}
     */
    hasJinja: function (value) {
        return this.getRegex('jinja').test(value);
    },
    /**
     * Inserts a block node (respecting the rules of unbreakable nodes).
     * In order to insert the node, the DOM tree is split at the carret position.
     * If there is a selection, it is deleted first.
     *
     * @param {Node} node
     */
    insertBlockNode: function (node) {
        var self = this;
        var range = this.context.invoke('editor.createRange');
        range = range.deleteContents();
        var point = range.getStartPoint();
        var unbreakable = point.node;
        if (!this.options.isUnbreakableNode(point.node)) {
            unbreakable = dom.ancestor(point.node, function (node) {
                return self.options.isUnbreakableNode(node.parentNode) || node === self.editable;
            }) || point.node;
        }

        if (unbreakable === point.node && !point.offset && point.node.tagName !== 'P') {
            if (point.node.innerHTML === '<br>') {
                $(point.node.firstElementChild).remove();
            }
            if (point.node.tagName === "BR") {
                $(point.node).replaceWith(node);
            } else {
                point.node.append(node);
            }
            return;
        }
        if (!this.options.isUnbreakableNode(point.node)) {
            var tree = dom.splitTree(unbreakable, point, {
                isSkipPaddingBlankHTML: true,
                isNotSplitEdgePoint: true,
            });
            if ((!tree || $.contains(tree, range.sc)) && (point.offset || point.node.tagName)) {
                tree = tree || dom.ancestor(point.node, function (node) {
                    return self.options.isUnbreakableNode(node.parentNode);
                });
                $(tree).after(node);
            } else {
                $(tree).before(node);
            }
        } else {
            // prevent unwrapped text in unbreakable
            if (dom.isText(unbreakable)) {
                $(unbreakable).wrap(this.document.createElement('p'));
                unbreakable.splitText(point.offset);
                unbreakable = unbreakable.parentNode;
                point.offset = 1;
            }
            $(unbreakable.childNodes[point.offset]).before(node);
        }
        if (range.sc.innerHTML === '<br>') {
            var clone = range.sc.cloneNode(true);
            if (node.previousSibling === range.sc) {
                $(node).after(clone);
            } else if (node.nextSibling === range.sc) {
                $(node).before(clone);
            }
        }
    },
    /**
     * Inserts a string as a text node in the DOM.
     * If the range is on a text node, splits the text node first.
     * Otherwise just inserts the text node.
     * Wraps it in a P if needed.
     *
     * @param {String} text
     */
    insertTextInline: function (text) {
        if (text === " ") {
            text = "\u00A0";
        }
        this.editable.normalize();
        this.deleteSelection();

        var range = this.context.invoke('editor.createRange');


        if (!range.sc.tagName && range.sc.textContent.match(/\S/)) {
            var before = range.sc.textContent.slice(0, range.so);
            var after = range.sc.textContent.slice(range.so);

            if (
                (before.length || after.length) &&
                (!before.length || before[before.length - 1] === ' ') &&
                (!after.length || after[0] === ' ')
            ) {
                var startSpace = this.getRegex('startSpace');
                var endSpace = this.getRegex('endSpace');
                before = before.replace(endSpace, '\u00A0');
                after = after.replace(startSpace, '\u00A0');
                range.sc.textContent = before + after;
                if (range.so > before.length) {
                    range.so = range.eo = before.length;
                }
                range.select();
            }
        }


        range = range.deleteContents();
        range = this._standardizeRangeOnEdge(range);
        var textNode = this._insertTextNodeInEditableArea(range, text);

        // if the text node can't be inserted in the dom (not editable area) do nothing
        if (!textNode) {
            return;
        }

        this.secureExtremeSingleSpace(range.sc);

        this._wrapTextWithP(textNode);

        range = this.context.invoke('editor.setRange', textNode, text.length);
        range.select();
        this.context.invoke('editor.saveRange');

        // Clean up and make leading/trailing/multiple space visible
        this.normalize();
        range = this.context.invoke('editor.createRange');
        var reStartBlanks = this.getRegex('startBlanks', '', '^([\\s\\u00A0\\u200B]*)');
        var reEndBlanks = this.getRegex('endBlanks', '', '([\\s\\u00A0\\u200B]*)$');
        var reAllNBSP = /\u00A0/g;
        var reMultipleSpace = /(\s){2,}/;

        var textContent = range.sc.textContent;
        var startBlanks = range.sc.textContent.match(reStartBlanks)[0] || '';
        var endBlanks = range.sc.textContent.match(reEndBlanks)[0] || '';
        var trimmed = range.sc.textContent.replace(reStartBlanks, '').replace(reEndBlanks, '');
        // Remove the single inner nbsp's and replace the multiple inner spaces with nbsp's
        var cleanContents = trimmed.replace(reAllNBSP, ' ')
            .replace(reMultipleSpace, function (space) {
                return Array(space.length + 1).join('\u00A0');
            });
        // Keep the leading/trailing whitespace, nbsp's and zero-width chars
        range.sc.textContent = startBlanks + cleanContents + endBlanks;

        this._removeInvisibleChar(range);

        try {
            range.select();
        } catch (e) {
            /* Under certain unknown conditions, the range cannot be
            applied and triggered an error. In order to allow the user to
            keep editing, we need to prevent the dialog from showing, hence
            the use of `console.error`.
            If this error appears, the carret is moved to the beginning
            of the focused node.*/
            console.error(e);
            console.error('Informations for debugging', [
                ['textContent', textContent],
                ['trimmed', trimmed],
                ['cleanContents', cleanContents],
                ['start', range.sc.outerHTML || range.sc.textContent, range.so],
                ['end', range.ec.outerHTML || range.ec.textContent, range.eo],
                ['parent', range.sc.parentNode && range.sc.parentNode.outerHTML],
            ]);
        }
        this.context.invoke('editor.saveRange');
    },
    /**
     * Returns true if the node is a text node containing nothing
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    isBlankText: function (node) {
        return dom.isText(node) &&
            this.getRegexBlank({
                not: true,
                notspace: true,
                nbsp: true,
                invisible: true,
            })
            .test(node.textContent);
    },
    /**
     * Returns true if the node is blank.
     * In this context, a blank node is understood as
     * a node expecting text contents (or with children expecting text contents)
     * but without any.
     *
     * @param {Node} node
     * @param {Boolean} brIsBlank true to consider nodes with BR element
     *  as ultimate only child to be blank
     * @returns {Boolean}
     */
    isBlankNode: function (node, brIsBlank) {
        var self = this;
        if (brIsBlank && dom.isBR(node)) {
            return true;
        }
        if (dom.isVoid(node) || dom.isIcon(node)) {
            return false;
        }
        if (this.getRegexBlank({
                space: true,
            }).test(node[dom.isText(node) ? 'textContent' : 'innerHTML'])) {
            return true;
        }
        var areAllChildrenBlank = _.all(node.childNodes, function (node) {
            return self.isBlankNode(node, brIsBlank);
        });
        if (node.childNodes.length && areAllChildrenBlank) {
            return true;
        }
        return false;
    },
    /**
     * Returns true if the point is on the left/right edge of the first
     * previous/next point with the given tag name (skips insignificant nodes).
     *
     * @param {Object} point
     * @param {String} tagName
     * @param {String('left'|'right')} side
     * @returns {Boolean}
     */
    isEdgeOfTag: function (point, tagName, side) {
        var method = side === 'left' ? 'isLeftEdgePoint' : 'isRightEdgePoint';
        var prevOrNext = side === 'left' ? 'prev' : 'next';
        var newPt;
        var first = true;
        while (point && point.node.tagName !== tagName) {
            newPt = this.skipNodes(point, prevOrNext, function (pt) {
                return pt.node.tagName === tagName && dom[method](pt);
            });
            if (newPt.node.tagName === tagName || newPt.node.tagName === 'BR') {
                point = newPt;
                break;
            }
            if (newPt === point && (!first || dom.isText(point.node) && !dom[method](point))) {
                break;
            }
            point = dom[prevOrNext + 'Point'](newPt);
            first = false;
        }
        if (!point) {
            return false;
        }
        var ancestor = dom.ancestor(point.node, function (n) {
            return n.tagName === tagName;
        });
        return !!(ancestor && dom[method + 'Of'](point, ancestor));
    },
    /**
     * Returns true if the node is a "format" node.
     * In this context, a "format" node is understood as
     * an editable block or an editable element expecting text
     * (eg.: p, h1, span).
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    isFormatNode: function (node) {
        return node.tagName && this.options.styleTags.indexOf(node.tagName.toLowerCase()) !== -1;
    },
    /**
     * Returns true if the node is within a table.
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    isInTable: function (node) {
        return !!dom.ancestor(node, function (n) {
            return n.tagName === 'TABLE';
        });
    },
    /**
     * Returns true if the point is on the left edge of a block node
     * (skips insignificant nodes).
     *
     * @param {Object} point
     * @returns {Boolean}
     */
    isLeftEdgeOfBlock: function (point) {
        point = this.skipNodes(point, 'prev');
        return dom.isLeftEdgePointOf(point, this.firstBlockAncestor(point.node));
    },
    /**
     * Returns true if the point is on the left edge of the first
     * previous point with the given tag name (skips insignificant nodes).
     *
     * @param {Object} point
     * @param {String} tagName
     * @returns {Boolean}
     */
    isLeftEdgeOfTag: function (point, tagName) {
        return this.isEdgeOfTag(point, tagName, 'left');
    },
    /**
     * Returns true if the node is a block.
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    isNodeBlockType: function (node) {
        if (dom.isText(node)) {
            return false;
        }
        var display = this.window.getComputedStyle(node).display;
        // All inline elements have the word 'inline' in their display value, except 'contents'
        return display.indexOf('inline') === -1 && display !== 'contents';
    },
    /**
     * Returns true if the point is on the right edge of the first
     * next point with the given tag name (skips insignificant nodes).
     *
     * @param {Object} point
     * @param {String} tagName
     * @returns {Boolean}
     */
    isRightEdgeOfTag: function (point, tagName) {
        return this.isEdgeOfTag(point, tagName, 'right');
    },
    /**
     * Returns true if point should be ignored.
     * This is generally used for trying to figure out if the point is an edge point.
     *
     * @param {Object} point
     * @param {String} direction ('prev' or 'next')
     * @param {Object} options
     * @param {Boolean} options.noSkipBlankText true to not skip blank text
     * @param {Boolean} options.noSkipSingleBRs true to not skip single BRs
     * @param {Boolean} options.noSkipExtremeBreakableSpace true to not skip leading/trailing breakable space
     * @param {Boolean} options.noSkipParent true to not skip to leaf nodes or offset 0
     * @param {Boolean} options.noSkipSibling true to not skip if on edge and sibling is skippable
     * @returns {Boolean}
     */
    isSkippable: function (point, direction, options) {
        options = options || {};
        var isEdge = direction === 'prev' ? dom.isLeftEdgePoint(point) : dom.isRightEdgePoint(point);

        // skip blank text nodes
        if (
            !options.noSkipBlankText &&
            this.isBlankText(point.node)
        ) {
            return true;
        }
        // skip single BRs
        if (
            !options.noSkipSingleBRs &&
            point.node.tagName === 'BR' &&
            (!point.node.previousSibling || this.isBlankText(point.node.previousSibling)) &&
            (!point.node.nextSibling || this.isBlankText(point.node.nextSibling))
        ) {
            return true;
        }
        // skip leading/trailing breakable space
        if (
            !options.noSkipExtremeBreakableSpace &&
            (direction === 'prev' && !isEdge && point.offset <= this.countLeadingBreakableSpace(point.node) ||
                direction === 'next' && point.offset > dom.nodeLength(point.node) - this.countTrailingBreakableSpace(point.node))
        ) {
            return true;
        }
        // skip to leaf node or edge
        var node = direction === 'prev' ? point.node.childNodes[0] : point.node.childNodes[point.node.childNodes.length - 1];
        var offset = direction === 'prev' ? 0 : dom.nodeLength(node);
        if (
            !options.noSkipParent &&
            !isEdge && point.node.childNodes.length &&
            this.isSkippable(this.makePoint(node, offset), direction, options)
        ) {
            return true;
        }
        // skip if on edge and sibling is skippable
        var sibling = direction === 'prev' ? point.node.previousSibling : point.node.nextSibling;
        offset = direction === 'prev' ? 0 : dom.nodeLength(sibling);
        if (
            !options.noSkipSibling &&
            isEdge && sibling &&
            this.isSkippable(this.makePoint(sibling, offset), direction, _.defaults({
                noSkipSibling: true,
            }, options))
        ) {
            return true;
        }
        return false;
    },
    /**
     * Returns true if the node is a text node with visible text.
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    isVisibleText: function (node) {
        return !node.tagName && this.getRegex('char').test(node.textContent);
    },
    /**
     * Get the last leaf of a node, that is editable and not a media.
     * In this context, a leaf node is understood as a childless node.
     *
     * @param {Node} node
     * @returns {Node}
     */
    lastLeaf: function (node) {
        while (node.lastChild && !dom.isMedia(node) && this.options.isEditableNode(node)) {
            node = node.lastChild;
        }
        return node;
    },
    /**
     * Returns a Point object from a node and an offset.
     *
     * @param {Node} node
     * @param {Number} offset
     */
    makePoint: function (node, offset) {
        return {
            node: node,
            offset: offset,
        };
    },
    /**
     * Merges mergeFromBlock into mergeIntoBlock, respecting the rules of unbreakable.
     *
     * @param {Node} mergeFromBlock block to merge from
     * @param {Node} mergeIntoBlock block to merge into
     * @returns {Object} {node, offset}
     */
    mergeNonSimilarBlocks: function (mergeFromBlock, mergeIntoBlock) {
        var point;
        var mergeableTags = this.options.styleTags.join(', ') + ', li';
        var $contents = $(mergeFromBlock).find('*').addBack()
            .filter(mergeableTags)
            .filter(function (i, n) {
                if (!(n.tagName === 'LI' && $(n).find(mergeableTags).length)) {
                    return n;
                }
            }).contents();
        var containsUnbreakables = !!$contents.filter(this.options.isUnbreakable).length;

        if ($contents.length && !containsUnbreakables) {
            if (dom.isText($contents[0])) {
                this.removeExtremeBreakableSpace($contents[0]);
            }
            var $lastContents = $(mergeIntoBlock).contents().last();
            if (!($contents.length === 1 && $contents[0].tagName === 'BR')) {
                if (mergeIntoBlock.innerHTML.trim() === '<br>') {
                    $(mergeIntoBlock).contents().remove();
                    $(mergeIntoBlock).append($contents);
                    $lastContents = false;
                } else {
                    $lastContents.after($contents);
                }
            }
            while (mergeFromBlock.parentNode && this.isBlankNode(mergeFromBlock.parentNode, true)) {
                mergeFromBlock = mergeFromBlock.parentNode;
            }
            $(mergeFromBlock).remove();

            point = {};
            if ($lastContents && $lastContents.length) {
                point = this.makePoint($lastContents[0], dom.nodeLength($lastContents[0]));
            } else {
                point = this.makePoint($contents[0], 0);
            }

            point = this.deleteEdge(point.node, 'next', true) || point;
        }
        return point;
    },
    /**
     * Normalize the DOM and range.
     */
    normalize: function () {
        this.editable.normalize();
        var range = this.context.invoke('editor.createRange');
        var rangeN = range.normalize();

        // summernote's normalize function fails when br in text,
        // and targets the br instead of the point just after br.
        var point = rangeN.getStartPoint();
        if (point.node.tagName === "BR") {
            point = dom.nextPoint(point);
        }
        if (point.node.tagName && point.node.childNodes[point.offset]) {
            point = dom.nextPoint(point);
        }
        if (point.node.tagName === "BR") {
            point = dom.nextPoint(point);
        }
        if (point.node !== range.sc || point.offset !== range.so) {
            range = this.context.invoke('editor.setRange', point.node, point.offset);
            range.select();
        }
    },
    /**
     * Simulate a do_notify by notifying the user through a dialog.
     *
     * @param {String} title
     * @param {String} content
     */
    notify: function (title, content) {
        var $notif = $('<p>' + content + '</p>');
        new Dialog(this, {
            title: title,
            size: 'medium',
            $content: $notif,
        }).open();
    },
    /**
     * Return true if the `container` contains the `contained` and only
     * the `contained` (blank text nodes are ignored).
     *
     * @param {Node} container
     * @param {Node} contained
     * @returns {Boolean}
     */
    onlyContains: function (container, contained) {
        var self = this;
        if (!$.contains(container, contained)) {
            return false;
        }
        var $contents = $(container).contents();
        var otherContents = $contents.filter(function (index, node) {
            if (node === contained || dom.isText(node) && !self.isVisibleText(node)) {
                return false;
            }
            return true;
        });
        return !otherContents.length;
    },
    /**
     * Reorders the classes in the node's class attribute and returns it.
     *
     * @param {Node} node
     * @returns {String}
     */
    orderClass: function (node) {
        var className = node.getAttribute && node.getAttribute('class');
        if (!className) {
            return null;
        }
        className = className.replace(this.getRegex('spaceOrNewline', 'g'), ' ')
            .replace(this.getRegex('startAndEndSpace', 'g'), '')
            .replace(this.getRegex('space', 'g'), ' ');
        className = className.replace('o_default_snippet_text', '')
            .replace('o_checked', '');
        if (!className.length) {
            node.removeAttribute("class");
            return null;
        }
        className = className.split(" ");
        className.sort();
        className = className.join(" ");
        node.setAttribute('class', className);
        return className;
    },
    /**
     * Reorders the styles in the node's style attributes and returns it.
     *
     * @param {Node} node
     * @returns {String}
     */
    orderStyle: function (node) {
        var style = node.getAttribute('style');
        if (!style) {
            return null;
        }
        style = style.replace(this.getRegex('spaceOrNewline'), ' ')
            .replace(this.getRegex('startAndEndSemicolon', 'g'), '')
            .replace(this.getRegex('semicolon', 'g'), ';');
        if (!style.length) {
            node.removeAttribute("style");
            return null;
        }
        style = style.split(";");
        style.sort();
        style = style.join("; ") + ";";
        node.setAttribute('style', style);
        return style;
    },
    /**
     * Returns the path from the editable node to the given node.
     *
     * @param {Node} node
     * @returns {Object[]} list of objects (tagName, offset)
     */
    path: function (node) {
        var path = [];
        while (node && node !== this.editable) {
            var tagName = node.tagName;
            path.unshift({
                tagName: tagName,
                offset: _.filter(node.parentNode.childNodes, function (node) {
                    return node.tagName === tagName;
                }).indexOf(node),
            });
            node = node.parentNode;
        }
        return path;
    },
    /**
     * Removes all attributes without a value from the given node.
     *
     * @param {Node} node
     * @returns {Node}
     */
    removeBlankAttrs: function (node) {
        _.each([].slice.call(node.attributes), function (attr) {
            if (!attr.value) {
                node.removeAttribute(attr.name);
            }
        });
        return node;
    },
    /**
     * Remove a node's direct blank siblings, if any.
     * Eg: Text<i></i>Node<b></b>Text => TextNodeText
     *
     * @param {Node} node
     */
    removeBlankSiblings: function (node) {
        var isAfterBlank = node.previousSibling && this.isBlankNode(node.previousSibling);
        if (isAfterBlank) {
            $(node.previousSibling).remove();
        }
        var isBeforeBlank = node.nextSibling && this.isBlankNode(node.nextSibling);
        if (isBeforeBlank) {
            $(node.nextSibling).remove();
        }
    },
    /**
     * Removes the block target and joins its siblings.
     *
     * @param {Node} target
     * @param {Boolean} doNotInsertP true to NOT fill an empty unbreakable with a p element.
     * @returns {Object} {node, offset}
     */
    removeBlockNode: function (target, doNotInsertP) {
        var self = this;
        var check = function (point) {
            if (point.node === target) {
                return false;
            }
            return !point.node || self.options.isEditableNode(point.node) &&
                (point.node.tagName === "BR" || self.isVisibleText(point.node));
        };
        var parent = target.parentNode;
        var offset = [].indexOf.call(parent.childNodes, target);
        var deleteEdge = 'next';
        var point = dom.prevPointUntil(this.makePoint(target, 0), check);
        if (!point || !point.node) {
            deleteEdge = 'prev';
            point = dom.nextPointUntil(this.makePoint(target, 0), check);
        }

        $(target).remove();

        if (
            point && (deleteEdge === 'prev' && point.offset) ||
            deleteEdge === 'next' && point.offset === dom.nodeLength(point.node)
        ) {
            point = this.deleteEdge(point.node, deleteEdge) || point;
        }

        $(parent).contents().filter(function () {
            return dom.isText(this) && self.getRegexBlank({
                atLeastOne: true,
                invisible: true,
            }).test(this.textContent);
        }).remove();

        var br;
        if (parent.innerHTML === '') {
            br = this.document.createElement('br');
            $(parent).append(br);
            point = this.makePoint(parent, 0);
        }

        if (!doNotInsertP && this.getRegexBlank({
                space: true,
                invisible: true,
            }).test(parent.innerHTML)) {
            br = this.document.createElement('br');
            if (this.options.isUnbreakableNode(parent) && parent.tagName !== "TD") {
                var p = this.document.createElement('p');
                $(p).append(br);
                $(parent).append(p);
            } else {
                $(parent).append(br);
            }
            point = this.makePoint(br.parentNode, 0);
        }

        if (point && point.node.tagName === "BR" && point.node.parentNode) {
            point = {
                node: point.node.parentNode,
                offset: [].indexOf.call(point.node.parentNode.childNodes, point.node),
            };
        }

        return point || this.makePoint(parent, offset);
    },
    /**
     * Removes the empty inline nodes around the point, and joins its siblings.
     *
     * @param {Object} point {node, offset}
     * @returns {Object} {node, offset}
     */
    removeEmptyInlineNodes: function (point) {
        var node = point.node;
        if (!point.node.tagName && !point.node.textContent.length) {
            node = node.parentNode;
            if ($(node).hasClass('o_default_snippet_text')) {
                // for default snippet value
                return point;
            }
        }
        var prev;
        var next;
        while (
            node.tagName !== 'BR' &&
            (node.tagName ? node.innerHTML : node.textContent) === '' &&
            !this.isNodeBlockType(node) &&
            this.options.isEditableNode(node.parentNode) &&
            (!node.attributes || !node.attributes.contenteditable) &&
            !dom.isMedia(node)
        ) {
            prev = node.previousSibling;
            next = node.nextSibling;
            point = {
                node: node.parentNode,
                offset: [].indexOf.call(node.parentNode.childNodes, node)
            };
            $(node).remove();
            node = point.node;
        }
        if (next && !next.tagName) {
            if (/^\s+[^\s<]/.test(next.textContent)) {
                next.textContent = next.textContent.replace(this.getRegex('startSpace'), '\u00A0');
            }
        }
        if (prev) {
            if (!prev.tagName) {
                if (/[^\s>]\s+$/.test(prev.textContent)) {
                    prev.textContent = prev.textContent.replace(this.getRegex('endSpace'), ' ');
                }
            }
            point = this.makePoint(prev, dom.nodeLength(prev));
        }
        return point;
    },
    /**
     * Removes any amount of leading/trailing breakable space from a text node.
     * Returns how many characters were removed at the start
     * and at the end of the text node.
     *
     * @param {Node} textNode
     * @param {Boolean} secureExtremeties (defaults to true)
     * @returns {Object} removed {start, end}
     */
    removeExtremeBreakableSpace: function (textNode, secureExtremeties) {
        if (arguments.length === 1) {
            secureExtremeties = true;
        }
        if (secureExtremeties) {
            this.secureExtremeSingleSpace(textNode);
        }
        var removed = {
            start: 0,
            end: 0,
        };
        textNode.textContent = textNode.textContent.replace(this.getRegex('startNotChar'), function (toRemove) {
            removed.start = toRemove.length;
            return '';
        });
        textNode.textContent = textNode.textContent.replace(this.getRegex('endNotChar'), function (toRemove) {
            removed.end = toRemove.length;
            return '';
        });
        return removed;
    },
    /**
     * Makes the leading/trailing single space of a node non breakable (nbsp).
     *
     * @param {Node} node
     */
    secureExtremeSingleSpace: function (node) {
        if (this.getRegex('endSingleSpace').test(node.textContent)) {
            // if the text ends with a single space, make it insecable
            node.textContent = node.textContent.substr(0, node.textContent.length - 1) + '\u00A0';
        }
        if (this.getRegex('startSingleSpace').test(node.textContent)) {
            // if the text starts with a single space, make it insecable
            node.textContent = '\u00A0' + node.textContent.substr(1, node.textContent.length);
        }
    },
    /**
     * Skips points to ignore (generally for trying to figure out if edge point).
     * Returns the resulting point.
     *
     * @param {Object} point
     * @param {String} direction ('prev' or 'next')
     * @param {function} pred (extra condition to stop at)
     * @param {Object} options
     * @param {Boolean} options.noSkipBlankText true to not skip blank text
     * @param {Boolean} options.noSkipSingleBRs true to not skip single BRs
     * @param {Boolean} options.noSkipExtremeBreakableSpace true to not skip leading/trailing breakable space
     * @param {Boolean} options.noSkipParent true to not skip to leaf nodes or offset 0
     * @param {Boolean} options.noSkipSibling true to not skip if on edge and sibling is skippable
     * @returns {Object} {node, offset}
     */
    skipNodes: function (point, direction, pred, options) {
        var self = this;
        if (arguments.length === 3 && !_.isFunction(arguments[2])) {
            // allow for passing options and no pred function
            options = _.clone(pred);
            pred = null;
        }
        options = options || {};
        return dom[direction + 'PointUntil'](point, function (pt) {
            return !self.isSkippable(pt, direction, options) || pred && pred(pt);
        });
    },
    /**
     * Split the DOM tree at the node's start and end points.
     *
     * @param {Node} node
     */
    splitAtNodeEnds: function (node) {
        if (!node.parentNode) {
            return;
        }
        var startPoint = this.makePoint(node, 0);
        var endPoint = this.makePoint(node, dom.nodeLength(node));
        var splitOptions = {
            isSkipPaddingBlankHTML: true,
        };
        this.splitTree(node.parentNode, startPoint, splitOptions);
        this.splitTree(node.parentNode, endPoint, splitOptions);
        // Splitting at ends may create blank nodes (because of dom.splitTree) so let's clean it up:
        this.removeBlankSiblings(node.parentNode);
    },
    /**
     * Split the DOM tree at the point
     *
     * @param {Node} root - split root
     * @param {BoundaryPoint} point {node, offset}
     * @param {Object} [options]
     * @param {Boolean} [options.nextText] - default: false
     * @param {Boolean} [options.isSkipPaddingBlankHTML] - default: false
     * @param {Boolean} [options.isNotSplitEdgePoint] - default: false
     * @returns {Node} right node of boundary point
     */
    splitTree: function (root, point, options) {
        var nextText;
        if (options && options.nextText && !point.node.tagName) {
            nextText = point.node.splitText(point.offset);
        }
        var emptyText = false;
        if (!point.node.tagName && point.node.textContent === "") {
            emptyText = true;
            point.node.textContent = '\u200B';
            point.offset = 1;
        }
        var next = dom.splitTree(root, point, options);
        if (emptyText) {
            point.node.textContent = '';
        }
        var result = nextText || next || point.node;
        var att = nextText ? 'textContent' : 'innerHTML';
        if (/^\s+([^\s<])/.test(result[att])) {
            result[att] = result[att].replace(this.getRegex('startSpace'), '\u00A0');
        }
        return result;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getAttrsNoID: function (node) {
        var nodeAttributes = [];
        for (var i = 0; i < node.attributes.length; i++) {
            if (node.attributes[i].name !== 'id') {
                nodeAttributes.push(node.attributes[i]);
            }
        }
        return nodeAttributes;
    },
    _insertTextNodeInEditableArea: function (range, text) {
        // try to insert the text node in editable area
        var textNode = this.document.createTextNode(text);
        if (this.options.isEditableNode(range.sc) && $(range.sc).closest('[contenteditable]').attr('contenteditable') === 'true') {
            if (dom.isText(range.sc) && this.isVisibleText(range.sc)) {
                // If range is on visible text: split the text at offset and insert the text node
                range.sc.splitText(range.so);
                range.so = range.eo = dom.nodeLength(range.sc);
                $(range.sc).after(textNode);
            } else if (dom.isBR(range.sc)) {
                if (range.sc.nextSibling && this.isVisibleText(range.sc.nextSibling)) {
                    $(range.sc).before(textNode);
                } else {
                    $(range.sc).replaceWith(textNode);
                }
            } else if (dom.isVoid(range.sc)) {
                $(range.sc).before(textNode);
            } else if (range.sc.childNodes[range.so]) {
                var node = range.sc.childNodes[range.so];
                if (dom.isBR(node)) {
                    $(node).replaceWith(textNode);
                } else {
                    $(node).before(textNode);
                }
            } else if (dom.isText(range.sc)) {
                $(range.sc).after(textNode);
            } else if (this.options.isUnbreakableNode(range.sc)) {
                $(range.sc).append(textNode);
            }
        }
        if (!textNode.parentNode && this.options.isEditableNode(range.sc.parentNode)) {
            $(range.sc).before(textNode);
        }

        return textNode.parentNode && textNode;
    },
    /**
     * Perform operations that are necessary after the insertion of a visible character:
     * adapt range for the presence of zero-width characters, move out of media, rerange.
     *
     * @private
     */
    _removeInvisibleChar: function (range) {
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
            range = range.normalize();
        }
        return range;
    },
    _standardizeRangeOnEdge: function (range) {
        var self = this;

        var invisible = this.document.createTextNode('\u200B');

        if (dom.isText(range.sc) && !this.isVisibleText(range.sc) && range.sc.nextSibling) {
            var firstLeafOfNext = this.firstLeaf(range.sc.nextSibling);
            range = this.context.invoke('editor.setRange', firstLeafOfNext, 0);
        }

        // Create empty text node to have a range into the node
        if (range.sc.tagName && !dom.isVoid(range.sc) && !range.sc.childNodes[range.so]) {
            $(range.sc).append(invisible);
            range = this.context.invoke('editor.setRange', invisible, 0);
        }

        // On left edge of non-empty element: move before
        var siblings = range.sc.parentNode && range.sc.parentNode.childNodes;
        var isInEmptyElem = !siblings || !siblings.length || _.all(siblings, this.isBlankNode.bind(this));
        if (
            !range.so && !isInEmptyElem &&
            !(range.sc.previousSibling && range.sc.previousSibling.tagName === "BR") &&
            !this.options.isEditableNode(range.sc)
        ) {
            var point = range.getStartPoint();
            var newPoint = dom.prevPointUntil(point, function (pt) {
                return pt.node !== range.sc && !pt.node.tagName && !self.isBlankText(pt.node);
            });
            if (!newPoint || this.firstBlockAncestor(newPoint.node) !== this.firstBlockAncestor(point.node)) {
                range = this.context.invoke('editor.setRange', point.node, point.offset);
            } else {
                range = this.context.invoke('editor.setRange', newPoint.node, newPoint.offset);
            }
        }

        return range;
    },
    _wrapTextWithP: function (textNode) {
        if (dom.ancestor(textNode, dom.isAnchor)) {
            return;
        }
        var self = this;
        var isFormatNode = dom.ancestor(textNode, this.isFormatNode.bind(this));
        if (!isFormatNode) {
            var hasInlineParent = dom.ancestor(textNode.parentNode, function (node) {
                return !self.isNodeBlockType(node);
            });
            if (
                !hasInlineParent &&
                (textNode.tagName ||
                    !(textNode.previousSibling && this.isVisibleText(textNode.previousSibling) ||
                      textNode.nextSibling && this.isVisibleText(textNode.nextSibling))
                )
            ) {
                var blankP = this.document.createElement('p');
                $(textNode).after(blankP);
                $(blankP).prepend(textNode);
            }
        }
    },
});

registry.add('HelperPlugin', HelperPlugin);

return HelperPlugin;

});
