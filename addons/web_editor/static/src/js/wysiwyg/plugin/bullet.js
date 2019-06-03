odoo.define('web_editor.wysiwyg.plugin.bullet', function (require) {
'use strict';

var core = require('web.core');
var AbstractPlugin = require('web_editor.wysiwyg.plugin.abstract');
var wysiwygOptions = require('web_editor.wysiwyg.options');
var registry = require('web_editor.wysiwyg.plugin.registry');
var wysiwygTranslation = require('web_editor.wysiwyg.translation');

var _t = core._t;
var dom = $.summernote.dom;

wysiwygOptions.icons.checklist = 'fa fa-check-square';
wysiwygOptions.keyMap.pc['CTRL+SHIFT+NUM9'] = 'insertCheckList';
wysiwygOptions.keyMap.mac['CMD+SHIFT+NUM9'] = 'insertCheckList';
wysiwygTranslation.lists.checklist = _t('Checklist');
wysiwygTranslation.help.checklist = _t('Toggle checkbox list');


var BulletPlugin = AbstractPlugin.extend({
    events: {
        'summernote.mousedown': '_onMouseDown',
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Insert an ordered list, an unordered list or a checklist.
     * If already in list, remove the list or convert it to the given type.
     *
     * @param {string('ol'|'ul'|'checklist')} type the type of list to insert
     * @returns {false|Node[]} contents of the ul/ol or content of the converted/removed list
     */
    insertList: function (type) {
        var range = this.context.invoke('editor.createRange');
        if (!range) {
            return;
        }
        var res;
        var start = range.getStartPoint();
        var end = range.getEndPoint();

        var isInList = dom.ancestor(range.sc, dom.isList);
        if (isInList) {
            res = this._convertList(false, [], start, end, type);
        } else {
            var ul = this._createList(type);
            res = [].slice.call(ul.children);
        }

        var startLeaf = this.context.invoke('HelperPlugin.firstLeaf', start.node);
        var endLeaf = this.context.invoke('HelperPlugin.firstLeaf', end.node);
        range = this.context.invoke('editor.setRange', startLeaf, start.offset, endLeaf, end.offset);
        range.select();
        this.context.invoke('editor.saveRange');

        return res;
    },
    /**
     * Indent a node (list or format node).
     *
     * @returns {false|Node[]} contents of list/indented item
     */
    indent: function () {
        return this._indent();
    },
    /**
     * Outdent a node (list or format node).
     *
     * @returns {false|Node[]} contents of list/outdented item
     */
    outdent: function () {
        return this._indent(true);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add checklist buttons.
     */
    _addButtons: function () {
        var self = this;
        this._super();
        this.context.memo('help.checklist', this.lang.help.checklist);
        this._createButton('checklist', this.options.icons.checklist, this.lang.lists.checklist, function (e) {
            e.preventDefault();
            self.context.invoke('editor.insertCheckList');
        });
    },
    /**
     * Convert ul<->ol or remove ul/ol.
     *
     * @param {boolean} isWithinElem true if selection already inside the LI
     * @param {DOM[]} nodes selected nodes
     * @param {Object} startPoint
     * @param {Object} endPoint
     * @param {boolean} sorted
     * @returns {boolean} isWithinElem
     */
    _convertList: function (isWithinElem, nodes, startPoint, endPoint, sorted) {
        var ol = dom.ancestor(startPoint.node, dom.isList);
        var parent = ol.parentNode;

        // get selected lis

        var lis = [];
        var lisBefore = [];
        var lisAfter = [];
        _.each(ol.children, function (li) {
            if (!isWithinElem && (li === startPoint.node || $.contains(li, startPoint.node))) {
                isWithinElem = true;
            }
            if (isWithinElem) {
                lis.push(li);
            } else if (lis.length) {
                lisAfter.push(li);
            } else {
                lisBefore.push(li);
            }
            if (isWithinElem && (li === endPoint.node || $.contains(li, endPoint.node))) {
                isWithinElem = false;
            }
        });

        var res = lis;

        if (lisBefore.length) {
            var ulBefore = this.document.createElement(ol.tagName);
            ulBefore.className = ol.className;

            if (dom.isLi(ol.parentNode)) {
                var li = this.document.createElement('li');
                li.className = ol.parentNode.className;
                $(li).insertBefore(ol.parentNode);
                li.appendChild(ulBefore);
            } else {
                $(ulBefore).insertBefore(ol);
            }

            $(ulBefore).append(lisBefore);
        }
        if (lisAfter.length) {
            var ulAfter = this.document.createElement(ol.tagName);
            ulAfter.className = ol.className;

            if (dom.isLi(ol.parentNode)) {
                var li = this.document.createElement('li');
                li.className = ol.parentNode.className;
                $(li).insertAfter(ol.parentNode);
                li.appendChild(ulAfter);
            } else {
                $(ulAfter).insertAfter(ol);
            }

            $(ulAfter).append(lisAfter);
        }

        // convert ul<->ol or remove list
        var current = ol.tagName === 'UL' && ol.className.indexOf('o_checklist') !== -1 ? 'checklist' : ol.tagName.toLowerCase();
        if (current !== sorted) {
            // convert ul <-> ol

            var ul;
            $(ol).removeClass('o_checklist');
            if (sorted === 'checklist' && current === "ul") {
                ul = ol;
            } else if (sorted === 'ul' && current === 'checklist') {
                ul = ol;
            } else {
                ul = this.document.createElement(sorted === "ol" ? "ol" : "ul");
                ul.className = ol.className;
                $(ul).removeClass('o_checklist');
                $(ul).insertBefore(ol).append(lis);
                parent.removeChild(ol);
            }
            if (sorted === 'checklist') {
                $(ul).addClass('o_checklist');
            }

            this.context.invoke('HelperPlugin.deleteEdge', ul, 'next');
            this.context.invoke('HelperPlugin.deleteEdge', ul, 'prev');

        } else {
            // remove ol/ul

            if (dom.isLi(parent) || dom.isList(parent)) {
                if (dom.isLi(parent)) {
                    ol = parent;
                    parent = ol.parentNode;
                }
                $(lis).insertBefore(ol);
            } else {
                res = [];
                _.each(lis, function (li) {
                    res.push.apply(res, li.childNodes);
                    $(li.childNodes).insertBefore(ol);
                });

                // wrap in p

                var hasNode = _.find(res, function (node) {
                    return node.tagName && node.tagName !== "BR" && !dom.isMedia(node);
                });
                if (!hasNode) {
                    var p = this.document.createElement('p');
                    $(p).insertBefore(ol).append(res);
                    res = [p];
                }
            }
            parent.removeChild(ol);

        }

        nodes.push.apply(nodes, res);

        return isWithinElem;
    },
    /**
     * Create a list if allowed.
     *
     * @param {string('ol'|'ul'|'checklist')} type the type of list to insert
     * @returns {false|Node} the list, if any
     */
    _createList: function (type) {
        var nodes = this.context.invoke('HelperPlugin.getSelectedNodes');
        var formatNodes = this._filterEditableFormatNodes(nodes);
        if (!formatNodes.length) {
            return;
        }

        var ul = this._createListElement(type);
        $(formatNodes[0][0] || formatNodes[0]).before(ul);
        this._fillListElementWith(ul, formatNodes);
        this._deleteListElementEdges(ul);

        return ul;
    },
    /**
     * Create a list element of the given type and return it.
     *
     * @param {string('ol'|'ul'|'checklist')} type the type of list to insert
     * @returns {Node}
     */
    _createListElement: function (type) {
        var ul = this.document.createElement(type === "ol" ? "ol" : "ul");
        if (type === 'checklist') {
            ul.className = 'o_checklist';
        }
        return ul;
    },
    /**
     * Delete a list element's edges if necessary.
     *
     * @param {Node} ul
     */
    _deleteListElementEdges: function (ul) {
        this.context.invoke('HelperPlugin.deleteEdge', ul, 'next');
        this.context.invoke('HelperPlugin.deleteEdge', ul, 'prev');
        this.editable.normalize();
    },
    /**
     * Fill a list element with the nodes passed, wrapped in LIs.
     *
     * @param {Node} ul
     * @param {Node[]} nodes
     */
    _fillListElementWith: function (ul, nodes) {
        var self = this;
        _.each(nodes, function (node) {
            var li = self.document.createElement('li');
            $(li).append(node);
            ul.appendChild(li);
        });
    },
    /**
     * Filter the editable format ancestors of the given nodes
     * and fill or wrap them if needed for range selection.
     *
     * @param {Node[]} nodes
     * @returns {Node[]}
     */
    _filterEditableFormatNodes: function (nodes) {
        var self = this;
        var formatNodes = this.context.invoke('HelperPlugin.filterFormatAncestors', nodes);
        formatNodes = _.compact(_.map(formatNodes, function (node) {
            var ancestor = (!node.tagName || node.tagName === 'BR') && dom.ancestor(node, dom.isCell);
            if (ancestor && self.options.isEditableNode(ancestor)) {
                if (!ancestor.childNodes.length) {
                    var br = self.document.createElement('br');
                    ancestor.appendChild(br);
                }
                var p = self.document.createElement('p');
                $(p).append(ancestor.childNodes);
                ancestor.appendChild(p);
                return p;
            }
            return self.options.isEditableNode(node) && node || null;
        }));
        return formatNodes;
    },
    /**
     * Indent or outdent a format node.
     *
     * @param {bool} outdent true to outdent, false to indent
     * @returns {false|[]Node} indented nodes
     */
    _indent: function (outdent) {
        var range = this.context.invoke('editor.createRange');
        if (!range) {
            return;
        }
        // list groups shouldn't be outdented like regular lists
        if ($(dom.ancestor(range.sc, dom.isList)).hasClass('list-group')) {
            return;
        }

        var self = this;
        var nodes = [];
        var isWithinElem;
        var ancestor = range.commonAncestor() || this.editable;
        var $dom = $(ancestor);

        if (!dom.isList(ancestor)) {
            // to indent a selection, we indent the child nodes of the common
            // ancestor that contains this selection
            $dom = $(ancestor.tagName ? ancestor : ancestor.parentNode).children();
        }

        // if selection is inside indented contents and outdent is true, we can outdent this node
        var indentedContent = outdent && dom.ancestor(ancestor, function (node) {
            var style = dom.isCell(node) ? 'paddingLeft' : 'marginLeft';
            return node.tagName && !!parseFloat(node.style[style] || 0);
        });

        if (indentedContent) {
            $dom = $(indentedContent);
        } else {
            // if selection is inside a list, we indent its list items
            $dom = $(dom.ancestor(ancestor, dom.isList));
            if (!$dom.length) {
                // if the selection is contained in a single HTML node, we indent
                // the first ancestor 'content block' (P, H1, PRE, ...) or TD
                var nodes = this.context.invoke('HelperPlugin.getSelectedNodes');
                $dom = $(this._filterEditableFormatNodes(nodes));
            }
        }

        // if select tr, take the first td
        $dom = $dom.map(function () {
            return this.tagName === "TR" ? this.firstElementChild : this;
        });

        $dom.each(function () {
            if (isWithinElem || $.contains(this, range.sc)) {
                if (dom.isList(this)) {
                    if (outdent) {
                        var type = this.tagName === 'OL' ? 'ol' : (this.className && this.className.indexOf('o_checklist') !== -1 ? 'checklist' : 'ul');
                        isWithinElem = self._convertList(isWithinElem, nodes, range.getStartPoint(), range.getEndPoint(), type);
                    } else {
                        isWithinElem = self._indentUL(isWithinElem, nodes, this, range.sc, range.ec);
                    }
                } else if (self.context.invoke('HelperPlugin.isFormatNode', this) || dom.ancestor(this, dom.isCell)) {
                    isWithinElem = self._indentFormatNode(outdent, isWithinElem, nodes, this, range.sc, range.ec);
                }
            }
        });

        if ($dom.parent().length) {
            var $parent = $dom.parent();

            // remove text nodes between lists
            var $ul = $parent.find('ul, ol');
            if (!$ul.length) {
                $ul = $(dom.ancestor(range.sc, dom.isList));
            }
            $ul.each(function () {
                var notWhitespace = /\S/;
                if (
                    this.previousSibling &&
                    this.previousSibling !== this.previousElementSibling &&
                    !this.previousSibling.textContent.match(notWhitespace)
                ) {
                    this.parentNode.removeChild(this.previousSibling);
                }
                if (
                    this.nextSibling &&
                    this.nextSibling !== this.nextElementSibling &&
                    !this.nextSibling.textContent.match(notWhitespace)
                ) {
                    this.parentNode.removeChild(this.nextSibling);
                }
            });

            // merge same ul or ol
            $ul.prev('ul, ol').each(function () {
                self.context.invoke('HelperPlugin.deleteEdge', this, 'next');
            });

        }

        range.normalize().select();
        this.context.invoke('editor.saveRange');

        return !!nodes.length && nodes;
    },
    /**
     * Indent several LIs in a list.
     *
     * @param {bool} isWithinElem true if selection already inside the LI
     * @param {Node[]} nodes
     * @param {Node} UL
     * @param {Node} start
     * @param {Node} end
     * @returns {bool} isWithinElem
     */
    _indentUL: function (isWithinElem, nodes, UL, start, end) {
        var next;
        var tagName = UL.tagName;
        var node = UL.firstChild;
        var ul = document.createElement(tagName);
        ul.className = UL.className;
        var flag;

        if (isWithinElem) {
            flag = true;
        }

        // create and fill ul into a li
        while (node) {
            if (flag || node === start || $.contains(node, start)) {
                isWithinElem = true;
                node.parentNode.insertBefore(ul, node);
            }
            next = node.nextElementSibling;
            if (isWithinElem) {
                ul.appendChild(node);
                nodes.push(node);
            }
            if (node === end || $.contains(node, end)) {
                isWithinElem = false;
                break;
            }
            node = next;
        }

        var temp;
        var prev = ul.previousElementSibling;
        if (
            prev && prev.tagName === "LI" &&
            (temp = prev.firstElementChild) && temp.tagName === tagName &&
            ((prev.firstElementChild || prev.firstChild) !== ul)
        ) {
            $(prev.firstElementChild || prev.firstChild).append($(ul).contents());
            $(ul).remove();
            ul = prev;
            ul.parentNode.removeChild(ul.nextElementSibling);
        }
        next = ul.nextElementSibling;
        if (
            next && next.tagName === "LI" &&
            (temp = next.firstElementChild) && temp.tagName === tagName &&
            (ul.firstElementChild !== next.firstElementChild)
        ) {
            $(ul.firstElementChild).append($(next.firstElementChild).contents());
            $(next.firstElementChild).remove();
            ul.parentNode.removeChild(ul.nextElementSibling);
        }

        // wrap in li
        var li = this.document.createElement('li');
        li.className = 'o_indent';
        $(ul).before(li);
        li.appendChild(ul);

        return isWithinElem;
    },
    /**
     * Outdent a container node.
     *
     * @param {Node} node
     * @returns {float} margin
     */
    _outdentContainer: function (node) {
        var style = dom.isCell(node) ? 'paddingLeft' : 'marginLeft';
        var margin = parseFloat(node.style[style] || 0) - 1.5;
        node.style[style] = margin > 0 ? margin + "em" : "";
        return margin;
    },
    /**
     * Indent a container node.
     *
     * @param {Node} node
     * @returns {float} margin
     */
    _indentContainer: function (node) {
        var style = dom.isCell(node) ? 'paddingLeft' : 'marginLeft';
        var margin = parseFloat(node.style[style] || 0) + 1.5;
        node.style[style] = margin + "em";
        return margin;
    },
    /**
     * Indent/outdent a format node.
     *
     * @param {bool} outdent true to outdent, false to indent
     * @param {bool} isWithinElem true if selection already inside the element
     * @param {DOM[]} nodes
     * @param {DOM} p
     * @param {DOM} start
     * @param {DOM} end
     * @returns {bool} isWithinElem
     */
    _indentFormatNode: function (outdent, isWithinElem, nodes, p, start, end) {
        if (p === start || $.contains(p, start) || $.contains(start, p)) {
            isWithinElem = true;
        }
        if (isWithinElem) {
            nodes.push(p);
            if (outdent) {
                this._outdentContainer(p);
            } else {
                this._indentContainer(p);
            }
        }
        if (p === end || $.contains(p, end) || $.contains(end, p)) {
            isWithinElem = false;
        }
        return isWithinElem;
    },

    //--------------------------------------------------------------------------
    // Handle
    //--------------------------------------------------------------------------

    /**
     * @param {SummernoteEvent} se
     * @param {jQueryEvent} e
     */
    _onMouseDown: function (se, e) {
        if (!dom.isLi(e.target) || !$(e.target).parent('ul.o_checklist').length || e.offsetX > 0) {
            return;
        }
        e.preventDefault();
        var checked = $(e.target).hasClass('o_checked');
        $(e.target).toggleClass('o_checked', !checked);
        var $sublevel = $(e.target).next('ul.o_checklist, li:has(> ul.o_checklist)').find('> li, ul.o_checklist > li');
        var $parents = $(e.target).parents('ul.o_checklist').map(function () {
            return this.parentNode.tagName === 'LI' ? this.parentNode : this;
        });
        if (checked) {
            $sublevel.removeClass('o_checked');
            $parents.prev('ul.o_checklist li').removeClass('o_checked');
        } else {
            $sublevel.addClass('o_checked');
            var $lis;
            do {
                $lis = $parents.not(':has(li:not(.o_checked))').prev('ul.o_checklist li:not(.o_checked)');
                $lis.addClass('o_checked');
            } while ($lis.length);
        }
    },
});

registry.add('BulletPlugin', BulletPlugin);

return BulletPlugin;

});
