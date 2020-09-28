odoo.define('web_editor.summernote', function (require) {
'use strict';

var core = require('web.core');
require('summernote/summernote'); // wait that summernote is loaded
var weDefaultOptions = require('web_editor.wysiwyg.default_options');

var _t = core._t;

// Summernote Lib (neek hack to make accessible: method and object)
// var agent = $.summernote.core.agent;
var dom = $.summernote.core.dom;
var range = $.summernote.core.range;
var list = $.summernote.core.list;
var key = $.summernote.core.key;
var eventHandler = $.summernote.eventHandler;
var editor = eventHandler.modules.editor;
var renderer = $.summernote.renderer;
var options = $.summernote.options;

// Browser-unify execCommand
var oldJustify = {};
_.each(['Left', 'Right', 'Full', 'Center'], function (align) {
    oldJustify[align] = editor['justify' + align];
    editor['justify' + align] = function ($editable, value) {
        // Before calling the standard function, check all elements which have
        // an 'align' attribute and mark them with their value
        var $align = $editable.find('[align]');
        _.each($align, function (el) {
            var $el = $(el);
            $el.data('__align', $el.attr('align'));
        });

        // Call the standard function
        oldJustify[align].apply(this, arguments);

        // Then:

        // Remove the text-align of elements which lost the 'align' attribute
        var $newAlign = $editable.find('[align]');
        $align.not($newAlign).css('text-align', '');

        // Transform the 'align' attribute into the 'text-align' css
        // property for elements which received the 'align' attribute or whose
        // 'align' attribute changed
        _.each($newAlign, function (el) {
            var $el = $(el);

            var oldAlignValue = $align.data('__align');
            var alignValue = $el.attr('align');
            if (oldAlignValue === alignValue) {
                // If the element already had an 'align' attribute and that it
                // did not changed, do nothing (compatibility)
                return;
            }

            $el.removeAttr('align');
            $el.css('text-align', alignValue);

            // Note the first step (removing the text-align of elemnts which
            // lost the 'align' attribute) is kinda the same as this one, but
            // this one handles the elements which have been edited with chrome
            // or with this new system
            $el.find('*').css('text-align', '');
        });

        // Unmark the elements
        $align.removeData('__align');
    };
});


// Add methods to summernote

dom.hasContentAfter = function (node) {
    var next;
    if (dom.isEditable(node)) return;
    while (node.nextSibling) {
        next = node.nextSibling;
        if (next.tagName || dom.isVisibleText(next) || dom.isBR(next)) return next;
        node = next;
    }
};
dom.hasContentBefore = function (node) {
    var prev;
    if (dom.isEditable(node)) return;
    while (node.previousSibling) {
        prev = node.previousSibling;
        if (prev.tagName || dom.isVisibleText(prev) || dom.isBR(prev)) return prev;
        node = prev;
    }
};
dom.ancestorHaveNextSibling = function (node, pred) {
    pred = pred || dom.hasContentAfter;
    while (!dom.isEditable(node) && (!node.nextSibling || !pred(node))) { node = node.parentNode; }
    return node;
};
dom.ancestorHavePreviousSibling = function (node, pred) {
    pred = pred || dom.hasContentBefore;
    while (!dom.isEditable(node) && (!node.previousSibling || !pred(node))) { node = node.parentNode; }
    return node;
};
dom.nextElementSibling = function (node) {
    while (node) {
        node = node.nextSibling;
        if (node && node.tagName) {
            break;
        }
    }
    return node;
};
dom.previousElementSibling = function (node) {
    while (node) {
        node = node.previousSibling;
        if (node && node.tagName) {
            break;
        }
    }
    return node;
};
dom.lastChild = function (node) {
    while (node.lastChild) { node = node.lastChild; }
    return node;
};
dom.firstChild = function (node) {
    while (node.firstChild) { node = node.firstChild; }
    return node;
};
dom.lastElementChild = function (node, deep) {
    node = deep ? dom.lastChild(node) : node.lastChild;
    return !node || node.tagName ? node : dom.previousElementSibling(node);
};
dom.firstElementChild = function (node, deep) {
    node = deep ? dom.firstChild(node) : node.firstChild;
    return !node || node.tagName ? node : dom.nextElementSibling(node);
};
dom.isEqual = function (prev, cur) {
    if (prev.tagName !== cur.tagName) {
        return false;
    }
    if ((prev.attributes ? prev.attributes.length : 0) !== (cur.attributes ? cur.attributes.length : 0)) {
        return false;
    }

    function strip(text) {
        return text && text.replace(/^\s+|\s+$/g, '').replace(/\s+/g, ' ');
    }
    var att, att2;
    loop_prev:
    for (var a in prev.attributes) {
        att = prev.attributes[a];
        for (var b in cur.attributes) {
            att2 = cur.attributes[b];
            if (att.name === att2.name) {
                if (strip(att.value) !== strip(att2.value)) return false;
                continue loop_prev;
            }
        }
        return false;
    }
    return true;
};
dom.hasOnlyStyle = function (node) {
    for (var i = 0; i < node.attributes.length; i++) {
        var attr = node.attributes[i];
        if (attr.attributeName !== 'style') {
            return false;
        }
    }
    return true;
};
dom.hasProgrammaticStyle = function (node) {
    var styles = ["float", "display", "position", "top", "left", "right", "bottom"];
    for (var i = 0; i < node.style.length; i++) {
      var style = node.style[i];
      if (styles.indexOf(style) !== -1) {
          return true;
      }
    }
    return false;
};
dom.mergeFilter = function (prev, cur, parent) {
    // merge text nodes
    if (prev && (dom.isText(prev) || (['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'LI', 'P'].indexOf(prev.tagName) !== -1 && prev !== cur.parentNode)) && dom.isText(cur)) {
        return true;
    }
    if (prev && prev.tagName === "P" && dom.isText(cur)) {
        return true;
    }
    if (prev && dom.isText(cur) && !dom.isVisibleText(cur) && (dom.isText(prev) || dom.isVisibleText(prev))) {
        return true;
    }
    if (prev && !dom.isBR(prev) && dom.isEqual(prev, cur) &&
        ((prev.tagName && dom.getComputedStyle(prev).display === "inline" &&
          cur.tagName && dom.getComputedStyle(cur).display === "inline"))) {
        return true;
    }
    if (dom.isEqual(parent, cur) &&
        ((parent.tagName && dom.getComputedStyle(parent).display === "inline" &&
          cur.tagName && dom.getComputedStyle(cur).display === "inline"))) {
        return true;
    }
    if (parent && cur.tagName === "FONT" && (!cur.firstChild || (!cur.attributes.getNamedItem('style') && !cur.className.length))) {
        return true;
    }
    // On backspace, webkit browsers create a <span> with a bunch of
    // inline styles "remembering" where they come from.
    // chances are we had e.g.
    //  <p>foo</p>
    //  <p>bar</p>
    // merged the lines getting this in webkit
    //  <p>foo<span>bar</span></p>
    if (parent && cur.tagName === "SPAN" && dom.hasOnlyStyle(cur) && !dom.hasProgrammaticStyle(cur)) {
        return true;
    }
};
dom.doMerge = function (prev, cur) {
    if (prev.tagName) {
        if (prev.childNodes.length && !prev.textContent.match(/\S/) && dom.firstElementChild(prev) && dom.isBR(dom.firstElementChild(prev))) {
            prev.removeChild(dom.firstElementChild(prev));
        }
        if (cur.tagName) {
            while (cur.firstChild) {
                prev.appendChild(cur.firstChild);
            }
            cur.parentNode.removeChild(cur);
        } else {
            prev.appendChild(cur);
        }
    } else {
        if (cur.tagName) {
            var deep = cur;
            while (deep.tagName && deep.firstChild) {deep = deep.firstChild;}
            prev.appendData(deep.textContent);
            cur.parentNode.removeChild(cur);
        } else {
            prev.appendData(cur.textContent);
            cur.parentNode.removeChild(cur);
        }
    }
};
dom.merge = function (node, begin, so, end, eo, mergeFilter, all) {
    mergeFilter = mergeFilter || dom.mergeFilter;
    var _merged = false;
    var add = all || false;

    if (!begin) {
        begin = node;
        while (begin.firstChild) {begin = begin.firstChild;}
        so = 0;
    } else if (begin.tagName && begin.childNodes[so]) {
        begin = begin.childNodes[so];
        so = 0;
    }
    if (!end) {
        end = node;
        while (end.lastChild) {end = end.lastChild;}
        eo = end.textContent.length-1;
    } else if (end.tagName && end.childNodes[so]) {
        end = end.childNodes[so];
        so = 0;
    }

    begin = dom.firstChild(begin);
    if (dom.isText(begin) && so > begin.textContent.length) {
        so = 0;
    }
    end = dom.firstChild(end);
    if (dom.isText(end) && eo > end.textContent.length) {
        eo = 0;
    }

    function __merge(node) {
        var merged = false;
        var prev;
        for (var k=0; k<node.childNodes.length; k++) {
            var cur = node.childNodes[k];

            if (cur === begin) {
                if (!all) add = true;
            }

            __merge(cur);
            dom.orderClass(dom.node(cur));

            if (!add || !cur) continue;
            if (cur === end) {
                if (!all) add = false;
            }

            // create the first prev value
            if (!prev) {
                if (mergeFilter.call(dom, prev, cur, node)) {
                    prev = prev || cur.previousSibling;
                    dom.moveTo(cur, cur.parentNode, cur);
                    k--;
                } else {
                    prev = cur;
                }
                continue;
            } else if (mergeFilter.call(dom, null, cur, node)) { // merge with parent
                prev = prev || cur.previousSibling;
                dom.moveTo(cur, cur.parentNode, cur);
                k--;
                continue;
            }

            // merge nodes
            if (mergeFilter.call(dom, prev, cur, node)) {
                var p = prev;
                var c = cur;
                // compute prev/end and offset
                if (prev.tagName) {
                    if (cur.tagName) {
                        if (cur === begin) begin = prev;
                        if (cur === end) end = prev;
                    }
                } else {
                    if (cur.tagName) {
                        var deep = cur;
                        while (deep.tagName && deep.lastChild) {deep = deep.lastChild;}
                        if (deep === begin) {
                            so += prev.textContent.length;
                            begin = prev;
                        }
                        if (deep === end) {
                            eo += prev.textContent.length;
                            end = prev;
                        }
                    } else {
                        // merge text nodes
                        if (cur === begin) {
                            so += prev.textContent.length;
                            begin = prev;
                        }
                        if (cur === end) {
                            eo += prev.textContent.length;
                            end = prev;
                        }
                    }
                }

                dom.doMerge(p, c);

                merged = true;
                k--;
                continue;
            }

            prev = cur;
        }

        // an other loop to merge the new shibbing nodes
        if (merged) {
            _merged = true;
            __merge(node);
        }
    }
    if (node) {
        __merge(node);
    }

    return {
        merged: _merged,
        sc: begin,
        ec: end,
        so: so,
        eo: eo
    };
};
dom.autoMerge = function (target, previous) {
    var node = dom.lastChild(target);
    var nodes = [];
    var temp;

    while (node) {
        nodes.push(node);
        temp = (previous ? dom.hasContentBefore(node) : dom.hasContentAfter(node));
        if (temp) {
            if (!dom.isText(node) && !dom.isMergable(node) && temp.tagName !== node.tagName) {
                nodes = [];
            }
            break;
        }
        node = node.parentNode;
    }

    while (nodes.length) {
        node = nodes.pop();
        if (node && (temp = (previous ? dom.hasContentBefore(node) : dom.hasContentAfter(node))) &&
            temp.tagName === node.tagName &&
            !dom.isText(node) &&
            dom.isMergable(node) &&
            !dom.isNotBreakable(node) && !dom.isNotBreakable(previous ? dom.previousElementSibling(node) : dom.nextElementSibling(node))) {

            if (previous) {
                dom.doMerge(temp, node);
            } else {
                dom.doMerge(node, temp);
            }
        }
    }
};
dom.removeSpace = function (node, begin, so, end, eo) {
    var removed = false;
    var add = node === begin;

    if (node === begin && begin === end && dom.isBR(node)) {
        return {
            removed: removed,
            sc: begin,
            ec: end,
            so: so,
            eo: eo
        };
    }

    (function __remove_space(node) {
        if (!node) return;
        var t_begin, t_end;
        for (var k=0; k<node.childNodes.length; k++) {
            var cur = node.childNodes[k];

            if (cur === begin) add = true;

            if (cur.tagName && cur.tagName !== "SCRIPT" && cur.tagName !== "STYLE" && dom.getComputedStyle(cur).whiteSpace !== "pre") {
                __remove_space(cur);
            }

            if (!add) continue;
            if (cur === end) add = false;

            // remove begin empty text node
            if (node.childNodes.length > 1 && dom.isText(cur) && !dom.isVisibleText(cur)) {
                removed = true;
                if (cur === begin) {
                        t_begin = dom.hasContentBefore(dom.ancestorHavePreviousSibling(cur));
                        if (t_begin) {
                            so = 0;
                            begin = dom.lastChild(t_begin);
                        }
                }
                if (cur === end) {
                        t_end = dom.hasContentAfter(dom.ancestorHaveNextSibling(cur));
                        if (t_end) {
                            eo = 1;
                            end = dom.firstChild(t_end);
                            if (dom.isText(end)) {
                                eo = end.textContent.length;
                            }
                    }
                }
                cur.parentNode.removeChild(cur);
                begin = dom.lastChild(begin);
                end = dom.lastChild(end);
                k--;
                continue;
            }

            // convert HTML space
            if (dom.isText(cur)) {
                var text;
                var temp;
                var _temp;
                var exp1 = /[\t\n\r ]+/g;
                var exp2 = /(?!([ ]|\u00A0)|^)\u00A0(?!([ ]|\u00A0)|$)/g;
                if (cur === begin) {
                    temp = cur.textContent.substr(0, so);
                    _temp = temp.replace(exp1, ' ').replace(exp2, ' ');
                    so -= temp.length - _temp.length;
                }
                if (cur === end) {
                    temp = cur.textContent.substr(0, eo);
                    _temp = temp.replace(exp1, ' ').replace(exp2, ' ');
                    eo -= temp.length - _temp.length;
                }
                text = cur.textContent.replace(exp1, ' ').replace(exp2, ' ');
                removed = removed || cur.textContent.length !== text.length;
                cur.textContent = text;
            }
        }
    })(node);

    return {
        removed: removed,
        sc: begin,
        ec: end,
        so: !dom.isBR(begin) && so > 0 ? so : 0,
        eo: dom.isBR(end) ? 0 : eo
    };
};
dom.removeBetween = function (sc, so, ec, eo, towrite) {
    var text;
    if (ec.tagName) {
        if (ec.childNodes[eo]) {
            ec = ec.childNodes[eo];
            eo = 0;
        } else {
            ec = dom.lastChild(ec);
            eo = dom.nodeLength(ec);
        }
    }
    if (sc.tagName) {
        sc = sc.childNodes[so] || dom.firstChild(ec);
        so = 0;
        if (!dom.hasContentBefore(sc) && towrite) {
            sc.parentNode.insertBefore(document.createTextNode('\u00A0'), sc);
        }
    }
    if (!eo && sc !== ec) {
        ec = dom.lastChild(dom.hasContentBefore(dom.ancestorHavePreviousSibling(ec)) || ec);
        eo = ec.textContent.length;
    }

    var ancestor = dom.commonAncestor(sc.tagName ? sc.parentNode : sc, ec.tagName ? ec.parentNode : ec) || dom.ancestor(sc, dom.isEditable);

    if (!dom.isContentEditable(ancestor)) {
        return {
            sc: sc,
            so: so,
            ec: sc,
            eo: eo
        };
    }

    if (ancestor.tagName) {
        var ancestor_sc = sc;
        var ancestor_ec = ec;
        while (ancestor !== ancestor_sc && ancestor !== ancestor_sc.parentNode) { ancestor_sc = ancestor_sc.parentNode; }
        while (ancestor !== ancestor_ec && ancestor !== ancestor_ec.parentNode) { ancestor_ec = ancestor_ec.parentNode; }


        var node = dom.node(sc);
        if (!dom.isNotBreakable(node) && !dom.isVoid(sc)) {
            sc = dom.splitTree(ancestor_sc, {'node': sc, 'offset': so});
        }
        var before = dom.hasContentBefore(dom.ancestorHavePreviousSibling(sc));

        var after;
        if (ec.textContent.slice(eo, Infinity).match(/\S|\u00A0/)) {
            after = dom.splitTree(ancestor_ec, {'node': ec, 'offset': eo});
        } else {
            after = dom.hasContentAfter(dom.ancestorHaveNextSibling(ec));
        }

        var nodes = dom.listBetween(sc, ec);

        var ancestor_first_last = function (node) {
            return node === before || node === after;
        };

        for (var i=0; i<nodes.length; i++) {
            if (!dom.ancestor(nodes[i], ancestor_first_last) && !$.contains(nodes[i], before) && !$.contains(nodes[i], after) && !dom.isEditable(nodes[i])) {
                nodes[i].parentNode.removeChild(nodes[i]);
            }
        }

        if (dom.listAncestor(after).length  <= dom.listAncestor(before).length) {
            sc = dom.lastChild(before || ancestor);
            so = dom.nodeLength(sc);
        } else {
            sc = dom.firstChild(after);
            so = 0;
        }

        if (dom.isVoid(node)) {
            // we don't need to append a br
        } else if (towrite && !node.firstChild && node.parentNode && !dom.isNotBreakable(node)) {
            var br = $("<br/>")[0];
            node.appendChild(sc);
            sc = br;
            so = 0;
        } else if (!ancestor.children.length && !ancestor.textContent.match(/\S|\u00A0/)) {
            sc = $("<br/>")[0];
            so = 0;
            $(ancestor).prepend(sc);
        } else if (dom.isText(sc)) {
            text = sc.textContent.replace(/[ \t\n\r]+$/, '\u00A0');
            so = Math.min(so, text.length);
            sc.textContent = text;
        }
    } else {
        text = ancestor.textContent;
        ancestor.textContent = text.slice(0, so) + text.slice(eo, Infinity).replace(/^[ \t\n\r]+/, '\u00A0');
    }

    eo = so;
    if (!dom.isBR(sc) && !dom.isVisibleText(sc) && !dom.isText(dom.hasContentBefore(sc)) && !dom.isText(dom.hasContentAfter(sc))) {
        ancestor = dom.node(sc);
        text = document.createTextNode('\u00A0');
        $(sc).before(text);
        sc = text;
        so = 0;
        eo = 1;
    }

    var parentNode = sc && sc.parentNode;
    if (parentNode && sc.tagName === 'BR') {
        sc = parentNode;
        ec = parentNode;
    }

    return {
        sc: sc,
        so: so,
        ec: sc,
        eo: eo
    };
};
dom.indent = function (node) {
    var style = dom.isCell(node) ? 'paddingLeft' : 'marginLeft';
    var margin = parseFloat(node.style[style] || 0)+1.5;
    node.style[style] = margin + "em";
    return margin;
};
dom.outdent = function (node) {
    var style = dom.isCell(node) ? 'paddingLeft' : 'marginLeft';
    var margin = parseFloat(node.style[style] || 0)-1.5;
    node.style[style] = margin > 0 ? margin + "em" : "";
    return margin;
};
dom.scrollIntoViewIfNeeded = function (node) {
    node = dom.node(node);

    var $span;
    if (dom.isBR(node)) {
        $span = $('<span/>').text('\u00A0');
        $(node).after($span);
        node = $span[0];
    }

    if (node.scrollIntoViewIfNeeded) {
        node.scrollIntoViewIfNeeded(false);
    } else {
        var offsetParent = node.offsetParent;
        while (offsetParent) {
            var elY = 0;
            var elH = node.offsetHeight;
            var parent = node;

            while (offsetParent && parent) {
                elY += node.offsetTop;

                // get if a parent have a scrollbar
                parent = node.parentNode;
                while (parent !== offsetParent &&
                    (parent.tagName === "BODY" || ["auto", "scroll"].indexOf(dom.getComputedStyle(parent).overflowY) === -1)) {
                    parent = parent.parentNode;
                }
                node = parent;

                if (parent !== offsetParent) {
                    elY -= parent.offsetTop;
                    parent = null;
                }

                offsetParent = node.offsetParent;
            }

            if ((node.tagName === "BODY" || ["auto", "scroll"].indexOf(dom.getComputedStyle(node).overflowY) !== -1) &&
                (node.scrollTop + node.clientHeight) < (elY + elH)) {
                node.scrollTop = (elY + elH) - node.clientHeight;
            }
        }
    }

    if ($span) {
        $span.remove();
    }

    return;
};
dom.moveTo = function (node, target, before) {
    var nodes = [];
    while (node.firstChild) {
        nodes.push(node.firstChild);
        if (before) {
            target.insertBefore(node.firstChild, before);
        } else {
            target.appendChild(node.firstChild);
        }
    }
    node.parentNode.removeChild(node);
    return nodes;
};
dom.isMergable = function (node) {
    return node.tagName && "h1 h2 h3 h4 h5 h6 p b bold i u code sup strong small li a ul ol font".indexOf(node.tagName.toLowerCase()) !== -1;
};
dom.isSplitable = function (node) {
    return node.tagName && "h1 h2 h3 h4 h5 h6 p b bold i u code sup strong small li a font".indexOf(node.tagName.toLowerCase()) !== -1;
};
dom.isRemovableEmptyNode = function (node) {
    return "h1 h2 h3 h4 h5 h6 p b bold i u code sup strong small li a ul ol font span br".indexOf(node.tagName.toLowerCase()) !== -1;
};
dom.isForbiddenNode = function (node) {
    return node.tagName === "BR" || $(node).is(".fa, img");
};
/**
 * @todo 'so' and 'eo' were added as a bugfix and are not given everytime. They
 * however should be as the function may be wrong without them (for example,
 * when asking the list between an element and its parent, as there is no path
 * from the beginning of the former to the beginning of the later).
 */
dom.listBetween = function (sc, ec, so, eo) {
    var nodes = [];
    var ancestor = dom.commonAncestor(sc, ec);
    dom.walkPoint({'node': sc, 'offset': so || 0}, {'node': ec, 'offset': eo || 0}, function (point) {
        if (ancestor !== point.node || ancestor === sc || ancestor === ec) {
            nodes.push(point.node);
        }
    });
    return list.unique(nodes);
};
dom.isNotBreakable = function (node) {
    // avoid triple click => crappy dom
    return !dom.isText(node) && !dom.isBR(dom.firstChild(node)) && dom.isVoid(dom.firstChild(node));
};
dom.isContentEditable = function (node) {
    return $(node).closest('[contenteditable]').prop('contenteditable') === 'true';
};
dom.isContentEditableFalse = function (node) {
    return $(node).closest('[contenteditable]').prop('contenteditable') === 'false';
};
dom.isFont = function (node) {
    var nodeName = node && node.nodeName.toUpperCase();
    return node && (nodeName === "FONT" ||
        (nodeName === "SPAN" && (
            node.className.match(/(^|\s)fa(\s|$)/i) ||
            node.className.match(/(^|\s)(text|bg)-/i) ||
            (node.attributes.style && node.attributes.style.value.match(/(^|\s)(color|background-color|font-size):/i)))) );
};
dom.isVisibleText = function (textNode) {
  return !!textNode.textContent.match(/\S|\u00A0/);
};
var old_isVisiblePoint = dom.isVisiblePoint;
dom.isVisiblePoint = function (point) {
  return point.node.nodeType !== 8 && old_isVisiblePoint.apply(this, arguments);
};
dom.orderStyle = function (node) {
  var style = node.getAttribute('style');
  if (!style) return null;
  style = style.replace(/[\s\n\r]+/, ' ').replace(/^ ?;? ?| ?;? ?$/g, '').replace(/ ?; ?/g, ';');
  if (!style.length) {
      node.removeAttribute("style");
      return null;
  }
  style = style.split(";");
  style.sort();
  style = style.join("; ")+";";
  node.setAttribute('style', style);
  return style;
};
dom.orderClass = function (node) {
    var className = node.getAttribute && node.getAttribute('class');
    if (!className) return null;
    className = className.replace(/[\s\n\r]+/, ' ').replace(/^ | $/g, '').replace(/ +/g, ' ');
    if (!className.length) {
        node.removeAttribute("class");
        return null;
    }
    className = className.split(" ");
    className.sort();
    className = className.join(" ");
    node.setAttribute('class', className);
    return className;
};
dom.node = function (node) {
    return dom.isText(node) ? node.parentNode : node;
};
dom.moveContent = function (from, to) {
  if (from === to) {
    return;
  }
  if (from.parentNode === to) {
    while (from.lastChild) {
      dom.insertAfter(from.lastChild, from);
    }
  } else {
    while (from.firstChild && from.firstChild !== to) {
      to.appendChild(from.firstChild);
    }
  }
};
dom.getComputedStyle = function (node) {
    return node.nodeType === Node.COMMENT_NODE ? {} : window.getComputedStyle(node);
};

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

range.WrappedRange.prototype.reRange = function (keep_end, isNotBreakable) {
    var sc = this.sc;
    var so = this.so;
    var ec = this.ec;
    var eo = this.eo;
    isNotBreakable = isNotBreakable || dom.isNotBreakable;

    // search the first snippet editable node
    var start = keep_end ? ec : sc;
    while (start) {
        if (isNotBreakable(start, sc, so, ec, eo)) {
            break;
        }
        start = start.parentNode;
    }

    // check if the end caret have the same node
    var lastFilterEnd;
    var end = keep_end ? sc : ec;
    while (end) {
        if (start === end) {
            break;
        }
        if (isNotBreakable(end, sc, so, ec, eo)) {
            lastFilterEnd = end;
        }
        end = end.parentNode;
    }
    if (lastFilterEnd) {
        end = lastFilterEnd;
    }
    if (!end) {
        end = document.getElementsByTagName('body')[0];
    }

    // if same node, keep range
    if (start === end || !start) {
        return this;
    }

    // reduce or extend the range to don't break a isNotBreakable area
    if ($.contains(start, end)) {

        if (keep_end) {
                sc = dom.lastChild(dom.hasContentBefore(dom.ancestorHavePreviousSibling(end)) || sc);
            so = sc.textContent.length;
        } else if (!eo) {
                ec = dom.lastChild(dom.hasContentBefore(dom.ancestorHavePreviousSibling(end)) || ec);
            eo = ec.textContent.length;
        } else {
                ec = dom.firstChild(dom.hasContentAfter(dom.ancestorHaveNextSibling(end)) || ec);
            eo = 0;
        }
    } else {

        if (keep_end) {
            sc = dom.firstChild(start);
            so = 0;
        } else {
            ec = dom.lastChild(start);
            eo = ec.textContent.length;
        }
    }

    return new range.WrappedRange(sc, so, ec, eo);
};
/**
 * Returns the image the range is in or matches (if any, false otherwise).
 *
 * @todo this implementation may not cover all corner cases but should do the
 * trick for all reproductible ones
 * @returns {DOMElement|boolean}
 */
range.WrappedRange.prototype.isOnImg = function () {
    // If not a selection but a cursor position, just check if a point's
    // ancestor is an image or not
    if (this.sc === this.ec && this.so === this.eo) {
        return dom.ancestor(this.sc, dom.isImg);
    }

    var startPoint = {node: this.sc, offset: this.so};
    var endPoint = {node: this.ec, offset: this.eo};

    var nb = 0;
    var image;
    var textNode;
    dom.walkPoint(startPoint, endPoint, function (point) {
        // If the element has children (not a text node and not empty node),
        // the element cannot be considered as selected (these children will
        // be processed to determine that)
        if (dom.hasChildren(point.node)) {
            return;
        }

        // Check if an ancestor of the current point is an image
        var pointImg = dom.ancestor(point.node, dom.isImg);
        var isText = dom.isText(point.node);

        // Check if a visible element is selected, i.e.
        // - If an ancestor of the current is an image we did not see yet
        // - If the point is not in a br or a text (so a node with no children)
        // - If the point is in a non empty text node we already saw
        if (pointImg ?
            (image !== pointImg) :
            ((!dom.isBR(point.node) && !isText) || (textNode === point.node && point.node.textContent.match(/\S|\u00A0/)))) {
            nb++;
        }

        // If an ancestor of the current point is an image, then save it as the
        // image we are looking for
        if (pointImg) {
            image = pointImg;
        }
        // If the current point is a text node save it as the last text node
        // seen (if we see it again, this might mean it is selected)
        if (isText) {
            textNode = point.node;
        }
    });

    return nb === 1 && image;
};
range.WrappedRange.prototype.deleteContents = function (towrite) {
    if (this.sc === this.ec && this.so === this.eo) {
        return this;
    }

    var r;
    var image = this.isOnImg();
    if (image) {
        // If the range matches/is in an image, then the image is to be removed
        // and the cursor moved to its previous position
        var parentNode = image.parentNode;
        var index = _.indexOf(parentNode.childNodes, image);
        parentNode.removeChild(image);
        r = new range.WrappedRange(parentNode, index, parentNode, index);
    } else {
        r = dom.removeBetween(this.sc, this.so, this.ec, this.eo, towrite);
    }

    $(dom.node(r.sc)).trigger("click"); // trigger click to disable and reanable editor and image handler
    return new range.WrappedRange(r.sc, r.so, r.ec, r.eo);
};
range.WrappedRange.prototype.clean = function (mergeFilter, all) {
    var node = dom.node(this.sc === this.ec ? this.sc : this.commonAncestor());
        node = node || $(this.sc).closest('[contenteditable]')[0];
    if (node.childNodes.length <=1) {
        return this;
    }

    var merge = dom.merge(node, this.sc, this.so, this.ec, this.eo, mergeFilter, all);
    var rem = dom.removeSpace(node.parentNode, merge.sc, merge.so, merge.ec, merge.eo);

    if (merge.merged || rem.removed) {
        return range.create(rem.sc, rem.so, rem.ec, rem.eo);
    }
    return this;
};
range.WrappedRange.prototype.remove = function (mergeFilter) {
};
range.WrappedRange.prototype.isOnCellFirst = function () {
    var node = dom.ancestor(this.sc, function (node) {return ["LI", "DIV", "TD","TH"].indexOf(node.tagName) !== -1;});
    return node && ["TD","TH"].indexOf(node.tagName) !== -1;
};
range.WrappedRange.prototype.isContentEditable = function () {
    return dom.isContentEditable(this.sc) && (this.sc === this.ec || dom.isContentEditable(this.ec));
};

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

renderer.tplButtonInfo.fontsize = function (lang, options) {
    var items = options.fontSizes.reduce(function (memo, v) {
        return memo + '<a data-event="fontSize" href="#" class="dropdown-item" data-value="' + v + '">' +
                  '<i class="fa fa-check"></i> ' + v +
                '</a>';
    }, '');

    var sLabel = '<span class="note-current-fontsize">11</span>';
    return renderer.getTemplate().button(sLabel, {
        title: lang.font.size,
        dropdown: '<div class="dropdown-menu">' + items + '</div>'
    });
};

renderer.tplButtonInfo.color = function (lang, options) {
    var foreColorButtonLabel = '<i class="' + options.iconPrefix + options.icons.color.recent + '"></i>';
    var backColorButtonLabel = '<i class="' + options.iconPrefix + 'paint-brush"></i>';
    // TODO Remove recent color button if possible.
    // It is still put to avoid JS errors when clicking other buttons as the
    // editor still expects it to exist.
    var recentColorButton = renderer.getTemplate().button(foreColorButtonLabel, {
        className: 'note-recent-color d-none',
        title: lang.color.foreground,
        event: 'color',
        value: '{"backColor":"#B35E9B"}'
    });
    var foreColorButton = renderer.getTemplate().button(foreColorButtonLabel, {
        className: 'note-fore-color-preview',
        title: lang.color.foreground,
        dropdown: renderer.getTemplate().dropdown('<li><div data-event-name="foreColor" class="colorPalette"/></li>'),
    });
    var backColorButton = renderer.getTemplate().button(backColorButtonLabel, {
        className: 'note-back-color-preview',
        title: lang.color.background,
        dropdown: renderer.getTemplate().dropdown('<li><div data-event-name="backColor" class="colorPalette"/></li>'),
    });
    return recentColorButton + foreColorButton + backColorButton;
};

renderer.tplButtonInfo.checklist = function (lang, options) {
    return '<button ' +
            'type="button" ' +
            'class="btn btn-secondary btn-sm" ' +
            'title="' + _t('Checklist') + '" ' +
            'data-event="insertCheckList" ' +
            'tabindex="-1" ' +
            'data-name="ul" ' +
        '><i class="fa fa-check-square"></i></button>';
};

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

key.nameFromCode[46] = 'DELETE';
key.nameFromCode[27] = 'ESCAPE';

options.keyMap.pc['BACKSPACE'] = 'backspace';
options.keyMap.pc['DELETE'] = 'delete';
options.keyMap.pc['ENTER'] = 'enter';
options.keyMap.pc['ESCAPE'] = 'cancel';
options.keyMap.mac['SHIFT+TAB'] = 'untab';
options.keyMap.pc['UP'] = 'up';
options.keyMap.pc['DOWN'] = 'down';

options.keyMap.mac['BACKSPACE'] = 'backspace';
options.keyMap.mac['DELETE'] = 'delete';
options.keyMap.mac['ENTER'] = 'enter';
options.keyMap.mac['ESCAPE'] = 'cancel';
options.keyMap.mac['UP'] = 'up';
options.keyMap.mac['DOWN'] = 'down';

options.styleTags = weDefaultOptions.styleTags;

$.summernote.pluginEvents.insertTable = function (event, editor, layoutInfo, sDim) {
  var $editable = layoutInfo.editable();
  $editable.focus();
  var dimension = sDim.split('x');
  var r = range.create();
  if (!r) return;
  r = r.deleteContents(true);

  var table = editor.table.createTable(dimension[0], dimension[1]);
  var parent = r.sc;
  while (dom.isText(parent.parentNode) || dom.isRemovableEmptyNode(parent.parentNode)) {
    parent = parent.parentNode;
  }
  var node = dom.splitTree(parent, {'node': r.sc, 'offset': r.so}) || r.sc;
  node.parentNode.insertBefore(table, node);

  if ($(node).text() === '' || node.textContent === '\u00A0') {
    node.parentNode.removeChild(node);
  }

  editor.afterCommand($editable);
  event.preventDefault();
  return false;
};
$.summernote.pluginEvents.tab = function (event, editor, layoutInfo, outdent) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable, 'tab');
    var r = range.create();
    outdent = outdent || false;
    event.preventDefault();

    if (r && (dom.ancestor(r.sc, dom.isCell) || dom.ancestor(r.ec, dom.isCell))) {
        if (r.isCollapsed() && r.isOnCell() && r.isOnCellFirst()) {
            var td = dom.ancestor(r.sc, dom.isCell);
            if (!outdent && !dom.nextElementSibling(td) && !dom.nextElementSibling(td.parentNode)) {
                var last = dom.lastChild(td);
                range.create(last, dom.nodeLength(last), last, dom.nodeLength(last)).select();
                $.summernote.pluginEvents.enter(event, editor, layoutInfo);
            } else if (outdent && !dom.previousElementSibling(td) && !$(td.parentNode).text().match(/\S/)) {
                $.summernote.pluginEvents.backspace(event, editor, layoutInfo);
            } else {
                editor.table.tab(r, outdent);
            }
        } else {
            $.summernote.pluginEvents.indent(event, editor, layoutInfo, outdent);
        }
    } else if (r && r.isCollapsed()) {
        if (!r.sc.textContent.slice(0,r.so).match(/\S/) && r.isOnList()) {
            if (outdent) {
                $.summernote.pluginEvents.outdent(event, editor, layoutInfo);
            } else {
                $.summernote.pluginEvents.indent(event, editor, layoutInfo);
            }
        } else {
            var next;
            if (!outdent) {
                if (dom.isText(r.sc)) {
                    next = r.sc.splitText(r.so);
                } else {
                    next = document.createTextNode('');
                    $(r.sc.childNodes[r.so]).before(next);
                }
                editor.typing.insertTab($editable, r, options.tabsize);
                r = range.create(next, 0, next, 0);
                r = dom.merge(r.sc.parentNode, r.sc, r.so, r.ec, r.eo, null, true);
                range.create(r.sc, r.so, r.ec, r.eo).select();
            } else {
                r = dom.merge(r.sc.parentNode, r.sc, r.so, r.ec, r.eo, null, true);
                r = range.create(r.sc, r.so, r.ec, r.eo);
                if (r.sc.splitText) {
                    next = r.sc.splitText(r.so);
                    r.sc.textContent = r.sc.textContent.replace(/(\u00A0)+$/g, '');
                    next.textContent = next.textContent.replace(/^(\u00A0)+/g, '');
                    range.create(r.sc, r.sc.textContent.length, r.sc, r.sc.textContent.length).select();
                }
            }
        }
    }
    return false;
};
$.summernote.pluginEvents.untab = function (event, editor, layoutInfo) {
    return $.summernote.pluginEvents.tab(event, editor, layoutInfo, true);
};
$.summernote.pluginEvents.up = function (event, editor, layoutInfo) {
    var r = range.create();
    var node = dom.firstChild(r.sc.childNodes[r.so] || r.sc);
    if (!r.isOnCell()) {
        return;
    }
    // check if an ancestor between node and cell has content before
    var ancestor = dom.ancestor(node, function (ancestorNode) {
        return dom.hasContentBefore(ancestorNode) || dom.isCell(ancestorNode);
    });
    if (!dom.isCell(ancestor) && (!dom.isBR(dom.hasContentBefore(ancestor)) || !dom.isText(node) || dom.isVisibleText(node) || dom.hasContentBefore(dom.hasContentBefore(ancestor)))) {
        return;
    }
    event.preventDefault();
    var td = dom.ancestor(r.sc, dom.isCell);
    var tr = td.parentNode;
    var target = tr.previousElementSibling && tr.previousElementSibling.children[_.indexOf(tr.children, td)];
    if (!target) {
        target = (dom.ancestorHavePreviousSibling(tr) || tr).previousSibling;
    }
    if (target) {
        range.create(dom.lastChild(target), dom.lastChild(target).textContent.length).select();
    }
};
$.summernote.pluginEvents.down = function (event, editor, layoutInfo) {
    var r = range.create();
    var node = dom.firstChild(r.sc.childNodes[r.so] || r.sc);
    if (!r.isOnCell()) {
        return;
    }
    // check if an ancestor between node and cell has content after
    var ancestor = dom.ancestor(node, function (ancestorNode) {
        return dom.hasContentAfter(ancestorNode) || dom.isCell(ancestorNode);
    });
    if (!dom.isCell(ancestor) && (!dom.isBR(dom.hasContentAfter(ancestor)) || !dom.isText(node) || dom.isVisibleText(node) || dom.hasContentAfter(dom.hasContentAfter(ancestor)))) {
        return;
    }
    event.preventDefault();
    var td = dom.ancestor(r.sc, dom.isCell);
    var tr = td.parentNode;
    var target = tr.nextElementSibling && tr.nextElementSibling.children[_.indexOf(tr.children, td)];
    if (!target) {
        target = (dom.ancestorHaveNextSibling(tr) || tr).nextSibling;
    }
    if (target) {
        range.create(dom.firstChild(target), 0).select();
    }
};
$.summernote.pluginEvents.enter = function (event, editor, layoutInfo) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable, 'enter');

    var r = range.create();
    if (!r.isContentEditable()) {
        event.preventDefault();
        return false;
    }
    if (!r.isCollapsed()) {
        r = r.deleteContents();
        r.select();
    }

    var br = $("<br/>")[0];

    // set selection outside of A if range is at beginning or end
    var elem = dom.isBR(elem) ? elem.parentNode : dom.node(r.sc);
    if (elem.tagName === "A") {
        if (r.so === 0 && dom.firstChild(elem) === r.sc) {
            r.ec = r.sc = dom.hasContentBefore(elem) || $(dom.createText('')).insertBefore(elem)[0];
            r.eo = r.so = dom.nodeLength(r.sc);
            r.select();
        } else if (dom.nodeLength(r.sc) === r.so && dom.lastChild(elem) === r.sc) {
            r.ec = r.sc = dom.hasContentAfter(elem) || dom.insertAfter(dom.createText(''), elem);
            r.eo = r.so = 0;
            r.select();
        }
    }

    var node;
    var $node;
    var $clone;
    var contentBefore = r.sc.textContent.slice(0,r.so).match(/\S|\u00A0/);
    if (!contentBefore && dom.isText(r.sc)) {
        node = r.sc.previousSibling;
        while (!contentBefore && node && dom.isText(node)) {
            contentBefore = dom.isVisibleText(node);
            node = node.previousSibling;
        }
    }

    node = dom.node(r.sc);
    var exist = r.sc.childNodes[r.so] || r.sc;
    exist = dom.isVisibleText(exist) || dom.isBR(exist) ? exist : dom.hasContentAfter(exist) || (dom.hasContentBefore(exist) || exist);

    // table: add a tr
    var td = dom.ancestor(node, dom.isCell);
    if (td && !dom.nextElementSibling(node) && !dom.nextElementSibling(td) && !dom.nextElementSibling(td.parentNode) && (!dom.isText(r.sc) || !r.sc.textContent.slice(r.so).match(/\S|\u00A0/))) {
        $node = $(td.parentNode);
        $clone = $node.clone();
        $clone.children().html(dom.blank);
        $node.after($clone);
        node = dom.firstElementChild($clone[0]) || $clone[0];
        range.create(node, 0, node, 0).select();
        dom.scrollIntoViewIfNeeded(br);
        event.preventDefault();
        return false;
    }

    var last = node;
    while (node && dom.isSplitable(node) && !dom.isList(node)) {
        last = node;
        node = node.parentNode;
    }

    if (last === node && !dom.isBR(node)) {
        node = r.insertNode(br, true);
        if (isFormatNode(last.firstChild) && $(last).closest(options.styleTags.join(',')).length) {
            dom.moveContent(last.firstChild, last);
            last.removeChild(last.firstChild);
        }
        do {
            node = dom.hasContentAfter(node);
        } while (node && dom.isBR(node));

        // create an other br because the user can't see the new line with only br in a block
        if (!node && (!br.nextElementSibling || !dom.isBR(br.nextElementSibling))) {
            $(br).before($("<br/>")[0]);
        }
        node = br.nextSibling || br;
    } else if (last === node && dom.isBR(node)) {
        $(node).after(br);
        node = br;
    } else if (!r.so && r.isOnList() && !r.sc.textContent.length && !dom.ancestor(r.sc, dom.isLi).nextElementSibling) {
        // double enter on the end of a list = new line out of the list
        $('<p></p>').append(br).insertAfter(dom.ancestor(r.sc, dom.isList));
        node = br;
    } else if (dom.isBR(exist) && $(r.sc).closest('blockquote, pre').length && !dom.hasContentAfter($(exist.parentNode).closest('blockquote *, pre *').length ? exist.parentNode : exist)) {
        // double enter on the end of a blockquote & pre = new line out of the list
        $('<p></p>').append(br).insertAfter($(r.sc).closest('blockquote, pre'));
        node = br;
    } else if (dom.isEditable(dom.node(r.sc))) {
        // if we are directly in an editable, only SHIFT + ENTER should add a newline
        node = null;
    } else if (last === r.sc) {
        if (dom.isBR(last)) {
            last = last.parentNode;
        }
        $node = $(last);
        $clone = $node.clone().text("");
        $node.after($clone);
        node = dom.node(dom.firstElementChild($clone[0]) || $clone[0]);
        $(node).html(br);
        node = br;
    } else {
        node = dom.splitTree(last, {'node': r.sc, 'offset': r.so}) || r.sc;
        if (!contentBefore) {
            // dom.node chooses the parent if node is text
            var cur = dom.node(dom.lastChild(node.previousSibling));
            if (!dom.isBR(cur)) {
                // We should concat what was before with a <br>
                $(cur).html(cur.innerHTML + br.outerHTML);
            }
        }
        if (!dom.isVisibleText(node)) {
            node = dom.firstChild(node);
            $(dom.node( dom.isBR(node) ? node.parentNode : node )).html(br);
            node = br;
        }
    }

    if (node) {
        node = dom.firstChild(node);
        if (dom.isBR(node)) {
            range.createFromNode(node).select();
        } else {
            range.create(node,0).select();
        }
        dom.scrollIntoViewIfNeeded(node);
    }
    event.preventDefault();
    return false;
};
$.summernote.pluginEvents.visible = function (event, editor, layoutInfo) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable, "visible");

    var r = range.create();
    if (!r) return;

    if (!r.isCollapsed()) {
        if ((dom.isCell(dom.node(r.sc)) || dom.isCell(dom.node(r.ec))) && dom.node(r.sc) !== dom.node(r.ec)) {
            remove_table_content(r);
            r = range.create(r.ec, 0);
        }
        r.select();
    }

    // don't write in forbidden tag (like span for font awsome)
    var node = dom.firstChild(r.sc.tagName && r.so ? r.sc.childNodes[r.so] || r.sc : r.sc);
    while (node.parentNode) {
        if (dom.isForbiddenNode(node)) {
            var text = node.previousSibling;
            if (text && dom.isText(text) && dom.isVisibleText(text)) {
                range.create(text, text.textContent.length, text, text.textContent.length).select();
            } else {
                text = node.parentNode.insertBefore(document.createTextNode( "." ), node);
                range.create(text, 1, text, 1).select();
                setTimeout(function () {
                    var text = range.create().sc;
                    text.textContent = text.textContent.replace(/^./, '');
                    range.create(text, text.textContent.length, text, text.textContent.length).select();
                },0);
            }
            break;
        }
        node = node.parentNode;
    }

    return true;
};

function remove_table_content(r) {
    var nodes = dom.listBetween(r.sc, r.ec, r.so, r.eo);
    if (dom.isText(r.sc)) {
        r.sc.textContent = r.sc.textContent.slice(0, r.so);
    }
    if (dom.isText(r.ec)) {
        r.ec.textContent = r.ec.textContent.slice(r.eo);
    }
    for (var i in nodes) {
        var node = nodes[i];
        if (node === r.sc || node === r.ec || $.contains(node, r.sc) || $.contains(node, r.ec)) {
            continue;
        } else if (dom.isCell(node)) {
            $(node).html("<br/>");
        } else if (node.parentNode) {
            do {
                var parent = node.parentNode;
                parent.removeChild(node);
                node = parent;
            } while (!dom.isVisibleText(node) && !dom.firstElementChild(node) &&
                !dom.isCell(node) &&
                node.parentNode && !$(node.parentNode).hasClass('o_editable'));
        }
    }
    return false;
}

$.summernote.pluginEvents.delete = function (event, editor, layoutInfo) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable, "delete");

    var r = range.create();
    if (!r) return;
    if (!r.isContentEditable()) {
        event.preventDefault();
        return false;
    }
    if (!r.isCollapsed()) {
        if (dom.isCell(dom.node(r.sc)) || dom.isCell(dom.node(r.ec))) {
            remove_table_content(r);
            range.create(r.ec, 0).select();
        } else {
            r = r.deleteContents();
            r.select();
        }
        event.preventDefault();
        return false;
    }

    var target = r.ec;
    var offset = r.eo;
    if (target.tagName && target.childNodes[offset]) {
        target = target.childNodes[offset];
        offset = 0;
    }

    var node = dom.node(target);
    var data = dom.merge(node, target, offset, target, offset, null, true);
    data = dom.removeSpace(node.parentNode, data.sc, data.so, data.ec, data.eo);
    r = range.create(data.sc, data.so);
    r.select();
    target = r.sc;
    offset = r.so;

    while (!dom.hasContentAfter(node) && !dom.hasContentBefore(node) && !dom.isImg(node)) {node = node.parentNode;}

    var contentAfter = target.textContent.slice(offset,Infinity).match(/\S|\u00A0/);
    var content = target.textContent.replace(/[ \t\r\n]+$/, '');
    var temp;
    var temp2;
    var next;

    // media
    if (dom.isImg(node) || (!contentAfter && dom.isImg(dom.hasContentAfter(node)))) {
        var parent;
        var index;
        if (!dom.isImg(node)) {
            node = dom.hasContentAfter(node);
        }
        while (dom.isImg(node)) {
            parent = node.parentNode;
            index = dom.position(node);
            if (index>0) {
                next = node.previousSibling;
                r = range.create(next, next.textContent.length);
            } else {
                r = range.create(parent, 0);
            }
            if (!dom.hasContentAfter(node) && !dom.hasContentBefore(node)) {
                parent.appendChild($('<br/>')[0]);
            }
            parent.removeChild(node);
            node = parent;
            r.select();
        }
    }
    // empty tag
    else if (!content.length && target.tagName && dom.isRemovableEmptyNode(dom.isBR(target) ? target.parentNode : target)) {
        if (node === $editable[0] || $.contains(node, $editable[0])) {
            event.preventDefault();
            return false;
        }
        var before = false;
        next = dom.hasContentAfter(dom.ancestorHaveNextSibling(node));
        if (!dom.isContentEditable(next)) {
            before = true;
            next = dom.hasContentBefore(dom.ancestorHavePreviousSibling(node));
        }
        dom.removeSpace(next.parentNode, next, 0, next, 0); // clean before jump for not select invisible space between 2 tag
        next = dom.firstChild(next);
        node.parentNode.removeChild(node);
        range.create(next, before ? next.textContent.length : 0).select();
    }
    // normal feature if same tag and not the end
    else if (contentAfter) {
        return true;
    }
    // merge with the next text node
    else if (dom.isText(target) && (temp = dom.hasContentAfter(target)) && dom.isText(temp)) {
        return true;
    }
    //merge with the next block
    else if ((temp = dom.ancestorHaveNextSibling(target)) &&
            !r.isOnCell() &&
            dom.isMergable(temp) &&
            dom.isMergable(temp2 = dom.hasContentAfter(temp)) &&
            temp.tagName === temp2.tagName &&
            (temp.tagName !== "LI" || !$('ul,ol', temp).length) && (temp2.tagName !== "LI" || !$('ul,ol', temp2).length) && // protect li
            !dom.isNotBreakable(temp) &&
            !dom.isNotBreakable(temp2)) {
        dom.autoMerge(target, false);
        next = dom.firstChild(dom.hasContentAfter(dom.ancestorHaveNextSibling(target)));
        if (dom.isBR(next)) {
            if (dom.position(next) === 0) {
                range.create(next.parentNode, 0).select();
            }
            else {
                range.create(next.previousSibling, next.previousSibling.textContent.length).select();
            }
            next.parentNode.removeChild(next);
        } else {
            range.create(next, 0).select();
        }
    }
    // jump to next node for delete
    else if ((temp = dom.ancestorHaveNextSibling(target)) && (temp2 = dom.hasContentAfter(temp)) && dom.isContentEditable(temp2)) {

        dom.removeSpace(temp2.parentNode, temp2, 0, temp, 0); // clean before jump for not select invisible space between 2 tag
        temp2 = dom.firstChild(temp2);

        r = range.create(temp2, 0);
        r.select();

        if ((dom.isText(temp) || dom.getComputedStyle(temp).display === "inline") && (dom.isText(temp2) || dom.getComputedStyle(temp2).display === "inline")) {
            if (dom.isText(temp2)) {
                temp2.textContent = temp2.textContent.replace(/^\s*\S/, '');
            } else {
                $.summernote.pluginEvents.delete(event, editor, layoutInfo);
            }
        }
    }

    $(dom.node(r.sc)).trigger("click"); // trigger click to disable and reanable editor and image handler
    event.preventDefault();
    return false;
};
$.summernote.pluginEvents.backspace = function (event, editor, layoutInfo) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable, "backspace");

    var r = range.create();
    if (!r) return;
    if (!r.isContentEditable()) {
        event.preventDefault();
        return false;
    }
    if (!r.isCollapsed()) {
        if (dom.isCell(dom.node(r.sc)) || dom.isCell(dom.node(r.ec))) {
            remove_table_content(r);
            range.create(r.sc, dom.nodeLength(r.sc)).select();
        } else {
            r = r.deleteContents();
            r.select();
        }
        event.preventDefault();
        return false;
    }

    var target = r.sc;
    var offset = r.so;
    if (target.tagName && target.childNodes[offset]) {
        target = target.childNodes[offset];
        offset = 0;
    }

    var node = dom.node(target);
    var data = dom.merge(node, target, offset, target, offset, null, true);
    data = dom.removeSpace(node.parentNode, data.sc, data.so, data.ec, data.eo);
    r = dom.isVoid(data.sc) ? range.createFromNode(data.sc) : range.create(data.sc, data.so);
    r.select();
    target = r.sc;
    offset = r.so;
    if (target.tagName && target.childNodes[offset]) {
        target = target.childNodes[offset];
        offset = 0;
        node = dom.node(target);
    }

    while (node.parentNode && !dom.hasContentAfter(node) && !dom.hasContentBefore(node) && !dom.isImg(node)) {node = node.parentNode;}

    var contentBefore = target.textContent.slice(0,offset).match(/\S|\u00A0/);
    var content = target.textContent.replace(/[ \t\r\n]+$/, '');
    var temp;
    var temp2;
    var prev;

    // delete media
    if (dom.isImg(node) || (!contentBefore && dom.isImg(dom.hasContentBefore(node)))) {
        if (!dom.isImg(node)) {
            node = dom.hasContentBefore(node);
        }
        range.createFromNode(node).select();
        $.summernote.pluginEvents.delete(event, editor, layoutInfo);
    }
    // table tr td
    else if (r.isOnCell() && !offset && (target === (temp = dom.ancestor(target, dom.isCell)) || target === temp.firstChild || (dom.isText(temp.firstChild) && !dom.isVisibleText(temp.firstChild) && target === temp.firstChild.nextSibling))) {
        if (dom.previousElementSibling(temp)) {
            var td = dom.previousElementSibling(temp);
            node = td.lastChild || td;
        } else {
            var tr = temp.parentNode;
            var prevTr = dom.previousElementSibling(tr);
            if (!$(temp.parentNode).text().match(/\S|\u00A0/)) {
                if (prevTr) {
                    node = dom.lastChild(dom.lastElementChild(prevTr));
                } else {
                    node = dom.lastChild(dom.hasContentBefore(dom.ancestorHavePreviousSibling(tr)) || $editable.get(0));
                }
                $(tr).empty();
                if (!$(tr).closest('table').has('td, th').length) {
                    $(tr).closest('table').remove();
                }
                $(tr).remove();
                range.create(node, node.textContent.length, node, node.textContent.length).select();
            } else {
                node = dom.lastElementChild(prevTr).lastChild || dom.lastElementChild(prevTr);
            }
        }
        if (dom.isBR(node)) {
            range.createFromNode(node).select();
        } else {
            range.create(node, dom.nodeLength(node)).select();
        }
    }
    // empty tag
    else if (!content.length && target.tagName && dom.isRemovableEmptyNode(target)) {
        if (node === $editable[0] || $.contains(node, $editable[0])) {
            event.preventDefault();
            return false;
        }
        var before = true;
        prev = dom.hasContentBefore(dom.ancestorHavePreviousSibling(node));
        if (!dom.isContentEditable(prev)) {
            before = false;
            prev = dom.hasContentAfter(dom.ancestorHaveNextSibling(node));
        }
        dom.removeSpace(prev.parentNode, prev, 0, prev, 0); // clean before jump for not select invisible space between 2 tag
        prev = dom.lastChild(prev);
        node.parentNode.removeChild(node);
        range.createFromNode(prev).select();
        range.create(prev, before ? prev.textContent.length : 0).select();
    }
    // normal feature if same tag and not the begin
    else if (contentBefore) {
        return true;
    }
    // merge with the previous text node
    else if (dom.isText(target) && (temp = dom.hasContentBefore(target)) && (dom.isText(temp) || dom.isBR(temp))) {
        return true;
    }
    //merge with the previous block
    else if ((temp = dom.ancestorHavePreviousSibling(target)) &&
            dom.isMergable(temp) &&
            dom.isMergable(temp2 = dom.hasContentBefore(temp)) &&
            temp.tagName === temp2.tagName &&
            (temp.tagName !== "LI" || !$('ul,ol', temp).length) && (temp2.tagName !== "LI" || !$('ul,ol', temp2).length) && // protect li
            !dom.isNotBreakable(temp) &&
            !dom.isNotBreakable(temp2)) {
        prev = dom.firstChild(target);
        dom.autoMerge(target, true);
        range.create(prev, 0).select();
    }
    // jump to previous node for delete
    else if ((temp = dom.ancestorHavePreviousSibling(target)) && (temp2 = dom.hasContentBefore(temp)) && dom.isContentEditable(temp2)) {

        dom.removeSpace(temp2.parentNode, temp2, 0, temp, 0); // clean before jump for not select invisible space between 2 tag
        temp2 = dom.lastChild(temp2);

        r = range.create(temp2, temp2.textContent.length, temp2, temp2.textContent.length);
        r.select();

        if ((dom.isText(temp) || dom.getComputedStyle(temp).display === "inline") && (dom.isText(temp2) || dom.getComputedStyle(temp2).display === "inline")) {
            if (dom.isText(temp2)) {
                temp2.textContent = temp2.textContent.replace(/\S\s*$/, '');
            } else {
                $.summernote.pluginEvents.backspace(event, editor, layoutInfo);
            }
        }
    }

    r = range.create();
    if (r) {
        $(dom.node(r.sc)).trigger("click"); // trigger click to disable and reanable editor and image handler
        dom.scrollIntoViewIfNeeded(r.sc.parentNode.previousElementSibling || r.sc);
    }

    event.preventDefault();
    return false;
};

function isFormatNode(node) {
    return node.tagName && options.styleTags.indexOf(node.tagName.toLowerCase()) !== -1;
}

$.summernote.pluginEvents.insertUnorderedList = function (event, editor, layoutInfo, type) {
    var $editable = layoutInfo.editable();
    $editable.focus();
    $editable.data('NoteHistory').recordUndo($editable);

    type = type || "UL";
    var sorted = type === "OL";

    var parent;
    var r = range.create();
    if (!r) return;
    var node = r.sc;
    while (node && node !== $editable[0]) {

        parent = node.parentNode;
        if (node.tagName === (sorted ? "UL" : "OL")) {

            var ul = document.createElement(sorted ? "ol" : "ul");
            ul.className = node.className;
            if (type !== 'checklist') {
                ul.classList.remove('o_checklist');
            } else {
                ul.classList.add('o_checklist');
            }
            parent.insertBefore(ul, node);
            while (node.firstChild) {
                ul.appendChild(node.firstChild);
            }
            parent.removeChild(node);
            r.select();
            return;

        } else if (node.tagName === (sorted ? "OL" : "UL")) {

            if (type === 'checklist' && !node.classList.contains('o_checklist')) {
                node.classList.add('o_checklist');
                return;
            } else if (type === 'UL' && node.classList.contains('o_checklist')) {
                node.classList.remove('o_checklist');
                return;
            }

            var lis = [];
            for (var i=0; i<node.children.length; i++) {
                lis.push(node.children[i]);
            }

            if (parent.tagName === "LI") {
                node = parent;
                parent = node.parentNode;
                _.each(lis, function (li) {
                    parent.insertBefore(li, node);
                });
            } else {
                _.each(lis, function (li) {
                    while (li.firstChild) {
                        parent.insertBefore(li.firstChild, node);
                    }
                });
            }

            parent.removeChild(node);
            r.select();
            return;

        }
        node = parent;
    }

    var p0 = r.sc;
    while (p0 && p0.parentNode && p0.parentNode !== $editable[0] && !isFormatNode(p0)) {
        p0 = p0.parentNode;
    }
    if (!p0) return;
    var p1 = r.ec;
    while (p1 && p1.parentNode && p1.parentNode !== $editable[0] && !isFormatNode(p1)) {
        p1 = p1.parentNode;
    }
    if (!p0.parentNode || p0.parentNode !== p1.parentNode) {
        return;
    }

    parent = p0.parentNode;
    ul = document.createElement(sorted ? "ol" : "ul");
    if (type === 'checklist') {
        ul.classList.add('o_checklist');
    }
    parent.insertBefore(ul, p0);
    var childNodes = parent.childNodes;
    var brs = [];
    var begin = false;
    for (i = 0; i < childNodes.length; i++) {
        if (begin && dom.isBR(childNodes[i])) {
            parent.removeChild(childNodes[i]);
            i--;
        }
        if ((!dom.isText(childNodes[i]) && !isFormatNode(childNodes[i])) || (!ul.firstChild && childNodes[i] !== p0) ||
            $.contains(ul, childNodes[i]) || (dom.isText(childNodes[i]) && !childNodes[i].textContent.match(/\S|u00A0/))) {
            continue;
        }
        begin = true;
        var li = document.createElement('li');
        ul.appendChild(li);
        li.appendChild(childNodes[i]);
        if (li.firstChild === p1) {
            break;
        }
        i--;
    }
    if (dom.isBR(childNodes[i])) {
        parent.removeChild(childNodes[i]);
    }

    for (i = 0; i < brs.length ; i++) {
        parent.removeChild(brs[i]);
    }
    r.clean().select();
    event.preventDefault();

    return false;
};
$.summernote.pluginEvents.insertOrderedList = function (event, editor, layoutInfo) {
    $.summernote.pluginEvents.insertUnorderedList(event, editor, layoutInfo, "OL");
};
$.summernote.pluginEvents.insertCheckList = function (event, editor, layoutInfo) {
    $.summernote.pluginEvents.insertUnorderedList(event, editor, layoutInfo, "checklist");
    $(range.create().sc.parentNode).trigger('input'); // to update checklist-id
};
$.summernote.pluginEvents.indent = function (event, editor, layoutInfo, outdent) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable);
    var r = range.create();
    if (!r) return;

    var flag = false;
    function indentUL(UL, start, end) {
        var next;
        var previous;
        var tagName = UL.tagName;
        var node = UL.firstChild;
        var ul = document.createElement(tagName);
        ul.className = UL.className;
        var li = document.createElement("li");
        li.classList.add('o_indent');
        li.appendChild(ul);

        if (flag) {
            flag = 1;
        }

        // create and fill ul into a li
        while (node) {
            if (flag === 1 || node === start || $.contains(node, start)) {
                flag = true;
                if (previous) {
                    if (dom.isList(previous.lastChild)) {
                        ul = previous.lastChild;
                    } else {
                        previous.appendChild(ul);
                    }
                } else {
                    node.parentNode.insertBefore(li, node);
                }
            }
            next = dom.nextElementSibling(node);
            if (flag) {
                ul.appendChild(node);
            }
            if (node === end || $.contains(node, end)) {
                flag = false;
                break;
            }
            previous = node;
            node = next;
        }

        var temp;
        var prev = dom.previousElementSibling(li);
        if (prev && prev.tagName === "LI" && (temp = dom.firstElementChild(prev)) && temp.tagName === tagName && ((dom.firstElementChild(prev) || prev.firstChild) !== ul)) {
            dom.doMerge(dom.firstElementChild(prev) || prev.firstChild, ul);
            li = prev;
            li.parentNode.removeChild(dom.nextElementSibling(li));
        }
        next = dom.nextElementSibling(li);
        if (next && next.tagName === "LI" && (temp = dom.firstElementChild(next)) && temp.tagName === tagName && (dom.firstElementChild(li) !== dom.firstElementChild(next))) {
            dom.doMerge(dom.firstElementChild(li), dom.firstElementChild(next));
            li.parentNode.removeChild(dom.nextElementSibling(li));
        }
    }
    function outdenttUL(UL, start, end) {
        var next;
        var node = UL.firstChild;
        var parent = UL.parentNode;
        var li = UL.parentNode.tagName === "LI" ? UL.parentNode : UL;
        var ul = UL.parentNode.tagName === "LI" ? UL.parentNode.parentNode : UL.parentNode;
        start = dom.ancestor(start, dom.isLi);
        end = dom.ancestor(end, dom.isLi);

        if (ul.tagName !== "UL" && ul.tagName !== "OL") return;

        // create and fill ul into a li
        while (node) {
            if (node === start || $.contains(node, start)) {
                flag = true;
                if (dom.previousElementSibling(node) && li.tagName === "LI") {
                    li = dom.splitTree(li, dom.prevPoint({'node': node, 'offset': 0}));
                }
            }
            next = dom.nextElementSibling(node);
            if (flag) {
                var $succeeding = $(node).nextAll();
                ul = node.parentNode;
                if (dom.previousElementSibling(ul)) {
                    dom.insertAfter(node, li);
                } else {
                    li.parentNode.insertBefore(node, li);
                }
                $succeeding.insertAfter(node);
                if (!ul.children.length) {
                    if (ul.parentNode.tagName === "LI" && !dom.previousElementSibling(ul)) {
                        ul = ul.parentNode;
                    }
                    ul.parentNode.removeChild(ul);
                }
                flag = false;
                break;
            }

            if (node === end || $.contains(node, end)) {
                flag = false;
                break;
            }
            node = next;
        }

        dom.merge(parent, start, 0, end, 1, null, true);
    }
    function indentOther(p, start, end) {
        if (p === start || $.contains(p, start) || $.contains(start, p)) {
            flag = true;
        }
        if (flag) {
            if (outdent) {
                dom.outdent(p);
            } else {
                dom.indent(p);
            }
        }
        if (p === end || $.contains(p, end) || $.contains(end, p)) {
            flag = false;
        }
    }

    var ancestor = r.commonAncestor();
    var $dom = $(ancestor);

    if (!dom.isList(ancestor)) {
        if (dom.isList(ancestor.parentNode)) {
            $dom = $(ancestor.parentNode);
        } else {
            // to indent a selection, we indent the child nodes of the common
            // ancestor that contains this selection
            $dom = $(dom.node(ancestor)).children();
        }
    }
    if (!$dom.not('br').length) {
        // if selection is inside a list, we indent its list items
        $dom = $(dom.ancestor(r.sc, dom.isList));
        if (!$dom.length) {
            // if the selection is contained in a single HTML node, we indent
            // the first ancestor 'content block' (P, H1, PRE, ...) or TD
            $dom = $(r.sc).closest(options.styleTags.join(',')+',td');
        }
    }

    // if select tr, take the first td
    $dom = $dom.map(function () { return this.tagName === "TR" ? dom.firstElementChild(this) : this; });

    $dom.each(function () {
        if (flag || $.contains(this, r.sc)) {
            if (dom.isList(this)) {
                if (outdent) {
                    outdenttUL(this, r.sc, r.ec);
                } else {
                    indentUL(this, r.sc, r.ec);
                }
            } else if (isFormatNode(this) || dom.ancestor(this, dom.isCell)) {
                indentOther(this, r.sc, r.ec);
            }
        }
    });

    if ($dom.length) {
        var $parent = $dom.parent();

        // remove text nodes between lists
        var $ul = $parent.find('ul, ol');
        if (!$ul.length) {
            $ul = $(dom.ancestor(r.sc, dom.isList));
        }
        $ul.each(function () {
            if (this.previousSibling &&
                this.previousSibling !== dom.previousElementSibling(this) &&
                !this.previousSibling.textContent.match(/\S/)) {
                this.parentNode.removeChild(this.previousSibling);
            }
            if (this.nextSibling &&
                this.nextSibling !== dom.nextElementSibling(this) &&
                !this.nextSibling.textContent.match(/\S/)) {
                this.parentNode.removeChild(this.nextSibling);
            }
        });

        // merge same ul or ol
        r = dom.merge($parent[0], r.sc, r.so, r.ec, r.eo, function (prev, cur) {
                if (prev && dom.isList(prev) && dom.isEqual(prev, cur)) {
                    return true;
                }
            }, true);
        range.create(r.sc, r.so, r.ec, r.eo).select();
    }
    event.preventDefault();
    return false;
};
$.summernote.pluginEvents.outdent = function (event, editor, layoutInfo) {
    return $.summernote.pluginEvents.indent(event, editor, layoutInfo, true);
};

$.summernote.pluginEvents.formatBlock = function (event, editor, layoutInfo, sTagName) {
    $.summernote.pluginEvents.applyFont(event, editor, layoutInfo, null, null, "Default");
    var $editable = layoutInfo.editable();
    $editable.focus();
    $editable.data('NoteHistory').recordUndo($editable);
    event.preventDefault();

    var r = range.create();
    if (!r) {
        return;
    }
    // select content since container (that firefox selects) may be removed
    if (r.so === 0) {
        r.sc = dom.firstChild(r.sc);
    }
    if (dom.nodeLength(r.ec) >= r.eo) {
        r.ec = dom.lastChild(r.ec);
        r.eo = dom.nodeLength(r.ec);
    }
    r = range.create(r.sc, r.so, r.ec, r.eo);
    r.reRange().select();

    if (sTagName === "blockquote" || sTagName === "pre") {
      sTagName = $.summernote.core.agent.isMSIE ? '<' + sTagName + '>' : sTagName;
      document.execCommand('FormatBlock', false, sTagName);
      return;
    }

    // fix by odoo because if you select a style in a li with no p tag all the ul is wrapped by the style tag
    var nodes = dom.listBetween(r.sc, r.ec, r.so, r.eo);
    for (var i=0; i<nodes.length; i++) {
        if (dom.isBR(nodes[i]) || (dom.isText(nodes[i]) && dom.isVisibleText(nodes[i])) || dom.isB(nodes[i]) || dom.isU(nodes[i]) || dom.isS(nodes[i]) || dom.isI(nodes[i]) || dom.isFont(nodes[i])) {
            var ancestor = dom.ancestor(nodes[i], isFormatNode);
            if ($(ancestor).parent().is('blockquote')) {
                // firefox may wrap formatting block in blockquote
                $(ancestor).unwrap();
            }
            if (!ancestor) {
                dom.wrap(nodes[i], sTagName);
            } else if (ancestor.tagName.toLowerCase() !== sTagName) {
                var tag = document.createElement(sTagName);
                ancestor.parentNode.insertBefore(tag, ancestor);
                dom.moveContent(ancestor, tag);
                if (ancestor.className) {
                    tag.className = ancestor.className;
                }
                ancestor.parentNode.removeChild(ancestor);
            }
        }
    }
    r.select();
};
$.summernote.pluginEvents.removeFormat = function (event, editor, layoutInfo, value) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable);
    var r = range.create();
    if (!r) return;
    var node = range.create().sc.parentNode;
    document.execCommand('removeFormat');
    document.execCommand('removeFormat');
    r = range.create();
    if (!r) return;
    r = dom.merge(node, r.sc, r.so, r.ec, r.eo, null, true);
    range.create(r.sc, r.so, r.ec, r.eo).select();
    event.preventDefault();
    return false;
};

eventHandler.modules.editor.undo = function ($popover) {
    if (!$popover.attr('disabled')) $popover.data('NoteHistory').undo();
};
eventHandler.modules.editor.redo = function ($popover) {
    if (!$popover.attr('disabled'))  $popover.data('NoteHistory').redo();
};

// Get color and background color of node to update recent color button
var fn_from_node = eventHandler.modules.editor.style.fromNode;
eventHandler.modules.editor.style.fromNode = function ($node) {
    var styleInfo = fn_from_node.apply(this, arguments);
    styleInfo['color'] = $node.css('color');
    styleInfo['background-color'] = $node.css('background-color');
    return styleInfo;
};

// use image toolbar if current range is on image
var fn_editor_currentstyle = eventHandler.modules.editor.currentStyle;
eventHandler.modules.editor.currentStyle = function (target) {
    var styleInfo = fn_editor_currentstyle.apply(this, arguments);
    // with our changes for inline editor, the targeted element could be a button of the editor
    if (!styleInfo.image || !dom.isEditable(styleInfo.image)) {
        styleInfo.image = undefined;
        var r = range.create();
        if (r)
            styleInfo.image = r.isOnImg();
    }
    // Fix when the target is a link: the text-align buttons state should
    // indicate the alignment of the link in the parent, not the text inside
    // the link (which is not possible to customize with summernote). Summernote fixed
    // this in their newest version... by just not showing the active button
    // for alignments.
    if (styleInfo.anchor) {
        styleInfo['text-align'] = $(styleInfo.anchor).parent().css('text-align');
    }
    return styleInfo;
};

options.fontSizes = weDefaultOptions.fontSizes;
$.summernote.pluginEvents.applyFont = function (event, editor, layoutInfo, color, bgcolor, size) {
    var r = range.create();
    if (!r) return;
    var startPoint = r.getStartPoint();
    var endPoint = r.getEndPoint();

    if (r.isCollapsed() && !dom.isFont(r.sc)) {
        return {
            sc: startPoint.node,
            so: startPoint.offset,
            ec: endPoint.node,
            offset: endPoint.offset
        };
    }

    if (startPoint.node.tagName && startPoint.node.childNodes[startPoint.offset]) {
        startPoint.node = startPoint.node.childNodes[startPoint.offset];
        startPoint.offset = 0;
    }
    if (endPoint.node.tagName && endPoint.node.childNodes[endPoint.offset]) {
        endPoint.node = endPoint.node.childNodes[endPoint.offset];
        endPoint.offset = 0;
    }

    // get first and last point
    var ancestor;
    var node;
    if (endPoint.offset && endPoint.offset !== dom.nodeLength(endPoint.node)) {
      ancestor = dom.ancestor(endPoint.node, dom.isFont) || endPoint.node;
      dom.splitTree(ancestor, endPoint);
    }
    if (startPoint.offset && startPoint.offset !== dom.nodeLength(startPoint.node)) {
      ancestor = dom.ancestor(startPoint.node, dom.isFont) || startPoint.node;
      node = dom.splitTree(ancestor, startPoint);
      if (endPoint.node === startPoint.node) {
        endPoint.node = node;
        endPoint.offset = dom.nodeLength(node);
      }
      startPoint.node = node;
      startPoint.offset = 0;
    }

    // get list of nodes to change
    var nodes = [];
    dom.walkPoint(startPoint, endPoint, function (point) {
      var node = point.node;
      if (((dom.isText(node) && dom.isVisibleText(node)) ||
          (dom.isFont(node) && !dom.isVisibleText(node))) &&
          (node !== endPoint.node || endPoint.offset)) {

          nodes.push(point.node);

      }
    });
    nodes = list.unique(nodes);

        // If ico fa
    if (r.isCollapsed()) {
        nodes.push(startPoint.node);
    }

    // apply font: foreColor, backColor, size (the color can be use a class text-... or bg-...)
    var font, $font, fonts = [], className;
    var i;
    if (color || bgcolor || size) {
      for (i=0; i<nodes.length; i++) {
        node = nodes[i];

        font = dom.ancestor(node, dom.isFont);
        if (!font) {
          if (node.textContent.match(/^[ ]|[ ]$/)) {
            node.textContent = node.textContent.replace(/^[ ]|[ ]$/g, '\u00A0');
          }

          font = dom.create("font");
          node.parentNode.insertBefore(font, node);
          font.appendChild(node);
        }

        fonts.push(font);

        className = font.className.split(/\s+/);

        var k;
        if (color) {
          for (k=0; k<className.length; k++) {
            if (className[k].length && className[k].slice(0,5) === "text-") {
              className.splice(k,1);
              k--;
            }
          }

          if (color.indexOf('text-') !== -1) {
            font.className = className.join(" ") + " " + color;
            font.style.color = "inherit";
          } else {
            font.className = className.join(" ");
            font.style.color = color;
          }
        }
        if (bgcolor) {
          for (k=0; k<className.length; k++) {
            if (className[k].length && className[k].slice(0,3) === "bg-") {
              className.splice(k,1);
              k--;
            }
          }

          if (bgcolor.indexOf('bg-') !== -1) {
            font.className = className.join(" ") + " " + bgcolor;
            font.style.backgroundColor = "inherit";
          } else {
            font.className = className.join(" ");
            font.style.backgroundColor = bgcolor;
          }
        }
        if (size) {
          font.style.fontSize = "inherit";
          if (!isNaN(size) && Math.abs(parseInt(dom.getComputedStyle(font).fontSize, 10)-size)/size > 0.05) {
            font.style.fontSize = size + "px";
          }
        }
      }
    }

    // remove empty values
    // we must remove the value in 2 steps (applay inherit then remove) because some
    // browser like chrome have some time an error for the rendering and/or keep inherit
    for (i=0; i<fonts.length; i++) {
        font = fonts[i];
        if (font.style.backgroundColor === "inherit") {
            font.style.backgroundColor = "";
        }
        if (font.style.color === "inherit") {
            font.style.color = "";
        }
        if (font.style.fontSize === "inherit") {
            font.style.fontSize = "";
        }

        $font = $(font);

        if (!$font.css("color") && !$font.css("background-color") && !$font.css("font-size")) {
            $font.removeAttr("style");
        }
        if (!font.className.length) {
            $font.removeAttr("class");
        }
    }

    // select nodes to clean (to remove empty font and merge same nodes)
    nodes = [];
    dom.walkPoint(startPoint, endPoint, function (point) {
      nodes.push(point.node.childNodes[point.offset] || point.node);
    });
    nodes = list.unique(nodes);

    function remove(node, to) {
      if (node === endPoint.node) {
        endPoint = dom.prevPoint(endPoint);
      }
      if (to) {
        dom.moveContent(node, to);
      }
      dom.remove(node);
    }

    // remove node without attributes (move content), and merge the same nodes
     var className2, style, style2;
     for (i=0; i<nodes.length; i++) {
      node = nodes[i];

      if (dom.isText(node) && !node.nodeValue) {
        remove(node);
        continue;
      }

      font = dom.ancestor(node, dom.isFont);
      node = font || dom.ancestor(node, dom.isSpan);

      if (!node) {
        continue;
      }

      $font = $(node);
      className = dom.orderClass(node);
      style = dom.orderStyle(node);

      if (!className && !style) {
        remove(node, node.parentNode);
        continue;
      }

      if (font = dom.ancestor(node.previousSibling, dom.isFont)) {
        className2 = font.getAttribute('class');
        style2 = font.getAttribute('style');
        if (node !== font && className === className2 && style === style2) {
          remove(node, font);
          continue;
        }
      }
     }

    range.create(startPoint.node, startPoint.offset, endPoint.node, endPoint.offset).select();
};
$.summernote.pluginEvents.fontSize = function (event, editor, layoutInfo, value) {
  var $editable = layoutInfo.editable();
  event.preventDefault();
  $.summernote.pluginEvents.applyFont(event, editor, layoutInfo, null, null, value);
  editor.afterCommand($editable);
};
$.summernote.pluginEvents.color = function (event, editor, layoutInfo, sObjColor) {
  var oColor = JSON.parse(sObjColor);
  var foreColor = oColor.foreColor, backColor = oColor.backColor;

  if (foreColor) { $.summernote.pluginEvents.foreColor(event, editor, layoutInfo, foreColor); }
  if (backColor) { $.summernote.pluginEvents.backColor(event, editor, layoutInfo, backColor); }
};
$.summernote.pluginEvents.foreColor = function (event, editor, layoutInfo, foreColor, preview) {
  var $editable = layoutInfo.editable();
  $.summernote.pluginEvents.applyFont(event, editor, layoutInfo, foreColor, null, null);
  if (!preview) {
    editor.afterCommand($editable);
  }
};
$.summernote.pluginEvents.backColor = function (event, editor, layoutInfo, backColor, preview) {
  var $editable = layoutInfo.editable();
  var r = range.create();
  if (!r) return;
  if (r.isCollapsed() && r.isOnCell()) {
    var cell = dom.ancestor(r.sc, dom.isCell);
    cell.className = cell.className.replace(new RegExp('(^|\\s+)bg-[^\\s]+(\\s+|$)', 'gi'), '');
    cell.style.backgroundColor = "";
    if (backColor.indexOf('bg-') !== -1) {
      cell.className += ' ' + backColor;
    } else if (backColor !== 'inherit') {
      cell.style.backgroundColor = backColor;
    }
    return;
  }
  $.summernote.pluginEvents.applyFont(event, editor, layoutInfo, null, backColor, null);
  if (!preview) {
    editor.afterCommand($editable);
  }
};

options.onCreateLink = function (sLinkUrl) {
    if (sLinkUrl.indexOf('mailto:') === 0 || sLinkUrl.indexOf('tel:') === 0) {
      sLinkUrl = sLinkUrl.replace(/^tel:([0-9]+)$/, 'tel://$1');
    } else if (sLinkUrl.indexOf('@') !== -1 && sLinkUrl.indexOf(':') === -1) {
      sLinkUrl =  'mailto:' + sLinkUrl;
    } else if (sLinkUrl.indexOf('://') === -1 && sLinkUrl[0] !== '/'
               && sLinkUrl[0] !== '#' && sLinkUrl.slice(0, 2) !== '${') {
      sLinkUrl = 'http://' + sLinkUrl;
    }
    return sLinkUrl;
};

function summernote_table_scroll(event) {
    var r = range.create();
    if (r && r.isOnCell()) {
        $('.o_table_handler').remove();
    }
}
function summernote_table_update(oStyle) {
    var r = range.create();
    if (!oStyle.range || !r || !r.isOnCell() || !r.isOnCellFirst()) {
        $('.o_table_handler').remove();
        return;
    }
    var table = dom.ancestor(oStyle.range.sc, dom.isTable);
    if (!table) { // if the editable tag is inside the table
        return;
    }
    var $editable = $(table).closest('.o_editable');

    $('.o_table_handler').remove();

    var $dels = $();
    var $adds = $();
    var $tds = $('tr:first', table).children();
    $tds.each(function () {
        var $td = $(this);
        var pos = $td.offset();

        var $del = $('<span class="o_table_handler fa fa-minus-square"/>').appendTo('body');
        $del.data('td', this);
        $dels = $dels.add($del);
        $del.css({
            left: ((pos.left + $td.outerWidth()/2)-6) + "px",
            top: (pos.top-6) + "px"
        });

        var $add = $('<span class="o_table_handler fa fa-plus-square"/>').appendTo('body');
        $add.data('td', this);
        $adds = $adds.add($add);
        $add.css({
            left: (pos.left-6) + "px",
            top: (pos.top-6) + "px"
        });
    });

    var $last = $tds.last();
    var pos = $last.offset();
    var $add = $('<span class="o_table_handler fa fa-plus-square"/>').appendTo('body');
    $adds = $adds.add($add);
    $add.css({
        left: (pos.left+$last.outerWidth()-6) + "px",
        top: (pos.top-6) + "px"
    });

    var $table = $(table);
    $dels.data('table', table).on('mousedown', function (event) {
        var td = $(this).data('td');
        $editable.data('NoteHistory').recordUndo($editable);

        var newTd;
        if ($(td).siblings().length) {
            var eq = $(td).index();
            $table.find('tr').each(function () {
                $('> td:eq('+eq+')', this).remove();
            });
            newTd = $table.find('tr:first > td:eq('+eq+'), tr:first > td:last').first();
        } else {
            var prev = dom.lastChild(dom.hasContentBefore(dom.ancestorHavePreviousSibling($table[0])));
            $table.remove();
            $('.o_table_handler').remove();
            r = range.create(prev, prev.textContent.length);
            r.select();
            $(r.sc).trigger('mouseup');
            return;
        }

        $('.o_table_handler').remove();
        range.create(newTd[0], 0, newTd[0], 0).select();
        newTd.trigger('mouseup');
    });
    $adds.data('table', table).on('mousedown', function (event) {
        var td = $(this).data('td');
        $editable.data('NoteHistory').recordUndo($editable);

        var newTd;
        if (td) {
            var eq = $(td).index();
            $table.find('tr').each(function () {
                $('td:eq('+eq+')', this).before('<td>'+dom.blank+'</td>');
            });
            newTd = $table.find('tr:first td:eq('+eq+')');
        } else {
            $table.find('tr').each(function () {
                $(this).append('<td>'+dom.blank+'</td>');
            });
            newTd = $table.find('tr:first td:last');
        }

        $('.o_table_handler').remove();
        range.create(newTd[0], 0, newTd[0], 0).select();
        newTd.trigger('mouseup');
    });

    $dels.css({
        'position': 'absolute',
        'cursor': 'pointer',
        'background-color': '#fff',
        'color': '#ff0000'
    });
    $adds.css({
        'position': 'absolute',
        'cursor': 'pointer',
        'background-color': '#fff',
        'color': '#00ff00'
    });
}
var fn_popover_update = eventHandler.modules.popover.update;
eventHandler.modules.popover.update = function ($popover, oStyle, isAirMode) {
    fn_popover_update.call(this, $popover, oStyle, isAirMode);
    if ((isAirMode ? $popover : $popover.parent()).find('.note-table').length) {
        summernote_table_update(oStyle);
    }
};

function mouseDownChecklist (e) {
    if (!dom.isLi(e.target) || !$(e.target).parent('ul.o_checklist').length || e.offsetX > 0) {
        return;
    }
    e.stopPropagation();
    e.preventDefault();
    var checked = $(e.target).hasClass('o_checked');
    $(e.target).toggleClass('o_checked', !checked);
    var $sublevel = $(e.target).next('ul.o_checklist, li:has(> ul.o_checklist)').find('> li, ul.o_checklist > li');
    var $parents = $(e.target).parents('ul.o_checklist').map(function () {
        return this.parentNode.tagName === 'LI' ? this.parentNode : this;
    });
    if (checked) {
        $sublevel.removeClass('o_checked');
        do {
            $parents = $parents.prev('ul.o_checklist li').removeClass('o_checked');
        } while ($parents.length);
    } else {
        $sublevel.addClass('o_checked');
        var $lis;
        do {
            $lis = $parents.not(':has(li[id^="checklist-id"]:not(.o_checked))').prev('ul.o_checklist li:not(.o_checked)');
            $lis.addClass('o_checked');
        } while ($lis.length);
    }
}

var fn_attach = eventHandler.attach;
eventHandler.attach = function (oLayoutInfo, options) {
    var $editable = oLayoutInfo.editor().hasClass('note-editable') ? oLayoutInfo.editor() : oLayoutInfo.editor().find('.note-editable');
    fn_attach.call(this, oLayoutInfo, options);
    $editable.on("scroll", summernote_table_scroll);
    $editable.on("mousedown", mouseDownChecklist);
};
var fn_detach = eventHandler.detach;
eventHandler.detach = function (oLayoutInfo, options) {
    var $editable = oLayoutInfo.editor().hasClass('note-editable') ? oLayoutInfo.editor() : oLayoutInfo.editor().find('.note-editable');
    fn_detach.call(this, oLayoutInfo, options);
    $editable.off("scroll", summernote_table_scroll);
    $editable.off("mousedown", mouseDownChecklist);
    $('.o_table_handler').remove();
};

options.icons.image.image = "file-image-o";
$.summernote.lang['en-US'].image.image = "File / Image";

return $.summernote;
});
