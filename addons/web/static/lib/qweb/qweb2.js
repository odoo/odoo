/*
Copyright (c) 2013, Fabien Meghazi

Released under the MIT license

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

// TODO: trim support
// TODO: line number -> https://bugzilla.mozilla.org/show_bug.cgi?id=618650
// TODO: templates orverwritten could be called by t-call="__super__" ?
// TODO: t-set + t-value + children node == scoped variable ?
var QWeb2 = {
    expressions_cache: { },
    RESERVED_WORDS: 'true,false,NaN,null,undefined,debugger,console,window,in,instanceof,new,function,return,this,typeof,eval,void,Math,RegExp,Array,Object,Date'.split(','),
    ACTIONS_PRECEDENCE: 'foreach,if,elif,else,call,set,tag,esc,raw,js,debug,log'.split(','),
    WORD_REPLACEMENT: {
        'and': '&&',
        'or': '||',
        'gt': '>',
        'gte': '>=',
        'lt': '<',
        'lte': '<='
    },
    VOID_ELEMENTS: 'area,base,br,col,embed,hr,img,input,keygen,link,menuitem,meta,param,source,track,wbr'.split(','),
    tools: {
        exception: function(message, context) {
            context = context || {};
            var prefix = 'QWeb2';
            if (context.template) {
                prefix += " - template['" + context.template + "']";
            }
            throw new Error(prefix + ": " + message);
        },
        warning : function(message) {
            if (typeof(window) !== 'undefined' && window.console) {
                window.console.warn(message);
            }
        },
        trim: function(s, mode) {
            switch (mode) {
                case "left":
                    return s.replace(/^\s*/, "");
                case "right":
                    return s.replace(/\s*$/, "");
                default:
                    return s.replace(/^\s*|\s*$/g, "");
            }
        },
        js_escape: function(s, noquotes) {
            return (noquotes ? '' : "'") + s.replace(/\r?\n/g, "\\n").replace(/'/g, "\\'") + (noquotes ? '' : "'");
        },
        html_escape: function(s, attribute) {
            if (s == null) {
                return '';
            }
            s = String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            if (attribute) {
                s = s.replace(/"/g, '&quot;');
            }
            return s;
        },
        gen_attribute: function(o) {
            if (o !== null && o !== undefined) {
                if (o.constructor === Array) {
                    if (o[1] !== null && o[1] !== undefined) {
                        return this.format_attribute(o[0], o[1]);
                    }
                } else if (typeof o === 'object') {
                    var r = '';
                    for (var k in o) {
                        if (o.hasOwnProperty(k)) {
                            r += this.gen_attribute([k, o[k]]);
                        }
                    }
                    return r;
                }
            }
            return '';
        },
        format_attribute: function(name, value) {
            return ' ' + name + '="' + this.html_escape(value, true) + '"';
        },
        extend: function(dst, src, exclude) {
            for (var p in src) {
                if (src.hasOwnProperty(p) && !(exclude && this.arrayIndexOf(exclude, p) !== -1)) {
                    dst[p] = src[p];
                }
            }
            return dst;
        },
        arrayIndexOf : function(array, item) {
            for (var i = 0, ilen = array.length; i < ilen; i++) {
                if (array[i] === item) {
                    return i;
                }
            }
            return -1;
        },
        get_element_sibling: function(node, dom_attr) {
            // This helper keeps support for IE8 which does not
            // implement DOMNode.(previous|next)ElementSibling
            var sibling = node[dom_attr];
            while (sibling && sibling.nodeType !== 1) {
                sibling = sibling[dom_attr];
            }
            return sibling;
        },
        xml_node_to_string : function(node, childs_only) {
            if (childs_only) {
                var childs = node.childNodes, r = [];
                for (var i = 0, ilen = childs.length; i < ilen; i++) {
                    r.push(this.xml_node_to_string(childs[i]));
                }
                return r.join('');
            } else {
                // avoid XMLSerializer with text node for IE
                if (node.nodeType == 3) {
                    return node.data;
                }
                if (typeof XMLSerializer !== 'undefined') {
                    return (new XMLSerializer()).serializeToString(node);
                } else {
                    switch(node.nodeType) {
                    case 1: return node.outerHTML;
                    case 4: return '<![CDATA[' + node.data + ']]>';
                    case 8: return '<!-- ' + node.data + '-->';
                    }
                    throw new Error('Unknown node type ' + node.nodeType);
                }
            }
        },
        call: function(context, template, old_dict, _import, callback) {
            var new_dict = this.extend({}, old_dict);
            new_dict['__caller__'] = old_dict['__template__'];
            if (callback) {
                new_dict[0] = callback(context, new_dict);
            }
            return context.engine._render(template, new_dict);
        },
        foreach: function(context, enu, as, old_dict, callback) {
            if (enu != null) {
                var index, jlen, cur;
                var new_dict = this.extend({}, old_dict);
                new_dict[as + "_all"] = enu;
                var as_value = as + "_value",
                    as_index = as + "_index",
                    as_first = as + "_first",
                    as_last = as + "_last",
                    as_parity = as + "_parity";
                if (enu instanceof Array) {
                    var size = enu.length;
                    new_dict[as + "_size"] = size;
                    for (index = 0, jlen = enu.length; index < jlen; index++) {
                        cur = enu[index];
                        new_dict[as_value] = cur;
                        new_dict[as_index] = index;
                        new_dict[as_first] = index === 0;
                        new_dict[as_last] = index + 1 === size;
                        new_dict[as_parity] = (index % 2 == 1 ? 'odd' : 'even');
                        if (cur.constructor === Object) {
                            this.extend(new_dict, cur);
                        }
                        new_dict[as] = cur;
                        callback(context, new_dict);
                    }
                } else if (enu.constructor == Number) {
                    var _enu = [];
                    for (var i = 0; i < enu; i++) {
                        _enu.push(i);
                    }
                    this.foreach(context, _enu, as, old_dict, callback);
                } else {
                    index = 0;
                    for (var k in enu) {
                        if (enu.hasOwnProperty(k)) {
                            cur = enu[k];
                            new_dict[as_value] = cur;
                            new_dict[as_index] = index;
                            new_dict[as_first] = index === 0;
                            new_dict[as_parity] = (index % 2 == 1 ? 'odd' : 'even');
                            new_dict[as] = k;
                            callback(context, new_dict);
                            index += 1;
                        }
                      }
                }

                _.each(Object.keys(old_dict), function(z) {
                    old_dict[z] = new_dict[z];
                });
            } else {
                this.exception("No enumerator given to foreach", context);
            }
        }
    }
};

QWeb2.Engine = (function() {
    function Engine() {
        // TODO: handle prefix at template level : t-prefix="x", don't forget to lowercase it
        this.prefix = 't';
        this.debug = false;
        this.templates_resources = []; // TODO: implement this.reload()
        this.templates = {};
        this.compiled_templates = {};
        this.extend_templates = {};
        this.default_dict = {};
        this.tools = QWeb2.tools;
        this.jQuery = window.jQuery;
        this.reserved_words = QWeb2.RESERVED_WORDS.slice(0);
        this.actions_precedence = QWeb2.ACTIONS_PRECEDENCE.slice(0);
        this.void_elements = QWeb2.VOID_ELEMENTS.slice(0);
        this.word_replacement = QWeb2.tools.extend({}, QWeb2.WORD_REPLACEMENT);
        this.preprocess_node = null;
        for (var i = 0; i < arguments.length; i++) {
            this.add_template(arguments[i]);
        }
    }

    QWeb2.tools.extend(Engine.prototype, {
        /**
         * Add a template to the engine
         *
         * @param {String|Document} template Template as string or url or DOM Document
         * @param {Function} [callback] Called when the template is loaded, force async request
         */
        add_template : function(template, callback) {
            var self = this;
            this.templates_resources.push(template);
            if (template.constructor === String) {
                return this.load_xml(template, function (err, xDoc) {
                    if (err) {
                        if (callback) {
                            return callback(err);
                        } else {
                            throw err;
                        }
                    }
                    self.add_template(xDoc, callback);
                });
            }
            template = this.preprocess(template);
            var ec = (template.documentElement && template.documentElement.childNodes) || template.childNodes || [];
            for (var i = 0; i < ec.length; i++) {
                var node = ec[i];
                if (node.nodeType === 1) {
                    var name = node.getAttribute(this.prefix + '-name');
                    var extend = node.getAttribute(this.prefix + '-extend');
                    if (name && extend) {
                        // Clone template and extend it
                        if (!this.templates[extend]) {
                            return this.tools.exception("Can't clone undefined template " + extend);
                        }
                        this.templates[name] = this.templates[extend].cloneNode(true);
                        extend = name;
                        name = undefined;
                    }
                    if (name) {
                        this.templates[name] = node;
                        this.compiled_templates[name] = null;
                    } else if (extend) {
                        delete(this.compiled_templates[extend]);
                        if (this.extend_templates[extend]) {
                            this.extend_templates[extend].push(node);
                        } else {
                            this.extend_templates[extend] = [node];
                        }
                    }
                }
            }
            if (callback) {
                callback(null, template);
            }
            return true;
        },
        preprocess: function(doc) {
            /**
             * Preprocess a template's document at load time.
             * This method is mostly used for template sanitization but could
             * also be overloaded for extended features such as translations, ...
             * Throws an exception if a template is invalid.
             *
             * @param {Document} doc Document containg the loaded templates
             * @return {Document} Returns the pre-processed/sanitized template
             */
            var self = this;
            var childs = (doc.documentElement && doc.documentElement.childNodes) || doc.childNodes || [];

            // Check for load errors
            for (var i = 0; i < childs.length; i++) {
                var node = childs[i];
                if (node.nodeType === 1 && node.nodeName == 'parsererror') {
                    return this.tools.exception(node.innerText);
                }
            }

            // Sanitize t-elif and t-else directives
            var tbranch = doc.querySelectorAll('[t-elif], [t-else]');
            for (var i = 0, ilen = tbranch.length; i < ilen; i++) {
                var node = tbranch[i];
                var prev_elem = self.tools.get_element_sibling(node, 'previousSibling');
                var pattr = function(name) { return prev_elem.getAttribute(name); }
                var nattr = function(name) { return +!!node.getAttribute(name); }
                if (prev_elem && (pattr('t-if') || pattr('t-elif'))) {
                    if (pattr('t-foreach')) {
                        return self.tools.exception("Error: t-if cannot stay at the same level as t-foreach when using t-elif or t-else");
                    }
                    if (['t-if', 't-elif', 't-else'].map(nattr).reduce(function(a, b) { return a + b; }) > 1) {
                        return self.tools.exception("Error: only one conditional branching directive is allowed per node");
                    }
                    // All text nodes between branch nodes are removed
                    var text_node;
                    while ((text_node = node.previousSibling) !== prev_elem) {
                        if (self.tools.trim(text_node.nodeValue)) {
                            return self.tools.exception("Error: text is not allowed between branching directives");
                        }
                        // IE <= 11.0 doesn't support ChildNode.remove
                        text_node.parentNode.removeChild(text_node);
                    }
                } else {
                    return self.tools.exception("Error: t-elif and t-else directives must be preceded by a t-if or t-elif directive");
                }
            }

            return doc;
        },
        load_xml : function(s, callback) {
            var self = this;
            var async = !!callback;
            s = this.tools.trim(s);
            if (s.charAt(0) === '<') {
                var tpl = this.load_xml_string(s);
                if (callback) {
                    callback(null, tpl);
                }
                return tpl;
            } else {
                var req = this.get_xhr();
                if (this.debug) {
                    s += '?debug=' + (new Date()).getTime(); // TODO fme: do it properly in case there's already url parameters
                }
                req.open('GET', s, async);
                if (async) {
                    req.addEventListener("load", function() {
                        // 0, not being a valid HTTP status code, is used by browsers
                        // to indicate success for a non-http xhr response
                        // (for example, using the file:// protocol)
                        // https://developer.mozilla.org/fr/docs/Web/API/XMLHttpRequest
                        // https://bugzilla.mozilla.org/show_bug.cgi?id=331610
                        if (req.status == 200 || req.status == 0) {
                            callback(null, self._parse_from_request(req));
                        } else {
                            callback(new Error("Can't load template " + s + ", http status " + req.status));
                        }
                    });
                }
                req.send(null);
                if (!async) {
                    return this._parse_from_request(req);
                }
            }
        },
        _parse_from_request: function(req) {
            var xDoc = req.responseXML;
            if (xDoc) {
                if (!xDoc.documentElement) {
                    throw new Error("QWeb2: This xml document has no root document : " + xDoc.responseText);
                }
                if (xDoc.documentElement.nodeName == "parsererror") {
                    throw new Error("QWeb2: Could not parse document :" + xDoc.documentElement.childNodes[0].nodeValue);
                }
                return xDoc;
            } else {
                return this.load_xml_string(req.responseText);
            }
        },
        load_xml_string : function(s) {
            if (window.DOMParser) {
                var dp = new DOMParser();
                var r = dp.parseFromString(s, "text/xml");
                if (r.body && r.body.firstChild && r.body.firstChild.nodeName == 'parsererror') {
                    throw new Error("QWeb2: Could not parse document :" + r.body.innerText);
                }
                return r;
            }
            var xDoc;
            try {
                xDoc = new ActiveXObject("MSXML2.DOMDocument");
            } catch (e) {
                throw new Error("Could not find a DOM Parser: " + e.message);
            }
            xDoc.async = false;
            xDoc.preserveWhiteSpace = true;
            xDoc.loadXML(s);
            return xDoc;
        },
        has_template : function(template) {
            return !!this.templates[template];
        },
        get_xhr : function() {
            if (window.XMLHttpRequest) {
                return new window.XMLHttpRequest();
            }
            try {
                return new ActiveXObject('MSXML2.XMLHTTP.3.0');
            } catch (e) {
                throw new Error("Could not get XHR");
            }
        },
        compile : function(node) {
            var e = new QWeb2.Element(this, node);
            var template = node.getAttribute(this.prefix + '-name');
            return  "   /* 'this' refers to Qweb2.Engine instance */\n" +
                    "   var context = { engine : this, template : " + (this.tools.js_escape(template)) + " };\n" +
                    "   dict = dict || {};\n" +
                    "   dict['__template__'] = '" + template + "';\n" +
                    "   var r = [];\n" +
                    "   /* START TEMPLATE */" +
                    (this.debug ? "" : " try {\n") +
                    (e.compile()) + "\n" +
                    "   /* END OF TEMPLATE */" +
                    (this.debug ? "" : " } catch(error) {\n" +
                    "       if (console && console.exception) console.exception(error);\n" +
                    "       context.engine.tools.exception('Runtime Error: ' + error, context);\n") +
                    (this.debug ? "" : "   }\n") +
                    "   return r.join('');";
        },
        render : function(template, dict) {
            dict = dict || {};
            QWeb2.tools.extend(dict, this.default_dict);
            /*if (this.debug && window['console'] !== undefined) {
                console.time("QWeb render template " + template);
            }*/
            var r = this._render(template, dict);
            /*if (this.debug && window['console'] !== undefined) {
                console.timeEnd("QWeb render template " + template);
            }*/
            return r;
        },
        _render : function(template, dict) {
            if (this.compiled_templates[template]) {
                return this.compiled_templates[template].apply(this, [dict || {}]);
            } else if (this.templates[template]) {
                var ext;
                if (ext = this.extend_templates[template]) {
                    var extend_node;
                    while (extend_node = ext.shift()) {
                        this.extend(template, extend_node);
                    }
                }
                var code = this.compile(this.templates[template]), tcompiled;
                try {
                    tcompiled = new Function(['dict'], code);
                } catch (error) {
                    if (this.debug && window.console) {
                        console.log(code);
                    }
                    this.tools.exception("Error evaluating template: " + error, { template: template });
                }
                if (!tcompiled) {
                    this.tools.exception("Error evaluating template: (IE?)" + error, { template: template });
                }
                this.compiled_templates[template] = tcompiled;
                return this.render(template, dict);
            } else {
                return this.tools.exception("Template '" + template + "' not found");
            }
        },
        extend : function(template, extend_node) {
            var jQuery = this.jQuery;
            if (!jQuery) {
                return this.tools.exception("Can't extend template " + template + " without jQuery");
            }
            var template_dest = this.templates[template];
            for (var i = 0, ilen = extend_node.childNodes.length; i < ilen; i++) {
                var child = extend_node.childNodes[i];
                if (child.nodeType === 1) {
                    var jquery = child.getAttribute(this.prefix + '-jquery'),
                        operation = child.getAttribute(this.prefix + '-operation'),
                        target,
                        error_msg = "Error while extending template '" + template;
                    if (jquery) {
                        target = jQuery(jquery, template_dest);
                        if (!target.length && window.console) {
                            console.debug('Can\'t find "'+jquery+'" when extending template '+template);
                        }
                    } else {
                        this.tools.exception(error_msg + "No expression given");
                    }
                    error_msg += "' (expression='" + jquery + "') : ";
                    if (operation) {
                        var allowed_operations = "append,prepend,before,after,replace,inner,attributes".split(',');
                        if (this.tools.arrayIndexOf(allowed_operations, operation) == -1) {
                            this.tools.exception(error_msg + "Invalid operation : '" + operation + "'");
                        }
                        operation = {'replace' : 'replaceWith', 'inner' : 'html'}[operation] || operation;
                        if (operation === 'attributes') {
                            jQuery('attribute', child).each(function () {
                                var attrib = jQuery(this);
                                target.attr(attrib.attr('name'), attrib.text());
                            });
                        } else {
                            target[operation](child.cloneNode(true).childNodes);
                        }
                    } else {
                        try {
                            var f = new Function(['$', 'document'], this.tools.xml_node_to_string(child, true));
                        } catch(error) {
                            return this.tools.exception("Parse " + error_msg + error);
                        }
                        try {
                            f.apply(target, [jQuery, template_dest.ownerDocument]);
                        } catch(error) {
                            return this.tools.exception("Runtime " + error_msg + error);
                        }
                    }
                }
            }
        }
    });
    return Engine;
})();

QWeb2.Element = (function() {
    function Element(engine, node) {
        this.engine = engine;
        this.node = node;
        this.tag = node.tagName;
        this.actions = {tag: this.tag};
        this.actions_done = [];
        this.attributes = {};
        this.children = [];
        this._top = [];
        this._bottom = [];
        this._indent = 1;
        this.process_children = true;
        this.is_void_element = ~QWeb2.tools.arrayIndexOf(this.engine.void_elements, this.tag);
        var childs = this.node.childNodes;
        if (childs) {
            for (var i = 0, ilen = childs.length; i < ilen; i++) {
                this.children.push(new QWeb2.Element(this.engine, childs[i]));
            }
        }
        var attrs = this.node.attributes;
        if (attrs) {
            for (var j = 0, jlen = attrs.length; j < jlen; j++) {
                var attr = attrs[j];
                var name = attr.name;
                var m = name.match(new RegExp("^" + this.engine.prefix + "-(.+)"));
                if (m) {
                    name = m[1];
                    if (name === 'name') {
                        continue;
                    }
                    if (name.match(/^attf?(-.*)?/)) {
                        this.attributes[m[0]] = attr.value;
                    } else {
                        this.actions[name] = attr.value;
                    }
                } else {
                    this.attributes[name] = attr.value;
                }
            }
        }
        if (this.engine.preprocess_node) {
            this.engine.preprocess_node.call(this);
        }
    }

    QWeb2.tools.extend(Element.prototype, {
        compile : function() {
            var r = [],
                instring = false,
                lines = this._compile().split('\n');
            for (var i = 0, ilen = lines.length; i < ilen; i++) {
                var m, line = lines[i];
                if (m = line.match(/^(\s*)\/\/@string=(.*)/)) {
                    if (instring) {
                        if (this.engine.debug) {
                            // Split string lines in indented r.push arguments
                            r.push((m[2].indexOf("\\n") != -1 ? "',\n\t" + m[1] + "'" : '') + m[2]);
                        } else {
                            r.push(m[2]);
                        }
                    } else {
                        r.push(m[1] + "r.push('" + m[2]);
                        instring = true;
                    }
                } else {
                    if (instring) {
                        r.push("');\n");
                    }
                    instring = false;
                    r.push(line + '\n');
                }
            }
            return r.join('');
        },
        _compile : function() {
            switch (this.node.nodeType) {
                case 3:
                case 4:
                    this.top_string(this.node.data);
                break;
                case 1:
                    this.compile_element();
            }
            var r = this._top.join('');
            if (this.process_children) {
                for (var i = 0, ilen = this.children.length; i < ilen; i++) {
                    var child = this.children[i];
                    child._indent = this._indent;
                    r += child._compile();
                }
            }
            r += this._bottom.join('');
            return r;
        },
        format_expression : function(e) {
            /* Naive format expression builder. Replace reserved words and variables to dict[variable]
             * Does not handle spaces before dot yet, and causes problems for anonymous functions. Use t-js="" for that */
             if (QWeb2.expressions_cache[e]) {
              return QWeb2.expressions_cache[e];
            }
            var chars = e.split(''),
                instring = '',
                invar = '',
                invar_pos = 0,
                r = '';
            chars.push(' ');
            for (var i = 0, ilen = chars.length; i < ilen; i++) {
                var c = chars[i];
                if (instring.length) {
                    if (c === instring && chars[i - 1] !== "\\") {
                        instring = '';
                    }
                } else if (c === '"' || c === "'") {
                    instring = c;
                } else if (c.match(/[a-zA-Z_\$]/) && !invar.length) {
                    invar = c;
                    invar_pos = i;
                    continue;
                } else if (c.match(/\W/) && invar.length) {
                    // TODO: Should check for possible spaces before dot
                    if (chars[invar_pos - 1] !== '.' && QWeb2.tools.arrayIndexOf(this.engine.reserved_words, invar) < 0) {
                        invar = this.engine.word_replacement[invar] || ("dict['" + invar + "']");
                    }
                    r += invar;
                    invar = '';
                } else if (invar.length) {
                    invar += c;
                    continue;
                }
                r += c;
            }
            r = r.slice(0, -1);
            QWeb2.expressions_cache[e] = r;
            return r;
        },
        format_str: function (e) {
            if (e == '0') {
                return 'dict[0]';
            }
            return this.format_expression(e);
        },
        string_interpolation : function(s) {
            var _this = this;
            if (!s) {
              return "''";
            }
            function append_literal(s) {
                s && r.push(_this.engine.tools.js_escape(s));
            }

            var re = /(?:#{(.+?)}|{{(.+?)}})/g, start = 0, r = [], m;
            while (m = re.exec(s)) {
                // extract literal string between previous and current match
                append_literal(s.slice(start, re.lastIndex - m[0].length));
                // extract matched expression
                r.push('(' + this.format_str(m[2] || m[1]) + ')');
                // update position of new matching
                start = re.lastIndex;
            }
            // remaining text after last expression
            append_literal(s.slice(start));

            return r.join(' + ');
        },
        indent : function() {
            return this._indent++;
        },
        dedent : function() {
            if (this._indent !== 0) {
                return this._indent--;
            }
        },
        get_indent : function() {
            return new Array(this._indent + 1).join("\t");
        },
        top : function(s) {
            return this._top.push(this.get_indent() + s + '\n');
        },
        top_string : function(s) {
            return this._top.push(this.get_indent() + "//@string=" + this.engine.tools.js_escape(s, true) + '\n');
        },
        bottom : function(s) {
            return this._bottom.unshift(this.get_indent() + s + '\n');
        },
        bottom_string : function(s) {
            return this._bottom.unshift(this.get_indent() + "//@string=" + this.engine.tools.js_escape(s, true) + '\n');
        },
        compile_element : function() {
            for (var i = 0, ilen = this.engine.actions_precedence.length; i < ilen; i++) {
                var a = this.engine.actions_precedence[i];
                if (a in this.actions) {
                    var value = this.actions[a];
                    var key = 'compile_action_' + a;
                    if (this[key]) {
                        this[key](value);
                    } else if (this.engine[key]) {
                        this.engine[key].call(this, value);
                    } else {
                        this.engine.tools.exception("No handler method for action '" + a + "'");
                    }
                }
            }
        },
        compile_action_tag : function() {
            if (this.tag.toLowerCase() !== this.engine.prefix) {
                this.top_string("<" + this.tag);
                for (var a in this.attributes) {
                    var v = this.attributes[a];
                    var d = a.split('-');
                    if (d[0] === this.engine.prefix && d.length > 1) {
                        if (d.length === 2) {
                            this.top("r.push(context.engine.tools.gen_attribute(" + (this.format_expression(v)) + "));");
                        } else {
                            this.top("r.push(context.engine.tools.gen_attribute(['" + d.slice(2).join('-') + "', (" +
                                (d[1] === 'att' ? this.format_expression(v) : this.string_interpolation(v)) + ")]));");
                        }
                    } else {
                        this.top_string(this.engine.tools.gen_attribute([a, v]));
                    }
                }

                if (this.actions.opentag === 'true' || (!this.children.length && this.is_void_element)) {
                    // We do not enforce empty content on void elements
                    // because QWeb rendering is not necessarily html.
                    this.top_string("/>");
                } else {
                    this.top_string(">");
                    this.bottom_string("</" + this.tag + ">");
                }
            }
        },
        compile_action_if : function(value) {
            this.top("if (" + (this.format_expression(value)) + ") {");
            this.bottom("}");
            this.indent();
        },
        compile_action_elif : function(value) {
            this.top("else if (" + (this.format_expression(value)) + ") {");
            this.bottom("}");
            this.indent();
        },
        compile_action_else : function(value) {
            this.top("else {");
            this.bottom("}");
            this.indent();
        },
        compile_action_foreach : function(value) {
            var as = this.actions['as'] || value.replace(/[^a-zA-Z0-9]/g, '_');
            //TODO: exception if t-as not valid
            this.top("context.engine.tools.foreach(context, " + (this.format_expression(value)) + ", " + (this.engine.tools.js_escape(as)) + ", dict, function(context, dict) {");
            this.bottom("});");
            this.indent();
        },
        compile_action_call : function(value) {
            if (this.children.length === 0) {
                return this.top("r.push(context.engine.tools.call(context, " + (this.string_interpolation(value)) + ", dict));");
            } else {
                this.top("r.push(context.engine.tools.call(context, " + (this.string_interpolation(value)) + ", dict, null, function(context, dict) {");
                this.bottom("}));");
                this.indent();
                this.top("var r = [];");
                return this.bottom("return r.join('');");
            }
        },
        compile_action_set : function(value) {
            var variable = this.format_expression(value);
            if (this.actions['value']) {
                if (this.children.length) {
                    this.engine.tools.warning("@set with @value plus node chidren found. Children are ignored.");
                }
                this.top(variable + " = (" + (this.format_expression(this.actions['value'])) + ");");
                this.process_children = false;
            } else {
                if (this.children.length === 0) {
                    this.top(variable + " = '';");
                } else if (this.children.length === 1 && this.children[0].node.nodeType === 3) {
                    this.top(variable + " = " + (this.engine.tools.js_escape(this.children[0].node.data)) + ";");
                    this.process_children = false;
                } else {
                    this.top(variable + " = (function(dict) {");
                    this.bottom("})(dict);");
                    this.indent();
                    this.top("var r = [];");
                    this.bottom("return r.join('');");
                }
            }
        },
        compile_action_esc : function(value) {
            this.top("var t = " + this.format_str(value) + ";");
            this.top("if (t != null) r.push(context.engine.tools.html_escape(t));");
            this.top("else {");
            this.bottom("}");
            this.indent();
        },
        compile_action_raw : function(value) {
            this.top("var t = " + this.format_str(value) + ";");
            this.top("if (t != null) r.push(t);");
            this.top("else {");
            this.bottom("}");
            this.indent();
        },
        compile_action_js : function(value) {
            this.top("(function(" + value + ") {");
            this.bottom("})(dict);");
            this.indent();
            var lines = this.engine.tools.xml_node_to_string(this.node, true).split(/\r?\n/);
            for (var i = 0, ilen = lines.length; i < ilen; i++) {
                this.top(lines[i]);
            }
            this.process_children = false;
        },
        compile_action_debug : function(value) {
            this.top("debugger;");
        },
        compile_action_log : function(value) {
            this.top("console.log(" + this.format_expression(value) + ");");
        }
    });
    return Element;
})();
