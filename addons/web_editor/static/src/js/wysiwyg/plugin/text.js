odoo.define('web_editor.wysiwyg.plugin.text', function (require) {
'use strict';

var AbstractPlugin = require('web_editor.wysiwyg.plugin.abstract');
var registry = require('web_editor.wysiwyg.plugin.registry');

var dom = $.summernote.dom;
dom.isAnchor = function (node) {
    return (node.tagName === 'A' || node.tagName === 'BUTTON' || $(node).hasClass('btn')) &&
        !$(node).hasClass('fa') && !$(node).hasClass('o_image');
};


var TextPlugin = AbstractPlugin.extend({
    events: {
        'summernote.paste': '_onPaste',
    },

    // See: https://dvcs.w3.org/hg/editing/raw-file/tip/editing.html#removeformat-candidate
    formatTags: [
        'abbr',
        'acronym',
        'b',
        'bdi',
        'bdo',
        'big',
        'blink',
        'cite',
        'code',
        'dfn',
        'em',
        'font',
        'i',
        'ins',
        'kbd',
        'mark',
        'nobr',
        'q',
        's',
        'samp',
        'small',
        'span',
        'strike',
        'strong',
        'sub',
        'sup',
        'tt',
        'u',
        'var',
    ],
    tab: '\u00A0\u00A0\u00A0\u00A0',

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Insert a Horizontal Rule element (hr).
     */
    insertHR: function () {
        var self = this;
        var hr = this.document.createElement('hr');
        this.context.invoke('HelperPlugin.insertBlockNode', hr);
        var point = this.context.invoke('HelperPlugin.makePoint', hr, 0);
        point = dom.nextPointUntil(point, function (pt) {
            return pt.node !== hr && !self.options.isUnbreakableNode(pt.node);
        }) || point;
        var range = $.summernote.range.create(point.node, point.offset);
        range.select();
    },
    /**
     * Insert a TAB (4 non-breakable spaces).
     */
    insertTab: function () {
        this.context.invoke('HelperPlugin.insertTextInline', this.tab);
    },
    /**
     * Paste nodes or their text content into the editor.
     *
     * @param {Node[]} nodes
     * @param {Boolean} textOnly true to allow only dropping plain text
     */
    pasteNodes: function (nodes, textOnly) {
        if (!nodes.length) {
            return;
        }
        nodes = textOnly ? this.document.createTextNode($(nodes).text()) : nodes;
        nodes = textOnly ? nodes : this._mergeAdjacentULs(nodes);

        var point = this._getPastePoint();
        // Prevent pasting HTML within a link:
        point = textOnly ? point : dom.nextPointUntil(point, this._isPointInAnchor.bind(this));

        this._insertNodesAt(nodes, point);

        var start = nodes[nodes.length - 1];
        this.context.invoke('editor.setRange', start, dom.nodeLength(start)).normalize().select();
    },
    /**
     * Prepare clipboard data for safe pasting into the editor.
     *
     * @see clipboardWhitelist
     * @see clipboardBlacklist
     *
     * @param {DOMString} clipboardData
     * @returns {Node[]}
     */
    prepareClipboardData: function (clipboardData) {
        var $clipboardData = this._removeIllegalClipboardElements($(clipboardData));

        var $all = $clipboardData.find('*').addBack();
        $all.filter('table').addClass('table table-bordered');
        this._wrapTDContents($all.filter('td'));
        this._fillEmptyBlocks($all);
        this._removeIllegalClipboardAttributes($all);
        $all.filter('a').removeClass();
        $all.filter('img').css('max-width', '100%');

        return $clipboardData.toArray();
    },
    /**
     * Format a 'format' block: change its tagName (eg: p -> h1).
     *
     * @param {string} tagName
     *       P, H1, H2, H3, H4, H5, H6, BLOCKQUOTE, PRE
     */
    formatBlock: function (tagName) {
        var self = this;
        var r = this.context.invoke('editor.createRange');
        if (
            !r ||
            !this.$editable.has(r.sc).length ||
            !this.$editable.has(r.ec).length ||
            this.options.isUnbreakableNode(r.sc)
        ) {
            return;
        }
        var nodes = this.context.invoke('HelperPlugin.getSelectedNodes');
        nodes = this.context.invoke('HelperPlugin.filterFormatAncestors', nodes);
        if (!nodes.length) {
            var node = this.context.invoke('editor.createRange').sc;
            if (node.tagName === 'BR' || dom.isText(node)) {
                node = node.parentNode;
            }
            nodes = [node];
        }
        var changedNodes = [];
        _.each(nodes, function (node) {
            var newNode = self.document.createElement(tagName);
            $(newNode).append($(node).contents());
            var attributes = $(node).prop("attributes");
            _.each(attributes, function (attr) {
                $(newNode).attr(attr.name, attr.value);
            });
            $(node).replaceWith(newNode);
            changedNodes.push(newNode);
        });

        // Select all formatted nodes
        if (changedNodes.length) {
            var lastNode = changedNodes[changedNodes.length - 1];
            var startNode = changedNodes[0].firstChild || changedNodes[0];
            var endNode = lastNode.lastChild || lastNode;
            var range = this.context.invoke('editor.setRange', startNode, 0, endNode, dom.nodeLength(endNode));
            range.select();
        }
    },
    /**
     * Change the paragraph alignment of a 'format' block.
     *
     * @param {string} style
     *       justifyLeft, justifyCenter, justifyRight, justifyFull
     */
    formatBlockStyle: function (style) {
        var self = this;
        var nodes = this.context.invoke('HelperPlugin.getSelectedNodes');
        nodes = this.context.invoke('HelperPlugin.filterFormatAncestors', nodes);
        var align = style === 'justifyLeft' ? 'left' :
            style === 'justifyCenter' ? 'center' :
            style === 'justifyRight' ? 'right' : 'justify';
        _.each(nodes, function (node) {
            if (dom.isText(node)) {
                return;
            }
            var textAlign = self.window.getComputedStyle(node).textAlign;
            if (align !== textAlign) {
                if (align !== self.window.getComputedStyle(node.parentNode).textAlign) {
                    $(node).css('text-align', align);
                } else {
                    $(node).css('text-align', '');
                }
            }
        });
        this.editable.normalize();
    },
    /**
     * (Un-)format text: make it bold, italic, ...
     *
     * @param {string} tagName
     *       bold, italic, underline, strikethrough, superscript, subscript
     */
    formatText: function (tagName) {
        var self = this;
        var tag = {
            bold: 'B',
            italic: 'I',
            underline: 'U',
            strikethrough: 'S',
            superscript: 'SUP',
            subscript: 'SUB',
        } [tagName];
        if (!tag) {
            throw new Error(tagName);
        }

        var range = this.context.invoke('editor.createRange');
        if (!range || !this.$editable.has(range.sc).length || !this.$editable.has(range.ec).length) {
            return;
        }
        if (range.isCollapsed()) {
            var br;
            if (range.sc.tagName === 'BR') {
                br = range.sc;
            } else if (range.sc.firstChild && range.sc.firstChild.tagName === 'BR') {
                br = range.sc.firstChild;
            }
            if (br) {
                var emptyText = this.document.createTextNode('\u200B');
                $(br).before(emptyText).remove();
                range = this.context.invoke('editor.setRange', emptyText, 0, emptyText, 1);
            } else {
                var offset = range.so;
                this.context.invoke('HelperPlugin.insertTextInline', '\u200B');
                range = this.context.invoke('editor.createRange');
                range.so = offset;
                range.eo = offset + 1;
            }
            range.select();
        }

        var nodes = this.context.invoke('HelperPlugin.getSelectedNodes');
        var texts = this.context.invoke('HelperPlugin.filterLeafChildren', nodes);
        var formatted = this.context.invoke('HelperPlugin.filterFormatAncestors', nodes);

        var start = this.context.invoke('HelperPlugin.firstLeaf', nodes[0]);
        var end = this.context.invoke('HelperPlugin.lastLeaf', nodes[nodes.length - 1]);

        function containsOnlySelectedText(node) {
            return _.all(node.childNodes, function (n) {
                return _.any(texts, function (t) {
                    return n === t && !(dom.isText(n) && n.textContent === '');
                }) && containsOnlySelectedText(n);
            });
        }

        function containsAllSelectedText(node) {
            return _.all(texts, function (t) {
                return _.any(node.childNodes, function (n) {
                    return n === t && !(dom.isText(n) && n.textContent === '') || containsAllSelectedText(n);
                });
            });
        }

        var nodeAlreadyStyled = [];
        var toStyled = [];
        var notStyled = _.filter(texts, function (text, index) {
            if (toStyled.indexOf(text) !== -1 || nodeAlreadyStyled.indexOf(text) !== -1) {
                return;
            }
            nodeAlreadyStyled.push(text);

            end = text;

            var styled = dom.ancestor(text, function (node) {
                return node.tagName === tag;
            });
            if (styled) {
                if (
                    !/^\u200B$/.test(text.textContent) &&
                    containsAllSelectedText(styled) &&
                    containsOnlySelectedText(styled)
                ) {
                    // Unwrap all contents
                    nodes = $(styled).contents();
                    $(styled).before(nodes).remove();
                    nodeAlreadyStyled.push.apply(nodeAlreadyStyled, nodes);
                    end = _.last(nodeAlreadyStyled);
                } else {
                    var options = {
                        isSkipPaddingBlankHTML: true,
                        isNotSplitEdgePoint: true,
                    };

                    if (
                        nodeAlreadyStyled.indexOf(text.nextSibling) === -1 &&
                        !dom.isRightEdgeOf(text, styled)
                    ) {
                        options.nextText = false;
                        var point = self.context.invoke('HelperPlugin.makePoint', text, dom.nodeLength(text));
                        if (dom.isMedia(text)) {
                            point = dom.nextPoint(point);
                        }
                        var next = self.context.invoke('HelperPlugin.splitTree', styled, point, options);
                        nodeAlreadyStyled.push(next);
                    }
                    if (
                        nodeAlreadyStyled.indexOf(text.previousSibling) === -1 &&
                        !dom.isLeftEdgeOf(text, styled)
                    ) {
                        options.nextText = true;
                        var textPoint = self.context.invoke('HelperPlugin.makePoint', text, 0);
                        text = self.context.invoke('HelperPlugin.splitTree', styled, textPoint, options);
                        nodeAlreadyStyled.push(text);
                        if (index === 0) {
                            start = text;
                        }
                        end = text;
                    }

                    var toRemove = dom.ancestor(text, function (n) {
                        return n.tagName === tag;
                    });
                    if (toRemove) {
                        // Remove generated empty elements
                        if (
                            toRemove.nextSibling &&
                            self.context.invoke('HelperPlugin.isBlankNode', toRemove.nextSibling)
                        ) {
                            $(toRemove.nextSibling).remove();
                        }
                        if (
                            toRemove.previousSibling &&
                            self.context.invoke('HelperPlugin.isBlankNode', toRemove.previousSibling)
                        ) {
                            $(toRemove.previousSibling).remove();
                        }

                        // Unwrap the element
                        nodes = $(toRemove).contents();
                        $(toRemove).before(nodes).remove();
                        nodeAlreadyStyled.push.apply(nodeAlreadyStyled, nodes);
                        end = _.last(nodeAlreadyStyled);
                    }
                }
            }

            if (dom.ancestor(text, function (node) {
                    return toStyled.indexOf(node) !== -1;
                })) {
                return;
            }

            var node = text;
            while (
                node && node.parentNode &&
                formatted.indexOf(node) === -1 &&
                formatted.indexOf(node.parentNode) === -1
            ) {
                node = node.parentNode;
            }
            if (node !== text) {
                if (containsAllSelectedText(node)) {
                    toStyled.push.apply(toStyled, texts);
                    node = text;
                } else if (!containsOnlySelectedText(node)) {

                    node = text;
                }
            }

            if (toStyled.indexOf(node) === -1) {
                toStyled.push(node);
            }
            return !styled;
        });

        toStyled = _.uniq(toStyled);

        if (notStyled.length) {
            nodes = [];
            var toMerge = [];
            _.each(toStyled, function (node) {
                var next = true;
                if (node.nextSibling && node.nextSibling.tagName === tag) {
                    $(node.nextSibling).prepend(node);
                    next = false;
                }
                if (node.previousSibling && node.previousSibling.tagName === tag) {
                    $(node.previousSibling).append(node);
                }
                if (node.parentNode && node.parentNode.tagName !== tag) {
                    var styled = self.document.createElement(tag);
                    if (node.tagName) {
                        $(styled).append(node.childNodes);
                        $(node).append(styled);
                    } else {
                        $(node).before(styled);
                        styled.appendChild(node);
                    }
                }
                // Add adjacent nodes with same tagName to list of nodes to merge
                if (
                    node.parentNode && node.parentNode[next ? 'nextSibling' : 'previousSibling'] &&
                    node.parentNode.tagName === node.parentNode[next ? 'nextSibling' : 'previousSibling'].tagName
                ) {
                    toMerge.push(next ? node.parentNode : node.parentNode.previousSibling);
                }
            });
            // Merge what needs merging
            while (toMerge.length) {
                this.context.invoke('HelperPlugin.deleteEdge', toMerge.pop(), 'next');
            }
        }

        range = this.context.invoke('editor.setRange', start, 0, end, dom.nodeLength(end));

        if (range.sc === range.ec && range.sc.textContent === '\u200B') {
            range.so = range.eo = 1;
        }

        range.select();
        this.editable.normalize();
    },
    /**
     * Remove format on the current range.
     *
     * @see _isParentRemoveFormatCandidate
     */
    removeFormat: function () {
        this._selectCurrentIfCollapsed();
        var selectedText = this.context.invoke('HelperPlugin.getSelectedText');
        var selectedIcons = this.context.invoke('HelperPlugin.getSelectedNodes');
        selectedIcons = _.filter(selectedIcons, dom.isIcon);
        if (!selectedText.length && !selectedIcons.length) {
            return;
        }
        _.each(selectedIcons, this._removeIconFormat.bind(this));
        _.each(selectedText, this._removeTextFormat.bind(this));
        var startNode = selectedText[0];
        var endNode = selectedText[selectedText.length - 1];
        this.context.invoke('editor.setRange', startNode, 0, endNode, dom.nodeLength(endNode)).select();
        this.editable.normalize();
        this.context.invoke('editor.saveRange');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Remove the non-whitelisted or blacklisted
     * top level elements from clipboard data.
     *
     * @see clipboardWhitelist
     * @see clipboardBlacklist
     *
     * @private
     * @param {JQuery} $clipboardData
     * @returns {Object} {$clipboardData: JQuery, didRemoveNodes: Boolean}
     */
    _cleanClipboardRoot: function ($clipboardData) {
        var didRemoveNodes = false;
        var whiteList = this._clipboardWhitelist();
        var blackList = this._clipboardBlacklist();
        var $fakeParent = $(this.document.createElement('div'));
        _.each($clipboardData, function (node) {
            var isWhitelisted = dom.isText(node) || $(node).filter(whiteList.join(',')).length;
            var isBlacklisted = $(node).filter(blackList.join(',')).length;
            if (!isWhitelisted || isBlacklisted) {
                $fakeParent.append(node.childNodes);
                didRemoveNodes = true;
            } else {
                $fakeParent.append(node);
            }
        });
        return {
            $clipboardData: $fakeParent.contents(),
            didRemoveNodes: didRemoveNodes,
        };
    },
    /**
     * Return a list of jQuery selectors for prohibited nodes on paste.
     *
     * @private
     * @returns {String[]}
     */
    _clipboardBlacklist: function () {
        return ['.Apple-interchange-newline'];
    },
    /**
     * Return a list of jQuery selectors for exclusively authorized nodes on paste.
     *
     * @private
     * @returns {String[]}
     */
    _clipboardWhitelist: function () {
        var listSels = ['ul', 'ol', 'li'];
        var styleSels = ['i', 'b', 'u', 'em', 'strong'];
        var tableSels = ['table', 'th', 'tbody', 'tr', 'td'];
        var miscSels = ['img', 'br', 'a', '.fa'];
        return this.options.styleTags.concat(listSels, styleSels, tableSels, miscSels);
    },
    /**
     * Return a list of attribute names that are exclusively authorized on paste.
     * 
     * @private
     * @returns {String[]}
     */
    _clipboardWhitelistAttr: function () {
        return ['class', 'href', 'src'];
    },
    /**
     * Fill up empty block elements with BR elements so the carret can enter them.
     *
     * @private
     * @param {JQuery} $els
     */
    _fillEmptyBlocks: function ($els) {
        var self = this;

        $els.filter(function (i, n) {
            return self.context.invoke('HelperPlugin.isNodeBlockType', n) && !n.childNodes;
        }).append(this.document.createElement('br'));
    },
    /**
     * Get all non-whitelisted or blacklisted elements from clipboard data.
     *
     * @private
     * @param {JQuery} $clipboardData
     * @returns {JQuery}
     */
    _filterIllegalClipboardElements: function ($clipboardData) {
        return $clipboardData.find('*').addBack()
                .not(this._clipboardWhitelist().join(','))
                .addBack(this._clipboardBlacklist().join(','))
                .filter(function () {
                    return !dom.isText(this);
                });
    },
    /**
     * Get a legal point to paste at, from the current range's start point.
     *
     * @private
     * @returns {Object} {node: Node, offset: Number}
     */
    _getPastePoint: function () {
        var point = this.context.invoke('editor.createRange').getStartPoint();
        var offsetChild = point.node.childNodes[point.offset];
        point = offsetChild ? this.context.invoke('HelperPlugin.makePoint', offsetChild, 0) : point;
        return dom.nextPointUntil(point, this._isPastePointLegal.bind(this));
    },
    /**
     * Insert nodes at a point. Insert them inline if the first node is inline
     * and pasting inline is legal at that point.
     *
     * @private
     * @param {Node[]} nodes
     * @param {Object} point {node: Node, offset: Number}
     */
    _insertNodesAt: function (nodes, point) {
        var canInsertInline = dom.isText(point.node) || point.node.tagName === 'BR' || dom.isMedia(point.node);
        var $fakeParent = $(this.document.createElement('div'));
        $fakeParent.append(nodes);
        if (dom.isInline(nodes[0]) && canInsertInline) {
            point.node = point.node.tagName ? point.node : point.node.splitText(point.offset);
            $(point.node).before($fakeParent.contents());
        } else {
            this.context.invoke('HelperPlugin.insertBlockNode', $fakeParent[0]);
        }
        $fakeParent.contents().unwrap();
    },
    /**
     * Return true if the parent of the given node is a removeFormat candidate:
     * - It is a removeFormat candidate as defined by W3C
     * - It is contained within the editable area
     * - It is not unbreakable
     *
     * @see formatTags the list of removeFormat candidates as defined by W3C
     *
     * @private
     * @param {Node} node
     */
    _isParentRemoveFormatCandidate: function (node) {
        var parent = node.parentNode;
        if (!parent) {
            return false;
        }
        var isEditableOrAbove = parent && (parent === this.editable || $.contains(parent, this.editable));
        var isUnbreakable = parent && this.options.isUnbreakableNode(parent);
        var isRemoveFormatCandidate = parent && parent.tagName && this.formatTags.indexOf(parent.tagName.toLowerCase()) !== -1;
        return parent && !isEditableOrAbove && !isUnbreakable && isRemoveFormatCandidate;
    },
    /**
     * Return true if it's legal to paste nodes at the given point:
     * if the point is not within a void node and the point is not unbreakable.
     *
     * @private
     * @param {Object} point {node: Node, offset: Number}
     * @returns {Boolean}
     */
    _isPastePointLegal: function (point) {
        var node = point.node;
        var isWithinVoid = false;
        if (node.parentNode) {
            isWithinVoid = dom.isVoid(node.parentNode) || $(node.parentNode).filter('.fa').length;
        }
        return !isWithinVoid && !this.options.isUnbreakableNode(point.node);
    },
    /**
     * @private
     * @param {Object} point {node: Node, offset: Number}
     * @returns {Boolean}
     */
    _isPointInAnchor: function (point) {
        var ancestor = dom.ancestor(point.node, dom.isAnchor);
        return !ancestor || ancestor === this.editable;
    },
    /**
     * Check a list of nodes and merges all adjacent ULs together:
     * [ul, ul, p, ul, ul] will return [ul, p, ul], with the li's of
     * nodes[1] and nodes[4] appended to nodes[0] and nodes[3].
     *
     * @private
     * @param {Node[]} nodes
     * @return {Node[]} the remaining, merged nodes
     */
    _mergeAdjacentULs: function (nodes) {
        var res = [];
        var prevNode;
        _.each(nodes, function (node) {
            prevNode = res[res.length - 1];
            if (prevNode && node.tagName === 'UL' && prevNode.tagName === 'UL') {
                $(prevNode).append(node.childNodes);
            } else {
                res.push(node);
            }
        });
        return res;
    },
    /**
     * Remove an icon's format (colors, font size).
     *
     * @private
     * @param {Node} icon
     */
    _removeIconFormat: function (icon) {
        $(icon).css({
            color: '',
            backgroundColor: '',
            fontSize: '',
        });
        var reColorClasses = /(^|\s+)(bg|text)-\S*|/g;
        icon.className = icon.className.replace(reColorClasses, '').trim();
    },
    /**
     * Remove non-whitelisted attributes from clipboard.
     *
     * @private
     * @param {JQuery} $els
     */
    _removeIllegalClipboardAttributes: function ($els) {
        var self = this;
        $els.each(function () {
            var $node = $(this);
            _.each(_.pluck(this.attributes, 'name'), function (attribute) {
                if (self._clipboardWhitelistAttr().indexOf(attribute) === -1) {
                    $node.removeAttr(attribute);
                }
            });
        }).removeClass('o_editable o_not_editable');
    },
    /**
     * Remove non-whitelisted and blacklisted elements from clipboard data.
     *
     * @private
     * @param {JQuery} $clipboardData
     * @returns {JQuery}
     */
    _removeIllegalClipboardElements: function ($clipboardData) {
        var root = true;
        $clipboardData = $clipboardData.not('meta').not('style').not('script');
        var $badNodes = this._filterIllegalClipboardElements($clipboardData);

        do {
            if (root) {
                root = false;
                var cleanData = this._cleanClipboardRoot($clipboardData);
                $clipboardData = cleanData.$clipboardData;
                root = cleanData.didRemoveNodes;
            } else {
                this._removeNodesPreserveContents($badNodes);
            }

            $badNodes = this._filterIllegalClipboardElements($clipboardData);
        } while ($badNodes.length);
        return $clipboardData;
    },
    /**
     * Remove nodes from the DOM while preserving their contents if any.
     *
     * @private
     * @param {JQuery} $nodes
     */
    _removeNodesPreserveContents: function ($nodes) {
        var $contents = $nodes.contents();
        if ($contents.length) {
            $contents.unwrap();
        } else {
            $nodes.remove();
        }
    },
    /**
     * Remove a text node's format: remove its style parents (b, i, u, ...).
     *
     * @private
     * @param {Node} textNode
     */
    _removeTextFormat: function (textNode) {
        var node = textNode;
        while (this._isParentRemoveFormatCandidate(node)) {
            this.context.invoke('HelperPlugin.splitAtNodeEnds', node);
            $(node.parentNode).before(node).remove();
        }
    },
    /**
     * Select the whole current node if the range is collapsed
     *
     * @private
     */
    _selectCurrentIfCollapsed: function () {
        var range = this.context.invoke('editor.createRange');
        if (!range.isCollapsed()) {
            return;
        }
        this.context.invoke('editor.setRange', range.sc, 0, range.sc, dom.nodeLength(range.sc)).select();
        this.context.invoke('editor.saveRange');
    },
    /**
     * Prevent inline nodes directly in TDs by wrapping them in P elements.
     *
     * @private
     * @param {JQuery} $tds
     */
    _wrapTDContents: function ($tds) {
        var self = this;
        var $inlinesInTD = $tds.contents().filter(function () {
            return !self.context.invoke('HelperPlugin.isNodeBlockType', this);
        });
        var parentsOfInlinesInTD = [];
        _.each($inlinesInTD, function (n) {
            parentsOfInlinesInTD.push(self.context.invoke('HelperPlugin.firstBlockAncestor', n));
        });
        $($.unique(parentsOfInlinesInTD)).wrapInner(this.document.createElement('p'));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handle paste events to permit cleaning/sorting of the data before pasting.
     *
     * @private
     * @param {SummernoteEvent} se
     * @param {jQueryEvent} e
     */
    _onPaste: function (se, e) {
        se.preventDefault();
        se.stopImmediatePropagation();
        e.preventDefault();
        e.stopImmediatePropagation();

        this.context.invoke('editor.beforeCommand');

        // Clean up
        var clipboardData = e.originalEvent.clipboardData.getData('text/html');
        if (clipboardData) {
            clipboardData = this.prepareClipboardData(clipboardData);
        } else {
            clipboardData = e.originalEvent.clipboardData.getData('text/plain');
            // get that text as an array of text nodes separated by <br> where needed
            var allNewlines = /\n/g;
            clipboardData = $('<p>' + clipboardData.replace(allNewlines, '<br>') + '</p>').contents().toArray();
        }

        // Delete selection
        this.context.invoke('HelperPlugin.deleteSelection');

        // Insert the nodes
        this.pasteNodes(clipboardData);
        this.context.invoke('HelperPlugin.normalize');
        this.context.invoke('editor.saveRange');

        this.context.invoke('editor.afterCommand');
    },
});

registry.add('TextPlugin', TextPlugin);

return TextPlugin;

});
