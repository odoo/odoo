// TODO: trim support
// TODO: line number -> https://bugzilla.mozilla.org/show_bug.cgi?id=618650
// TODO: templates orverwritten could be called by t-call="__super__" ?
// TODO: t-set + t-value + children node == scoped variable ?
var QWeb2 = {
    expressions_cache: {},
    reserved_words: 'true,false,NaN,null,undefined,debugger,in,instanceof,new,function,return,this,typeof,eval,Math,RegExp,Array,Object,Date'.split(','),
    actions_precedence: 'foreach,if,call,set,esc,escf,raw,rawf,js,debug,log'.split(','),
    word_replacement: {
        'and': '&&',
        'or': '||',
        'gt': '>',
        'gte': '>=',
        'lt': '<',
        'lte': '<='
    },
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
                        return ' ' + o[0] + '="' + this.html_escape(o[1], true) + '"';
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
        xml_node_to_string : function(node, childs_only) {
            if (childs_only) {
                var childs = node.childNodes, r = [];
                for (var i = 0, ilen = childs.length; i < ilen; i++) {
                    r.push(this.xml_node_to_string(childs[i]));
                }
                return r.join('');
            } else {
                if (node.xml !== undefined) {
                    return node.xml;
                } else {
                    return (new XMLSerializer()).serializeToString(node);
                }
            }
        },
        xpath_selectNodes : function(node, expr) {
            if (node.selectNodes !== undefined) {
                return node.selectNodes(expr);
            } else {
                var xpath = new XPathEvaluator();
                try {
                    var result = xpath.evaluate(expr, node, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE, null);
                } catch(error) {
                    this.exception("Error with XPath expression '" + expr + "' : " + error);
                }
                var r = [];
                if (result != null) {
                    var element;
                    while (element = result.iterateNext()) {
                        r.push(element);
                    }
                }
                return r
            }
        },
        call: function(context, template, old_dict, _import, callback) {
            var new_dict = this.extend({}, old_dict);
            new_dict['__caller__'] = old_dict['__template__'];
            if (callback) {
                new_dict['__content__'] = callback(context, new_dict);
            }
            var r = context.engine._render(template, new_dict);
            if (_import) {
                if (_import === '*') {
                    this.extend(old_dict, new_dict, ['__caller__', '__template__']);
                } else {
                    _import = _import.split(',');
                    for (var i = 0, ilen = _import.length; i < ilen; i++) {
                        var v = _import[i];
                        old_dict[v] = new_dict[v];
                    }
                }
            }
            return r;
        },
        foreach: function(context, enu, as, old_dict, callback) {
            if (enu != null) {
                var size, new_dict = this.extend({}, old_dict);
                new_dict[as + "_all"] = enu;
                var as_value = as + "_value",
                    as_index = as + "_index",
                    as_first = as + "_first",
                    as_last = as + "_last",
                    as_parity = as + "_parity";
                if (size = enu.length) {
                    new_dict[as + "_size"] = size;
                    for (var j = 0, jlen = enu.length; j < jlen; j++) {
                        var cur = enu[j];
                        new_dict[as_value] = cur;
                        new_dict[as_index] = j;
                        new_dict[as_first] = j === 0;
                        new_dict[as_last] = j + 1 === size;
                        new_dict[as_parity] = (j % 2 == 1 ? 'odd' : 'even');
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
                    var index = 0;
                    for (var k in enu) {
                        if (enu.hasOwnProperty(k)) {
                            var v = enu[k];
                            new_dict[as_value] = v;
                            new_dict[as_index] = index;
                            new_dict[as_first] = index === 0;
                            new_dict[as_parity] = (j % 2 == 1 ? 'odd' : 'even');
                            new_dict[as] = k;
                            callback(context, new_dict);
                            index += 1;
                        }
                      }
                }
            } else {
                this.exception("No enumerator given to foreach", context);
            }
        }
    }
};

QWeb2.Engine = (function() {
    function Engine() {
        // TODO: handle prefix at template level : t-prefix="x"
        this.prefix = 't';
        this.debug = false;
        this.templates_resources = []; // TODO: implement this.reload()
        this.templates = {};
        this.compiled_templates = {};
        this.extend_templates = {};
        this.dict = {};
        this.tools = QWeb2.tools;
        this.jQuery = window.jQuery;
        for (var i = 0; i < arguments.length; i++) {
            this.add_template(arguments[i]);
        }
    }

    QWeb2.tools.extend(Engine.prototype, {
        add_template : function(template) {
            this.templates_resources.push(template);
            if (template.constructor === String) {
                template = this.load_xml(template);
            }
            var ec = (template.documentElement && template.documentElement.childNodes) || template.childNodes || [];
            for (var i = 0; i < ec.length; i++) {
                var node = ec[i];
                if (node.nodeType === 1) {
                    if (node.nodeName == 'parsererror') {
                        return this.tools.exception(node.innerText);
                    }
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
            return true;
        },
        load_xml : function(s) {
            s = s.replace(/^\s*|\s*$/g, '');
            if (this.tools.trim(s)[0] === '<') {
                return this.load_xml_string(s);
            } else {
                var req = this.get_xhr();
                if (req) {
                    // TODO: third parameter is async : https://developer.mozilla.org/en/XMLHttpRequest#open()
                    // do an on_ready in QWeb2{} that could be passed to add_template
                    req.open('GET', s, false);
                    req.send(null);
                    if (req.responseXML) {
                        if (req.responseXML.documentElement.nodeName == "parsererror") {
                            return this.tools.exception(req.responseXML.documentElement.childNodes[0].nodeValue);
                        }
                        return req.responseXML;
                    } else {
                        return this.load_xml_string(req.responseText);
                    }
                }
            }
        },
        load_xml_string : function(s) {
            if (window.DOMParser) {
                var dp = new DOMParser();
                var r = dp.parseFromString(s, "text/xml");
                if (r.body && r.body.firstChild && r.body.firstChild.nodeName == 'parsererror') {
                    return this.tools.exception(r.body.innerText);
                }
                return r;
            }
            var xDoc;
            try {
                // new ActiveXObject("Msxml2.DOMDocument.4.0");
                xDoc = new ActiveXObject("MSXML2.DOMDocument");
            } catch (e) {
                return this.tools.exception("Could not find a DOM Parser");
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
                return null;
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
                    "   /* START TEMPLATE */ try {\n" +
                    (e.compile()) + "\n" +
                    "   /* END OF TEMPLATE */ } catch(error) {\n" +
                    "       if (console && console.exception) console.exception(error);\n" +
                    "       context.engine.tools.exception('Runtime Error: ' + error, context);\n" +
                    "   }\n" +
                    "   return r.join('');";
        },
        render : function(template, dict) {
            if (this.debug && window['console'] !== undefined) {
                console.time("QWeb render template " + template);
            }
            var r = this._render(template, dict);
            if (this.debug && window['console'] !== undefined) {
                console.timeEnd("QWeb render template " + template);
            }
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
                    this.tools.exception("Error evaluating template: " + error, { template: name });
                }
                if (!tcompiled) {
                    this.tools.exception("Error evaluating template: (IE?)" + error, { template: name });
                }
                this.compiled_templates[template] = tcompiled;
                return this.render(template, dict);
            } else {
                return this.tools.exception("Template '" + template + "' not found");
            }
        },
        extend : function(template, extend_node) {
            if (!this.jQuery) {
                return this.tools.exception("Can't extend template " + template + " without jQuery");
            }
            for (var i = 0, ilen = extend_node.childNodes.length; i < ilen; i++) {
                var child = extend_node.childNodes[i];
                if (child.nodeType === 1) {
                    var xpath = child.getAttribute(this.prefix + '-xpath'),
                        jquery = child.getAttribute(this.prefix + '-jquery'),
                        operation = child.getAttribute(this.prefix + '-operation'),
                        target,
                        error_msg = "Error while extending template '" + template;
                    if (jquery) {
                        target = this.jQuery(jquery, this.templates[template]);
                    } else if (xpath) {
                        // NOTE: due to the XPath implementation, extending a template will only work once
                        // when using XPath because XPathResult won't match objects with other constructor than 'Element'
                        // As jQuery will create HTMLElements, xpath will ignore them then causing problems when a
                        // template has already been extended. XPath selectors will probably be removed in QWeb.
                        target = this.jQuery(this.tools.xpath_selectNodes(this.templates[template], xpath));
                    } else {
                        this.tools.exception(error_msg + "No expression given");
                    }
                    error_msg += "' (expression='" + (jquery || xpath) + "') : ";
                    var inner = this.tools.xml_node_to_string(child, true);
                    if (operation) {
                        var allowed_operations = "append,prepend,before,after,replace,inner".split(',');
                        if (this.tools.arrayIndexOf(allowed_operations, operation) == -1) {
                            this.tools.exception(error_msg + "Invalid operation : '" + operation + "'");
                        }
                        operation = {'replace' : 'replaceWith', 'inner' : 'html'}[operation] || operation;
                        target[operation](this.jQuery(inner));
                    } else {
                        try {
                            var f = new Function(['$'], inner);
                        } catch(error) {
                            return this.tools.exception("Parse " + error_msg + error);
                        }
                        try {
                            f.apply(target, [this.jQuery]);
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
        this.actions = {};
        this.actions_done = [];
        this.attributes = {};
        this.children = [];
        this._top = [];
        this._bottom = [];
        this._indent = 1;
        this.process_children = true;
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
                    this.actions[name] = attr.value;
                } else {
                    this.attributes[name] = attr.value;
                }
            }
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
                    if (chars[invar_pos - 1] !== '.' && QWeb2.tools.arrayIndexOf(QWeb2.reserved_words, invar) < 0) {
                        invar = QWeb2.word_replacement[invar] || ("dict['" + invar + "']");
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
        string_interpolation : function(s) {
            if (!s) {
              return "''";
            }
            var regex = /^{(.*)}(.*)/,
                src = s.split(/#/),
                r = [];
            for (var i = 0, ilen = src.length; i < ilen; i++) {
                var val = src[i],
                    m = val.match(regex);
                if (m) {
                    r.push("(" + this.format_expression(m[1]) + ")");
                    if (m[2]) {
                        r.push(this.engine.tools.js_escape(m[2]));
                    }
                } else if (!(i === 0 && val === '')) {
                    r.push(this.engine.tools.js_escape((i === 0 ? '' : '#') + val));
                }
            }
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
            for (var i = 0, ilen = QWeb2.actions_precedence.length; i < ilen; i++) {
                var a = QWeb2.actions_precedence[i];
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
            if (this.tag !== this.engine.prefix) {
                var tag = "<" + this.tag;
                for (var a in this.attributes) {
                    tag += this.engine.tools.gen_attribute([a, this.attributes[a]]);
                }
                this.top_string(tag);
                if (this.actions.att) {
                    this.top("r.push(context.engine.tools.gen_attribute(" + (this.format_expression(this.actions.att)) + "));");
                }
                for (var a in this.actions) {
                    var v = this.actions[a];
                    var m = a.match(/att-(.+)/);
                    if (m) {
                        this.top("r.push(context.engine.tools.gen_attribute(['" + m[1] + "', (" + (this.format_expression(v)) + ")]));");
                    }
                    var m = a.match(/attf-(.+)/);
                    if (m) {
                        this.top("r.push(context.engine.tools.gen_attribute(['" + m[1] + "', (" + (this.string_interpolation(v)) + ")]));");
                    }
                }
                if (this.children.length || this.actions.opentag === 'true') {
                    this.top_string(">");
                    this.bottom_string("</" + this.tag + ">");
                } else {
                    this.top_string("/>");
                }
            }
        },
        compile_action_if : function(value) {
            this.top("if (" + (this.format_expression(value)) + ") {");
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
            var _import = this.actions['import'] || '';
            if (this.children.length === 0) {
                return this.top("r.push(context.engine.tools.call(context, " + (this.engine.tools.js_escape(value)) + ", dict, " + (this.engine.tools.js_escape(_import)) + "));");
            } else {
                this.top("r.push(context.engine.tools.call(context, " + (this.engine.tools.js_escape(value)) + ", dict, " + (this.engine.tools.js_escape(_import)) + ", function(context, dict) {");
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
            this.top("r.push(context.engine.tools.html_escape(" + (this.format_expression(value)) + "));");
        },
        compile_action_escf : function(value) {
            this.top("r.push(context.engine.tools.html_escape(" + (this.string_interpolation(value)) + "));");
        },
        compile_action_raw : function(value) {
            this.top("r.push(" + (this.format_expression(value)) + ");");
        },
        compile_action_rawf : function(value) {
            this.top("r.push(" + (this.string_interpolation(value)) + ");");
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
            this.top("console.log(" + this.format_expression(value) + "});");
        }
    });
    return Element;
})();
