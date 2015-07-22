odoo.define('web_editor.summernote', function (require) {
'use strict';

var core = require('web.core');
require('summernote/summernote'); // wait that summernote is loaded

var _t = core._t;

//////////////////////////////////////////////////////////////////////////////////////////////////////////
/* Summernote Lib (neek hack to make accessible: method and object) */

var agent = $.summernote.core.agent;
var dom = $.summernote.core.dom;
var range = $.summernote.core.range;
var list = $.summernote.core.list;
var key = $.summernote.core.key;
var eventHandler = $.summernote.eventHandler;
var editor = eventHandler.editor;
var renderer = $.summernote.renderer;
var options = $.summernote.options;

//////////////////////////////////////////////////////////////////////////////////////////////////////////
/* Add method to Summernote*/

dom.hasContentAfter = function (node) {
    var next;
    while (node.nextSibling) {
        next = node.nextSibling;
        if (next.tagName || next.textContent.match(/\S|\u00A0/) || dom.isBR(next)) return next;
        node = next;
    }
};
dom.hasContentBefore = function (node) {
    var prev;
    while (node.previousSibling) {
        prev = node.previousSibling;
        if (prev.tagName || prev.textContent.match(/\S|\u00A0/) || dom.isBR(prev)) return prev;
        node = prev;
    }
};
dom.ancestorHaveNextSibling = function (node, pred) {
    pred = pred || dom.hasContentAfter;
    while (!node.nextSibling || !pred(node)) { node = node.parentNode; }
    return node;
};
dom.ancestorHavePreviousSibling = function (node, pred) {
    pred = pred || dom.hasContentBefore;
    while (!node.previousSibling || !pred(node)) { node = node.parentNode; }
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
    for(var a in prev.attributes) {
        att = prev.attributes[a];
        for(var b in cur.attributes) {
            att2 = cur.attributes[b];
            if (att.name === att2.name) {
                if (strip(att.value) != strip(att2.value)) return false;
                continue loop_prev;
            }
        }
        return false;
    }
    return true;
};
/**
 * Checks that the node only has a @style, not e.g. @class or whatever
 */
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
    if (prev && (dom.isText(prev) || (dom.pasteTextApply.indexOf(prev.tagName) !== -1 && prev !== cur.parentNode)) && dom.isText(cur)) {
        return true;
    }
    if (prev && prev.tagName === "P" && dom.isText(cur)) {
        return true;
    }
    if (prev && dom.isText(cur) && !cur.textContent.match(/\S|\u00A0/) && (dom.isText(prev) || prev.textContent.match(/\S|\u00A0/))) {
        return true;
    }
    if (prev && !dom.isBR(prev) && dom.isEqual(prev, cur) &&
        ((prev.tagName && window.getComputedStyle(prev).display === "inline" &&
          cur.tagName && window.getComputedStyle(cur).display === "inline"))) {
        return true;
    }
    if (dom.isEqual(parent, cur) &&
        ((parent.tagName && window.getComputedStyle(parent).display === "inline" &&
          cur.tagName && window.getComputedStyle(cur).display === "inline"))) {
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
        while(begin.firstChild) {begin = begin.firstChild;}
        so = 0;
    } else if (begin.tagName && begin.childNodes[so]) {
        begin = begin.childNodes[so];
        so = 0;
    }
    if (!end) {
        end = node;
        while(end.lastChild) {end = end.lastChild;}
        eo = end.textContent.length-1;
    } else if (end.tagName) {
        
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

    function __merge (node) {
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
        if (temp = (previous ? dom.hasContentBefore(node) : dom.hasContentAfter(node))) {
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

    (function __remove_space (node) {
        if (!node) return;
        for (var k=0; k<node.childNodes.length; k++) {
            var cur = node.childNodes[k];

            if (cur === begin) add = true;

            if (cur.tagName && cur.tagName !== "SCRIPT" && cur.tagName !== "STYLE" && window.getComputedStyle(cur).whiteSpace !== "pre") {
                __remove_space(cur);
            }

            if (!add) continue;
            if (cur === end) add = false;

            // remove begin empty text node
            if (node.childNodes.length > 1 && dom.isText(cur) && !cur.textContent.match(/\S|\u00A0/)) {
                removed = true;
                if (cur === begin) {
                    so = 0;
                    begin = dom.lastChild(dom.hasContentBefore(dom.ancestorHavePreviousSibling(cur)));
                }
                if (cur === end) {
                    eo = 1;
                    end = dom.firstChild(dom.hasContentAfter(dom.ancestorHaveNextSibling(cur)));
                    if (dom.isText(end)) {
                        eo = end.textContent.length;
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
                var exp1 = /[\t\n\r ]+/g;
                var exp2 = /(?!([ ]|\u00A0)|^)\u00A0(?!([ ]|\u00A0)|$)/g;
                if (cur === begin) {
                    var temp = cur.textContent.substr(0, so);
                    var _temp = temp.replace(exp1, ' ').replace(exp2, ' ');
                    so -= temp.length - _temp.length;
                }
                if (cur === end) {
                    var temp = cur.textContent.substr(0, eo);
                    var _temp = temp.replace(exp1, ' ').replace(exp2, ' ');
                    eo -= temp.length - _temp.length;
                }
                var text = cur.textContent.replace(exp1, ' ').replace(exp2, ' ');
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
        eo: eo
    };
};
dom.node = function (node) {
    return node.tagName ? node : node.parentNode;
};
dom.pasteTextApply = "h1 h2 h3 h4 h5 h6 li p".split(" ");
dom.pasteTextClose = "h1 h2 h3 h4 h5 h6 p b bold i u code sup strong small li pre".split(" ");
dom.pasteText = function (textNode, offset, text, isOnlyText) {
    // clean the node
    var node = dom.node(textNode);
    var data = dom.merge(node.parentNode, textNode, offset, textNode, offset, null, true);
    data = dom.removeSpace(node.parentNode, data.sc, data.so, data.ec, data.eo);
    // Break the text node up
    if (data.sc.tagName) {
        if (node === data.sc.parentNode) {
            data.sc = node.insertBefore(document.createTextNode(" "), data.sc);
        } else if (node.firstChild && !dom.isBR(dom.firstChild(node))) {
            data.sc = node.insertBefore(document.createTextNode(" "), dom.firstChild(node));
        } else {
            data.sc = node.appendChild(document.createTextNode(" "));
        }
        data.so = 0;
    }
    data.sc.splitText(data.so);
    var first = data.sc;
    var last = data.sc.nextSibling;

    isOnlyText = isOnlyText || !text.match('\n');
    
    if (!isOnlyText) {
        // tag to close and open
        var tag = node.tagName.toLowerCase();
        if(dom.pasteTextApply.indexOf(tag) === -1) {
            text = text.split('\n').join("<br/>");
        } else {
            text = "<"+tag+">"+text.split('\n').join("</"+tag+"><"+tag+">")+"</"+tag+">";
        }

        var $text = $(text);

        // split parent node and insert text
        if(dom.pasteTextClose.indexOf(tag) !== -1) {
            var $next = $(node).clone().empty();
            $next.append( last );
            $(node).after( $next );
            $(node).after( $text );
        } else {
            $(data.sc).after( $text );
        }
    } else {
        first.appendData( text );
    }

    // clean the dom content
    data = dom.merge(node.parentNode.parentNode, last, 0, last, 0, null, true);
    data = dom.removeSpace(node.parentNode.parentNode, data.sc, data.so, data.ec, data.eo);

    // move caret
    range.create(data.sc, data.so, data.ec, data.eo).select();
};
dom.removeBetween = function (sc, so, ec, eo, towrite) {
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
        if (!dom.hasContentBefore(sc)) {
            sc.parentNode.insertBefore(document.createTextNode('\u00A0'), sc);
        }
    }
    if (!eo && sc !== ec) {
        ec = dom.lastChild(dom.hasContentBefore(dom.ancestorHavePreviousSibling(ec)));
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
        if (!dom.isNotBreakable(node)) {
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
            if (!dom.ancestor(nodes[i], ancestor_first_last) && !$.contains(nodes[i], before) && !$.contains(nodes[i], after)) {
                nodes[i].parentNode.removeChild(nodes[i]);
            }
        }

        sc = before ? dom.lastChild(before) : dom.firstChild(after);
        so = sc.textContent.length;

        if (before) {
            var text = sc.textContent.replace(/[ \t\n\r]+$/, '\u00A0');
            so -= sc.textContent.length - text.length;
            sc.textContent = text;
        }
        if (towrite && !node.firstChild && node.parentNode && !dom.isNotBreakable(node)) {
            var br = $("<br/>")[0];
            node.appendChild(br);
            sc = br;
            so = 0;
        }
        dom.autoMerge(sc, false);

    } else {

        var text = ancestor.textContent;
        ancestor.textContent = text.slice(0, so) + text.slice(eo, Infinity).replace(/^[ \t\n\r]+/, '\u00A0');

    }

    eo = so;
    if(!dom.isBR(sc) && !sc.textContent.match(/\S|\u00A0/) && !dom.isText(dom.hasContentBefore(sc)) && !dom.isText(dom.hasContentAfter(sc))) {
        ancestor = dom.node(sc);
        var text = document.createTextNode('\u00A0');
        $(sc).before(text);
        sc = text;
        so = 0;
        eo = 1;
    }
    return {
        sc: sc,
        so: so,
        ec: sc,
        eo: eo
    };
};
dom.indent = function (node) {
    var margin = parseFloat(node.style.marginLeft || 0)+1.5;
    node.style.marginLeft = margin + "em";
    return margin;
};
dom.outdent = function (node) {
    var margin = parseFloat(node.style.marginLeft || 0)-1.5;
    node.style.marginLeft = margin > 0 ? margin + "em" : "";
    return margin;
};
dom.scrollIntoViewIfNeeded = function (node) {
    var node = dom.node(node);

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
                while (parent != offsetParent &&
                    (parent.tagName === "BODY" || ["auto", "scroll"].indexOf(window.getComputedStyle(parent).overflowY) === -1)) {
                    parent = parent.parentNode;
                }
                node = parent;

                if (parent !== offsetParent) {
                    elY -= parent.offsetTop;
                    parent = null;
                }

                offsetParent = node.offsetParent;
            }

            if ((node.tagName === "BODY" || ["auto", "scroll"].indexOf(window.getComputedStyle(node).overflowY) !== -1) &&
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
dom.listBetween = function (sc, ec) {
    var nodes = [];
    var ancestor = dom.commonAncestor(sc, ec);
    dom.walkPoint({'node': sc, 'offset': 0}, {'node': ec, 'offset': 0}, function (point) {
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
    return $(node).closest('[contenteditable]').is('[contenteditable="true"]');
};

dom.isFont = function (node) {
    var nodeName = node && node.nodeName.toUpperCase();
    return node && (nodeName === "FONT" ||
        (nodeName === "SPAN" && (
            node.className.match(/(^|\s)fa(\s|$)/i) ||
            node.className.match(/(^|\s)(text|bg)-/i) ||
            (node.attributes.style && node.attributes.style.value.match(/(^|\s)(color|background-color):/i)))) );
};
dom.isVisibleText = function (textNode) {
  return !!textNode.textContent.match(/\S|\u00A0/);
};
/**
 * order the style of the node to compare 2 nodes and remove attribute if empty
 *
 * @param {Node} node
 * @return {String} className
 */
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
/**
 * order the class of the node to compare 2 nodes and remove attribute if empty
 *
 * @param {Node} node
 * @return {String} className
 */
dom.orderClass = function (node) {
    var className = node.getAttribute('class');
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
/**
 * return the current node (if text node, return parentNode)
 *
 * @param {Node} node
 * @return {Node} node
 */
dom.node = function (node) {
    return dom.isText(node) ? node.parentNode : node;
};
/**
 * move all childNode to an other node
 *
 * @param {Node} from
 * @param {Node} to
 */
dom.moveContent = function (from, to) {
  if (from === to) {
    return;
  }
  if (from.parentNode === to) {
    while (from.lastChild) {
      dom.insertAfter(from.lastChild, from);
    }
  } else {
    while (from.firstChild && from.firstChild != to) {
      to.appendChild(from.firstChild);
    }
  }
};

//////////////////////////////////////////////////////////////////////////////////////////////////////////

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
            sc = dom.lastChild(dom.hasContentBefore(dom.ancestorHavePreviousSibling(end)));
            so = sc.textContent.length;
        } else if (!eo) {
            ec = dom.lastChild(dom.hasContentBefore(dom.ancestorHavePreviousSibling(end)));
            eo = ec.textContent.length;
        } else {
            ec = dom.firstChild(dom.hasContentAfter(dom.ancestorHaveNextSibling(end)));
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
range.WrappedRange.prototype.deleteContents = function (towrite) {
    var prevBP = dom.removeBetween(this.sc, this.so, this.ec, this.eo, towrite);

    $(dom.node(prevBP.sc)).trigger("click"); // trigger click to disable and reanable editor and image handler
    return new range.WrappedRange(
      prevBP.sc,
      prevBP.so,
      prevBP.ec,
      prevBP.eo
    );
};
range.WrappedRange.prototype.clean = function (mergeFilter, all) {
    var node = dom.node(this.sc === this.ec ? this.sc : this.commonAncestor());
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

//////////////////////////////////////////////////////////////////////////////////////////////////////////

renderer.tplButtonInfo.fontsize = function (lang, options) {
    var items = options.fontSizes.reduce(function (memo, v) {
        return memo + '<li><a data-event="fontSize" href="#" data-value="' + v + '">' +
                  '<i class="fa fa-check"></i> ' + v +
                '</a></li>';
    }, '');

    var sLabel = '<span class="note-current-fontsize">11</span>';
    return renderer.getTemplate().button(sLabel, {
        title: lang.font.size,
        dropdown: '<ul class="dropdown-menu">' + items + '</ul>'
    });
};

//////////////////////////////////////////////////////////////////////////////////////////////////////////
/* add some text commands */

key.nameFromCode[46] = 'DELETE';
key.nameFromCode[27] = 'ESCAPE';

options.keyMap.pc['BACKSPACE'] = 'backspace';
options.keyMap.pc['DELETE'] = 'delete';
options.keyMap.pc['ENTER'] = 'enter';
options.keyMap.pc['ESCAPE'] = 'cancel';
options.keyMap.mac['SHIFT+TAB'] = 'untab';

options.keyMap.mac['BACKSPACE'] = 'backspace';
options.keyMap.mac['CMD+BACKSPACE'] = 'delete';
options.keyMap.mac['SHIFT+BACKSPACE'] = 'delete';
options.keyMap.mac['ENTER'] = 'enter';
options.keyMap.mac['ESCAPE'] = 'cancel';

$.summernote.pluginEvents.insertTable = function (event, editor, layoutInfo, sDim) {
  var $editable = layoutInfo.editable();
  var dimension = sDim.split('x');
  var rng = range.create();
  rng = rng.deleteContents();

  var isBodyContainer = dom.isBodyContainer;
  dom.isBodyContainer = dom.isNotBreakable;
  rng.insertNode(editor.table.createTable(dimension[0], dimension[1]));
  dom.isBodyContainer = isBodyContainer;

  editor.afterCommand($editable);
  event.preventDefault();
  return false;
};
$.summernote.pluginEvents.tab = function (event, editor, layoutInfo, outdent) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable, 'tab');
    var r = range.create();
    var outdent = outdent || false;

    if (r.isCollapsed()) {
        if (r.isOnCell() && r.isOnCellFirst()) {
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
            event.preventDefault();
            return false;
        }

        if (!r.sc.textContent.slice(0,r.so).match(/\S/) && r.isOnList()) {
            if (outdent) {
                $.summernote.pluginEvents.outdent(event, editor, layoutInfo);
            } else {
                $.summernote.pluginEvents.indent(event, editor, layoutInfo);
            }
        } else {
            if (!outdent){
                var next = r.sc.splitText(r.so);
                editor.typing.insertTab($editable, r, options.tabsize);
                r = range.create(next, 0, next, 0);
                r = dom.merge(r.sc.parentNode, r.sc, r.so, r.ec, r.eo, null, true);
                range.create(r.sc, r.so, r.ec, r.eo).select();
            } else {
                r = dom.merge(r.sc.parentNode, r.sc, r.so, r.ec, r.eo, null, true);
                r = range.create(r.sc, r.so, r.ec, r.eo);
                var next = r.sc.splitText(r.so);
                r.sc.textContent = r.sc.textContent.replace(/(\u00A0)+$/g, '');
                next.textContent = next.textContent.replace(/^(\u00A0)+/g, '');
                range.create(r.sc, r.sc.textContent.length, r.sc, r.sc.textContent.length).select();
            }
            event.preventDefault();
            return false;
        }
    }
    event.preventDefault();
    return false;
};
$.summernote.pluginEvents.untab = function (event, editor, layoutInfo) {
    return $.summernote.pluginEvents.tab(event, editor, layoutInfo, true);
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

    // table: add a tr
    var td = dom.ancestor(r.sc, dom.isCell);
    if (td && (r.sc === td || r.sc === td.lastChild || (dom.isBR(td.lastChild) && r.sc === td.lastChild.previousSibling)) && r.so === r.sc.textContent.length && r.isOnCell() && !dom.nextElementSibling(td)) {
        var $node = $(td.parentNode);
        var $clone = $node.clone();
        $clone.children().html(dom.blank);
        $node.after($clone);
        var node = dom.firstElementChild($clone[0]) || $clone[0];
        range.create(node, 0, node, 0).select();
        dom.scrollIntoViewIfNeeded(br);
        event.preventDefault();
        return false;
    }

    var contentBefore = r.sc.textContent.slice(0,r.so).match(/\S|\u00A0/);
    if (!contentBefore && dom.isText(r.sc)) {
        var node = r.sc.previousSibling;
        while (!contentBefore && node && dom.isText(node)) {
            contentBefore = dom.isVisibleText(node);
            node = node.previousSibling;
        }
    }

    var node = dom.node(r.sc);
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
        if (!node) {
            $(br).before($("<br/>")[0]);
        }
        node = br.nextSibling || br;
    } else if (last === node && dom.isBR(node)) {
        $(node).after(br);
        node = br;
    } else if (!r.so && r.isOnList() && !r.sc.textContent.length && !dom.ancestor(r.sc, dom.isLi).nextElementSibling) {
        // double enter on the end of a list = new line out of the list
        node = $('<p></p>').append(br).insertAfter(dom.ancestor(r.sc, dom.isList))[0];
        node = br;
    } else if (last === r.sc) {
        if (dom.isBR(last)) {
            last = last.parentNode;
        }
        var $node = $(last);
        var $clone = $node.clone().text("");
        $node.after($clone);
        node = dom.node(dom.firstElementChild($clone[0]) || $clone[0]);
        $(node).html(br);
        node = br;
    } else {
        node = dom.splitTree(last, {'node': r.sc, 'offset': r.so});
        if (!contentBefore) {
            var cur = dom.node(dom.lastChild(node.previousSibling));
            if (!dom.isBR(cur)) {
                $(cur).html(br);
            }
        }
        if (!node.textContent.match(/\S|\u00A0/)) {
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
    if (r && !r.isCollapsed()) {
        r = r.deleteContents(true);
        r.select();
    }

    // don't write in forbidden tag (like span for font awsome)
    var node = dom.firstChild(r.sc.tagName && r.so ? r.sc.childNodes[r.so] : r.sc);
    while (node.parentNode) {
        if (dom.isForbiddenNode(node)) {
            var text = node.previousSibling;
            if (text && dom.isText(text) && text.textContent.match(/\S|\u00A0/)) {
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

function summernote_keydown_clean (field) {
    setTimeout(function () {
        var r = range.create();
        if (!r) return;
        var node = r[field];
        while (dom.isText(node)) {node = node.parentNode;}
        node = node.parentNode;
        var data = dom.merge(node, r.sc, r.so, r.ec, r.eo, null, true);
        data = dom.removeSpace(node.parentNode, data.sc, data.so, data.sc, data.so);

        range.create(data.sc, data.so, data.sc, data.so).select();
    },0);
}

function remove_table_content(sc, ec) {
    var nodes = dom.listBetween(sc, ec);
    nodes.push(dom.node(sc), dom.node(ec));
    for (var i in nodes) {
        if (dom.isCell(nodes[i])) {
            $(nodes[i]).html("<br/>");
        }
    }
    event.preventDefault();
    return false;
}

$.summernote.pluginEvents.delete = function (event, editor, layoutInfo) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable, "delete");
    
    var r = range.create();
    if (!r.isContentEditable()) {
        return false;
    }
    if (!r.isCollapsed()) {
        if (dom.isCell(dom.node(r.sc)) || dom.isCell(dom.node(r.ec))) {
            return remove_table_content(r.sc, r.ec);
        }
        r = r.deleteContents();
        r.select();
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

    // media
    if (dom.isImg(node) || (!contentAfter && dom.isImg(dom.hasContentAfter(node)))) {
        var parent;
        var index;
        if (!dom.isImg(node)) {
            node = dom.hasContentAfter(node);
        }
        while (dom.isImg(node)) {
            parent = node.parentNode;
            index = dom.makeOffsetPath(parent, node)[0];
            if (index>0) {
                var next = node.previousSibling;
                range.create(next,next.textContent.length).select();
            }
            if (!dom.hasContentAfter(node) && !dom.hasContentBefore(node)) {
                parent.appendChild($('<br/>')[0]);
            }
            parent.removeChild(node);
            node = parent;
        }
    }
    // empty tag
    else if (!content.length && target.tagName && dom.isRemovableEmptyNode(dom.isBR(target) ? target.parentNode : target)) {
        if (node === $editable[0] || $.contains(node, $editable[0])) {
            event.preventDefault();
            return false;
        }
        var before = false;
        var next = dom.hasContentAfter(dom.ancestorHaveNextSibling(node));
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
            dom.isMergable(temp) &&
            dom.isMergable(temp2 = dom.hasContentAfter(temp)) &&
            temp.tagName === temp2.tagName &&
            (temp.tagName !== "LI" || !$('ul,ol', temp).length) && (temp2.tagName !== "LI" || !$('ul,ol', temp2).length) && // protect li
            !dom.isNotBreakable(temp) &&
            !dom.isNotBreakable(temp2)) {
        dom.autoMerge(target, false);
        var next = dom.firstChild(dom.hasContentAfter(dom.ancestorHaveNextSibling(target)));
        if (dom.isBR(next)) {
            range.create(next.previousSibling, next.previousSibling.textContent.length).select();
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

        if ((dom.isText(temp) || window.getComputedStyle(temp).display === "inline") && (dom.isText(temp2) || window.getComputedStyle(temp2).display === "inline")) {
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
    if (!r.isContentEditable()) {
        event.preventDefault();
        return false;
    }
    if (!r.isCollapsed()) {
        if (dom.isCell(dom.node(r.sc)) || dom.isCell(dom.node(r.ec))) {
            return remove_table_content(r.sc, r.ec);
        }
        r = r.deleteContents();
        r.select();
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
    r = range.create(data.sc, data.so);
    r.select();
    target = r.sc;
    offset = r.so;

    while (node.parentNode && !dom.hasContentAfter(node) && !dom.hasContentBefore(node) && !dom.isImg(node)) {node = node.parentNode;}

    var contentBefore = target.textContent.slice(0,offset).match(/\S|\u00A0/);
    var content = target.textContent.replace(/[ \t\r\n]+$/, '');
    var temp;
    var temp2;

    // delete media
    if (dom.isImg(node) || (!contentBefore && dom.isImg(dom.hasContentBefore(node)))) {
        if (!dom.isImg(node)) {
            node = dom.hasContentBefore(node);
        }
        range.createFromNode(node).select();
        $.summernote.pluginEvents.delete(event, editor, layoutInfo);
    }
    // table tr td
    else if (r.isOnCell() && !offset && (target === (temp = dom.ancestor(target, dom.isCell)) || target === temp.firstChild)) {
        if (dom.previousElementSibling(temp)) {
            var td = dom.previousElementSibling(temp);
            node = td.lastChild || td;
        } else {
            var tr = temp.parentNode;
            var prevTr = dom.previousElementSibling(tr);
            if (!$(temp.parentNode).text().match(/\S|\u00A0/)) {
                if (prevTr) {
                    tr.parentNode.removeChild(tr);
                    node = (dom.lastElementChild(prevTr).lastChild && dom.lastElementChild(prevTr).lastChild.tagName ? dom.lastElementChild(prevTr).lastChild.previousSibling : dom.lastElementChild(prevTr).lastChild) || dom.lastElementChild(prevTr);
                    range.create(node, node.textContent.length, node, node.textContent.length).select();
                }
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
        var prev = dom.hasContentBefore(dom.ancestorHavePreviousSibling(node));
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
        var prev = dom.firstChild(target);
        dom.autoMerge(target, true);
        range.create(prev, 0).select();
    }
    // jump to previous node for delete
    else if ((temp = dom.ancestorHavePreviousSibling(target)) && (temp2 = dom.hasContentBefore(temp)) && dom.isContentEditable(temp2)) {

        dom.removeSpace(temp2.parentNode, temp2, 0, temp, 0); // clean before jump for not select invisible space between 2 tag
        temp2 = dom.lastChild(temp2);
    
        r = range.create(temp2, temp2.textContent.length, temp2, temp2.textContent.length);
        r.select();

        if ((dom.isText(temp) || window.getComputedStyle(temp).display === "inline") && (dom.isText(temp2) || window.getComputedStyle(temp2).display === "inline")) {
            if (dom.isText(temp2)) {
                temp2.textContent = temp2.textContent.replace(/\S\s*$/, '');
            } else {
                $.summernote.pluginEvents.backspace(event, editor, layoutInfo);
            }
        }
    }

    var rng = range.create();
    if (rng) {
        $(dom.node(rng.sc)).trigger("click"); // trigger click to disable and reanable editor and image handler
        dom.scrollIntoViewIfNeeded(rng.sc.parentNode.previousElementSibling || rng.sc);
    }

    event.preventDefault();
    return false;
};

//////////////////////////////////////////////////////////////////////////////////////////////////////////
/* add list command (create a uggly dom for chrome) */

function isFormatNode(node) {
    return node.tagName && options.styleTags.indexOf(node.tagName.toLowerCase()) !== -1;
}

$.summernote.pluginEvents.insertUnorderedList = function (event, editor, layoutInfo, sorted) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable);

    var parent;
    var rng = range.create();
    var node = rng.sc;
    while (node && node !== $editable[0]) {

        parent = node.parentNode;
        if (node.tagName === (sorted ? "UL" : "OL")) {

            var ul = document.createElement(sorted ? "ol" : "ul");
            ul.className = node.className;
            parent.insertBefore(ul, node);
            while (node.firstChild) {
                ul.appendChild(node.firstChild);
            }
            parent.removeChild(node);
            rng.select();
            return;

        } else if (node.tagName === (sorted ? "OL" : "UL")) {

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
            rng.select();
            return;

        }
        node = parent;
    }

    var p0 = rng.sc;
    while (p0 && p0.parentNode && p0.parentNode !== $editable[0] && !isFormatNode(p0)) {
        p0 = p0.parentNode;
    }
    if (!p0) return;
    var p1 = rng.ec;
    while (p1 && p1.parentNode && p1.parentNode !== $editable[0] && !isFormatNode(p1)) {
        p1 = p1.parentNode;
    }
    if (!p0.parentNode || p0.parentNode !== p1.parentNode) {
        return;
    }

    var parent = p0.parentNode;
    var ul = document.createElement(sorted ? "ol" : "ul");
    parent.insertBefore(ul, p0);
    var childNodes = parent.childNodes;
    var brs = [];
    var begin = false;
    for (var i=0; i<childNodes.length; i++) {
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

    for (var i=0; i<brs.length; i++) {
        parent.removeChild(brs[i]);
    }
    rng.clean().select();
    event.preventDefault();
    return false;
};
$.summernote.pluginEvents.insertOrderedList = function (event, editor, layoutInfo) {
    return $.summernote.pluginEvents.insertUnorderedList(event, editor, layoutInfo, true);
};
$.summernote.pluginEvents.indent = function (event, editor, layoutInfo, outdent) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable);
    var r = range.create();

    var flag = false;
    function indentUL (UL, start, end) {
        var next;
        var tagName = UL.tagName;
        var node = UL.firstChild;
        var parent = UL.parentNode;
        var ul = document.createElement(tagName);
        var li = document.createElement("li");
        li.style.listStyle = "none";
        li.appendChild(ul);

        if (flag) {
            flag = 1;
        }

        // create and fill ul into a li
        while (node) {
            if (flag === 1 || node === start || $.contains(node, start)) {
                flag = true;
                node.parentNode.insertBefore(li, node);
            }
            next = dom.nextElementSibling(node);
            if (flag) {
                ul.appendChild(node);
            }
            if (node === end || $.contains(node, end)) {
                flag = false;
                break;
            }
            node = next;
        }

        var temp;
        var prev = dom.previousElementSibling(li);
        if (prev && prev.tagName === "LI" && (temp = dom.firstElementChild(prev)) && temp.tagName === tagName && ((dom.firstElementChild(prev) || prev.firstChild) !== ul)) {
            dom.doMerge(dom.firstElementChild(prev) || prev.firstChild, ul);
            li = prev;
            li.parentNode.removeChild(dom.nextElementSibling(li));
        }
        var next = dom.nextElementSibling(li);
        if (next && next.tagName === "LI" && (temp = dom.firstElementChild(next)) && temp.tagName === tagName && (dom.firstElementChild(li) !== dom.firstElementChild(next))) {
            dom.doMerge(dom.firstElementChild(li), dom.firstElementChild(next));
            li.parentNode.removeChild(dom.nextElementSibling(li));
        }
    }
    function outdenttUL (UL, start, end) {
        var next;
        var tagName = UL.tagName;
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
                ul = node.parentNode;
                li.parentNode.insertBefore(node, li);
                if (!ul.children.length) {
                    if (ul.parentNode.tagName === "LI") {
                        ul = ul.parentNode;
                    }
                    ul.parentNode.removeChild(ul);
                }
            }

            if (node === end || $.contains(node, end)) {
                flag = false;
                break;
            }
            node = next;
        }

        dom.merge(parent, start, 0, end, 1, null, true);
    }
    function indentOther (p, start, end) {
        if (p === start || $.contains(p, start)) {
            flag = true;
        }
        if (flag) {
            if (outdent) {
                dom.outdent(p);
            } else {
                dom.indent(p);
            }
        }
        if (p === end || $.contains(p, end)) {
            flag = false;
        }
    }

    var ancestor = r.commonAncestor();
    var $dom = $(ancestor);

    if (!dom.isList(ancestor)) {
        $dom = $(ancestor).children();
    }
    if (!$dom.length) {
        $dom = $(dom.ancestor(r.sc, dom.isList));
        if (!$dom.length) {
            $dom = $(r.sc).closest(options.styleTags.join(','));
        }
    }

    $dom.each(function () {
        if (flag || $.contains(this, r.sc)) {
            if (dom.isList(this)) {
                if (outdent) {
                    outdenttUL(this, r.sc, r.ec);
                } else {
                    indentUL(this, r.sc, r.ec);
                }
            } else if (isFormatNode(this)) {
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

//////////////////////////////////////////////////////////////////////////////////////////////////////////

$.summernote.pluginEvents.formatBlock = function (event, editor, layoutInfo, sTagName) {
    var $editable = layoutInfo.editable();
    $editable.data('NoteHistory').recordUndo($editable);
    event.preventDefault();

    var r = range.create();
    if (!r) {
        return;
    }
    r.reRange().select();

    if (sTagName === "blockquote" || sTagName === "pre") {
      sTagName = $.summernote.core.agent.isMSIE ? '<' + sTagName + '>' : sTagName;
      document.execCommand('FormatBlock', false, sTagName);
      return;
    }

    // fix by odoo because if you select a style in a li with no p tag all the ul is wrapped by the style tag
    var nodes = dom.listBetween(r.sc, r.ec);
    for (var i=0; i<nodes.length; i++) {
        if (dom.isBR(nodes[i]) || (dom.isText(nodes[i]) && nodes[i].textContent.match(/\S|\u00A0/)) || dom.isB(nodes[i]) || dom.isU(nodes[i]) || dom.isS(nodes[i]) || dom.isI(nodes[i]) || dom.isFont(nodes[i])) {
            var ancestor = dom.ancestor(nodes[i], isFormatNode);
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
    var node = range.create().sc.parentNode;
    document.execCommand('removeFormat');
    document.execCommand('removeFormat');
    var r = range.create();
    r = dom.merge(node, r.sc, r.so, r.ec, r.eo, null, true);
    range.create(r.sc, r.so, r.ec, r.eo).select();
    event.preventDefault();
    return false;
};
var fn_boutton_updateRecentColor = eventHandler.toolbar.button.updateRecentColor;
eventHandler.toolbar.button.updateRecentColor = function (elBtn, sEvent, sValue) {
    fn_boutton_updateRecentColor.call(this, elBtn, sEvent, sValue);
    var font = $(elBtn).closest('.note-color').find('.note-recent-color i')[0];

    if (sEvent === "foreColor") {
        if (sValue.indexOf('text-') !== -1) {
            font.className += ' ' + sValue;
            font.style.color = '';
        } else {
            font.className = font.className.replace(/(^|\s+)text-\S+/);
            font.style.color = sValue !== 'inherit' ? sValue : "";
        }
    } else {
        if (sValue.indexOf('bg-') !== -1) {
            font.className += ' ' + sValue;
            font.style.backgroundColor = "";
        } else {
            font.className = font.className.replace(/(^|\s+)bg-\S+/);
            font.style.backgroundColor = sValue !== 'inherit' ? sValue : "";
        }
    }
    event.preventDefault();
    return false;
};

options.fontSizes = [_t('Default'), 8, 9, 10, 11, 12, 14, 18, 24, 36, 48, 62];
$.summernote.pluginEvents.applyFont = function (event, editor, layoutInfo, color, bgcolor, size) {
    var rng = range.create();
    var startPoint = rng.getStartPoint();
    var endPoint = rng.getEndPoint();

    if (rng.isCollapsed() && !dom.isFont(rng.sc)) {
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
    if (endPoint.offset && endPoint.offset != dom.nodeLength(endPoint.node)) {
      var ancestor = dom.ancestor(endPoint.node, dom.isFont) || endPoint.node;
      dom.splitTree(ancestor, endPoint);
    }
    if (startPoint.offset && startPoint.offset != dom.nodeLength(startPoint.node)) {
      var ancestor = dom.ancestor(startPoint.node, dom.isFont) || startPoint.node;
      var node = dom.splitTree(ancestor, startPoint);
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
          (node != endPoint.node || endPoint.offset)) {

          nodes.push(point.node);

      }
    });
    nodes = list.unique(nodes);

        // If ico fa
    if (rng.isCollapsed()) {
        nodes.push(startPoint.node);
    }

    // apply font: foreColor, backColor, size (the color can be use a class text-... or bg-...)
    var node, font, $font, fonts = [], className;
    if (color || bgcolor || size) {
      for (var i=0; i<nodes.length; i++) {
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

        if (color) {
          for (var k=0; k<className.length; k++) {
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
          for (var k=0; k<className.length; k++) {
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
          if (!isNaN(size) && Math.abs(parseInt(window.getComputedStyle(font).fontSize, 10)-size)/size > 0.05) {
            font.style.fontSize = size + "px";
          }
        }
      }
    }

    // remove empty values
    // we must remove the value in 2 steps (applay inherit then remove) because some
    // browser like chrome have some time an error for the rendering and/or keep inherit
    for (var i=0; i<fonts.length; i++) {
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
    var nodes = [];
    dom.walkPoint(startPoint, endPoint, function (point) {
      nodes.push(point.node);
    });
    nodes = list.unique(nodes);

    function remove (node, to) {
      if (node === endPoint.node) {
        endPoint = dom.prevPoint(endPoint);
      }
      if (to) {
        dom.moveContent(node, to);
      }
      dom.remove(node);
    }

    // remove node without attributes (move content), and merge the same nodes
    var className2, style, style2, $prev;
    for (var i=0; i<nodes.length; i++) {
      node = nodes[i];

      if ((dom.isText(node) || dom.isBR(node)) && !dom.isVisibleText(node)) {
        remove(node);
        nodes.splice(i,1);
        i--;
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
        nodes.splice(i,1);
        i--;
        continue;
      }

      if (i>0 && (font = dom.ancestor(nodes[i-1], dom.isFont))) {
        className2 = font.getAttribute('class');
        style2 = font.getAttribute('style');
        if (node !== font && className == className2 && style == style2) {
          remove(node, font);
          nodes.splice(i,1);
          i--;
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
  var $editable = layoutInfo.editable();
  var oColor = JSON.parse(sObjColor);
  var foreColor = oColor.foreColor, backColor = oColor.backColor;

  if (foreColor) { $.summernote.pluginEvents.foreColor(event, editor, layoutInfo, foreColor); }
  if (backColor) { $.summernote.pluginEvents.backColor(event, editor, layoutInfo, backColor); }
};
$.summernote.pluginEvents.foreColor = function (event, editor, layoutInfo, foreColor) {
  var $editable = layoutInfo.editable();
  $.summernote.pluginEvents.applyFont(event, editor, layoutInfo, foreColor, null, null);
  editor.afterCommand($editable);
};
$.summernote.pluginEvents.backColor = function (event, editor, layoutInfo, backColor) {
  var $editable = layoutInfo.editable();
  var r = range.create();
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
  editor.afterCommand($editable);
};

//////////////////////////////////////////////////////////////////////////////////////////////////////////

options.onCreateLink = function (sLinkUrl) {
    if (sLinkUrl.indexOf('mailto:') === 0) {
      // pass
    } else if (sLinkUrl.indexOf('@') !== -1 && sLinkUrl.indexOf(':') === -1) {
      sLinkUrl =  'mailto:' + sLinkUrl;
    } else if (sLinkUrl.indexOf('://') === -1 && sLinkUrl.indexOf('/') !== 0 && sLinkUrl.indexOf('#') !== 0) {
      sLinkUrl = 'http://' + sLinkUrl;
    }
    return sLinkUrl;
};

//////////////////////////////////////////////////////////////////////////////////////////////////////////
/* table */

function summernote_table_scroll (event) {
    if (range.create().isOnCell()) {
        $('.o_table_handler').remove();
    }
}
function summernote_table_update (oStyle) {
    var r = range.create();
    if (!r || !r.isOnCell() || !r.isOnCellFirst()) {
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
var fn_popover_update = eventHandler.popover.update;
eventHandler.popover.update = function ($popover, oStyle, isAirMode) {
    fn_popover_update.call(this, $popover, oStyle, isAirMode);
    if(!!(isAirMode ? $popover : $popover.parent()).find('.note-table').length) {
        summernote_table_update(oStyle);
    }
};

//////////////////////////////////////////////////////////////////////////////////////////////////////////

function summernote_paste (event) {
    // keep norma feature if copy a picture
    var clipboardData = event.originalEvent.clipboardData;
    if (clipboardData.items) {
        var item = list.last(clipboardData.items);
        var isClipboardImage = item.kind === 'file' && item.type.indexOf('image/') !== -1;
        if (isClipboardImage) {
            return true;
        }
    }

    var $editable = $(event.currentTarget);
    $editable = $editable.is('[contenteditable]') ? $editable : $editable.find('[contenteditable]');
    $editable.data('NoteHistory').recordUndo($editable);

    if (["INPUT", "TEXTAREA"].indexOf(event.target.tagName) === -1) {
        var r = range.create();
        if (!r.isCollapsed()) {
            r = r.deleteContents();
            r.select();
        }

        var text = clipboardData.getData("text/plain").replace(/</g, "&lt;");
        dom.pasteText(r.sc, r.so, text);
        event.preventDefault();
        return false;
    }
}

var fn_attach = eventHandler.attach;
eventHandler.attach = function (oLayoutInfo, options) {
    var $editable = oLayoutInfo.editor.hasClass('note-editable') ? oLayoutInfo.editor : oLayoutInfo.editor.find('.note-editable');
    fn_attach.call(this, oLayoutInfo, options);
    oLayoutInfo.editor.on("paste", summernote_paste);
    $editable.on("scroll", summernote_table_scroll);
};
var fn_detach = eventHandler.detach;
eventHandler.detach = function (oLayoutInfo, options) {
    var $editable = oLayoutInfo.editor.hasClass('note-editable') ? oLayoutInfo.editor : oLayoutInfo.editor.find('.note-editable');
    fn_detach.call(this, oLayoutInfo, options);
    oLayoutInfo.editor.off("paste", summernote_paste);
    $editable.off("scroll", summernote_table_scroll);
    $('.o_table_handler').remove();
};

return $.summernote;

});
