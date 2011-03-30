// vim:set noet fdm=syntax fdl=0 fdc=3 fdn=2:
//---------------------------------------------------------
// QWeb javascript
//---------------------------------------------------------

/*
	TODO

		String parsing
			if (window.DOMParser) {
				parser=new DOMParser();
				xmlDoc=parser.parseFromString(text,"text/xml");
			} else {
				xmlDoc=new ActiveXObject("Msxml2.DOMDocument.4.0");
				xmlDoc=new ActiveXObject("Microsoft.XMLDOM");
					Which versions to try, it's confusing...
				xmlDoc.async="false";
				xmlDoc.async=false;
				xmlDoc.preserveWhiteSpace=true;
				xmlDoc.load("f.xml");
				xmlDoc.loadXML(text);  ?
			}

		Support space in IE by reparsing the responseText
			xmlhttp.responseXML.loadXML(xmlhttp.responseText); ?

		Preprocess: (nice optimization) 
			preprocess by flattening all non t- element to a TEXT_NODE.
			count the number of "\n" in text nodes to give an aproximate LINE NUMBER on elements for error reporting
			if from IE HTMLDOM use if(a[i].specified) to avoid 88 empty attributes per element during the preprocess, 

		implement t-trim 'left' 'right' 'both', is it needed ? inner=render_trim(l_inner.join(), t_att)

		Ruby/python: to backport from javascript to python/ruby render_node to use regexp, factorize foreach %var, t-att test for tuple(attname,value)

	DONE
		we reintroduced t-att-id, no more t-esc-id because of the new convention t-att="["id","val"]"
*/

var QWeb = {
    templates:{},
    prefix:"t",
    reg:new RegExp(),
    tag:{},
    att:{},
    ValueException: function (value, message) {
        this.value = value;
        this.message = message;
    },
    eval_object:function(e, v) {
        // TODO: Currently this will also replace and, or, ... in strings. Try
        // 'hi boys and girls' != '' and 1 == 1  -- will be replaced to : 'hi boys && girls' != '' && 1 == 1
        // try to find a solution without tokenizing
        e = '(' + e + ')';
        e = e.replace(/\band\b/g, " && ");
        e = e.replace(/\bor\b/g, " || ");
        e = e.replace(/\bgt\b/g, " > ");
        e = e.replace(/\bgte\b/g, " >= ");
        e = e.replace(/\blt\b/g, " < ");
        e = e.replace(/\blte\b/g, " <= ");
        if (v[e] != undefined) {
            return v[e];
        } else {
            with (v) return eval(e);
        }
    },
    eval_str:function(e, v) {
        var r = this.eval_object(e, v);
        r = (typeof(r) == "undefined" || r == null) ? "" : r.toString();
        return e == "0" ? v["0"] : r;
    },
    eval_format:function(e, v) {
        var m, src = e.split(/#/), r = src[0];
        for (var i = 1; i < src.length; i++) {
            if (m = src[i].match(/^{(.*)}(.*)/)) {
                r += this.eval_str(m[1], v) + m[2];
            } else {
                r += "#" + src[i];
            }
        }
        return r;
    },
    eval_bool:function(e, v) {
        return !!this.eval_object(e, v);
    },
    trim : function(v, mode) {
        if (!v || !mode) return v;
        switch (mode) {
            case 'both':
                return v.replace(/^\s*|\s*$/g, "");
            case "left":
                return v.replace(/^\s*/, "");
            case "right":
                return v.replace(/\s*$/, "");
        }
        throw new QWeb.ValueException(
            mode, "unknown trimming mode, trim mode must follow the pattern '[inner] (left|right|both)'");
    },
    escape_text:function(s) {
        return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    },
    escape_att:function(s) {
        return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    },
    render_node : function(e, v, inner_trim) {
        if (e.nodeType == 3) {
            return inner_trim ? this.trim(e.data, inner_trim) : e.data;
        }
        if (e.nodeType == 1) {
            var g_att = {};
            var t_att = {};
            var t_render = null;
            var a = e.attributes;
            for (var i = 0; i < a.length; i++) {
                var an = a[i].name,av = a[i].value;
                var m;
                if (m = an.match(this.reg)) {
                    var n = m[1];
                    if (n == "eval") {
                        n = m[2].substring(1);
                        av = this.eval_str(av, v);
                    }
                    var f;
                    if (f = this.att[n]) {
                        this[f](e, t_att, g_att, v, m[2], av);
                    } else if (f = this.tag[n]) {
                        t_render = f;
                    }
                    t_att[n] = av;
                } else {
                    g_att[an] = av;
                }
            }
            if (inner_trim && !t_att["trim"]) {
                t_att["trim"] = "inner " + inner_trim;
            }
            if (t_render) {
                return this[t_render](e, t_att, g_att, v);
            }
            return this.render_element(e, t_att, g_att, v);
        }
        return "";
    },
    render_element:function(e, t_att, g_att, v) {
        var inner = "", ec = e.childNodes, trim = t_att["trim"], inner_trim;
        if (trim) {
            if (/\binner\b/.test(trim)) {
                inner_trim = true;
                if (trim == 'inner') {
                    trim = "both";
                }
            }
            var tm = /\b(both|left|right)\b/.exec(trim);
            if (tm) trim = tm[1];
        }
        for (var i = 0; i < ec.length; i++) {
            inner += inner_trim ? this.trim(this.render_node(ec[i], v, inner_trim ? trim : null), trim) : this.render_node(ec[i], v, inner_trim ? trim : null);
        }
        if (trim && !inner_trim) {
            inner = this.trim(inner, trim);
        }
        if (e.tagName == this.prefix) {
            return inner;
        }
        var att = "";
        for (var an in g_att) {
            att += " " + an + '="' + this.escape_att(g_att[an]) + '"';
        }
        return inner.length ? "<" + e.tagName + att + ">" + inner + "</" + e.tagName + ">" : "<" + e.tagName + att + "/>";
    },
    render_att_att:function(e, t_att, g_att, v, ext, av) {
        if (ext) {
            var attv = this.eval_object(av, v);
            if (attv != null) {
                g_att[ext.substring(1)] = attv.toString();
            }
        } else {
            var o = this.eval_object(av, v);
            if (o != null) {
                // TODO: http://bonsaiden.github.com/JavaScript-Garden/#types.typeof
                if (o.constructor == Array && o.length > 1 && o[1] != null) {
                    g_att[o[0]] = new String(o[1]);
                } else if (o.constructor == Object) {
                    for (var i in o) {
                    	if(o[i]!=null) {
                    		g_att[i] = new String(o[i]);
                    	}
                    }
                }
            }
        }
    },
    render_att_attf:function(e, t_att, g_att, v, ext, av) {
        g_att[ext.substring(1)] = this.eval_format(av, v);
    },
    render_tag_raw:function(e, t_att, g_att, v) {
        return this.eval_str(t_att["raw"], v);
    },
    render_tag_rawf:function(e, t_att, g_att, v) {
        return this.eval_format(t_att["rawf"], v);
    },
    /*
     * Idea: if the name of the tag != t render the tag around the value <a name="a" t-esc="label"/>
     */
    render_tag_esc:function(e, t_att, g_att, v) {
        return this.escape_text(this.eval_str(t_att["esc"], v));
    },
    render_tag_escf:function(e, t_att, g_att, v) {
        return this.escape_text(this.eval_format(t_att["escf"], v));
    },
    render_tag_if:function(e, t_att, g_att, v) {
        return this.eval_bool(t_att["if"], v) ? this.render_element(e, t_att, g_att, v) : "";
    },
    render_tag_set:function(e, t_att, g_att, v) {
        var ev = t_att["value"];
        if (ev && ev.constructor != Function) {
            v[t_att["set"]] = this.eval_object(ev, v);
        } else {
            v[t_att["set"]] = this.render_element(e, t_att, g_att, v);
        }
        return "";
    },
    render_tag_call:function(e, t_att, g_att, v) {
        var d = v;
        if (!t_att["import"]) {
            d = {};
            for (var i in v) {
                d[i] = v[i];
            }
        }
        d["0"] = this.render_element(e, t_att, g_att, d);
        return this.render(t_att["call"], d);
    },
    render_tag_js:function(e, t_att, g_att, v) {
        var r = this.eval_str(this.render_element(e, t_att, g_att, v), v);
        return t_att["js"] != "quiet" ? r : "";
    },
    /**
     * Renders a foreach loop (@t-foreach).
     *
     * Adds the following elements to its context, where <code>${name}</code>
     * is specified via <code>@t-as</code>:
     * * <code>${name}</code> The current element itself
     * * <code>${name}_value</code> Same as <code>${name}</code>
     * * <code>${name}_index</code> The 0-based index of the current element
     * * <code>${name}_first</code> Whether the current element is the first one
     * * <code>${name}_parity</code> odd|even (as strings)
     * * <code>${name}_all</code> The iterated collection itself
     *
     * If the collection being iterated is an array, also adds:
     * * <code>${name}_last</code> Whether the current element is the last one
     * * All members of the current object
     *
     * If the collection being iterated is an object, the value is actually the object's key
     *
     * @param e ?
     * @param t_att attributes of the element being <code>t-foreach</code>'d
     * @param g_att ?
     * @param old_context the context in which the foreach is evaluated
     */
    render_tag_foreach:function(e, t_att, g_att, old_context) {
        var expr = t_att["foreach"];
        var enu = this.eval_object(expr, old_context);
        var ru = [];
        if (enu) {
            var val = t_att['as'] || expr.replace(/[^a-zA-Z0-9]/g, '_');
            var context = {};
            for (var i in old_context) {
                context[i] = old_context[i];
            }
            context[val + "_all"] = enu;
            var val_value = val + "_value",
                val_index = val + "_index",
                val_first = val + "_first",
                val_last = val + "_last",
                val_parity = val + "_parity";
            var size = enu.length;
            if (size) {
                context[val + "_size"] = size;
                for (var j = 0; j < size; j++) {
                    var cur = enu[j];
                    context[val_value] = cur;
                    context[val_index] = j;
                    context[val_first] = j == 0;
                    context[val_last] = j + 1 == size;
                    context[val_parity] = (j % 2 == 1 ? 'odd' : 'even');
                    if (cur.constructor == Object) {
                        for (var k in cur) {
                            context[k] = cur[k];
                        }
                    }
                    context[val] = cur;
                    var r = this.render_element(e, t_att, g_att, context);
                    ru.push(r);
                }
            } else {
                var index = 0;
                for (cur in enu) {
                    context[val_value] = cur;
                    context[val_index] = index;
                    context[val_first] = index == 0;
                    context[val_parity] = (index % 2 == 1 ? 'odd' : 'even');
                    context[val] = cur;
                    ru.push(this.render_element(e, t_att, g_att, context));
                    index += 1;
                }
            }
            return ru.join("");
        } else {
            return "qweb: foreach " + expr + " not found.";
        }
    },
    hash:function() {
        var l = [], m;
        for (var i in this) {
            if (m = i.match(/render_tag_(.*)/)) {
                this.tag[m[1]] = i;
                l.push(m[1]);
            } else if (m = i.match(/render_att_(.*)/)) {
                this.att[m[1]] = i;
                l.push(m[1]);
            }
        }
        l.sort(function(a, b) {
            return a.length > b.length ? -1 : 1;
        });
        var s = "^" + this.prefix + "-(eval|" + l.join("|") + "|.*)(.*)$";
        this.reg = new RegExp(s);
    },
    /**
     * returns the correct XMLHttpRequest instance for the browser, or null if
     * it was not able to build any XHR instance.
     *
     * @returns XMLHttpRequest|MSXML2.XMLHTTP.3.0|null
     */
    get_xhr:function () {
        if (window.XMLHttpRequest) {
            return new window.XMLHttpRequest();
        }
        try {
            return new ActiveXObject('MSXML2.XMLHTTP.3.0');
        } catch(e) {
            return null;
        }
    },
    load_xml:function(s) {
        var xml;
        if (s[0] == "<") {
            /*
             manque ca pour sarrisa
             if(window.DOMParser){
             mozilla
             if(!window.DOMParser){
             var doc = Sarissa.getDomDocument();
             doc.loadXML(sXml);
             return doc;
             };
             };
             */
        } else {
            var req = this.get_xhr();
            if (req) {
                req.open("GET", s, false);
                req.send(null);
                //if ie r.setRequestHeader("If-Modified-Since", "Sat, 1 Jan 2000 00:00:00 GMT");
                xml = req.responseXML;
                /*
                 TODO
                 if intsernetexploror
                 getdomimplmentation() for try catch
                 responseXML.getImplet
                 d=domimple()
                 d.preserverWhitespace=1
                 d.loadXML()

                 xml.preserverWhitespace=1
                 xml.loadXML(r.reponseText)
                 */
                return xml;
            }
        }
    },
    add_template:function(e) {
        // TODO: keep sources so we can implement reload()
        this.hash();
        if (e.constructor == String) {
            e = this.load_xml(e);
        }
        var ec = e.documentElement ? e.documentElement.childNodes
               : e.childNodes ? e.childNodes
               : [];
        for (var i = 0; i < ec.length; i++) {
            var n = ec[i];
            if (n.nodeType == 1) {
                var name = n.getAttribute(this.prefix + "-name");
                this.templates[name] = n;
            }
        }
    },
    render:function(name, v) {
        var e;
        if (e = this.templates[name]) {
            return this.render_node(e, v);
        }
        throw new Error("template " + name + " not found");
    }
};

