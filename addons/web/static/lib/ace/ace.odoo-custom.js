(function() {
    function o(n) {
        var i = e;
        n && (e[n] || (e[n] = {}), i = e[n]);
        if (!i.define || !i.define.packaged) t.original = i.define, i.define = t, i.define.packaged = !0;
        if (!i.require || !i.require.packaged) r.original = i.require, i.require = r, i.require.packaged = !0
    }
    var ACE_NAMESPACE = "",
        e = {};
    window.ace = e;
    if (!ACE_NAMESPACE && typeof requirejs != "undefined") return;
    var t = function(e, n, r) {
        if (typeof e != "string") {
            t.original ? t.original.apply(this, arguments) : (console.error("dropping module because define wasn't a string."), console.trace());
            return
        }
        arguments.length == 2 && (r = n), t.modules[e] || (t.payloads[e] = r, t.modules[e] = null)
    };
    t.modules = {}, t.payloads = {};
    var n = function(e, t, n) {
            if (typeof t == "string") {
                var i = s(e, t);
                if (i != undefined) return n && n(), i
            } else if (Object.prototype.toString.call(t) === "[object Array]") {
                var o = [];
                for (var u = 0, a = t.length; u < a; ++u) {
                    var f = s(e, t[u]);
                    if (f == undefined && r.original) return;
                    o.push(f)
                }
                return n && n.apply(null, o) || !0
            }
        },
        r = function(e, t) {
            var i = n("", e, t);
            return i == undefined && r.original ? r.original.apply(this, arguments) : i
        },
        i = function(e, t) {
            if (t.indexOf("!") !== -1) {
                var n = t.split("!");
                return i(e, n[0]) + "!" + i(e, n[1])
            }
            if (t.charAt(0) == ".") {
                var r = e.split("/").slice(0, -1).join("/");
                t = r + "/" + t;
                while (t.indexOf(".") !== -1 && s != t) {
                    var s = t;
                    t = t.replace(/\/\.\//, "/").replace(/[^\/]+\/\.\.\//, "")
                }
            }
            return t
        },
        s = function(e, r) {
            r = i(e, r);
            var s = t.modules[r];
            if (!s) {
                s = t.payloads[r];
                if (typeof s == "function") {
                    var o = {},
                        u = {
                            id: r,
                            uri: "",
                            exports: o,
                            packaged: !0
                        },
                        a = function(e, t) {
                            return n(r, e, t)
                        },
                        f = s(a, o, u);
                    o = f || u.exports, t.modules[r] = o, delete t.payloads[r]
                }
                s = t.modules[r] = o || s
            }
            return s
        };
    o(ACE_NAMESPACE)
})();
(function() {var define = ace.define, require = ace.require;
define("ace/lib/regexp", ["require", "exports", "module"], function(e, t, n) {
    "use strict";

    function o(e) {
        return (e.global ? "g" : "") + (e.ignoreCase ? "i" : "") + (e.multiline ? "m" : "") + (e.extended ? "x" : "") + (e.sticky ? "y" : "")
    }

    function u(e, t, n) {
        if (Array.prototype.indexOf) return e.indexOf(t, n);
        for (var r = n || 0; r < e.length; r++)
            if (e[r] === t) return r;
        return -1
    }
    var r = {
            exec: RegExp.prototype.exec,
            test: RegExp.prototype.test,
            match: String.prototype.match,
            replace: String.prototype.replace,
            split: String.prototype.split
        },
        i = r.exec.call(/()??/, "")[1] === undefined,
        s = function() {
            var e = /^/g;
            return r.test.call(e, ""), !e.lastIndex
        }();
    if (s && i) return;
    RegExp.prototype.exec = function(e) {
        var t = r.exec.apply(this, arguments),
            n, a;
        if (typeof e == "string" && t) {
            !i && t.length > 1 && u(t, "") > -1 && (a = RegExp(this.source, r.replace.call(o(this), "g", "")), r.replace.call(e.slice(t.index), a, function() {
                for (var e = 1; e < arguments.length - 2; e++) arguments[e] === undefined && (t[e] = undefined)
            }));
            if (this._xregexp && this._xregexp.captureNames)
                for (var f = 1; f < t.length; f++) n = this._xregexp.captureNames[f - 1], n && (t[n] = t[f]);
            !s && this.global && !t[0].length && this.lastIndex > t.index && this.lastIndex--
        }
        return t
    }, s || (RegExp.prototype.test = function(e) {
        var t = r.exec.call(this, e);
        return t && this.global && !t[0].length && this.lastIndex > t.index && this.lastIndex--, !!t
    })
}), define("ace/lib/es5-shim", ["require", "exports", "module"], function(e, t, n) {
    function r() {}

    function w(e) {
        try {
            return Object.defineProperty(e, "sentinel", {}), "sentinel" in e
        } catch (t) {}
    }

    function H(e) {
        return e = +e, e !== e ? e = 0 : e !== 0 && e !== 1 / 0 && e !== -1 / 0 && (e = (e > 0 || -1) * Math.floor(Math.abs(e))), e
    }

    function B(e) {
        var t = typeof e;
        return e === null || t === "undefined" || t === "boolean" || t === "number" || t === "string"
    }

    function j(e) {
        var t, n, r;
        if (B(e)) return e;
        n = e.valueOf;
        if (typeof n == "function") {
            t = n.call(e);
            if (B(t)) return t
        }
        r = e.toString;
        if (typeof r == "function") {
            t = r.call(e);
            if (B(t)) return t
        }
        throw new TypeError
    }
    Function.prototype.bind || (Function.prototype.bind = function(t) {
        var n = this;
        if (typeof n != "function") throw new TypeError("Function.prototype.bind called on incompatible " + n);
        var i = u.call(arguments, 1),
            s = function() {
                if (this instanceof s) {
                    var e = n.apply(this, i.concat(u.call(arguments)));
                    return Object(e) === e ? e : this
                }
                return n.apply(t, i.concat(u.call(arguments)))
            };
        return n.prototype && (r.prototype = n.prototype, s.prototype = new r, r.prototype = null), s
    });
    var i = Function.prototype.call,
        s = Array.prototype,
        o = Object.prototype,
        u = s.slice,
        a = i.bind(o.toString),
        f = i.bind(o.hasOwnProperty),
        l, c, h, p, d;
    if (d = f(o, "__defineGetter__")) l = i.bind(o.__defineGetter__), c = i.bind(o.__defineSetter__), h = i.bind(o.__lookupGetter__), p = i.bind(o.__lookupSetter__);
    if ([1, 2].splice(0).length != 2)
        if (! function() {
                function e(e) {
                    var t = new Array(e + 2);
                    return t[0] = t[1] = 0, t
                }
                var t = [],
                    n;
                t.splice.apply(t, e(20)), t.splice.apply(t, e(26)), n = t.length, t.splice(5, 0, "XXX"), n + 1 == t.length;
                if (n + 1 == t.length) return !0
            }()) Array.prototype.splice = function(e, t) {
            var n = this.length;
            e > 0 ? e > n && (e = n) : e == void 0 ? e = 0 : e < 0 && (e = Math.max(n + e, 0)), e + t < n || (t = n - e);
            var r = this.slice(e, e + t),
                i = u.call(arguments, 2),
                s = i.length;
            if (e === n) s && this.push.apply(this, i);
            else {
                var o = Math.min(t, n - e),
                    a = e + o,
                    f = a + s - o,
                    l = n - a,
                    c = n - o;
                if (f < a)
                    for (var h = 0; h < l; ++h) this[f + h] = this[a + h];
                else if (f > a)
                    for (h = l; h--;) this[f + h] = this[a + h];
                if (s && e === c) this.length = c, this.push.apply(this, i);
                else {
                    this.length = c + s;
                    for (h = 0; h < s; ++h) this[e + h] = i[h]
                }
            }
            return r
        };
        else {
            var v = Array.prototype.splice;
            Array.prototype.splice = function(e, t) {
                return arguments.length ? v.apply(this, [e === void 0 ? 0 : e, t === void 0 ? this.length - e : t].concat(u.call(arguments, 2))) : []
            }
        }
    Array.isArray || (Array.isArray = function(t) {
        return a(t) == "[object Array]"
    });
    var m = Object("a"),
        g = m[0] != "a" || !(0 in m);
    Array.prototype.forEach || (Array.prototype.forEach = function(t) {
        var n = F(this),
            r = g && a(this) == "[object String]" ? this.split("") : n,
            i = arguments[1],
            s = -1,
            o = r.length >>> 0;
        if (a(t) != "[object Function]") throw new TypeError;
        while (++s < o) s in r && t.call(i, r[s], s, n)
    }), Array.prototype.map || (Array.prototype.map = function(t) {
        var n = F(this),
            r = g && a(this) == "[object String]" ? this.split("") : n,
            i = r.length >>> 0,
            s = Array(i),
            o = arguments[1];
        if (a(t) != "[object Function]") throw new TypeError(t + " is not a function");
        for (var u = 0; u < i; u++) u in r && (s[u] = t.call(o, r[u], u, n));
        return s
    }), Array.prototype.filter || (Array.prototype.filter = function(t) {
        var n = F(this),
            r = g && a(this) == "[object String]" ? this.split("") : n,
            i = r.length >>> 0,
            s = [],
            o, u = arguments[1];
        if (a(t) != "[object Function]") throw new TypeError(t + " is not a function");
        for (var f = 0; f < i; f++) f in r && (o = r[f], t.call(u, o, f, n) && s.push(o));
        return s
    }), Array.prototype.every || (Array.prototype.every = function(t) {
        var n = F(this),
            r = g && a(this) == "[object String]" ? this.split("") : n,
            i = r.length >>> 0,
            s = arguments[1];
        if (a(t) != "[object Function]") throw new TypeError(t + " is not a function");
        for (var o = 0; o < i; o++)
            if (o in r && !t.call(s, r[o], o, n)) return !1;
        return !0
    }), Array.prototype.some || (Array.prototype.some = function(t) {
        var n = F(this),
            r = g && a(this) == "[object String]" ? this.split("") : n,
            i = r.length >>> 0,
            s = arguments[1];
        if (a(t) != "[object Function]") throw new TypeError(t + " is not a function");
        for (var o = 0; o < i; o++)
            if (o in r && t.call(s, r[o], o, n)) return !0;
        return !1
    }), Array.prototype.reduce || (Array.prototype.reduce = function(t) {
        var n = F(this),
            r = g && a(this) == "[object String]" ? this.split("") : n,
            i = r.length >>> 0;
        if (a(t) != "[object Function]") throw new TypeError(t + " is not a function");
        if (!i && arguments.length == 1) throw new TypeError("reduce of empty array with no initial value");
        var s = 0,
            o;
        if (arguments.length >= 2) o = arguments[1];
        else
            do {
                if (s in r) {
                    o = r[s++];
                    break
                }
                if (++s >= i) throw new TypeError("reduce of empty array with no initial value")
            } while (!0);
        for (; s < i; s++) s in r && (o = t.call(void 0, o, r[s], s, n));
        return o
    }), Array.prototype.reduceRight || (Array.prototype.reduceRight = function(t) {
        var n = F(this),
            r = g && a(this) == "[object String]" ? this.split("") : n,
            i = r.length >>> 0;
        if (a(t) != "[object Function]") throw new TypeError(t + " is not a function");
        if (!i && arguments.length == 1) throw new TypeError("reduceRight of empty array with no initial value");
        var s, o = i - 1;
        if (arguments.length >= 2) s = arguments[1];
        else
            do {
                if (o in r) {
                    s = r[o--];
                    break
                }
                if (--o < 0) throw new TypeError("reduceRight of empty array with no initial value")
            } while (!0);
        do o in this && (s = t.call(void 0, s, r[o], o, n)); while (o--);
        return s
    });
    if (!Array.prototype.indexOf || [0, 1].indexOf(1, 2) != -1) Array.prototype.indexOf = function(t) {
        var n = g && a(this) == "[object String]" ? this.split("") : F(this),
            r = n.length >>> 0;
        if (!r) return -1;
        var i = 0;
        arguments.length > 1 && (i = H(arguments[1])), i = i >= 0 ? i : Math.max(0, r + i);
        for (; i < r; i++)
            if (i in n && n[i] === t) return i;
        return -1
    };
    if (!Array.prototype.lastIndexOf || [0, 1].lastIndexOf(0, -3) != -1) Array.prototype.lastIndexOf = function(t) {
        var n = g && a(this) == "[object String]" ? this.split("") : F(this),
            r = n.length >>> 0;
        if (!r) return -1;
        var i = r - 1;
        arguments.length > 1 && (i = Math.min(i, H(arguments[1]))), i = i >= 0 ? i : r - Math.abs(i);
        for (; i >= 0; i--)
            if (i in n && t === n[i]) return i;
        return -1
    };
    Object.getPrototypeOf || (Object.getPrototypeOf = function(t) {
        return t.__proto__ || (t.constructor ? t.constructor.prototype : o)
    });
    if (!Object.getOwnPropertyDescriptor) {
        var y = "Object.getOwnPropertyDescriptor called on a non-object: ";
        Object.getOwnPropertyDescriptor = function(t, n) {
            if (typeof t != "object" && typeof t != "function" || t === null) throw new TypeError(y + t);
            if (!f(t, n)) return;
            var r, i, s;
            r = {
                enumerable: !0,
                configurable: !0
            };
            if (d) {
                var u = t.__proto__;
                t.__proto__ = o;
                var i = h(t, n),
                    s = p(t, n);
                t.__proto__ = u;
                if (i || s) return i && (r.get = i), s && (r.set = s), r
            }
            return r.value = t[n], r
        }
    }
    Object.getOwnPropertyNames || (Object.getOwnPropertyNames = function(t) {
        return Object.keys(t)
    });
    if (!Object.create) {
        var b;
        Object.prototype.__proto__ === null ? b = function() {
            return {
                __proto__: null
            }
        } : b = function() {
            var e = {};
            for (var t in e) e[t] = null;
            return e.constructor = e.hasOwnProperty = e.propertyIsEnumerable = e.isPrototypeOf = e.toLocaleString = e.toString = e.valueOf = e.__proto__ = null, e
        }, Object.create = function(t, n) {
            var r;
            if (t === null) r = b();
            else {
                if (typeof t != "object") throw new TypeError("typeof prototype[" + typeof t + "] != 'object'");
                var i = function() {};
                i.prototype = t, r = new i, r.__proto__ = t
            }
            return n !== void 0 && Object.defineProperties(r, n), r
        }
    }
    if (Object.defineProperty) {
        var E = w({}),
            S = typeof document == "undefined" || w(document.createElement("div"));
        if (!E || !S) var x = Object.defineProperty
    }
    if (!Object.defineProperty || x) {
        var T = "Property description must be an object: ",
            N = "Object.defineProperty called on non-object: ",
            C = "getters & setters can not be defined on this javascript engine";
        Object.defineProperty = function(t, n, r) {
            if (typeof t != "object" && typeof t != "function" || t === null) throw new TypeError(N + t);
            if (typeof r != "object" && typeof r != "function" || r === null) throw new TypeError(T + r);
            if (x) try {
                return x.call(Object, t, n, r)
            } catch (i) {}
            if (f(r, "value"))
                if (d && (h(t, n) || p(t, n))) {
                    var s = t.__proto__;
                    t.__proto__ = o, delete t[n], t[n] = r.value, t.__proto__ = s
                } else t[n] = r.value;
            else {
                if (!d) throw new TypeError(C);
                f(r, "get") && l(t, n, r.get), f(r, "set") && c(t, n, r.set)
            }
            return t
        }
    }
    Object.defineProperties || (Object.defineProperties = function(t, n) {
        for (var r in n) f(n, r) && Object.defineProperty(t, r, n[r]);
        return t
    }), Object.seal || (Object.seal = function(t) {
        return t
    }), Object.freeze || (Object.freeze = function(t) {
        return t
    });
    try {
        Object.freeze(function() {})
    } catch (k) {
        Object.freeze = function(t) {
            return function(n) {
                return typeof n == "function" ? n : t(n)
            }
        }(Object.freeze)
    }
    Object.preventExtensions || (Object.preventExtensions = function(t) {
        return t
    }), Object.isSealed || (Object.isSealed = function(t) {
        return !1
    }), Object.isFrozen || (Object.isFrozen = function(t) {
        return !1
    }), Object.isExtensible || (Object.isExtensible = function(t) {
        if (Object(t) === t) throw new TypeError;
        var n = "";
        while (f(t, n)) n += "?";
        t[n] = !0;
        var r = f(t, n);
        return delete t[n], r
    });
    if (!Object.keys) {
        var L = !0,
            A = ["toString", "toLocaleString", "valueOf", "hasOwnProperty", "isPrototypeOf", "propertyIsEnumerable", "constructor"],
            O = A.length;
        for (var M in {
                toString: null
            }) L = !1;
        Object.keys = function I(e) {
            if (typeof e != "object" && typeof e != "function" || e === null) throw new TypeError("Object.keys called on a non-object");
            var I = [];
            for (var t in e) f(e, t) && I.push(t);
            if (L)
                for (var n = 0, r = O; n < r; n++) {
                    var i = A[n];
                    f(e, i) && I.push(i)
                }
            return I
        }
    }
    Date.now || (Date.now = function() {
        return (new Date).getTime()
    });
    var _ = "   \n\f\r \u00a0\u1680\u180e\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000\u2028\u2029\ufeff";
    if (!String.prototype.trim || _.trim()) {
        _ = "[" + _ + "]";
        var D = new RegExp("^" + _ + _ + "*"),
            P = new RegExp(_ + _ + "*$");
        String.prototype.trim = function() {
            return String(this).replace(D, "").replace(P, "")
        }
    }
    var F = function(e) {
        if (e == null) throw new TypeError("can't convert " + e + " to object");
        return Object(e)
    }
}), define("ace/lib/fixoldbrowsers", ["require", "exports", "module", "ace/lib/regexp", "ace/lib/es5-shim"], function(e, t, n) {
    "use strict";
    e("./regexp"), e("./es5-shim")
}), define("ace/lib/dom", ["require", "exports", "module"], function(e, t, n) {
    "use strict";
    var r = "http://www.w3.org/1999/xhtml";
    t.getDocumentHead = function(e) {
        return e || (e = document), e.head || e.getElementsByTagName("head")[0] || e.documentElement
    }, t.createElement = function(e, t) {
        return document.createElementNS ? document.createElementNS(t || r, e) : document.createElement(e)
    }, t.hasCssClass = function(e, t) {
        var n = (e.className || "").split(/\s+/g);
        return n.indexOf(t) !== -1
    }, t.addCssClass = function(e, n) {
        t.hasCssClass(e, n) || (e.className += " " + n)
    }, t.removeCssClass = function(e, t) {
        var n = e.className.split(/\s+/g);
        for (;;) {
            var r = n.indexOf(t);
            if (r == -1) break;
            n.splice(r, 1)
        }
        e.className = n.join(" ")
    }, t.toggleCssClass = function(e, t) {
        var n = e.className.split(/\s+/g),
            r = !0;
        for (;;) {
            var i = n.indexOf(t);
            if (i == -1) break;
            r = !1, n.splice(i, 1)
        }
        return r && n.push(t), e.className = n.join(" "), r
    }, t.setCssClass = function(e, n, r) {
        r ? t.addCssClass(e, n) : t.removeCssClass(e, n)
    }, t.hasCssString = function(e, t) {
        var n = 0,
            r;
        t = t || document;
        if (t.createStyleSheet && (r = t.styleSheets)) {
            while (n < r.length)
                if (r[n++].owningElement.id === e) return !0
        } else if (r = t.getElementsByTagName("style"))
            while (n < r.length)
                if (r[n++].id === e) return !0;
        return !1
    }, t.importCssString = function(n, i, s) {
        s = s || document;
        if (i && t.hasCssString(i, s)) return null;
        var o;
        i && (n += "\n/*# sourceURL=ace/css/" + i + " */"), s.createStyleSheet ? (o = s.createStyleSheet(), o.cssText = n, i && (o.owningElement.id = i)) : (o = s.createElementNS ? s.createElementNS(r, "style") : s.createElement("style"), o.appendChild(s.createTextNode(n)), i && (o.id = i), t.getDocumentHead(s).appendChild(o))
    }, t.importCssStylsheet = function(e, n) {
        if (n.createStyleSheet) n.createStyleSheet(e);
        else {
            var r = t.createElement("link");
            r.rel = "stylesheet", r.href = e, t.getDocumentHead(n).appendChild(r)
        }
    }, t.getInnerWidth = function(e) {
        return parseInt(t.computedStyle(e, "paddingLeft"), 10) + parseInt(t.computedStyle(e, "paddingRight"), 10) + e.clientWidth
    }, t.getInnerHeight = function(e) {
        return parseInt(t.computedStyle(e, "paddingTop"), 10) + parseInt(t.computedStyle(e, "paddingBottom"), 10) + e.clientHeight
    }, t.scrollbarWidth = function(e) {
        var n = t.createElement("ace_inner");
        n.style.width = "100%", n.style.minWidth = "0px", n.style.height = "200px", n.style.display = "block";
        var r = t.createElement("ace_outer"),
            i = r.style;
        i.position = "absolute", i.left = "-10000px", i.overflow = "hidden", i.width = "200px", i.minWidth = "0px", i.height = "150px", i.display = "block", r.appendChild(n);
        var s = e.documentElement;
        s.appendChild(r);
        var o = n.offsetWidth;
        i.overflow = "scroll";
        var u = n.offsetWidth;
        return o == u && (u = r.clientWidth), s.removeChild(r), o - u
    };
    if (typeof document == "undefined") {
        t.importCssString = function() {};
        return
    }
    window.pageYOffset !== undefined ? (t.getPageScrollTop = function() {
        return window.pageYOffset
    }, t.getPageScrollLeft = function() {
        return window.pageXOffset
    }) : (t.getPageScrollTop = function() {
        return document.body.scrollTop
    }, t.getPageScrollLeft = function() {
        return document.body.scrollLeft
    }), window.getComputedStyle ? t.computedStyle = function(e, t) {
        return t ? (window.getComputedStyle(e, "") || {})[t] || "" : window.getComputedStyle(e, "") || {}
    } : t.computedStyle = function(e, t) {
        return t ? e.currentStyle[t] : e.currentStyle
    }, t.setInnerHtml = function(e, t) {
        var n = e.cloneNode(!1);
        return n.innerHTML = t, e.parentNode.replaceChild(n, e), n
    }, "textContent" in document.documentElement ? (t.setInnerText = function(e, t) {
        e.textContent = t
    }, t.getInnerText = function(e) {
        return e.textContent
    }) : (t.setInnerText = function(e, t) {
        e.innerText = t
    }, t.getInnerText = function(e) {
        return e.innerText
    }), t.getParentWindow = function(e) {
        return e.defaultView || e.parentWindow
    }
}), define("ace/lib/oop", ["require", "exports", "module"], function(e, t, n) {
    "use strict";
    t.inherits = function(e, t) {
        e.super_ = t, e.prototype = Object.create(t.prototype, {
            constructor: {
                value: e,
                enumerable: !1,
                writable: !0,
                configurable: !0
            }
        })
    }, t.mixin = function(e, t) {
        for (var n in t) e[n] = t[n];
        return e
    }, t.implement = function(e, n) {
        t.mixin(e, n)
    }
}), define("ace/lib/keys", ["require", "exports", "module", "ace/lib/fixoldbrowsers", "ace/lib/oop"], function(e, t, n) {
    "use strict";
    e("./fixoldbrowsers");
    var r = e("./oop"),
        i = function() {
            var e = {
                    MODIFIER_KEYS: {
                        16: "Shift",
                        17: "Ctrl",
                        18: "Alt",
                        224: "Meta"
                    },
                    KEY_MODS: {
                        ctrl: 1,
                        alt: 2,
                        option: 2,
                        shift: 4,
                        "super": 8,
                        meta: 8,
                        command: 8,
                        cmd: 8
                    },
                    FUNCTION_KEYS: {
                        8: "Backspace",
                        9: "Tab",
                        13: "Return",
                        19: "Pause",
                        27: "Esc",
                        32: "Space",
                        33: "PageUp",
                        34: "PageDown",
                        35: "End",
                        36: "Home",
                        37: "Left",
                        38: "Up",
                        39: "Right",
                        40: "Down",
                        44: "Print",
                        45: "Insert",
                        46: "Delete",
                        96: "Numpad0",
                        97: "Numpad1",
                        98: "Numpad2",
                        99: "Numpad3",
                        100: "Numpad4",
                        101: "Numpad5",
                        102: "Numpad6",
                        103: "Numpad7",
                        104: "Numpad8",
                        105: "Numpad9",
                        "-13": "NumpadEnter",
                        112: "F1",
                        113: "F2",
                        114: "F3",
                        115: "F4",
                        116: "F5",
                        117: "F6",
                        118: "F7",
                        119: "F8",
                        120: "F9",
                        121: "F10",
                        122: "F11",
                        123: "F12",
                        144: "Numlock",
                        145: "Scrolllock"
                    },
                    PRINTABLE_KEYS: {
                        32: " ",
                        48: "0",
                        49: "1",
                        50: "2",
                        51: "3",
                        52: "4",
                        53: "5",
                        54: "6",
                        55: "7",
                        56: "8",
                        57: "9",
                        59: ";",
                        61: "=",
                        65: "a",
                        66: "b",
                        67: "c",
                        68: "d",
                        69: "e",
                        70: "f",
                        71: "g",
                        72: "h",
                        73: "i",
                        74: "j",
                        75: "k",
                        76: "l",
                        77: "m",
                        78: "n",
                        79: "o",
                        80: "p",
                        81: "q",
                        82: "r",
                        83: "s",
                        84: "t",
                        85: "u",
                        86: "v",
                        87: "w",
                        88: "x",
                        89: "y",
                        90: "z",
                        107: "+",
                        109: "-",
                        110: ".",
                        186: ";",
                        187: "=",
                        188: ",",
                        189: "-",
                        190: ".",
                        191: "/",
                        192: "`",
                        219: "[",
                        220: "\\",
                        221: "]",
                        222: "'"
                    }
                },
                t, n;
            for (n in e.FUNCTION_KEYS) t = e.FUNCTION_KEYS[n].toLowerCase(), e[t] = parseInt(n, 10);
            for (n in e.PRINTABLE_KEYS) t = e.PRINTABLE_KEYS[n].toLowerCase(), e[t] = parseInt(n, 10);
            return r.mixin(e, e.MODIFIER_KEYS), r.mixin(e, e.PRINTABLE_KEYS), r.mixin(e, e.FUNCTION_KEYS), e.enter = e["return"], e.escape = e.esc, e.del = e["delete"], e[173] = "-",
                function() {
                    var t = ["cmd", "ctrl", "alt", "shift"];
                    for (var n = Math.pow(2, t.length); n--;) e.KEY_MODS[n] = t.filter(function(t) {
                        return n & e.KEY_MODS[t]
                    }).join("-") + "-"
                }(), e.KEY_MODS[0] = "", e.KEY_MODS[-1] = "input-", e
        }();
    r.mixin(t, i), t.keyCodeToString = function(e) {
        var t = i[e];
        return typeof t != "string" && (t = String.fromCharCode(e)), t.toLowerCase()
    }
}), define("ace/lib/useragent", ["require", "exports", "module"], function(e, t, n) {
    "use strict";
    t.OS = {
        LINUX: "LINUX",
        MAC: "MAC",
        WINDOWS: "WINDOWS"
    }, t.getOS = function() {
        return t.isMac ? t.OS.MAC : t.isLinux ? t.OS.LINUX : t.OS.WINDOWS
    };
    if (typeof navigator != "object") return;
    var r = (navigator.platform.match(/mac|win|linux/i) || ["other"])[0].toLowerCase(),
        i = navigator.userAgent;
    t.isWin = r == "win", t.isMac = r == "mac", t.isLinux = r == "linux", t.isIE = navigator.appName == "Microsoft Internet Explorer" || navigator.appName.indexOf("MSAppHost") >= 0 ? parseFloat((i.match(/(?:MSIE |Trident\/[0-9]+[\.0-9]+;.*rv:)([0-9]+[\.0-9]+)/) || [])[1]) : parseFloat((i.match(/(?:Trident\/[0-9]+[\.0-9]+;.*rv:)([0-9]+[\.0-9]+)/) || [])[1]), t.isOldIE = t.isIE && t.isIE < 9, t.isGecko = t.isMozilla = (window.Controllers || window.controllers) && window.navigator.product === "Gecko", t.isOldGecko = t.isGecko && parseInt((i.match(/rv\:(\d+)/) || [])[1], 10) < 4, t.isOpera = window.opera && Object.prototype.toString.call(window.opera) == "[object Opera]", t.isWebKit = parseFloat(i.split("WebKit/")[1]) || undefined, t.isChrome = parseFloat(i.split(" Chrome/")[1]) || undefined, t.isAIR = i.indexOf("AdobeAIR") >= 0, t.isIPad = i.indexOf("iPad") >= 0, t.isTouchPad = i.indexOf("TouchPad") >= 0, t.isChromeOS = i.indexOf(" CrOS ") >= 0
}), define("ace/lib/event", ["require", "exports", "module", "ace/lib/keys", "ace/lib/useragent"], function(e, t, n) {
    "use strict";

    function o(e, t, n) {
        var o = s(t);
        if (!i.isMac && u) {
            if (u[91] || u[92]) o |= 8;
            if (u.altGr) {
                if ((3 & o) == 3) return;
                u.altGr = 0
            }
            if (n === 18 || n === 17) {
                var f = "location" in t ? t.location : t.keyLocation;
                if (n === 17 && f === 1) u[n] == 1 && (a = t.timeStamp);
                else if (n === 18 && o === 3 && f === 2) {
                    var l = t.timeStamp - a;
                    l < 50 && (u.altGr = !0)
                }
            }
        }
        n in r.MODIFIER_KEYS && (n = -1), o & 8 && (n === 91 || n === 93) && (n = -1);
        if (!o && n === 13) {
            var f = "location" in t ? t.location : t.keyLocation;
            if (f === 3) {
                e(t, o, -n);
                if (t.defaultPrevented) return
            }
        }
        if (i.isChromeOS && o & 8) {
            e(t, o, n);
            if (t.defaultPrevented) return;
            o &= -9
        }
        return !!o || n in r.FUNCTION_KEYS || n in r.PRINTABLE_KEYS ? e(t, o, n) : !1
    }

    function f(e) {
        u = Object.create(null)
    }
    var r = e("./keys"),
        i = e("./useragent");
    t.addListener = function(e, t, n) {
        if (e.addEventListener) return e.addEventListener(t, n, !1);
        if (e.attachEvent) {
            var r = function() {
                n.call(e, window.event)
            };
            n._wrapper = r, e.attachEvent("on" + t, r)
        }
    }, t.removeListener = function(e, t, n) {
        if (e.removeEventListener) return e.removeEventListener(t, n, !1);
        e.detachEvent && e.detachEvent("on" + t, n._wrapper || n)
    }, t.stopEvent = function(e) {
        return t.stopPropagation(e), t.preventDefault(e), !1
    }, t.stopPropagation = function(e) {
        e.stopPropagation ? e.stopPropagation() : e.cancelBubble = !0
    }, t.preventDefault = function(e) {
        e.preventDefault ? e.preventDefault() : e.returnValue = !1
    }, t.getButton = function(e) {
        return e.type == "dblclick" ? 0 : e.type == "contextmenu" || i.isMac && e.ctrlKey && !e.altKey && !e.shiftKey ? 2 : e.preventDefault ? e.button : {
            1: 0,
            2: 2,
            4: 1
        }[e.button]
    }, t.capture = function(e, n, r) {
        function i(e) {
            n && n(e), r && r(e), t.removeListener(document, "mousemove", n, !0), t.removeListener(document, "mouseup", i, !0), t.removeListener(document, "dragstart", i, !0)
        }
        return t.addListener(document, "mousemove", n, !0), t.addListener(document, "mouseup", i, !0), t.addListener(document, "dragstart", i, !0), i
    }, t.addTouchMoveListener = function(e, n) {
        if ("ontouchmove" in e) {
            var r, i;
            t.addListener(e, "touchstart", function(e) {
                var t = e.changedTouches[0];
                r = t.clientX, i = t.clientY
            }), t.addListener(e, "touchmove", function(e) {
                var t = 1,
                    s = e.changedTouches[0];
                e.wheelX = -(s.clientX - r) / t, e.wheelY = -(s.clientY - i) / t, r = s.clientX, i = s.clientY, n(e)
            })
        }
    }, t.addMouseWheelListener = function(e, n) {
        "onmousewheel" in e ? t.addListener(e, "mousewheel", function(e) {
            var t = 8;
            e.wheelDeltaX !== undefined ? (e.wheelX = -e.wheelDeltaX / t, e.wheelY = -e.wheelDeltaY / t) : (e.wheelX = 0, e.wheelY = -e.wheelDelta / t), n(e)
        }) : "onwheel" in e ? t.addListener(e, "wheel", function(e) {
            var t = .35;
            switch (e.deltaMode) {
                case e.DOM_DELTA_PIXEL:
                    e.wheelX = e.deltaX * t || 0, e.wheelY = e.deltaY * t || 0;
                    break;
                case e.DOM_DELTA_LINE:
                case e.DOM_DELTA_PAGE:
                    e.wheelX = (e.deltaX || 0) * 5, e.wheelY = (e.deltaY || 0) * 5
            }
            n(e)
        }) : t.addListener(e, "DOMMouseScroll", function(e) {
            e.axis && e.axis == e.HORIZONTAL_AXIS ? (e.wheelX = (e.detail || 0) * 5, e.wheelY = 0) : (e.wheelX = 0, e.wheelY = (e.detail || 0) * 5), n(e)
        })
    }, t.addMultiMouseDownListener = function(e, n, r, s) {
        var o = 0,
            u, a, f, l = {
                2: "dblclick",
                3: "tripleclick",
                4: "quadclick"
            };
        t.addListener(e, "mousedown", function(e) {
            t.getButton(e) !== 0 ? o = 0 : e.detail > 1 ? (o++, o > 4 && (o = 1)) : o = 1;
            if (i.isIE) {
                var c = Math.abs(e.clientX - u) > 5 || Math.abs(e.clientY - a) > 5;
                if (!f || c) o = 1;
                f && clearTimeout(f), f = setTimeout(function() {
                    f = null
                }, n[o - 1] || 600), o == 1 && (u = e.clientX, a = e.clientY)
            }
            e._clicks = o, r[s]("mousedown", e);
            if (o > 4) o = 0;
            else if (o > 1) return r[s](l[o], e)
        }), i.isOldIE && t.addListener(e, "dblclick", function(e) {
            o = 2, f && clearTimeout(f), f = setTimeout(function() {
                f = null
            }, n[o - 1] || 600), r[s]("mousedown", e), r[s](l[o], e)
        })
    };
    var s = !i.isMac || !i.isOpera || "KeyboardEvent" in window ? function(e) {
        return 0 | (e.ctrlKey ? 1 : 0) | (e.altKey ? 2 : 0) | (e.shiftKey ? 4 : 0) | (e.metaKey ? 8 : 0)
    } : function(e) {
        return 0 | (e.metaKey ? 1 : 0) | (e.altKey ? 2 : 0) | (e.shiftKey ? 4 : 0) | (e.ctrlKey ? 8 : 0)
    };
    t.getModifierString = function(e) {
        return r.KEY_MODS[s(e)]
    };
    var u = null,
        a = 0;
    t.addCommandKeyListener = function(e, n) {
        var r = t.addListener;
        if (i.isOldGecko || i.isOpera && !("KeyboardEvent" in window)) {
            var s = null;
            r(e, "keydown", function(e) {
                s = e.keyCode
            }), r(e, "keypress", function(e) {
                return o(n, e, s)
            })
        } else {
            var a = null;
            r(e, "keydown", function(e) {
                u[e.keyCode] = (u[e.keyCode] || 0) + 1;
                var t = o(n, e, e.keyCode);
                return a = e.defaultPrevented, t
            }), r(e, "keypress", function(e) {
                a && (e.ctrlKey || e.altKey || e.shiftKey || e.metaKey) && (t.stopEvent(e), a = null)
            }), r(e, "keyup", function(e) {
                u[e.keyCode] = null
            }), u || (f(), r(window, "focus", f))
        }
    };
    if (typeof window == "object" && window.postMessage && !i.isOldIE) {
        var l = 1;
        t.nextTick = function(e, n) {
            n = n || window;
            var r = "zero-timeout-message-" + l;
            t.addListener(n, "message", function i(s) {
                s.data == r && (t.stopPropagation(s), t.removeListener(n, "message", i), e())
            }), n.postMessage(r, "*")
        }
    }
    t.nextFrame = typeof window == "object" && (window.requestAnimationFrame || window.mozRequestAnimationFrame || window.webkitRequestAnimationFrame || window.msRequestAnimationFrame || window.oRequestAnimationFrame), t.nextFrame ? t.nextFrame = t.nextFrame.bind(window) : t.nextFrame = function(e) {
        setTimeout(e, 17)
    }
}), define("ace/lib/lang", ["require", "exports", "module"], function(e, t, n) {
    "use strict";
    t.last = function(e) {
        return e[e.length - 1]
    }, t.stringReverse = function(e) {
        return e.split("").reverse().join("")
    }, t.stringRepeat = function(e, t) {
        var n = "";
        while (t > 0) {
            t & 1 && (n += e);
            if (t >>= 1) e += e
        }
        return n
    };
    var r = /^\s\s*/,
        i = /\s\s*$/;
    t.stringTrimLeft = function(e) {
        return e.replace(r, "")
    }, t.stringTrimRight = function(e) {
        return e.replace(i, "")
    }, t.copyObject = function(e) {
        var t = {};
        for (var n in e) t[n] = e[n];
        return t
    }, t.copyArray = function(e) {
        var t = [];
        for (var n = 0, r = e.length; n < r; n++) e[n] && typeof e[n] == "object" ? t[n] = this.copyObject(e[n]) : t[n] = e[n];
        return t
    }, t.deepCopy = function s(e) {
        if (typeof e != "object" || !e) return e;
        var t;
        if (Array.isArray(e)) {
            t = [];
            for (var n = 0; n < e.length; n++) t[n] = s(e[n]);
            return t
        }
        var r = e.constructor;
        if (r === RegExp) return e;
        t = r();
        for (var n in e) t[n] = s(e[n]);
        return t
    }, t.arrayToMap = function(e) {
        var t = {};
        for (var n = 0; n < e.length; n++) t[e[n]] = 1;
        return t
    }, t.createMap = function(e) {
        var t = Object.create(null);
        for (var n in e) t[n] = e[n];
        return t
    }, t.arrayRemove = function(e, t) {
        for (var n = 0; n <= e.length; n++) t === e[n] && e.splice(n, 1)
    }, t.escapeRegExp = function(e) {
        return e.replace(/([.*+?^${}()|[\]\/\\])/g, "\\$1")
    }, t.escapeHTML = function(e) {
        return e.replace(/&/g, "&#38;").replace(/"/g, "&#34;").replace(/'/g, "&#39;").replace(/</g, "&#60;")
    }, t.getMatchOffsets = function(e, t) {
        var n = [];
        return e.replace(t, function(e) {
            n.push({
                offset: arguments[arguments.length - 2],
                length: e.length
            })
        }), n
    }, t.deferredCall = function(e) {
        var t = null,
            n = function() {
                t = null, e()
            },
            r = function(e) {
                return r.cancel(), t = setTimeout(n, e || 0), r
            };
        return r.schedule = r, r.call = function() {
            return this.cancel(), e(), r
        }, r.cancel = function() {
            return clearTimeout(t), t = null, r
        }, r.isPending = function() {
            return t
        }, r
    }, t.delayedCall = function(e, t) {
        var n = null,
            r = function() {
                n = null, e()
            },
            i = function(e) {
                n == null && (n = setTimeout(r, e || t))
            };
        return i.delay = function(e) {
            n && clearTimeout(n), n = setTimeout(r, e || t)
        }, i.schedule = i, i.call = function() {
            this.cancel(), e()
        }, i.cancel = function() {
            n && clearTimeout(n), n = null
        }, i.isPending = function() {
            return n
        }, i
    }
}), define("ace/keyboard/textinput", ["require", "exports", "module", "ace/lib/event", "ace/lib/useragent", "ace/lib/dom", "ace/lib/lang"], function(e, t, n) {
    "use strict";
    var r = e("../lib/event"),
        i = e("../lib/useragent"),
        s = e("../lib/dom"),
        o = e("../lib/lang"),
        u = i.isChrome < 18,
        a = i.isIE,
        f = function(e, t) {
            function b(e) {
                if (h) return;
                h = !0;
                if (k) t = 0, r = e ? 0 : n.value.length - 1;
                else var t = e ? 2 : 1,
                    r = 2;
                try {
                    n.setSelectionRange(t, r)
                } catch (i) {}
                h = !1
            }

            function w() {
                if (h) return;
                n.value = f, i.isWebKit && y.schedule()
            }

            function R() {
                clearTimeout(q), q = setTimeout(function() {
                    p && (n.style.cssText = p, p = ""), t.renderer.$keepTextAreaAtCursor == null && (t.renderer.$keepTextAreaAtCursor = !0, t.renderer.$moveTextAreaToCursor())
                }, i.isOldIE ? 200 : 0)
            }
            var n = s.createElement("textarea");
            n.className = "ace_text-input", i.isTouchPad && n.setAttribute("x-palm-disable-auto-cap", !0), n.setAttribute("wrap", "off"), n.setAttribute("autocorrect", "off"), n.setAttribute("autocapitalize", "off"), n.setAttribute("spellcheck", !1), n.style.opacity = "0", i.isOldIE && (n.style.top = "-1000px"), e.insertBefore(n, e.firstChild);
            var f = "",
                l = !1,
                c = !1,
                h = !1,
                p = "",
                d = !0;
            try {
                var v = document.activeElement === n
            } catch (m) {}
            r.addListener(n, "blur", function(e) {
                t.onBlur(e), v = !1
            }), r.addListener(n, "focus", function(e) {
                v = !0, t.onFocus(e), b()
            }), this.focus = function() {
                if (p) return n.focus();
                var e = n.style.top;
                n.style.position = "fixed", n.style.top = "-1000px", n.focus(), setTimeout(function() {
                    n.style.position = "", n.style.top == "-1000px" && (n.style.top = e)
                }, 0)
            }, this.blur = function() {
                n.blur()
            }, this.isFocused = function() {
                return v
            };
            var g = o.delayedCall(function() {
                    v && b(d)
                }),
                y = o.delayedCall(function() {
                    h || (n.value = f, v && b())
                });
            i.isWebKit || t.addEventListener("changeSelection", function() {
                t.selection.isEmpty() != d && (d = !d, g.schedule())
            }), w(), v && t.onFocus();
            var E = function(e) {
                return e.selectionStart === 0 && e.selectionEnd === e.value.length
            };
            !n.setSelectionRange && n.createTextRange && (n.setSelectionRange = function(e, t) {
                var n = this.createTextRange();
                n.collapse(!0), n.moveStart("character", e), n.moveEnd("character", t), n.select()
            }, E = function(e) {
                try {
                    var t = e.ownerDocument.selection.createRange()
                } catch (n) {}
                return !t || t.parentElement() != e ? !1 : t.text == e.value
            });
            if (i.isOldIE) {
                var S = !1,
                    x = function(e) {
                        if (S) return;
                        var t = n.value;
                        if (h || !t || t == f) return;
                        if (e && t == f[0]) return T.schedule();
                        A(t), S = !0, w(), S = !1
                    },
                    T = o.delayedCall(x);
                r.addListener(n, "propertychange", x);
                var N = {
                    13: 1,
                    27: 1
                };
                r.addListener(n, "keyup", function(e) {
                    h && (!n.value || N[e.keyCode]) && setTimeout(F, 0);
                    if ((n.value.charCodeAt(0) || 0) < 129) return T.call();
                    h ? j() : B()
                }), r.addListener(n, "keydown", function(e) {
                    T.schedule(50)
                })
            }
            var C = function(e) {
                    l ? l = !1 : E(n) ? (t.selectAll(), b()) : k && b(t.selection.isEmpty())
                },
                k = null;
            this.setInputHandler = function(e) {
                k = e
            }, this.getInputHandler = function() {
                return k
            };
            var L = !1,
                A = function(e) {
                    k && (e = k(e), k = null), c ? (b(), e && t.onPaste(e), c = !1) : e == f.charAt(0) ? L ? t.execCommand("del", {
                        source: "ace"
                    }) : t.execCommand("backspace", {
                        source: "ace"
                    }) : (e.substring(0, 2) == f ? e = e.substr(2) : e.charAt(0) == f.charAt(0) ? e = e.substr(1) : e.charAt(e.length - 1) == f.charAt(0) && (e = e.slice(0, -1)), e.charAt(e.length - 1) == f.charAt(0) && (e = e.slice(0, -1)), e && t.onTextInput(e)), L && (L = !1)
                },
                O = function(e) {
                    if (h) return;
                    var t = n.value;
                    A(t), w()
                },
                M = function(e, t) {
                    var n = e.clipboardData || window.clipboardData;
                    if (!n || u) return;
                    var r = a ? "Text" : "text/plain";
                    return t ? n.setData(r, t) !== !1 : n.getData(r)
                },
                _ = function(e, i) {
                    var s = t.getCopyText();
                    if (!s) return r.preventDefault(e);
                    M(e, s) ? (i ? t.onCut() : t.onCopy(), r.preventDefault(e)) : (l = !0, n.value = s, n.select(), setTimeout(function() {
                        l = !1, w(), b(), i ? t.onCut() : t.onCopy()
                    }))
                },
                D = function(e) {
                    _(e, !0)
                },
                P = function(e) {
                    _(e, !1)
                },
                H = function(e) {
                    var s = M(e);
                    typeof s == "string" ? (s && t.onPaste(s, e), i.isIE && setTimeout(b), r.preventDefault(e)) : (n.value = "", c = !0)
                };
            r.addCommandKeyListener(n, t.onCommandKey.bind(t)), r.addListener(n, "select", C), r.addListener(n, "input", O), r.addListener(n, "cut", D), r.addListener(n, "copy", P), r.addListener(n, "paste", H), (!("oncut" in n) || !("oncopy" in n) || !("onpaste" in n)) && r.addListener(e, "keydown", function(e) {
                if (i.isMac && !e.metaKey || !e.ctrlKey) return;
                switch (e.keyCode) {
                    case 67:
                        P(e);
                        break;
                    case 86:
                        H(e);
                        break;
                    case 88:
                        D(e)
                }
            });
            var B = function(e) {
                    if (h || !t.onCompositionStart || t.$readOnly) return;
                    h = {}, t.onCompositionStart(), setTimeout(j, 0), t.on("mousedown", F), t.selection.isEmpty() || (t.insert(""), t.session.markUndoGroup(), t.selection.clearSelection()), t.session.markUndoGroup()
                },
                j = function() {
                    if (!h || !t.onCompositionUpdate || t.$readOnly) return;
                    var e = n.value.replace(/\x01/g, "");
                    if (h.lastValue === e) return;
                    t.onCompositionUpdate(e), h.lastValue && t.undo(), h.lastValue = e;
                    if (h.lastValue) {
                        var r = t.selection.getRange();
                        t.insert(h.lastValue), t.session.markUndoGroup(), h.range = t.selection.getRange(), t.selection.setRange(r), t.selection.clearSelection()
                    }
                },
                F = function(e) {
                    if (!t.onCompositionEnd || t.$readOnly) return;
                    var r = h;
                    h = !1;
                    var i = setTimeout(function() {
                        i = null;
                        var e = n.value.replace(/\x01/g, "");
                        if (h) return;
                        e == r.lastValue ? w() : !r.lastValue && e && (w(), A(e))
                    });
                    k = function(n) {
                        return i && clearTimeout(i), n = n.replace(/\x01/g, ""), n == r.lastValue ? "" : (r.lastValue && i && t.undo(), n)
                    }, t.onCompositionEnd(), t.removeListener("mousedown", F), e.type == "compositionend" && r.range && t.selection.setRange(r.range)
                },
                I = o.delayedCall(j, 50);
            r.addListener(n, "compositionstart", B), i.isGecko ? r.addListener(n, "text", function() {
                I.schedule()
            }) : (r.addListener(n, "keyup", function() {
                I.schedule()
            }), r.addListener(n, "keydown", function() {
                I.schedule()
            })), r.addListener(n, "compositionend", F), this.getElement = function() {
                return n
            }, this.setReadOnly = function(e) {
                n.readOnly = e
            }, this.onContextMenu = function(e) {
                L = !0, b(t.selection.isEmpty()), t._emit("nativecontextmenu", {
                    target: t,
                    domEvent: e
                }), this.moveToMouse(e, !0)
            }, this.moveToMouse = function(e, o) {
                if (!o && i.isOldIE) return;
                p || (p = n.style.cssText), n.style.cssText = (o ? "z-index:100000;" : "") + "height:" + n.style.height + ";" + (i.isIE ? "opacity:0.1;" : "");
                var u = t.container.getBoundingClientRect(),
                    a = s.computedStyle(t.container),
                    f = u.top + (parseInt(a.borderTopWidth) || 0),
                    l = u.left + (parseInt(u.borderLeftWidth) || 0),
                    c = u.bottom - f - n.clientHeight - 2,
                    h = function(e) {
                        n.style.left = e.clientX - l - 2 + "px", n.style.top = Math.min(e.clientY - f - 2, c) + "px"
                    };
                h(e);
                if (e.type != "mousedown") return;
                t.renderer.$keepTextAreaAtCursor && (t.renderer.$keepTextAreaAtCursor = null), i.isWin && !i.isOldIE && r.capture(t.container, h, R)
            }, this.onContextMenuClose = R;
            var q, U = function(e) {
                t.textInput.onContextMenu(e), R()
            };
            r.addListener(t.renderer.scroller, "contextmenu", U), r.addListener(n, "contextmenu", U)
        };
    t.TextInput = f
}), define("ace/mouse/default_handlers", ["require", "exports", "module", "ace/lib/dom", "ace/lib/event", "ace/lib/useragent"], function(e, t, n) {
    "use strict";

    function u(e) {
        e.$clickSelection = null;
        var t = e.editor;
        t.setDefaultHandler("mousedown", this.onMouseDown.bind(e)), t.setDefaultHandler("dblclick", this.onDoubleClick.bind(e)), t.setDefaultHandler("tripleclick", this.onTripleClick.bind(e)), t.setDefaultHandler("quadclick", this.onQuadClick.bind(e)), t.setDefaultHandler("mousewheel", this.onMouseWheel.bind(e)), t.setDefaultHandler("touchmove", this.onTouchMove.bind(e));
        var n = ["select", "startSelect", "selectEnd", "selectAllEnd", "selectByWordsEnd", "selectByLinesEnd", "dragWait", "dragWaitEnd", "focusWait"];
        n.forEach(function(t) {
            e[t] = this[t]
        }, this), e.selectByLines = this.extendSelectionBy.bind(e, "getLineRange"), e.selectByWords = this.extendSelectionBy.bind(e, "getWordRange")
    }

    function a(e, t, n, r) {
        return Math.sqrt(Math.pow(n - e, 2) + Math.pow(r - t, 2))
    }

    function f(e, t) {
        if (e.start.row == e.end.row) var n = 2 * t.column - e.start.column - e.end.column;
        else if (e.start.row == e.end.row - 1 && !e.start.column && !e.end.column) var n = t.column - 4;
        else var n = 2 * t.row - e.start.row - e.end.row;
        return n < 0 ? {
            cursor: e.start,
            anchor: e.end
        } : {
            cursor: e.end,
            anchor: e.start
        }
    }
    var r = e("../lib/dom"),
        i = e("../lib/event"),
        s = e("../lib/useragent"),
        o = 0;
    (function() {
        this.onMouseDown = function(e) {
            var t = e.inSelection(),
                n = e.getDocumentPosition();
            this.mousedownEvent = e;
            var r = this.editor,
                i = e.getButton();
            if (i !== 0) {
                var s = r.getSelectionRange(),
                    o = s.isEmpty();
                r.$blockScrolling++, o && r.selection.moveToPosition(n), r.$blockScrolling--, r.textInput.onContextMenu(e.domEvent);
                return
            }
            this.mousedownEvent.time = Date.now();
            if (t && !r.isFocused()) {
                r.focus();
                if (this.$focusTimout && !this.$clickSelection && !r.inMultiSelectMode) {
                    this.setState("focusWait"), this.captureMouse(e);
                    return
                }
            }
            return this.captureMouse(e), this.startSelect(n, e.domEvent._clicks > 1), e.preventDefault()
        }, this.startSelect = function(e, t) {
            e = e || this.editor.renderer.screenToTextCoordinates(this.x, this.y);
            var n = this.editor;
            n.$blockScrolling++, this.mousedownEvent.getShiftKey() ? n.selection.selectToPosition(e) : t || n.selection.moveToPosition(e), t || this.select(), n.renderer.scroller.setCapture && n.renderer.scroller.setCapture(), n.setStyle("ace_selecting"), this.setState("select"), n.$blockScrolling--
        }, this.select = function() {
            var e, t = this.editor,
                n = t.renderer.screenToTextCoordinates(this.x, this.y);
            t.$blockScrolling++;
            if (this.$clickSelection) {
                var r = this.$clickSelection.comparePoint(n);
                if (r == -1) e = this.$clickSelection.end;
                else if (r == 1) e = this.$clickSelection.start;
                else {
                    var i = f(this.$clickSelection, n);
                    n = i.cursor, e = i.anchor
                }
                t.selection.setSelectionAnchor(e.row, e.column)
            }
            t.selection.selectToPosition(n), t.$blockScrolling--, t.renderer.scrollCursorIntoView()
        }, this.extendSelectionBy = function(e) {
            var t, n = this.editor,
                r = n.renderer.screenToTextCoordinates(this.x, this.y),
                i = n.selection[e](r.row, r.column);
            n.$blockScrolling++;
            if (this.$clickSelection) {
                var s = this.$clickSelection.comparePoint(i.start),
                    o = this.$clickSelection.comparePoint(i.end);
                if (s == -1 && o <= 0) {
                    t = this.$clickSelection.end;
                    if (i.end.row != r.row || i.end.column != r.column) r = i.start
                } else if (o == 1 && s >= 0) {
                    t = this.$clickSelection.start;
                    if (i.start.row != r.row || i.start.column != r.column) r = i.end
                } else if (s == -1 && o == 1) r = i.end, t = i.start;
                else {
                    var u = f(this.$clickSelection, r);
                    r = u.cursor, t = u.anchor
                }
                n.selection.setSelectionAnchor(t.row, t.column)
            }
            n.selection.selectToPosition(r), n.$blockScrolling--, n.renderer.scrollCursorIntoView()
        }, this.selectEnd = this.selectAllEnd = this.selectByWordsEnd = this.selectByLinesEnd = function() {
            this.$clickSelection = null, this.editor.unsetStyle("ace_selecting"), this.editor.renderer.scroller.releaseCapture && this.editor.renderer.scroller.releaseCapture()
        }, this.focusWait = function() {
            var e = a(this.mousedownEvent.x, this.mousedownEvent.y, this.x, this.y),
                t = Date.now();
            (e > o || t - this.mousedownEvent.time > this.$focusTimout) && this.startSelect(this.mousedownEvent.getDocumentPosition())
        }, this.onDoubleClick = function(e) {
            var t = e.getDocumentPosition(),
                n = this.editor,
                r = n.session,
                i = r.getBracketRange(t);
            i ? (i.isEmpty() && (i.start.column--, i.end.column++), this.setState("select")) : (i = n.selection.getWordRange(t.row, t.column), this.setState("selectByWords")), this.$clickSelection = i, this.select()
        }, this.onTripleClick = function(e) {
            var t = e.getDocumentPosition(),
                n = this.editor;
            this.setState("selectByLines");
            var r = n.getSelectionRange();
            r.isMultiLine() && r.contains(t.row, t.column) ? (this.$clickSelection = n.selection.getLineRange(r.start.row), this.$clickSelection.end = n.selection.getLineRange(r.end.row).end) : this.$clickSelection = n.selection.getLineRange(t.row), this.select()
        }, this.onQuadClick = function(e) {
            var t = this.editor;
            t.selectAll(), this.$clickSelection = t.getSelectionRange(), this.setState("selectAll")
        }, this.onMouseWheel = function(e) {
            if (e.getAccelKey()) return;
            e.getShiftKey() && e.wheelY && !e.wheelX && (e.wheelX = e.wheelY, e.wheelY = 0);
            var t = e.domEvent.timeStamp,
                n = t - (this.$lastScrollTime || 0),
                r = this.editor,
                i = r.renderer.isScrollableBy(e.wheelX * e.speed, e.wheelY * e.speed);
            if (i || n < 200) return this.$lastScrollTime = t, r.renderer.scrollBy(e.wheelX * e.speed, e.wheelY * e.speed), e.stop()
        }, this.onTouchMove = function(e) {
            var t = e.domEvent.timeStamp,
                n = t - (this.$lastScrollTime || 0),
                r = this.editor,
                i = r.renderer.isScrollableBy(e.wheelX * e.speed, e.wheelY * e.speed);
            if (i || n < 200) return this.$lastScrollTime = t, r.renderer.scrollBy(e.wheelX * e.speed, e.wheelY * e.speed), e.stop()
        }
    }).call(u.prototype), t.DefaultHandlers = u
}), define("ace/tooltip", ["require", "exports", "module", "ace/lib/oop", "ace/lib/dom"], function(e, t, n) {
    "use strict";

    function s(e) {
        this.isOpen = !1, this.$element = null, this.$parentNode = e
    }
    var r = e("./lib/oop"),
        i = e("./lib/dom");
    (function() {
        this.$init = function() {
            return this.$element = i.createElement("div"), this.$element.className = "ace_tooltip", this.$element.style.display = "none", this.$parentNode.appendChild(this.$element), this.$element
        }, this.getElement = function() {
            return this.$element || this.$init()
        }, this.setText = function(e) {
            i.setInnerText(this.getElement(), e)
        }, this.setHtml = function(e) {
            this.getElement().innerHTML = e
        }, this.setPosition = function(e, t) {
            this.getElement().style.left = e + "px", this.getElement().style.top = t + "px"
        }, this.setClassName = function(e) {
            i.addCssClass(this.getElement(), e)
        }, this.show = function(e, t, n) {
            e != null && this.setText(e), t != null && n != null && this.setPosition(t, n), this.isOpen || (this.getElement().style.display = "block", this.isOpen = !0)
        }, this.hide = function() {
            this.isOpen && (this.getElement().style.display = "none", this.isOpen = !1)
        }, this.getHeight = function() {
            return this.getElement().offsetHeight
        }, this.getWidth = function() {
            return this.getElement().offsetWidth
        }
    }).call(s.prototype), t.Tooltip = s
}), define("ace/mouse/default_gutter_handler", ["require", "exports", "module", "ace/lib/dom", "ace/lib/oop", "ace/lib/event", "ace/tooltip"], function(e, t, n) {
    "use strict";

    function u(e) {
        function l() {
            var r = u.getDocumentPosition().row,
                s = n.$annotations[r];
            if (!s) return c();
            var o = t.session.getLength();
            if (r == o) {
                var a = t.renderer.pixelToScreenCoordinates(0, u.y).row,
                    l = u.$pos;
                if (a > t.session.documentToScreenRow(l.row, l.column)) return c()
            }
            if (f == s) return;
            f = s.text.join("<br/>"), i.setHtml(f), i.show(), t.on("mousewheel", c);
            if (e.$tooltipFollowsMouse) h(u);
            else {
                var p = n.$cells[t.session.documentToScreenRow(r, 0)].element,
                    d = p.getBoundingClientRect(),
                    v = i.getElement().style;
                v.left = d.right + "px", v.top = d.bottom + "px"
            }
        }

        function c() {
            o && (o = clearTimeout(o)), f && (i.hide(), f = null, t.removeEventListener("mousewheel", c))
        }

        function h(e) {
            i.setPosition(e.x, e.y)
        }
        var t = e.editor,
            n = t.renderer.$gutterLayer,
            i = new a(t.container);
        e.editor.setDefaultHandler("guttermousedown", function(r) {
            if (!t.isFocused() || r.getButton() != 0) return;
            var i = n.getRegion(r);
            if (i == "foldWidgets") return;
            var s = r.getDocumentPosition().row,
                o = t.session.selection;
            if (r.getShiftKey()) o.selectTo(s, 0);
            else {
                if (r.domEvent.detail == 2) return t.selectAll(), r.preventDefault();
                e.$clickSelection = t.selection.getLineRange(s)
            }
            return e.setState("selectByLines"), e.captureMouse(r), r.preventDefault()
        });
        var o, u, f;
        e.editor.setDefaultHandler("guttermousemove", function(t) {
            var n = t.domEvent.target || t.domEvent.srcElement;
            if (r.hasCssClass(n, "ace_fold-widget")) return c();
            f && e.$tooltipFollowsMouse && h(t), u = t;
            if (o) return;
            o = setTimeout(function() {
                o = null, u && !e.isMousePressed ? l() : c()
            }, 50)
        }), s.addListener(t.renderer.$gutter, "mouseout", function(e) {
            u = null;
            if (!f || o) return;
            o = setTimeout(function() {
                o = null, c()
            }, 50)
        }), t.on("changeSession", c)
    }

    function a(e) {
        o.call(this, e)
    }
    var r = e("../lib/dom"),
        i = e("../lib/oop"),
        s = e("../lib/event"),
        o = e("../tooltip").Tooltip;
    i.inherits(a, o),
        function() {
            this.setPosition = function(e, t) {
                var n = window.innerWidth || document.documentElement.clientWidth,
                    r = window.innerHeight || document.documentElement.clientHeight,
                    i = this.getWidth(),
                    s = this.getHeight();
                e += 15, t += 15, e + i > n && (e -= e + i - n), t + s > r && (t -= 20 + s), o.prototype.setPosition.call(this, e, t)
            }
        }.call(a.prototype), t.GutterHandler = u
}), define("ace/mouse/mouse_event", ["require", "exports", "module", "ace/lib/event", "ace/lib/useragent"], function(e, t, n) {
    "use strict";
    var r = e("../lib/event"),
        i = e("../lib/useragent"),
        s = t.MouseEvent = function(e, t) {
            this.domEvent = e, this.editor = t, this.x = this.clientX = e.clientX, this.y = this.clientY = e.clientY, this.$pos = null, this.$inSelection = null, this.propagationStopped = !1, this.defaultPrevented = !1
        };
    (function() {
        this.stopPropagation = function() {
            r.stopPropagation(this.domEvent), this.propagationStopped = !0
        }, this.preventDefault = function() {
            r.preventDefault(this.domEvent), this.defaultPrevented = !0
        }, this.stop = function() {
            this.stopPropagation(), this.preventDefault()
        }, this.getDocumentPosition = function() {
            return this.$pos ? this.$pos : (this.$pos = this.editor.renderer.screenToTextCoordinates(this.clientX, this.clientY), this.$pos)
        }, this.inSelection = function() {
            if (this.$inSelection !== null) return this.$inSelection;
            var e = this.editor,
                t = e.getSelectionRange();
            if (t.isEmpty()) this.$inSelection = !1;
            else {
                var n = this.getDocumentPosition();
                this.$inSelection = t.contains(n.row, n.column)
            }
            return this.$inSelection
        }, this.getButton = function() {
            return r.getButton(this.domEvent)
        }, this.getShiftKey = function() {
            return this.domEvent.shiftKey
        }, this.getAccelKey = i.isMac ? function() {
            return this.domEvent.metaKey
        } : function() {
            return this.domEvent.ctrlKey
        }
    }).call(s.prototype)
}), define("ace/mouse/dragdrop_handler", ["require", "exports", "module", "ace/lib/dom", "ace/lib/event", "ace/lib/useragent"], function(e, t, n) {
    "use strict";

    function f(e) {
        function T(e, n) {
            var r = Date.now(),
                i = !n || e.row != n.row,
                s = !n || e.column != n.column;
            if (!S || i || s) t.$blockScrolling += 1, t.moveCursorToPosition(e), t.$blockScrolling -= 1, S = r, x = {
                x: p,
                y: d
            };
            else {
                var o = l(x.x, x.y, p, d);
                o > a ? S = null : r - S >= u && (t.renderer.scrollCursorIntoView(), S = null)
            }
        }

        function N(e, n) {
            var r = Date.now(),
                i = t.renderer.layerConfig.lineHeight,
                s = t.renderer.layerConfig.characterWidth,
                u = t.renderer.scroller.getBoundingClientRect(),
                a = {
                    x: {
                        left: p - u.left,
                        right: u.right - p
                    },
                    y: {
                        top: d - u.top,
                        bottom: u.bottom - d
                    }
                },
                f = Math.min(a.x.left, a.x.right),
                l = Math.min(a.y.top, a.y.bottom),
                c = {
                    row: e.row,
                    column: e.column
                };
            f / s <= 2 && (c.column += a.x.left < a.x.right ? -3 : 2), l / i <= 1 && (c.row += a.y.top < a.y.bottom ? -1 : 1);
            var h = e.row != c.row,
                v = e.column != c.column,
                m = !n || e.row != n.row;
            h || v && !m ? E ? r - E >= o && t.renderer.scrollCursorIntoView(c) : E = r : E = null
        }

        function C() {
            var e = g;
            g = t.renderer.screenToTextCoordinates(p, d), T(g, e), N(g, e)
        }

        function k() {
            m = t.selection.toOrientedRange(), h = t.session.addMarker(m, "ace_selection", t.getSelectionStyle()), t.clearSelection(), t.isFocused() && t.renderer.$cursorLayer.setBlinking(!1), clearInterval(v), C(), v = setInterval(C, 20), y = 0, i.addListener(document, "mousemove", O)
        }

        function L() {
            clearInterval(v), t.session.removeMarker(h), h = null, t.$blockScrolling += 1, t.selection.fromOrientedRange(m), t.$blockScrolling -= 1, t.isFocused() && !w && t.renderer.$cursorLayer.setBlinking(!t.getReadOnly()), m = null, g = null, y = 0, E = null, S = null, i.removeListener(document, "mousemove", O)
        }

        function O() {
            A == null && (A = setTimeout(function() {
                A != null && h && L()
            }, 20))
        }

        function M(e) {
            var t = e.types;
            return !t || Array.prototype.some.call(t, function(e) {
                return e == "text/plain" || e == "Text"
            })
        }

        function _(e) {
            var t = ["copy", "copymove", "all", "uninitialized"],
                n = ["move", "copymove", "linkmove", "all", "uninitialized"],
                r = s.isMac ? e.altKey : e.ctrlKey,
                i = "uninitialized";
            try {
                i = e.dataTransfer.effectAllowed.toLowerCase()
            } catch (e) {}
            var o = "none";
            return r && t.indexOf(i) >= 0 ? o = "copy" : n.indexOf(i) >= 0 ? o = "move" : t.indexOf(i) >= 0 && (o = "copy"), o
        }
        var t = e.editor,
            n = r.createElement("img");
        n.src = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==", s.isOpera && (n.style.cssText = "width:1px;height:1px;position:fixed;top:0;left:0;z-index:2147483647;opacity:0;");
        var f = ["dragWait", "dragWaitEnd", "startDrag", "dragReadyEnd", "onMouseDrag"];
        f.forEach(function(t) {
            e[t] = this[t]
        }, this), t.addEventListener("mousedown", this.onMouseDown.bind(e));
        var c = t.container,
            h, p, d, v, m, g, y = 0,
            b, w, E, S, x;
        this.onDragStart = function(e) {
            if (this.cancelDrag || !c.draggable) {
                var r = this;
                return setTimeout(function() {
                    r.startSelect(), r.captureMouse(e)
                }, 0), e.preventDefault()
            }
            m = t.getSelectionRange();
            var i = e.dataTransfer;
            i.effectAllowed = t.getReadOnly() ? "copy" : "copyMove", s.isOpera && (t.container.appendChild(n), n.scrollTop = 0), i.setDragImage && i.setDragImage(n, 0, 0), s.isOpera && t.container.removeChild(n), i.clearData(), i.setData("Text", t.session.getTextRange()), w = !0, this.setState("drag")
        }, this.onDragEnd = function(e) {
            c.draggable = !1, w = !1, this.setState(null);
            if (!t.getReadOnly()) {
                var n = e.dataTransfer.dropEffect;
                !b && n == "move" && t.session.remove(t.getSelectionRange()), t.renderer.$cursorLayer.setBlinking(!0)
            }
            this.editor.unsetStyle("ace_dragging"), this.editor.renderer.setCursorStyle("")
        }, this.onDragEnter = function(e) {
            if (t.getReadOnly() || !M(e.dataTransfer)) return;
            return p = e.clientX, d = e.clientY, h || k(), y++, e.dataTransfer.dropEffect = b = _(e), i.preventDefault(e)
        }, this.onDragOver = function(e) {
            if (t.getReadOnly() || !M(e.dataTransfer)) return;
            return p = e.clientX, d = e.clientY, h || (k(), y++), A !== null && (A = null), e.dataTransfer.dropEffect = b = _(e), i.preventDefault(e)
        }, this.onDragLeave = function(e) {
            y--;
            if (y <= 0 && h) return L(), b = null, i.preventDefault(e)
        }, this.onDrop = function(e) {
            if (!g) return;
            var n = e.dataTransfer;
            if (w) switch (b) {
                case "move":
                    m.contains(g.row, g.column) ? m = {
                        start: g,
                        end: g
                    } : m = t.moveText(m, g);
                    break;
                case "copy":
                    m = t.moveText(m, g, !0)
            } else {
                var r = n.getData("Text");
                m = {
                    start: g,
                    end: t.session.insert(g, r)
                }, t.focus(), b = null
            }
            return L(), i.preventDefault(e)
        }, i.addListener(c, "dragstart", this.onDragStart.bind(e)), i.addListener(c, "dragend", this.onDragEnd.bind(e)), i.addListener(c, "dragenter", this.onDragEnter.bind(e)), i.addListener(c, "dragover", this.onDragOver.bind(e)), i.addListener(c, "dragleave", this.onDragLeave.bind(e)), i.addListener(c, "drop", this.onDrop.bind(e));
        var A = null
    }

    function l(e, t, n, r) {
        return Math.sqrt(Math.pow(n - e, 2) + Math.pow(r - t, 2))
    }
    var r = e("../lib/dom"),
        i = e("../lib/event"),
        s = e("../lib/useragent"),
        o = 200,
        u = 200,
        a = 5;
    (function() {
        this.dragWait = function() {
            var e = Date.now() - this.mousedownEvent.time;
            e > this.editor.getDragDelay() && this.startDrag()
        }, this.dragWaitEnd = function() {
            var e = this.editor.container;
            e.draggable = !1, this.startSelect(this.mousedownEvent.getDocumentPosition()), this.selectEnd()
        }, this.dragReadyEnd = function(e) {
            this.editor.renderer.$cursorLayer.setBlinking(!this.editor.getReadOnly()), this.editor.unsetStyle("ace_dragging"), this.editor.renderer.setCursorStyle(""), this.dragWaitEnd()
        }, this.startDrag = function() {
            this.cancelDrag = !1;
            var e = this.editor,
                t = e.container;
            t.draggable = !0, e.renderer.$cursorLayer.setBlinking(!1), e.setStyle("ace_dragging");
            var n = s.isWin ? "default" : "move";
            e.renderer.setCursorStyle(n), this.setState("dragReady")
        }, this.onMouseDrag = function(e) {
            var t = this.editor.container;
            if (s.isIE && this.state == "dragReady") {
                var n = l(this.mousedownEvent.x, this.mousedownEvent.y, this.x, this.y);
                n > 3 && t.dragDrop()
            }
            if (this.state === "dragWait") {
                var n = l(this.mousedownEvent.x, this.mousedownEvent.y, this.x, this.y);
                n > 0 && (t.draggable = !1, this.startSelect(this.mousedownEvent.getDocumentPosition()))
            }
        }, this.onMouseDown = function(e) {
            if (!this.$dragEnabled) return;
            this.mousedownEvent = e;
            var t = this.editor,
                n = e.inSelection(),
                r = e.getButton(),
                i = e.domEvent.detail || 1;
            if (i === 1 && r === 0 && n) {
                if (e.editor.inMultiSelectMode && (e.getAccelKey() || e.getShiftKey())) return;
                this.mousedownEvent.time = Date.now();
                var o = e.domEvent.target || e.domEvent.srcElement;
                "unselectable" in o && (o.unselectable = "on");
                if (t.getDragDelay()) {
                    if (s.isWebKit) {
                        this.cancelDrag = !0;
                        var u = t.container;
                        u.draggable = !0
                    }
                    this.setState("dragWait")
                } else this.startDrag();
                this.captureMouse(e, this.onMouseDrag.bind(this)), e.defaultPrevented = !0
            }
        }
    }).call(f.prototype), t.DragdropHandler = f
}), define("ace/lib/net", ["require", "exports", "module", "ace/lib/dom"], function(e, t, n) {
    "use strict";
    var r = e("./dom");
    t.get = function(e, t) {
        var n = new XMLHttpRequest;
        n.open("GET", e, !0), n.onreadystatechange = function() {
            n.readyState === 4 && t(n.responseText)
        }, n.send(null)
    }, t.loadScript = function(e, t) {
        var n = r.getDocumentHead(),
            i = document.createElement("script");
        i.src = e, n.appendChild(i), i.onload = i.onreadystatechange = function(e, n) {
            if (n || !i.readyState || i.readyState == "loaded" || i.readyState == "complete") i = i.onload = i.onreadystatechange = null, n || t()
        }
    }, t.qualifyURL = function(e) {
        var t = document.createElement("a");
        return t.href = e, t.href
    }
}), define("ace/lib/event_emitter", ["require", "exports", "module"], function(e, t, n) {
    "use strict";
    var r = {},
        i = function() {
            this.propagationStopped = !0
        },
        s = function() {
            this.defaultPrevented = !0
        };
    r._emit = r._dispatchEvent = function(e, t) {
        this._eventRegistry || (this._eventRegistry = {}), this._defaultHandlers || (this._defaultHandlers = {});
        var n = this._eventRegistry[e] || [],
            r = this._defaultHandlers[e];
        if (!n.length && !r) return;
        if (typeof t != "object" || !t) t = {};
        t.type || (t.type = e), t.stopPropagation || (t.stopPropagation = i), t.preventDefault || (t.preventDefault = s), n = n.slice();
        for (var o = 0; o < n.length; o++) {
            n[o](t, this);
            if (t.propagationStopped) break
        }
        if (r && !t.defaultPrevented) return r(t, this)
    }, r._signal = function(e, t) {
        var n = (this._eventRegistry || {})[e];
        if (!n) return;
        n = n.slice();
        for (var r = 0; r < n.length; r++) n[r](t, this)
    }, r.once = function(e, t) {
        var n = this;
        t && this.addEventListener(e, function r() {
            n.removeEventListener(e, r), t.apply(null, arguments)
        })
    }, r.setDefaultHandler = function(e, t) {
        var n = this._defaultHandlers;
        n || (n = this._defaultHandlers = {
            _disabled_: {}
        });
        if (n[e]) {
            var r = n[e],
                i = n._disabled_[e];
            i || (n._disabled_[e] = i = []), i.push(r);
            var s = i.indexOf(t);
            s != -1 && i.splice(s, 1)
        }
        n[e] = t
    }, r.removeDefaultHandler = function(e, t) {
        var n = this._defaultHandlers;
        if (!n) return;
        var r = n._disabled_[e];
        if (n[e] == t) {
            var i = n[e];
            r && this.setDefaultHandler(e, r.pop())
        } else if (r) {
            var s = r.indexOf(t);
            s != -1 && r.splice(s, 1)
        }
    }, r.on = r.addEventListener = function(e, t, n) {
        this._eventRegistry = this._eventRegistry || {};
        var r = this._eventRegistry[e];
        return r || (r = this._eventRegistry[e] = []), r.indexOf(t) == -1 && r[n ? "unshift" : "push"](t), t
    }, r.off = r.removeListener = r.removeEventListener = function(e, t) {
        this._eventRegistry = this._eventRegistry || {};
        var n = this._eventRegistry[e];
        if (!n) return;
        var r = n.indexOf(t);
        r !== -1 && n.splice(r, 1)
    }, r.removeAllListeners = function(e) {
        this._eventRegistry && (this._eventRegistry[e] = [])
    }, t.EventEmitter = r
}), define("ace/lib/app_config", ["require", "exports", "module", "ace/lib/oop", "ace/lib/event_emitter"], function(e, t, n) {
    "no use strict";

    function o(e) {
        typeof console != "undefined" && console.warn && console.warn.apply(console, arguments)
    }

    function u(e, t) {
        var n = new Error(e);
        n.data = t, typeof console == "object" && console.error && console.error(n), setTimeout(function() {
            throw n
        })
    }
    var r = e("./oop"),
        i = e("./event_emitter").EventEmitter,
        s = {
            setOptions: function(e) {
                Object.keys(e).forEach(function(t) {
                    this.setOption(t, e[t])
                }, this)
            },
            getOptions: function(e) {
                var t = {};
                return e ? Array.isArray(e) || (t = e, e = Object.keys(t)) : e = Object.keys(this.$options), e.forEach(function(e) {
                    t[e] = this.getOption(e)
                }, this), t
            },
            setOption: function(e, t) {
                if (this["$" + e] === t) return;
                var n = this.$options[e];
                if (!n) return o('misspelled option "' + e + '"');
                if (n.forwardTo) return this[n.forwardTo] && this[n.forwardTo].setOption(e, t);
                n.handlesSet || (this["$" + e] = t), n && n.set && n.set.call(this, t)
            },
            getOption: function(e) {
                var t = this.$options[e];
                return t ? t.forwardTo ? this[t.forwardTo] && this[t.forwardTo].getOption(e) : t && t.get ? t.get.call(this) : this["$" + e] : o('misspelled option "' + e + '"')
            }
        },
        a = function() {
            this.$defaultOptions = {}
        };
    (function() {
        r.implement(this, i), this.defineOptions = function(e, t, n) {
            return e.$options || (this.$defaultOptions[t] = e.$options = {}), Object.keys(n).forEach(function(t) {
                var r = n[t];
                typeof r == "string" && (r = {
                    forwardTo: r
                }), r.name || (r.name = t), e.$options[r.name] = r, "initialValue" in r && (e["$" + r.name] = r.initialValue)
            }), r.implement(e, s), this
        }, this.resetOptions = function(e) {
            Object.keys(e.$options).forEach(function(t) {
                var n = e.$options[t];
                "value" in n && e.setOption(t, n.value)
            })
        }, this.setDefaultValue = function(e, t, n) {
            var r = this.$defaultOptions[e] || (this.$defaultOptions[e] = {});
            r[t] && (r.forwardTo ? this.setDefaultValue(r.forwardTo, t, n) : r[t].value = n)
        }, this.setDefaultValues = function(e, t) {
            Object.keys(t).forEach(function(n) {
                this.setDefaultValue(e, n, t[n])
            }, this)
        }, this.warn = o, this.reportError = u
    }).call(a.prototype), t.AppConfig = a
}), define("ace/config", ["require", "exports", "module", "ace/lib/lang", "ace/lib/oop", "ace/lib/net", "ace/lib/app_config"], function(e, t, n) {
    "no use strict";

    function f(r) {
        a.packaged = r || e.packaged || n.packaged || u.define && define.packaged;
        if (!u.document) return "";
        var i = {},
            s = "",
            o = document.currentScript || document._currentScript,
            f = o && o.ownerDocument || document,
            c = f.getElementsByTagName("script");
        for (var h = 0; h < c.length; h++) {
            var p = c[h],
                d = p.src || p.getAttribute("src");
            if (!d) continue;
            var v = p.attributes;
            for (var m = 0, g = v.length; m < g; m++) {
                var y = v[m];
                y.name.indexOf("data-ace-") === 0 && (i[l(y.name.replace(/^data-ace-/, ""))] = y.value)
            }
            var b = d.match(/^(.*)\/ace(\-\w+)?\.js(\?|$)/);
            b && (s = b[1])
        }
        s && (i.base = i.base || s, i.packaged = !0), i.basePath = i.base, i.workerPath = i.workerPath || i.base, i.modePath = i.modePath || i.base, i.themePath = i.themePath || i.base, delete i.base;
        for (var w in i) typeof i[w] != "undefined" && t.set(w, i[w])
    }

    function l(e) {
        return e.replace(/-(.)/g, function(e, t) {
            return t.toUpperCase()
        })
    }
    var r = e("./lib/lang"),
        i = e("./lib/oop"),
        s = e("./lib/net"),
        o = e("./lib/app_config").AppConfig;
    n.exports = t = new o;
    var u = function() {
            return this || typeof window != "undefined" && window
        }(),
        a = {
            packaged: !1,
            workerPath: null,
            modePath: null,
            themePath: null,
            basePath: "",
            suffix: ".js",
            $moduleUrls: {}
        };
    t.get = function(e) {
        if (!a.hasOwnProperty(e)) throw new Error("Unknown config key: " + e);
        return a[e]
    }, t.set = function(e, t) {
        if (!a.hasOwnProperty(e)) throw new Error("Unknown config key: " + e);
        a[e] = t
    }, t.all = function() {
        return r.copyObject(a)
    }, t.moduleUrl = function(e, t) {
        if (a.$moduleUrls[e]) return a.$moduleUrls[e];
        var n = e.split("/");
        t = t || n[n.length - 2] || "";
        var r = t == "snippets" ? "/" : "-",
            i = n[n.length - 1];
        if (t == "worker" && r == "-") {
            var s = new RegExp("^" + t + "[\\-_]|[\\-_]" + t + "$", "g");
            i = i.replace(s, "")
        }(!i || i == t) && n.length > 1 && (i = n[n.length - 2]);
        var o = a[t + "Path"];
        return o == null ? o = a.basePath : r == "/" && (t = r = ""), o && o.slice(-1) != "/" && (o += "/"), o + t + r + i + this.get("suffix")
    }, t.setModuleUrl = function(e, t) {
        return a.$moduleUrls[e] = t
    }, t.$loading = {}, t.loadModule = function(n, r) {
        var i, o;
        Array.isArray(n) && (o = n[0], n = n[1]);
        try {
            i = e(n)
        } catch (u) {}
        if (i && !t.$loading[n]) return r && r(i);
        t.$loading[n] || (t.$loading[n] = []), t.$loading[n].push(r);
        if (t.$loading[n].length > 1) return;
        var a = function() {
            e([n], function(e) {
                t._emit("load.module", {
                    name: n,
                    module: e
                });
                var r = t.$loading[n];
                t.$loading[n] = null, r.forEach(function(t) {
                    t && t(e)
                })
            })
        };
        if (!t.get("packaged")) return a();
        s.loadScript(t.moduleUrl(n, o), a)
    }, t.init = f
}), define("ace/mouse/mouse_handler", ["require", "exports", "module", "ace/lib/event", "ace/lib/useragent", "ace/mouse/default_handlers", "ace/mouse/default_gutter_handler", "ace/mouse/mouse_event", "ace/mouse/dragdrop_handler", "ace/config"], function(e, t, n) {
    "use strict";
    var r = e("../lib/event"),
        i = e("../lib/useragent"),
        s = e("./default_handlers").DefaultHandlers,
        o = e("./default_gutter_handler").GutterHandler,
        u = e("./mouse_event").MouseEvent,
        a = e("./dragdrop_handler").DragdropHandler,
        f = e("../config"),
        l = function(e) {
            var t = this;
            this.editor = e, new s(this), new o(this), new a(this);
            var n = function(t) {
                    (!document.hasFocus || !document.hasFocus()) && window.focus(), e.focus()
                },
                u = e.renderer.getMouseEventTarget();
            r.addListener(u, "click", this.onMouseEvent.bind(this, "click")), r.addListener(u, "mousemove", this.onMouseMove.bind(this, "mousemove")), r.addMultiMouseDownListener(u, [400, 300, 250], this, "onMouseEvent"), e.renderer.scrollBarV && (r.addMultiMouseDownListener(e.renderer.scrollBarV.inner, [400, 300, 250], this, "onMouseEvent"), r.addMultiMouseDownListener(e.renderer.scrollBarH.inner, [400, 300, 250], this, "onMouseEvent"), i.isIE && (r.addListener(e.renderer.scrollBarV.element, "mousedown", n), r.addListener(e.renderer.scrollBarH.element, "mousedown", n))), r.addMouseWheelListener(e.container, this.onMouseWheel.bind(this, "mousewheel")), r.addTouchMoveListener(e.container, this.onTouchMove.bind(this, "touchmove"));
            var f = e.renderer.$gutter;
            r.addListener(f, "mousedown", this.onMouseEvent.bind(this, "guttermousedown")), r.addListener(f, "click", this.onMouseEvent.bind(this, "gutterclick")), r.addListener(f, "dblclick", this.onMouseEvent.bind(this, "gutterdblclick")), r.addListener(f, "mousemove", this.onMouseEvent.bind(this, "guttermousemove")), r.addListener(u, "mousedown", n), r.addListener(f, "mousedown", function(t) {
                return e.focus(), r.preventDefault(t)
            }), e.on("mousemove", function(n) {
                if (t.state || t.$dragDelay || !t.$dragEnabled) return;
                var r = e.renderer.screenToTextCoordinates(n.x, n.y),
                    i = e.session.selection.getRange(),
                    s = e.renderer;
                !i.isEmpty() && i.insideStart(r.row, r.column) ? s.setCursorStyle("default") : s.setCursorStyle("")
            })
        };
    (function() {
        this.onMouseEvent = function(e, t) {
            this.editor._emit(e, new u(t, this.editor))
        }, this.onMouseMove = function(e, t) {
            var n = this.editor._eventRegistry && this.editor._eventRegistry.mousemove;
            if (!n || !n.length) return;
            this.editor._emit(e, new u(t, this.editor))
        }, this.onMouseWheel = function(e, t) {
            var n = new u(t, this.editor);
            n.speed = this.$scrollSpeed * 2, n.wheelX = t.wheelX, n.wheelY = t.wheelY, this.editor._emit(e, n)
        }, this.onTouchMove = function(e, t) {
            var n = new u(t, this.editor);
            n.speed = 1, n.wheelX = t.wheelX, n.wheelY = t.wheelY, this.editor._emit(e, n)
        }, this.setState = function(e) {
            this.state = e
        }, this.captureMouse = function(e, t) {
            this.x = e.x, this.y = e.y, this.isMousePressed = !0;
            var n = this.editor.renderer;
            n.$keepTextAreaAtCursor && (n.$keepTextAreaAtCursor = null);
            var s = this,
                o = function(e) {
                    if (!e) return;
                    if (i.isWebKit && !e.which && s.releaseMouse) return s.releaseMouse();
                    s.x = e.clientX, s.y = e.clientY, t && t(e), s.mouseEvent = new u(e, s.editor), s.$mouseMoved = !0
                },
                a = function(e) {
                    clearInterval(l), f(), s[s.state + "End"] && s[s.state + "End"](e), s.state = "", n.$keepTextAreaAtCursor == null && (n.$keepTextAreaAtCursor = !0, n.$moveTextAreaToCursor()), s.isMousePressed = !1, s.$onCaptureMouseMove = s.releaseMouse = null, e && s.onMouseEvent("mouseup", e)
                },
                f = function() {
                    s[s.state] && s[s.state](), s.$mouseMoved = !1
                };
            if (i.isOldIE && e.domEvent.type == "dblclick") return setTimeout(function() {
                a(e)
            });
            s.$onCaptureMouseMove = o, s.releaseMouse = r.capture(this.editor.container, o, a);
            var l = setInterval(f, 20)
        }, this.releaseMouse = null, this.cancelContextMenu = function() {
            var e = function(t) {
                if (t && t.domEvent && t.domEvent.type != "contextmenu") return;
                this.editor.off("nativecontextmenu", e), t && t.domEvent && r.stopEvent(t.domEvent)
            }.bind(this);
            setTimeout(e, 10), this.editor.on("nativecontextmenu", e)
        }
    }).call(l.prototype), f.defineOptions(l.prototype, "mouseHandler", {
        scrollSpeed: {
            initialValue: 2
        },
        dragDelay: {
            initialValue: i.isMac ? 150 : 0
        },
        dragEnabled: {
            initialValue: !0
        },
        focusTimout: {
            initialValue: 0
        },
        tooltipFollowsMouse: {
            initialValue: !0
        }
    }), t.MouseHandler = l
}), define("ace/mouse/fold_handler", ["require", "exports", "module"], function(e, t, n) {
    "use strict";

    function r(e) {
        e.on("click", function(t) {
            var n = t.getDocumentPosition(),
                r = e.session,
                i = r.getFoldAt(n.row, n.column, 1);
            i && (t.getAccelKey() ? r.removeFold(i) : r.expandFold(i), t.stop())
        }), e.on("gutterclick", function(t) {
            var n = e.renderer.$gutterLayer.getRegion(t);
            if (n == "foldWidgets") {
                var r = t.getDocumentPosition().row,
                    i = e.session;
                i.foldWidgets && i.foldWidgets[r] && e.session.onFoldWidgetClick(r, t), e.isFocused() || e.focus(), t.stop()
            }
        }), e.on("gutterdblclick", function(t) {
            var n = e.renderer.$gutterLayer.getRegion(t);
            if (n == "foldWidgets") {
                var r = t.getDocumentPosition().row,
                    i = e.session,
                    s = i.getParentFoldRangeData(r, !0),
                    o = s.range || s.firstRange;
                if (o) {
                    r = o.start.row;
                    var u = i.getFoldAt(r, i.getLine(r).length, 1);
                    u ? i.removeFold(u) : (i.addFold("...", o), e.renderer.scrollCursorIntoView({
                        row: o.start.row,
                        column: 0
                    }))
                }
                t.stop()
            }
        })
    }
    t.FoldHandler = r
}), define("ace/keyboard/keybinding", ["require", "exports", "module", "ace/lib/keys", "ace/lib/event"], function(e, t, n) {
    "use strict";
    var r = e("../lib/keys"),
        i = e("../lib/event"),
        s = function(e) {
            this.$editor = e, this.$data = {
                editor: e
            }, this.$handlers = [], this.setDefaultHandler(e.commands)
        };
    (function() {
        this.setDefaultHandler = function(e) {
            this.removeKeyboardHandler(this.$defaultHandler), this.$defaultHandler = e, this.addKeyboardHandler(e, 0)
        }, this.setKeyboardHandler = function(e) {
            var t = this.$handlers;
            if (t[t.length - 1] == e) return;
            while (t[t.length - 1] && t[t.length - 1] != this.$defaultHandler) this.removeKeyboardHandler(t[t.length - 1]);
            this.addKeyboardHandler(e, 1)
        }, this.addKeyboardHandler = function(e, t) {
            if (!e) return;
            typeof e == "function" && !e.handleKeyboard && (e.handleKeyboard = e);
            var n = this.$handlers.indexOf(e);
            n != -1 && this.$handlers.splice(n, 1), t == undefined ? this.$handlers.push(e) : this.$handlers.splice(t, 0, e), n == -1 && e.attach && e.attach(this.$editor)
        }, this.removeKeyboardHandler = function(e) {
            var t = this.$handlers.indexOf(e);
            return t == -1 ? !1 : (this.$handlers.splice(t, 1), e.detach && e.detach(this.$editor), !0)
        }, this.getKeyboardHandler = function() {
            return this.$handlers[this.$handlers.length - 1]
        }, this.getStatusText = function() {
            var e = this.$data,
                t = e.editor;
            return this.$handlers.map(function(n) {
                return n.getStatusText && n.getStatusText(t, e) || ""
            }).filter(Boolean).join(" ")
        }, this.$callKeyboardHandlers = function(e, t, n, r) {
            var s, o = !1,
                u = this.$editor.commands;
            for (var a = this.$handlers.length; a--;) {
                s = this.$handlers[a].handleKeyboard(this.$data, e, t, n, r);
                if (!s || !s.command) continue;
                s.command == "null" ? o = !0 : o = u.exec(s.command, this.$editor, s.args, r), o && r && e != -1 && s.passEvent != 1 && s.command.passEvent != 1 && i.stopEvent(r);
                if (o) break
            }
            return o
        }, this.onCommandKey = function(e, t, n) {
            var i = r.keyCodeToString(n);
            this.$callKeyboardHandlers(t, i, n, e)
        }, this.onTextInput = function(e) {
            var t = this.$callKeyboardHandlers(-1, e);
            t || this.$editor.commands.exec("insertstring", this.$editor, e)
        }
    }).call(s.prototype), t.KeyBinding = s
}), define("ace/range", ["require", "exports", "module"], function(e, t, n) {
    "use strict";
    var r = function(e, t) {
            return e.row - t.row || e.column - t.column
        },
        i = function(e, t, n, r) {
            this.start = {
                row: e,
                column: t
            }, this.end = {
                row: n,
                column: r
            }
        };
    (function() {
        this.isEqual = function(e) {
            return this.start.row === e.start.row && this.end.row === e.end.row && this.start.column === e.start.column && this.end.column === e.end.column
        }, this.toString = function() {
            return "Range: [" + this.start.row + "/" + this.start.column + "] -> [" + this.end.row + "/" + this.end.column + "]"
        }, this.contains = function(e, t) {
            return this.compare(e, t) == 0
        }, this.compareRange = function(e) {
            var t, n = e.end,
                r = e.start;
            return t = this.compare(n.row, n.column), t == 1 ? (t = this.compare(r.row, r.column), t == 1 ? 2 : t == 0 ? 1 : 0) : t == -1 ? -2 : (t = this.compare(r.row, r.column), t == -1 ? -1 : t == 1 ? 42 : 0)
        }, this.comparePoint = function(e) {
            return this.compare(e.row, e.column)
        }, this.containsRange = function(e) {
            return this.comparePoint(e.start) == 0 && this.comparePoint(e.end) == 0
        }, this.intersects = function(e) {
            var t = this.compareRange(e);
            return t == -1 || t == 0 || t == 1
        }, this.isEnd = function(e, t) {
            return this.end.row == e && this.end.column == t
        }, this.isStart = function(e, t) {
            return this.start.row == e && this.start.column == t
        }, this.setStart = function(e, t) {
            typeof e == "object" ? (this.start.column = e.column, this.start.row = e.row) : (this.start.row = e, this.start.column = t)
        }, this.setEnd = function(e, t) {
            typeof e == "object" ? (this.end.column = e.column, this.end.row = e.row) : (this.end.row = e, this.end.column = t)
        }, this.inside = function(e, t) {
            return this.compare(e, t) == 0 ? this.isEnd(e, t) || this.isStart(e, t) ? !1 : !0 : !1
        }, this.insideStart = function(e, t) {
            return this.compare(e, t) == 0 ? this.isEnd(e, t) ? !1 : !0 : !1
        }, this.insideEnd = function(e, t) {
            return this.compare(e, t) == 0 ? this.isStart(e, t) ? !1 : !0 : !1
        }, this.compare = function(e, t) {
            return !this.isMultiLine() && e === this.start.row ? t < this.start.column ? -1 : t > this.end.column ? 1 : 0 : e < this.start.row ? -1 : e > this.end.row ? 1 : this.start.row === e ? t >= this.start.column ? 0 : -1 : this.end.row === e ? t <= this.end.column ? 0 : 1 : 0
        }, this.compareStart = function(e, t) {
            return this.start.row == e && this.start.column == t ? -1 : this.compare(e, t)
        }, this.compareEnd = function(e, t) {
            return this.end.row == e && this.end.column == t ? 1 : this.compare(e, t)
        }, this.compareInside = function(e, t) {
            return this.end.row == e && this.end.column == t ? 1 : this.start.row == e && this.start.column == t ? -1 : this.compare(e, t)
        }, this.clipRows = function(e, t) {
            if (this.end.row > t) var n = {
                row: t + 1,
                column: 0
            };
            else if (this.end.row < e) var n = {
                row: e,
                column: 0
            };
            if (this.start.row > t) var r = {
                row: t + 1,
                column: 0
            };
            else if (this.start.row < e) var r = {
                row: e,
                column: 0
            };
            return i.fromPoints(r || this.start, n || this.end)
        }, this.extend = function(e, t) {
            var n = this.compare(e, t);
            if (n == 0) return this;
            if (n == -1) var r = {
                row: e,
                column: t
            };
            else var s = {
                row: e,
                column: t
            };
            return i.fromPoints(r || this.start, s || this.end)
        }, this.isEmpty = function() {
            return this.start.row === this.end.row && this.start.column === this.end.column
        }, this.isMultiLine = function() {
            return this.start.row !== this.end.row
        }, this.clone = function() {
            return i.fromPoints(this.start, this.end)
        }, this.collapseRows = function() {
            return this.end.column == 0 ? new i(this.start.row, 0, Math.max(this.start.row, this.end.row - 1), 0) : new i(this.start.row, 0, this.end.row, 0)
        }, this.toScreenRange = function(e) {
            var t = e.documentToScreenPosition(this.start),
                n = e.documentToScreenPosition(this.end);
            return new i(t.row, t.column, n.row, n.column)
        }, this.moveBy = function(e, t) {
            this.start.row += e, this.start.column += t, this.end.row += e, this.end.column += t
        }
    }).call(i.prototype), i.fromPoints = function(e, t) {
        return new i(e.row, e.column, t.row, t.column)
    }, i.comparePoints = r, i.comparePoints = function(e, t) {
        return e.row - t.row || e.column - t.column
    }, t.Range = i
}), define("ace/selection", ["require", "exports", "module", "ace/lib/oop", "ace/lib/lang", "ace/lib/event_emitter", "ace/range"], function(e, t, n) {
    "use strict";
    var r = e("./lib/oop"),
        i = e("./lib/lang"),
        s = e("./lib/event_emitter").EventEmitter,
        o = e("./range").Range,
        u = function(e) {
            this.session = e, this.doc = e.getDocument(), this.clearSelection(), this.lead = this.selectionLead = this.doc.createAnchor(0, 0), this.anchor = this.selectionAnchor = this.doc.createAnchor(0, 0);
            var t = this;
            this.lead.on("change", function(e) {
                t._emit("changeCursor"), t.$isEmpty || t._emit("changeSelection"), !t.$keepDesiredColumnOnChange && e.old.column != e.value.column && (t.$desiredColumn = null)
            }), this.selectionAnchor.on("change", function() {
                t.$isEmpty || t._emit("changeSelection")
            })
        };
    (function() {
        r.implement(this, s), this.isEmpty = function() {
            return this.$isEmpty || this.anchor.row == this.lead.row && this.anchor.column == this.lead.column
        }, this.isMultiLine = function() {
            return this.isEmpty() ? !1 : this.getRange().isMultiLine()
        }, this.getCursor = function() {
            return this.lead.getPosition()
        }, this.setSelectionAnchor = function(e, t) {
            this.anchor.setPosition(e, t), this.$isEmpty && (this.$isEmpty = !1, this._emit("changeSelection"))
        }, this.getSelectionAnchor = function() {
            return this.$isEmpty ? this.getSelectionLead() : this.anchor.getPosition()
        }, this.getSelectionLead = function() {
            return this.lead.getPosition()
        }, this.shiftSelection = function(e) {
            if (this.$isEmpty) {
                this.moveCursorTo(this.lead.row, this.lead.column + e);
                return
            }
            var t = this.getSelectionAnchor(),
                n = this.getSelectionLead(),
                r = this.isBackwards();
            (!r || t.column !== 0) && this.setSelectionAnchor(t.row, t.column + e), (r || n.column !== 0) && this.$moveSelection(function() {
                this.moveCursorTo(n.row, n.column + e)
            })
        }, this.isBackwards = function() {
            var e = this.anchor,
                t = this.lead;
            return e.row > t.row || e.row == t.row && e.column > t.column
        }, this.getRange = function() {
            var e = this.anchor,
                t = this.lead;
            return this.isEmpty() ? o.fromPoints(t, t) : this.isBackwards() ? o.fromPoints(t, e) : o.fromPoints(e, t)
        }, this.clearSelection = function() {
            this.$isEmpty || (this.$isEmpty = !0, this._emit("changeSelection"))
        }, this.selectAll = function() {
            var e = this.doc.getLength() - 1;
            this.setSelectionAnchor(0, 0), this.moveCursorTo(e, this.doc.getLine(e).length)
        }, this.setRange = this.setSelectionRange = function(e, t) {
            t ? (this.setSelectionAnchor(e.end.row, e.end.column), this.selectTo(e.start.row, e.start.column)) : (this.setSelectionAnchor(e.start.row, e.start.column), this.selectTo(e.end.row, e.end.column)), this.getRange().isEmpty() && (this.$isEmpty = !0), this.$desiredColumn = null
        }, this.$moveSelection = function(e) {
            var t = this.lead;
            this.$isEmpty && this.setSelectionAnchor(t.row, t.column), e.call(this)
        }, this.selectTo = function(e, t) {
            this.$moveSelection(function() {
                this.moveCursorTo(e, t)
            })
        }, this.selectToPosition = function(e) {
            this.$moveSelection(function() {
                this.moveCursorToPosition(e)
            })
        }, this.moveTo = function(e, t) {
            this.clearSelection(), this.moveCursorTo(e, t)
        }, this.moveToPosition = function(e) {
            this.clearSelection(), this.moveCursorToPosition(e)
        }, this.selectUp = function() {
            this.$moveSelection(this.moveCursorUp)
        }, this.selectDown = function() {
            this.$moveSelection(this.moveCursorDown)
        }, this.selectRight = function() {
            this.$moveSelection(this.moveCursorRight)
        }, this.selectLeft = function() {
            this.$moveSelection(this.moveCursorLeft)
        }, this.selectLineStart = function() {
            this.$moveSelection(this.moveCursorLineStart)
        }, this.selectLineEnd = function() {
            this.$moveSelection(this.moveCursorLineEnd)
        }, this.selectFileEnd = function() {
            this.$moveSelection(this.moveCursorFileEnd)
        }, this.selectFileStart = function() {
            this.$moveSelection(this.moveCursorFileStart)
        }, this.selectWordRight = function() {
            this.$moveSelection(this.moveCursorWordRight)
        }, this.selectWordLeft = function() {
            this.$moveSelection(this.moveCursorWordLeft)
        }, this.getWordRange = function(e, t) {
            if (typeof t == "undefined") {
                var n = e || this.lead;
                e = n.row, t = n.column
            }
            return this.session.getWordRange(e, t)
        }, this.selectWord = function() {
            this.setSelectionRange(this.getWordRange())
        }, this.selectAWord = function() {
            var e = this.getCursor(),
                t = this.session.getAWordRange(e.row, e.column);
            this.setSelectionRange(t)
        }, this.getLineRange = function(e, t) {
            var n = typeof e == "number" ? e : this.lead.row,
                r, i = this.session.getFoldLine(n);
            return i ? (n = i.start.row, r = i.end.row) : r = n, t === !0 ? new o(n, 0, r, this.session.getLine(r).length) : new o(n, 0, r + 1, 0)
        }, this.selectLine = function() {
            this.setSelectionRange(this.getLineRange())
        }, this.moveCursorUp = function() {
            this.moveCursorBy(-1, 0)
        }, this.moveCursorDown = function() {
            this.moveCursorBy(1, 0)
        }, this.moveCursorLeft = function() {
            var e = this.lead.getPosition(),
                t;
            if (t = this.session.getFoldAt(e.row, e.column, -1)) this.moveCursorTo(t.start.row, t.start.column);
            else if (e.column === 0) e.row > 0 && this.moveCursorTo(e.row - 1, this.doc.getLine(e.row - 1).length);
            else {
                var n = this.session.getTabSize();
                this.session.isTabStop(e) && this.doc.getLine(e.row).slice(e.column - n, e.column).split(" ").length - 1 == n ? this.moveCursorBy(0, -n) : this.moveCursorBy(0, -1)
            }
        }, this.moveCursorRight = function() {
            var e = this.lead.getPosition(),
                t;
            if (t = this.session.getFoldAt(e.row, e.column, 1)) this.moveCursorTo(t.end.row, t.end.column);
            else if (this.lead.column == this.doc.getLine(this.lead.row).length) this.lead.row < this.doc.getLength() - 1 && this.moveCursorTo(this.lead.row + 1, 0);
            else {
                var n = this.session.getTabSize(),
                    e = this.lead;
                this.session.isTabStop(e) && this.doc.getLine(e.row).slice(e.column, e.column + n).split(" ").length - 1 == n ? this.moveCursorBy(0, n) : this.moveCursorBy(0, 1)
            }
        }, this.moveCursorLineStart = function() {
            var e = this.lead.row,
                t = this.lead.column,
                n = this.session.documentToScreenRow(e, t),
                r = this.session.screenToDocumentPosition(n, 0),
                i = this.session.getDisplayLine(e, null, r.row, r.column),
                s = i.match(/^\s*/);
            s[0].length != t && !this.session.$useEmacsStyleLineStart && (r.column += s[0].length), this.moveCursorToPosition(r)
        }, this.moveCursorLineEnd = function() {
            var e = this.lead,
                t = this.session.getDocumentLastRowColumnPosition(e.row, e.column);
            if (this.lead.column == t.column) {
                var n = this.session.getLine(t.row);
                if (t.column == n.length) {
                    var r = n.search(/\s+$/);
                    r > 0 && (t.column = r)
                }
            }
            this.moveCursorTo(t.row, t.column)
        }, this.moveCursorFileEnd = function() {
            var e = this.doc.getLength() - 1,
                t = this.doc.getLine(e).length;
            this.moveCursorTo(e, t)
        }, this.moveCursorFileStart = function() {
            this.moveCursorTo(0, 0)
        }, this.moveCursorLongWordRight = function() {
            var e = this.lead.row,
                t = this.lead.column,
                n = this.doc.getLine(e),
                r = n.substring(t),
                i;
            this.session.nonTokenRe.lastIndex = 0, this.session.tokenRe.lastIndex = 0;
            var s = this.session.getFoldAt(e, t, 1);
            if (s) {
                this.moveCursorTo(s.end.row, s.end.column);
                return
            }
            if (i = this.session.nonTokenRe.exec(r)) t += this.session.nonTokenRe.lastIndex, this.session.nonTokenRe.lastIndex = 0, r = n.substring(t);
            if (t >= n.length) {
                this.moveCursorTo(e, n.length), this.moveCursorRight(), e < this.doc.getLength() - 1 && this.moveCursorWordRight();
                return
            }
            if (i = this.session.tokenRe.exec(r)) t += this.session.tokenRe.lastIndex, this.session.tokenRe.lastIndex = 0;
            this.moveCursorTo(e, t)
        }, this.moveCursorLongWordLeft = function() {
            var e = this.lead.row,
                t = this.lead.column,
                n;
            if (n = this.session.getFoldAt(e, t, -1)) {
                this.moveCursorTo(n.start.row, n.start.column);
                return
            }
            var r = this.session.getFoldStringAt(e, t, -1);
            r == null && (r = this.doc.getLine(e).substring(0, t));
            var s = i.stringReverse(r),
                o;
            this.session.nonTokenRe.lastIndex = 0, this.session.tokenRe.lastIndex = 0;
            if (o = this.session.nonTokenRe.exec(s)) t -= this.session.nonTokenRe.lastIndex, s = s.slice(this.session.nonTokenRe.lastIndex), this.session.nonTokenRe.lastIndex = 0;
            if (t <= 0) {
                this.moveCursorTo(e, 0), this.moveCursorLeft(), e > 0 && this.moveCursorWordLeft();
                return
            }
            if (o = this.session.tokenRe.exec(s)) t -= this.session.tokenRe.lastIndex, this.session.tokenRe.lastIndex = 0;
            this.moveCursorTo(e, t)
        }, this.$shortWordEndIndex = function(e) {
            var t, n = 0,
                r, i = /\s/,
                s = this.session.tokenRe;
            s.lastIndex = 0;
            if (t = this.session.tokenRe.exec(e)) n = this.session.tokenRe.lastIndex;
            else {
                while ((r = e[n]) && i.test(r)) n++;
                if (n < 1) {
                    s.lastIndex = 0;
                    while ((r = e[n]) && !s.test(r)) {
                        s.lastIndex = 0, n++;
                        if (i.test(r)) {
                            if (n > 2) {
                                n--;
                                break
                            }
                            while ((r = e[n]) && i.test(r)) n++;
                            if (n > 2) break
                        }
                    }
                }
            }
            return s.lastIndex = 0, n
        }, this.moveCursorShortWordRight = function() {
            var e = this.lead.row,
                t = this.lead.column,
                n = this.doc.getLine(e),
                r = n.substring(t),
                i = this.session.getFoldAt(e, t, 1);
            if (i) return this.moveCursorTo(i.end.row, i.end.column);
            if (t == n.length) {
                var s = this.doc.getLength();
                do e++, r = this.doc.getLine(e); while (e < s && /^\s*$/.test(r));
                /^\s+/.test(r) || (r = ""), t = 0
            }
            var o = this.$shortWordEndIndex(r);
            this.moveCursorTo(e, t + o)
        }, this.moveCursorShortWordLeft = function() {
            var e = this.lead.row,
                t = this.lead.column,
                n;
            if (n = this.session.getFoldAt(e, t, -1)) return this.moveCursorTo(n.start.row, n.start.column);
            var r = this.session.getLine(e).substring(0, t);
            if (t === 0) {
                do e--, r = this.doc.getLine(e); while (e > 0 && /^\s*$/.test(r));
                t = r.length, /\s+$/.test(r) || (r = "")
            }
            var s = i.stringReverse(r),
                o = this.$shortWordEndIndex(s);
            return this.moveCursorTo(e, t - o)
        }, this.moveCursorWordRight = function() {
            this.session.$selectLongWords ? this.moveCursorLongWordRight() : this.moveCursorShortWordRight()
        }, this.moveCursorWordLeft = function() {
            this.session.$selectLongWords ? this.moveCursorLongWordLeft() : this.moveCursorShortWordLeft()
        }, this.moveCursorBy = function(e, t) {
            var n = this.session.documentToScreenPosition(this.lead.row, this.lead.column);
            t === 0 && (this.$desiredColumn ? n.column = this.$desiredColumn : this.$desiredColumn = n.column);
            var r = this.session.screenToDocumentPosition(n.row + e, n.column);
            e !== 0 && t === 0 && r.row === this.lead.row && r.column === this.lead.column && this.session.lineWidgets && this.session.lineWidgets[r.row] && r.row++, this.moveCursorTo(r.row, r.column + t, t === 0)
        }, this.moveCursorToPosition = function(e) {
            this.moveCursorTo(e.row, e.column)
        }, this.moveCursorTo = function(e, t, n) {
            var r = this.session.getFoldAt(e, t, 1);
            r && (e = r.start.row, t = r.start.column), this.$keepDesiredColumnOnChange = !0, this.lead.setPosition(e, t), this.$keepDesiredColumnOnChange = !1, n || (this.$desiredColumn = null)
        }, this.moveCursorToScreen = function(e, t, n) {
            var r = this.session.screenToDocumentPosition(e, t);
            this.moveCursorTo(r.row, r.column, n)
        }, this.detach = function() {
            this.lead.detach(), this.anchor.detach(), this.session = this.doc = null
        }, this.fromOrientedRange = function(e) {
            this.setSelectionRange(e, e.cursor == e.start), this.$desiredColumn = e.desiredColumn || this.$desiredColumn
        }, this.toOrientedRange = function(e) {
            var t = this.getRange();
            return e ? (e.start.column = t.start.column, e.start.row = t.start.row, e.end.column = t.end.column, e.end.row = t.end.row) : e = t, e.cursor = this.isBackwards() ? e.start : e.end, e.desiredColumn = this.$desiredColumn, e
        }, this.getRangeOfMovements = function(e) {
            var t = this.getCursor();
            try {
                e.call(null, this);
                var n = this.getCursor();
                return o.fromPoints(t, n)
            } catch (r) {
                return o.fromPoints(t, t)
            } finally {
                this.moveCursorToPosition(t)
            }
        }, this.toJSON = function() {
            if (this.rangeCount) var e = this.ranges.map(function(e) {
                var t = e.clone();
                return t.isBackwards = e.cursor == e.start, t
            });
            else {
                var e = this.getRange();
                e.isBackwards = this.isBackwards()
            }
            return e
        }, this.fromJSON = function(e) {
            if (e.start == undefined) {
                if (this.rangeList) {
                    this.toSingleRange(e[0]);
                    for (var t = e.length; t--;) {
                        var n = o.fromPoints(e[t].start, e[t].end);
                        e[t].isBackwards && (n.cursor = n.start), this.addRange(n, !0)
                    }
                    return
                }
                e = e[0]
            }
            this.rangeList && this.toSingleRange(e), this.setSelectionRange(e, e.isBackwards)
        }, this.isEqual = function(e) {
            if ((e.length || this.rangeCount) && e.length != this.rangeCount) return !1;
            if (!e.length || !this.ranges) return this.getRange().isEqual(e);
            for (var t = this.ranges.length; t--;)
                if (!this.ranges[t].isEqual(e[t])) return !1;
            return !0
        }
    }).call(u.prototype), t.Selection = u
}), define("ace/tokenizer", ["require", "exports", "module", "ace/config"], function(e, t, n) {
    "use strict";
    var r = e("./config"),
        i = 2e3,
        s = function(e) {
            this.states = e, this.regExps = {}, this.matchMappings = {};
            for (var t in this.states) {
                var n = this.states[t],
                    r = [],
                    i = 0,
                    s = this.matchMappings[t] = {
                        defaultToken: "text"
                    },
                    o = "g",
                    u = [];
                for (var a = 0; a < n.length; a++) {
                    var f = n[a];
                    f.defaultToken && (s.defaultToken = f.defaultToken), f.caseInsensitive && (o = "gi");
                    if (f.regex == null) continue;
                    f.regex instanceof RegExp && (f.regex = f.regex.toString().slice(1, -1));
                    var l = f.regex,
                        c = (new RegExp("(?:(" + l + ")|(.))")).exec("a").length - 2;
                    Array.isArray(f.token) ? f.token.length == 1 || c == 1 ? f.token = f.token[0] : c - 1 != f.token.length ? (this.reportError("number of classes and regexp groups doesn't match", {
                        rule: f,
                        groupCount: c - 1
                    }), f.token = f.token[0]) : (f.tokenArray = f.token, f.token = null, f.onMatch = this.$arrayTokens) : typeof f.token == "function" && !f.onMatch && (c > 1 ? f.onMatch = this.$applyToken : f.onMatch = f.token), c > 1 && (/\\\d/.test(f.regex) ? l = f.regex.replace(/\\([0-9]+)/g, function(e, t) {
                        return "\\" + (parseInt(t, 10) + i + 1)
                    }) : (c = 1, l = this.removeCapturingGroups(f.regex)), !f.splitRegex && typeof f.token != "string" && u.push(f)), s[i] = a, i += c, r.push(l), f.onMatch || (f.onMatch = null)
                }
                r.length || (s[0] = 0, r.push("$")), u.forEach(function(e) {
                    e.splitRegex = this.createSplitterRegexp(e.regex, o)
                }, this), this.regExps[t] = new RegExp("(" + r.join(")|(") + ")|($)", o)
            }
        };
    (function() {
        this.$setMaxTokenCount = function(e) {
            i = e | 0
        }, this.$applyToken = function(e) {
            var t = this.splitRegex.exec(e).slice(1),
                n = this.token.apply(this, t);
            if (typeof n == "string") return [{
                type: n,
                value: e
            }];
            var r = [];
            for (var i = 0, s = n.length; i < s; i++) t[i] && (r[r.length] = {
                type: n[i],
                value: t[i]
            });
            return r
        }, this.$arrayTokens = function(e) {
            if (!e) return [];
            var t = this.splitRegex.exec(e);
            if (!t) return "text";
            var n = [],
                r = this.tokenArray;
            for (var i = 0, s = r.length; i < s; i++) t[i + 1] && (n[n.length] = {
                type: r[i],
                value: t[i + 1]
            });
            return n
        }, this.removeCapturingGroups = function(e) {
            var t = e.replace(/\[(?:\\.|[^\]])*?\]|\\.|\(\?[:=!]|(\()/g, function(e, t) {
                return t ? "(?:" : e
            });
            return t
        }, this.createSplitterRegexp = function(e, t) {
            if (e.indexOf("(?=") != -1) {
                var n = 0,
                    r = !1,
                    i = {};
                e.replace(/(\\.)|(\((?:\?[=!])?)|(\))|([\[\]])/g, function(e, t, s, o, u, a) {
                    return r ? r = u != "]" : u ? r = !0 : o ? (n == i.stack && (i.end = a + 1, i.stack = -1), n--) : s && (n++, s.length != 1 && (i.stack = n, i.start = a)), e
                }), i.end != null && /^\)*$/.test(e.substr(i.end)) && (e = e.substring(0, i.start) + e.substr(i.end))
            }
            return new RegExp(e, (t || "").replace("g", ""))
        }, this.getLineTokens = function(e, t) {
            if (t && typeof t != "string") {
                var n = t.slice(0);
                t = n[0], t === "#tmp" && (n.shift(), t = n.shift())
            } else var n = [];
            var r = t || "start",
                s = this.states[r];
            s || (r = "start", s = this.states[r]);
            var o = this.matchMappings[r],
                u = this.regExps[r];
            u.lastIndex = 0;
            var a, f = [],
                l = 0,
                c = 0,
                h = {
                    type: null,
                    value: ""
                };
            while (a = u.exec(e)) {
                var p = o.defaultToken,
                    d = null,
                    v = a[0],
                    m = u.lastIndex;
                if (m - v.length > l) {
                    var g = e.substring(l, m - v.length);
                    h.type == p ? h.value += g : (h.type && f.push(h), h = {
                        type: p,
                        value: g
                    })
                }
                for (var y = 0; y < a.length - 2; y++) {
                    if (a[y + 1] === undefined) continue;
                    d = s[o[y]], d.onMatch ? p = d.onMatch(v, r, n) : p = d.token, d.next && (typeof d.next == "string" ? r = d.next : r = d.next(r, n), s = this.states[r], s || (this.reportError("state doesn't exist", r), r = "start", s = this.states[r]), o = this.matchMappings[r], l = m, u = this.regExps[r], u.lastIndex = m);
                    break
                }
                if (v)
                    if (typeof p == "string") !!d && d.merge === !1 || h.type !== p ? (h.type && f.push(h), h = {
                        type: p,
                        value: v
                    }) : h.value += v;
                    else if (p) {
                    h.type && f.push(h), h = {
                        type: null,
                        value: ""
                    };
                    for (var y = 0; y < p.length; y++) f.push(p[y])
                }
                if (l == e.length) break;
                l = m;
                if (c++ > i) {
                    c > 2 * e.length && this.reportError("infinite loop with in ace tokenizer", {
                        startState: t,
                        line: e
                    });
                    while (l < e.length) h.type && f.push(h), h = {
                        value: e.substring(l, l += 2e3),
                        type: "overflow"
                    };
                    r = "start", n = [];
                    break
                }
            }
            return h.type && f.push(h), n.length > 1 && n[0] !== r && n.unshift("#tmp", r), {
                tokens: f,
                state: n.length ? n : r
            }
        }, this.reportError = r.reportError
    }).call(s.prototype), t.Tokenizer = s
}), define("ace/mode/text_highlight_rules", ["require", "exports", "module", "ace/lib/lang"], function(e, t, n) {
    "use strict";
    var r = e("../lib/lang"),
        i = function() {
            this.$rules = {
                start: [{
                    token: "empty_line",
                    regex: "^$"
                }, {
                    defaultToken: "text"
                }]
            }
        };
    (function() {
        this.addRules = function(e, t) {
            if (!t) {
                for (var n in e) this.$rules[n] = e[n];
                return
            }
            for (var n in e) {
                var r = e[n];
                for (var i = 0; i < r.length; i++) {
                    var s = r[i];
                    if (s.next || s.onMatch) typeof s.next != "string" ? s.nextState && s.nextState.indexOf(t) !== 0 && (s.nextState = t + s.nextState) : s.next.indexOf(t) !== 0 && (s.next = t + s.next)
                }
                this.$rules[t + n] = r
            }
        }, this.getRules = function() {
            return this.$rules
        }, this.embedRules = function(e, t, n, i, s) {
            var o = typeof e == "function" ? (new e).getRules() : e;
            if (i)
                for (var u = 0; u < i.length; u++) i[u] = t + i[u];
            else {
                i = [];
                for (var a in o) i.push(t + a)
            }
            this.addRules(o, t);
            if (n) {
                var f = Array.prototype[s ? "push" : "unshift"];
                for (var u = 0; u < i.length; u++) f.apply(this.$rules[i[u]], r.deepCopy(n))
            }
            this.$embeds || (this.$embeds = []), this.$embeds.push(t)
        }, this.getEmbeds = function() {
            return this.$embeds
        };
        var e = function(e, t) {
                return (e != "start" || t.length) && t.unshift(this.nextState, e), this.nextState
            },
            t = function(e, t) {
                return t.shift(), t.shift() || "start"
            };
        this.normalizeRules = function() {
            function i(s) {
                var o = r[s];
                o.processed = !0;
                for (var u = 0; u < o.length; u++) {
                    var a = o[u];
                    !a.regex && a.start && (a.regex = a.start, a.next || (a.next = []), a.next.push({
                        defaultToken: a.token
                    }, {
                        token: a.token + ".end",
                        regex: a.end || a.start,
                        next: "pop"
                    }), a.token = a.token + ".start", a.push = !0);
                    var f = a.next || a.push;
                    if (f && Array.isArray(f)) {
                        var l = a.stateName;
                        l || (l = a.token, typeof l != "string" && (l = l[0] || ""), r[l] && (l += n++)), r[l] = f, a.next = l, i(l)
                    } else f == "pop" && (a.next = t);
                    a.push && (a.nextState = a.next || a.push, a.next = e, delete a.push);
                    if (a.rules)
                        for (var c in a.rules) r[c] ? r[c].push && r[c].push.apply(r[c], a.rules[c]) : r[c] = a.rules[c];
                    if (a.include || typeof a == "string") var h = a.include || a,
                        p = r[h];
                    else Array.isArray(a) && (p = a);
                    if (p) {
                        var d = [u, 1].concat(p);
                        a.noEscape && (d = d.filter(function(e) {
                            return !e.next
                        })), o.splice.apply(o, d), u--, p = null
                    }
                    a.keywordMap && (a.token = this.createKeywordMapper(a.keywordMap, a.defaultToken || "text", a.caseInsensitive), delete a.defaultToken)
                }
            }
            var n = 0,
                r = this.$rules;
            Object.keys(r).forEach(i, this)
        }, this.createKeywordMapper = function(e, t, n, r) {
            var i = Object.create(null);
            return Object.keys(e).forEach(function(t) {
                var s = e[t];
                n && (s = s.toLowerCase());
                var o = s.split(r || "|");
                for (var u = o.length; u--;) i[o[u]] = t
            }), Object.getPrototypeOf(i) && (i.__proto__ = null), this.$keywordList = Object.keys(i), e = null, n ? function(e) {
                return i[e.toLowerCase()] || t
            } : function(e) {
                return i[e] || t
            }
        }, this.getKeywords = function() {
            return this.$keywords
        }
    }).call(i.prototype), t.TextHighlightRules = i
}), define("ace/mode/behaviour", ["require", "exports", "module"], function(e, t, n) {
    "use strict";
    var r = function() {
        this.$behaviours = {}
    };
    (function() {
        this.add = function(e, t, n) {
            switch (undefined) {
                case this.$behaviours:
                    this.$behaviours = {};
                case this.$behaviours[e]:
                    this.$behaviours[e] = {}
            }
            this.$behaviours[e][t] = n
        }, this.addBehaviours = function(e) {
            for (var t in e)
                for (var n in e[t]) this.add(t, n, e[t][n])
        }, this.remove = function(e) {
            this.$behaviours && this.$behaviours[e] && delete this.$behaviours[e]
        }, this.inherit = function(e, t) {
            if (typeof e == "function") var n = (new e).getBehaviours(t);
            else var n = e.getBehaviours(t);
            this.addBehaviours(n)
        }, this.getBehaviours = function(e) {
            if (!e) return this.$behaviours;
            var t = {};
            for (var n = 0; n < e.length; n++) this.$behaviours[e[n]] && (t[e[n]] = this.$behaviours[e[n]]);
            return t
        }
    }).call(r.prototype), t.Behaviour = r
}), define("ace/unicode", ["require", "exports", "module"], function(e, t, n) {
    "use strict";

    function r(e) {
        var n = /\w{4}/g;
        for (var r in e) t.packages[r] = e[r].replace(n, "\\u$&")
    }
    t.packages = {}, r({
        L: "0041-005A0061-007A00AA00B500BA00C0-00D600D8-00F600F8-02C102C6-02D102E0-02E402EC02EE0370-037403760377037A-037D03860388-038A038C038E-03A103A3-03F503F7-0481048A-05250531-055605590561-058705D0-05EA05F0-05F20621-064A066E066F0671-06D306D506E506E606EE06EF06FA-06FC06FF07100712-072F074D-07A507B107CA-07EA07F407F507FA0800-0815081A082408280904-0939093D09500958-0961097109720979-097F0985-098C098F09900993-09A809AA-09B009B209B6-09B909BD09CE09DC09DD09DF-09E109F009F10A05-0A0A0A0F0A100A13-0A280A2A-0A300A320A330A350A360A380A390A59-0A5C0A5E0A72-0A740A85-0A8D0A8F-0A910A93-0AA80AAA-0AB00AB20AB30AB5-0AB90ABD0AD00AE00AE10B05-0B0C0B0F0B100B13-0B280B2A-0B300B320B330B35-0B390B3D0B5C0B5D0B5F-0B610B710B830B85-0B8A0B8E-0B900B92-0B950B990B9A0B9C0B9E0B9F0BA30BA40BA8-0BAA0BAE-0BB90BD00C05-0C0C0C0E-0C100C12-0C280C2A-0C330C35-0C390C3D0C580C590C600C610C85-0C8C0C8E-0C900C92-0CA80CAA-0CB30CB5-0CB90CBD0CDE0CE00CE10D05-0D0C0D0E-0D100D12-0D280D2A-0D390D3D0D600D610D7A-0D7F0D85-0D960D9A-0DB10DB3-0DBB0DBD0DC0-0DC60E01-0E300E320E330E40-0E460E810E820E840E870E880E8A0E8D0E94-0E970E99-0E9F0EA1-0EA30EA50EA70EAA0EAB0EAD-0EB00EB20EB30EBD0EC0-0EC40EC60EDC0EDD0F000F40-0F470F49-0F6C0F88-0F8B1000-102A103F1050-1055105A-105D106110651066106E-10701075-1081108E10A0-10C510D0-10FA10FC1100-1248124A-124D1250-12561258125A-125D1260-1288128A-128D1290-12B012B2-12B512B8-12BE12C012C2-12C512C8-12D612D8-13101312-13151318-135A1380-138F13A0-13F41401-166C166F-167F1681-169A16A0-16EA1700-170C170E-17111720-17311740-17511760-176C176E-17701780-17B317D717DC1820-18771880-18A818AA18B0-18F51900-191C1950-196D1970-19741980-19AB19C1-19C71A00-1A161A20-1A541AA71B05-1B331B45-1B4B1B83-1BA01BAE1BAF1C00-1C231C4D-1C4F1C5A-1C7D1CE9-1CEC1CEE-1CF11D00-1DBF1E00-1F151F18-1F1D1F20-1F451F48-1F4D1F50-1F571F591F5B1F5D1F5F-1F7D1F80-1FB41FB6-1FBC1FBE1FC2-1FC41FC6-1FCC1FD0-1FD31FD6-1FDB1FE0-1FEC1FF2-1FF41FF6-1FFC2071207F2090-209421022107210A-211321152119-211D212421262128212A-212D212F-2139213C-213F2145-2149214E218321842C00-2C2E2C30-2C5E2C60-2CE42CEB-2CEE2D00-2D252D30-2D652D6F2D80-2D962DA0-2DA62DA8-2DAE2DB0-2DB62DB8-2DBE2DC0-2DC62DC8-2DCE2DD0-2DD62DD8-2DDE2E2F300530063031-3035303B303C3041-3096309D-309F30A1-30FA30FC-30FF3105-312D3131-318E31A0-31B731F0-31FF3400-4DB54E00-9FCBA000-A48CA4D0-A4FDA500-A60CA610-A61FA62AA62BA640-A65FA662-A66EA67F-A697A6A0-A6E5A717-A71FA722-A788A78BA78CA7FB-A801A803-A805A807-A80AA80C-A822A840-A873A882-A8B3A8F2-A8F7A8FBA90A-A925A930-A946A960-A97CA984-A9B2A9CFAA00-AA28AA40-AA42AA44-AA4BAA60-AA76AA7AAA80-AAAFAAB1AAB5AAB6AAB9-AABDAAC0AAC2AADB-AADDABC0-ABE2AC00-D7A3D7B0-D7C6D7CB-D7FBF900-FA2DFA30-FA6DFA70-FAD9FB00-FB06FB13-FB17FB1DFB1F-FB28FB2A-FB36FB38-FB3CFB3EFB40FB41FB43FB44FB46-FBB1FBD3-FD3DFD50-FD8FFD92-FDC7FDF0-FDFBFE70-FE74FE76-FEFCFF21-FF3AFF41-FF5AFF66-FFBEFFC2-FFC7FFCA-FFCFFFD2-FFD7FFDA-FFDC",
        Ll: "0061-007A00AA00B500BA00DF-00F600F8-00FF01010103010501070109010B010D010F01110113011501170119011B011D011F01210123012501270129012B012D012F01310133013501370138013A013C013E014001420144014601480149014B014D014F01510153015501570159015B015D015F01610163016501670169016B016D016F0171017301750177017A017C017E-0180018301850188018C018D019201950199-019B019E01A101A301A501A801AA01AB01AD01B001B401B601B901BA01BD-01BF01C601C901CC01CE01D001D201D401D601D801DA01DC01DD01DF01E101E301E501E701E901EB01ED01EF01F001F301F501F901FB01FD01FF02010203020502070209020B020D020F02110213021502170219021B021D021F02210223022502270229022B022D022F02310233-0239023C023F0240024202470249024B024D024F-02930295-02AF037103730377037B-037D039003AC-03CE03D003D103D5-03D703D903DB03DD03DF03E103E303E503E703E903EB03ED03EF-03F303F503F803FB03FC0430-045F04610463046504670469046B046D046F04710473047504770479047B047D047F0481048B048D048F04910493049504970499049B049D049F04A104A304A504A704A904AB04AD04AF04B104B304B504B704B904BB04BD04BF04C204C404C604C804CA04CC04CE04CF04D104D304D504D704D904DB04DD04DF04E104E304E504E704E904EB04ED04EF04F104F304F504F704F904FB04FD04FF05010503050505070509050B050D050F05110513051505170519051B051D051F0521052305250561-05871D00-1D2B1D62-1D771D79-1D9A1E011E031E051E071E091E0B1E0D1E0F1E111E131E151E171E191E1B1E1D1E1F1E211E231E251E271E291E2B1E2D1E2F1E311E331E351E371E391E3B1E3D1E3F1E411E431E451E471E491E4B1E4D1E4F1E511E531E551E571E591E5B1E5D1E5F1E611E631E651E671E691E6B1E6D1E6F1E711E731E751E771E791E7B1E7D1E7F1E811E831E851E871E891E8B1E8D1E8F1E911E931E95-1E9D1E9F1EA11EA31EA51EA71EA91EAB1EAD1EAF1EB11EB31EB51EB71EB91EBB1EBD1EBF1EC11EC31EC51EC71EC91ECB1ECD1ECF1ED11ED31ED51ED71ED91EDB1EDD1EDF1EE11EE31EE51EE71EE91EEB1EED1EEF1EF11EF31EF51EF71EF91EFB1EFD1EFF-1F071F10-1F151F20-1F271F30-1F371F40-1F451F50-1F571F60-1F671F70-1F7D1F80-1F871F90-1F971FA0-1FA71FB0-1FB41FB61FB71FBE1FC2-1FC41FC61FC71FD0-1FD31FD61FD71FE0-1FE71FF2-1FF41FF61FF7210A210E210F2113212F21342139213C213D2146-2149214E21842C30-2C5E2C612C652C662C682C6A2C6C2C712C732C742C76-2C7C2C812C832C852C872C892C8B2C8D2C8F2C912C932C952C972C992C9B2C9D2C9F2CA12CA32CA52CA72CA92CAB2CAD2CAF2CB12CB32CB52CB72CB92CBB2CBD2CBF2CC12CC32CC52CC72CC92CCB2CCD2CCF2CD12CD32CD52CD72CD92CDB2CDD2CDF2CE12CE32CE42CEC2CEE2D00-2D25A641A643A645A647A649A64BA64DA64FA651A653A655A657A659A65BA65DA65FA663A665A667A669A66BA66DA681A683A685A687A689A68BA68DA68FA691A693A695A697A723A725A727A729A72BA72DA72F-A731A733A735A737A739A73BA73DA73FA741A743A745A747A749A74BA74DA74FA751A753A755A757A759A75BA75DA75FA761A763A765A767A769A76BA76DA76FA771-A778A77AA77CA77FA781A783A785A787A78CFB00-FB06FB13-FB17FF41-FF5A",
        Lu: "0041-005A00C0-00D600D8-00DE01000102010401060108010A010C010E01100112011401160118011A011C011E01200122012401260128012A012C012E01300132013401360139013B013D013F0141014301450147014A014C014E01500152015401560158015A015C015E01600162016401660168016A016C016E017001720174017601780179017B017D018101820184018601870189-018B018E-0191019301940196-0198019C019D019F01A001A201A401A601A701A901AC01AE01AF01B1-01B301B501B701B801BC01C401C701CA01CD01CF01D101D301D501D701D901DB01DE01E001E201E401E601E801EA01EC01EE01F101F401F6-01F801FA01FC01FE02000202020402060208020A020C020E02100212021402160218021A021C021E02200222022402260228022A022C022E02300232023A023B023D023E02410243-02460248024A024C024E03700372037603860388-038A038C038E038F0391-03A103A3-03AB03CF03D2-03D403D803DA03DC03DE03E003E203E403E603E803EA03EC03EE03F403F703F903FA03FD-042F04600462046404660468046A046C046E04700472047404760478047A047C047E0480048A048C048E04900492049404960498049A049C049E04A004A204A404A604A804AA04AC04AE04B004B204B404B604B804BA04BC04BE04C004C104C304C504C704C904CB04CD04D004D204D404D604D804DA04DC04DE04E004E204E404E604E804EA04EC04EE04F004F204F404F604F804FA04FC04FE05000502050405060508050A050C050E05100512051405160518051A051C051E0520052205240531-055610A0-10C51E001E021E041E061E081E0A1E0C1E0E1E101E121E141E161E181E1A1E1C1E1E1E201E221E241E261E281E2A1E2C1E2E1E301E321E341E361E381E3A1E3C1E3E1E401E421E441E461E481E4A1E4C1E4E1E501E521E541E561E581E5A1E5C1E5E1E601E621E641E661E681E6A1E6C1E6E1E701E721E741E761E781E7A1E7C1E7E1E801E821E841E861E881E8A1E8C1E8E1E901E921E941E9E1EA01EA21EA41EA61EA81EAA1EAC1EAE1EB01EB21EB41EB61EB81EBA1EBC1EBE1EC01EC21EC41EC61EC81ECA1ECC1ECE1ED01ED21ED41ED61ED81EDA1EDC1EDE1EE01EE21EE41EE61EE81EEA1EEC1EEE1EF01EF21EF41EF61EF81EFA1EFC1EFE1F08-1F0F1F18-1F1D1F28-1F2F1F38-1F3F1F48-1F4D1F591F5B1F5D1F5F1F68-1F6F1FB8-1FBB1FC8-1FCB1FD8-1FDB1FE8-1FEC1FF8-1FFB21022107210B-210D2110-211221152119-211D212421262128212A-212D2130-2133213E213F214521832C00-2C2E2C602C62-2C642C672C692C6B2C6D-2C702C722C752C7E-2C802C822C842C862C882C8A2C8C2C8E2C902C922C942C962C982C9A2C9C2C9E2CA02CA22CA42CA62CA82CAA2CAC2CAE2CB02CB22CB42CB62CB82CBA2CBC2CBE2CC02CC22CC42CC62CC82CCA2CCC2CCE2CD02CD22CD42CD62CD82CDA2CDC2CDE2CE02CE22CEB2CEDA640A642A644A646A648A64AA64CA64EA650A652A654A656A658A65AA65CA65EA662A664A666A668A66AA66CA680A682A684A686A688A68AA68CA68EA690A692A694A696A722A724A726A728A72AA72CA72EA732A734A736A738A73AA73CA73EA740A742A744A746A748A74AA74CA74EA750A752A754A756A758A75AA75CA75EA760A762A764A766A768A76AA76CA76EA779A77BA77DA77EA780A782A784A786A78BFF21-FF3A",
        Lt: "01C501C801CB01F21F88-1F8F1F98-1F9F1FA8-1FAF1FBC1FCC1FFC",
        Lm: "02B0-02C102C6-02D102E0-02E402EC02EE0374037A0559064006E506E607F407F507FA081A0824082809710E460EC610FC17D718431AA71C78-1C7D1D2C-1D611D781D9B-1DBF2071207F2090-20942C7D2D6F2E2F30053031-3035303B309D309E30FC-30FEA015A4F8-A4FDA60CA67FA717-A71FA770A788A9CFAA70AADDFF70FF9EFF9F",
        Lo: "01BB01C0-01C3029405D0-05EA05F0-05F20621-063F0641-064A066E066F0671-06D306D506EE06EF06FA-06FC06FF07100712-072F074D-07A507B107CA-07EA0800-08150904-0939093D09500958-096109720979-097F0985-098C098F09900993-09A809AA-09B009B209B6-09B909BD09CE09DC09DD09DF-09E109F009F10A05-0A0A0A0F0A100A13-0A280A2A-0A300A320A330A350A360A380A390A59-0A5C0A5E0A72-0A740A85-0A8D0A8F-0A910A93-0AA80AAA-0AB00AB20AB30AB5-0AB90ABD0AD00AE00AE10B05-0B0C0B0F0B100B13-0B280B2A-0B300B320B330B35-0B390B3D0B5C0B5D0B5F-0B610B710B830B85-0B8A0B8E-0B900B92-0B950B990B9A0B9C0B9E0B9F0BA30BA40BA8-0BAA0BAE-0BB90BD00C05-0C0C0C0E-0C100C12-0C280C2A-0C330C35-0C390C3D0C580C590C600C610C85-0C8C0C8E-0C900C92-0CA80CAA-0CB30CB5-0CB90CBD0CDE0CE00CE10D05-0D0C0D0E-0D100D12-0D280D2A-0D390D3D0D600D610D7A-0D7F0D85-0D960D9A-0DB10DB3-0DBB0DBD0DC0-0DC60E01-0E300E320E330E40-0E450E810E820E840E870E880E8A0E8D0E94-0E970E99-0E9F0EA1-0EA30EA50EA70EAA0EAB0EAD-0EB00EB20EB30EBD0EC0-0EC40EDC0EDD0F000F40-0F470F49-0F6C0F88-0F8B1000-102A103F1050-1055105A-105D106110651066106E-10701075-1081108E10D0-10FA1100-1248124A-124D1250-12561258125A-125D1260-1288128A-128D1290-12B012B2-12B512B8-12BE12C012C2-12C512C8-12D612D8-13101312-13151318-135A1380-138F13A0-13F41401-166C166F-167F1681-169A16A0-16EA1700-170C170E-17111720-17311740-17511760-176C176E-17701780-17B317DC1820-18421844-18771880-18A818AA18B0-18F51900-191C1950-196D1970-19741980-19AB19C1-19C71A00-1A161A20-1A541B05-1B331B45-1B4B1B83-1BA01BAE1BAF1C00-1C231C4D-1C4F1C5A-1C771CE9-1CEC1CEE-1CF12135-21382D30-2D652D80-2D962DA0-2DA62DA8-2DAE2DB0-2DB62DB8-2DBE2DC0-2DC62DC8-2DCE2DD0-2DD62DD8-2DDE3006303C3041-3096309F30A1-30FA30FF3105-312D3131-318E31A0-31B731F0-31FF3400-4DB54E00-9FCBA000-A014A016-A48CA4D0-A4F7A500-A60BA610-A61FA62AA62BA66EA6A0-A6E5A7FB-A801A803-A805A807-A80AA80C-A822A840-A873A882-A8B3A8F2-A8F7A8FBA90A-A925A930-A946A960-A97CA984-A9B2AA00-AA28AA40-AA42AA44-AA4BAA60-AA6FAA71-AA76AA7AAA80-AAAFAAB1AAB5AAB6AAB9-AABDAAC0AAC2AADBAADCABC0-ABE2AC00-D7A3D7B0-D7C6D7CB-D7FBF900-FA2DFA30-FA6DFA70-FAD9FB1DFB1F-FB28FB2A-FB36FB38-FB3CFB3EFB40FB41FB43FB44FB46-FBB1FBD3-FD3DFD50-FD8FFD92-FDC7FDF0-FDFBFE70-FE74FE76-FEFCFF66-FF6FFF71-FF9DFFA0-FFBEFFC2-FFC7FFCA-FFCFFFD2-FFD7FFDA-FFDC",
        M: "0300-036F0483-04890591-05BD05BF05C105C205C405C505C70610-061A064B-065E067006D6-06DC06DE-06E406E706E806EA-06ED07110730-074A07A6-07B007EB-07F30816-0819081B-08230825-08270829-082D0900-0903093C093E-094E0951-0955096209630981-098309BC09BE-09C409C709C809CB-09CD09D709E209E30A01-0A030A3C0A3E-0A420A470A480A4B-0A4D0A510A700A710A750A81-0A830ABC0ABE-0AC50AC7-0AC90ACB-0ACD0AE20AE30B01-0B030B3C0B3E-0B440B470B480B4B-0B4D0B560B570B620B630B820BBE-0BC20BC6-0BC80BCA-0BCD0BD70C01-0C030C3E-0C440C46-0C480C4A-0C4D0C550C560C620C630C820C830CBC0CBE-0CC40CC6-0CC80CCA-0CCD0CD50CD60CE20CE30D020D030D3E-0D440D46-0D480D4A-0D4D0D570D620D630D820D830DCA0DCF-0DD40DD60DD8-0DDF0DF20DF30E310E34-0E3A0E47-0E4E0EB10EB4-0EB90EBB0EBC0EC8-0ECD0F180F190F350F370F390F3E0F3F0F71-0F840F860F870F90-0F970F99-0FBC0FC6102B-103E1056-1059105E-10601062-10641067-106D1071-10741082-108D108F109A-109D135F1712-17141732-1734175217531772177317B6-17D317DD180B-180D18A91920-192B1930-193B19B0-19C019C819C91A17-1A1B1A55-1A5E1A60-1A7C1A7F1B00-1B041B34-1B441B6B-1B731B80-1B821BA1-1BAA1C24-1C371CD0-1CD21CD4-1CE81CED1CF21DC0-1DE61DFD-1DFF20D0-20F02CEF-2CF12DE0-2DFF302A-302F3099309AA66F-A672A67CA67DA6F0A6F1A802A806A80BA823-A827A880A881A8B4-A8C4A8E0-A8F1A926-A92DA947-A953A980-A983A9B3-A9C0AA29-AA36AA43AA4CAA4DAA7BAAB0AAB2-AAB4AAB7AAB8AABEAABFAAC1ABE3-ABEAABECABEDFB1EFE00-FE0FFE20-FE26",
        Mn: "0300-036F0483-04870591-05BD05BF05C105C205C405C505C70610-061A064B-065E067006D6-06DC06DF-06E406E706E806EA-06ED07110730-074A07A6-07B007EB-07F30816-0819081B-08230825-08270829-082D0900-0902093C0941-0948094D0951-095509620963098109BC09C1-09C409CD09E209E30A010A020A3C0A410A420A470A480A4B-0A4D0A510A700A710A750A810A820ABC0AC1-0AC50AC70AC80ACD0AE20AE30B010B3C0B3F0B41-0B440B4D0B560B620B630B820BC00BCD0C3E-0C400C46-0C480C4A-0C4D0C550C560C620C630CBC0CBF0CC60CCC0CCD0CE20CE30D41-0D440D4D0D620D630DCA0DD2-0DD40DD60E310E34-0E3A0E47-0E4E0EB10EB4-0EB90EBB0EBC0EC8-0ECD0F180F190F350F370F390F71-0F7E0F80-0F840F860F870F90-0F970F99-0FBC0FC6102D-10301032-10371039103A103D103E10581059105E-10601071-1074108210851086108D109D135F1712-17141732-1734175217531772177317B7-17BD17C617C9-17D317DD180B-180D18A91920-19221927192819321939-193B1A171A181A561A58-1A5E1A601A621A65-1A6C1A73-1A7C1A7F1B00-1B031B341B36-1B3A1B3C1B421B6B-1B731B801B811BA2-1BA51BA81BA91C2C-1C331C361C371CD0-1CD21CD4-1CE01CE2-1CE81CED1DC0-1DE61DFD-1DFF20D0-20DC20E120E5-20F02CEF-2CF12DE0-2DFF302A-302F3099309AA66FA67CA67DA6F0A6F1A802A806A80BA825A826A8C4A8E0-A8F1A926-A92DA947-A951A980-A982A9B3A9B6-A9B9A9BCAA29-AA2EAA31AA32AA35AA36AA43AA4CAAB0AAB2-AAB4AAB7AAB8AABEAABFAAC1ABE5ABE8ABEDFB1EFE00-FE0FFE20-FE26",
        Mc: "0903093E-09400949-094C094E0982098309BE-09C009C709C809CB09CC09D70A030A3E-0A400A830ABE-0AC00AC90ACB0ACC0B020B030B3E0B400B470B480B4B0B4C0B570BBE0BBF0BC10BC20BC6-0BC80BCA-0BCC0BD70C01-0C030C41-0C440C820C830CBE0CC0-0CC40CC70CC80CCA0CCB0CD50CD60D020D030D3E-0D400D46-0D480D4A-0D4C0D570D820D830DCF-0DD10DD8-0DDF0DF20DF30F3E0F3F0F7F102B102C10311038103B103C105610571062-10641067-106D108310841087-108C108F109A-109C17B617BE-17C517C717C81923-19261929-192B193019311933-193819B0-19C019C819C91A19-1A1B1A551A571A611A631A641A6D-1A721B041B351B3B1B3D-1B411B431B441B821BA11BA61BA71BAA1C24-1C2B1C341C351CE11CF2A823A824A827A880A881A8B4-A8C3A952A953A983A9B4A9B5A9BAA9BBA9BD-A9C0AA2FAA30AA33AA34AA4DAA7BABE3ABE4ABE6ABE7ABE9ABEAABEC",
        Me: "0488048906DE20DD-20E020E2-20E4A670-A672",
        N: "0030-003900B200B300B900BC-00BE0660-066906F0-06F907C0-07C90966-096F09E6-09EF09F4-09F90A66-0A6F0AE6-0AEF0B66-0B6F0BE6-0BF20C66-0C6F0C78-0C7E0CE6-0CEF0D66-0D750E50-0E590ED0-0ED90F20-0F331040-10491090-10991369-137C16EE-16F017E0-17E917F0-17F91810-18191946-194F19D0-19DA1A80-1A891A90-1A991B50-1B591BB0-1BB91C40-1C491C50-1C5920702074-20792080-20892150-21822185-21892460-249B24EA-24FF2776-27932CFD30073021-30293038-303A3192-31953220-32293251-325F3280-328932B1-32BFA620-A629A6E6-A6EFA830-A835A8D0-A8D9A900-A909A9D0-A9D9AA50-AA59ABF0-ABF9FF10-FF19",
        Nd: "0030-00390660-066906F0-06F907C0-07C90966-096F09E6-09EF0A66-0A6F0AE6-0AEF0B66-0B6F0BE6-0BEF0C66-0C6F0CE6-0CEF0D66-0D6F0E50-0E590ED0-0ED90F20-0F291040-10491090-109917E0-17E91810-18191946-194F19D0-19DA1A80-1A891A90-1A991B50-1B591BB0-1BB91C40-1C491C50-1C59A620-A629A8D0-A8D9A900-A909A9D0-A9D9AA50-AA59ABF0-ABF9FF10-FF19",
        Nl: "16EE-16F02160-21822185-218830073021-30293038-303AA6E6-A6EF",
        No: "00B200B300B900BC-00BE09F4-09F90BF0-0BF20C78-0C7E0D70-0D750F2A-0F331369-137C17F0-17F920702074-20792080-20892150-215F21892460-249B24EA-24FF2776-27932CFD3192-31953220-32293251-325F3280-328932B1-32BFA830-A835",
        P: "0021-00230025-002A002C-002F003A003B003F0040005B-005D005F007B007D00A100AB00B700BB00BF037E0387055A-055F0589058A05BE05C005C305C605F305F40609060A060C060D061B061E061F066A-066D06D40700-070D07F7-07F90830-083E0964096509700DF40E4F0E5A0E5B0F04-0F120F3A-0F3D0F850FD0-0FD4104A-104F10FB1361-13681400166D166E169B169C16EB-16ED1735173617D4-17D617D8-17DA1800-180A1944194519DE19DF1A1E1A1F1AA0-1AA61AA8-1AAD1B5A-1B601C3B-1C3F1C7E1C7F1CD32010-20272030-20432045-20512053-205E207D207E208D208E2329232A2768-277527C527C627E6-27EF2983-299829D8-29DB29FC29FD2CF9-2CFC2CFE2CFF2E00-2E2E2E302E313001-30033008-30113014-301F3030303D30A030FBA4FEA4FFA60D-A60FA673A67EA6F2-A6F7A874-A877A8CEA8CFA8F8-A8FAA92EA92FA95FA9C1-A9CDA9DEA9DFAA5C-AA5FAADEAADFABEBFD3EFD3FFE10-FE19FE30-FE52FE54-FE61FE63FE68FE6AFE6BFF01-FF03FF05-FF0AFF0C-FF0FFF1AFF1BFF1FFF20FF3B-FF3DFF3FFF5BFF5DFF5F-FF65",
        Pd: "002D058A05BE140018062010-20152E172E1A301C303030A0FE31FE32FE58FE63FF0D",
        Ps: "0028005B007B0F3A0F3C169B201A201E2045207D208D23292768276A276C276E27702772277427C527E627E827EA27EC27EE2983298529872989298B298D298F299129932995299729D829DA29FC2E222E242E262E283008300A300C300E3010301430163018301A301DFD3EFE17FE35FE37FE39FE3BFE3DFE3FFE41FE43FE47FE59FE5BFE5DFF08FF3BFF5BFF5FFF62",
        Pe: "0029005D007D0F3B0F3D169C2046207E208E232A2769276B276D276F27712773277527C627E727E927EB27ED27EF298429862988298A298C298E2990299229942996299829D929DB29FD2E232E252E272E293009300B300D300F3011301530173019301B301E301FFD3FFE18FE36FE38FE3AFE3CFE3EFE40FE42FE44FE48FE5AFE5CFE5EFF09FF3DFF5DFF60FF63",
        Pi: "00AB2018201B201C201F20392E022E042E092E0C2E1C2E20",
        Pf: "00BB2019201D203A2E032E052E0A2E0D2E1D2E21",
        Pc: "005F203F20402054FE33FE34FE4D-FE4FFF3F",
        Po: "0021-00230025-0027002A002C002E002F003A003B003F0040005C00A100B700BF037E0387055A-055F058905C005C305C605F305F40609060A060C060D061B061E061F066A-066D06D40700-070D07F7-07F90830-083E0964096509700DF40E4F0E5A0E5B0F04-0F120F850FD0-0FD4104A-104F10FB1361-1368166D166E16EB-16ED1735173617D4-17D617D8-17DA1800-18051807-180A1944194519DE19DF1A1E1A1F1AA0-1AA61AA8-1AAD1B5A-1B601C3B-1C3F1C7E1C7F1CD3201620172020-20272030-2038203B-203E2041-20432047-205120532055-205E2CF9-2CFC2CFE2CFF2E002E012E06-2E082E0B2E0E-2E162E182E192E1B2E1E2E1F2E2A-2E2E2E302E313001-3003303D30FBA4FEA4FFA60D-A60FA673A67EA6F2-A6F7A874-A877A8CEA8CFA8F8-A8FAA92EA92FA95FA9C1-A9CDA9DEA9DFAA5C-AA5FAADEAADFABEBFE10-FE16FE19FE30FE45FE46FE49-FE4CFE50-FE52FE54-FE57FE5F-FE61FE68FE6AFE6BFF01-FF03FF05-FF07FF0AFF0CFF0EFF0FFF1AFF1BFF1FFF20FF3CFF61FF64FF65",
        S: "0024002B003C-003E005E0060007C007E00A2-00A900AC00AE-00B100B400B600B800D700F702C2-02C502D2-02DF02E5-02EB02ED02EF-02FF03750384038503F604820606-0608060B060E060F06E906FD06FE07F609F209F309FA09FB0AF10B700BF3-0BFA0C7F0CF10CF20D790E3F0F01-0F030F13-0F170F1A-0F1F0F340F360F380FBE-0FC50FC7-0FCC0FCE0FCF0FD5-0FD8109E109F13601390-139917DB194019E0-19FF1B61-1B6A1B74-1B7C1FBD1FBF-1FC11FCD-1FCF1FDD-1FDF1FED-1FEF1FFD1FFE20442052207A-207C208A-208C20A0-20B8210021012103-21062108210921142116-2118211E-2123212521272129212E213A213B2140-2144214A-214D214F2190-2328232B-23E82400-24262440-244A249C-24E92500-26CD26CF-26E126E326E8-26FF2701-27042706-2709270C-27272729-274B274D274F-27522756-275E2761-276727942798-27AF27B1-27BE27C0-27C427C7-27CA27CC27D0-27E527F0-29822999-29D729DC-29FB29FE-2B4C2B50-2B592CE5-2CEA2E80-2E992E9B-2EF32F00-2FD52FF0-2FFB300430123013302030363037303E303F309B309C319031913196-319F31C0-31E33200-321E322A-32503260-327F328A-32B032C0-32FE3300-33FF4DC0-4DFFA490-A4C6A700-A716A720A721A789A78AA828-A82BA836-A839AA77-AA79FB29FDFCFDFDFE62FE64-FE66FE69FF04FF0BFF1C-FF1EFF3EFF40FF5CFF5EFFE0-FFE6FFE8-FFEEFFFCFFFD",
        Sm: "002B003C-003E007C007E00AC00B100D700F703F60606-060820442052207A-207C208A-208C2140-2144214B2190-2194219A219B21A021A321A621AE21CE21CF21D221D421F4-22FF2308-230B23202321237C239B-23B323DC-23E125B725C125F8-25FF266F27C0-27C427C7-27CA27CC27D0-27E527F0-27FF2900-29822999-29D729DC-29FB29FE-2AFF2B30-2B442B47-2B4CFB29FE62FE64-FE66FF0BFF1C-FF1EFF5CFF5EFFE2FFE9-FFEC",
        Sc: "002400A2-00A5060B09F209F309FB0AF10BF90E3F17DB20A0-20B8A838FDFCFE69FF04FFE0FFE1FFE5FFE6",
        Sk: "005E006000A800AF00B400B802C2-02C502D2-02DF02E5-02EB02ED02EF-02FF0375038403851FBD1FBF-1FC11FCD-1FCF1FDD-1FDF1FED-1FEF1FFD1FFE309B309CA700-A716A720A721A789A78AFF3EFF40FFE3",
        So: "00A600A700A900AE00B000B60482060E060F06E906FD06FE07F609FA0B700BF3-0BF80BFA0C7F0CF10CF20D790F01-0F030F13-0F170F1A-0F1F0F340F360F380FBE-0FC50FC7-0FCC0FCE0FCF0FD5-0FD8109E109F13601390-1399194019E0-19FF1B61-1B6A1B74-1B7C210021012103-21062108210921142116-2118211E-2123212521272129212E213A213B214A214C214D214F2195-2199219C-219F21A121A221A421A521A7-21AD21AF-21CD21D021D121D321D5-21F32300-2307230C-231F2322-2328232B-237B237D-239A23B4-23DB23E2-23E82400-24262440-244A249C-24E92500-25B625B8-25C025C2-25F72600-266E2670-26CD26CF-26E126E326E8-26FF2701-27042706-2709270C-27272729-274B274D274F-27522756-275E2761-276727942798-27AF27B1-27BE2800-28FF2B00-2B2F2B452B462B50-2B592CE5-2CEA2E80-2E992E9B-2EF32F00-2FD52FF0-2FFB300430123013302030363037303E303F319031913196-319F31C0-31E33200-321E322A-32503260-327F328A-32B032C0-32FE3300-33FF4DC0-4DFFA490-A4C6A828-A82BA836A837A839AA77-AA79FDFDFFE4FFE8FFEDFFEEFFFCFFFD",
        Z: "002000A01680180E2000-200A20282029202F205F3000",
        Zs: "002000A01680180E2000-200A202F205F3000",
        Zl: "2028",
        Zp: "2029",
        C: "0000-001F007F-009F00AD03780379037F-0383038B038D03A20526-05300557055805600588058B-059005C8-05CF05EB-05EF05F5-0605061C061D0620065F06DD070E070F074B074C07B2-07BF07FB-07FF082E082F083F-08FF093A093B094F095609570973-097809800984098D098E0991099209A909B109B3-09B509BA09BB09C509C609C909CA09CF-09D609D8-09DB09DE09E409E509FC-0A000A040A0B-0A0E0A110A120A290A310A340A370A3A0A3B0A3D0A43-0A460A490A4A0A4E-0A500A52-0A580A5D0A5F-0A650A76-0A800A840A8E0A920AA90AB10AB40ABA0ABB0AC60ACA0ACE0ACF0AD1-0ADF0AE40AE50AF00AF2-0B000B040B0D0B0E0B110B120B290B310B340B3A0B3B0B450B460B490B4A0B4E-0B550B58-0B5B0B5E0B640B650B72-0B810B840B8B-0B8D0B910B96-0B980B9B0B9D0BA0-0BA20BA5-0BA70BAB-0BAD0BBA-0BBD0BC3-0BC50BC90BCE0BCF0BD1-0BD60BD8-0BE50BFB-0C000C040C0D0C110C290C340C3A-0C3C0C450C490C4E-0C540C570C5A-0C5F0C640C650C70-0C770C800C810C840C8D0C910CA90CB40CBA0CBB0CC50CC90CCE-0CD40CD7-0CDD0CDF0CE40CE50CF00CF3-0D010D040D0D0D110D290D3A-0D3C0D450D490D4E-0D560D58-0D5F0D640D650D76-0D780D800D810D840D97-0D990DB20DBC0DBE0DBF0DC7-0DC90DCB-0DCE0DD50DD70DE0-0DF10DF5-0E000E3B-0E3E0E5C-0E800E830E850E860E890E8B0E8C0E8E-0E930E980EA00EA40EA60EA80EA90EAC0EBA0EBE0EBF0EC50EC70ECE0ECF0EDA0EDB0EDE-0EFF0F480F6D-0F700F8C-0F8F0F980FBD0FCD0FD9-0FFF10C6-10CF10FD-10FF1249124E124F12571259125E125F1289128E128F12B112B612B712BF12C112C612C712D7131113161317135B-135E137D-137F139A-139F13F5-13FF169D-169F16F1-16FF170D1715-171F1737-173F1754-175F176D17711774-177F17B417B517DE17DF17EA-17EF17FA-17FF180F181A-181F1878-187F18AB-18AF18F6-18FF191D-191F192C-192F193C-193F1941-1943196E196F1975-197F19AC-19AF19CA-19CF19DB-19DD1A1C1A1D1A5F1A7D1A7E1A8A-1A8F1A9A-1A9F1AAE-1AFF1B4C-1B4F1B7D-1B7F1BAB-1BAD1BBA-1BFF1C38-1C3A1C4A-1C4C1C80-1CCF1CF3-1CFF1DE7-1DFC1F161F171F1E1F1F1F461F471F4E1F4F1F581F5A1F5C1F5E1F7E1F7F1FB51FC51FD41FD51FDC1FF01FF11FF51FFF200B-200F202A-202E2060-206F20722073208F2095-209F20B9-20CF20F1-20FF218A-218F23E9-23FF2427-243F244B-245F26CE26E226E4-26E727002705270A270B2728274C274E2753-2755275F27602795-279727B027BF27CB27CD-27CF2B4D-2B4F2B5A-2BFF2C2F2C5F2CF2-2CF82D26-2D2F2D66-2D6E2D70-2D7F2D97-2D9F2DA72DAF2DB72DBF2DC72DCF2DD72DDF2E32-2E7F2E9A2EF4-2EFF2FD6-2FEF2FFC-2FFF3040309730983100-3104312E-3130318F31B8-31BF31E4-31EF321F32FF4DB6-4DBF9FCC-9FFFA48D-A48FA4C7-A4CFA62C-A63FA660A661A674-A67BA698-A69FA6F8-A6FFA78D-A7FAA82C-A82FA83A-A83FA878-A87FA8C5-A8CDA8DA-A8DFA8FC-A8FFA954-A95EA97D-A97FA9CEA9DA-A9DDA9E0-A9FFAA37-AA3FAA4EAA4FAA5AAA5BAA7C-AA7FAAC3-AADAAAE0-ABBFABEEABEFABFA-ABFFD7A4-D7AFD7C7-D7CAD7FC-F8FFFA2EFA2FFA6EFA6FFADA-FAFFFB07-FB12FB18-FB1CFB37FB3DFB3FFB42FB45FBB2-FBD2FD40-FD4FFD90FD91FDC8-FDEFFDFEFDFFFE1A-FE1FFE27-FE2FFE53FE67FE6C-FE6FFE75FEFD-FF00FFBF-FFC1FFC8FFC9FFD0FFD1FFD8FFD9FFDD-FFDFFFE7FFEF-FFFBFFFEFFFF",
        Cc: "0000-001F007F-009F",
        Cf: "00AD0600-060306DD070F17B417B5200B-200F202A-202E2060-2064206A-206FFEFFFFF9-FFFB",
        Co: "E000-F8FF",
        Cs: "D800-DFFF",
        Cn: "03780379037F-0383038B038D03A20526-05300557055805600588058B-059005C8-05CF05EB-05EF05F5-05FF06040605061C061D0620065F070E074B074C07B2-07BF07FB-07FF082E082F083F-08FF093A093B094F095609570973-097809800984098D098E0991099209A909B109B3-09B509BA09BB09C509C609C909CA09CF-09D609D8-09DB09DE09E409E509FC-0A000A040A0B-0A0E0A110A120A290A310A340A370A3A0A3B0A3D0A43-0A460A490A4A0A4E-0A500A52-0A580A5D0A5F-0A650A76-0A800A840A8E0A920AA90AB10AB40ABA0ABB0AC60ACA0ACE0ACF0AD1-0ADF0AE40AE50AF00AF2-0B000B040B0D0B0E0B110B120B290B310B340B3A0B3B0B450B460B490B4A0B4E-0B550B58-0B5B0B5E0B640B650B72-0B810B840B8B-0B8D0B910B96-0B980B9B0B9D0BA0-0BA20BA5-0BA70BAB-0BAD0BBA-0BBD0BC3-0BC50BC90BCE0BCF0BD1-0BD60BD8-0BE50BFB-0C000C040C0D0C110C290C340C3A-0C3C0C450C490C4E-0C540C570C5A-0C5F0C640C650C70-0C770C800C810C840C8D0C910CA90CB40CBA0CBB0CC50CC90CCE-0CD40CD7-0CDD0CDF0CE40CE50CF00CF3-0D010D040D0D0D110D290D3A-0D3C0D450D490D4E-0D560D58-0D5F0D640D650D76-0D780D800D810D840D97-0D990DB20DBC0DBE0DBF0DC7-0DC90DCB-0DCE0DD50DD70DE0-0DF10DF5-0E000E3B-0E3E0E5C-0E800E830E850E860E890E8B0E8C0E8E-0E930E980EA00EA40EA60EA80EA90EAC0EBA0EBE0EBF0EC50EC70ECE0ECF0EDA0EDB0EDE-0EFF0F480F6D-0F700F8C-0F8F0F980FBD0FCD0FD9-0FFF10C6-10CF10FD-10FF1249124E124F12571259125E125F1289128E128F12B112B612B712BF12C112C612C712D7131113161317135B-135E137D-137F139A-139F13F5-13FF169D-169F16F1-16FF170D1715-171F1737-173F1754-175F176D17711774-177F17DE17DF17EA-17EF17FA-17FF180F181A-181F1878-187F18AB-18AF18F6-18FF191D-191F192C-192F193C-193F1941-1943196E196F1975-197F19AC-19AF19CA-19CF19DB-19DD1A1C1A1D1A5F1A7D1A7E1A8A-1A8F1A9A-1A9F1AAE-1AFF1B4C-1B4F1B7D-1B7F1BAB-1BAD1BBA-1BFF1C38-1C3A1C4A-1C4C1C80-1CCF1CF3-1CFF1DE7-1DFC1F161F171F1E1F1F1F461F471F4E1F4F1F581F5A1F5C1F5E1F7E1F7F1FB51FC51FD41FD51FDC1FF01FF11FF51FFF2065-206920722073208F2095-209F20B9-20CF20F1-20FF218A-218F23E9-23FF2427-243F244B-245F26CE26E226E4-26E727002705270A270B2728274C274E2753-2755275F27602795-279727B027BF27CB27CD-27CF2B4D-2B4F2B5A-2BFF2C2F2C5F2CF2-2CF82D26-2D2F2D66-2D6E2D70-2D7F2D97-2D9F2DA72DAF2DB72DBF2DC72DCF2DD72DDF2E32-2E7F2E9A2EF4-2EFF2FD6-2FEF2FFC-2FFF3040309730983100-3104312E-3130318F31B8-31BF31E4-31EF321F32FF4DB6-4DBF9FCC-9FFFA48D-A48FA4C7-A4CFA62C-A63FA660A661A674-A67BA698-A69FA6F8-A6FFA78D-A7FAA82C-A82FA83A-A83FA878-A87FA8C5-A8CDA8DA-A8DFA8FC-A8FFA954-A95EA97D-A97FA9CEA9DA-A9DDA9E0-A9FFAA37-AA3FAA4EAA4FAA5AAA5BAA7C-AA7FAAC3-AADAAAE0-ABBFABEEABEFABFA-ABFFD7A4-D7AFD7C7-D7CAD7FC-D7FFFA2EFA2FFA6EFA6FFADA-FAFFFB07-FB12FB18-FB1CFB37FB3DFB3FFB42FB45FBB2-FBD2FD40-FD4FFD90FD91FDC8-FDEFFDFEFDFFFE1A-FE1FFE27-FE2FFE53FE67FE6C-FE6FFE75FEFDFEFEFF00FFBF-FFC1FFC8FFC9FFD0FFD1FFD8FFD9FFDD-FFDFFFE7FFEF-FFF8FFFEFFFF"
    })
}), define("ace/token_iterator", ["require", "exports", "module"], function(e, t, n) {
    "use strict";
    var r = function(e, t, n) {
        this.$session = e, this.$row = t, this.$rowTokens = e.getTokens(t);
        var r = e.getTokenAt(t, n);
        this.$tokenIndex = r ? r.index : -1
    };
    (function() {
        this.stepBackward = function() {
            this.$tokenIndex -= 1;
            while (this.$tokenIndex < 0) {
                this.$row -= 1;
                if (this.$row < 0) return this.$row = 0, null;
                this.$rowTokens = this.$session.getTokens(this.$row), this.$tokenIndex = this.$rowTokens.length - 1
            }
            return this.$rowTokens[this.$tokenIndex]
        }, this.stepForward = function() {
            this.$tokenIndex += 1;
            var e;
            while (this.$tokenIndex >= this.$rowTokens.length) {
                this.$row += 1, e || (e = this.$session.getLength());
                if (this.$row >= e) return this.$row = e - 1, null;
                this.$rowTokens = this.$session.getTokens(this.$row), this.$tokenIndex = 0
            }
            return this.$rowTokens[this.$tokenIndex]
        }, this.getCurrentToken = function() {
            return this.$rowTokens[this.$tokenIndex]
        }, this.getCurrentTokenRow = function() {
            return this.$row
        }, this.getCurrentTokenColumn = function() {
            var e = this.$rowTokens,
                t = this.$tokenIndex,
                n = e[t].start;
            if (n !== undefined) return n;
            n = 0;
            while (t > 0) t -= 1, n += e[t].value.length;
            return n
        }, this.getCurrentTokenPosition = function() {
            return {
                row: this.$row,
                column: this.getCurrentTokenColumn()
            }
        }
    }).call(r.prototype), t.TokenIterator = r
}), define("ace/mode/text", ["require", "exports", "module", "ace/tokenizer", "ace/mode/text_highlight_rules", "ace/mode/behaviour", "ace/unicode", "ace/lib/lang", "ace/token_iterator", "ace/range"], function(e, t, n) {
    "use strict";
    var r = e("../tokenizer").Tokenizer,
        i = e("./text_highlight_rules").TextHighlightRules,
        s = e("./behaviour").Behaviour,
        o = e("../unicode"),
        u = e("../lib/lang"),
        a = e("../token_iterator").TokenIterator,
        f = e("../range").Range,
        l = function() {
            this.HighlightRules = i, this.$behaviour = new s
        };
    (function() {
        this.tokenRe = new RegExp("^[" + o.packages.L + o.packages.Mn + o.packages.Mc + o.packages.Nd + o.packages.Pc + "\\$_]+", "g"), this.nonTokenRe = new RegExp("^(?:[^" + o.packages.L + o.packages.Mn + o.packages.Mc + o.packages.Nd + o.packages.Pc + "\\$_]|\\s])+", "g"), this.getTokenizer = function() {
            return this.$tokenizer || (this.$highlightRules = this.$highlightRules || new this.HighlightRules, this.$tokenizer = new r(this.$highlightRules.getRules())), this.$tokenizer
        }, this.lineCommentStart = "", this.blockComment = "", this.toggleCommentLines = function(e, t, n, r) {
            function w(e) {
                for (var t = n; t <= r; t++) e(i.getLine(t), t)
            }
            var i = t.doc,
                s = !0,
                o = !0,
                a = Infinity,
                f = t.getTabSize(),
                l = !1;
            if (!this.lineCommentStart) {
                if (!this.blockComment) return !1;
                var c = this.blockComment.start,
                    h = this.blockComment.end,
                    p = new RegExp("^(\\s*)(?:" + u.escapeRegExp(c) + ")"),
                    d = new RegExp("(?:" + u.escapeRegExp(h) + ")\\s*$"),
                    v = function(e, t) {
                        if (g(e, t)) return;
                        if (!s || /\S/.test(e)) i.insertInLine({
                            row: t,
                            column: e.length
                        }, h), i.insertInLine({
                            row: t,
                            column: a
                        }, c)
                    },
                    m = function(e, t) {
                        var n;
                        (n = e.match(d)) && i.removeInLine(t, e.length - n[0].length, e.length), (n = e.match(p)) && i.removeInLine(t, n[1].length, n[0].length)
                    },
                    g = function(e, n) {
                        if (p.test(e)) return !0;
                        var r = t.getTokens(n);
                        for (var i = 0; i < r.length; i++)
                            if (r[i].type === "comment") return !0
                    }
            } else {
                if (Array.isArray(this.lineCommentStart)) var p = this.lineCommentStart.map(u.escapeRegExp).join("|"),
                    c = this.lineCommentStart[0];
                else var p = u.escapeRegExp(this.lineCommentStart),
                    c = this.lineCommentStart;
                p = new RegExp("^(\\s*)(?:" + p + ") ?"), l = t.getUseSoftTabs();
                var m = function(e, t) {
                        var n = e.match(p);
                        if (!n) return;
                        var r = n[1].length,
                            s = n[0].length;
                        !b(e, r, s) && n[0][s - 1] == " " && s--, i.removeInLine(t, r, s)
                    },
                    y = c + " ",
                    v = function(e, t) {
                        if (!s || /\S/.test(e)) b(e, a, a) ? i.insertInLine({
                            row: t,
                            column: a
                        }, y) : i.insertInLine({
                            row: t,
                            column: a
                        }, c)
                    },
                    g = function(e, t) {
                        return p.test(e)
                    },
                    b = function(e, t, n) {
                        var r = 0;
                        while (t-- && e.charAt(t) == " ") r++;
                        if (r % f != 0) return !1;
                        var r = 0;
                        while (e.charAt(n++) == " ") r++;
                        return f > 2 ? r % f != f - 1 : r % f == 0
                    }
            }
            var E = Infinity;
            w(function(e, t) {
                var n = e.search(/\S/);
                n !== -1 ? (n < a && (a = n), o && !g(e, t) && (o = !1)) : E > e.length && (E = e.length)
            }), a == Infinity && (a = E, s = !1, o = !1), l && a % f != 0 && (a = Math.floor(a / f) * f), w(o ? m : v)
        }, this.toggleBlockComment = function(e, t, n, r) {
            var i = this.blockComment;
            if (!i) return;
            !i.start && i[0] && (i = i[0]);
            var s = new a(t, r.row, r.column),
                o = s.getCurrentToken(),
                u = t.selection,
                l = t.selection.toOrientedRange(),
                c, h;
            if (o && /comment/.test(o.type)) {
                var p, d;
                while (o && /comment/.test(o.type)) {
                    var v = o.value.indexOf(i.start);
                    if (v != -1) {
                        var m = s.getCurrentTokenRow(),
                            g = s.getCurrentTokenColumn() + v;
                        p = new f(m, g, m, g + i.start.length);
                        break
                    }
                    o = s.stepBackward()
                }
                var s = new a(t, r.row, r.column),
                    o = s.getCurrentToken();
                while (o && /comment/.test(o.type)) {
                    var v = o.value.indexOf(i.end);
                    if (v != -1) {
                        var m = s.getCurrentTokenRow(),
                            g = s.getCurrentTokenColumn() + v;
                        d = new f(m, g, m, g + i.end.length);
                        break
                    }
                    o = s.stepForward()
                }
                d && t.remove(d), p && (t.remove(p), c = p.start.row, h = -i.start.length)
            } else h = i.start.length, c = n.start.row, t.insert(n.end, i.end), t.insert(n.start, i.start);
            l.start.row == c && (l.start.column += h), l.end.row == c && (l.end.column += h), t.selection.fromOrientedRange(l)
        }, this.getNextLineIndent = function(e, t, n) {
            return this.$getIndent(t)
        }, this.checkOutdent = function(e, t, n) {
            return !1
        }, this.autoOutdent = function(e, t, n) {}, this.$getIndent = function(e) {
            return e.match(/^\s*/)[0]
        }, this.createWorker = function(e) {
            return null
        }, this.createModeDelegates = function(e) {
            this.$embeds = [], this.$modes = {};
            for (var t in e) e[t] && (this.$embeds.push(t), this.$modes[t] = new e[t]);
            var n = ["toggleBlockComment", "toggleCommentLines", "getNextLineIndent", "checkOutdent", "autoOutdent", "transformAction", "getCompletions"];
            for (var t = 0; t < n.length; t++)(function(e) {
                var r = n[t],
                    i = e[r];
                e[n[t]] = function() {
                    return this.$delegator(r, arguments, i)
                }
            })(this)
        }, this.$delegator = function(e, t, n) {
            var r = t[0];
            typeof r != "string" && (r = r[0]);
            for (var i = 0; i < this.$embeds.length; i++) {
                if (!this.$modes[this.$embeds[i]]) continue;
                var s = r.split(this.$embeds[i]);
                if (!s[0] && s[1]) {
                    t[0] = s[1];
                    var o = this.$modes[this.$embeds[i]];
                    return o[e].apply(o, t)
                }
            }
            var u = n.apply(this, t);
            return n ? u : undefined
        }, this.transformAction = function(e, t, n, r, i) {
            if (this.$behaviour) {
                var s = this.$behaviour.getBehaviours();
                for (var o in s)
                    if (s[o][t]) {
                        var u = s[o][t].apply(this, arguments);
                        if (u) return u
                    }
            }
        }, this.getKeywords = function(e) {
            if (!this.completionKeywords) {
                var t = this.$tokenizer.rules,
                    n = [];
                for (var r in t) {
                    var i = t[r];
                    for (var s = 0, o = i.length; s < o; s++)
                        if (typeof i[s].token == "string") /keyword|support|storage/.test(i[s].token) && n.push(i[s].regex);
                        else if (typeof i[s].token == "object")
                        for (var u = 0, a = i[s].token.length; u < a; u++)
                            if (/keyword|support|storage/.test(i[s].token[u])) {
                                var r = i[s].regex.match(/\(.+?\)/g)[u];
                                n.push(r.substr(1, r.length - 2))
                            }
                }
                this.completionKeywords = n
            }
            return e ? n.concat(this.$keywordList || []) : this.$keywordList
        }, this.$createKeywordList = function() {
            return this.$highlightRules || this.getTokenizer(), this.$keywordList = this.$highlightRules.$keywordList || []
        }, this.getCompletions = function(e, t, n, r) {
            var i = this.$keywordList || this.$createKeywordList();
            return i.map(function(e) {
                return {
                    name: e,
                    value: e,
                    score: 0,
                    meta: "keyword"
                }
            })
        }, this.$id = "ace/mode/text"
    }).call(l.prototype), t.Mode = l
}), define("ace/apply_delta", ["require", "exports", "module"], function(e, t, n) {
    "use strict";

    function r(e, t) {
        throw console.log("Invalid Delta:", e), "Invalid Delta: " + t
    }

    function i(e, t) {
        return t.row >= 0 && t.row < e.length && t.column >= 0 && t.column <= e[t.row].length
    }

    function s(e, t) {
        t.action != "insert" && t.action != "remove" && r(t, "delta.action must be 'insert' or 'remove'"), t.lines instanceof Array || r(t, "delta.lines must be an Array"), (!t.start || !t.end) && r(t, "delta.start/end must be an present");
        var n = t.start;
        i(e, t.start) || r(t, "delta.start must be contained in document");
        var s = t.end;
        t.action == "remove" && !i(e, s) && r(t, "delta.end must contained in document for 'remove' actions");
        var o = s.row - n.row,
            u = s.column - (o == 0 ? n.column : 0);
        (o != t.lines.length - 1 || t.lines[o].length != u) && r(t, "delta.range must match delta lines")
    }
    t.applyDelta = function(e, t, n) {
        var r = t.start.row,
            i = t.start.column,
            s = e[r] || "";
        switch (t.action) {
            case "insert":
                var o = t.lines;
                if (o.length === 1) e[r] = s.substring(0, i) + t.lines[0] + s.substring(i);
                else {
                    var u = [r, 1].concat(t.lines);
                    e.splice.apply(e, u), e[r] = s.substring(0, i) + e[r], e[r + t.lines.length - 1] += s.substring(i)
                }
                break;
            case "remove":
                var a = t.end.column,
                    f = t.end.row;
                r === f ? e[r] = s.substring(0, i) + s.substring(a) : e.splice(r, f - r + 1, s.substring(0, i) + e[f].substring(a))
        }
    }
}), define("ace/anchor", ["require", "exports", "module", "ace/lib/oop", "ace/lib/event_emitter"], function(e, t, n) {
    "use strict";
    var r = e("./lib/oop"),
        i = e("./lib/event_emitter").EventEmitter,
        s = t.Anchor = function(e, t, n) {
            this.$onChange = this.onChange.bind(this), this.attach(e), typeof n == "undefined" ? this.setPosition(t.row, t.column) : this.setPosition(t, n)
        };
    (function() {
        function e(e, t, n) {
            var r = n ? e.column <= t.column : e.column < t.column;
            return e.row < t.row || e.row == t.row && r
        }

        function t(t, n, r) {
            var i = t.action == "insert",
                s = (i ? 1 : -1) * (t.end.row - t.start.row),
                o = (i ? 1 : -1) * (t.end.column - t.start.column),
                u = t.start,
                a = i ? u : t.end;
            return e(n, u, r) ? {
                row: n.row,
                column: n.column
            } : e(a, n, !r) ? {
                row: n.row + s,
                column: n.column + (n.row == a.row ? o : 0)
            } : {
                row: u.row,
                column: u.column
            }
        }
        r.implement(this, i), this.getPosition = function() {
            return this.$clipPositionToDocument(this.row, this.column)
        }, this.getDocument = function() {
            return this.document
        }, this.$insertRight = !1, this.onChange = function(e) {
            if (e.start.row == e.end.row && e.start.row != this.row) return;
            if (e.start.row > this.row) return;
            var n = t(e, {
                row: this.row,
                column: this.column
            }, this.$insertRight);
            this.setPosition(n.row, n.column, !0)
        }, this.setPosition = function(e, t, n) {
            var r;
            n ? r = {
                row: e,
                column: t
            } : r = this.$clipPositionToDocument(e, t);
            if (this.row == r.row && this.column == r.column) return;
            var i = {
                row: this.row,
                column: this.column
            };
            this.row = r.row, this.column = r.column, this._signal("change", {
                old: i,
                value: r
            })
        }, this.detach = function() {
            this.document.removeEventListener("change", this.$onChange)
        }, this.attach = function(e) {
            this.document = e || this.document, this.document.on("change", this.$onChange)
        }, this.$clipPositionToDocument = function(e, t) {
            var n = {};
            return e >= this.document.getLength() ? (n.row = Math.max(0, this.document.getLength() - 1), n.column = this.document.getLine(n.row).length) : e < 0 ? (n.row = 0, n.column = 0) : (n.row = e, n.column = Math.min(this.document.getLine(n.row).length, Math.max(0, t))), t < 0 && (n.column = 0), n
        }
    }).call(s.prototype)
}), define("ace/document", ["require", "exports", "module", "ace/lib/oop", "ace/apply_delta", "ace/lib/event_emitter", "ace/range", "ace/anchor"], function(e, t, n) {
    "use strict";
    var r = e("./lib/oop"),
        i = e("./apply_delta").applyDelta,
        s = e("./lib/event_emitter").EventEmitter,
        o = e("./range").Range,
        u = e("./anchor").Anchor,
        a = function(e) {
            this.$lines = [""], e.length === 0 ? this.$lines = [""] : Array.isArray(e) ? this.insertMergedLines({
                row: 0,
                column: 0
            }, e) : this.insert({
                row: 0,
                column: 0
            }, e)
        };
    (function() {
        r.implement(this, s), this.setValue = function(e) {
            var t = this.getLength() - 1;
            this.remove(new o(0, 0, t, this.getLine(t).length)), this.insert({
                row: 0,
                column: 0
            }, e)
        }, this.getValue = function() {
            return this.getAllLines().join(this.getNewLineCharacter())
        }, this.createAnchor = function(e, t) {
            return new u(this, e, t)
        }, "aaa".split(/a/).length === 0 ? this.$split = function(e) {
            return e.replace(/\r\n|\r/g, "\n").split("\n")
        } : this.$split = function(e) {
            return e.split(/\r\n|\r|\n/)
        }, this.$detectNewLine = function(e) {
            var t = e.match(/^.*?(\r\n|\r|\n)/m);
            this.$autoNewLine = t ? t[1] : "\n", this._signal("changeNewLineMode")
        }, this.getNewLineCharacter = function() {
            switch (this.$newLineMode) {
                case "windows":
                    return "\r\n";
                case "unix":
                    return "\n";
                default:
                    return this.$autoNewLine || "\n"
            }
        }, this.$autoNewLine = "", this.$newLineMode = "auto", this.setNewLineMode = function(e) {
            if (this.$newLineMode === e) return;
            this.$newLineMode = e, this._signal("changeNewLineMode")
        }, this.getNewLineMode = function() {
            return this.$newLineMode
        }, this.isNewLine = function(e) {
            return e == "\r\n" || e == "\r" || e == "\n"
        }, this.getLine = function(e) {
            return this.$lines[e] || ""
        }, this.getLines = function(e, t) {
            return this.$lines.slice(e, t + 1)
        }, this.getAllLines = function() {
            return this.getLines(0, this.getLength())
        }, this.getLength = function() {
            return this.$lines.length
        }, this.getTextRange = function(e) {
            return this.getLinesForRange(e).join(this.getNewLineCharacter())
        }, this.getLinesForRange = function(e) {
            var t;
            if (e.start.row === e.end.row) t = [this.getLine(e.start.row).substring(e.start.column, e.end.column)];
            else {
                t = this.getLines(e.start.row, e.end.row), t[0] = (t[0] || "").substring(e.start.column);
                var n = t.length - 1;
                e.end.row - e.start.row == n && (t[n] = t[n].substring(0, e.end.column))
            }
            return t
        }, this.insertLines = function(e, t) {
            return console.warn("Use of document.insertLines is deprecated. Use the insertFullLines method instead."), this.insertFullLines(e, t)
        }, this.removeLines = function(e, t) {
            return console.warn("Use of document.removeLines is deprecated. Use the removeFullLines method instead."), this.removeFullLines(e, t)
        }, this.insertNewLine = function(e) {
            return console.warn("Use of document.insertNewLine is deprecated. Use insertMergedLines(position, ['', '']) instead."), this.insertMergedLines(e, ["", ""])
        }, this.insert = function(e, t) {
            return this.getLength() <= 1 && this.$detectNewLine(t), this.insertMergedLines(e, this.$split(t))
        }, this.insertInLine = function(e, t) {
            var n = this.clippedPos(e.row, e.column),
                r = this.pos(e.row, e.column + t.length);
            return this.applyDelta({
                start: n,
                end: r,
                action: "insert",
                lines: [t]
            }, !0), this.clonePos(r)
        }, this.clippedPos = function(e, t) {
            var n = this.getLength();
            e === undefined ? e = n : e < 0 ? e = 0 : e >= n && (e = n - 1, t = undefined);
            var r = this.getLine(e);
            return t == undefined && (t = r.length), t = Math.min(Math.max(t, 0), r.length), {
                row: e,
                column: t
            }
        }, this.clonePos = function(e) {
            return {
                row: e.row,
                column: e.column
            }
        }, this.pos = function(e, t) {
            return {
                row: e,
                column: t
            }
        }, this.$clipPosition = function(e) {
            var t = this.getLength();
            return e.row >= t ? (e.row = Math.max(0, t - 1), e.column = this.getLine(t - 1).length) : (e.row = Math.max(0, e.row), e.column = Math.min(Math.max(e.column, 0), this.getLine(e.row).length)), e
        }, this.insertFullLines = function(e, t) {
            e = Math.min(Math.max(e, 0), this.getLength());
            var n = 0;
            e < this.getLength() ? (t = t.concat([""]), n = 0) : (t = [""].concat(t), e--, n = this.$lines[e].length), this.insertMergedLines({
                row: e,
                column: n
            }, t)
        }, this.insertMergedLines = function(e, t) {
            var n = this.clippedPos(e.row, e.column),
                r = {
                    row: n.row + t.length - 1,
                    column: (t.length == 1 ? n.column : 0) + t[t.length - 1].length
                };
            return this.applyDelta({
                start: n,
                end: r,
                action: "insert",
                lines: t
            }), this.clonePos(r)
        }, this.remove = function(e) {
            var t = this.clippedPos(e.start.row, e.start.column),
                n = this.clippedPos(e.end.row, e.end.column);
            return this.applyDelta({
                start: t,
                end: n,
                action: "remove",
                lines: this.getLinesForRange({
                    start: t,
                    end: n
                })
            }), this.clonePos(t)
        }, this.removeInLine = function(e, t, n) {
            var r = this.clippedPos(e, t),
                i = this.clippedPos(e, n);
            return this.applyDelta({
                start: r,
                end: i,
                action: "remove",
                lines: this.getLinesForRange({
                    start: r,
                    end: i
                })
            }, !0), this.clonePos(r)
        }, this.removeFullLines = function(e, t) {
            e = Math.min(Math.max(0, e), this.getLength() - 1), t = Math.min(Math.max(0, t), this.getLength() - 1);
            var n = t == this.getLength() - 1 && e > 0,
                r = t < this.getLength() - 1,
                i = n ? e - 1 : e,
                s = n ? this.getLine(i).length : 0,
                u = r ? t + 1 : t,
                a = r ? 0 : this.getLine(u).length,
                f = new o(i, s, u, a),
                l = this.$lines.slice(e, t + 1);
            return this.applyDelta({
                start: f.start,
                end: f.end,
                action: "remove",
                lines: this.getLinesForRange(f)
            }), l
        }, this.removeNewLine = function(e) {
            e < this.getLength() - 1 && e >= 0 && this.applyDelta({
                start: this.pos(e, this.getLine(e).length),
                end: this.pos(e + 1, 0),
                action: "remove",
                lines: ["", ""]
            })
        }, this.replace = function(e, t) {
            !e instanceof o && (e = o.fromPoints(e.start, e.end));
            if (t.length === 0 && e.isEmpty()) return e.start;
            if (t == this.getTextRange(e)) return e.end;
            this.remove(e);
            var n;
            return t ? n = this.insert(e.start, t) : n = e.start, n
        }, this.applyDeltas = function(e) {
            for (var t = 0; t < e.length; t++) this.applyDelta(e[t])
        }, this.revertDeltas = function(e) {
            for (var t = e.length - 1; t >= 0; t--) this.revertDelta(e[t])
        }, this.applyDelta = function(e, t) {
            var n = e.action == "insert";
            if (n ? e.lines.length <= 1 && !e.lines[0] : !o.comparePoints(e.start, e.end)) return;
            n && e.lines.length > 2e4 && this.$splitAndapplyLargeDelta(e, 2e4), i(this.$lines, e, t), this._signal("change", e)
        }, this.$splitAndapplyLargeDelta = function(e, t) {
            var n = e.lines,
                r = n.length,
                i = e.start.row,
                s = e.start.column,
                o = 0,
                u = 0;
            do {
                o = u, u += t - 1;
                var a = n.slice(o, u);
                if (u > r) {
                    e.lines = a, e.start.row = i + o, e.start.column = s;
                    break
                }
                a.push(""), this.applyDelta({
                    start: this.pos(i + o, s),
                    end: this.pos(i + u, s = 0),
                    action: e.action,
                    lines: a
                }, !0)
            } while (!0)
        }, this.revertDelta = function(e) {
            this.applyDelta({
                start: this.clonePos(e.start),
                end: this.clonePos(e.end),
                action: e.action == "insert" ? "remove" : "insert",
                lines: e.lines.slice()
            })
        }, this.indexToPosition = function(e, t) {
            var n = this.$lines || this.getAllLines(),
                r = this.getNewLineCharacter().length;
            for (var i = t || 0, s = n.length; i < s; i++) {
                e -= n[i].length + r;
                if (e < 0) return {
                    row: i,
                    column: e + n[i].length + r
                }
            }
            return {
                row: s - 1,
                column: n[s - 1].length
            }
        }, this.positionToIndex = function(e, t) {
            var n = this.$lines || this.getAllLines(),
                r = this.getNewLineCharacter().length,
                i = 0,
                s = Math.min(e.row, n.length);
            for (var o = t || 0; o < s; ++o) i += n[o].length + r;
            return i + e.column
        }
    }).call(a.prototype), t.Document = a
}), define("ace/background_tokenizer", ["require", "exports", "module", "ace/lib/oop", "ace/lib/event_emitter"], function(e, t, n) {
    "use strict";
    var r = e("./lib/oop"),
        i = e("./lib/event_emitter").EventEmitter,
        s = function(e, t) {
            this.running = !1, this.lines = [], this.states = [], this.currentLine = 0, this.tokenizer = e;
            var n = this;
            this.$worker = function() {
                if (!n.running) return;
                var e = new Date,
                    t = n.currentLine,
                    r = -1,
                    i = n.doc,
                    s = t;
                while (n.lines[t]) t++;
                var o = i.getLength(),
                    u = 0;
                n.running = !1;
                while (t < o) {
                    n.$tokenizeRow(t), r = t;
                    do t++; while (n.lines[t]);
                    u++;
                    if (u % 5 === 0 && new Date - e > 20) {
                        n.running = setTimeout(n.$worker, 20);
                        break
                    }
                }
                n.currentLine = t, s <= r && n.fireUpdateEvent(s, r)
            }
        };
    (function() {
        r.implement(this, i), this.setTokenizer = function(e) {
            this.tokenizer = e, this.lines = [], this.states = [], this.start(0)
        }, this.setDocument = function(e) {
            this.doc = e, this.lines = [], this.states = [], this.stop()
        }, this.fireUpdateEvent = function(e, t) {
            var n = {
                first: e,
                last: t
            };
            this._signal("update", {
                data: n
            })
        }, this.start = function(e) {
            this.currentLine = Math.min(e || 0, this.currentLine, this.doc.getLength()), this.lines.splice(this.currentLine, this.lines.length), this.states.splice(this.currentLine, this.states.length), this.stop(), this.running = setTimeout(this.$worker, 700)
        }, this.scheduleStart = function() {
            this.running || (this.running = setTimeout(this.$worker, 700))
        }, this.$updateOnChange = function(e) {
            var t = e.start.row,
                n = e.end.row - t;
            if (n === 0) this.lines[t] = null;
            else if (e.action == "remove") this.lines.splice(t, n + 1, null), this.states.splice(t, n + 1, null);
            else {
                var r = Array(n + 1);
                r.unshift(t, 1), this.lines.splice.apply(this.lines, r), this.states.splice.apply(this.states, r)
            }
            this.currentLine = Math.min(t, this.currentLine, this.doc.getLength()), this.stop()
        }, this.stop = function() {
            this.running && clearTimeout(this.running), this.running = !1
        }, this.getTokens = function(e) {
            return this.lines[e] || this.$tokenizeRow(e)
        }, this.getState = function(e) {
            return this.currentLine == e && this.$tokenizeRow(e), this.states[e] || "start"
        }, this.$tokenizeRow = function(e) {
            var t = this.doc.getLine(e),
                n = this.states[e - 1],
                r = this.tokenizer.getLineTokens(t, n, e);
            return this.states[e] + "" != r.state + "" ? (this.states[e] = r.state, this.lines[e + 1] = null, this.currentLine > e + 1 && (this.currentLine = e + 1)) : this.currentLine == e && (this.currentLine = e + 1), this.lines[e] = r.tokens
        }
    }).call(s.prototype), t.BackgroundTokenizer = s
}), define("ace/search_highlight", ["require", "exports", "module", "ace/lib/lang", "ace/lib/oop", "ace/range"], function(e, t, n) {
    "use strict";
    var r = e("./lib/lang"),
        i = e("./lib/oop"),
        s = e("./range").Range,
        o = function(e, t, n) {
            this.setRegexp(e), this.clazz = t, this.type = n || "text"
        };
    (function() {
        this.MAX_RANGES = 500, this.setRegexp = function(e) {
            if (this.regExp + "" == e + "") return;
            this.regExp = e, this.cache = []
        }, this.update = function(e, t, n, i) {
            if (!this.regExp) return;
            var o = i.firstRow,
                u = i.lastRow;
            for (var a = o; a <= u; a++) {
                var f = this.cache[a];
                f == null && (f = r.getMatchOffsets(n.getLine(a), this.regExp), f.length > this.MAX_RANGES && (f = f.slice(0, this.MAX_RANGES)), f = f.map(function(e) {
                    return new s(a, e.offset, a, e.offset + e.length)
                }), this.cache[a] = f.length ? f : "");
                for (var l = f.length; l--;) t.drawSingleLineMarker(e, f[l].toScreenRange(n), this.clazz, i)
            }
        }
    }).call(o.prototype), t.SearchHighlight = o
}), define("ace/edit_session/fold_line", ["require", "exports", "module", "ace/range"], function(e, t, n) {
    "use strict";

    function i(e, t) {
        this.foldData = e, Array.isArray(t) ? this.folds = t : t = this.folds = [t];
        var n = t[t.length - 1];
        this.range = new r(t[0].start.row, t[0].start.column, n.end.row, n.end.column), this.start = this.range.start, this.end = this.range.end, this.folds.forEach(function(e) {
            e.setFoldLine(this)
        }, this)
    }
    var r = e("../range").Range;
    (function() {
        this.shiftRow = function(e) {
            this.start.row += e, this.end.row += e, this.folds.forEach(function(t) {
                t.start.row += e, t.end.row += e
            })
        }, this.addFold = function(e) {
            if (e.sameRow) {
                if (e.start.row < this.startRow || e.endRow > this.endRow) throw new Error("Can't add a fold to this FoldLine as it has no connection");
                this.folds.push(e), this.folds.sort(function(e, t) {
                    return -e.range.compareEnd(t.start.row, t.start.column)
                }), this.range.compareEnd(e.start.row, e.start.column) > 0 ? (this.end.row = e.end.row, this.end.column = e.end.column) : this.range.compareStart(e.end.row, e.end.column) < 0 && (this.start.row = e.start.row, this.start.column = e.start.column)
            } else if (e.start.row == this.end.row) this.folds.push(e), this.end.row = e.end.row, this.end.column = e.end.column;
            else {
                if (e.end.row != this.start.row) throw new Error("Trying to add fold to FoldRow that doesn't have a matching row");
                this.folds.unshift(e), this.start.row = e.start.row, this.start.column = e.start.column
            }
            e.foldLine = this
        }, this.containsRow = function(e) {
            return e >= this.start.row && e <= this.end.row
        }, this.walk = function(e, t, n) {
            var r = 0,
                i = this.folds,
                s, o, u, a = !0;
            t == null && (t = this.end.row, n = this.end.column);
            for (var f = 0; f < i.length; f++) {
                s = i[f], o = s.range.compareStart(t, n);
                if (o == -1) {
                    e(null, t, n, r, a);
                    return
                }
                u = e(null, s.start.row, s.start.column, r, a), u = !u && e(s.placeholder, s.start.row, s.start.column, r);
                if (u || o === 0) return;
                a = !s.sameRow, r = s.end.column
            }
            e(null, t, n, r, a)
        }, this.getNextFoldTo = function(e, t) {
            var n, r;
            for (var i = 0; i < this.folds.length; i++) {
                n = this.folds[i], r = n.range.compareEnd(e, t);
                if (r == -1) return {
                    fold: n,
                    kind: "after"
                };
                if (r === 0) return {
                    fold: n,
                    kind: "inside"
                }
            }
            return null
        }, this.addRemoveChars = function(e, t, n) {
            var r = this.getNextFoldTo(e, t),
                i, s;
            if (r) {
                i = r.fold;
                if (r.kind == "inside" && i.start.column != t && i.start.row != e) window.console && window.console.log(e, t, i);
                else if (i.start.row == e) {
                    s = this.folds;
                    var o = s.indexOf(i);
                    o === 0 && (this.start.column += n);
                    for (o; o < s.length; o++) {
                        i = s[o], i.start.column += n;
                        if (!i.sameRow) return;
                        i.end.column += n
                    }
                    this.end.column += n
                }
            }
        }, this.split = function(e, t) {
            var n = this.getNextFoldTo(e, t);
            if (!n || n.kind == "inside") return null;
            var r = n.fold,
                s = this.folds,
                o = this.foldData,
                u = s.indexOf(r),
                a = s[u - 1];
            this.end.row = a.end.row, this.end.column = a.end.column, s = s.splice(u, s.length - u);
            var f = new i(o, s);
            return o.splice(o.indexOf(this) + 1, 0, f), f
        }, this.merge = function(e) {
            var t = e.folds;
            for (var n = 0; n < t.length; n++) this.addFold(t[n]);
            var r = this.foldData;
            r.splice(r.indexOf(e), 1)
        }, this.toString = function() {
            var e = [this.range.toString() + ": ["];
            return this.folds.forEach(function(t) {
                e.push("  " + t.toString())
            }), e.push("]"), e.join("\n")
        }, this.idxToPosition = function(e) {
            var t = 0;
            for (var n = 0; n < this.folds.length; n++) {
                var r = this.folds[n];
                e -= r.start.column - t;
                if (e < 0) return {
                    row: r.start.row,
                    column: r.start.column + e
                };
                e -= r.placeholder.length;
                if (e < 0) return r.start;
                t = r.end.column
            }
            return {
                row: this.end.row,
                column: this.end.column + e
            }
        }
    }).call(i.prototype), t.FoldLine = i
}), define("ace/range_list", ["require", "exports", "module", "ace/range"], function(e, t, n) {
    "use strict";
    var r = e("./range").Range,
        i = r.comparePoints,
        s = function() {
            this.ranges = []
        };
    (function() {
        this.comparePoints = i, this.pointIndex = function(e, t, n) {
            var r = this.ranges;
            for (var s = n || 0; s < r.length; s++) {
                var o = r[s],
                    u = i(e, o.end);
                if (u > 0) continue;
                var a = i(e, o.start);
                return u === 0 ? t && a !== 0 ? -s - 2 : s : a > 0 || a === 0 && !t ? s : -s - 1
            }
            return -s - 1
        }, this.add = function(e) {
            var t = !e.isEmpty(),
                n = this.pointIndex(e.start, t);
            n < 0 && (n = -n - 1);
            var r = this.pointIndex(e.end, t, n);
            return r < 0 ? r = -r - 1 : r++, this.ranges.splice(n, r - n, e)
        }, this.addList = function(e) {
            var t = [];
            for (var n = e.length; n--;) t.push.call(t, this.add(e[n]));
            return t
        }, this.substractPoint = function(e) {
            var t = this.pointIndex(e);
            if (t >= 0) return this.ranges.splice(t, 1)
        }, this.merge = function() {
            var e = [],
                t = this.ranges;
            t = t.sort(function(e, t) {
                return i(e.start, t.start)
            });
            var n = t[0],
                r;
            for (var s = 1; s < t.length; s++) {
                r = n, n = t[s];
                var o = i(r.end, n.start);
                if (o < 0) continue;
                if (o == 0 && !r.isEmpty() && !n.isEmpty()) continue;
                i(r.end, n.end) < 0 && (r.end.row = n.end.row, r.end.column = n.end.column), t.splice(s, 1), e.push(n), n = r, s--
            }
            return this.ranges = t, e
        }, this.contains = function(e, t) {
            return this.pointIndex({
                row: e,
                column: t
            }) >= 0
        }, this.containsPoint = function(e) {
            return this.pointIndex(e) >= 0
        }, this.rangeAtPoint = function(e) {
            var t = this.pointIndex(e);
            if (t >= 0) return this.ranges[t]
        }, this.clipRows = function(e, t) {
            var n = this.ranges;
            if (n[0].start.row > t || n[n.length - 1].start.row < e) return [];
            var r = this.pointIndex({
                row: e,
                column: 0
            });
            r < 0 && (r = -r - 1);
            var i = this.pointIndex({
                row: t,
                column: 0
            }, r);
            i < 0 && (i = -i - 1);
            var s = [];
            for (var o = r; o < i; o++) s.push(n[o]);
            return s
        }, this.removeAll = function() {
            return this.ranges.splice(0, this.ranges.length)
        }, this.attach = function(e) {
            this.session && this.detach(), this.session = e, this.onChange = this.$onChange.bind(this), this.session.on("change", this.onChange)
        }, this.detach = function() {
            if (!this.session) return;
            this.session.removeListener("change", this.onChange), this.session = null
        }, this.$onChange = function(e) {
            if (e.action == "insert") var t = e.start,
                n = e.end;
            else var n = e.start,
                t = e.end;
            var r = t.row,
                i = n.row,
                s = i - r,
                o = -t.column + n.column,
                u = this.ranges;
            for (var a = 0, f = u.length; a < f; a++) {
                var l = u[a];
                if (l.end.row < r) continue;
                if (l.start.row > r) break;
                l.start.row == r && l.start.column >= t.column && (l.start.column != t.column || !this.$insertRight) && (l.start.column += o, l.start.row += s);
                if (l.end.row == r && l.end.column >= t.column) {
                    if (l.end.column == t.column && this.$insertRight) continue;
                    l.end.column == t.column && o > 0 && a < f - 1 && l.end.column > l.start.column && l.end.column == u[a + 1].start.column && (l.end.column -= o), l.end.column += o, l.end.row += s
                }
            }
            if (s != 0 && a < f)
                for (; a < f; a++) {
                    var l = u[a];
                    l.start.row += s, l.end.row += s
                }
        }
    }).call(s.prototype), t.RangeList = s
}), define("ace/edit_session/fold", ["require", "exports", "module", "ace/range", "ace/range_list", "ace/lib/oop"], function(e, t, n) {
    "use strict";

    function u(e, t) {
        e.row -= t.row, e.row == 0 && (e.column -= t.column)
    }

    function a(e, t) {
        u(e.start, t), u(e.end, t)
    }

    function f(e, t) {
        e.row == 0 && (e.column += t.column), e.row += t.row
    }

    function l(e, t) {
        f(e.start, t), f(e.end, t)
    }
    var r = e("../range").Range,
        i = e("../range_list").RangeList,
        s = e("../lib/oop"),
        o = t.Fold = function(e, t) {
            this.foldLine = null, this.placeholder = t, this.range = e, this.start = e.start, this.end = e.end, this.sameRow = e.start.row == e.end.row, this.subFolds = this.ranges = []
        };
    s.inherits(o, i),
        function() {
            this.toString = function() {
                return '"' + this.placeholder + '" ' + this.range.toString()
            }, this.setFoldLine = function(e) {
                this.foldLine = e, this.subFolds.forEach(function(t) {
                    t.setFoldLine(e)
                })
            }, this.clone = function() {
                var e = this.range.clone(),
                    t = new o(e, this.placeholder);
                return this.subFolds.forEach(function(e) {
                    t.subFolds.push(e.clone())
                }), t.collapseChildren = this.collapseChildren, t
            }, this.addSubFold = function(e) {
                if (this.range.isEqual(e)) return;
                if (!this.range.containsRange(e)) throw new Error("A fold can't intersect already existing fold" + e.range + this.range);
                a(e, this.start);
                var t = e.start.row,
                    n = e.start.column;
                for (var r = 0, i = -1; r < this.subFolds.length; r++) {
                    i = this.subFolds[r].range.compare(t, n);
                    if (i != 1) break
                }
                var s = this.subFolds[r];
                if (i == 0) return s.addSubFold(e);
                var t = e.range.end.row,
                    n = e.range.end.column;
                for (var o = r, i = -1; o < this.subFolds.length; o++) {
                    i = this.subFolds[o].range.compare(t, n);
                    if (i != 1) break
                }
                var u = this.subFolds[o];
                if (i == 0) throw new Error("A fold can't intersect already existing fold" + e.range + this.range);
                var f = this.subFolds.splice(r, o - r, e);
                return e.setFoldLine(this.foldLine), e
            }, this.restoreRange = function(e) {
                return l(e, this.start)
            }
        }.call(o.prototype)
}), define("ace/edit_session/folding", ["require", "exports", "module", "ace/range", "ace/edit_session/fold_line", "ace/edit_session/fold", "ace/token_iterator"], function(e, t, n) {
    "use strict";

    function u() {
        this.getFoldAt = function(e, t, n) {
            var r = this.getFoldLine(e);
            if (!r) return null;
            var i = r.folds;
            for (var s = 0; s < i.length; s++) {
                var o = i[s];
                if (o.range.contains(e, t)) {
                    if (n == 1 && o.range.isEnd(e, t)) continue;
                    if (n == -1 && o.range.isStart(e, t)) continue;
                    return o
                }
            }
        }, this.getFoldsInRange = function(e) {
            var t = e.start,
                n = e.end,
                r = this.$foldData,
                i = [];
            t.column += 1, n.column -= 1;
            for (var s = 0; s < r.length; s++) {
                var o = r[s].range.compareRange(e);
                if (o == 2) continue;
                if (o == -2) break;
                var u = r[s].folds;
                for (var a = 0; a < u.length; a++) {
                    var f = u[a];
                    o = f.range.compareRange(e);
                    if (o == -2) break;
                    if (o == 2) continue;
                    if (o == 42) break;
                    i.push(f)
                }
            }
            return t.column -= 1, n.column += 1, i
        }, this.getFoldsInRangeList = function(e) {
            if (Array.isArray(e)) {
                var t = [];
                e.forEach(function(e) {
                    t = t.concat(this.getFoldsInRange(e))
                }, this)
            } else var t = this.getFoldsInRange(e);
            return t
        }, this.getAllFolds = function() {
            var e = [],
                t = this.$foldData;
            for (var n = 0; n < t.length; n++)
                for (var r = 0; r < t[n].folds.length; r++) e.push(t[n].folds[r]);
            return e
        }, this.getFoldStringAt = function(e, t, n, r) {
            r = r || this.getFoldLine(e);
            if (!r) return null;
            var i = {
                    end: {
                        column: 0
                    }
                },
                s, o;
            for (var u = 0; u < r.folds.length; u++) {
                o = r.folds[u];
                var a = o.range.compareEnd(e, t);
                if (a == -1) {
                    s = this.getLine(o.start.row).substring(i.end.column, o.start.column);
                    break
                }
                if (a === 0) return null;
                i = o
            }
            return s || (s = this.getLine(o.start.row).substring(i.end.column)), n == -1 ? s.substring(0, t - i.end.column) : n == 1 ? s.substring(t - i.end.column) : s
        }, this.getFoldLine = function(e, t) {
            var n = this.$foldData,
                r = 0;
            t && (r = n.indexOf(t)), r == -1 && (r = 0);
            for (r; r < n.length; r++) {
                var i = n[r];
                if (i.start.row <= e && i.end.row >= e) return i;
                if (i.end.row > e) return null
            }
            return null
        }, this.getNextFoldLine = function(e, t) {
            var n = this.$foldData,
                r = 0;
            t && (r = n.indexOf(t)), r == -1 && (r = 0);
            for (r; r < n.length; r++) {
                var i = n[r];
                if (i.end.row >= e) return i
            }
            return null
        }, this.getFoldedRowCount = function(e, t) {
            var n = this.$foldData,
                r = t - e + 1;
            for (var i = 0; i < n.length; i++) {
                var s = n[i],
                    o = s.end.row,
                    u = s.start.row;
                if (o >= t) {
                    u < t && (u >= e ? r -= t - u : r = 0);
                    break
                }
                o >= e && (u >= e ? r -= o - u : r -= o - e + 1)
            }
            return r
        }, this.$addFoldLine = function(e) {
            return this.$foldData.push(e), this.$foldData.sort(function(e, t) {
                return e.start.row - t.start.row
            }), e
        }, this.addFold = function(e, t) {
            var n = this.$foldData,
                r = !1,
                o;
            e instanceof s ? o = e : (o = new s(t, e), o.collapseChildren = t.collapseChildren), this.$clipRangeToDocument(o.range);
            var u = o.start.row,
                a = o.start.column,
                f = o.end.row,
                l = o.end.column;
            if (u < f || u == f && a <= l - 2) {
                var c = this.getFoldAt(u, a, 1),
                    h = this.getFoldAt(f, l, -1);
                if (c && h == c) return c.addSubFold(o);
                c && !c.range.isStart(u, a) && this.removeFold(c), h && !h.range.isEnd(f, l) && this.removeFold(h);
                var p = this.getFoldsInRange(o.range);
                p.length > 0 && (this.removeFolds(p), p.forEach(function(e) {
                    o.addSubFold(e)
                }));
                for (var d = 0; d < n.length; d++) {
                    var v = n[d];
                    if (f == v.start.row) {
                        v.addFold(o), r = !0;
                        break
                    }
                    if (u == v.end.row) {
                        v.addFold(o), r = !0;
                        if (!o.sameRow) {
                            var m = n[d + 1];
                            if (m && m.start.row == f) {
                                v.merge(m);
                                break
                            }
                        }
                        break
                    }
                    if (f <= v.start.row) break
                }
                return r || (v = this.$addFoldLine(new i(this.$foldData, o))), this.$useWrapMode ? this.$updateWrapData(v.start.row, v.start.row) : this.$updateRowLengthCache(v.start.row, v.start.row), this.$modified = !0, this._emit("changeFold", {
                    data: o,
                    action: "add"
                }), o
            }
            throw new Error("The range has to be at least 2 characters width")
        }, this.addFolds = function(e) {
            e.forEach(function(e) {
                this.addFold(e)
            }, this)
        }, this.removeFold = function(e) {
            var t = e.foldLine,
                n = t.start.row,
                r = t.end.row,
                i = this.$foldData,
                s = t.folds;
            if (s.length == 1) i.splice(i.indexOf(t), 1);
            else if (t.range.isEnd(e.end.row, e.end.column)) s.pop(), t.end.row = s[s.length - 1].end.row, t.end.column = s[s.length - 1].end.column;
            else if (t.range.isStart(e.start.row, e.start.column)) s.shift(), t.start.row = s[0].start.row, t.start.column = s[0].start.column;
            else if (e.sameRow) s.splice(s.indexOf(e), 1);
            else {
                var o = t.split(e.start.row, e.start.column);
                s = o.folds, s.shift(), o.start.row = s[0].start.row, o.start.column = s[0].start.column
            }
            this.$updating || (this.$useWrapMode ? this.$updateWrapData(n, r) : this.$updateRowLengthCache(n, r)), this.$modified = !0, this._emit("changeFold", {
                data: e,
                action: "remove"
            })
        }, this.removeFolds = function(e) {
            var t = [];
            for (var n = 0; n < e.length; n++) t.push(e[n]);
            t.forEach(function(e) {
                this.removeFold(e)
            }, this), this.$modified = !0
        }, this.expandFold = function(e) {
            this.removeFold(e), e.subFolds.forEach(function(t) {
                e.restoreRange(t), this.addFold(t)
            }, this), e.collapseChildren > 0 && this.foldAll(e.start.row + 1, e.end.row, e.collapseChildren - 1), e.subFolds = []
        }, this.expandFolds = function(e) {
            e.forEach(function(e) {
                this.expandFold(e)
            }, this)
        }, this.unfold = function(e, t) {
            var n, i;
            e == null ? (n = new r(0, 0, this.getLength(), 0), t = !0) : typeof e == "number" ? n = new r(e, 0, e, this.getLine(e).length) : "row" in e ? n = r.fromPoints(e, e) : n = e, i = this.getFoldsInRangeList(n);
            if (t) this.removeFolds(i);
            else {
                var s = i;
                while (s.length) this.expandFolds(s), s = this.getFoldsInRangeList(n)
            }
            if (i.length) return i
        }, this.isRowFolded = function(e, t) {
            return !!this.getFoldLine(e, t)
        }, this.getRowFoldEnd = function(e, t) {
            var n = this.getFoldLine(e, t);
            return n ? n.end.row : e
        }, this.getRowFoldStart = function(e, t) {
            var n = this.getFoldLine(e, t);
            return n ? n.start.row : e
        }, this.getFoldDisplayLine = function(e, t, n, r, i) {
            r == null && (r = e.start.row), i == null && (i = 0), t == null && (t = e.end.row), n == null && (n = this.getLine(t).length);
            var s = this.doc,
                o = "";
            return e.walk(function(e, t, n, u) {
                if (t < r) return;
                if (t == r) {
                    if (n < i) return;
                    u = Math.max(i, u)
                }
                e != null ? o += e : o += s.getLine(t).substring(u, n)
            }, t, n), o
        }, this.getDisplayLine = function(e, t, n, r) {
            var i = this.getFoldLine(e);
            if (!i) {
                var s;
                return s = this.doc.getLine(e), s.substring(r || 0, t || s.length)
            }
            return this.getFoldDisplayLine(i, e, t, n, r)
        }, this.$cloneFoldData = function() {
            var e = [];
            return e = this.$foldData.map(function(t) {
                var n = t.folds.map(function(e) {
                    return e.clone()
                });
                return new i(e, n)
            }), e
        }, this.toggleFold = function(e) {
            var t = this.selection,
                n = t.getRange(),
                r, i;
            if (n.isEmpty()) {
                var s = n.start;
                r = this.getFoldAt(s.row, s.column);
                if (r) {
                    this.expandFold(r);
                    return
                }(i = this.findMatchingBracket(s)) ? n.comparePoint(i) == 1 ? n.end = i : (n.start = i, n.start.column++, n.end.column--): (i = this.findMatchingBracket({
                    row: s.row,
                    column: s.column + 1
                })) ? (n.comparePoint(i) == 1 ? n.end = i : n.start = i, n.start.column++) : n = this.getCommentFoldRange(s.row, s.column) || n
            } else {
                var o = this.getFoldsInRange(n);
                if (e && o.length) {
                    this.expandFolds(o);
                    return
                }
                o.length == 1 && (r = o[0])
            }
            r || (r = this.getFoldAt(n.start.row, n.start.column));
            if (r && r.range.toString() == n.toString()) {
                this.expandFold(r);
                return
            }
            var u = "...";
            if (!n.isMultiLine()) {
                u = this.getTextRange(n);
                if (u.length < 4) return;
                u = u.trim().substring(0, 2) + ".."
            }
            this.addFold(u, n)
        }, this.getCommentFoldRange = function(e, t, n) {
            var i = new o(this, e, t),
                s = i.getCurrentToken();
            if (s && /^comment|string/.test(s.type)) {
                var u = new r,
                    a = new RegExp(s.type.replace(/\..*/, "\\."));
                if (n != 1) {
                    do s = i.stepBackward(); while (s && a.test(s.type));
                    i.stepForward()
                }
                u.start.row = i.getCurrentTokenRow(), u.start.column = i.getCurrentTokenColumn() + 2, i = new o(this, e, t);
                if (n != -1) {
                    do s = i.stepForward(); while (s && a.test(s.type));
                    s = i.stepBackward()
                } else s = i.getCurrentToken();
                return u.end.row = i.getCurrentTokenRow(), u.end.column = i.getCurrentTokenColumn() + s.value.length - 2, u
            }
        }, this.foldAll = function(e, t, n) {
            n == undefined && (n = 1e5);
            var r = this.foldWidgets;
            if (!r) return;
            t = t || this.getLength(), e = e || 0;
            for (var i = e; i < t; i++) {
                r[i] == null && (r[i] = this.getFoldWidget(i));
                if (r[i] != "start") continue;
                var s = this.getFoldWidgetRange(i);
                if (s && s.isMultiLine() && s.end.row <= t && s.start.row >= e) {
                    i = s.end.row;
                    try {
                        var o = this.addFold("...", s);
                        o && (o.collapseChildren = n)
                    } catch (u) {}
                }
            }
        }, this.$foldStyles = {
            manual: 1,
            markbegin: 1,
            markbeginend: 1
        }, this.$foldStyle = "markbegin", this.setFoldStyle = function(e) {
            if (!this.$foldStyles[e]) throw new Error("invalid fold style: " + e + "[" + Object.keys(this.$foldStyles).join(", ") + "]");
            if (this.$foldStyle == e) return;
            this.$foldStyle = e, e == "manual" && this.unfold();
            var t = this.$foldMode;
            this.$setFolding(null), this.$setFolding(t)
        }, this.$setFolding = function(e) {
            if (this.$foldMode == e) return;
            this.$foldMode = e, this.off("change", this.$updateFoldWidgets), this.off("tokenizerUpdate", this.$tokenizerUpdateFoldWidgets), this._emit("changeAnnotation");
            if (!e || this.$foldStyle == "manual") {
                this.foldWidgets = null;
                return
            }
            this.foldWidgets = [], this.getFoldWidget = e.getFoldWidget.bind(e, this, this.$foldStyle), this.getFoldWidgetRange = e.getFoldWidgetRange.bind(e, this, this.$foldStyle), this.$updateFoldWidgets = this.updateFoldWidgets.bind(this), this.$tokenizerUpdateFoldWidgets = this.tokenizerUpdateFoldWidgets.bind(this), this.on("change", this.$updateFoldWidgets), this.on("tokenizerUpdate", this.$tokenizerUpdateFoldWidgets)
        }, this.getParentFoldRangeData = function(e, t) {
            var n = this.foldWidgets;
            if (!n || t && n[e]) return {};
            var r = e - 1,
                i;
            while (r >= 0) {
                var s = n[r];
                s == null && (s = n[r] = this.getFoldWidget(r));
                if (s == "start") {
                    var o = this.getFoldWidgetRange(r);
                    i || (i = o);
                    if (o && o.end.row >= e) break
                }
                r--
            }
            return {
                range: r !== -1 && o,
                firstRange: i
            }
        }, this.onFoldWidgetClick = function(e, t) {
            t = t.domEvent;
            var n = {
                    children: t.shiftKey,
                    all: t.ctrlKey || t.metaKey,
                    siblings: t.altKey
                },
                r = this.$toggleFoldWidget(e, n);
            if (!r) {
                var i = t.target || t.srcElement;
                i && /ace_fold-widget/.test(i.className) && (i.className += " ace_invalid")
            }
        }, this.$toggleFoldWidget = function(e, t) {
            if (!this.getFoldWidget) return;
            var n = this.getFoldWidget(e),
                r = this.getLine(e),
                i = n === "end" ? -1 : 1,
                s = this.getFoldAt(e, i === -1 ? 0 : r.length, i);
            if (s) {
                t.children || t.all ? this.removeFold(s) : this.expandFold(s);
                return
            }
            var o = this.getFoldWidgetRange(e, !0);
            if (o && !o.isMultiLine()) {
                s = this.getFoldAt(o.start.row, o.start.column, 1);
                if (s && o.isEqual(s.range)) {
                    this.removeFold(s);
                    return
                }
            }
            if (t.siblings) {
                var u = this.getParentFoldRangeData(e);
                if (u.range) var a = u.range.start.row + 1,
                    f = u.range.end.row;
                this.foldAll(a, f, t.all ? 1e4 : 0)
            } else t.children ? (f = o ? o.end.row : this.getLength(), this.foldAll(e + 1, f, t.all ? 1e4 : 0)) : o && (t.all && (o.collapseChildren = 1e4), this.addFold("...", o));
            return o
        }, this.toggleFoldWidget = function(e) {
            var t = this.selection.getCursor().row;
            t = this.getRowFoldStart(t);
            var n = this.$toggleFoldWidget(t, {});
            if (n) return;
            var r = this.getParentFoldRangeData(t, !0);
            n = r.range || r.firstRange;
            if (n) {
                t = n.start.row;
                var i = this.getFoldAt(t, this.getLine(t).length, 1);
                i ? this.removeFold(i) : this.addFold("...", n)
            }
        }, this.updateFoldWidgets = function(e) {
            var t = e.start.row,
                n = e.end.row - t;
            if (n === 0) this.foldWidgets[t] = null;
            else if (e.action == "remove") this.foldWidgets.splice(t, n + 1, null);
            else {
                var r = Array(n + 1);
                r.unshift(t, 1), this.foldWidgets.splice.apply(this.foldWidgets, r)
            }
        }, this.tokenizerUpdateFoldWidgets = function(e) {
            var t = e.data;
            t.first != t.last && this.foldWidgets.length > t.first && this.foldWidgets.splice(t.first, this.foldWidgets.length)
        }
    }
    var r = e("../range").Range,
        i = e("./fold_line").FoldLine,
        s = e("./fold").Fold,
        o = e("../token_iterator").TokenIterator;
    t.Folding = u
}), define("ace/edit_session/bracket_match", ["require", "exports", "module", "ace/token_iterator", "ace/range"], function(e, t, n) {
    "use strict";

    function s() {
        this.findMatchingBracket = function(e, t) {
            if (e.column == 0) return null;
            var n = t || this.getLine(e.row).charAt(e.column - 1);
            if (n == "") return null;
            var r = n.match(/([\(\[\{])|([\)\]\}])/);
            return r ? r[1] ? this.$findClosingBracket(r[1], e) : this.$findOpeningBracket(r[2], e) : null
        }, this.getBracketRange = function(e) {
            var t = this.getLine(e.row),
                n = !0,
                r, s = t.charAt(e.column - 1),
                o = s && s.match(/([\(\[\{])|([\)\]\}])/);
            o || (s = t.charAt(e.column), e = {
                row: e.row,
                column: e.column + 1
            }, o = s && s.match(/([\(\[\{])|([\)\]\}])/), n = !1);
            if (!o) return null;
            if (o[1]) {
                var u = this.$findClosingBracket(o[1], e);
                if (!u) return null;
                r = i.fromPoints(e, u), n || (r.end.column++, r.start.column--), r.cursor = r.end
            } else {
                var u = this.$findOpeningBracket(o[2], e);
                if (!u) return null;
                r = i.fromPoints(u, e), n || (r.start.column++, r.end.column--), r.cursor = r.start
            }
            return r
        }, this.$brackets = {
            ")": "(",
            "(": ")",
            "]": "[",
            "[": "]",
            "{": "}",
            "}": "{"
        }, this.$findOpeningBracket = function(e, t, n) {
            var i = this.$brackets[e],
                s = 1,
                o = new r(this, t.row, t.column),
                u = o.getCurrentToken();
            u || (u = o.stepForward());
            if (!u) return;
            n || (n = new RegExp("(\\.?" + u.type.replace(".", "\\.").replace("rparen", ".paren").replace(/\b(?:end)\b/, "(?:start|begin|end)") + ")+"));
            var a = t.column - o.getCurrentTokenColumn() - 2,
                f = u.value;
            for (;;) {
                while (a >= 0) {
                    var l = f.charAt(a);
                    if (l == i) {
                        s -= 1;
                        if (s == 0) return {
                            row: o.getCurrentTokenRow(),
                            column: a + o.getCurrentTokenColumn()
                        }
                    } else l == e && (s += 1);
                    a -= 1
                }
                do u = o.stepBackward(); while (u && !n.test(u.type));
                if (u == null) break;
                f = u.value, a = f.length - 1
            }
            return null
        }, this.$findClosingBracket = function(e, t, n) {
            var i = this.$brackets[e],
                s = 1,
                o = new r(this, t.row, t.column),
                u = o.getCurrentToken();
            u || (u = o.stepForward());
            if (!u) return;
            n || (n = new RegExp("(\\.?" + u.type.replace(".", "\\.").replace("lparen", ".paren").replace(/\b(?:start|begin)\b/, "(?:start|begin|end)") + ")+"));
            var a = t.column - o.getCurrentTokenColumn();
            for (;;) {
                var f = u.value,
                    l = f.length;
                while (a < l) {
                    var c = f.charAt(a);
                    if (c == i) {
                        s -= 1;
                        if (s == 0) return {
                            row: o.getCurrentTokenRow(),
                            column: a + o.getCurrentTokenColumn()
                        }
                    } else c == e && (s += 1);
                    a += 1
                }
                do u = o.stepForward(); while (u && !n.test(u.type));
                if (u == null) break;
                a = 0
            }
            return null
        }
    }
    var r = e("../token_iterator").TokenIterator,
        i = e("../range").Range;
    t.BracketMatch = s
}), define("ace/edit_session", ["require", "exports", "module", "ace/lib/oop", "ace/lib/lang", "ace/config", "ace/lib/event_emitter", "ace/selection", "ace/mode/text", "ace/range", "ace/document", "ace/background_tokenizer", "ace/search_highlight", "ace/edit_session/folding", "ace/edit_session/bracket_match"], function(e, t, n) {
    "use strict";
    var r = e("./lib/oop"),
        i = e("./lib/lang"),
        s = e("./config"),
        o = e("./lib/event_emitter").EventEmitter,
        u = e("./selection").Selection,
        a = e("./mode/text").Mode,
        f = e("./range").Range,
        l = e("./document").Document,
        c = e("./background_tokenizer").BackgroundTokenizer,
        h = e("./search_highlight").SearchHighlight,
        p = function(e, t) {
            this.$breakpoints = [], this.$decorations = [], this.$frontMarkers = {}, this.$backMarkers = {}, this.$markerId = 1, this.$undoSelect = !0, this.$foldData = [], this.$foldData.toString = function() {
                return this.join("\n")
            }, this.on("changeFold", this.onChangeFold.bind(this)), this.$onChange = this.onChange.bind(this);
            if (typeof e != "object" || !e.getLine) e = new l(e);
            this.setDocument(e), this.selection = new u(this), s.resetOptions(this), this.setMode(t), s._signal("session", this)
        };
    (function() {
        function m(e) {
            return e < 4352 ? !1 : e >= 4352 && e <= 4447 || e >= 4515 && e <= 4519 || e >= 4602 && e <= 4607 || e >= 9001 && e <= 9002 || e >= 11904 && e <= 11929 || e >= 11931 && e <= 12019 || e >= 12032 && e <= 12245 || e >= 12272 && e <= 12283 || e >= 12288 && e <= 12350 || e >= 12353 && e <= 12438 || e >= 12441 && e <= 12543 || e >= 12549 && e <= 12589 || e >= 12593 && e <= 12686 || e >= 12688 && e <= 12730 || e >= 12736 && e <= 12771 || e >= 12784 && e <= 12830 || e >= 12832 && e <= 12871 || e >= 12880 && e <= 13054 || e >= 13056 && e <= 19903 || e >= 19968 && e <= 42124 || e >= 42128 && e <= 42182 || e >= 43360 && e <= 43388 || e >= 44032 && e <= 55203 || e >= 55216 && e <= 55238 || e >= 55243 && e <= 55291 || e >= 63744 && e <= 64255 || e >= 65040 && e <= 65049 || e >= 65072 && e <= 65106 || e >= 65108 && e <= 65126 || e >= 65128 && e <= 65131 || e >= 65281 && e <= 65376 || e >= 65504 && e <= 65510
        }
        r.implement(this, o), this.setDocument = function(e) {
            this.doc && this.doc.removeListener("change", this.$onChange), this.doc = e, e.on("change", this.$onChange), this.bgTokenizer && this.bgTokenizer.setDocument(this.getDocument()), this.resetCaches()
        }, this.getDocument = function() {
            return this.doc
        }, this.$resetRowCache = function(e) {
            if (!e) {
                this.$docRowCache = [], this.$screenRowCache = [];
                return
            }
            var t = this.$docRowCache.length,
                n = this.$getRowCacheIndex(this.$docRowCache, e) + 1;
            t > n && (this.$docRowCache.splice(n, t), this.$screenRowCache.splice(n, t))
        }, this.$getRowCacheIndex = function(e, t) {
            var n = 0,
                r = e.length - 1;
            while (n <= r) {
                var i = n + r >> 1,
                    s = e[i];
                if (t > s) n = i + 1;
                else {
                    if (!(t < s)) return i;
                    r = i - 1
                }
            }
            return n - 1
        }, this.resetCaches = function() {
            this.$modified = !0, this.$wrapData = [], this.$rowLengthCache = [], this.$resetRowCache(0), this.bgTokenizer && this.bgTokenizer.start(0)
        }, this.onChangeFold = function(e) {
            var t = e.data;
            this.$resetRowCache(t.start.row)
        }, this.onChange = function(e) {
            this.$modified = !0, this.$resetRowCache(e.start.row);
            var t = this.$updateInternalDataOnChange(e);
            !this.$fromUndo && this.$undoManager && !e.ignore && (this.$deltasDoc.push(e), t && t.length != 0 && this.$deltasFold.push({
                action: "removeFolds",
                folds: t
            }), this.$informUndoManager.schedule()), this.bgTokenizer && this.bgTokenizer.$updateOnChange(e), this._signal("change", e)
        }, this.setValue = function(e) {
            this.doc.setValue(e), this.selection.moveTo(0, 0), this.$resetRowCache(0), this.$deltas = [], this.$deltasDoc = [], this.$deltasFold = [], this.setUndoManager(this.$undoManager), this.getUndoManager().reset()
        }, this.getValue = this.toString = function() {
            return this.doc.getValue()
        }, this.getSelection = function() {
            return this.selection
        }, this.getState = function(e) {
            return this.bgTokenizer.getState(e)
        }, this.getTokens = function(e) {
            return this.bgTokenizer.getTokens(e)
        }, this.getTokenAt = function(e, t) {
            var n = this.bgTokenizer.getTokens(e),
                r, i = 0;
            if (t == null) s = n.length - 1, i = this.getLine(e).length;
            else
                for (var s = 0; s < n.length; s++) {
                    i += n[s].value.length;
                    if (i >= t) break
                }
            return r = n[s], r ? (r.index = s, r.start = i - r.value.length, r) : null
        }, this.setUndoManager = function(e) {
            this.$undoManager = e, this.$deltas = [], this.$deltasDoc = [], this.$deltasFold = [], this.$informUndoManager && this.$informUndoManager.cancel();
            if (e) {
                var t = this;
                this.$syncInformUndoManager = function() {
                    t.$informUndoManager.cancel(), t.$deltasFold.length && (t.$deltas.push({
                        group: "fold",
                        deltas: t.$deltasFold
                    }), t.$deltasFold = []), t.$deltasDoc.length && (t.$deltas.push({
                        group: "doc",
                        deltas: t.$deltasDoc
                    }), t.$deltasDoc = []), t.$deltas.length > 0 && e.execute({
                        action: "aceupdate",
                        args: [t.$deltas, t],
                        merge: t.mergeUndoDeltas
                    }), t.mergeUndoDeltas = !1, t.$deltas = []
                }, this.$informUndoManager = i.delayedCall(this.$syncInformUndoManager)
            }
        }, this.markUndoGroup = function() {
            this.$syncInformUndoManager && this.$syncInformUndoManager()
        }, this.$defaultUndoManager = {
            undo: function() {},
            redo: function() {},
            reset: function() {}
        }, this.getUndoManager = function() {
            return this.$undoManager || this.$defaultUndoManager
        }, this.getTabString = function() {
            return this.getUseSoftTabs() ? i.stringRepeat(" ", this.getTabSize()) : "   "
        }, this.setUseSoftTabs = function(e) {
            this.setOption("useSoftTabs", e)
        }, this.getUseSoftTabs = function() {
            return this.$useSoftTabs && !this.$mode.$indentWithTabs
        }, this.setTabSize = function(e) {
            this.setOption("tabSize", e)
        }, this.getTabSize = function() {
            return this.$tabSize
        }, this.isTabStop = function(e) {
            return this.$useSoftTabs && e.column % this.$tabSize === 0
        }, this.$overwrite = !1, this.setOverwrite = function(e) {
            this.setOption("overwrite", e)
        }, this.getOverwrite = function() {
            return this.$overwrite
        }, this.toggleOverwrite = function() {
            this.setOverwrite(!this.$overwrite)
        }, this.addGutterDecoration = function(e, t) {
            this.$decorations[e] || (this.$decorations[e] = ""), this.$decorations[e] += " " + t, this._signal("changeBreakpoint", {})
        }, this.removeGutterDecoration = function(e, t) {
            this.$decorations[e] = (this.$decorations[e] || "").replace(" " + t, ""), this._signal("changeBreakpoint", {})
        }, this.getBreakpoints = function() {
            return this.$breakpoints
        }, this.setBreakpoints = function(e) {
            this.$breakpoints = [];
            for (var t = 0; t < e.length; t++) this.$breakpoints[e[t]] = "ace_breakpoint";
            this._signal("changeBreakpoint", {})
        }, this.clearBreakpoints = function() {
            this.$breakpoints = [], this._signal("changeBreakpoint", {})
        }, this.setBreakpoint = function(e, t) {
            t === undefined && (t = "ace_breakpoint"), t ? this.$breakpoints[e] = t : delete this.$breakpoints[e], this._signal("changeBreakpoint", {})
        }, this.clearBreakpoint = function(e) {
            delete this.$breakpoints[e], this._signal("changeBreakpoint", {})
        }, this.addMarker = function(e, t, n, r) {
            var i = this.$markerId++,
                s = {
                    range: e,
                    type: n || "line",
                    renderer: typeof n == "function" ? n : null,
                    clazz: t,
                    inFront: !!r,
                    id: i
                };
            return r ? (this.$frontMarkers[i] = s, this._signal("changeFrontMarker")) : (this.$backMarkers[i] = s, this._signal("changeBackMarker")), i
        }, this.addDynamicMarker = function(e, t) {
            if (!e.update) return;
            var n = this.$markerId++;
            return e.id = n, e.inFront = !!t, t ? (this.$frontMarkers[n] = e, this._signal("changeFrontMarker")) : (this.$backMarkers[n] = e, this._signal("changeBackMarker")), e
        }, this.removeMarker = function(e) {
            var t = this.$frontMarkers[e] || this.$backMarkers[e];
            if (!t) return;
            var n = t.inFront ? this.$frontMarkers : this.$backMarkers;
            t && (delete n[e], this._signal(t.inFront ? "changeFrontMarker" : "changeBackMarker"))
        }, this.getMarkers = function(e) {
            return e ? this.$frontMarkers : this.$backMarkers
        }, this.highlight = function(e) {
            if (!this.$searchHighlight) {
                var t = new h(null, "ace_selected-word", "text");
                this.$searchHighlight = this.addDynamicMarker(t)
            }
            this.$searchHighlight.setRegexp(e)
        }, this.highlightLines = function(e, t, n, r) {
            typeof t != "number" && (n = t, t = e), n || (n = "ace_step");
            var i = new f(e, 0, t, Infinity);
            return i.id = this.addMarker(i, n, "fullLine", r), i
        }, this.setAnnotations = function(e) {
            this.$annotations = e, this._signal("changeAnnotation", {})
        }, this.getAnnotations = function() {
            return this.$annotations || []
        }, this.clearAnnotations = function() {
            this.setAnnotations([])
        }, this.$detectNewLine = function(e) {
            var t = e.match(/^.*?(\r?\n)/m);
            t ? this.$autoNewLine = t[1] : this.$autoNewLine = "\n"
        }, this.getWordRange = function(e, t) {
            var n = this.getLine(e),
                r = !1;
            t > 0 && (r = !!n.charAt(t - 1).match(this.tokenRe)), r || (r = !!n.charAt(t).match(this.tokenRe));
            if (r) var i = this.tokenRe;
            else if (/^\s+$/.test(n.slice(t - 1, t + 1))) var i = /\s/;
            else var i = this.nonTokenRe;
            var s = t;
            if (s > 0) {
                do s--; while (s >= 0 && n.charAt(s).match(i));
                s++
            }
            var o = t;
            while (o < n.length && n.charAt(o).match(i)) o++;
            return new f(e, s, e, o)
        }, this.getAWordRange = function(e, t) {
            var n = this.getWordRange(e, t),
                r = this.getLine(n.end.row);
            while (r.charAt(n.end.column).match(/[ \t]/)) n.end.column += 1;
            return n
        }, this.setNewLineMode = function(e) {
            this.doc.setNewLineMode(e)
        }, this.getNewLineMode = function() {
            return this.doc.getNewLineMode()
        }, this.setUseWorker = function(e) {
            this.setOption("useWorker", e)
        }, this.getUseWorker = function() {
            return this.$useWorker
        }, this.onReloadTokenizer = function(e) {
            var t = e.data;
            this.bgTokenizer.start(t.first), this._signal("tokenizerUpdate", e)
        }, this.$modes = {}, this.$mode = null, this.$modeId = null, this.setMode = function(e, t) {
            if (e && typeof e == "object") {
                if (e.getTokenizer) return this.$onChangeMode(e);
                var n = e,
                    r = n.path
            } else r = e || "ace/mode/text";
            this.$modes["ace/mode/text"] || (this.$modes["ace/mode/text"] = new a);
            if (this.$modes[r] && !n) {
                this.$onChangeMode(this.$modes[r]), t && t();
                return
            }
            this.$modeId = r, s.loadModule(["mode", r], function(e) {
                if (this.$modeId !== r) return t && t();
                this.$modes[r] && !n ? this.$onChangeMode(this.$modes[r]) : e && e.Mode && (e = new e.Mode(n), n || (this.$modes[r] = e, e.$id = r), this.$onChangeMode(e)), t && t()
            }.bind(this)), this.$mode || this.$onChangeMode(this.$modes["ace/mode/text"], !0)
        }, this.$onChangeMode = function(e, t) {
            t || (this.$modeId = e.$id);
            if (this.$mode === e) return;
            this.$mode = e, this.$stopWorker(), this.$useWorker && this.$startWorker();
            var n = e.getTokenizer();
            if (n.addEventListener !== undefined) {
                var r = this.onReloadTokenizer.bind(this);
                n.addEventListener("update", r)
            }
            if (!this.bgTokenizer) {
                this.bgTokenizer = new c(n);
                var i = this;
                this.bgTokenizer.addEventListener("update", function(e) {
                    i._signal("tokenizerUpdate", e)
                })
            } else this.bgTokenizer.setTokenizer(n);
            this.bgTokenizer.setDocument(this.getDocument()), this.tokenRe = e.tokenRe, this.nonTokenRe = e.nonTokenRe, t || (e.attachToSession && e.attachToSession(this), this.$options.wrapMethod.set.call(this, this.$wrapMethod), this.$setFolding(e.foldingRules), this.bgTokenizer.start(0), this._emit("changeMode"))
        }, this.$stopWorker = function() {
            this.$worker && (this.$worker.terminate(), this.$worker = null)
        }, this.$startWorker = function() {
            try {
                this.$worker = this.$mode.createWorker(this)
            } catch (e) {
                s.warn("Could not load worker", e), this.$worker = null
            }
        }, this.getMode = function() {
            return this.$mode
        }, this.$scrollTop = 0, this.setScrollTop = function(e) {
            if (this.$scrollTop === e || isNaN(e)) return;
            this.$scrollTop = e, this._signal("changeScrollTop", e)
        }, this.getScrollTop = function() {
            return this.$scrollTop
        }, this.$scrollLeft = 0, this.setScrollLeft = function(e) {
            if (this.$scrollLeft === e || isNaN(e)) return;
            this.$scrollLeft = e, this._signal("changeScrollLeft", e)
        }, this.getScrollLeft = function() {
            return this.$scrollLeft
        }, this.getScreenWidth = function() {
            return this.$computeWidth(), this.lineWidgets ? Math.max(this.getLineWidgetMaxWidth(), this.screenWidth) : this.screenWidth
        }, this.getLineWidgetMaxWidth = function() {
            if (this.lineWidgetsWidth != null) return this.lineWidgetsWidth;
            var e = 0;
            return this.lineWidgets.forEach(function(t) {
                t && t.screenWidth > e && (e = t.screenWidth)
            }), this.lineWidgetWidth = e
        }, this.$computeWidth = function(e) {
            if (this.$modified || e) {
                this.$modified = !1;
                if (this.$useWrapMode) return this.screenWidth = this.$wrapLimit;
                var t = this.doc.getAllLines(),
                    n = this.$rowLengthCache,
                    r = 0,
                    i = 0,
                    s = this.$foldData[i],
                    o = s ? s.start.row : Infinity,
                    u = t.length;
                for (var a = 0; a < u; a++) {
                    if (a > o) {
                        a = s.end.row + 1;
                        if (a >= u) break;
                        s = this.$foldData[i++], o = s ? s.start.row : Infinity
                    }
                    n[a] == null && (n[a] = this.$getStringScreenWidth(t[a])[0]), n[a] > r && (r = n[a])
                }
                this.screenWidth = r
            }
        }, this.getLine = function(e) {
            return this.doc.getLine(e)
        }, this.getLines = function(e, t) {
            return this.doc.getLines(e, t)
        }, this.getLength = function() {
            return this.doc.getLength()
        }, this.getTextRange = function(e) {
            return this.doc.getTextRange(e || this.selection.getRange())
        }, this.insert = function(e, t) {
            return this.doc.insert(e, t)
        }, this.remove = function(e) {
            return this.doc.remove(e)
        }, this.removeFullLines = function(e, t) {
            return this.doc.removeFullLines(e, t)
        }, this.undoChanges = function(e, t) {
            if (!e.length) return;
            this.$fromUndo = !0;
            var n = null;
            for (var r = e.length - 1; r != -1; r--) {
                var i = e[r];
                i.group == "doc" ? (this.doc.revertDeltas(i.deltas), n = this.$getUndoSelection(i.deltas, !0, n)) : i.deltas.forEach(function(e) {
                    this.addFolds(e.folds)
                }, this)
            }
            return this.$fromUndo = !1, n && this.$undoSelect && !t && this.selection.setSelectionRange(n), n
        }, this.redoChanges = function(e, t) {
            if (!e.length) return;
            this.$fromUndo = !0;
            var n = null;
            for (var r = 0; r < e.length; r++) {
                var i = e[r];
                i.group == "doc" && (this.doc.applyDeltas(i.deltas), n = this.$getUndoSelection(i.deltas, !1, n))
            }
            return this.$fromUndo = !1, n && this.$undoSelect && !t && this.selection.setSelectionRange(n), n
        }, this.setUndoSelect = function(e) {
            this.$undoSelect = e
        }, this.$getUndoSelection = function(e, t, n) {
            function r(e) {
                return t ? e.action !== "insert" : e.action === "insert"
            }
            var i = e[0],
                s, o, u = !1;
            r(i) ? (s = f.fromPoints(i.start, i.end), u = !0) : (s = f.fromPoints(i.start, i.start), u = !1);
            for (var a = 1; a < e.length; a++) i = e[a], r(i) ? (o = i.start, s.compare(o.row, o.column) == -1 && s.setStart(o), o = i.end, s.compare(o.row, o.column) == 1 && s.setEnd(o), u = !0) : (o = i.start, s.compare(o.row, o.column) == -1 && (s = f.fromPoints(i.start, i.start)), u = !1);
            if (n != null) {
                f.comparePoints(n.start, s.start) === 0 && (n.start.column += s.end.column - s.start.column, n.end.column += s.end.column - s.start.column);
                var l = n.compareRange(s);
                l == 1 ? s.setStart(n.start) : l == -1 && s.setEnd(n.end)
            }
            return s
        }, this.replace = function(e, t) {
            return this.doc.replace(e, t)
        }, this.moveText = function(e, t, n) {
            var r = this.getTextRange(e),
                i = this.getFoldsInRange(e),
                s = f.fromPoints(t, t);
            if (!n) {
                this.remove(e);
                var o = e.start.row - e.end.row,
                    u = o ? -e.end.column : e.start.column - e.end.column;
                u && (s.start.row == e.end.row && s.start.column > e.end.column && (s.start.column += u), s.end.row == e.end.row && s.end.column > e.end.column && (s.end.column += u)), o && s.start.row >= e.end.row && (s.start.row += o, s.end.row += o)
            }
            s.end = this.insert(s.start, r);
            if (i.length) {
                var a = e.start,
                    l = s.start,
                    o = l.row - a.row,
                    u = l.column - a.column;
                this.addFolds(i.map(function(e) {
                    return e = e.clone(), e.start.row == a.row && (e.start.column += u), e.end.row == a.row && (e.end.column += u), e.start.row += o, e.end.row += o, e
                }))
            }
            return s
        }, this.indentRows = function(e, t, n) {
            n = n.replace(/\t/g, this.getTabString());
            for (var r = e; r <= t; r++) this.doc.insertInLine({
                row: r,
                column: 0
            }, n)
        }, this.outdentRows = function(e) {
            var t = e.collapseRows(),
                n = new f(0, 0, 0, 0),
                r = this.getTabSize();
            for (var i = t.start.row; i <= t.end.row; ++i) {
                var s = this.getLine(i);
                n.start.row = i, n.end.row = i;
                for (var o = 0; o < r; ++o)
                    if (s.charAt(o) != " ") break;
                o < r && s.charAt(o) == "   " ? (n.start.column = o, n.end.column = o + 1) : (n.start.column = 0, n.end.column = o), this.remove(n)
            }
        }, this.$moveLines = function(e, t, n) {
            e = this.getRowFoldStart(e), t = this.getRowFoldEnd(t);
            if (n < 0) {
                var r = this.getRowFoldStart(e + n);
                if (r < 0) return 0;
                var i = r - e
            } else if (n > 0) {
                var r = this.getRowFoldEnd(t + n);
                if (r > this.doc.getLength() - 1) return 0;
                var i = r - t
            } else {
                e = this.$clipRowToDocument(e), t = this.$clipRowToDocument(t);
                var i = t - e + 1
            }
            var s = new f(e, 0, t, Number.MAX_VALUE),
                o = this.getFoldsInRange(s).map(function(e) {
                    return e = e.clone(), e.start.row += i, e.end.row += i, e
                }),
                u = n == 0 ? this.doc.getLines(e, t) : this.doc.removeFullLines(e, t);
            return this.doc.insertFullLines(e + i, u), o.length && this.addFolds(o), i
        }, this.moveLinesUp = function(e, t) {
            return this.$moveLines(e, t, -1)
        }, this.moveLinesDown = function(e, t) {
            return this.$moveLines(e, t, 1)
        }, this.duplicateLines = function(e, t) {
            return this.$moveLines(e, t, 0)
        }, this.$clipRowToDocument = function(e) {
            return Math.max(0, Math.min(e, this.doc.getLength() - 1))
        }, this.$clipColumnToRow = function(e, t) {
            return t < 0 ? 0 : Math.min(this.doc.getLine(e).length, t)
        }, this.$clipPositionToDocument = function(e, t) {
            t = Math.max(0, t);
            if (e < 0) e = 0, t = 0;
            else {
                var n = this.doc.getLength();
                e >= n ? (e = n - 1, t = this.doc.getLine(n - 1).length) : t = Math.min(this.doc.getLine(e).length, t)
            }
            return {
                row: e,
                column: t
            }
        }, this.$clipRangeToDocument = function(e) {
            e.start.row < 0 ? (e.start.row = 0, e.start.column = 0) : e.start.column = this.$clipColumnToRow(e.start.row, e.start.column);
            var t = this.doc.getLength() - 1;
            return e.end.row > t ? (e.end.row = t, e.end.column = this.doc.getLine(t).length) : e.end.column = this.$clipColumnToRow(e.end.row, e.end.column), e
        }, this.$wrapLimit = 80, this.$useWrapMode = !1, this.$wrapLimitRange = {
            min: null,
            max: null
        }, this.setUseWrapMode = function(e) {
            if (e != this.$useWrapMode) {
                this.$useWrapMode = e, this.$modified = !0, this.$resetRowCache(0);
                if (e) {
                    var t = this.getLength();
                    this.$wrapData = Array(t), this.$updateWrapData(0, t - 1)
                }
                this._signal("changeWrapMode")
            }
        }, this.getUseWrapMode = function() {
            return this.$useWrapMode
        }, this.setWrapLimitRange = function(e, t) {
            if (this.$wrapLimitRange.min !== e || this.$wrapLimitRange.max !== t) this.$wrapLimitRange = {
                min: e,
                max: t
            }, this.$modified = !0, this.$useWrapMode && this._signal("changeWrapMode")
        }, this.adjustWrapLimit = function(e, t) {
            var n = this.$wrapLimitRange;
            n.max < 0 && (n = {
                min: t,
                max: t
            });
            var r = this.$constrainWrapLimit(e, n.min, n.max);
            return r != this.$wrapLimit && r > 1 ? (this.$wrapLimit = r, this.$modified = !0, this.$useWrapMode && (this.$updateWrapData(0, this.getLength() - 1), this.$resetRowCache(0), this._signal("changeWrapLimit")), !0) : !1
        }, this.$constrainWrapLimit = function(e, t, n) {
            return t && (e = Math.max(t, e)), n && (e = Math.min(n, e)), e
        }, this.getWrapLimit = function() {
            return this.$wrapLimit
        }, this.setWrapLimit = function(e) {
            this.setWrapLimitRange(e, e)
        }, this.getWrapLimitRange = function() {
            return {
                min: this.$wrapLimitRange.min,
                max: this.$wrapLimitRange.max
            }
        }, this.$updateInternalDataOnChange = function(e) {
            var t = this.$useWrapMode,
                n = e.action,
                r = e.start,
                i = e.end,
                s = r.row,
                o = i.row,
                u = o - s,
                a = null;
            this.$updating = !0;
            if (u != 0)
                if (n === "remove") {
                    this[t ? "$wrapData" : "$rowLengthCache"].splice(s, u);
                    var f = this.$foldData;
                    a = this.getFoldsInRange(e), this.removeFolds(a);
                    var l = this.getFoldLine(i.row),
                        c = 0;
                    if (l) {
                        l.addRemoveChars(i.row, i.column, r.column - i.column), l.shiftRow(-u);
                        var h = this.getFoldLine(s);
                        h && h !== l && (h.merge(l), l = h), c = f.indexOf(l) + 1
                    }
                    for (c; c < f.length; c++) {
                        var l = f[c];
                        l.start.row >= i.row && l.shiftRow(-u)
                    }
                    o = s
                } else {
                    var p = Array(u);
                    p.unshift(s, 0);
                    var d = t ? this.$wrapData : this.$rowLengthCache;
                    d.splice.apply(d, p);
                    var f = this.$foldData,
                        l = this.getFoldLine(s),
                        c = 0;
                    if (l) {
                        var v = l.range.compareInside(r.row, r.column);
                        v == 0 ? (l = l.split(r.row, r.column), l && (l.shiftRow(u), l.addRemoveChars(o, 0, i.column - r.column))) : v == -1 && (l.addRemoveChars(s, 0, i.column - r.column), l.shiftRow(u)), c = f.indexOf(l) + 1
                    }
                    for (c; c < f.length; c++) {
                        var l = f[c];
                        l.start.row >= s && l.shiftRow(u)
                    }
                } else {
                u = Math.abs(e.start.column - e.end.column), n === "remove" && (a = this.getFoldsInRange(e), this.removeFolds(a), u = -u);
                var l = this.getFoldLine(s);
                l && l.addRemoveChars(s, r.column, u)
            }
            return t && this.$wrapData.length != this.doc.getLength() && console.error("doc.getLength() and $wrapData.length have to be the same!"), this.$updating = !1, t ? this.$updateWrapData(s, o) : this.$updateRowLengthCache(s, o), a
        }, this.$updateRowLengthCache = function(e, t, n) {
            this.$rowLengthCache[e] = null, this.$rowLengthCache[t] = null
        }, this.$updateWrapData = function(e, t) {
            var r = this.doc.getAllLines(),
                i = this.getTabSize(),
                s = this.$wrapData,
                o = this.$wrapLimit,
                a, f, l = e;
            t = Math.min(t, r.length - 1);
            while (l <= t) f = this.getFoldLine(l, f), f ? (a = [], f.walk(function(e, t, i, s) {
                var o;
                if (e != null) {
                    o = this.$getDisplayTokens(e, a.length), o[0] = n;
                    for (var f = 1; f < o.length; f++) o[f] = u
                } else o = this.$getDisplayTokens(r[t].substring(s, i), a.length);
                a = a.concat(o)
            }.bind(this), f.end.row, r[f.end.row].length + 1), s[f.start.row] = this.$computeWrapSplits(a, o, i), l = f.end.row + 1) : (a = this.$getDisplayTokens(r[l]), s[l] = this.$computeWrapSplits(a, o, i), l++)
        };
        var e = 1,
            t = 2,
            n = 3,
            u = 4,
            l = 9,
            p = 10,
            d = 11,
            v = 12;
        this.$computeWrapSplits = function(e, r, i) {
            function g() {
                var t = 0;
                if (m === 0) return t;
                if (h)
                    for (var n = 0; n < e.length; n++) {
                        var r = e[n];
                        if (r == p) t += 1;
                        else {
                            if (r != d) {
                                if (r == v) continue;
                                break
                            }
                            t += i
                        }
                    }
                return c && h !== !1 && (t += i), Math.min(t, m)
            }

            function y(t) {
                var n = e.slice(a, t),
                    r = n.length;
                n.join("").replace(/12/g, function() {
                    r -= 1
                }).replace(/2/g, function() {
                    r -= 1
                }), s.length || (b = g(), s.indent = b), f += r, s.push(f), a = t
            }
            if (e.length == 0) return [];
            var s = [],
                o = e.length,
                a = 0,
                f = 0,
                c = this.$wrapAsCode,
                h = this.$indentedSoftWrap,
                m = r <= Math.max(2 * i, 8) || h === !1 ? 0 : Math.floor(r / 2),
                b = 0;
            while (o - a > r - b) {
                var w = a + r - b;
                if (e[w - 1] >= p && e[w] >= p) {
                    y(w);
                    continue
                }
                if (e[w] == n || e[w] == u) {
                    for (w; w != a - 1; w--)
                        if (e[w] == n) break;
                    if (w > a) {
                        y(w);
                        continue
                    }
                    w = a + r;
                    for (w; w < e.length; w++)
                        if (e[w] != u) break;
                    if (w == e.length) break;
                    y(w);
                    continue
                }
                var E = Math.max(w - (r - (r >> 2)), a - 1);
                while (w > E && e[w] < n) w--;
                if (c) {
                    while (w > E && e[w] < n) w--;
                    while (w > E && e[w] == l) w--
                } else
                    while (w > E && e[w] < p) w--;
                if (w > E) {
                    y(++w);
                    continue
                }
                w = a + r, e[w] == t && w--, y(w - b)
            }
            return s
        }, this.$getDisplayTokens = function(n, r) {
            var i = [],
                s;
            r = r || 0;
            for (var o = 0; o < n.length; o++) {
                var u = n.charCodeAt(o);
                if (u == 9) {
                    s = this.getScreenTabSize(i.length + r), i.push(d);
                    for (var a = 1; a < s; a++) i.push(v)
                } else u == 32 ? i.push(p) : u > 39 && u < 48 || u > 57 && u < 64 ? i.push(l) : u >= 4352 && m(u) ? i.push(e, t) : i.push(e)
            }
            return i
        }, this.$getStringScreenWidth = function(e, t, n) {
            if (t == 0) return [0, 0];
            t == null && (t = Infinity), n = n || 0;
            var r, i;
            for (i = 0; i < e.length; i++) {
                r = e.charCodeAt(i), r == 9 ? n += this.getScreenTabSize(n) : r >= 4352 && m(r) ? n += 2 : n += 1;
                if (n > t) break
            }
            return [n, i]
        }, this.lineWidgets = null, this.getRowLength = function(e) {
            if (this.lineWidgets) var t = this.lineWidgets[e] && this.lineWidgets[e].rowCount || 0;
            else t = 0;
            return !this.$useWrapMode || !this.$wrapData[e] ? 1 + t : this.$wrapData[e].length + 1 + t
        }, this.getRowLineCount = function(e) {
            return !this.$useWrapMode || !this.$wrapData[e] ? 1 : this.$wrapData[e].length + 1
        }, this.getRowWrapIndent = function(e) {
            if (this.$useWrapMode) {
                var t = this.screenToDocumentPosition(e, Number.MAX_VALUE),
                    n = this.$wrapData[t.row];
                return n.length && n[0] < t.column ? n.indent : 0
            }
            return 0
        }, this.getScreenLastRowColumn = function(e) {
            var t = this.screenToDocumentPosition(e, Number.MAX_VALUE);
            return this.documentToScreenColumn(t.row, t.column)
        }, this.getDocumentLastRowColumn = function(e, t) {
            var n = this.documentToScreenRow(e, t);
            return this.getScreenLastRowColumn(n)
        }, this.getDocumentLastRowColumnPosition = function(e, t) {
            var n = this.documentToScreenRow(e, t);
            return this.screenToDocumentPosition(n, Number.MAX_VALUE / 10)
        }, this.getRowSplitData = function(e) {
            return this.$useWrapMode ? this.$wrapData[e] : undefined
        }, this.getScreenTabSize = function(e) {
            return this.$tabSize - e % this.$tabSize
        }, this.screenToDocumentRow = function(e, t) {
            return this.screenToDocumentPosition(e, t).row
        }, this.screenToDocumentColumn = function(e, t) {
            return this.screenToDocumentPosition(e, t).column
        }, this.screenToDocumentPosition = function(e, t) {
            if (e < 0) return {
                row: 0,
                column: 0
            };
            var n, r = 0,
                i = 0,
                s, o = 0,
                u = 0,
                a = this.$screenRowCache,
                f = this.$getRowCacheIndex(a, e),
                l = a.length;
            if (l && f >= 0) var o = a[f],
                r = this.$docRowCache[f],
                c = e > a[l - 1];
            else var c = !l;
            var h = this.getLength() - 1,
                p = this.getNextFoldLine(r),
                d = p ? p.start.row : Infinity;
            while (o <= e) {
                u = this.getRowLength(r);
                if (o + u > e || r >= h) break;
                o += u, r++, r > d && (r = p.end.row + 1, p = this.getNextFoldLine(r, p), d = p ? p.start.row : Infinity), c && (this.$docRowCache.push(r), this.$screenRowCache.push(o))
            }
            if (p && p.start.row <= r) n = this.getFoldDisplayLine(p), r = p.start.row;
            else {
                if (o + u <= e || r > h) return {
                    row: h,
                    column: this.getLine(h).length
                };
                n = this.getLine(r), p = null
            }
            var v = 0;
            if (this.$useWrapMode) {
                var m = this.$wrapData[r];
                if (m) {
                    var g = Math.floor(e - o);
                    s = m[g], g > 0 && m.length && (v = m.indent, i = m[g - 1] || m[m.length - 1], n = n.substring(i))
                }
            }
            return i += this.$getStringScreenWidth(n, t - v)[1], this.$useWrapMode && i >= s && (i = s - 1), p ? p.idxToPosition(i) : {
                row: r,
                column: i
            }
        }, this.documentToScreenPosition = function(e, t) {
            if (typeof t == "undefined") var n = this.$clipPositionToDocument(e.row, e.column);
            else n = this.$clipPositionToDocument(e, t);
            e = n.row, t = n.column;
            var r = 0,
                i = null,
                s = null;
            s = this.getFoldAt(e, t, 1), s && (e = s.start.row, t = s.start.column);
            var o, u = 0,
                a = this.$docRowCache,
                f = this.$getRowCacheIndex(a, e),
                l = a.length;
            if (l && f >= 0) var u = a[f],
                r = this.$screenRowCache[f],
                c = e > a[l - 1];
            else var c = !l;
            var h = this.getNextFoldLine(u),
                p = h ? h.start.row : Infinity;
            while (u < e) {
                if (u >= p) {
                    o = h.end.row + 1;
                    if (o > e) break;
                    h = this.getNextFoldLine(o, h), p = h ? h.start.row : Infinity
                } else o = u + 1;
                r += this.getRowLength(u), u = o, c && (this.$docRowCache.push(u), this.$screenRowCache.push(r))
            }
            var d = "";
            h && u >= p ? (d = this.getFoldDisplayLine(h, e, t), i = h.start.row) : (d = this.getLine(e).substring(0, t), i = e);
            var v = 0;
            if (this.$useWrapMode) {
                var m = this.$wrapData[i];
                if (m) {
                    var g = 0;
                    while (d.length >= m[g]) r++, g++;
                    d = d.substring(m[g - 1] || 0, d.length), v = g > 0 ? m.indent : 0
                }
            }
            return {
                row: r,
                column: v + this.$getStringScreenWidth(d)[0]
            }
        }, this.documentToScreenColumn = function(e, t) {
            return this.documentToScreenPosition(e, t).column
        }, this.documentToScreenRow = function(e, t) {
            return this.documentToScreenPosition(e, t).row
        }, this.getScreenLength = function() {
            var e = 0,
                t = null;
            if (!this.$useWrapMode) {
                e = this.getLength();
                var n = this.$foldData;
                for (var r = 0; r < n.length; r++) t = n[r], e -= t.end.row - t.start.row
            } else {
                var i = this.$wrapData.length,
                    s = 0,
                    r = 0,
                    t = this.$foldData[r++],
                    o = t ? t.start.row : Infinity;
                while (s < i) {
                    var u = this.$wrapData[s];
                    e += u ? u.length + 1 : 1, s++, s > o && (s = t.end.row + 1, t = this.$foldData[r++], o = t ? t.start.row : Infinity)
                }
            }
            return this.lineWidgets && (e += this.$getWidgetScreenLength()), e
        }, this.$setFontMetrics = function(e) {}, this.destroy = function() {
            this.bgTokenizer && (this.bgTokenizer.setDocument(null), this.bgTokenizer = null), this.$stopWorker()
        }
    }).call(p.prototype), e("./edit_session/folding").Folding.call(p.prototype), e("./edit_session/bracket_match").BracketMatch.call(p.prototype), s.defineOptions(p.prototype, "session", {
        wrap: {
            set: function(e) {
                !e || e == "off" ? e = !1 : e == "free" ? e = !0 : e == "printMargin" ? e = -1 : typeof e == "string" && (e = parseInt(e, 10) || !1);
                if (this.$wrap == e) return;
                this.$wrap = e;
                if (!e) this.setUseWrapMode(!1);
                else {
                    var t = typeof e == "number" ? e : null;
                    this.setWrapLimitRange(t, t), this.setUseWrapMode(!0)
                }
            },
            get: function() {
                return this.getUseWrapMode() ? this.$wrap == -1 ? "printMargin" : this.getWrapLimitRange().min ? this.$wrap : "free" : "off"
            },
            handlesSet: !0
        },
        wrapMethod: {
            set: function(e) {
                e = e == "auto" ? this.$mode.type != "text" : e != "text", e != this.$wrapAsCode && (this.$wrapAsCode = e, this.$useWrapMode && (this.$modified = !0, this.$resetRowCache(0), this.$updateWrapData(0, this.getLength() - 1)))
            },
            initialValue: "auto"
        },
        indentedSoftWrap: {
            initialValue: !0
        },
        firstLineNumber: {
            set: function() {
                this._signal("changeBreakpoint")
            },
            initialValue: 1
        },
        useWorker: {
            set: function(e) {
                this.$useWorker = e, this.$stopWorker(), e && this.$startWorker()
            },
            initialValue: !0
        },
        useSoftTabs: {
            initialValue: !0
        },
        tabSize: {
            set: function(e) {
                if (isNaN(e) || this.$tabSize === e) return;
                this.$modified = !0, this.$rowLengthCache = [], this.$tabSize = e, this._signal("changeTabSize")
            },
            initialValue: 4,
            handlesSet: !0
        },
        overwrite: {
            set: function(e) {
                this._signal("changeOverwrite")
            },
            initialValue: !1
        },
        newLineMode: {
            set: function(e) {
                this.doc.setNewLineMode(e)
            },
            get: function() {
                return this.doc.getNewLineMode()
            },
            handlesSet: !0
        },
        mode: {
            set: function(e) {
                this.setMode(e)
            },
            get: function() {
                return this.$modeId
            }
        }
    }), t.EditSession = p
}), define("ace/search", ["require", "exports", "module", "ace/lib/lang", "ace/lib/oop", "ace/range"], function(e, t, n) {
    "use strict";
    var r = e("./lib/lang"),
        i = e("./lib/oop"),
        s = e("./range").Range,
        o = function() {
            this.$options = {}
        };
    (function() {
        this.set = function(e) {
            return i.mixin(this.$options, e), this
        }, this.getOptions = function() {
            return r.copyObject(this.$options)
        }, this.setOptions = function(e) {
            this.$options = e
        }, this.find = function(e) {
            var t = this.$options,
                n = this.$matchIterator(e, t);
            if (!n) return !1;
            var r = null;
            return n.forEach(function(e, n, i) {
                if (!e.start) {
                    var o = e.offset + (i || 0);
                    r = new s(n, o, n, o + e.length);
                    if (!e.length && t.start && t.start.start && t.skipCurrent != 0 && r.isEqual(t.start)) return r = null, !1
                } else r = e;
                return !0
            }), r
        }, this.findAll = function(e) {
            var t = this.$options;
            if (!t.needle) return [];
            this.$assembleRegExp(t);
            var n = t.range,
                i = n ? e.getLines(n.start.row, n.end.row) : e.doc.getAllLines(),
                o = [],
                u = t.re;
            if (t.$isMultiLine) {
                var a = u.length,
                    f = i.length - a,
                    l;
                e: for (var c = u.offset || 0; c <= f; c++) {
                    for (var h = 0; h < a; h++)
                        if (i[c + h].search(u[h]) == -1) continue e;
                    var p = i[c],
                        d = i[c + a - 1],
                        v = p.length - p.match(u[0])[0].length,
                        m = d.match(u[a - 1])[0].length;
                    if (l && l.end.row === c && l.end.column > v) continue;
                    o.push(l = new s(c, v, c + a - 1, m)), a > 2 && (c = c + a - 2)
                }
            } else
                for (var g = 0; g < i.length; g++) {
                    var y = r.getMatchOffsets(i[g], u);
                    for (var h = 0; h < y.length; h++) {
                        var b = y[h];
                        o.push(new s(g, b.offset, g, b.offset + b.length))
                    }
                }
            if (n) {
                var w = n.start.column,
                    E = n.start.column,
                    g = 0,
                    h = o.length - 1;
                while (g < h && o[g].start.column < w && o[g].start.row == n.start.row) g++;
                while (g < h && o[h].end.column > E && o[h].end.row == n.end.row) h--;
                o = o.slice(g, h + 1);
                for (g = 0, h = o.length; g < h; g++) o[g].start.row += n.start.row, o[g].end.row += n.start.row
            }
            return o
        }, this.replace = function(e, t) {
            var n = this.$options,
                r = this.$assembleRegExp(n);
            if (n.$isMultiLine) return t;
            if (!r) return;
            var i = r.exec(e);
            if (!i || i[0].length != e.length) return null;
            t = e.replace(r, t);
            if (n.preserveCase) {
                t = t.split("");
                for (var s = Math.min(e.length, e.length); s--;) {
                    var o = e[s];
                    o && o.toLowerCase() != o ? t[s] = t[s].toUpperCase() : t[s] = t[s].toLowerCase()
                }
                t = t.join("")
            }
            return t
        }, this.$matchIterator = function(e, t) {
            var n = this.$assembleRegExp(t);
            if (!n) return !1;
            var i;
            if (t.$isMultiLine) var o = n.length,
                u = function(t, r, u) {
                    var a = t.search(n[0]);
                    if (a == -1) return;
                    for (var f = 1; f < o; f++) {
                        t = e.getLine(r + f);
                        if (t.search(n[f]) == -1) return
                    }
                    var l = t.match(n[o - 1])[0].length,
                        c = new s(r, a, r + o - 1, l);
                    n.offset == 1 ? (c.start.row--, c.start.column = Number.MAX_VALUE) : u && (c.start.column += u);
                    if (i(c)) return !0
                };
            else if (t.backwards) var u = function(e, t, s) {
                var o = r.getMatchOffsets(e, n);
                for (var u = o.length - 1; u >= 0; u--)
                    if (i(o[u], t, s)) return !0
            };
            else var u = function(e, t, s) {
                var o = r.getMatchOffsets(e, n);
                for (var u = 0; u < o.length; u++)
                    if (i(o[u], t, s)) return !0
            };
            var a = this.$lineIterator(e, t);
            return {
                forEach: function(e) {
                    i = e, a.forEach(u)
                }
            }
        }, this.$assembleRegExp = function(e, t) {
            if (e.needle instanceof RegExp) return e.re = e.needle;
            var n = e.needle;
            if (!e.needle) return e.re = !1;
            e.regExp || (n = r.escapeRegExp(n)), e.wholeWord && (n = "\\b" + n + "\\b");
            var i = e.caseSensitive ? "gm" : "gmi";
            e.$isMultiLine = !t && /[\n\r]/.test(n);
            if (e.$isMultiLine) return e.re = this.$assembleMultilineRegExp(n, i);
            try {
                var s = new RegExp(n, i)
            } catch (o) {
                s = !1
            }
            return e.re = s
        }, this.$assembleMultilineRegExp = function(e, t) {
            var n = e.replace(/\r\n|\r|\n/g, "$\n^").split("\n"),
                r = [];
            for (var i = 0; i < n.length; i++) try {
                r.push(new RegExp(n[i], t))
            } catch (s) {
                return !1
            }
            return n[0] == "" ? (r.shift(), r.offset = 1) : r.offset = 0, r
        }, this.$lineIterator = function(e, t) {
            var n = t.backwards == 1,
                r = t.skipCurrent != 0,
                i = t.range,
                s = t.start;
            s || (s = i ? i[n ? "end" : "start"] : e.selection.getRange()), s.start && (s = s[r != n ? "end" : "start"]);
            var o = i ? i.start.row : 0,
                u = i ? i.end.row : e.getLength() - 1,
                a = n ? function(n) {
                    var r = s.row,
                        i = e.getLine(r).substring(0, s.column);
                    if (n(i, r)) return;
                    for (r--; r >= o; r--)
                        if (n(e.getLine(r), r)) return;
                    if (t.wrap == 0) return;
                    for (r = u, o = s.row; r >= o; r--)
                        if (n(e.getLine(r), r)) return
                } : function(n) {
                    var r = s.row,
                        i = e.getLine(r).substr(s.column);
                    if (n(i, r, s.column)) return;
                    for (r += 1; r <= u; r++)
                        if (n(e.getLine(r), r)) return;
                    if (t.wrap == 0) return;
                    for (r = o, u = s.row; r <= u; r++)
                        if (n(e.getLine(r), r)) return
                };
            return {
                forEach: a
            }
        }
    }).call(o.prototype), t.Search = o
}), define("ace/keyboard/hash_handler", ["require", "exports", "module", "ace/lib/keys", "ace/lib/useragent"], function(e, t, n) {
    "use strict";

    function o(e, t) {
        this.platform = t || (i.isMac ? "mac" : "win"), this.commands = {}, this.commandKeyBinding = {}, this.addCommands(e), this.$singleCommand = !0
    }

    function u(e, t) {
        o.call(this, e, t), this.$singleCommand = !1
    }
    var r = e("../lib/keys"),
        i = e("../lib/useragent"),
        s = r.KEY_MODS;
    u.prototype = o.prototype,
        function() {
            function e(e) {
                return typeof e == "object" && e.bindKey && e.bindKey.position || 0
            }
            this.addCommand = function(e) {
                this.commands[e.name] && this.removeCommand(e), this.commands[e.name] = e, e.bindKey && this._buildKeyHash(e)
            }, this.removeCommand = function(e, t) {
                var n = e && (typeof e == "string" ? e : e.name);
                e = this.commands[n], t || delete this.commands[n];
                var r = this.commandKeyBinding;
                for (var i in r) {
                    var s = r[i];
                    if (s == e) delete r[i];
                    else if (Array.isArray(s)) {
                        var o = s.indexOf(e);
                        o != -1 && (s.splice(o, 1), s.length == 1 && (r[i] = s[0]))
                    }
                }
            }, this.bindKey = function(e, t, n) {
                typeof e == "object" && (n == undefined && (n = e.position), e = e[this.platform]);
                if (!e) return;
                if (typeof t == "function") return this.addCommand({
                    exec: t,
                    bindKey: e,
                    name: t.name || e
                });
                e.split("|").forEach(function(e) {
                    var r = "";
                    if (e.indexOf(" ") != -1) {
                        var i = e.split(/\s+/);
                        e = i.pop(), i.forEach(function(e) {
                            var t = this.parseKeys(e),
                                n = s[t.hashId] + t.key;
                            r += (r ? " " : "") + n, this._addCommandToBinding(r, "chainKeys")
                        }, this), r += " "
                    }
                    var o = this.parseKeys(e),
                        u = s[o.hashId] + o.key;
                    this._addCommandToBinding(r + u, t, n)
                }, this)
            }, this._addCommandToBinding = function(t, n, r) {
                var i = this.commandKeyBinding,
                    s;
                if (!n) delete i[t];
                else if (!i[t] || this.$singleCommand) i[t] = n;
                else {
                    Array.isArray(i[t]) ? (s = i[t].indexOf(n)) != -1 && i[t].splice(s, 1) : i[t] = [i[t]], typeof r != "number" && (r || n.isDefault ? r = -100 : r = e(n));
                    var o = i[t];
                    for (s = 0; s < o.length; s++) {
                        var u = o[s],
                            a = e(u);
                        if (a > r) break
                    }
                    o.splice(s, 0, n)
                }
            }, this.addCommands = function(e) {
                e && Object.keys(e).forEach(function(t) {
                    var n = e[t];
                    if (!n) return;
                    if (typeof n == "string") return this.bindKey(n, t);
                    typeof n == "function" && (n = {
                        exec: n
                    });
                    if (typeof n != "object") return;
                    n.name || (n.name = t), this.addCommand(n)
                }, this)
            }, this.removeCommands = function(e) {
                Object.keys(e).forEach(function(t) {
                    this.removeCommand(e[t])
                }, this)
            }, this.bindKeys = function(e) {
                Object.keys(e).forEach(function(t) {
                    this.bindKey(t, e[t])
                }, this)
            }, this._buildKeyHash = function(e) {
                this.bindKey(e.bindKey, e)
            }, this.parseKeys = function(e) {
                var t = e.toLowerCase().split(/[\-\+]([\-\+])?/).filter(function(e) {
                        return e
                    }),
                    n = t.pop(),
                    i = r[n];
                if (r.FUNCTION_KEYS[i]) n = r.FUNCTION_KEYS[i].toLowerCase();
                else {
                    if (!t.length) return {
                        key: n,
                        hashId: -1
                    };
                    if (t.length == 1 && t[0] == "shift") return {
                        key: n.toUpperCase(),
                        hashId: -1
                    }
                }
                var s = 0;
                for (var o = t.length; o--;) {
                    var u = r.KEY_MODS[t[o]];
                    if (u == null) return typeof console != "undefined" && console.error("invalid modifier " + t[o] + " in " + e), !1;
                    s |= u
                }
                return {
                    key: n,
                    hashId: s
                }
            }, this.findKeyCommand = function(t, n) {
                var r = s[t] + n;
                return this.commandKeyBinding[r]
            }, this.handleKeyboard = function(e, t, n, r) {
                var i = s[t] + n,
                    o = this.commandKeyBinding[i];
                e.$keyChain && (e.$keyChain += " " + i, o = this.commandKeyBinding[e.$keyChain] || o);
                if (o)
                    if (o == "chainKeys" || o[o.length - 1] == "chainKeys") return e.$keyChain = e.$keyChain || i, {
                        command: "null"
                    };
                if (e.$keyChain)
                    if (!!t && t != 4 || n.length != 1) {
                        if (t == -1 || r > 0) e.$keyChain = ""
                    } else e.$keyChain = e.$keyChain.slice(0, -i.length - 1);
                return {
                    command: o
                }
            }, this.getStatusText = function(e, t) {
                return t.$keyChain || ""
            }
        }.call(o.prototype), t.HashHandler = o, t.MultiHashHandler = u
}), define("ace/commands/command_manager", ["require", "exports", "module", "ace/lib/oop", "ace/keyboard/hash_handler", "ace/lib/event_emitter"], function(e, t, n) {
    "use strict";
    var r = e("../lib/oop"),
        i = e("../keyboard/hash_handler").MultiHashHandler,
        s = e("../lib/event_emitter").EventEmitter,
        o = function(e, t) {
            i.call(this, t, e), this.byName = this.commands, this.setDefaultHandler("exec", function(e) {
                return e.command.exec(e.editor, e.args || {})
            })
        };
    r.inherits(o, i),
        function() {
            r.implement(this, s), this.exec = function(e, t, n) {
                if (Array.isArray(e)) {
                    for (var r = e.length; r--;)
                        if (this.exec(e[r], t, n)) return !0;
                    return !1
                }
                typeof e == "string" && (e = this.commands[e]);
                if (!e) return !1;
                if (t && t.$readOnly && !e.readOnly) return !1;
                var i = {
                    editor: t,
                    command: e,
                    args: n
                };
                return i.returnValue = this._emit("exec", i), this._signal("afterExec", i), i.returnValue === !1 ? !1 : !0
            }, this.toggleRecording = function(e) {
                if (this.$inReplay) return;
                return e && e._emit("changeStatus"), this.recording ? (this.macro.pop(), this.removeEventListener("exec", this.$addCommandToMacro), this.macro.length || (this.macro = this.oldMacro), this.recording = !1) : (this.$addCommandToMacro || (this.$addCommandToMacro = function(e) {
                    this.macro.push([e.command, e.args])
                }.bind(this)), this.oldMacro = this.macro, this.macro = [], this.on("exec", this.$addCommandToMacro), this.recording = !0)
            }, this.replay = function(e) {
                if (this.$inReplay || !this.macro) return;
                if (this.recording) return this.toggleRecording(e);
                try {
                    this.$inReplay = !0, this.macro.forEach(function(t) {
                        typeof t == "string" ? this.exec(t, e) : this.exec(t[0], e, t[1])
                    }, this)
                } finally {
                    this.$inReplay = !1
                }
            }, this.trimMacro = function(e) {
                return e.map(function(e) {
                    return typeof e[0] != "string" && (e[0] = e[0].name), e[1] || (e = e[0]), e
                })
            }
        }.call(o.prototype), t.CommandManager = o
}), define("ace/commands/default_commands", ["require", "exports", "module", "ace/lib/lang", "ace/config", "ace/range"], function(e, t, n) {
    "use strict";

    function o(e, t) {
        return {
            win: e,
            mac: t
        }
    }
    var r = e("../lib/lang"),
        i = e("../config"),
        s = e("../range").Range;
    t.commands = [{
        name: "showSettingsMenu",
        bindKey: o("Ctrl-,", "Command-,"),
        exec: function(e) {
            i.loadModule("ace/ext/settings_menu", function(t) {
                t.init(e), e.showSettingsMenu()
            })
        },
        readOnly: !0
    }, {
        name: "goToNextError",
        bindKey: o("Alt-E", "Ctrl-E"),
        exec: function(e) {
            i.loadModule("ace/ext/error_marker", function(t) {
                t.showErrorMarker(e, 1)
            })
        },
        scrollIntoView: "animate",
        readOnly: !0
    }, {
        name: "goToPreviousError",
        bindKey: o("Alt-Shift-E", "Ctrl-Shift-E"),
        exec: function(e) {
            i.loadModule("ace/ext/error_marker", function(t) {
                t.showErrorMarker(e, -1)
            })
        },
        scrollIntoView: "animate",
        readOnly: !0
    }, {
        name: "selectall",
        bindKey: o("Ctrl-A", "Command-A"),
        exec: function(e) {
            e.selectAll()
        },
        readOnly: !0
    }, {
        name: "centerselection",
        bindKey: o(null, "Ctrl-L"),
        exec: function(e) {
            e.centerSelection()
        },
        readOnly: !0
    }, {
        name: "gotoline",
        bindKey: o("Ctrl-L", "Command-L"),
        exec: function(e) {
            var t = parseInt(prompt("Enter line number:"), 10);
            isNaN(t) || e.gotoLine(t)
        },
        readOnly: !0
    }, {
        name: "fold",
        bindKey: o("Alt-L|Ctrl-F1", "Command-Alt-L|Command-F1"),
        exec: function(e) {
            e.session.toggleFold(!1)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "center",
        readOnly: !0
    }, {
        name: "unfold",
        bindKey: o("Alt-Shift-L|Ctrl-Shift-F1", "Command-Alt-Shift-L|Command-Shift-F1"),
        exec: function(e) {
            e.session.toggleFold(!0)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "center",
        readOnly: !0
    }, {
        name: "toggleFoldWidget",
        bindKey: o("F2", "F2"),
        exec: function(e) {
            e.session.toggleFoldWidget()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "center",
        readOnly: !0
    }, {
        name: "toggleParentFoldWidget",
        bindKey: o("Alt-F2", "Alt-F2"),
        exec: function(e) {
            e.session.toggleFoldWidget(!0)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "center",
        readOnly: !0
    }, {
        name: "foldall",
        bindKey: o(null, "Ctrl-Command-Option-0"),
        exec: function(e) {
            e.session.foldAll()
        },
        scrollIntoView: "center",
        readOnly: !0
    }, {
        name: "foldOther",
        bindKey: o("Alt-0", "Command-Option-0"),
        exec: function(e) {
            e.session.foldAll(), e.session.unfold(e.selection.getAllRanges())
        },
        scrollIntoView: "center",
        readOnly: !0
    }, {
        name: "unfoldall",
        bindKey: o("Alt-Shift-0", "Command-Option-Shift-0"),
        exec: function(e) {
            e.session.unfold()
        },
        scrollIntoView: "center",
        readOnly: !0
    }, {
        name: "findnext",
        bindKey: o("Ctrl-K", "Command-G"),
        exec: function(e) {
            e.findNext()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "center",
        readOnly: !0
    }, {
        name: "findprevious",
        bindKey: o("Ctrl-Shift-K", "Command-Shift-G"),
        exec: function(e) {
            e.findPrevious()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "center",
        readOnly: !0
    }, {
        name: "selectOrFindNext",
        bindKey: o("Alt-K", "Ctrl-G"),
        exec: function(e) {
            e.selection.isEmpty() ? e.selection.selectWord() : e.findNext()
        },
        readOnly: !0
    }, {
        name: "selectOrFindPrevious",
        bindKey: o("Alt-Shift-K", "Ctrl-Shift-G"),
        exec: function(e) {
            e.selection.isEmpty() ? e.selection.selectWord() : e.findPrevious()
        },
        readOnly: !0
    }, {
        name: "find",
        bindKey: o("Ctrl-F", "Command-F"),
        exec: function(e) {
            i.loadModule("ace/ext/searchbox", function(t) {
                t.Search(e)
            })
        },
        readOnly: !0
    }, {
        name: "overwrite",
        bindKey: "Insert",
        exec: function(e) {
            e.toggleOverwrite()
        },
        readOnly: !0
    }, {
        name: "selecttostart",
        bindKey: o("Ctrl-Shift-Home", "Command-Shift-Up"),
        exec: function(e) {
            e.getSelection().selectFileStart()
        },
        multiSelectAction: "forEach",
        readOnly: !0,
        scrollIntoView: "animate",
        aceCommandGroup: "fileJump"
    }, {
        name: "gotostart",
        bindKey: o("Ctrl-Home", "Command-Home|Command-Up"),
        exec: function(e) {
            e.navigateFileStart()
        },
        multiSelectAction: "forEach",
        readOnly: !0,
        scrollIntoView: "animate",
        aceCommandGroup: "fileJump"
    }, {
        name: "selectup",
        bindKey: o("Shift-Up", "Shift-Up"),
        exec: function(e) {
            e.getSelection().selectUp()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "golineup",
        bindKey: o("Up", "Up|Ctrl-P"),
        exec: function(e, t) {
            e.navigateUp(t.times)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selecttoend",
        bindKey: o("Ctrl-Shift-End", "Command-Shift-Down"),
        exec: function(e) {
            e.getSelection().selectFileEnd()
        },
        multiSelectAction: "forEach",
        readOnly: !0,
        scrollIntoView: "animate",
        aceCommandGroup: "fileJump"
    }, {
        name: "gotoend",
        bindKey: o("Ctrl-End", "Command-End|Command-Down"),
        exec: function(e) {
            e.navigateFileEnd()
        },
        multiSelectAction: "forEach",
        readOnly: !0,
        scrollIntoView: "animate",
        aceCommandGroup: "fileJump"
    }, {
        name: "selectdown",
        bindKey: o("Shift-Down", "Shift-Down"),
        exec: function(e) {
            e.getSelection().selectDown()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "golinedown",
        bindKey: o("Down", "Down|Ctrl-N"),
        exec: function(e, t) {
            e.navigateDown(t.times)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selectwordleft",
        bindKey: o("Ctrl-Shift-Left", "Option-Shift-Left"),
        exec: function(e) {
            e.getSelection().selectWordLeft()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "gotowordleft",
        bindKey: o("Ctrl-Left", "Option-Left"),
        exec: function(e) {
            e.navigateWordLeft()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selecttolinestart",
        bindKey: o("Alt-Shift-Left", "Command-Shift-Left"),
        exec: function(e) {
            e.getSelection().selectLineStart()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "gotolinestart",
        bindKey: o("Alt-Left|Home", "Command-Left|Home|Ctrl-A"),
        exec: function(e) {
            e.navigateLineStart()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selectleft",
        bindKey: o("Shift-Left", "Shift-Left"),
        exec: function(e) {
            e.getSelection().selectLeft()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "gotoleft",
        bindKey: o("Left", "Left|Ctrl-B"),
        exec: function(e, t) {
            e.navigateLeft(t.times)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selectwordright",
        bindKey: o("Ctrl-Shift-Right", "Option-Shift-Right"),
        exec: function(e) {
            e.getSelection().selectWordRight()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "gotowordright",
        bindKey: o("Ctrl-Right", "Option-Right"),
        exec: function(e) {
            e.navigateWordRight()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selecttolineend",
        bindKey: o("Alt-Shift-Right", "Command-Shift-Right"),
        exec: function(e) {
            e.getSelection().selectLineEnd()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "gotolineend",
        bindKey: o("Alt-Right|End", "Command-Right|End|Ctrl-E"),
        exec: function(e) {
            e.navigateLineEnd()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selectright",
        bindKey: o("Shift-Right", "Shift-Right"),
        exec: function(e) {
            e.getSelection().selectRight()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "gotoright",
        bindKey: o("Right", "Right|Ctrl-F"),
        exec: function(e, t) {
            e.navigateRight(t.times)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selectpagedown",
        bindKey: "Shift-PageDown",
        exec: function(e) {
            e.selectPageDown()
        },
        readOnly: !0
    }, {
        name: "pagedown",
        bindKey: o(null, "Option-PageDown"),
        exec: function(e) {
            e.scrollPageDown()
        },
        readOnly: !0
    }, {
        name: "gotopagedown",
        bindKey: o("PageDown", "PageDown|Ctrl-V"),
        exec: function(e) {
            e.gotoPageDown()
        },
        readOnly: !0
    }, {
        name: "selectpageup",
        bindKey: "Shift-PageUp",
        exec: function(e) {
            e.selectPageUp()
        },
        readOnly: !0
    }, {
        name: "pageup",
        bindKey: o(null, "Option-PageUp"),
        exec: function(e) {
            e.scrollPageUp()
        },
        readOnly: !0
    }, {
        name: "gotopageup",
        bindKey: "PageUp",
        exec: function(e) {
            e.gotoPageUp()
        },
        readOnly: !0
    }, {
        name: "scrollup",
        bindKey: o("Ctrl-Up", null),
        exec: function(e) {
            e.renderer.scrollBy(0, -2 * e.renderer.layerConfig.lineHeight)
        },
        readOnly: !0
    }, {
        name: "scrolldown",
        bindKey: o("Ctrl-Down", null),
        exec: function(e) {
            e.renderer.scrollBy(0, 2 * e.renderer.layerConfig.lineHeight)
        },
        readOnly: !0
    }, {
        name: "selectlinestart",
        bindKey: "Shift-Home",
        exec: function(e) {
            e.getSelection().selectLineStart()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selectlineend",
        bindKey: "Shift-End",
        exec: function(e) {
            e.getSelection().selectLineEnd()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "togglerecording",
        bindKey: o("Ctrl-Alt-E", "Command-Option-E"),
        exec: function(e) {
            e.commands.toggleRecording(e)
        },
        readOnly: !0
    }, {
        name: "replaymacro",
        bindKey: o("Ctrl-Shift-E", "Command-Shift-E"),
        exec: function(e) {
            e.commands.replay(e)
        },
        readOnly: !0
    }, {
        name: "jumptomatching",
        bindKey: o("Ctrl-P", "Ctrl-P"),
        exec: function(e) {
            e.jumpToMatching()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "animate",
        readOnly: !0
    }, {
        name: "selecttomatching",
        bindKey: o("Ctrl-Shift-P", "Ctrl-Shift-P"),
        exec: function(e) {
            e.jumpToMatching(!0)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "animate",
        readOnly: !0
    }, {
        name: "expandToMatching",
        bindKey: o("Ctrl-Shift-M", "Ctrl-Shift-M"),
        exec: function(e) {
            e.jumpToMatching(!0, !0)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "animate",
        readOnly: !0
    }, {
        name: "passKeysToBrowser",
        bindKey: o(null, null),
        exec: function() {},
        passEvent: !0,
        readOnly: !0
    }, {
        name: "copy",
        exec: function(e) {},
        readOnly: !0
    }, {
        name: "cut",
        exec: function(e) {
            var t = e.getSelectionRange();
            e._emit("cut", t), e.selection.isEmpty() || (e.session.remove(t), e.clearSelection())
        },
        scrollIntoView: "cursor",
        multiSelectAction: "forEach"
    }, {
        name: "paste",
        exec: function(e, t) {
            e.$handlePaste(t)
        },
        scrollIntoView: "cursor"
    }, {
        name: "removeline",
        bindKey: o("Ctrl-D", "Command-D"),
        exec: function(e) {
            e.removeLines()
        },
        scrollIntoView: "cursor",
        multiSelectAction: "forEachLine"
    }, {
        name: "duplicateSelection",
        bindKey: o("Ctrl-Shift-D", "Command-Shift-D"),
        exec: function(e) {
            e.duplicateSelection()
        },
        scrollIntoView: "cursor",
        multiSelectAction: "forEach"
    }, {
        name: "sortlines",
        bindKey: o("Ctrl-Alt-S", "Command-Alt-S"),
        exec: function(e) {
            e.sortLines()
        },
        scrollIntoView: "selection",
        multiSelectAction: "forEachLine"
    }, {
        name: "togglecomment",
        bindKey: o("Ctrl-/", "Command-/"),
        exec: function(e) {
            e.toggleCommentLines()
        },
        multiSelectAction: "forEachLine",
        scrollIntoView: "selectionPart"
    }, {
        name: "toggleBlockComment",
        bindKey: o("Ctrl-Shift-/", "Command-Shift-/"),
        exec: function(e) {
            e.toggleBlockComment()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "selectionPart"
    }, {
        name: "modifyNumberUp",
        bindKey: o("Ctrl-Shift-Up", "Alt-Shift-Up"),
        exec: function(e) {
            e.modifyNumber(1)
        },
        scrollIntoView: "cursor",
        multiSelectAction: "forEach"
    }, {
        name: "modifyNumberDown",
        bindKey: o("Ctrl-Shift-Down", "Alt-Shift-Down"),
        exec: function(e) {
            e.modifyNumber(-1)
        },
        scrollIntoView: "cursor",
        multiSelectAction: "forEach"
    }, {
        name: "replace",
        bindKey: o("Ctrl-H", "Command-Option-F"),
        exec: function(e) {
            i.loadModule("ace/ext/searchbox", function(t) {
                t.Search(e, !0)
            })
        }
    }, {
        name: "undo",
        bindKey: o("Ctrl-Z", "Command-Z"),
        exec: function(e) {
            e.undo()
        }
    }, {
        name: "redo",
        bindKey: o("Ctrl-Shift-Z|Ctrl-Y", "Command-Shift-Z|Command-Y"),
        exec: function(e) {
            e.redo()
        }
    }, {
        name: "copylinesup",
        bindKey: o("Alt-Shift-Up", "Command-Option-Up"),
        exec: function(e) {
            e.copyLinesUp()
        },
        scrollIntoView: "cursor"
    }, {
        name: "movelinesup",
        bindKey: o("Alt-Up", "Option-Up"),
        exec: function(e) {
            e.moveLinesUp()
        },
        scrollIntoView: "cursor"
    }, {
        name: "copylinesdown",
        bindKey: o("Alt-Shift-Down", "Command-Option-Down"),
        exec: function(e) {
            e.copyLinesDown()
        },
        scrollIntoView: "cursor"
    }, {
        name: "movelinesdown",
        bindKey: o("Alt-Down", "Option-Down"),
        exec: function(e) {
            e.moveLinesDown()
        },
        scrollIntoView: "cursor"
    }, {
        name: "del",
        bindKey: o("Delete", "Delete|Ctrl-D|Shift-Delete"),
        exec: function(e) {
            e.remove("right")
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "backspace",
        bindKey: o("Shift-Backspace|Backspace", "Ctrl-Backspace|Shift-Backspace|Backspace|Ctrl-H"),
        exec: function(e) {
            e.remove("left")
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "cut_or_delete",
        bindKey: o("Shift-Delete", null),
        exec: function(e) {
            if (!e.selection.isEmpty()) return !1;
            e.remove("left")
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "removetolinestart",
        bindKey: o("Alt-Backspace", "Command-Backspace"),
        exec: function(e) {
            e.removeToLineStart()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "removetolineend",
        bindKey: o("Alt-Delete", "Ctrl-K"),
        exec: function(e) {
            e.removeToLineEnd()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "removewordleft",
        bindKey: o("Ctrl-Backspace", "Alt-Backspace|Ctrl-Alt-Backspace"),
        exec: function(e) {
            e.removeWordLeft()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "removewordright",
        bindKey: o("Ctrl-Delete", "Alt-Delete"),
        exec: function(e) {
            e.removeWordRight()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "outdent",
        bindKey: o("Shift-Tab", "Shift-Tab"),
        exec: function(e) {
            e.blockOutdent()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "selectionPart"
    }, {
        name: "indent",
        bindKey: o("Tab", "Tab"),
        exec: function(e) {
            e.indent()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "selectionPart"
    }, {
        name: "blockoutdent",
        bindKey: o("Ctrl-[", "Ctrl-["),
        exec: function(e) {
            e.blockOutdent()
        },
        multiSelectAction: "forEachLine",
        scrollIntoView: "selectionPart"
    }, {
        name: "blockindent",
        bindKey: o("Ctrl-]", "Ctrl-]"),
        exec: function(e) {
            e.blockIndent()
        },
        multiSelectAction: "forEachLine",
        scrollIntoView: "selectionPart"
    }, {
        name: "insertstring",
        exec: function(e, t) {
            e.insert(t)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "inserttext",
        exec: function(e, t) {
            e.insert(r.stringRepeat(t.text || "", t.times || 1))
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "splitline",
        bindKey: o(null, "Ctrl-O"),
        exec: function(e) {
            e.splitLine()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "transposeletters",
        bindKey: o("Ctrl-T", "Ctrl-T"),
        exec: function(e) {
            e.transposeLetters()
        },
        multiSelectAction: function(e) {
            e.transposeSelections(1)
        },
        scrollIntoView: "cursor"
    }, {
        name: "touppercase",
        bindKey: o("Ctrl-U", "Ctrl-U"),
        exec: function(e) {
            e.toUpperCase()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "tolowercase",
        bindKey: o("Ctrl-Shift-U", "Ctrl-Shift-U"),
        exec: function(e) {
            e.toLowerCase()
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor"
    }, {
        name: "expandtoline",
        bindKey: o("Ctrl-Shift-L", "Command-Shift-L"),
        exec: function(e) {
            var t = e.selection.getRange();
            t.start.column = t.end.column = 0, t.end.row++, e.selection.setRange(t, !1)
        },
        multiSelectAction: "forEach",
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "joinlines",
        bindKey: o(null, null),
        exec: function(e) {
            var t = e.selection.isBackwards(),
                n = t ? e.selection.getSelectionLead() : e.selection.getSelectionAnchor(),
                i = t ? e.selection.getSelectionAnchor() : e.selection.getSelectionLead(),
                o = e.session.doc.getLine(n.row).length,
                u = e.session.doc.getTextRange(e.selection.getRange()),
                a = u.replace(/\n\s*/, " ").length,
                f = e.session.doc.getLine(n.row);
            for (var l = n.row + 1; l <= i.row + 1; l++) {
                var c = r.stringTrimLeft(r.stringTrimRight(e.session.doc.getLine(l)));
                c.length !== 0 && (c = " " + c), f += c
            }
            i.row + 1 < e.session.doc.getLength() - 1 && (f += e.session.doc.getNewLineCharacter()), e.clearSelection(), e.session.doc.replace(new s(n.row, 0, i.row + 2, 0), f), a > 0 ? (e.selection.moveCursorTo(n.row, n.column), e.selection.selectTo(n.row, n.column + a)) : (o = e.session.doc.getLine(n.row).length > o ? o + 1 : o, e.selection.moveCursorTo(n.row, o))
        },
        multiSelectAction: "forEach",
        readOnly: !0
    }, {
        name: "invertSelection",
        bindKey: o(null, null),
        exec: function(e) {
            var t = e.session.doc.getLength() - 1,
                n = e.session.doc.getLine(t).length,
                r = e.selection.rangeList.ranges,
                i = [];
            r.length < 1 && (r = [e.selection.getRange()]);
            for (var o = 0; o < r.length; o++) o == r.length - 1 && (r[o].end.row !== t || r[o].end.column !== n) && i.push(new s(r[o].end.row, r[o].end.column, t, n)), o === 0 ? (r[o].start.row !== 0 || r[o].start.column !== 0) && i.push(new s(0, 0, r[o].start.row, r[o].start.column)) : i.push(new s(r[o - 1].end.row, r[o - 1].end.column, r[o].start.row, r[o].start.column));
            e.exitMultiSelectMode(), e.clearSelection();
            for (var o = 0; o < i.length; o++) e.selection.addRange(i[o], !1)
        },
        readOnly: !0,
        scrollIntoView: "none"
    }]
}), define("ace/editor", ["require", "exports", "module", "ace/lib/fixoldbrowsers", "ace/lib/oop", "ace/lib/dom", "ace/lib/lang", "ace/lib/useragent", "ace/keyboard/textinput", "ace/mouse/mouse_handler", "ace/mouse/fold_handler", "ace/keyboard/keybinding", "ace/edit_session", "ace/search", "ace/range", "ace/lib/event_emitter", "ace/commands/command_manager", "ace/commands/default_commands", "ace/config", "ace/token_iterator"], function(e, t, n) {
    "use strict";
    e("./lib/fixoldbrowsers");
    var r = e("./lib/oop"),
        i = e("./lib/dom"),
        s = e("./lib/lang"),
        o = e("./lib/useragent"),
        u = e("./keyboard/textinput").TextInput,
        a = e("./mouse/mouse_handler").MouseHandler,
        f = e("./mouse/fold_handler").FoldHandler,
        l = e("./keyboard/keybinding").KeyBinding,
        c = e("./edit_session").EditSession,
        h = e("./search").Search,
        p = e("./range").Range,
        d = e("./lib/event_emitter").EventEmitter,
        v = e("./commands/command_manager").CommandManager,
        m = e("./commands/default_commands").commands,
        g = e("./config"),
        y = e("./token_iterator").TokenIterator,
        b = function(e, t) {
            var n = e.getContainerElement();
            this.container = n, this.renderer = e, this.commands = new v(o.isMac ? "mac" : "win", m), this.textInput = new u(e.getTextAreaContainer(), this), this.renderer.textarea = this.textInput.getElement(), this.keyBinding = new l(this), this.$mouseHandler = new a(this), new f(this), this.$blockScrolling = 0, this.$search = (new h).set({
                wrap: !0
            }), this.$historyTracker = this.$historyTracker.bind(this), this.commands.on("exec", this.$historyTracker), this.$initOperationListeners(), this._$emitInputEvent = s.delayedCall(function() {
                this._signal("input", {}), this.session && this.session.bgTokenizer && this.session.bgTokenizer.scheduleStart()
            }.bind(this)), this.on("change", function(e, t) {
                t._$emitInputEvent.schedule(31)
            }), this.setSession(t || new c("")), g.resetOptions(this), g._signal("editor", this)
        };
    (function() {
        r.implement(this, d), this.$initOperationListeners = function() {
            function e(e) {
                return e[e.length - 1]
            }
            this.selections = [], this.commands.on("exec", this.startOperation.bind(this), !0), this.commands.on("afterExec", this.endOperation.bind(this), !0), this.$opResetTimer = s.delayedCall(this.endOperation.bind(this)), this.on("change", function() {
                this.curOp || this.startOperation(), this.curOp.docChanged = !0
            }.bind(this), !0), this.on("changeSelection", function() {
                this.curOp || this.startOperation(), this.curOp.selectionChanged = !0
            }.bind(this), !0)
        }, this.curOp = null, this.prevOp = {}, this.startOperation = function(e) {
            if (this.curOp) {
                if (!e || this.curOp.command) return;
                this.prevOp = this.curOp
            }
            e || (this.previousCommand = null, e = {}), this.$opResetTimer.schedule(), this.curOp = {
                command: e.command || {},
                args: e.args,
                scrollTop: this.renderer.scrollTop
            }, this.curOp.command.name && this.curOp.command.scrollIntoView !== undefined && this.$blockScrolling++
        }, this.endOperation = function(e) {
            if (this.curOp) {
                if (e && e.returnValue === !1) return this.curOp = null;
                this._signal("beforeEndOperation");
                var t = this.curOp.command;
                t.name && this.$blockScrolling > 0 && this.$blockScrolling--;
                var n = t && t.scrollIntoView;
                if (n) {
                    switch (n) {
                        case "center-animate":
                            n = "animate";
                        case "center":
                            this.renderer.scrollCursorIntoView(null, .5);
                            break;
                        case "animate":
                        case "cursor":
                            this.renderer.scrollCursorIntoView();
                            break;
                        case "selectionPart":
                            var r = this.selection.getRange(),
                                i = this.renderer.layerConfig;
                            (r.start.row >= i.lastRow || r.end.row <= i.firstRow) && this.renderer.scrollSelectionIntoView(this.selection.anchor, this.selection.lead);
                            break;
                        default:
                    }
                    n == "animate" && this.renderer.animateScrolling(this.curOp.scrollTop)
                }
                this.prevOp = this.curOp, this.curOp = null
            }
        }, this.$mergeableCommands = ["backspace", "del", "insertstring"], this.$historyTracker = function(e) {
            if (!this.$mergeUndoDeltas) return;
            var t = this.prevOp,
                n = this.$mergeableCommands,
                r = t.command && e.command.name == t.command.name;
            if (e.command.name == "insertstring") {
                var i = e.args;
                this.mergeNextCommand === undefined && (this.mergeNextCommand = !0), r = r && this.mergeNextCommand && (!/\s/.test(i) || /\s/.test(t.args)), this.mergeNextCommand = !0
            } else r = r && n.indexOf(e.command.name) !== -1;
            this.$mergeUndoDeltas != "always" && Date.now() - this.sequenceStartTime > 2e3 && (r = !1), r ? this.session.mergeUndoDeltas = !0 : n.indexOf(e.command.name) !== -1 && (this.sequenceStartTime = Date.now())
        }, this.setKeyboardHandler = function(e, t) {
            if (e && typeof e == "string") {
                this.$keybindingId = e;
                var n = this;
                g.loadModule(["keybinding", e], function(r) {
                    n.$keybindingId == e && n.keyBinding.setKeyboardHandler(r && r.handler), t && t()
                })
            } else this.$keybindingId = null, this.keyBinding.setKeyboardHandler(e), t && t()
        }, this.getKeyboardHandler = function() {
            return this.keyBinding.getKeyboardHandler()
        }, this.setSession = function(e) {
            if (this.session == e) return;
            this.curOp && this.endOperation(), this.curOp = {};
            var t = this.session;
            if (t) {
                this.session.removeEventListener("change", this.$onDocumentChange), this.session.removeEventListener("changeMode", this.$onChangeMode), this.session.removeEventListener("tokenizerUpdate", this.$onTokenizerUpdate), this.session.removeEventListener("changeTabSize", this.$onChangeTabSize), this.session.removeEventListener("changeWrapLimit", this.$onChangeWrapLimit), this.session.removeEventListener("changeWrapMode", this.$onChangeWrapMode), this.session.removeEventListener("onChangeFold", this.$onChangeFold), this.session.removeEventListener("changeFrontMarker", this.$onChangeFrontMarker), this.session.removeEventListener("changeBackMarker", this.$onChangeBackMarker), this.session.removeEventListener("changeBreakpoint", this.$onChangeBreakpoint), this.session.removeEventListener("changeAnnotation", this.$onChangeAnnotation), this.session.removeEventListener("changeOverwrite", this.$onCursorChange), this.session.removeEventListener("changeScrollTop", this.$onScrollTopChange), this.session.removeEventListener("changeScrollLeft", this.$onScrollLeftChange);
                var n = this.session.getSelection();
                n.removeEventListener("changeCursor", this.$onCursorChange), n.removeEventListener("changeSelection", this.$onSelectionChange)
            }
            this.session = e, e ? (this.$onDocumentChange = this.onDocumentChange.bind(this), e.addEventListener("change", this.$onDocumentChange), this.renderer.setSession(e), this.$onChangeMode = this.onChangeMode.bind(this), e.addEventListener("changeMode", this.$onChangeMode), this.$onTokenizerUpdate = this.onTokenizerUpdate.bind(this), e.addEventListener("tokenizerUpdate", this.$onTokenizerUpdate), this.$onChangeTabSize = this.renderer.onChangeTabSize.bind(this.renderer), e.addEventListener("changeTabSize", this.$onChangeTabSize), this.$onChangeWrapLimit = this.onChangeWrapLimit.bind(this), e.addEventListener("changeWrapLimit", this.$onChangeWrapLimit), this.$onChangeWrapMode = this.onChangeWrapMode.bind(this), e.addEventListener("changeWrapMode", this.$onChangeWrapMode), this.$onChangeFold = this.onChangeFold.bind(this), e.addEventListener("changeFold", this.$onChangeFold), this.$onChangeFrontMarker = this.onChangeFrontMarker.bind(this), this.session.addEventListener("changeFrontMarker", this.$onChangeFrontMarker), this.$onChangeBackMarker = this.onChangeBackMarker.bind(this), this.session.addEventListener("changeBackMarker", this.$onChangeBackMarker), this.$onChangeBreakpoint = this.onChangeBreakpoint.bind(this), this.session.addEventListener("changeBreakpoint", this.$onChangeBreakpoint), this.$onChangeAnnotation = this.onChangeAnnotation.bind(this), this.session.addEventListener("changeAnnotation", this.$onChangeAnnotation), this.$onCursorChange = this.onCursorChange.bind(this), this.session.addEventListener("changeOverwrite", this.$onCursorChange), this.$onScrollTopChange = this.onScrollTopChange.bind(this), this.session.addEventListener("changeScrollTop", this.$onScrollTopChange), this.$onScrollLeftChange = this.onScrollLeftChange.bind(this), this.session.addEventListener("changeScrollLeft", this.$onScrollLeftChange), this.selection = e.getSelection(), this.selection.addEventListener("changeCursor", this.$onCursorChange), this.$onSelectionChange = this.onSelectionChange.bind(this), this.selection.addEventListener("changeSelection", this.$onSelectionChange), this.onChangeMode(), this.$blockScrolling += 1, this.onCursorChange(), this.$blockScrolling -= 1, this.onScrollTopChange(), this.onScrollLeftChange(), this.onSelectionChange(), this.onChangeFrontMarker(), this.onChangeBackMarker(), this.onChangeBreakpoint(), this.onChangeAnnotation(), this.session.getUseWrapMode() && this.renderer.adjustWrapLimit(), this.renderer.updateFull()) : (this.selection = null, this.renderer.setSession(e)), this._signal("changeSession", {
                session: e,
                oldSession: t
            }), this.curOp = null, t && t._signal("changeEditor", {
                oldEditor: this
            }), e && e._signal("changeEditor", {
                editor: this
            })
        }, this.getSession = function() {
            return this.session
        }, this.setValue = function(e, t) {
            return this.session.doc.setValue(e), t ? t == 1 ? this.navigateFileEnd() : t == -1 && this.navigateFileStart() : this.selectAll(), e
        }, this.getValue = function() {
            return this.session.getValue()
        }, this.getSelection = function() {
            return this.selection
        }, this.resize = function(e) {
            this.renderer.onResize(e)
        }, this.setTheme = function(e, t) {
            this.renderer.setTheme(e, t)
        }, this.getTheme = function() {
            return this.renderer.getTheme()
        }, this.setStyle = function(e) {
            this.renderer.setStyle(e)
        }, this.unsetStyle = function(e) {
            this.renderer.unsetStyle(e)
        }, this.getFontSize = function() {
            return this.getOption("fontSize") || i.computedStyle(this.container, "fontSize")
        }, this.setFontSize = function(e) {
            this.setOption("fontSize", e)
        }, this.$highlightBrackets = function() {
            this.session.$bracketHighlight && (this.session.removeMarker(this.session.$bracketHighlight), this.session.$bracketHighlight = null);
            if (this.$highlightPending) return;
            var e = this;
            this.$highlightPending = !0, setTimeout(function() {
                e.$highlightPending = !1;
                var t = e.session;
                if (!t || !t.bgTokenizer) return;
                var n = t.findMatchingBracket(e.getCursorPosition());
                if (n) var r = new p(n.row, n.column, n.row, n.column + 1);
                else if (t.$mode.getMatching) var r = t.$mode.getMatching(e.session);
                r && (t.$bracketHighlight = t.addMarker(r, "ace_bracket", "text"))
            }, 50)
        }, this.$highlightTags = function() {
            if (this.$highlightTagPending) return;
            var e = this;
            this.$highlightTagPending = !0, setTimeout(function() {
                e.$highlightTagPending = !1;
                var t = e.session;
                if (!t || !t.bgTokenizer) return;
                var n = e.getCursorPosition(),
                    r = new y(e.session, n.row, n.column),
                    i = r.getCurrentToken();
                if (!i || !/\b(?:tag-open|tag-name)/.test(i.type)) {
                    t.removeMarker(t.$tagHighlight), t.$tagHighlight = null;
                    return
                }
                if (i.type.indexOf("tag-open") != -1) {
                    i = r.stepForward();
                    if (!i) return
                }
                var s = i.value,
                    o = 0,
                    u = r.stepBackward();
                if (u.value == "<") {
                    do u = i, i = r.stepForward(), i && i.value === s && i.type.indexOf("tag-name") !== -1 && (u.value === "<" ? o++ : u.value === "</" && o--); while (i && o >= 0)
                } else {
                    do i = u, u = r.stepBackward(), i && i.value === s && i.type.indexOf("tag-name") !== -1 && (u.value === "<" ? o++ : u.value === "</" && o--); while (u && o <= 0);
                    r.stepForward()
                }
                if (!i) {
                    t.removeMarker(t.$tagHighlight), t.$tagHighlight = null;
                    return
                }
                var a = r.getCurrentTokenRow(),
                    f = r.getCurrentTokenColumn(),
                    l = new p(a, f, a, f + i.value.length);
                t.$tagHighlight && l.compareRange(t.$backMarkers[t.$tagHighlight].range) !== 0 && (t.removeMarker(t.$tagHighlight), t.$tagHighlight = null), l && !t.$tagHighlight && (t.$tagHighlight = t.addMarker(l, "ace_bracket", "text"))
            }, 50)
        }, this.focus = function() {
            var e = this;
            setTimeout(function() {
                e.textInput.focus()
            }), this.textInput.focus()
        }, this.isFocused = function() {
            return this.textInput.isFocused()
        }, this.blur = function() {
            this.textInput.blur()
        }, this.onFocus = function(e) {
            if (this.$isFocused) return;
            this.$isFocused = !0, this.renderer.showCursor(), this.renderer.visualizeFocus(), this._emit("focus", e)
        }, this.onBlur = function(e) {
            if (!this.$isFocused) return;
            this.$isFocused = !1, this.renderer.hideCursor(), this.renderer.visualizeBlur(), this._emit("blur", e)
        }, this.$cursorChange = function() {
            this.renderer.updateCursor()
        }, this.onDocumentChange = function(e) {
            var t = this.session.$useWrapMode,
                n = e.start.row == e.end.row ? e.end.row : Infinity;
            this.renderer.updateLines(e.start.row, n, t), this._signal("change", e), this.$cursorChange(), this.$updateHighlightActiveLine()
        }, this.onTokenizerUpdate = function(e) {
            var t = e.data;
            this.renderer.updateLines(t.first, t.last)
        }, this.onScrollTopChange = function() {
            this.renderer.scrollToY(this.session.getScrollTop())
        }, this.onScrollLeftChange = function() {
            this.renderer.scrollToX(this.session.getScrollLeft())
        }, this.onCursorChange = function() {
            this.$cursorChange(), this.$blockScrolling || (g.warn("Automatically scrolling cursor into view after selection change", "this will be disabled in the next version", "set editor.$blockScrolling = Infinity to disable this message"), this.renderer.scrollCursorIntoView()), this.$highlightBrackets(), this.$highlightTags(), this.$updateHighlightActiveLine(), this._signal("changeSelection")
        }, this.$updateHighlightActiveLine = function() {
            var e = this.getSession(),
                t;
            if (this.$highlightActiveLine) {
                if (this.$selectionStyle != "line" || !this.selection.isMultiLine()) t = this.getCursorPosition();
                this.renderer.$maxLines && this.session.getLength() === 1 && !(this.renderer.$minLines > 1) && (t = !1)
            }
            if (e.$highlightLineMarker && !t) e.removeMarker(e.$highlightLineMarker.id), e.$highlightLineMarker = null;
            else if (!e.$highlightLineMarker && t) {
                var n = new p(t.row, t.column, t.row, Infinity);
                n.id = e.addMarker(n, "ace_active-line", "screenLine"), e.$highlightLineMarker = n
            } else t && (e.$highlightLineMarker.start.row = t.row, e.$highlightLineMarker.end.row = t.row, e.$highlightLineMarker.start.column = t.column, e._signal("changeBackMarker"))
        }, this.onSelectionChange = function(e) {
            var t = this.session;
            t.$selectionMarker && t.removeMarker(t.$selectionMarker), t.$selectionMarker = null;
            if (!this.selection.isEmpty()) {
                var n = this.selection.getRange(),
                    r = this.getSelectionStyle();
                t.$selectionMarker = t.addMarker(n, "ace_selection", r)
            } else this.$updateHighlightActiveLine();
            var i = this.$highlightSelectedWord && this.$getSelectionHighLightRegexp();
            this.session.highlight(i), this._signal("changeSelection")
        }, this.$getSelectionHighLightRegexp = function() {
            var e = this.session,
                t = this.getSelectionRange();
            if (t.isEmpty() || t.isMultiLine()) return;
            var n = t.start.column - 1,
                r = t.end.column + 1,
                i = e.getLine(t.start.row),
                s = i.length,
                o = i.substring(Math.max(n, 0), Math.min(r, s));
            if (n >= 0 && /^[\w\d]/.test(o) || r <= s && /[\w\d]$/.test(o)) return;
            o = i.substring(t.start.column, t.end.column);
            if (!/^[\w\d]+$/.test(o)) return;
            var u = this.$search.$assembleRegExp({
                wholeWord: !0,
                caseSensitive: !0,
                needle: o
            });
            return u
        }, this.onChangeFrontMarker = function() {
            this.renderer.updateFrontMarkers()
        }, this.onChangeBackMarker = function() {
            this.renderer.updateBackMarkers()
        }, this.onChangeBreakpoint = function() {
            this.renderer.updateBreakpoints()
        }, this.onChangeAnnotation = function() {
            this.renderer.setAnnotations(this.session.getAnnotations())
        }, this.onChangeMode = function(e) {
            this.renderer.updateText(), this._emit("changeMode", e)
        }, this.onChangeWrapLimit = function() {
            this.renderer.updateFull()
        }, this.onChangeWrapMode = function() {
            this.renderer.onResize(!0)
        }, this.onChangeFold = function() {
            this.$updateHighlightActiveLine(), this.renderer.updateFull()
        }, this.getSelectedText = function() {
            return this.session.getTextRange(this.getSelectionRange())
        }, this.getCopyText = function() {
            var e = this.getSelectedText();
            return this._signal("copy", e), e
        }, this.onCopy = function() {
            this.commands.exec("copy", this)
        }, this.onCut = function() {
            this.commands.exec("cut", this)
        }, this.onPaste = function(e, t) {
            var n = {
                text: e,
                event: t
            };
            this.commands.exec("paste", this, n)
        }, this.$handlePaste = function(e) {
            typeof e == "string" && (e = {
                text: e
            }), this._signal("paste", e);
            var t = e.text;
            if (!this.inMultiSelectMode || this.inVirtualSelectionMode) this.insert(t);
            else {
                var n = t.split(/\r\n|\r|\n/),
                    r = this.selection.rangeList.ranges;
                if (n.length > r.length || n.length < 2 || !n[1]) return this.commands.exec("insertstring", this, t);
                for (var i = r.length; i--;) {
                    var s = r[i];
                    s.isEmpty() || this.session.remove(s), this.session.insert(s.start, n[i])
                }
            }
        }, this.execCommand = function(e, t) {
            return this.commands.exec(e, this, t)
        }, this.insert = function(e, t) {
            var n = this.session,
                r = n.getMode(),
                i = this.getCursorPosition();
            if (this.getBehavioursEnabled() && !t) {
                var s = r.transformAction(n.getState(i.row), "insertion", this, n, e);
                s && (e !== s.text && (this.session.mergeUndoDeltas = !1, this.$mergeNextCommand = !1), e = s.text)
            }
            e == "  " && (e = this.session.getTabString());
            if (!this.selection.isEmpty()) {
                var o = this.getSelectionRange();
                i = this.session.remove(o), this.clearSelection()
            } else if (this.session.getOverwrite()) {
                var o = new p.fromPoints(i, i);
                o.end.column += e.length, this.session.remove(o)
            }
            if (e == "\n" || e == "\r\n") {
                var u = n.getLine(i.row);
                if (i.column > u.search(/\S|$/)) {
                    var a = u.substr(i.column).search(/\S|$/);
                    n.doc.removeInLine(i.row, i.column, i.column + a)
                }
            }
            this.clearSelection();
            var f = i.column,
                l = n.getState(i.row),
                u = n.getLine(i.row),
                c = r.checkOutdent(l, u, e),
                h = n.insert(i, e);
            s && s.selection && (s.selection.length == 2 ? this.selection.setSelectionRange(new p(i.row, f + s.selection[0], i.row, f + s.selection[1])) : this.selection.setSelectionRange(new p(i.row + s.selection[0], s.selection[1], i.row + s.selection[2], s.selection[3])));
            if (n.getDocument().isNewLine(e)) {
                var d = r.getNextLineIndent(l, u.slice(0, i.column), n.getTabString());
                n.insert({
                    row: i.row + 1,
                    column: 0
                }, d)
            }
            c && r.autoOutdent(l, n, i.row)
        }, this.onTextInput = function(e) {
            this.keyBinding.onTextInput(e)
        }, this.onCommandKey = function(e, t, n) {
            this.keyBinding.onCommandKey(e, t, n)
        }, this.setOverwrite = function(e) {
            this.session.setOverwrite(e)
        }, this.getOverwrite = function() {
            return this.session.getOverwrite()
        }, this.toggleOverwrite = function() {
            this.session.toggleOverwrite()
        }, this.setScrollSpeed = function(e) {
            this.setOption("scrollSpeed", e)
        }, this.getScrollSpeed = function() {
            return this.getOption("scrollSpeed")
        }, this.setDragDelay = function(e) {
            this.setOption("dragDelay", e)
        }, this.getDragDelay = function() {
            return this.getOption("dragDelay")
        }, this.setSelectionStyle = function(e) {
            this.setOption("selectionStyle", e)
        }, this.getSelectionStyle = function() {
            return this.getOption("selectionStyle")
        }, this.setHighlightActiveLine = function(e) {
            this.setOption("highlightActiveLine", e)
        }, this.getHighlightActiveLine = function() {
            return this.getOption("highlightActiveLine")
        }, this.setHighlightGutterLine = function(e) {
            this.setOption("highlightGutterLine", e)
        }, this.getHighlightGutterLine = function() {
            return this.getOption("highlightGutterLine")
        }, this.setHighlightSelectedWord = function(e) {
            this.setOption("highlightSelectedWord", e)
        }, this.getHighlightSelectedWord = function() {
            return this.$highlightSelectedWord
        }, this.setAnimatedScroll = function(e) {
            this.renderer.setAnimatedScroll(e)
        }, this.getAnimatedScroll = function() {
            return this.renderer.getAnimatedScroll()
        }, this.setShowInvisibles = function(e) {
            this.renderer.setShowInvisibles(e)
        }, this.getShowInvisibles = function() {
            return this.renderer.getShowInvisibles()
        }, this.setDisplayIndentGuides = function(e) {
            this.renderer.setDisplayIndentGuides(e)
        }, this.getDisplayIndentGuides = function() {
            return this.renderer.getDisplayIndentGuides()
        }, this.setShowPrintMargin = function(e) {
            this.renderer.setShowPrintMargin(e)
        }, this.getShowPrintMargin = function() {
            return this.renderer.getShowPrintMargin()
        }, this.setPrintMarginColumn = function(e) {
            this.renderer.setPrintMarginColumn(e)
        }, this.getPrintMarginColumn = function() {
            return this.renderer.getPrintMarginColumn()
        }, this.setReadOnly = function(e) {
            this.setOption("readOnly", e)
        }, this.getReadOnly = function() {
            return this.getOption("readOnly")
        }, this.setBehavioursEnabled = function(e) {
            this.setOption("behavioursEnabled", e)
        }, this.getBehavioursEnabled = function() {
            return this.getOption("behavioursEnabled")
        }, this.setWrapBehavioursEnabled = function(e) {
            this.setOption("wrapBehavioursEnabled", e)
        }, this.getWrapBehavioursEnabled = function() {
            return this.getOption("wrapBehavioursEnabled")
        }, this.setShowFoldWidgets = function(e) {
            this.setOption("showFoldWidgets", e)
        }, this.getShowFoldWidgets = function() {
            return this.getOption("showFoldWidgets")
        }, this.setFadeFoldWidgets = function(e) {
            this.setOption("fadeFoldWidgets", e)
        }, this.getFadeFoldWidgets = function() {
            return this.getOption("fadeFoldWidgets")
        }, this.remove = function(e) {
            this.selection.isEmpty() && (e == "left" ? this.selection.selectLeft() : this.selection.selectRight());
            var t = this.getSelectionRange();
            if (this.getBehavioursEnabled()) {
                var n = this.session,
                    r = n.getState(t.start.row),
                    i = n.getMode().transformAction(r, "deletion", this, n, t);
                if (t.end.column === 0) {
                    var s = n.getTextRange(t);
                    if (s[s.length - 1] == "\n") {
                        var o = n.getLine(t.end.row);
                        /^\s+$/.test(o) && (t.end.column = o.length)
                    }
                }
                i && (t = i)
            }
            this.session.remove(t), this.clearSelection()
        }, this.removeWordRight = function() {
            this.selection.isEmpty() && this.selection.selectWordRight(), this.session.remove(this.getSelectionRange()), this.clearSelection()
        }, this.removeWordLeft = function() {
            this.selection.isEmpty() && this.selection.selectWordLeft(), this.session.remove(this.getSelectionRange()), this.clearSelection()
        }, this.removeToLineStart = function() {
            this.selection.isEmpty() && this.selection.selectLineStart(), this.session.remove(this.getSelectionRange()), this.clearSelection()
        }, this.removeToLineEnd = function() {
            this.selection.isEmpty() && this.selection.selectLineEnd();
            var e = this.getSelectionRange();
            e.start.column == e.end.column && e.start.row == e.end.row && (e.end.column = 0, e.end.row++), this.session.remove(e), this.clearSelection()
        }, this.splitLine = function() {
            this.selection.isEmpty() || (this.session.remove(this.getSelectionRange()), this.clearSelection());
            var e = this.getCursorPosition();
            this.insert("\n"), this.moveCursorToPosition(e)
        }, this.transposeLetters = function() {
            if (!this.selection.isEmpty()) return;
            var e = this.getCursorPosition(),
                t = e.column;
            if (t === 0) return;
            var n = this.session.getLine(e.row),
                r, i;
            t < n.length ? (r = n.charAt(t) + n.charAt(t - 1), i = new p(e.row, t - 1, e.row, t + 1)) : (r = n.charAt(t - 1) + n.charAt(t - 2), i = new p(e.row, t - 2, e.row, t)), this.session.replace(i, r)
        }, this.toLowerCase = function() {
            var e = this.getSelectionRange();
            this.selection.isEmpty() && this.selection.selectWord();
            var t = this.getSelectionRange(),
                n = this.session.getTextRange(t);
            this.session.replace(t, n.toLowerCase()), this.selection.setSelectionRange(e)
        }, this.toUpperCase = function() {
            var e = this.getSelectionRange();
            this.selection.isEmpty() && this.selection.selectWord();
            var t = this.getSelectionRange(),
                n = this.session.getTextRange(t);
            this.session.replace(t, n.toUpperCase()), this.selection.setSelectionRange(e)
        }, this.indent = function() {
            var e = this.session,
                t = this.getSelectionRange();
            if (t.start.row < t.end.row) {
                var n = this.$getSelectedRows();
                e.indentRows(n.first, n.last, " ");
                return
            }
            if (t.start.column < t.end.column) {
                var r = e.getTextRange(t);
                if (!/^\s+$/.test(r)) {
                    var n = this.$getSelectedRows();
                    e.indentRows(n.first, n.last, " ");
                    return
                }
            }
            var i = e.getLine(t.start.row),
                o = t.start,
                u = e.getTabSize(),
                a = e.documentToScreenColumn(o.row, o.column);
            if (this.session.getUseSoftTabs()) var f = u - a % u,
                l = s.stringRepeat(" ", f);
            else {
                var f = a % u;
                while (i[t.start.column] == " " && f) t.start.column--, f--;
                this.selection.setSelectionRange(t), l = "  "
            }
            return this.insert(l)
        }, this.blockIndent = function() {
            var e = this.$getSelectedRows();
            this.session.indentRows(e.first, e.last, "  ")
        }, this.blockOutdent = function() {
            var e = this.session.getSelection();
            this.session.outdentRows(e.getRange())
        }, this.sortLines = function() {
            var e = this.$getSelectedRows(),
                t = this.session,
                n = [];
            for (i = e.first; i <= e.last; i++) n.push(t.getLine(i));
            n.sort(function(e, t) {
                return e.toLowerCase() < t.toLowerCase() ? -1 : e.toLowerCase() > t.toLowerCase() ? 1 : 0
            });
            var r = new p(0, 0, 0, 0);
            for (var i = e.first; i <= e.last; i++) {
                var s = t.getLine(i);
                r.start.row = i, r.end.row = i, r.end.column = s.length, t.replace(r, n[i - e.first])
            }
        }, this.toggleCommentLines = function() {
            var e = this.session.getState(this.getCursorPosition().row),
                t = this.$getSelectedRows();
            this.session.getMode().toggleCommentLines(e, this.session, t.first, t.last)
        }, this.toggleBlockComment = function() {
            var e = this.getCursorPosition(),
                t = this.session.getState(e.row),
                n = this.getSelectionRange();
            this.session.getMode().toggleBlockComment(t, this.session, n, e)
        }, this.getNumberAt = function(e, t) {
            var n = /[\-]?[0-9]+(?:\.[0-9]+)?/g;
            n.lastIndex = 0;
            var r = this.session.getLine(e);
            while (n.lastIndex < t) {
                var i = n.exec(r);
                if (i.index <= t && i.index + i[0].length >= t) {
                    var s = {
                        value: i[0],
                        start: i.index,
                        end: i.index + i[0].length
                    };
                    return s
                }
            }
            return null
        }, this.modifyNumber = function(e) {
            var t = this.selection.getCursor().row,
                n = this.selection.getCursor().column,
                r = new p(t, n - 1, t, n),
                i = this.session.getTextRange(r);
            if (!isNaN(parseFloat(i)) && isFinite(i)) {
                var s = this.getNumberAt(t, n);
                if (s) {
                    var o = s.value.indexOf(".") >= 0 ? s.start + s.value.indexOf(".") + 1 : s.end,
                        u = s.start + s.value.length - o,
                        a = parseFloat(s.value);
                    a *= Math.pow(10, u), o !== s.end && n < o ? e *= Math.pow(10, s.end - n - 1) : e *= Math.pow(10, s.end - n), a += e, a /= Math.pow(10, u);
                    var f = a.toFixed(u),
                        l = new p(t, s.start, t, s.end);
                    this.session.replace(l, f), this.moveCursorTo(t, Math.max(s.start + 1, n + f.length - s.value.length))
                }
            }
        }, this.removeLines = function() {
            var e = this.$getSelectedRows();
            this.session.removeFullLines(e.first, e.last), this.clearSelection()
        }, this.duplicateSelection = function() {
            var e = this.selection,
                t = this.session,
                n = e.getRange(),
                r = e.isBackwards();
            if (n.isEmpty()) {
                var i = n.start.row;
                t.duplicateLines(i, i)
            } else {
                var s = r ? n.start : n.end,
                    o = t.insert(s, t.getTextRange(n), !1);
                n.start = s, n.end = o, e.setSelectionRange(n, r)
            }
        }, this.moveLinesDown = function() {
            this.$moveLines(1, !1)
        }, this.moveLinesUp = function() {
            this.$moveLines(-1, !1)
        }, this.moveText = function(e, t, n) {
            return this.session.moveText(e, t, n)
        }, this.copyLinesUp = function() {
            this.$moveLines(-1, !0)
        }, this.copyLinesDown = function() {
            this.$moveLines(1, !0)
        }, this.$moveLines = function(e, t) {
            var n, r, i = this.selection;
            if (!i.inMultiSelectMode || this.inVirtualSelectionMode) {
                var s = i.toOrientedRange();
                n = this.$getSelectedRows(s), r = this.session.$moveLines(n.first, n.last, t ? 0 : e), t && e == -1 && (r = 0), s.moveBy(r, 0), i.fromOrientedRange(s)
            } else {
                var o = i.rangeList.ranges;
                i.rangeList.detach(this.session), this.inVirtualSelectionMode = !0;
                var u = 0,
                    a = 0,
                    f = o.length;
                for (var l = 0; l < f; l++) {
                    var c = l;
                    o[l].moveBy(u, 0), n = this.$getSelectedRows(o[l]);
                    var h = n.first,
                        p = n.last;
                    while (++l < f) {
                        a && o[l].moveBy(a, 0);
                        var d = this.$getSelectedRows(o[l]);
                        if (t && d.first != p) break;
                        if (!t && d.first > p + 1) break;
                        p = d.last
                    }
                    l--, u = this.session.$moveLines(h, p, t ? 0 : e), t && e == -1 && (c = l + 1);
                    while (c <= l) o[c].moveBy(u, 0), c++;
                    t || (u = 0), a += u
                }
                i.fromOrientedRange(i.ranges[0]), i.rangeList.attach(this.session), this.inVirtualSelectionMode = !1
            }
        }, this.$getSelectedRows = function(e) {
            return e = (e || this.getSelectionRange()).collapseRows(), {
                first: this.session.getRowFoldStart(e.start.row),
                last: this.session.getRowFoldEnd(e.end.row)
            }
        }, this.onCompositionStart = function(e) {
            this.renderer.showComposition(this.getCursorPosition())
        }, this.onCompositionUpdate = function(e) {
            this.renderer.setCompositionText(e)
        }, this.onCompositionEnd = function() {
            this.renderer.hideComposition()
        }, this.getFirstVisibleRow = function() {
            return this.renderer.getFirstVisibleRow()
        }, this.getLastVisibleRow = function() {
            return this.renderer.getLastVisibleRow()
        }, this.isRowVisible = function(e) {
            return e >= this.getFirstVisibleRow() && e <= this.getLastVisibleRow()
        }, this.isRowFullyVisible = function(e) {
            return e >= this.renderer.getFirstFullyVisibleRow() && e <= this.renderer.getLastFullyVisibleRow()
        }, this.$getVisibleRowCount = function() {
            return this.renderer.getScrollBottomRow() - this.renderer.getScrollTopRow() + 1
        }, this.$moveByPage = function(e, t) {
            var n = this.renderer,
                r = this.renderer.layerConfig,
                i = e * Math.floor(r.height / r.lineHeight);
            this.$blockScrolling++, t === !0 ? this.selection.$moveSelection(function() {
                this.moveCursorBy(i, 0)
            }) : t === !1 && (this.selection.moveCursorBy(i, 0), this.selection.clearSelection()), this.$blockScrolling--;
            var s = n.scrollTop;
            n.scrollBy(0, i * r.lineHeight), t != null && n.scrollCursorIntoView(null, .5), n.animateScrolling(s)
        }, this.selectPageDown = function() {
            this.$moveByPage(1, !0)
        }, this.selectPageUp = function() {
            this.$moveByPage(-1, !0)
        }, this.gotoPageDown = function() {
            this.$moveByPage(1, !1)
        }, this.gotoPageUp = function() {
            this.$moveByPage(-1, !1)
        }, this.scrollPageDown = function() {
            this.$moveByPage(1)
        }, this.scrollPageUp = function() {
            this.$moveByPage(-1)
        }, this.scrollToRow = function(e) {
            this.renderer.scrollToRow(e)
        }, this.scrollToLine = function(e, t, n, r) {
            this.renderer.scrollToLine(e, t, n, r)
        }, this.centerSelection = function() {
            var e = this.getSelectionRange(),
                t = {
                    row: Math.floor(e.start.row + (e.end.row - e.start.row) / 2),
                    column: Math.floor(e.start.column + (e.end.column - e.start.column) / 2)
                };
            this.renderer.alignCursor(t, .5)
        }, this.getCursorPosition = function() {
            return this.selection.getCursor()
        }, this.getCursorPositionScreen = function() {
            return this.session.documentToScreenPosition(this.getCursorPosition())
        }, this.getSelectionRange = function() {
            return this.selection.getRange()
        }, this.selectAll = function() {
            this.$blockScrolling += 1, this.selection.selectAll(), this.$blockScrolling -= 1
        }, this.clearSelection = function() {
            this.selection.clearSelection()
        }, this.moveCursorTo = function(e, t) {
            this.selection.moveCursorTo(e, t)
        }, this.moveCursorToPosition = function(e) {
            this.selection.moveCursorToPosition(e)
        }, this.jumpToMatching = function(e, t) {
            var n = this.getCursorPosition(),
                r = new y(this.session, n.row, n.column),
                i = r.getCurrentToken(),
                s = i || r.stepForward();
            if (!s) return;
            var o, u = !1,
                a = {},
                f = n.column - s.start,
                l, c = {
                    ")": "(",
                    "(": "(",
                    "]": "[",
                    "[": "[",
                    "{": "{",
                    "}": "{"
                };
            do {
                if (s.value.match(/[{}()\[\]]/g))
                    for (; f < s.value.length && !u; f++) {
                        if (!c[s.value[f]]) continue;
                        l = c[s.value[f]] + "." + s.type.replace("rparen", "lparen"), isNaN(a[l]) && (a[l] = 0);
                        switch (s.value[f]) {
                            case "(":
                            case "[":
                            case "{":
                                a[l]++;
                                break;
                            case ")":
                            case "]":
                            case "}":
                                a[l]--, a[l] === -1 && (o = "bracket", u = !0)
                        }
                    } else s && s.type.indexOf("tag-name") !== -1 && (isNaN(a[s.value]) && (a[s.value] = 0), i.value === "<" ? a[s.value]++ : i.value === "</" && a[s.value]--, a[s.value] === -1 && (o = "tag", u = !0));
                u || (i = s, s = r.stepForward(), f = 0)
            } while (s && !u);
            if (!o) return;
            var h, d;
            if (o === "bracket") {
                h = this.session.getBracketRange(n);
                if (!h) {
                    h = new p(r.getCurrentTokenRow(), r.getCurrentTokenColumn() + f - 1, r.getCurrentTokenRow(), r.getCurrentTokenColumn() + f - 1), d = h.start;
                    if (t || d.row === n.row && Math.abs(d.column - n.column) < 2) h = this.session.getBracketRange(d)
                }
            } else if (o === "tag") {
                if (!s || s.type.indexOf("tag-name") === -1) return;
                var v = s.value;
                h = new p(r.getCurrentTokenRow(), r.getCurrentTokenColumn() - 2, r.getCurrentTokenRow(), r.getCurrentTokenColumn() - 2);
                if (h.compare(n.row, n.column) === 0) {
                    u = !1;
                    do s = i, i = r.stepBackward(), i && (i.type.indexOf("tag-close") !== -1 && h.setEnd(r.getCurrentTokenRow(), r.getCurrentTokenColumn() + 1), s.value === v && s.type.indexOf("tag-name") !== -1 && (i.value === "<" ? a[v]++ : i.value === "</" && a[v]--, a[v] === 0 && (u = !0))); while (i && !u)
                }
                s && s.type.indexOf("tag-name") && (d = h.start, d.row == n.row && Math.abs(d.column - n.column) < 2 && (d = h.end))
            }
            d = h && h.cursor || d, d && (e ? h && t ? this.selection.setRange(h) : h && h.isEqual(this.getSelectionRange()) ? this.clearSelection() : this.selection.selectTo(d.row, d.column) : this.selection.moveTo(d.row, d.column))
        }, this.gotoLine = function(e, t, n) {
            this.selection.clearSelection(), this.session.unfold({
                row: e - 1,
                column: t || 0
            }), this.$blockScrolling += 1, this.exitMultiSelectMode && this.exitMultiSelectMode(), this.moveCursorTo(e - 1, t || 0), this.$blockScrolling -= 1, this.isRowFullyVisible(e - 1) || this.scrollToLine(e - 1, !0, n)
        }, this.navigateTo = function(e, t) {
            this.selection.moveTo(e, t)
        }, this.navigateUp = function(e) {
            if (this.selection.isMultiLine() && !this.selection.isBackwards()) {
                var t = this.selection.anchor.getPosition();
                return this.moveCursorToPosition(t)
            }
            this.selection.clearSelection(), this.selection.moveCursorBy(-e || -1, 0)
        }, this.navigateDown = function(e) {
            if (this.selection.isMultiLine() && this.selection.isBackwards()) {
                var t = this.selection.anchor.getPosition();
                return this.moveCursorToPosition(t)
            }
            this.selection.clearSelection(), this.selection.moveCursorBy(e || 1, 0)
        }, this.navigateLeft = function(e) {
            if (!this.selection.isEmpty()) {
                var t = this.getSelectionRange().start;
                this.moveCursorToPosition(t)
            } else {
                e = e || 1;
                while (e--) this.selection.moveCursorLeft()
            }
            this.clearSelection()
        }, this.navigateRight = function(e) {
            if (!this.selection.isEmpty()) {
                var t = this.getSelectionRange().end;
                this.moveCursorToPosition(t)
            } else {
                e = e || 1;
                while (e--) this.selection.moveCursorRight()
            }
            this.clearSelection()
        }, this.navigateLineStart = function() {
            this.selection.moveCursorLineStart(), this.clearSelection()
        }, this.navigateLineEnd = function() {
            this.selection.moveCursorLineEnd(), this.clearSelection()
        }, this.navigateFileEnd = function() {
            this.selection.moveCursorFileEnd(), this.clearSelection()
        }, this.navigateFileStart = function() {
            this.selection.moveCursorFileStart(), this.clearSelection()
        }, this.navigateWordRight = function() {
            this.selection.moveCursorWordRight(), this.clearSelection()
        }, this.navigateWordLeft = function() {
            this.selection.moveCursorWordLeft(), this.clearSelection()
        }, this.replace = function(e, t) {
            t && this.$search.set(t);
            var n = this.$search.find(this.session),
                r = 0;
            return n ? (this.$tryReplace(n, e) && (r = 1), n !== null && (this.selection.setSelectionRange(n), this.renderer.scrollSelectionIntoView(n.start, n.end)), r) : r
        }, this.replaceAll = function(e, t) {
            t && this.$search.set(t);
            var n = this.$search.findAll(this.session),
                r = 0;
            if (!n.length) return r;
            this.$blockScrolling += 1;
            var i = this.getSelectionRange();
            this.selection.moveTo(0, 0);
            for (var s = n.length - 1; s >= 0; --s) this.$tryReplace(n[s], e) && r++;
            return this.selection.setSelectionRange(i), this.$blockScrolling -= 1, r
        }, this.$tryReplace = function(e, t) {
            var n = this.session.getTextRange(e);
            return t = this.$search.replace(n, t), t !== null ? (e.end = this.session.replace(e, t), e) : null
        }, this.getLastSearchOptions = function() {
            return this.$search.getOptions()
        }, this.find = function(e, t, n) {
            t || (t = {}), typeof e == "string" || e instanceof RegExp ? t.needle = e : typeof e == "object" && r.mixin(t, e);
            var i = this.selection.getRange();
            t.needle == null && (e = this.session.getTextRange(i) || this.$search.$options.needle, e || (i = this.session.getWordRange(i.start.row, i.start.column), e = this.session.getTextRange(i)), this.$search.set({
                needle: e
            })), this.$search.set(t), t.start || this.$search.set({
                start: i
            });
            var s = this.$search.find(this.session);
            if (t.preventScroll) return s;
            if (s) return this.revealRange(s, n), s;
            t.backwards ? i.start = i.end : i.end = i.start, this.selection.setRange(i)
        }, this.findNext = function(e, t) {
            this.find({
                skipCurrent: !0,
                backwards: !1
            }, e, t)
        }, this.findPrevious = function(e, t) {
            this.find(e, {
                skipCurrent: !0,
                backwards: !0
            }, t)
        }, this.revealRange = function(e, t) {
            this.$blockScrolling += 1, this.session.unfold(e), this.selection.setSelectionRange(e), this.$blockScrolling -= 1;
            var n = this.renderer.scrollTop;
            this.renderer.scrollSelectionIntoView(e.start, e.end, .5), t !== !1 && this.renderer.animateScrolling(n)
        }, this.undo = function() {
            this.$blockScrolling++, this.session.getUndoManager().undo(), this.$blockScrolling--, this.renderer.scrollCursorIntoView(null, .5)
        }, this.redo = function() {
            this.$blockScrolling++, this.session.getUndoManager().redo(), this.$blockScrolling--, this.renderer.scrollCursorIntoView(null, .5)
        }, this.destroy = function() {
            this.renderer.destroy(), this._signal("destroy", this), this.session && this.session.destroy()
        }, this.setAutoScrollEditorIntoView = function(e) {
            if (!e) return;
            var t, n = this,
                r = !1;
            this.$scrollAnchor || (this.$scrollAnchor = document.createElement("div"));
            var i = this.$scrollAnchor;
            i.style.cssText = "position:absolute", this.container.insertBefore(i, this.container.firstChild);
            var s = this.on("changeSelection", function() {
                    r = !0
                }),
                o = this.renderer.on("beforeRender", function() {
                    r && (t = n.renderer.container.getBoundingClientRect())
                }),
                u = this.renderer.on("afterRender", function() {
                    if (r && t && (n.isFocused() || n.searchBox && n.searchBox.isFocused())) {
                        var e = n.renderer,
                            s = e.$cursorLayer.$pixelPos,
                            o = e.layerConfig,
                            u = s.top - o.offset;
                        s.top >= 0 && u + t.top < 0 ? r = !0 : s.top < o.height && s.top + t.top + o.lineHeight > window.innerHeight ? r = !1 : r = null, r != null && (i.style.top = u + "px", i.style.left = s.left + "px", i.style.height = o.lineHeight + "px", i.scrollIntoView(r)), r = t = null
                    }
                });
            this.setAutoScrollEditorIntoView = function(e) {
                if (e) return;
                delete this.setAutoScrollEditorIntoView, this.removeEventListener("changeSelection", s), this.renderer.removeEventListener("afterRender", u), this.renderer.removeEventListener("beforeRender", o)
            }
        }, this.$resetCursorStyle = function() {
            var e = this.$cursorStyle || "ace",
                t = this.renderer.$cursorLayer;
            if (!t) return;
            t.setSmoothBlinking(/smooth/.test(e)), t.isBlinking = !this.$readOnly && e != "wide", i.setCssClass(t.element, "ace_slim-cursors", /slim/.test(e))
        }
    }).call(b.prototype), g.defineOptions(b.prototype, "editor", {
        selectionStyle: {
            set: function(e) {
                this.onSelectionChange(), this._signal("changeSelectionStyle", {
                    data: e
                })
            },
            initialValue: "line"
        },
        highlightActiveLine: {
            set: function() {
                this.$updateHighlightActiveLine()
            },
            initialValue: !0
        },
        highlightSelectedWord: {
            set: function(e) {
                this.$onSelectionChange()
            },
            initialValue: !0
        },
        readOnly: {
            set: function(e) {
                this.$resetCursorStyle()
            },
            initialValue: !1
        },
        cursorStyle: {
            set: function(e) {
                this.$resetCursorStyle()
            },
            values: ["ace", "slim", "smooth", "wide"],
            initialValue: "ace"
        },
        mergeUndoDeltas: {
            values: [!1, !0, "always"],
            initialValue: !0
        },
        behavioursEnabled: {
            initialValue: !0
        },
        wrapBehavioursEnabled: {
            initialValue: !0
        },
        autoScrollEditorIntoView: {
            set: function(e) {
                this.setAutoScrollEditorIntoView(e)
            }
        },
        hScrollBarAlwaysVisible: "renderer",
        vScrollBarAlwaysVisible: "renderer",
        highlightGutterLine: "renderer",
        animatedScroll: "renderer",
        showInvisibles: "renderer",
        showPrintMargin: "renderer",
        printMarginColumn: "renderer",
        printMargin: "renderer",
        fadeFoldWidgets: "renderer",
        showFoldWidgets: "renderer",
        showLineNumbers: "renderer",
        showGutter: "renderer",
        displayIndentGuides: "renderer",
        fontSize: "renderer",
        fontFamily: "renderer",
        maxLines: "renderer",
        minLines: "renderer",
        scrollPastEnd: "renderer",
        fixedWidthGutter: "renderer",
        theme: "renderer",
        scrollSpeed: "$mouseHandler",
        dragDelay: "$mouseHandler",
        dragEnabled: "$mouseHandler",
        focusTimout: "$mouseHandler",
        tooltipFollowsMouse: "$mouseHandler",
        firstLineNumber: "session",
        overwrite: "session",
        newLineMode: "session",
        useWorker: "session",
        useSoftTabs: "session",
        tabSize: "session",
        wrap: "session",
        indentedSoftWrap: "session",
        foldStyle: "session",
        mode: "session"
    }), t.Editor = b
}), define("ace/undomanager", ["require", "exports", "module"], function(e, t, n) {
    "use strict";
    var r = function() {
        this.reset()
    };
    (function() {
        function e(e) {
            return {
                action: e.action,
                start: e.start,
                end: e.end,
                lines: e.lines.length == 1 ? null : e.lines,
                text: e.lines.length == 1 ? e.lines[0] : null
            }
        }

        function t(e) {
            return {
                action: e.action,
                start: e.start,
                end: e.end,
                lines: e.lines || [e.text]
            }
        }

        function n(e, t) {
            var n = new Array(e.length);
            for (var r = 0; r < e.length; r++) {
                var i = e[r],
                    s = {
                        group: i.group,
                        deltas: new Array(i.length)
                    };
                for (var o = 0; o < i.deltas.length; o++) {
                    var u = i.deltas[o];
                    s.deltas[o] = t(u)
                }
                n[r] = s
            }
            return n
        }
        this.execute = function(e) {
            var t = e.args[0];
            this.$doc = e.args[1], e.merge && this.hasUndo() && (this.dirtyCounter--, t = this.$undoStack.pop().concat(t)), this.$undoStack.push(t), this.$redoStack = [], this.dirtyCounter < 0 && (this.dirtyCounter = NaN), this.dirtyCounter++
        }, this.undo = function(e) {
            var t = this.$undoStack.pop(),
                n = null;
            return t && (n = this.$doc.undoChanges(this.$deserializeDeltas(t), e), this.$redoStack.push(t), this.dirtyCounter--), n
        }, this.redo = function(e) {
            var t = this.$redoStack.pop(),
                n = null;
            return t && (n = this.$doc.redoChanges(this.$deserializeDeltas(t), e), this.$undoStack.push(t), this.dirtyCounter++), n
        }, this.reset = function() {
            this.$undoStack = [], this.$redoStack = [], this.dirtyCounter = 0
        }, this.hasUndo = function() {
            return this.$undoStack.length > 0
        }, this.hasRedo = function() {
            return this.$redoStack.length > 0
        }, this.markClean = function() {
            this.dirtyCounter = 0
        }, this.isClean = function() {
            return this.dirtyCounter === 0
        }, this.$serializeDeltas = function(t) {
            return n(t, e)
        }, this.$deserializeDeltas = function(e) {
            return n(e, t)
        }
    }).call(r.prototype), t.UndoManager = r
}), define("ace/layer/gutter", ["require", "exports", "module", "ace/lib/dom", "ace/lib/oop", "ace/lib/lang", "ace/lib/event_emitter"], function(e, t, n) {
    "use strict";
    var r = e("../lib/dom"),
        i = e("../lib/oop"),
        s = e("../lib/lang"),
        o = e("../lib/event_emitter").EventEmitter,
        u = function(e) {
            this.element = r.createElement("div"), this.element.className = "ace_layer ace_gutter-layer", e.appendChild(this.element), this.setShowFoldWidgets(this.$showFoldWidgets), this.gutterWidth = 0, this.$annotations = [], this.$updateAnnotations = this.$updateAnnotations.bind(this), this.$cells = []
        };
    (function() {
        i.implement(this, o), this.setSession = function(e) {
            this.session && this.session.removeEventListener("change", this.$updateAnnotations), this.session = e, e && e.on("change", this.$updateAnnotations)
        }, this.addGutterDecoration = function(e, t) {
            window.console && console.warn && console.warn("deprecated use session.addGutterDecoration"), this.session.addGutterDecoration(e, t)
        }, this.removeGutterDecoration = function(e, t) {
            window.console && console.warn && console.warn("deprecated use session.removeGutterDecoration"), this.session.removeGutterDecoration(e, t)
        }, this.setAnnotations = function(e) {
            this.$annotations = [];
            for (var t = 0; t < e.length; t++) {
                var n = e[t],
                    r = n.row,
                    i = this.$annotations[r];
                i || (i = this.$annotations[r] = {
                    text: []
                });
                var o = n.text;
                o = o ? s.escapeHTML(o) : n.html || "", i.text.indexOf(o) === -1 && i.text.push(o);
                var u = n.type;
                u == "error" ? i.className = " ace_error" : u == "warning" && i.className != " ace_error" ? i.className = " ace_warning" : u == "info" && !i.className && (i.className = " ace_info")
            }
        }, this.$updateAnnotations = function(e) {
            if (!this.$annotations.length) return;
            var t = e.start.row,
                n = e.end.row - t;
            if (n !== 0)
                if (e.action == "remove") this.$annotations.splice(t, n + 1, null);
                else {
                    var r = new Array(n + 1);
                    r.unshift(t, 1), this.$annotations.splice.apply(this.$annotations, r)
                }
        }, this.update = function(e) {
            var t = this.session,
                n = e.firstRow,
                i = Math.min(e.lastRow + e.gutterOffset, t.getLength() - 1),
                s = t.getNextFoldLine(n),
                o = s ? s.start.row : Infinity,
                u = this.$showFoldWidgets && t.foldWidgets,
                a = t.$breakpoints,
                f = t.$decorations,
                l = t.$firstLineNumber,
                c = 0,
                h = t.gutterRenderer || this.$renderer,
                p = null,
                d = -1,
                v = n;
            for (;;) {
                v > o && (v = s.end.row + 1, s = t.getNextFoldLine(v, s), o = s ? s.start.row : Infinity);
                if (v > i) {
                    while (this.$cells.length > d + 1) p = this.$cells.pop(), this.element.removeChild(p.element);
                    break
                }
                p = this.$cells[++d], p || (p = {
                    element: null,
                    textNode: null,
                    foldWidget: null
                }, p.element = r.createElement("div"), p.textNode = document.createTextNode(""), p.element.appendChild(p.textNode), this.element.appendChild(p.element), this.$cells[d] = p);
                var m = "ace_gutter-cell ";
                a[v] && (m += a[v]), f[v] && (m += f[v]), this.$annotations[v] && (m += this.$annotations[v].className), p.element.className != m && (p.element.className = m);
                var g = t.getRowLength(v) * e.lineHeight + "px";
                g != p.element.style.height && (p.element.style.height = g);
                if (u) {
                    var y = u[v];
                    y == null && (y = u[v] = t.getFoldWidget(v))
                }
                if (y) {
                    p.foldWidget || (p.foldWidget = r.createElement("span"), p.element.appendChild(p.foldWidget));
                    var m = "ace_fold-widget ace_" + y;
                    y == "start" && v == o && v < s.end.row ? m += " ace_closed" : m += " ace_open", p.foldWidget.className != m && (p.foldWidget.className = m);
                    var g = e.lineHeight + "px";
                    p.foldWidget.style.height != g && (p.foldWidget.style.height = g)
                } else p.foldWidget && (p.element.removeChild(p.foldWidget), p.foldWidget = null);
                var b = c = h ? h.getText(t, v) : v + l;
                b != p.textNode.data && (p.textNode.data = b), v++
            }
            this.element.style.height = e.minHeight + "px";
            if (this.$fixedWidth || t.$useWrapMode) c = t.getLength() + l;
            var w = h ? h.getWidth(t, c, e) : c.toString().length * e.characterWidth,
                E = this.$padding || this.$computePadding();
            w += E.left + E.right, w !== this.gutterWidth && !isNaN(w) && (this.gutterWidth = w, this.element.style.width = Math.ceil(this.gutterWidth) + "px", this._emit("changeGutterWidth", w))
        }, this.$fixedWidth = !1, this.$showLineNumbers = !0, this.$renderer = "", this.setShowLineNumbers = function(e) {
            this.$renderer = !e && {
                getWidth: function() {
                    return ""
                },
                getText: function() {
                    return ""
                }
            }
        }, this.getShowLineNumbers = function() {
            return this.$showLineNumbers
        }, this.$showFoldWidgets = !0, this.setShowFoldWidgets = function(e) {
            e ? r.addCssClass(this.element, "ace_folding-enabled") : r.removeCssClass(this.element, "ace_folding-enabled"), this.$showFoldWidgets = e, this.$padding = null
        }, this.getShowFoldWidgets = function() {
            return this.$showFoldWidgets
        }, this.$computePadding = function() {
            if (!this.element.firstChild) return {
                left: 0,
                right: 0
            };
            var e = r.computedStyle(this.element.firstChild);
            return this.$padding = {}, this.$padding.left = parseInt(e.paddingLeft) + 1 || 0, this.$padding.right = parseInt(e.paddingRight) || 0, this.$padding
        }, this.getRegion = function(e) {
            var t = this.$padding || this.$computePadding(),
                n = this.element.getBoundingClientRect();
            if (e.x < t.left + n.left) return "markers";
            if (this.$showFoldWidgets && e.x > n.right - t.right) return "foldWidgets"
        }
    }).call(u.prototype), t.Gutter = u
}), define("ace/layer/marker", ["require", "exports", "module", "ace/range", "ace/lib/dom"], function(e, t, n) {
    "use strict";
    var r = e("../range").Range,
        i = e("../lib/dom"),
        s = function(e) {
            this.element = i.createElement("div"), this.element.className = "ace_layer ace_marker-layer", e.appendChild(this.element)
        };
    (function() {
        function e(e, t, n, r) {
            return (e ? 1 : 0) | (t ? 2 : 0) | (n ? 4 : 0) | (r ? 8 : 0)
        }
        this.$padding = 0, this.setPadding = function(e) {
            this.$padding = e
        }, this.setSession = function(e) {
            this.session = e
        }, this.setMarkers = function(e) {
            this.markers = e
        }, this.update = function(e) {
            var e = e || this.config;
            if (!e) return;
            this.config = e;
            var t = [];
            for (var n in this.markers) {
                var r = this.markers[n];
                if (!r.range) {
                    r.update(t, this, this.session, e);
                    continue
                }
                var i = r.range.clipRows(e.firstRow, e.lastRow);
                if (i.isEmpty()) continue;
                i = i.toScreenRange(this.session);
                if (r.renderer) {
                    var s = this.$getTop(i.start.row, e),
                        o = this.$padding + i.start.column * e.characterWidth;
                    r.renderer(t, i, o, s, e)
                } else r.type == "fullLine" ? this.drawFullLineMarker(t, i, r.clazz, e) : r.type == "screenLine" ? this.drawScreenLineMarker(t, i, r.clazz, e) : i.isMultiLine() ? r.type == "text" ? this.drawTextMarker(t, i, r.clazz, e) : this.drawMultiLineMarker(t, i, r.clazz, e) : this.drawSingleLineMarker(t, i, r.clazz + " ace_start" + " ace_br15", e)
            }
            this.element.innerHTML = t.join("")
        }, this.$getTop = function(e, t) {
            return (e - t.firstRowScreen) * t.lineHeight
        }, this.drawTextMarker = function(t, n, i, s, o) {
            var u = this.session,
                a = n.start.row,
                f = n.end.row,
                l = a,
                c = 0,
                h = 0,
                p = u.getScreenLastRowColumn(l),
                d = new r(l, n.start.column, l, h);
            for (; l <= f; l++) d.start.row = d.end.row = l, d.start.column = l == a ? n.start.column : u.getRowWrapIndent(l), d.end.column = p, c = h, h = p, p = l + 1 < f ? u.getScreenLastRowColumn(l + 1) : l == f ? 0 : n.end.column, this.drawSingleLineMarker(t, d, i + (l == a ? " ace_start" : "") + " ace_br" + e(l == a || l == a + 1 && n.start.column, c < h, h > p, l == f), s, l == f ? 0 : 1, o)
        }, this.drawMultiLineMarker = function(e, t, n, r, i) {
            var s = this.$padding,
                o = r.lineHeight,
                u = this.$getTop(t.start.row, r),
                a = s + t.start.column * r.characterWidth;
            i = i || "", e.push("<div class='", n, " ace_br1 ace_start' style='", "height:", o, "px;", "right:0;", "top:", u, "px;", "left:", a, "px;", i, "'></div>"), u = this.$getTop(t.end.row, r);
            var f = t.end.column * r.characterWidth;
            e.push("<div class='", n, " ace_br12' style='", "height:", o, "px;", "width:", f, "px;", "top:", u, "px;", "left:", s, "px;", i, "'></div>"), o = (t.end.row - t.start.row - 1) * r.lineHeight;
            if (o <= 0) return;
            u = this.$getTop(t.start.row + 1, r);
            var l = (t.start.column ? 1 : 0) | (t.end.column ? 0 : 8);
            e.push("<div class='", n, l ? " ace_br" + l : "", "' style='", "height:", o, "px;", "right:0;", "top:", u, "px;", "left:", s, "px;", i, "'></div>")
        }, this.drawSingleLineMarker = function(e, t, n, r, i, s) {
            var o = r.lineHeight,
                u = (t.end.column + (i || 0) - t.start.column) * r.characterWidth,
                a = this.$getTop(t.start.row, r),
                f = this.$padding + t.start.column * r.characterWidth;
            e.push("<div class='", n, "' style='", "height:", o, "px;", "width:", u, "px;", "top:", a, "px;", "left:", f, "px;", s || "", "'></div>")
        }, this.drawFullLineMarker = function(e, t, n, r, i) {
            var s = this.$getTop(t.start.row, r),
                o = r.lineHeight;
            t.start.row != t.end.row && (o += this.$getTop(t.end.row, r) - s), e.push("<div class='", n, "' style='", "height:", o, "px;", "top:", s, "px;", "left:0;right:0;", i || "", "'></div>")
        }, this.drawScreenLineMarker = function(e, t, n, r, i) {
            var s = this.$getTop(t.start.row, r),
                o = r.lineHeight;
            e.push("<div class='", n, "' style='", "height:", o, "px;", "top:", s, "px;", "left:0;right:0;", i || "", "'></div>")
        }
    }).call(s.prototype), t.Marker = s
}), define("ace/layer/text", ["require", "exports", "module", "ace/lib/oop", "ace/lib/dom", "ace/lib/lang", "ace/lib/useragent", "ace/lib/event_emitter"], function(e, t, n) {
    "use strict";
    var r = e("../lib/oop"),
        i = e("../lib/dom"),
        s = e("../lib/lang"),
        o = e("../lib/useragent"),
        u = e("../lib/event_emitter").EventEmitter,
        a = function(e) {
            this.element = i.createElement("div"), this.element.className = "ace_layer ace_text-layer", e.appendChild(this.element), this.$updateEolChar = this.$updateEolChar.bind(this)
        };
    (function() {
        r.implement(this, u), this.EOF_CHAR = "\u00b6", this.EOL_CHAR_LF = "\u00ac", this.EOL_CHAR_CRLF = "\u00a4", this.EOL_CHAR = this.EOL_CHAR_LF, this.TAB_CHAR = "\u2014", this.SPACE_CHAR = "\u00b7", this.$padding = 0, this.$updateEolChar = function() {
            var e = this.session.doc.getNewLineCharacter() == "\n" ? this.EOL_CHAR_LF : this.EOL_CHAR_CRLF;
            if (this.EOL_CHAR != e) return this.EOL_CHAR = e, !0
        }, this.setPadding = function(e) {
            this.$padding = e, this.element.style.padding = "0 " + e + "px"
        }, this.getLineHeight = function() {
            return this.$fontMetrics.$characterSize.height || 0
        }, this.getCharacterWidth = function() {
            return this.$fontMetrics.$characterSize.width || 0
        }, this.$setFontMetrics = function(e) {
            this.$fontMetrics = e, this.$fontMetrics.on("changeCharacterSize", function(e) {
                this._signal("changeCharacterSize", e)
            }.bind(this)), this.$pollSizeChanges()
        }, this.checkForSizeChanges = function() {
            this.$fontMetrics.checkForSizeChanges()
        }, this.$pollSizeChanges = function() {
            return this.$pollSizeChangesTimer = this.$fontMetrics.$pollSizeChanges()
        }, this.setSession = function(e) {
            this.session = e, e && this.$computeTabString()
        }, this.showInvisibles = !1, this.setShowInvisibles = function(e) {
            return this.showInvisibles == e ? !1 : (this.showInvisibles = e, this.$computeTabString(), !0)
        }, this.displayIndentGuides = !0, this.setDisplayIndentGuides = function(e) {
            return this.displayIndentGuides == e ? !1 : (this.displayIndentGuides = e, this.$computeTabString(), !0)
        }, this.$tabStrings = [], this.onChangeTabSize = this.$computeTabString = function() {
            var e = this.session.getTabSize();
            this.tabSize = e;
            var t = this.$tabStrings = [0];
            for (var n = 1; n < e + 1; n++) this.showInvisibles ? t.push("<span class='ace_invisible ace_invisible_tab'>" + s.stringRepeat(this.TAB_CHAR, n) + "</span>") : t.push(s.stringRepeat(" ", n));
            if (this.displayIndentGuides) {
                this.$indentGuideRe = /\s\S| \t|\t |\s$/;
                var r = "ace_indent-guide",
                    i = "",
                    o = "";
                if (this.showInvisibles) {
                    r += " ace_invisible", i = " ace_invisible_space", o = " ace_invisible_tab";
                    var u = s.stringRepeat(this.SPACE_CHAR, this.tabSize),
                        a = s.stringRepeat(this.TAB_CHAR, this.tabSize)
                } else var u = s.stringRepeat(" ", this.tabSize),
                    a = u;
                this.$tabStrings[" "] = "<span class='" + r + i + "'>" + u + "</span>", this.$tabStrings["  "] = "<span class='" + r + o + "'>" + a + "</span>"
            }
        }, this.updateLines = function(e, t, n) {
            (this.config.lastRow != e.lastRow || this.config.firstRow != e.firstRow) && this.scrollLines(e), this.config = e;
            var r = Math.max(t, e.firstRow),
                i = Math.min(n, e.lastRow),
                s = this.element.childNodes,
                o = 0;
            for (var u = e.firstRow; u < r; u++) {
                var a = this.session.getFoldLine(u);
                if (a) {
                    if (a.containsRow(r)) {
                        r = a.start.row;
                        break
                    }
                    u = a.end.row
                }
                o++
            }
            var u = r,
                a = this.session.getNextFoldLine(u),
                f = a ? a.start.row : Infinity;
            for (;;) {
                u > f && (u = a.end.row + 1, a = this.session.getNextFoldLine(u, a), f = a ? a.start.row : Infinity);
                if (u > i) break;
                var l = s[o++];
                if (l) {
                    var c = [];
                    this.$renderLine(c, u, !this.$useLineGroups(), u == f ? a : !1), l.style.height = e.lineHeight * this.session.getRowLength(u) + "px", l.innerHTML = c.join("")
                }
                u++
            }
        }, this.scrollLines = function(e) {
            var t = this.config;
            this.config = e;
            if (!t || t.lastRow < e.firstRow) return this.update(e);
            if (e.lastRow < t.firstRow) return this.update(e);
            var n = this.element;
            if (t.firstRow < e.firstRow)
                for (var r = this.session.getFoldedRowCount(t.firstRow, e.firstRow - 1); r > 0; r--) n.removeChild(n.firstChild);
            if (t.lastRow > e.lastRow)
                for (var r = this.session.getFoldedRowCount(e.lastRow + 1, t.lastRow); r > 0; r--) n.removeChild(n.lastChild);
            if (e.firstRow < t.firstRow) {
                var i = this.$renderLinesFragment(e, e.firstRow, t.firstRow - 1);
                n.firstChild ? n.insertBefore(i, n.firstChild) : n.appendChild(i)
            }
            if (e.lastRow > t.lastRow) {
                var i = this.$renderLinesFragment(e, t.lastRow + 1, e.lastRow);
                n.appendChild(i)
            }
        }, this.$renderLinesFragment = function(e, t, n) {
            var r = this.element.ownerDocument.createDocumentFragment(),
                s = t,
                o = this.session.getNextFoldLine(s),
                u = o ? o.start.row : Infinity;
            for (;;) {
                s > u && (s = o.end.row + 1, o = this.session.getNextFoldLine(s, o), u = o ? o.start.row : Infinity);
                if (s > n) break;
                var a = i.createElement("div"),
                    f = [];
                this.$renderLine(f, s, !1, s == u ? o : !1), a.innerHTML = f.join("");
                if (this.$useLineGroups()) a.className = "ace_line_group", r.appendChild(a), a.style.height = e.lineHeight * this.session.getRowLength(s) + "px";
                else
                    while (a.firstChild) r.appendChild(a.firstChild);
                s++
            }
            return r
        }, this.update = function(e) {
            this.config = e;
            var t = [],
                n = e.firstRow,
                r = e.lastRow,
                i = n,
                s = this.session.getNextFoldLine(i),
                o = s ? s.start.row : Infinity;
            for (;;) {
                i > o && (i = s.end.row + 1, s = this.session.getNextFoldLine(i, s), o = s ? s.start.row : Infinity);
                if (i > r) break;
                this.$useLineGroups() && t.push("<div class='ace_line_group' style='height:", e.lineHeight * this.session.getRowLength(i), "px'>"), this.$renderLine(t, i, !1, i == o ? s : !1), this.$useLineGroups() && t.push("</div>"), i++
            }
            this.element.innerHTML = t.join("")
        }, this.$textToken = {
            text: !0,
            rparen: !0,
            lparen: !0
        }, this.$renderToken = function(e, t, n, r) {
            var i = this,
                o = /\t|&|<|>|( +)|([\x00-\x1f\x80-\xa0\xad\u1680\u180E\u2000-\u200f\u2028\u2029\u202F\u205F\u3000\uFEFF])|[\u1100-\u115F\u11A3-\u11A7\u11FA-\u11FF\u2329-\u232A\u2E80-\u2E99\u2E9B-\u2EF3\u2F00-\u2FD5\u2FF0-\u2FFB\u3000-\u303E\u3041-\u3096\u3099-\u30FF\u3105-\u312D\u3131-\u318E\u3190-\u31BA\u31C0-\u31E3\u31F0-\u321E\u3220-\u3247\u3250-\u32FE\u3300-\u4DBF\u4E00-\uA48C\uA490-\uA4C6\uA960-\uA97C\uAC00-\uD7A3\uD7B0-\uD7C6\uD7CB-\uD7FB\uF900-\uFAFF\uFE10-\uFE19\uFE30-\uFE52\uFE54-\uFE66\uFE68-\uFE6B\uFF01-\uFF60\uFFE0-\uFFE6]/g,
                u = function(e, n, r, o, u) {
                    if (n) return i.showInvisibles ? "<span class='ace_invisible ace_invisible_space'>" + s.stringRepeat(i.SPACE_CHAR, e.length) + "</span>" : e;
                    if (e == "&") return "&#38;";
                    if (e == "<") return "&#60;";
                    if (e == ">") return "&#62;";
                    if (e == "  ") {
                        var a = i.session.getScreenTabSize(t + o);
                        return t += a - 1, i.$tabStrings[a]
                    }
                    if (e == "\u3000") {
                        var f = i.showInvisibles ? "ace_cjk ace_invisible ace_invisible_space" : "ace_cjk",
                            l = i.showInvisibles ? i.SPACE_CHAR : "";
                        return t += 1, "<span class='" + f + "' style='width:" + i.config.characterWidth * 2 + "px'>" + l + "</span>"
                    }
                    return r ? "<span class='ace_invisible ace_invisible_space ace_invalid'>" + i.SPACE_CHAR + "</span>" : (t += 1, "<span class='ace_cjk' style='width:" + i.config.characterWidth * 2 + "px'>" + e + "</span>")
                },
                a = r.replace(o, u);
            if (!this.$textToken[n.type]) {
                var f = "ace_" + n.type.replace(/\./g, " ace_"),
                    l = "";
                n.type == "fold" && (l = " style='width:" + n.value.length * this.config.characterWidth + "px;' "), e.push("<span class='", f, "'", l, ">", a, "</span>")
            } else e.push(a);
            return t + r.length
        }, this.renderIndentGuide = function(e, t, n) {
            var r = t.search(this.$indentGuideRe);
            return r <= 0 || r >= n ? t : t[0] == " " ? (r -= r % this.tabSize, e.push(s.stringRepeat(this.$tabStrings[" "], r / this.tabSize)), t.substr(r)) : t[0] == "   " ? (e.push(s.stringRepeat(this.$tabStrings["   "], r)), t.substr(r)) : t
        }, this.$renderWrappedLine = function(e, t, n, r) {
            var i = 0,
                o = 0,
                u = n[0],
                a = 0;
            for (var f = 0; f < t.length; f++) {
                var l = t[f],
                    c = l.value;
                if (f == 0 && this.displayIndentGuides) {
                    i = c.length, c = this.renderIndentGuide(e, c, u);
                    if (!c) continue;
                    i -= c.length
                }
                if (i + c.length < u) a = this.$renderToken(e, a, l, c), i += c.length;
                else {
                    while (i + c.length >= u) a = this.$renderToken(e, a, l, c.substring(0, u - i)), c = c.substring(u - i), i = u, r || e.push("</div>", "<div class='ace_line' style='height:", this.config.lineHeight, "px'>"), e.push(s.stringRepeat("\u00a0", n.indent)), o++, a = 0, u = n[o] || Number.MAX_VALUE;
                    c.length != 0 && (i += c.length, a = this.$renderToken(e, a, l, c))
                }
            }
        }, this.$renderSimpleLine = function(e, t) {
            var n = 0,
                r = t[0],
                i = r.value;
            this.displayIndentGuides && (i = this.renderIndentGuide(e, i)), i && (n = this.$renderToken(e, n, r, i));
            for (var s = 1; s < t.length; s++) r = t[s], i = r.value, n = this.$renderToken(e, n, r, i)
        }, this.$renderLine = function(e, t, n, r) {
            !r && r != 0 && (r = this.session.getFoldLine(t));
            if (r) var i = this.$getFoldLineTokens(t, r);
            else var i = this.session.getTokens(t);
            n || e.push("<div class='ace_line' style='height:", this.config.lineHeight * (this.$useLineGroups() ? 1 : this.session.getRowLength(t)), "px'>");
            if (i.length) {
                var s = this.session.getRowSplitData(t);
                s && s.length ? this.$renderWrappedLine(e, i, s, n) : this.$renderSimpleLine(e, i)
            }
            this.showInvisibles && (r && (t = r.end.row), e.push("<span class='ace_invisible ace_invisible_eol'>", t == this.session.getLength() - 1 ? this.EOF_CHAR : this.EOL_CHAR, "</span>")), n || e.push("</div>")
        }, this.$getFoldLineTokens = function(e, t) {
            function i(e, t, n) {
                var i = 0,
                    s = 0;
                while (s + e[i].value.length < t) {
                    s += e[i].value.length, i++;
                    if (i == e.length) return
                }
                if (s != t) {
                    var o = e[i].value.substring(t - s);
                    o.length > n - t && (o = o.substring(0, n - t)), r.push({
                        type: e[i].type,
                        value: o
                    }), s = t + o.length, i += 1
                }
                while (s < n && i < e.length) {
                    var o = e[i].value;
                    o.length + s > n ? r.push({
                        type: e[i].type,
                        value: o.substring(0, n - s)
                    }) : r.push(e[i]), s += o.length, i += 1
                }
            }
            var n = this.session,
                r = [],
                s = n.getTokens(e);
            return t.walk(function(e, t, o, u, a) {
                e != null ? r.push({
                    type: "fold",
                    value: e
                }) : (a && (s = n.getTokens(t)), s.length && i(s, u, o))
            }, t.end.row, this.session.getLine(t.end.row).length), r
        }, this.$useLineGroups = function() {
            return this.session.getUseWrapMode()
        }, this.destroy = function() {
            clearInterval(this.$pollSizeChangesTimer), this.$measureNode && this.$measureNode.parentNode.removeChild(this.$measureNode), delete this.$measureNode
        }
    }).call(a.prototype), t.Text = a
}), define("ace/layer/cursor", ["require", "exports", "module", "ace/lib/dom"], function(e, t, n) {
    "use strict";
    var r = e("../lib/dom"),
        i, s = function(e) {
            this.element = r.createElement("div"), this.element.className = "ace_layer ace_cursor-layer", e.appendChild(this.element), i === undefined && (i = !("opacity" in this.element.style)), this.isVisible = !1, this.isBlinking = !0, this.blinkInterval = 1e3, this.smoothBlinking = !1, this.cursors = [], this.cursor = this.addCursor(), r.addCssClass(this.element, "ace_hidden-cursors"), this.$updateCursors = (i ? this.$updateVisibility : this.$updateOpacity).bind(this)
        };
    (function() {
        this.$updateVisibility = function(e) {
            var t = this.cursors;
            for (var n = t.length; n--;) t[n].style.visibility = e ? "" : "hidden"
        }, this.$updateOpacity = function(e) {
            var t = this.cursors;
            for (var n = t.length; n--;) t[n].style.opacity = e ? "" : "0"
        }, this.$padding = 0, this.setPadding = function(e) {
            this.$padding = e
        }, this.setSession = function(e) {
            this.session = e
        }, this.setBlinking = function(e) {
            e != this.isBlinking && (this.isBlinking = e, this.restartTimer())
        }, this.setBlinkInterval = function(e) {
            e != this.blinkInterval && (this.blinkInterval = e, this.restartTimer())
        }, this.setSmoothBlinking = function(e) {
            e != this.smoothBlinking && !i && (this.smoothBlinking = e, r.setCssClass(this.element, "ace_smooth-blinking", e), this.$updateCursors(!0), this.$updateCursors = this.$updateOpacity.bind(this), this.restartTimer())
        }, this.addCursor = function() {
            var e = r.createElement("div");
            return e.className = "ace_cursor", this.element.appendChild(e), this.cursors.push(e), e
        }, this.removeCursor = function() {
            if (this.cursors.length > 1) {
                var e = this.cursors.pop();
                return e.parentNode.removeChild(e), e
            }
        }, this.hideCursor = function() {
            this.isVisible = !1, r.addCssClass(this.element, "ace_hidden-cursors"), this.restartTimer()
        }, this.showCursor = function() {
            this.isVisible = !0, r.removeCssClass(this.element, "ace_hidden-cursors"), this.restartTimer()
        }, this.restartTimer = function() {
            var e = this.$updateCursors;
            clearInterval(this.intervalId), clearTimeout(this.timeoutId), this.smoothBlinking && r.removeCssClass(this.element, "ace_smooth-blinking"), e(!0);
            if (!this.isBlinking || !this.blinkInterval || !this.isVisible) return;
            this.smoothBlinking && setTimeout(function() {
                r.addCssClass(this.element, "ace_smooth-blinking")
            }.bind(this));
            var t = function() {
                this.timeoutId = setTimeout(function() {
                    e(!1)
                }, .6 * this.blinkInterval)
            }.bind(this);
            this.intervalId = setInterval(function() {
                e(!0), t()
            }, this.blinkInterval), t()
        }, this.getPixelPosition = function(e, t) {
            if (!this.config || !this.session) return {
                left: 0,
                top: 0
            };
            e || (e = this.session.selection.getCursor());
            var n = this.session.documentToScreenPosition(e),
                r = this.$padding + n.column * this.config.characterWidth,
                i = (n.row - (t ? this.config.firstRowScreen : 0)) * this.config.lineHeight;
            return {
                left: r,
                top: i
            }
        }, this.update = function(e) {
            this.config = e;
            var t = this.session.$selectionMarkers,
                n = 0,
                r = 0;
            if (t === undefined || t.length === 0) t = [{
                cursor: null
            }];
            for (var n = 0, i = t.length; n < i; n++) {
                var s = this.getPixelPosition(t[n].cursor, !0);
                if ((s.top > e.height + e.offset || s.top < 0) && n > 1) continue;
                var o = (this.cursors[r++] || this.addCursor()).style;
                this.drawCursor ? this.drawCursor(o, s, e, t[n], this.session) : (o.left = s.left + "px", o.top = s.top + "px", o.width = e.characterWidth + "px", o.height = e.lineHeight + "px")
            }
            while (this.cursors.length > r) this.removeCursor();
            var u = this.session.getOverwrite();
            this.$setOverwrite(u), this.$pixelPos = s, this.restartTimer()
        }, this.drawCursor = null, this.$setOverwrite = function(e) {
            e != this.overwrite && (this.overwrite = e, e ? r.addCssClass(this.element, "ace_overwrite-cursors") : r.removeCssClass(this.element, "ace_overwrite-cursors"))
        }, this.destroy = function() {
            clearInterval(this.intervalId), clearTimeout(this.timeoutId)
        }
    }).call(s.prototype), t.Cursor = s
}), define("ace/scrollbar", ["require", "exports", "module", "ace/lib/oop", "ace/lib/dom", "ace/lib/event", "ace/lib/event_emitter"], function(e, t, n) {
    "use strict";
    var r = e("./lib/oop"),
        i = e("./lib/dom"),
        s = e("./lib/event"),
        o = e("./lib/event_emitter").EventEmitter,
        u = function(e) {
            this.element = i.createElement("div"), this.element.className = "ace_scrollbar ace_scrollbar" + this.classSuffix, this.inner = i.createElement("div"), this.inner.className = "ace_scrollbar-inner", this.element.appendChild(this.inner), e.appendChild(this.element), this.setVisible(!1), this.skipEvent = !1, s.addListener(this.element, "scroll", this.onScroll.bind(this)), s.addListener(this.element, "mousedown", s.preventDefault)
        };
    (function() {
        r.implement(this, o), this.setVisible = function(e) {
            this.element.style.display = e ? "" : "none", this.isVisible = e
        }
    }).call(u.prototype);
    var a = function(e, t) {
        u.call(this, e), this.scrollTop = 0, t.$scrollbarWidth = this.width = i.scrollbarWidth(e.ownerDocument), this.inner.style.width = this.element.style.width = (this.width || 15) + 5 + "px"
    };
    r.inherits(a, u),
        function() {
            this.classSuffix = "-v", this.onScroll = function() {
                this.skipEvent || (this.scrollTop = this.element.scrollTop, this._emit("scroll", {
                    data: this.scrollTop
                })), this.skipEvent = !1
            }, this.getWidth = function() {
                return this.isVisible ? this.width : 0
            }, this.setHeight = function(e) {
                this.element.style.height = e + "px"
            }, this.setInnerHeight = function(e) {
                this.inner.style.height = e + "px"
            }, this.setScrollHeight = function(e) {
                this.inner.style.height = e + "px"
            }, this.setScrollTop = function(e) {
                this.scrollTop != e && (this.skipEvent = !0, this.scrollTop = this.element.scrollTop = e)
            }
        }.call(a.prototype);
    var f = function(e, t) {
        u.call(this, e), this.scrollLeft = 0, this.height = t.$scrollbarWidth, this.inner.style.height = this.element.style.height = (this.height || 15) + 5 + "px"
    };
    r.inherits(f, u),
        function() {
            this.classSuffix = "-h", this.onScroll = function() {
                this.skipEvent || (this.scrollLeft = this.element.scrollLeft, this._emit("scroll", {
                    data: this.scrollLeft
                })), this.skipEvent = !1
            }, this.getHeight = function() {
                return this.isVisible ? this.height : 0
            }, this.setWidth = function(e) {
                this.element.style.width = e + "px"
            }, this.setInnerWidth = function(e) {
                this.inner.style.width = e + "px"
            }, this.setScrollWidth = function(e) {
                this.inner.style.width = e + "px"
            }, this.setScrollLeft = function(e) {
                this.scrollLeft != e && (this.skipEvent = !0, this.scrollLeft = this.element.scrollLeft = e)
            }
        }.call(f.prototype), t.ScrollBar = a, t.ScrollBarV = a, t.ScrollBarH = f, t.VScrollBar = a, t.HScrollBar = f
}), define("ace/renderloop", ["require", "exports", "module", "ace/lib/event"], function(e, t, n) {
    "use strict";
    var r = e("./lib/event"),
        i = function(e, t) {
            this.onRender = e, this.pending = !1, this.changes = 0, this.window = t || window
        };
    (function() {
        this.schedule = function(e) {
            this.changes = this.changes | e;
            if (!this.pending && this.changes) {
                this.pending = !0;
                var t = this;
                r.nextFrame(function() {
                    t.pending = !1;
                    var e;
                    while (e = t.changes) t.changes = 0, t.onRender(e)
                }, this.window)
            }
        }
    }).call(i.prototype), t.RenderLoop = i
}), define("ace/layer/font_metrics", ["require", "exports", "module", "ace/lib/oop", "ace/lib/dom", "ace/lib/lang", "ace/lib/useragent", "ace/lib/event_emitter"], function(e, t, n) {
    var r = e("../lib/oop"),
        i = e("../lib/dom"),
        s = e("../lib/lang"),
        o = e("../lib/useragent"),
        u = e("../lib/event_emitter").EventEmitter,
        a = 0,
        f = t.FontMetrics = function(e, t) {
            this.el = i.createElement("div"), this.$setMeasureNodeStyles(this.el.style, !0), this.$main = i.createElement("div"), this.$setMeasureNodeStyles(this.$main.style), this.$measureNode = i.createElement("div"), this.$setMeasureNodeStyles(this.$measureNode.style), this.el.appendChild(this.$main), this.el.appendChild(this.$measureNode), e.appendChild(this.el), a || this.$testFractionalRect(), this.$measureNode.innerHTML = s.stringRepeat("X", a), this.$characterSize = {
                width: 0,
                height: 0
            }, this.checkForSizeChanges()
        };
    (function() {
        r.implement(this, u), this.$characterSize = {
            width: 0,
            height: 0
        }, this.$testFractionalRect = function() {
            var e = i.createElement("div");
            this.$setMeasureNodeStyles(e.style), e.style.width = "0.2px", document.documentElement.appendChild(e);
            var t = e.getBoundingClientRect().width;
            t > 0 && t < 1 ? a = 50 : a = 100, e.parentNode.removeChild(e)
        }, this.$setMeasureNodeStyles = function(e, t) {
            e.width = e.height = "auto", e.left = e.top = "0px", e.visibility = "hidden", e.position = "absolute", e.whiteSpace = "pre", o.isIE < 8 ? e["font-family"] = "inherit" : e.font = "inherit", e.overflow = t ? "hidden" : "visible"
        }, this.checkForSizeChanges = function() {
            var e = this.$measureSizes();
            if (e && (this.$characterSize.width !== e.width || this.$characterSize.height !== e.height)) {
                this.$measureNode.style.fontWeight = "bold";
                var t = this.$measureSizes();
                this.$measureNode.style.fontWeight = "", this.$characterSize = e, this.charSizes = Object.create(null), this.allowBoldFonts = t && t.width === e.width && t.height === e.height, this._emit("changeCharacterSize", {
                    data: e
                })
            }
        }, this.$pollSizeChanges = function() {
            if (this.$pollSizeChangesTimer) return this.$pollSizeChangesTimer;
            var e = this;
            return this.$pollSizeChangesTimer = setInterval(function() {
                e.checkForSizeChanges()
            }, 500)
        }, this.setPolling = function(e) {
            e ? this.$pollSizeChanges() : this.$pollSizeChangesTimer && (clearInterval(this.$pollSizeChangesTimer), this.$pollSizeChangesTimer = 0)
        }, this.$measureSizes = function() {
            if (a === 50) {
                var e = null;
                try {
                    e = this.$measureNode.getBoundingClientRect()
                } catch (t) {
                    e = {
                        width: 0,
                        height: 0
                    }
                }
                var n = {
                    height: e.height,
                    width: e.width / a
                }
            } else var n = {
                height: this.$measureNode.clientHeight,
                width: this.$measureNode.clientWidth / a
            };
            return n.width === 0 || n.height === 0 ? null : n
        }, this.$measureCharWidth = function(e) {
            this.$main.innerHTML = s.stringRepeat(e, a);
            var t = this.$main.getBoundingClientRect();
            return t.width / a
        }, this.getCharacterWidth = function(e) {
            var t = this.charSizes[e];
            return t === undefined && (this.charSizes[e] = this.$measureCharWidth(e) / this.$characterSize.width), t
        }, this.destroy = function() {
            clearInterval(this.$pollSizeChangesTimer), this.el && this.el.parentNode && this.el.parentNode.removeChild(this.el)
        }
    }).call(f.prototype)
}), define("ace/virtual_renderer", ["require", "exports", "module", "ace/lib/oop", "ace/lib/dom", "ace/config", "ace/lib/useragent", "ace/layer/gutter", "ace/layer/marker", "ace/layer/text", "ace/layer/cursor", "ace/scrollbar", "ace/scrollbar", "ace/renderloop", "ace/layer/font_metrics", "ace/lib/event_emitter"], function(e, t, n) {
    "use strict";
    var r = e("./lib/oop"),
        i = e("./lib/dom"),
        s = e("./config"),
        o = e("./lib/useragent"),
        u = e("./layer/gutter").Gutter,
        a = e("./layer/marker").Marker,
        f = e("./layer/text").Text,
        l = e("./layer/cursor").Cursor,
        c = e("./scrollbar").HScrollBar,
        h = e("./scrollbar").VScrollBar,
        p = e("./renderloop").RenderLoop,
        d = e("./layer/font_metrics").FontMetrics,
        v = e("./lib/event_emitter").EventEmitter,
        m = '.ace_editor {position: relative;overflow: hidden;font: 12px/normal \'Monaco\', \'Menlo\', \'Ubuntu Mono\', \'Consolas\', \'source-code-pro\', monospace;direction: ltr;}.ace_scroller {position: absolute;overflow: hidden;top: 0;bottom: 0;background-color: inherit;-ms-user-select: none;-moz-user-select: none;-webkit-user-select: none;user-select: none;cursor: text;}.ace_content {position: absolute;-moz-box-sizing: border-box;-webkit-box-sizing: border-box;box-sizing: border-box;min-width: 100%;}.ace_dragging .ace_scroller:before{position: absolute;top: 0;left: 0;right: 0;bottom: 0;content: \'\';background: rgba(250, 250, 250, 0.01);z-index: 1000;}.ace_dragging.ace_dark .ace_scroller:before{background: rgba(0, 0, 0, 0.01);}.ace_selecting, .ace_selecting * {cursor: text !important;}.ace_gutter {position: absolute;overflow : hidden;width: auto;top: 0;bottom: 0;left: 0;cursor: default;z-index: 4;-ms-user-select: none;-moz-user-select: none;-webkit-user-select: none;user-select: none;}.ace_gutter-active-line {position: absolute;left: 0;right: 0;}.ace_scroller.ace_scroll-left {box-shadow: 17px 0 16px -16px rgba(0, 0, 0, 0.4) inset;}.ace_gutter-cell {padding-left: 19px;padding-right: 6px;background-repeat: no-repeat;}.ace_gutter-cell.ace_error {background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAABOFBMVEX/////////QRswFAb/Ui4wFAYwFAYwFAaWGAfDRymzOSH/PxswFAb/SiUwFAYwFAbUPRvjQiDllog5HhHdRybsTi3/Tyv9Tir+Syj/UC3////XurebMBIwFAb/RSHbPx/gUzfdwL3kzMivKBAwFAbbvbnhPx66NhowFAYwFAaZJg8wFAaxKBDZurf/RB6mMxb/SCMwFAYwFAbxQB3+RB4wFAb/Qhy4Oh+4QifbNRcwFAYwFAYwFAb/QRzdNhgwFAYwFAbav7v/Uy7oaE68MBK5LxLewr/r2NXewLswFAaxJw4wFAbkPRy2PyYwFAaxKhLm1tMwFAazPiQwFAaUGAb/QBrfOx3bvrv/VC/maE4wFAbRPBq6MRO8Qynew8Dp2tjfwb0wFAbx6eju5+by6uns4uH9/f36+vr/GkHjAAAAYnRSTlMAGt+64rnWu/bo8eAA4InH3+DwoN7j4eLi4xP99Nfg4+b+/u9B/eDs1MD1mO7+4PHg2MXa347g7vDizMLN4eG+Pv7i5evs/v79yu7S3/DV7/498Yv24eH+4ufQ3Ozu/v7+y13sRqwAAADLSURBVHjaZc/XDsFgGIBhtDrshlitmk2IrbHFqL2pvXf/+78DPokj7+Fz9qpU/9UXJIlhmPaTaQ6QPaz0mm+5gwkgovcV6GZzd5JtCQwgsxoHOvJO15kleRLAnMgHFIESUEPmawB9ngmelTtipwwfASilxOLyiV5UVUyVAfbG0cCPHig+GBkzAENHS0AstVF6bacZIOzgLmxsHbt2OecNgJC83JERmePUYq8ARGkJx6XtFsdddBQgZE2nPR6CICZhawjA4Fb/chv+399kfR+MMMDGOQAAAABJRU5ErkJggg==");background-repeat: no-repeat;background-position: 2px center;}.ace_gutter-cell.ace_warning {background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAmVBMVEX///8AAAD///8AAAAAAABPSzb/5sAAAAB/blH/73z/ulkAAAAAAAD85pkAAAAAAAACAgP/vGz/rkDerGbGrV7/pkQICAf////e0IsAAAD/oED/qTvhrnUAAAD/yHD/njcAAADuv2r/nz//oTj/p064oGf/zHAAAAA9Nir/tFIAAAD/tlTiuWf/tkIAAACynXEAAAAAAAAtIRW7zBpBAAAAM3RSTlMAABR1m7RXO8Ln31Z36zT+neXe5OzooRDfn+TZ4p3h2hTf4t3k3ucyrN1K5+Xaks52Sfs9CXgrAAAAjklEQVR42o3PbQ+CIBQFYEwboPhSYgoYunIqqLn6/z8uYdH8Vmdnu9vz4WwXgN/xTPRD2+sgOcZjsge/whXZgUaYYvT8QnuJaUrjrHUQreGczuEafQCO/SJTufTbroWsPgsllVhq3wJEk2jUSzX3CUEDJC84707djRc5MTAQxoLgupWRwW6UB5fS++NV8AbOZgnsC7BpEAAAAABJRU5ErkJggg==");background-position: 2px center;}.ace_gutter-cell.ace_info {background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAAAAAA6mKC9AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAAJ0Uk5TAAB2k804AAAAPklEQVQY02NgIB68QuO3tiLznjAwpKTgNyDbMegwisCHZUETUZV0ZqOquBpXj2rtnpSJT1AEnnRmL2OgGgAAIKkRQap2htgAAAAASUVORK5CYII=");background-position: 2px center;}.ace_dark .ace_gutter-cell.ace_info {background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQBAMAAADt3eJSAAAAJFBMVEUAAAChoaGAgIAqKiq+vr6tra1ZWVmUlJSbm5s8PDxubm56enrdgzg3AAAAAXRSTlMAQObYZgAAAClJREFUeNpjYMAPdsMYHegyJZFQBlsUlMFVCWUYKkAZMxZAGdxlDMQBAG+TBP4B6RyJAAAAAElFTkSuQmCC");}.ace_scrollbar {position: absolute;right: 0;bottom: 0;z-index: 6;}.ace_scrollbar-inner {position: absolute;cursor: text;left: 0;top: 0;}.ace_scrollbar-v{overflow-x: hidden;overflow-y: scroll;top: 0;}.ace_scrollbar-h {overflow-x: scroll;overflow-y: hidden;left: 0;}.ace_print-margin {position: absolute;height: 100%;}.ace_text-input {position: absolute;z-index: 0;width: 0.5em;height: 1em;opacity: 0;background: transparent;-moz-appearance: none;appearance: none;border: none;resize: none;outline: none;overflow: hidden;font: inherit;padding: 0 1px;margin: 0 -1px;text-indent: -1em;-ms-user-select: text;-moz-user-select: text;-webkit-user-select: text;user-select: text;white-space: pre!important;}.ace_text-input.ace_composition {background: inherit;color: inherit;z-index: 1000;opacity: 1;text-indent: 0;}.ace_layer {z-index: 1;position: absolute;overflow: hidden;word-wrap: normal;white-space: pre;height: 100%;width: 100%;-moz-box-sizing: border-box;-webkit-box-sizing: border-box;box-sizing: border-box;pointer-events: none;}.ace_gutter-layer {position: relative;width: auto;text-align: right;pointer-events: auto;}.ace_text-layer {font: inherit !important;}.ace_cjk {display: inline-block;text-align: center;}.ace_cursor-layer {z-index: 4;}.ace_cursor {z-index: 4;position: absolute;-moz-box-sizing: border-box;-webkit-box-sizing: border-box;box-sizing: border-box;border-left: 2px solid;transform: translatez(0);}.ace_slim-cursors .ace_cursor {border-left-width: 1px;}.ace_overwrite-cursors .ace_cursor {border-left-width: 0;border-bottom: 1px solid;}.ace_hidden-cursors .ace_cursor {opacity: 0.2;}.ace_smooth-blinking .ace_cursor {-webkit-transition: opacity 0.18s;transition: opacity 0.18s;}.ace_editor.ace_multiselect .ace_cursor {border-left-width: 1px;}.ace_marker-layer .ace_step, .ace_marker-layer .ace_stack {position: absolute;z-index: 3;}.ace_marker-layer .ace_selection {position: absolute;z-index: 5;}.ace_marker-layer .ace_bracket {position: absolute;z-index: 6;}.ace_marker-layer .ace_active-line {position: absolute;z-index: 2;}.ace_marker-layer .ace_selected-word {position: absolute;z-index: 4;-moz-box-sizing: border-box;-webkit-box-sizing: border-box;box-sizing: border-box;}.ace_line .ace_fold {-moz-box-sizing: border-box;-webkit-box-sizing: border-box;box-sizing: border-box;display: inline-block;height: 11px;margin-top: -2px;vertical-align: middle;background-image:url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAJCAYAAADU6McMAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAJpJREFUeNpi/P//PwOlgAXGYGRklAVSokD8GmjwY1wasKljQpYACtpCFeADcHVQfQyMQAwzwAZI3wJKvCLkfKBaMSClBlR7BOQikCFGQEErIH0VqkabiGCAqwUadAzZJRxQr/0gwiXIal8zQQPnNVTgJ1TdawL0T5gBIP1MUJNhBv2HKoQHHjqNrA4WO4zY0glyNKLT2KIfIMAAQsdgGiXvgnYAAAAASUVORK5CYII="),url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAA3CAYAAADNNiA5AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAACJJREFUeNpi+P//fxgTAwPDBxDxD078RSX+YeEyDFMCIMAAI3INmXiwf2YAAAAASUVORK5CYII=");background-repeat: no-repeat, repeat-x;background-position: center center, top left;color: transparent;border: 1px solid black;border-radius: 2px;cursor: pointer;pointer-events: auto;}.ace_dark .ace_fold {}.ace_fold:hover{background-image:url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAJCAYAAADU6McMAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAJpJREFUeNpi/P//PwOlgAXGYGRklAVSokD8GmjwY1wasKljQpYACtpCFeADcHVQfQyMQAwzwAZI3wJKvCLkfKBaMSClBlR7BOQikCFGQEErIH0VqkabiGCAqwUadAzZJRxQr/0gwiXIal8zQQPnNVTgJ1TdawL0T5gBIP1MUJNhBv2HKoQHHjqNrA4WO4zY0glyNKLT2KIfIMAAQsdgGiXvgnYAAAAASUVORK5CYII="),url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAA3CAYAAADNNiA5AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAACBJREFUeNpi+P//fz4TAwPDZxDxD5X4i5fLMEwJgAADAEPVDbjNw87ZAAAAAElFTkSuQmCC");}.ace_tooltip {background-color: #FFF;background-image: -webkit-linear-gradient(top, transparent, rgba(0, 0, 0, 0.1));background-image: linear-gradient(to bottom, transparent, rgba(0, 0, 0, 0.1));border: 1px solid gray;border-radius: 1px;box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);color: black;max-width: 100%;padding: 3px 4px;position: fixed;z-index: 999999;-moz-box-sizing: border-box;-webkit-box-sizing: border-box;box-sizing: border-box;cursor: default;white-space: pre;word-wrap: break-word;line-height: normal;font-style: normal;font-weight: normal;letter-spacing: normal;pointer-events: none;}.ace_folding-enabled > .ace_gutter-cell {padding-right: 13px;}.ace_fold-widget {-moz-box-sizing: border-box;-webkit-box-sizing: border-box;box-sizing: border-box;margin: 0 -12px 0 1px;display: none;width: 11px;vertical-align: top;background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAANElEQVR42mWKsQ0AMAzC8ixLlrzQjzmBiEjp0A6WwBCSPgKAXoLkqSot7nN3yMwR7pZ32NzpKkVoDBUxKAAAAABJRU5ErkJggg==");background-repeat: no-repeat;background-position: center;border-radius: 3px;border: 1px solid transparent;cursor: pointer;}.ace_folding-enabled .ace_fold-widget {display: inline-block;   }.ace_fold-widget.ace_end {background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAANElEQVR42m3HwQkAMAhD0YzsRchFKI7sAikeWkrxwScEB0nh5e7KTPWimZki4tYfVbX+MNl4pyZXejUO1QAAAABJRU5ErkJggg==");}.ace_fold-widget.ace_closed {background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAMAAAAGCAYAAAAG5SQMAAAAOUlEQVR42jXKwQkAMAgDwKwqKD4EwQ26sSOkVWjgIIHAzPiCgaqiqnJHZnKICBERHN194O5b9vbLuAVRL+l0YWnZAAAAAElFTkSuQmCCXA==");}.ace_fold-widget:hover {border: 1px solid rgba(0, 0, 0, 0.3);background-color: rgba(255, 255, 255, 0.2);box-shadow: 0 1px 1px rgba(255, 255, 255, 0.7);}.ace_fold-widget:active {border: 1px solid rgba(0, 0, 0, 0.4);background-color: rgba(0, 0, 0, 0.05);box-shadow: 0 1px 1px rgba(255, 255, 255, 0.8);}.ace_dark .ace_fold-widget {background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHklEQVQIW2P4//8/AzoGEQ7oGCaLLAhWiSwB146BAQCSTPYocqT0AAAAAElFTkSuQmCC");}.ace_dark .ace_fold-widget.ace_end {background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAH0lEQVQIW2P4//8/AxQ7wNjIAjDMgC4AxjCVKBirIAAF0kz2rlhxpAAAAABJRU5ErkJggg==");}.ace_dark .ace_fold-widget.ace_closed {background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAMAAAAFCAYAAACAcVaiAAAAHElEQVQIW2P4//+/AxAzgDADlOOAznHAKgPWAwARji8UIDTfQQAAAABJRU5ErkJggg==");}.ace_dark .ace_fold-widget:hover {box-shadow: 0 1px 1px rgba(255, 255, 255, 0.2);background-color: rgba(255, 255, 255, 0.1);}.ace_dark .ace_fold-widget:active {box-shadow: 0 1px 1px rgba(255, 255, 255, 0.2);}.ace_fold-widget.ace_invalid {background-color: #FFB4B4;border-color: #DE5555;}.ace_fade-fold-widgets .ace_fold-widget {-webkit-transition: opacity 0.4s ease 0.05s;transition: opacity 0.4s ease 0.05s;opacity: 0;}.ace_fade-fold-widgets:hover .ace_fold-widget {-webkit-transition: opacity 0.05s ease 0.05s;transition: opacity 0.05s ease 0.05s;opacity:1;}.ace_underline {text-decoration: underline;}.ace_bold {font-weight: bold;}.ace_nobold .ace_bold {font-weight: normal;}.ace_italic {font-style: italic;}.ace_error-marker {background-color: rgba(255, 0, 0,0.2);position: absolute;z-index: 9;}.ace_highlight-marker {background-color: rgba(255, 255, 0,0.2);position: absolute;z-index: 8;}.ace_br1 {border-top-left-radius    : 3px;}.ace_br2 {border-top-right-radius   : 3px;}.ace_br3 {border-top-left-radius    : 3px; border-top-right-radius:    3px;}.ace_br4 {border-bottom-right-radius: 3px;}.ace_br5 {border-top-left-radius    : 3px; border-bottom-right-radius: 3px;}.ace_br6 {border-top-right-radius   : 3px; border-bottom-right-radius: 3px;}.ace_br7 {border-top-left-radius    : 3px; border-top-right-radius:    3px; border-bottom-right-radius: 3px;}.ace_br8 {border-bottom-left-radius : 3px;}.ace_br9 {border-top-left-radius    : 3px; border-bottom-left-radius:  3px;}.ace_br10{border-top-right-radius   : 3px; border-bottom-left-radius:  3px;}.ace_br11{border-top-left-radius    : 3px; border-top-right-radius:    3px; border-bottom-left-radius:  3px;}.ace_br12{border-bottom-right-radius: 3px; border-bottom-left-radius:  3px;}.ace_br13{border-top-left-radius    : 3px; border-bottom-right-radius: 3px; border-bottom-left-radius:  3px;}.ace_br14{border-top-right-radius   : 3px; border-bottom-right-radius: 3px; border-bottom-left-radius:  3px;}.ace_br15{border-top-left-radius    : 3px; border-top-right-radius:    3px; border-bottom-right-radius: 3px; border-bottom-left-radius: 3px;}';
    i.importCssString(m, "ace_editor.css");
    var g = function(e, t) {
        var n = this;
        this.container = e || i.createElement("div"), this.$keepTextAreaAtCursor = !o.isOldIE, i.addCssClass(this.container, "ace_editor"), this.setTheme(t), this.$gutter = i.createElement("div"), this.$gutter.className = "ace_gutter", this.container.appendChild(this.$gutter), this.scroller = i.createElement("div"), this.scroller.className = "ace_scroller", this.container.appendChild(this.scroller), this.content = i.createElement("div"), this.content.className = "ace_content", this.scroller.appendChild(this.content), this.$gutterLayer = new u(this.$gutter), this.$gutterLayer.on("changeGutterWidth", this.onGutterResize.bind(this)), this.$markerBack = new a(this.content);
        var r = this.$textLayer = new f(this.content);
        this.canvas = r.element, this.$markerFront = new a(this.content), this.$cursorLayer = new l(this.content), this.$horizScroll = !1, this.$vScroll = !1, this.scrollBar = this.scrollBarV = new h(this.container, this), this.scrollBarH = new c(this.container, this), this.scrollBarV.addEventListener("scroll", function(e) {
            n.$scrollAnimation || n.session.setScrollTop(e.data - n.scrollMargin.top)
        }), this.scrollBarH.addEventListener("scroll", function(e) {
            n.$scrollAnimation || n.session.setScrollLeft(e.data - n.scrollMargin.left)
        }), this.scrollTop = 0, this.scrollLeft = 0, this.cursorPos = {
            row: 0,
            column: 0
        }, this.$fontMetrics = new d(this.container, 500), this.$textLayer.$setFontMetrics(this.$fontMetrics), this.$textLayer.addEventListener("changeCharacterSize", function(e) {
            n.updateCharacterSize(), n.onResize(!0, n.gutterWidth, n.$size.width, n.$size.height), n._signal("changeCharacterSize", e)
        }), this.$size = {
            width: 0,
            height: 0,
            scrollerHeight: 0,
            scrollerWidth: 0,
            $dirty: !0
        }, this.layerConfig = {
            width: 1,
            padding: 0,
            firstRow: 0,
            firstRowScreen: 0,
            lastRow: 0,
            lineHeight: 0,
            characterWidth: 0,
            minHeight: 1,
            maxHeight: 1,
            offset: 0,
            height: 1,
            gutterOffset: 1
        }, this.scrollMargin = {
            left: 0,
            right: 0,
            top: 0,
            bottom: 0,
            v: 0,
            h: 0
        }, this.$loop = new p(this.$renderChanges.bind(this), this.container.ownerDocument.defaultView), this.$loop.schedule(this.CHANGE_FULL), this.updateCharacterSize(), this.setPadding(4), s.resetOptions(this), s._emit("renderer", this)
    };
    (function() {
        this.CHANGE_CURSOR = 1, this.CHANGE_MARKER = 2, this.CHANGE_GUTTER = 4, this.CHANGE_SCROLL = 8, this.CHANGE_LINES = 16, this.CHANGE_TEXT = 32, this.CHANGE_SIZE = 64, this.CHANGE_MARKER_BACK = 128, this.CHANGE_MARKER_FRONT = 256, this.CHANGE_FULL = 512, this.CHANGE_H_SCROLL = 1024, r.implement(this, v), this.updateCharacterSize = function() {
            this.$textLayer.allowBoldFonts != this.$allowBoldFonts && (this.$allowBoldFonts = this.$textLayer.allowBoldFonts, this.setStyle("ace_nobold", !this.$allowBoldFonts)), this.layerConfig.characterWidth = this.characterWidth = this.$textLayer.getCharacterWidth(), this.layerConfig.lineHeight = this.lineHeight = this.$textLayer.getLineHeight(), this.$updatePrintMargin()
        }, this.setSession = function(e) {
            this.session && this.session.doc.off("changeNewLineMode", this.onChangeNewLineMode), this.session = e, e && this.scrollMargin.top && e.getScrollTop() <= 0 && e.setScrollTop(-this.scrollMargin.top), this.$cursorLayer.setSession(e), this.$markerBack.setSession(e), this.$markerFront.setSession(e), this.$gutterLayer.setSession(e), this.$textLayer.setSession(e);
            if (!e) return;
            this.$loop.schedule(this.CHANGE_FULL), this.session.$setFontMetrics(this.$fontMetrics), this.onChangeNewLineMode = this.onChangeNewLineMode.bind(this), this.onChangeNewLineMode(), this.session.doc.on("changeNewLineMode", this.onChangeNewLineMode)
        }, this.updateLines = function(e, t, n) {
            t === undefined && (t = Infinity), this.$changedLines ? (this.$changedLines.firstRow > e && (this.$changedLines.firstRow = e), this.$changedLines.lastRow < t && (this.$changedLines.lastRow = t)) : this.$changedLines = {
                firstRow: e,
                lastRow: t
            };
            if (this.$changedLines.lastRow < this.layerConfig.firstRow) {
                if (!n) return;
                this.$changedLines.lastRow = this.layerConfig.lastRow
            }
            if (this.$changedLines.firstRow > this.layerConfig.lastRow) return;
            this.$loop.schedule(this.CHANGE_LINES)
        }, this.onChangeNewLineMode = function() {
            this.$loop.schedule(this.CHANGE_TEXT), this.$textLayer.$updateEolChar()
        }, this.onChangeTabSize = function() {
            this.$loop.schedule(this.CHANGE_TEXT | this.CHANGE_MARKER), this.$textLayer.onChangeTabSize()
        }, this.updateText = function() {
            this.$loop.schedule(this.CHANGE_TEXT)
        }, this.updateFull = function(e) {
            e ? this.$renderChanges(this.CHANGE_FULL, !0) : this.$loop.schedule(this.CHANGE_FULL)
        }, this.updateFontSize = function() {
            this.$textLayer.checkForSizeChanges()
        }, this.$changes = 0, this.$updateSizeAsync = function() {
            this.$loop.pending ? this.$size.$dirty = !0 : this.onResize()
        }, this.onResize = function(e, t, n, r) {
            if (this.resizing > 2) return;
            this.resizing > 0 ? this.resizing++ : this.resizing = e ? 1 : 0;
            var i = this.container;
            r || (r = i.clientHeight || i.scrollHeight), n || (n = i.clientWidth || i.scrollWidth);
            var s = this.$updateCachedSize(e, t, n, r);
            if (!this.$size.scrollerHeight || !n && !r) return this.resizing = 0;
            e && (this.$gutterLayer.$padding = null), e ? this.$renderChanges(s | this.$changes, !0) : this.$loop.schedule(s | this.$changes), this.resizing && (this.resizing = 0), this.scrollBarV.scrollLeft = this.scrollBarV.scrollTop = null
        }, this.$updateCachedSize = function(e, t, n, r) {
            r -= this.$extraHeight || 0;
            var i = 0,
                s = this.$size,
                o = {
                    width: s.width,
                    height: s.height,
                    scrollerHeight: s.scrollerHeight,
                    scrollerWidth: s.scrollerWidth
                };
            r && (e || s.height != r) && (s.height = r, i |= this.CHANGE_SIZE, s.scrollerHeight = s.height, this.$horizScroll && (s.scrollerHeight -= this.scrollBarH.getHeight()), this.scrollBarV.element.style.bottom = this.scrollBarH.getHeight() + "px", i |= this.CHANGE_SCROLL);
            if (n && (e || s.width != n)) {
                i |= this.CHANGE_SIZE, s.width = n, t == null && (t = this.$showGutter ? this.$gutter.offsetWidth : 0), this.gutterWidth = t, this.scrollBarH.element.style.left = this.scroller.style.left = t + "px", s.scrollerWidth = Math.max(0, n - t - this.scrollBarV.getWidth()), this.scrollBarH.element.style.right = this.scroller.style.right = this.scrollBarV.getWidth() + "px", this.scroller.style.bottom = this.scrollBarH.getHeight() + "px";
                if (this.session && this.session.getUseWrapMode() && this.adjustWrapLimit() || e) i |= this.CHANGE_FULL
            }
            return s.$dirty = !n || !r, i && this._signal("resize", o), i
        }, this.onGutterResize = function() {
            var e = this.$showGutter ? this.$gutter.offsetWidth : 0;
            e != this.gutterWidth && (this.$changes |= this.$updateCachedSize(!0, e, this.$size.width, this.$size.height)), this.session.getUseWrapMode() && this.adjustWrapLimit() ? this.$loop.schedule(this.CHANGE_FULL) : this.$size.$dirty ? this.$loop.schedule(this.CHANGE_FULL) : (this.$computeLayerConfig(), this.$loop.schedule(this.CHANGE_MARKER))
        }, this.adjustWrapLimit = function() {
            var e = this.$size.scrollerWidth - this.$padding * 2,
                t = Math.floor(e / this.characterWidth);
            return this.session.adjustWrapLimit(t, this.$showPrintMargin && this.$printMarginColumn)
        }, this.setAnimatedScroll = function(e) {
            this.setOption("animatedScroll", e)
        }, this.getAnimatedScroll = function() {
            return this.$animatedScroll
        }, this.setShowInvisibles = function(e) {
            this.setOption("showInvisibles", e)
        }, this.getShowInvisibles = function() {
            return this.getOption("showInvisibles")
        }, this.getDisplayIndentGuides = function() {
            return this.getOption("displayIndentGuides")
        }, this.setDisplayIndentGuides = function(e) {
            this.setOption("displayIndentGuides", e)
        }, this.setShowPrintMargin = function(e) {
            this.setOption("showPrintMargin", e)
        }, this.getShowPrintMargin = function() {
            return this.getOption("showPrintMargin")
        }, this.setPrintMarginColumn = function(e) {
            this.setOption("printMarginColumn", e)
        }, this.getPrintMarginColumn = function() {
            return this.getOption("printMarginColumn")
        }, this.getShowGutter = function() {
            return this.getOption("showGutter")
        }, this.setShowGutter = function(e) {
            return this.setOption("showGutter", e)
        }, this.getFadeFoldWidgets = function() {
            return this.getOption("fadeFoldWidgets")
        }, this.setFadeFoldWidgets = function(e) {
            this.setOption("fadeFoldWidgets", e)
        }, this.setHighlightGutterLine = function(e) {
            this.setOption("highlightGutterLine", e)
        }, this.getHighlightGutterLine = function() {
            return this.getOption("highlightGutterLine")
        }, this.$updateGutterLineHighlight = function() {
            var e = this.$cursorLayer.$pixelPos,
                t = this.layerConfig.lineHeight;
            if (this.session.getUseWrapMode()) {
                var n = this.session.selection.getCursor();
                n.column = 0, e = this.$cursorLayer.getPixelPosition(n, !0), t *= this.session.getRowLength(n.row)
            }
            this.$gutterLineHighlight.style.top = e.top - this.layerConfig.offset + "px", this.$gutterLineHighlight.style.height = t + "px"
        }, this.$updatePrintMargin = function() {
            if (!this.$showPrintMargin && !this.$printMarginEl) return;
            if (!this.$printMarginEl) {
                var e = i.createElement("div");
                e.className = "ace_layer ace_print-margin-layer", this.$printMarginEl = i.createElement("div"), this.$printMarginEl.className = "ace_print-margin", e.appendChild(this.$printMarginEl), this.content.insertBefore(e, this.content.firstChild)
            }
            var t = this.$printMarginEl.style;
            t.left = this.characterWidth * this.$printMarginColumn + this.$padding + "px", t.visibility = this.$showPrintMargin ? "visible" : "hidden", this.session && this.session.$wrap == -1 && this.adjustWrapLimit()
        }, this.getContainerElement = function() {
            return this.container
        }, this.getMouseEventTarget = function() {
            return this.scroller
        }, this.getTextAreaContainer = function() {
            return this.container
        }, this.$moveTextAreaToCursor = function() {
            if (!this.$keepTextAreaAtCursor) return;
            var e = this.layerConfig,
                t = this.$cursorLayer.$pixelPos.top,
                n = this.$cursorLayer.$pixelPos.left;
            t -= e.offset;
            var r = this.textarea.style,
                i = this.lineHeight;
            if (t < 0 || t > e.height - i) {
                r.top = r.left = "0";
                return
            }
            var s = this.characterWidth;
            if (this.$composition) {
                var o = this.textarea.value.replace(/^\x01+/, "");
                s *= this.session.$getStringScreenWidth(o)[0] + 2, i += 2
            }
            n -= this.scrollLeft, n > this.$size.scrollerWidth - s && (n = this.$size.scrollerWidth - s), n += this.gutterWidth, r.height = i + "px", r.width = s + "px", r.left = Math.min(n, this.$size.scrollerWidth - s) + "px", r.top = Math.min(t, this.$size.height - i) + "px"
        // ODOO monkeypatch: When we use firefox top or bottom arrow the ace container does not scroll automatically if the cursor is not visible.
            this.$scrollViewToTextArea();
        }, this.$scrollViewToTextArea = function() {
            // scroll the page/container to the cursor
            var node = this.$cursorLayer.cursor;
            setTimeout(function () {
                if (node.scrollIntoViewIfNeeded) {
                    node.scrollIntoViewIfNeeded(false);
                } else if (node.scrollIntoView) {
                    var rect = node.getBoundingClientRect();
                    var parent = node.parentNode;

                    while (parent && parent.getBoundingClientRect) {
                        var parentRect = parent.getBoundingClientRect();
                        if (parentRect.bottom < rect.top) {
                            node.scrollIntoView(false);
                            return;
                        }
                        if (parentRect.top > rect.bottom-rect.height) {
                            node.scrollIntoView(true);
                            return;
                        }
                        if (parentRect.left > rect.right) {
                            node.scrollIntoView();
                            return;
                        }
                        if (parentRect.right < rect.left) {
                            node.scrollIntoView();
                            return;
                        }
                        parent = parent.parentNode;
                    }
                }
            });
        // ODOO end monkeypatch
        }, this.getFirstVisibleRow = function() {
            return this.layerConfig.firstRow
        }, this.getFirstFullyVisibleRow = function() {
            return this.layerConfig.firstRow + (this.layerConfig.offset === 0 ? 0 : 1)
        }, this.getLastFullyVisibleRow = function() {
            var e = Math.floor((this.layerConfig.height + this.layerConfig.offset) / this.layerConfig.lineHeight);
            return this.layerConfig.firstRow - 1 + e
        }, this.getLastVisibleRow = function() {
            return this.layerConfig.lastRow
        }, this.$padding = null, this.setPadding = function(e) {
            this.$padding = e, this.$textLayer.setPadding(e), this.$cursorLayer.setPadding(e), this.$markerFront.setPadding(e), this.$markerBack.setPadding(e), this.$loop.schedule(this.CHANGE_FULL), this.$updatePrintMargin()
        }, this.setScrollMargin = function(e, t, n, r) {
            var i = this.scrollMargin;
            i.top = e | 0, i.bottom = t | 0, i.right = r | 0, i.left = n | 0, i.v = i.top + i.bottom, i.h = i.left + i.right, i.top && this.scrollTop <= 0 && this.session && this.session.setScrollTop(-i.top), this.updateFull()
        }, this.getHScrollBarAlwaysVisible = function() {
            return this.$hScrollBarAlwaysVisible
        }, this.setHScrollBarAlwaysVisible = function(e) {
            this.setOption("hScrollBarAlwaysVisible", e)
        }, this.getVScrollBarAlwaysVisible = function() {
            return this.$vScrollBarAlwaysVisible
        }, this.setVScrollBarAlwaysVisible = function(e) {
            this.setOption("vScrollBarAlwaysVisible", e)
        }, this.$updateScrollBarV = function() {
            var e = this.layerConfig.maxHeight,
                t = this.$size.scrollerHeight;
            !this.$maxLines && this.$scrollPastEnd && (e -= (t - this.lineHeight) * this.$scrollPastEnd, this.scrollTop > e - t && (e = this.scrollTop + t, this.scrollBarV.scrollTop = null)), this.scrollBarV.setScrollHeight(e + this.scrollMargin.v), this.scrollBarV.setScrollTop(this.scrollTop + this.scrollMargin.top)
        }, this.$updateScrollBarH = function() {
            this.scrollBarH.setScrollWidth(this.layerConfig.width + 2 * this.$padding + this.scrollMargin.h), this.scrollBarH.setScrollLeft(this.scrollLeft + this.scrollMargin.left)
        }, this.$frozen = !1, this.freeze = function() {
            this.$frozen = !0
        }, this.unfreeze = function() {
            this.$frozen = !1
        }, this.$renderChanges = function(e, t) {
            this.$changes && (e |= this.$changes, this.$changes = 0);
            if (!this.session || !this.container.offsetWidth || this.$frozen || !e && !t) {
                this.$changes |= e;
                return
            }
            if (this.$size.$dirty) return this.$changes |= e, this.onResize(!0);
            this.lineHeight || this.$textLayer.checkForSizeChanges(), this._signal("beforeRender");
            var n = this.layerConfig;
            if (e & this.CHANGE_FULL || e & this.CHANGE_SIZE || e & this.CHANGE_TEXT || e & this.CHANGE_LINES || e & this.CHANGE_SCROLL || e & this.CHANGE_H_SCROLL) {
                e |= this.$computeLayerConfig();
                if (n.firstRow != this.layerConfig.firstRow && n.firstRowScreen == this.layerConfig.firstRowScreen) {
                    var r = this.scrollTop + (n.firstRow - this.layerConfig.firstRow) * this.lineHeight;
                    r > 0 && (this.scrollTop = r, e |= this.CHANGE_SCROLL, e |= this.$computeLayerConfig())
                }
                n = this.layerConfig, this.$updateScrollBarV(), e & this.CHANGE_H_SCROLL && this.$updateScrollBarH(), this.$gutterLayer.element.style.marginTop = -n.offset + "px", this.content.style.marginTop = -n.offset + "px", this.content.style.width = n.width + 2 * this.$padding + "px", this.content.style.height = n.minHeight + "px"
            }
            e & this.CHANGE_H_SCROLL && (this.content.style.marginLeft = -this.scrollLeft + "px", this.scroller.className = this.scrollLeft <= 0 ? "ace_scroller" : "ace_scroller ace_scroll-left");
            if (e & this.CHANGE_FULL) {
                this.$textLayer.update(n), this.$showGutter && this.$gutterLayer.update(n), this.$markerBack.update(n), this.$markerFront.update(n), this.$cursorLayer.update(n), this.$moveTextAreaToCursor(), this.$highlightGutterLine && this.$updateGutterLineHighlight(), this._signal("afterRender");
                return
            }
            if (e & this.CHANGE_SCROLL) {
                e & this.CHANGE_TEXT || e & this.CHANGE_LINES ? this.$textLayer.update(n) : this.$textLayer.scrollLines(n), this.$showGutter && this.$gutterLayer.update(n), this.$markerBack.update(n), this.$markerFront.update(n), this.$cursorLayer.update(n), this.$highlightGutterLine && this.$updateGutterLineHighlight(), this.$moveTextAreaToCursor(), this._signal("afterRender");
                return
            }
            e & this.CHANGE_TEXT ? (this.$textLayer.update(n), this.$showGutter && this.$gutterLayer.update(n)) : e & this.CHANGE_LINES ? (this.$updateLines() || e & this.CHANGE_GUTTER && this.$showGutter) && this.$gutterLayer.update(n) : (e & this.CHANGE_TEXT || e & this.CHANGE_GUTTER) && this.$showGutter && this.$gutterLayer.update(n), e & this.CHANGE_CURSOR && (this.$cursorLayer.update(n), this.$moveTextAreaToCursor(), this.$highlightGutterLine && this.$updateGutterLineHighlight()), e & (this.CHANGE_MARKER | this.CHANGE_MARKER_FRONT) && this.$markerFront.update(n), e & (this.CHANGE_MARKER | this.CHANGE_MARKER_BACK) && this.$markerBack.update(n), this._signal("afterRender")
        }, this.$autosize = function() {
            var e = this.session.getScreenLength() * this.lineHeight,
                t = this.$maxLines * this.lineHeight,
                n = Math.max((this.$minLines || 1) * this.lineHeight, Math.min(t, e)) + this.scrollMargin.v + (this.$extraHeight || 0);
            this.$horizScroll && (n += this.scrollBarH.getHeight());
            var r = e > t;
            if (n != this.desiredHeight || this.$size.height != this.desiredHeight || r != this.$vScroll) {
                r != this.$vScroll && (this.$vScroll = r, this.scrollBarV.setVisible(r));
                var i = this.container.clientWidth;
                this.container.style.height = n + "px", this.$updateCachedSize(!0, this.$gutterWidth, i, n), this.desiredHeight = n, this._signal("autosize")
            }
        }, this.$computeLayerConfig = function() {
            var e = this.session,
                t = this.$size,
                n = t.height <= 2 * this.lineHeight,
                r = this.session.getScreenLength(),
                i = r * this.lineHeight,
                s = this.$getLongestLine(),
                o = !n && (this.$hScrollBarAlwaysVisible || t.scrollerWidth - s - 2 * this.$padding < 0),
                u = this.$horizScroll !== o;
            u && (this.$horizScroll = o, this.scrollBarH.setVisible(o));
            var a = this.$vScroll;
            this.$maxLines && this.lineHeight > 1 && this.$autosize();
            var f = this.scrollTop % this.lineHeight,
                l = t.scrollerHeight + this.lineHeight,
                c = !this.$maxLines && this.$scrollPastEnd ? (t.scrollerHeight - this.lineHeight) * this.$scrollPastEnd : 0;
            i += c;
            var h = this.scrollMargin;
            this.session.setScrollTop(Math.max(-h.top, Math.min(this.scrollTop, i - t.scrollerHeight + h.bottom))), this.session.setScrollLeft(Math.max(-h.left, Math.min(this.scrollLeft, s + 2 * this.$padding - t.scrollerWidth + h.right)));
            var p = !n && (this.$vScrollBarAlwaysVisible || t.scrollerHeight - i + c < 0 || this.scrollTop > h.top),
                d = a !== p;
            d && (this.$vScroll = p, this.scrollBarV.setVisible(p));
            var v = Math.ceil(l / this.lineHeight) - 1,
                m = Math.max(0, Math.round((this.scrollTop - f) / this.lineHeight)),
                g = m + v,
                y, b, w = this.lineHeight;
            m = e.screenToDocumentRow(m, 0);
            var E = e.getFoldLine(m);
            E && (m = E.start.row), y = e.documentToScreenRow(m, 0), b = e.getRowLength(m) * w, g = Math.min(e.screenToDocumentRow(g, 0), e.getLength() - 1), l = t.scrollerHeight + e.getRowLength(g) * w + b, f = this.scrollTop - y * w;
            var S = 0;
            this.layerConfig.width != s && (S = this.CHANGE_H_SCROLL);
            if (u || d) S = this.$updateCachedSize(!0, this.gutterWidth, t.width, t.height), this._signal("scrollbarVisibilityChanged"), d && (s = this.$getLongestLine());
            return this.layerConfig = {
                width: s,
                padding: this.$padding,
                firstRow: m,
                firstRowScreen: y,
                lastRow: g,
                lineHeight: w,
                characterWidth: this.characterWidth,
                minHeight: l,
                maxHeight: i,
                offset: f,
                gutterOffset: Math.max(0, Math.ceil((f + t.height - t.scrollerHeight) / w)),
                height: this.$size.scrollerHeight
            }, S
        }, this.$updateLines = function() {
            var e = this.$changedLines.firstRow,
                t = this.$changedLines.lastRow;
            this.$changedLines = null;
            var n = this.layerConfig;
            if (e > n.lastRow + 1) return;
            if (t < n.firstRow) return;
            if (t === Infinity) {
                this.$showGutter && this.$gutterLayer.update(n), this.$textLayer.update(n);
                return
            }
            return this.$textLayer.updateLines(n, e, t), !0
        }, this.$getLongestLine = function() {
            var e = this.session.getScreenWidth();
            return this.showInvisibles && !this.session.$useWrapMode && (e += 1), Math.max(this.$size.scrollerWidth - 2 * this.$padding, Math.round(e * this.characterWidth))
        }, this.updateFrontMarkers = function() {
            this.$markerFront.setMarkers(this.session.getMarkers(!0)), this.$loop.schedule(this.CHANGE_MARKER_FRONT)
        }, this.updateBackMarkers = function() {
            this.$markerBack.setMarkers(this.session.getMarkers()), this.$loop.schedule(this.CHANGE_MARKER_BACK)
        }, this.addGutterDecoration = function(e, t) {
            this.$gutterLayer.addGutterDecoration(e, t)
        }, this.removeGutterDecoration = function(e, t) {
            this.$gutterLayer.removeGutterDecoration(e, t)
        }, this.updateBreakpoints = function(e) {
            this.$loop.schedule(this.CHANGE_GUTTER)
        }, this.setAnnotations = function(e) {
            this.$gutterLayer.setAnnotations(e), this.$loop.schedule(this.CHANGE_GUTTER)
        }, this.updateCursor = function() {
            this.$loop.schedule(this.CHANGE_CURSOR)
        }, this.hideCursor = function() {
            this.$cursorLayer.hideCursor()
        }, this.showCursor = function() {
            this.$cursorLayer.showCursor()
        }, this.scrollSelectionIntoView = function(e, t, n) {
            this.scrollCursorIntoView(e, n), this.scrollCursorIntoView(t, n)
        }, this.scrollCursorIntoView = function(e, t, n) {
            if (this.$size.scrollerHeight === 0) return;
            var r = this.$cursorLayer.getPixelPosition(e),
                i = r.left,
                s = r.top,
                o = n && n.top || 0,
                u = n && n.bottom || 0,
                a = this.$scrollAnimation ? this.session.getScrollTop() : this.scrollTop;
            a + o > s ? (t && (s -= t * this.$size.scrollerHeight), s === 0 && (s = -this.scrollMargin.top), this.session.setScrollTop(s)) : a + this.$size.scrollerHeight - u < s + this.lineHeight && (t && (s += t * this.$size.scrollerHeight), this.session.setScrollTop(s + this.lineHeight - this.$size.scrollerHeight));
            var f = this.scrollLeft;
            f > i ? (i < this.$padding + 2 * this.layerConfig.characterWidth && (i = -this.scrollMargin.left), this.session.setScrollLeft(i)) : f + this.$size.scrollerWidth < i + this.characterWidth ? this.session.setScrollLeft(Math.round(i + this.characterWidth - this.$size.scrollerWidth)) : f <= this.$padding && i - f < this.characterWidth && this.session.setScrollLeft(0)
        }, this.getScrollTop = function() {
            return this.session.getScrollTop()
        }, this.getScrollLeft = function() {
            return this.session.getScrollLeft()
        }, this.getScrollTopRow = function() {
            return this.scrollTop / this.lineHeight
        }, this.getScrollBottomRow = function() {
            return Math.max(0, Math.floor((this.scrollTop + this.$size.scrollerHeight) / this.lineHeight) - 1)
        }, this.scrollToRow = function(e) {
            this.session.setScrollTop(e * this.lineHeight)
        }, this.alignCursor = function(e, t) {
            typeof e == "number" && (e = {
                row: e,
                column: 0
            });
            var n = this.$cursorLayer.getPixelPosition(e),
                r = this.$size.scrollerHeight - this.lineHeight,
                i = n.top - r * (t || 0);
            return this.session.setScrollTop(i), i
        }, this.STEPS = 8, this.$calcSteps = function(e, t) {
            var n = 0,
                r = this.STEPS,
                i = [],
                s = function(e, t, n) {
                    return n * (Math.pow(e - 1, 3) + 1) + t
                };
            for (n = 0; n < r; ++n) i.push(s(n / this.STEPS, e, t - e));
            return i
        }, this.scrollToLine = function(e, t, n, r) {
            var i = this.$cursorLayer.getPixelPosition({
                    row: e,
                    column: 0
                }),
                s = i.top;
            t && (s -= this.$size.scrollerHeight / 2);
            var o = this.scrollTop;
            this.session.setScrollTop(s), n !== !1 && this.animateScrolling(o, r)
        }, this.animateScrolling = function(e, t) {
            var n = this.scrollTop;
            if (!this.$animatedScroll) return;
            var r = this;
            if (e == n) return;
            if (this.$scrollAnimation) {
                var i = this.$scrollAnimation.steps;
                if (i.length) {
                    e = i[0];
                    if (e == n) return
                }
            }
            var s = r.$calcSteps(e, n);
            this.$scrollAnimation = {
                from: e,
                to: n,
                steps: s
            }, clearInterval(this.$timer), r.session.setScrollTop(s.shift()), r.session.$scrollTop = n, this.$timer = setInterval(function() {
                s.length ? (r.session.setScrollTop(s.shift()), r.session.$scrollTop = n) : n != null ? (r.session.$scrollTop = -1, r.session.setScrollTop(n), n = null) : (r.$timer = clearInterval(r.$timer), r.$scrollAnimation = null, t && t())
            }, 10)
        }, this.scrollToY = function(e) {
            this.scrollTop !== e && (this.$loop.schedule(this.CHANGE_SCROLL), this.scrollTop = e)
        }, this.scrollToX = function(e) {
            this.scrollLeft !== e && (this.scrollLeft = e), this.$loop.schedule(this.CHANGE_H_SCROLL)
        }, this.scrollTo = function(e, t) {
            this.session.setScrollTop(t), this.session.setScrollLeft(t)
        }, this.scrollBy = function(e, t) {
            t && this.session.setScrollTop(this.session.getScrollTop() + t), e && this.session.setScrollLeft(this.session.getScrollLeft() + e)
        }, this.isScrollableBy = function(e, t) {
            if (t < 0 && this.session.getScrollTop() >= 1 - this.scrollMargin.top) return !0;
            if (t > 0 && this.session.getScrollTop() + this.$size.scrollerHeight - this.layerConfig.maxHeight < -1 + this.scrollMargin.bottom) return !0;
            if (e < 0 && this.session.getScrollLeft() >= 1 - this.scrollMargin.left) return !0;
            if (e > 0 && this.session.getScrollLeft() + this.$size.scrollerWidth - this.layerConfig.width < -1 + this.scrollMargin.right) return !0
        }, this.pixelToScreenCoordinates = function(e, t) {
            var n = this.scroller.getBoundingClientRect(),
                r = (e + this.scrollLeft - n.left - this.$padding) / this.characterWidth,
                i = Math.floor((t + this.scrollTop - n.top) / this.lineHeight),
                s = Math.round(r);
            return {
                row: i,
                column: s,
                side: r - s > 0 ? 1 : -1
            }
        }, this.screenToTextCoordinates = function(e, t) {
            var n = this.scroller.getBoundingClientRect(),
                r = Math.round((e + this.scrollLeft - n.left - this.$padding) / this.characterWidth),
                i = (t + this.scrollTop - n.top) / this.lineHeight;
            return this.session.screenToDocumentPosition(i, Math.max(r, 0))
        }, this.textToScreenCoordinates = function(e, t) {
            var n = this.scroller.getBoundingClientRect(),
                r = this.session.documentToScreenPosition(e, t),
                i = this.$padding + Math.round(r.column * this.characterWidth),
                s = r.row * this.lineHeight;
            return {
                pageX: n.left + i - this.scrollLeft,
                pageY: n.top + s - this.scrollTop
            }
        }, this.visualizeFocus = function() {
            i.addCssClass(this.container, "ace_focus")
        }, this.visualizeBlur = function() {
            i.removeCssClass(this.container, "ace_focus")
        }, this.showComposition = function(e) {
            this.$composition || (this.$composition = {
                keepTextAreaAtCursor: this.$keepTextAreaAtCursor,
                cssText: this.textarea.style.cssText
            }), this.$keepTextAreaAtCursor = !0, i.addCssClass(this.textarea, "ace_composition"), this.textarea.style.cssText = "", this.$moveTextAreaToCursor()
        }, this.setCompositionText = function(e) {
            this.$moveTextAreaToCursor()
        }, this.hideComposition = function() {
            if (!this.$composition) return;
            i.removeCssClass(this.textarea, "ace_composition"), this.$keepTextAreaAtCursor = this.$composition.keepTextAreaAtCursor, this.textarea.style.cssText = this.$composition.cssText, this.$composition = null
        }, this.setTheme = function(e, t) {
            function o(r) {
                if (n.$themeId != e) return t && t();
                if (!r.cssClass) return;
                i.importCssString(r.cssText, r.cssClass, n.container.ownerDocument), n.theme && i.removeCssClass(n.container, n.theme.cssClass);
                var s = "padding" in r ? r.padding : "padding" in (n.theme || {}) ? 4 : n.$padding;
                n.$padding && s != n.$padding && n.setPadding(s), n.$theme = r.cssClass, n.theme = r, i.addCssClass(n.container, r.cssClass), i.setCssClass(n.container, "ace_dark", r.isDark), n.$size && (n.$size.width = 0, n.$updateSizeAsync()), n._dispatchEvent("themeLoaded", {
                    theme: r
                }), t && t()
            }
            var n = this;
            this.$themeId = e, n._dispatchEvent("themeChange", {
                theme: e
            });
            if (!e || typeof e == "string") {
                var r = e || this.$options.theme.initialValue;
                s.loadModule(["theme", r], o)
            } else o(e)
        }, this.getTheme = function() {
            return this.$themeId
        }, this.setStyle = function(e, t) {
            i.setCssClass(this.container, e, t !== !1)
        }, this.unsetStyle = function(e) {
            i.removeCssClass(this.container, e)
        }, this.setCursorStyle = function(e) {
            this.scroller.style.cursor != e && (this.scroller.style.cursor = e)
        }, this.setMouseCursor = function(e) {
            this.scroller.style.cursor = e
        }, this.destroy = function() {
            this.$textLayer.destroy(), this.$cursorLayer.destroy()
        }
    }).call(g.prototype), s.defineOptions(g.prototype, "renderer", {
        animatedScroll: {
            initialValue: !1
        },
        showInvisibles: {
            set: function(e) {
                this.$textLayer.setShowInvisibles(e) && this.$loop.schedule(this.CHANGE_TEXT)
            },
            initialValue: !1
        },
        showPrintMargin: {
            set: function() {
                this.$updatePrintMargin()
            },
            initialValue: !0
        },
        printMarginColumn: {
            set: function() {
                this.$updatePrintMargin()
            },
            initialValue: 80
        },
        printMargin: {
            set: function(e) {
                typeof e == "number" && (this.$printMarginColumn = e), this.$showPrintMargin = !!e, this.$updatePrintMargin()
            },
            get: function() {
                return this.$showPrintMargin && this.$printMarginColumn
            }
        },
        showGutter: {
            set: function(e) {
                this.$gutter.style.display = e ? "block" : "none", this.$loop.schedule(this.CHANGE_FULL), this.onGutterResize()
            },
            initialValue: !0
        },
        fadeFoldWidgets: {
            set: function(e) {
                i.setCssClass(this.$gutter, "ace_fade-fold-widgets", e)
            },
            initialValue: !1
        },
        showFoldWidgets: {
            set: function(e) {
                this.$gutterLayer.setShowFoldWidgets(e)
            },
            initialValue: !0
        },
        showLineNumbers: {
            set: function(e) {
                this.$gutterLayer.setShowLineNumbers(e), this.$loop.schedule(this.CHANGE_GUTTER)
            },
            initialValue: !0
        },
        displayIndentGuides: {
            set: function(e) {
                this.$textLayer.setDisplayIndentGuides(e) && this.$loop.schedule(this.CHANGE_TEXT)
            },
            initialValue: !0
        },
        highlightGutterLine: {
            set: function(e) {
                if (!this.$gutterLineHighlight) {
                    this.$gutterLineHighlight = i.createElement("div"), this.$gutterLineHighlight.className = "ace_gutter-active-line", this.$gutter.appendChild(this.$gutterLineHighlight);
                    return
                }
                this.$gutterLineHighlight.style.display = e ? "" : "none", this.$cursorLayer.$pixelPos && this.$updateGutterLineHighlight()
            },
            initialValue: !1,
            value: !0
        },
        hScrollBarAlwaysVisible: {
            set: function(e) {
                (!this.$hScrollBarAlwaysVisible || !this.$horizScroll) && this.$loop.schedule(this.CHANGE_SCROLL)
            },
            initialValue: !1
        },
        vScrollBarAlwaysVisible: {
            set: function(e) {
                (!this.$vScrollBarAlwaysVisible || !this.$vScroll) && this.$loop.schedule(this.CHANGE_SCROLL)
            },
            initialValue: !1
        },
        fontSize: {
            set: function(e) {
                typeof e == "number" && (e += "px"), this.container.style.fontSize = e, this.updateFontSize()
            },
            initialValue: 12
        },
        fontFamily: {
            set: function(e) {
                this.container.style.fontFamily = e, this.updateFontSize()
            }
        },
        maxLines: {
            set: function(e) {
                this.updateFull()
            }
        },
        minLines: {
            set: function(e) {
                this.updateFull()
            }
        },
        scrollPastEnd: {
            set: function(e) {
                e = +e || 0;
                if (this.$scrollPastEnd == e) return;
                this.$scrollPastEnd = e, this.$loop.schedule(this.CHANGE_SCROLL)
            },
            initialValue: 0,
            handlesSet: !0
        },
        fixedWidthGutter: {
            set: function(e) {
                this.$gutterLayer.$fixedWidth = !!e, this.$loop.schedule(this.CHANGE_GUTTER)
            }
        },
        theme: {
            set: function(e) {
                this.setTheme(e)
            },
            get: function() {
                return this.$themeId || this.theme
            },
            initialValue: "./theme/textmate",
            handlesSet: !0
        }
    }), t.VirtualRenderer = g
}), define("ace/worker/worker_client", ["require", "exports", "module", "ace/lib/oop", "ace/lib/net", "ace/lib/event_emitter", "ace/config"], function(e, t, n) {
    "use strict";
    var r = e("../lib/oop"),
        i = e("../lib/net"),
        s = e("../lib/event_emitter").EventEmitter,
        o = e("../config"),
        u = function(t, n, r, i) {
            this.$sendDeltaQueue = this.$sendDeltaQueue.bind(this), this.changeListener = this.changeListener.bind(this), this.onMessage = this.onMessage.bind(this), e.nameToUrl && !e.toUrl && (e.toUrl = e.nameToUrl);
            if (o.get("packaged") || !e.toUrl) i = i || o.moduleUrl(n, "worker");
            else {
                var s = this.$normalizePath;
                i = i || s(e.toUrl("ace/worker/worker.js", null, "_"));
                var u = {};
                t.forEach(function(t) {
                    u[t] = s(e.toUrl(t, null, "_").replace(/(\.js)?(\?.*)?$/, ""))
                })
            }
            try {
                this.$worker = new Worker(i)
            } catch (a) {
                if (!(a instanceof window.DOMException)) throw a;
                var f = this.$workerBlob(i),
                    l = window.URL || window.webkitURL,
                    c = l.createObjectURL(f);
                this.$worker = new Worker(c), l.revokeObjectURL(c)
            }
            this.$worker.postMessage({
                init: !0,
                tlns: u,
                module: n,
                classname: r
            }), this.callbackId = 1, this.callbacks = {}, this.$worker.onmessage = this.onMessage
        };
    (function() {
        r.implement(this, s), this.onMessage = function(e) {
            var t = e.data;
            switch (t.type) {
                case "event":
                    this._signal(t.name, {
                        data: t.data
                    });
                    break;
                case "call":
                    var n = this.callbacks[t.id];
                    n && (n(t.data), delete this.callbacks[t.id]);
                    break;
                case "error":
                    this.reportError(t.data);
                    break;
                case "log":
                    window.console && console.log && console.log.apply(console, t.data)
            }
        }, this.reportError = function(e) {
            window.console && console.error && console.error(e)
        }, this.$normalizePath = function(e) {
            return i.qualifyURL(e)
        }, this.terminate = function() {
            this._signal("terminate", {}), this.deltaQueue = null, this.$worker.terminate(), this.$worker = null, this.$doc && this.$doc.off("change", this.changeListener), this.$doc = null
        }, this.send = function(e, t) {
            this.$worker.postMessage({
                command: e,
                args: t
            })
        }, this.call = function(e, t, n) {
            if (n) {
                var r = this.callbackId++;
                this.callbacks[r] = n, t.push(r)
            }
            this.send(e, t)
        }, this.emit = function(e, t) {
            try {
                this.$worker.postMessage({
                    event: e,
                    data: {
                        data: t.data
                    }
                })
            } catch (n) {
                console.error(n.stack)
            }
        }, this.attachToDocument = function(e) {
            this.$doc && this.terminate(), this.$doc = e, this.call("setValue", [e.getValue()]), e.on("change", this.changeListener)
        }, this.changeListener = function(e) {
            this.deltaQueue || (this.deltaQueue = [], setTimeout(this.$sendDeltaQueue, 0)), e.action == "insert" ? this.deltaQueue.push(e.start, e.lines) : this.deltaQueue.push(e.start, e.end)
        }, this.$sendDeltaQueue = function() {
            var e = this.deltaQueue;
            if (!e) return;
            this.deltaQueue = null, e.length > 50 && e.length > this.$doc.getLength() >> 1 ? this.call("setValue", [this.$doc.getValue()]) : this.emit("change", {
                data: e
            })
        }, this.$workerBlob = function(e) {
            var t = "importScripts('" + i.qualifyURL(e) + "');";
            try {
                return new Blob([t], {
                    type: "application/javascript"
                })
            } catch (n) {
                var r = window.BlobBuilder || window.WebKitBlobBuilder || window.MozBlobBuilder,
                    s = new r;
                return s.append(t), s.getBlob("application/javascript")
            }
        }
    }).call(u.prototype);
    var a = function(e, t, n) {
        this.$sendDeltaQueue = this.$sendDeltaQueue.bind(this), this.changeListener = this.changeListener.bind(this), this.callbackId = 1, this.callbacks = {}, this.messageBuffer = [];
        var r = null,
            i = !1,
            u = Object.create(s),
            a = this;
        this.$worker = {}, this.$worker.terminate = function() {}, this.$worker.postMessage = function(e) {
            a.messageBuffer.push(e), r && (i ? setTimeout(f) : f())
        }, this.setEmitSync = function(e) {
            i = e
        };
        var f = function() {
            var e = a.messageBuffer.shift();
            e.command ? r[e.command].apply(r, e.args) : e.event && u._signal(e.event, e.data)
        };
        u.postMessage = function(e) {
            a.onMessage({
                data: e
            })
        }, u.callback = function(e, t) {
            this.postMessage({
                type: "call",
                id: t,
                data: e
            })
        }, u.emit = function(e, t) {
            this.postMessage({
                type: "event",
                name: e,
                data: t
            })
        }, o.loadModule(["worker", t], function(e) {
            r = new e[n](u);
            while (a.messageBuffer.length) f()
        })
    };
    a.prototype = u.prototype, t.UIWorkerClient = a, t.WorkerClient = u
}), define("ace/placeholder", ["require", "exports", "module", "ace/range", "ace/lib/event_emitter", "ace/lib/oop"], function(e, t, n) {
    "use strict";
    var r = e("./range").Range,
        i = e("./lib/event_emitter").EventEmitter,
        s = e("./lib/oop"),
        o = function(e, t, n, r, i, s) {
            var o = this;
            this.length = t, this.session = e, this.doc = e.getDocument(), this.mainClass = i, this.othersClass = s, this.$onUpdate = this.onUpdate.bind(this), this.doc.on("change", this.$onUpdate), this.$others = r, this.$onCursorChange = function() {
                setTimeout(function() {
                    o.onCursorChange()
                })
            }, this.$pos = n;
            var u = e.getUndoManager().$undoStack || e.getUndoManager().$undostack || {
                length: -1
            };
            this.$undoStackDepth = u.length, this.setup(), e.selection.on("changeCursor", this.$onCursorChange)
        };
    (function() {
        s.implement(this, i), this.setup = function() {
            var e = this,
                t = this.doc,
                n = this.session,
                i = this.$pos;
            this.selectionBefore = n.selection.toJSON(), n.selection.inMultiSelectMode && n.selection.toSingleRange(), this.pos = t.createAnchor(i.row, i.column), this.markerId = n.addMarker(new r(i.row, i.column, i.row, i.column + this.length), this.mainClass, null, !1), this.pos.on("change", function(t) {
                n.removeMarker(e.markerId), e.markerId = n.addMarker(new r(t.value.row, t.value.column, t.value.row, t.value.column + e.length), e.mainClass, null, !1)
            }), this.others = [], this.$others.forEach(function(n) {
                var r = t.createAnchor(n.row, n.column);
                e.others.push(r)
            }), n.setUndoSelect(!1)
        }, this.showOtherMarkers = function() {
            if (this.othersActive) return;
            var e = this.session,
                t = this;
            this.othersActive = !0, this.others.forEach(function(n) {
                n.markerId = e.addMarker(new r(n.row, n.column, n.row, n.column + t.length), t.othersClass, null, !1), n.on("change", function(i) {
                    e.removeMarker(n.markerId), n.markerId = e.addMarker(new r(i.value.row, i.value.column, i.value.row, i.value.column + t.length), t.othersClass, null, !1)
                })
            })
        }, this.hideOtherMarkers = function() {
            if (!this.othersActive) return;
            this.othersActive = !1;
            for (var e = 0; e < this.others.length; e++) this.session.removeMarker(this.others[e].markerId)
        }, this.onUpdate = function(e) {
            var t = e;
            if (t.start.row !== t.end.row) return;
            if (t.start.row !== this.pos.row) return;
            if (this.$updating) return;
            this.$updating = !0;
            var n = e.action === "insert" ? t.end.column - t.start.column : t.start.column - t.end.column;
            if (t.start.column >= this.pos.column && t.start.column <= this.pos.column + this.length + 1) {
                var i = t.start.column - this.pos.column;
                this.length += n;
                if (!this.session.$fromUndo) {
                    if (e.action === "insert")
                        for (var s = this.others.length - 1; s >= 0; s--) {
                            var o = this.others[s],
                                u = {
                                    row: o.row,
                                    column: o.column + i
                                };
                            o.row === t.start.row && t.start.column < o.column && (u.column += n), this.doc.insertMergedLines(u, e.lines)
                        } else if (e.action === "remove")
                            for (var s = this.others.length - 1; s >= 0; s--) {
                                var o = this.others[s],
                                    u = {
                                        row: o.row,
                                        column: o.column + i
                                    };
                                o.row === t.start.row && t.start.column < o.column && (u.column += n), this.doc.remove(new r(u.row, u.column, u.row, u.column - n))
                            }
                        t.start.column === this.pos.column && e.action === "insert" ? setTimeout(function() {
                        this.pos.setPosition(this.pos.row, this.pos.column - n);
                        for (var e = 0; e < this.others.length; e++) {
                            var r = this.others[e],
                                i = {
                                    row: r.row,
                                    column: r.column - n
                                };
                            r.row === t.start.row && t.start.column < r.column && (i.column += n), r.setPosition(i.row, i.column)
                        }
                    }.bind(this), 0) : t.start.column === this.pos.column && e.action === "remove" && setTimeout(function() {
                        for (var e = 0; e < this.others.length; e++) {
                            var r = this.others[e];
                            r.row === t.start.row && t.start.column < r.column && r.setPosition(r.row, r.column - n)
                        }
                    }.bind(this), 0)
                }
                this.pos._emit("change", {
                    value: this.pos
                });
                for (var s = 0; s < this.others.length; s++) this.others[s]._emit("change", {
                    value: this.others[s]
                })
            }
            this.$updating = !1
        }, this.onCursorChange = function(e) {
            if (this.$updating || !this.session) return;
            var t = this.session.selection.getCursor();
            t.row === this.pos.row && t.column >= this.pos.column && t.column <= this.pos.column + this.length ? (this.showOtherMarkers(), this._emit("cursorEnter", e)) : (this.hideOtherMarkers(), this._emit("cursorLeave", e))
        }, this.detach = function() {
            this.session.removeMarker(this.markerId), this.hideOtherMarkers(), this.doc.removeEventListener("change", this.$onUpdate), this.session.selection.removeEventListener("changeCursor", this.$onCursorChange), this.pos.detach();
            for (var e = 0; e < this.others.length; e++) this.others[e].detach();
            this.session.setUndoSelect(!0), this.session = null
        }, this.cancel = function() {
            if (this.$undoStackDepth === -1) throw Error("Canceling placeholders only supported with undo manager attached to session.");
            var e = this.session.getUndoManager(),
                t = (e.$undoStack || e.$undostack).length - this.$undoStackDepth;
            for (var n = 0; n < t; n++) e.undo(!0);
            this.selectionBefore && this.session.selection.fromJSON(this.selectionBefore)
        }
    }).call(o.prototype), t.PlaceHolder = o
}), define("ace/mouse/multi_select_handler", ["require", "exports", "module", "ace/lib/event", "ace/lib/useragent"], function(e, t, n) {
    function s(e, t) {
        return e.row == t.row && e.column == t.column
    }

    function o(e) {
        var t = e.domEvent,
            n = t.altKey,
            o = t.shiftKey,
            u = t.ctrlKey,
            a = e.getAccelKey(),
            f = e.getButton();
        u && i.isMac && (f = t.button);
        if (e.editor.inMultiSelectMode && f == 2) {
            e.editor.textInput.onContextMenu(e.domEvent);
            return
        }
        if (!u && !n && !a) {
            f === 0 && e.editor.inMultiSelectMode && e.editor.exitMultiSelectMode();
            return
        }
        if (f !== 0) return;
        var l = e.editor,
            c = l.selection,
            h = l.inMultiSelectMode,
            p = e.getDocumentPosition(),
            d = c.getCursor(),
            v = e.inSelection() || c.isEmpty() && s(p, d),
            m = e.x,
            g = e.y,
            y = function(e) {
                m = e.clientX, g = e.clientY
            },
            b = l.session,
            w = l.renderer.pixelToScreenCoordinates(m, g),
            E = w,
            S;
        if (l.$mouseHandler.$enableJumpToDef) u && n || a && n ? S = o ? "block" : "add" : n && l.$blockSelectEnabled && (S = "block");
        else if (a && !n) {
            S = "add";
            if (!h && o) return
        } else n && l.$blockSelectEnabled && (S = "block");
        S && i.isMac && t.ctrlKey && l.$mouseHandler.cancelContextMenu();
        if (S == "add") {
            if (!h && v) return;
            if (!h) {
                var x = c.toOrientedRange();
                l.addSelectionMarker(x)
            }
            var T = c.rangeList.rangeAtPoint(p);
            l.$blockScrolling++, l.inVirtualSelectionMode = !0, o && (T = null, x = c.ranges[0] || x, l.removeSelectionMarker(x)), l.once("mouseup", function() {
                var e = c.toOrientedRange();
                T && e.isEmpty() && s(T.cursor, e.cursor) ? c.substractPoint(e.cursor) : (o ? c.substractPoint(x.cursor) : x && (l.removeSelectionMarker(x), c.addRange(x)), c.addRange(e)), l.$blockScrolling--, l.inVirtualSelectionMode = !1
            })
        } else if (S == "block") {
            e.stop(), l.inVirtualSelectionMode = !0;
            var N, C = [],
                k = function() {
                    var e = l.renderer.pixelToScreenCoordinates(m, g),
                        t = b.screenToDocumentPosition(e.row, e.column);
                    if (s(E, e) && s(t, c.lead)) return;
                    E = e, l.$blockScrolling++, l.selection.moveToPosition(t), l.renderer.scrollCursorIntoView(), l.removeSelectionMarkers(C), C = c.rectangularRangeBlock(E, w), l.$mouseHandler.$clickSelection && C.length == 1 && C[0].isEmpty() && (C[0] = l.$mouseHandler.$clickSelection.clone()), C.forEach(l.addSelectionMarker, l), l.updateSelectionMarkers(), l.$blockScrolling--
                };
            l.$blockScrolling++, h && !a ? c.toSingleRange() : !h && a && (N = c.toOrientedRange(), l.addSelectionMarker(N)), o ? w = b.documentToScreenPosition(c.lead) : c.moveToPosition(p), l.$blockScrolling--, E = {
                row: -1,
                column: -1
            };
            var L = function(e) {
                    clearInterval(O), l.removeSelectionMarkers(C), C.length || (C = [c.toOrientedRange()]), l.$blockScrolling++, N && (l.removeSelectionMarker(N), c.toSingleRange(N));
                    for (var t = 0; t < C.length; t++) c.addRange(C[t]);
                    l.inVirtualSelectionMode = !1, l.$mouseHandler.$clickSelection = null, l.$blockScrolling--
                },
                A = k;
            r.capture(l.container, y, L);
            var O = setInterval(function() {
                A()
            }, 20);
            return e.preventDefault()
        }
    }
    var r = e("../lib/event"),
        i = e("../lib/useragent");
    t.onMouseDown = o
}), define("ace/commands/multi_select_commands", ["require", "exports", "module", "ace/keyboard/hash_handler"], function(e, t, n) {
    t.defaultCommands = [{
        name: "addCursorAbove",
        exec: function(e) {
            e.selectMoreLines(-1)
        },
        bindKey: {
            win: "Ctrl-Alt-Up",
            mac: "Ctrl-Alt-Up"
        },
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "addCursorBelow",
        exec: function(e) {
            e.selectMoreLines(1)
        },
        bindKey: {
            win: "Ctrl-Alt-Down",
            mac: "Ctrl-Alt-Down"
        },
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "addCursorAboveSkipCurrent",
        exec: function(e) {
            e.selectMoreLines(-1, !0)
        },
        bindKey: {
            win: "Ctrl-Alt-Shift-Up",
            mac: "Ctrl-Alt-Shift-Up"
        },
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "addCursorBelowSkipCurrent",
        exec: function(e) {
            e.selectMoreLines(1, !0)
        },
        bindKey: {
            win: "Ctrl-Alt-Shift-Down",
            mac: "Ctrl-Alt-Shift-Down"
        },
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selectMoreBefore",
        exec: function(e) {
            e.selectMore(-1)
        },
        bindKey: {
            win: "Ctrl-Alt-Left",
            mac: "Ctrl-Alt-Left"
        },
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selectMoreAfter",
        exec: function(e) {
            e.selectMore(1)
        },
        bindKey: {
            win: "Ctrl-Alt-Right",
            mac: "Ctrl-Alt-Right"
        },
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selectNextBefore",
        exec: function(e) {
            e.selectMore(-1, !0)
        },
        bindKey: {
            win: "Ctrl-Alt-Shift-Left",
            mac: "Ctrl-Alt-Shift-Left"
        },
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "selectNextAfter",
        exec: function(e) {
            e.selectMore(1, !0)
        },
        bindKey: {
            win: "Ctrl-Alt-Shift-Right",
            mac: "Ctrl-Alt-Shift-Right"
        },
        scrollIntoView: "cursor",
        readOnly: !0
    }, {
        name: "splitIntoLines",
        exec: function(e) {
            e.multiSelect.splitIntoLines()
        },
        bindKey: {
            win: "Ctrl-Alt-L",
            mac: "Ctrl-Alt-L"
        },
        readOnly: !0
    }, {
        name: "alignCursors",
        exec: function(e) {
            e.alignCursors()
        },
        bindKey: {
            win: "Ctrl-Alt-A",
            mac: "Ctrl-Alt-A"
        },
        scrollIntoView: "cursor"
    }, {
        name: "findAll",
        exec: function(e) {
            e.findAll()
        },
        bindKey: {
            win: "Ctrl-Alt-K",
            mac: "Ctrl-Alt-G"
        },
        scrollIntoView: "cursor",
        readOnly: !0
    }], t.multiSelectCommands = [{
        name: "singleSelection",
        bindKey: "esc",
        exec: function(e) {
            e.exitMultiSelectMode()
        },
        scrollIntoView: "cursor",
        readOnly: !0,
        isAvailable: function(e) {
            return e && e.inMultiSelectMode
        }
    }];
    var r = e("../keyboard/hash_handler").HashHandler;
    t.keyboardHandler = new r(t.multiSelectCommands)
}), define("ace/multi_select", ["require", "exports", "module", "ace/range_list", "ace/range", "ace/selection", "ace/mouse/multi_select_handler", "ace/lib/event", "ace/lib/lang", "ace/commands/multi_select_commands", "ace/search", "ace/edit_session", "ace/editor", "ace/config"], function(e, t, n) {
    function h(e, t, n) {
        return c.$options.wrap = !0, c.$options.needle = t, c.$options.backwards = n == -1, c.find(e)
    }

    function v(e, t) {
        return e.row == t.row && e.column == t.column
    }

    function m(e) {
        if (e.$multiselectOnSessionChange) return;
        e.$onAddRange = e.$onAddRange.bind(e), e.$onRemoveRange = e.$onRemoveRange.bind(e), e.$onMultiSelect = e.$onMultiSelect.bind(e), e.$onSingleSelect = e.$onSingleSelect.bind(e), e.$multiselectOnSessionChange = t.onSessionChange.bind(e), e.$checkMultiselectChange = e.$checkMultiselectChange.bind(e), e.$multiselectOnSessionChange(e), e.on("changeSession", e.$multiselectOnSessionChange), e.on("mousedown", o), e.commands.addCommands(f.defaultCommands), g(e)
    }

    function g(e) {
        function r(t) {
            n && (e.renderer.setMouseCursor(""), n = !1)
        }
        var t = e.textInput.getElement(),
            n = !1;
        u.addListener(t, "keydown", function(t) {
            var i = t.keyCode == 18 && !(t.ctrlKey || t.shiftKey || t.metaKey);
            e.$blockSelectEnabled && i ? n || (e.renderer.setMouseCursor("crosshair"), n = !0) : n && r()
        }), u.addListener(t, "keyup", r), u.addListener(t, "blur", r)
    }
    var r = e("./range_list").RangeList,
        i = e("./range").Range,
        s = e("./selection").Selection,
        o = e("./mouse/multi_select_handler").onMouseDown,
        u = e("./lib/event"),
        a = e("./lib/lang"),
        f = e("./commands/multi_select_commands");
    t.commands = f.defaultCommands.concat(f.multiSelectCommands);
    var l = e("./search").Search,
        c = new l,
        p = e("./edit_session").EditSession;
    (function() {
        this.getSelectionMarkers = function() {
            return this.$selectionMarkers
        }
    }).call(p.prototype),
        function() {
            this.ranges = null, this.rangeList = null, this.addRange = function(e, t) {
                if (!e) return;
                if (!this.inMultiSelectMode && this.rangeCount === 0) {
                    var n = this.toOrientedRange();
                    this.rangeList.add(n), this.rangeList.add(e);
                    if (this.rangeList.ranges.length != 2) return this.rangeList.removeAll(), t || this.fromOrientedRange(e);
                    this.rangeList.removeAll(), this.rangeList.add(n), this.$onAddRange(n)
                }
                e.cursor || (e.cursor = e.end);
                var r = this.rangeList.add(e);
                return this.$onAddRange(e), r.length && this.$onRemoveRange(r), this.rangeCount > 1 && !this.inMultiSelectMode && (this._signal("multiSelect"), this.inMultiSelectMode = !0, this.session.$undoSelect = !1, this.rangeList.attach(this.session)), t || this.fromOrientedRange(e)
            }, this.toSingleRange = function(e) {
                e = e || this.ranges[0];
                var t = this.rangeList.removeAll();
                t.length && this.$onRemoveRange(t), e && this.fromOrientedRange(e)
            }, this.substractPoint = function(e) {
                var t = this.rangeList.substractPoint(e);
                if (t) return this.$onRemoveRange(t), t[0]
            }, this.mergeOverlappingRanges = function() {
                var e = this.rangeList.merge();
                e.length ? this.$onRemoveRange(e) : this.ranges[0] && this.fromOrientedRange(this.ranges[0])
            }, this.$onAddRange = function(e) {
                this.rangeCount = this.rangeList.ranges.length, this.ranges.unshift(e), this._signal("addRange", {
                    range: e
                })
            }, this.$onRemoveRange = function(e) {
                this.rangeCount = this.rangeList.ranges.length;
                if (this.rangeCount == 1 && this.inMultiSelectMode) {
                    var t = this.rangeList.ranges.pop();
                    e.push(t), this.rangeCount = 0
                }
                for (var n = e.length; n--;) {
                    var r = this.ranges.indexOf(e[n]);
                    this.ranges.splice(r, 1)
                }
                this._signal("removeRange", {
                    ranges: e
                }), this.rangeCount === 0 && this.inMultiSelectMode && (this.inMultiSelectMode = !1, this._signal("singleSelect"), this.session.$undoSelect = !0, this.rangeList.detach(this.session)), t = t || this.ranges[0], t && !t.isEqual(this.getRange()) && this.fromOrientedRange(t)
            }, this.$initRangeList = function() {
                if (this.rangeList) return;
                this.rangeList = new r, this.ranges = [], this.rangeCount = 0
            }, this.getAllRanges = function() {
                return this.rangeCount ? this.rangeList.ranges.concat() : [this.getRange()]
            }, this.splitIntoLines = function() {
                if (this.rangeCount > 1) {
                    var e = this.rangeList.ranges,
                        t = e[e.length - 1],
                        n = i.fromPoints(e[0].start, t.end);
                    this.toSingleRange(), this.setSelectionRange(n, t.cursor == t.start)
                } else {
                    var n = this.getRange(),
                        r = this.isBackwards(),
                        s = n.start.row,
                        o = n.end.row;
                    if (s == o) {
                        if (r) var u = n.end,
                            a = n.start;
                        else var u = n.start,
                            a = n.end;
                        this.addRange(i.fromPoints(a, a)), this.addRange(i.fromPoints(u, u));
                        return
                    }
                    var f = [],
                        l = this.getLineRange(s, !0);
                    l.start.column = n.start.column, f.push(l);
                    for (var c = s + 1; c < o; c++) f.push(this.getLineRange(c, !0));
                    l = this.getLineRange(o, !0), l.end.column = n.end.column, f.push(l), f.forEach(this.addRange, this)
                }
            }, this.toggleBlockSelection = function() {
                if (this.rangeCount > 1) {
                    var e = this.rangeList.ranges,
                        t = e[e.length - 1],
                        n = i.fromPoints(e[0].start, t.end);
                    this.toSingleRange(), this.setSelectionRange(n, t.cursor == t.start)
                } else {
                    var r = this.session.documentToScreenPosition(this.selectionLead),
                        s = this.session.documentToScreenPosition(this.selectionAnchor),
                        o = this.rectangularRangeBlock(r, s);
                    o.forEach(this.addRange, this)
                }
            }, this.rectangularRangeBlock = function(e, t, n) {
                var r = [],
                    s = e.column < t.column;
                if (s) var o = e.column,
                    u = t.column;
                else var o = t.column,
                    u = e.column;
                var a = e.row < t.row;
                if (a) var f = e.row,
                    l = t.row;
                else var f = t.row,
                    l = e.row;
                o < 0 && (o = 0), f < 0 && (f = 0), f == l && (n = !0);
                for (var c = f; c <= l; c++) {
                    var h = i.fromPoints(this.session.screenToDocumentPosition(c, o), this.session.screenToDocumentPosition(c, u));
                    if (h.isEmpty()) {
                        if (p && v(h.end, p)) break;
                        var p = h.end
                    }
                    h.cursor = s ? h.start : h.end, r.push(h)
                }
                a && r.reverse();
                if (!n) {
                    var d = r.length - 1;
                    while (r[d].isEmpty() && d > 0) d--;
                    if (d > 0) {
                        var m = 0;
                        while (r[m].isEmpty()) m++
                    }
                    for (var g = d; g >= m; g--) r[g].isEmpty() && r.splice(g, 1)
                }
                return r
            }
        }.call(s.prototype);
    var d = e("./editor").Editor;
    (function() {
        this.updateSelectionMarkers = function() {
            this.renderer.updateCursor(), this.renderer.updateBackMarkers()
        }, this.addSelectionMarker = function(e) {
            e.cursor || (e.cursor = e.end);
            var t = this.getSelectionStyle();
            return e.marker = this.session.addMarker(e, "ace_selection", t), this.session.$selectionMarkers.push(e), this.session.selectionMarkerCount = this.session.$selectionMarkers.length, e
        }, this.removeSelectionMarker = function(e) {
            if (!e.marker) return;
            this.session.removeMarker(e.marker);
            var t = this.session.$selectionMarkers.indexOf(e);
            t != -1 && this.session.$selectionMarkers.splice(t, 1), this.session.selectionMarkerCount = this.session.$selectionMarkers.length
        }, this.removeSelectionMarkers = function(e) {
            var t = this.session.$selectionMarkers;
            for (var n = e.length; n--;) {
                var r = e[n];
                if (!r.marker) continue;
                this.session.removeMarker(r.marker);
                var i = t.indexOf(r);
                i != -1 && t.splice(i, 1)
            }
            this.session.selectionMarkerCount = t.length
        }, this.$onAddRange = function(e) {
            this.addSelectionMarker(e.range), this.renderer.updateCursor(), this.renderer.updateBackMarkers()
        }, this.$onRemoveRange = function(e) {
            this.removeSelectionMarkers(e.ranges), this.renderer.updateCursor(), this.renderer.updateBackMarkers()
        }, this.$onMultiSelect = function(e) {
            if (this.inMultiSelectMode) return;
            this.inMultiSelectMode = !0, this.setStyle("ace_multiselect"), this.keyBinding.addKeyboardHandler(f.keyboardHandler), this.commands.setDefaultHandler("exec", this.$onMultiSelectExec), this.renderer.updateCursor(), this.renderer.updateBackMarkers()
        }, this.$onSingleSelect = function(e) {
            if (this.session.multiSelect.inVirtualMode) return;
            this.inMultiSelectMode = !1, this.unsetStyle("ace_multiselect"), this.keyBinding.removeKeyboardHandler(f.keyboardHandler), this.commands.removeDefaultHandler("exec", this.$onMultiSelectExec), this.renderer.updateCursor(), this.renderer.updateBackMarkers(), this._emit("changeSelection")
        }, this.$onMultiSelectExec = function(e) {
            var t = e.command,
                n = e.editor;
            if (!n.multiSelect) return;
            if (!t.multiSelectAction) {
                var r = t.exec(n, e.args || {});
                n.multiSelect.addRange(n.multiSelect.toOrientedRange()), n.multiSelect.mergeOverlappingRanges()
            } else t.multiSelectAction == "forEach" ? r = n.forEachSelection(t, e.args) : t.multiSelectAction == "forEachLine" ? r = n.forEachSelection(t, e.args, !0) : t.multiSelectAction == "single" ? (n.exitMultiSelectMode(), r = t.exec(n, e.args || {})) : r = t.multiSelectAction(n, e.args || {});
            return r
        }, this.forEachSelection = function(e, t, n) {
            if (this.inVirtualSelectionMode) return;
            var r = n && n.keepOrder,
                i = n == 1 || n && n.$byLines,
                o = this.session,
                u = this.selection,
                a = u.rangeList,
                f = (r ? u : a).ranges,
                l;
            if (!f.length) return e.exec ? e.exec(this, t || {}) : e(this, t || {});
            var c = u._eventRegistry;
            u._eventRegistry = {};
            var h = new s(o);
            this.inVirtualSelectionMode = !0;
            for (var p = f.length; p--;) {
                if (i)
                    while (p > 0 && f[p].start.row == f[p - 1].end.row) p--;
                h.fromOrientedRange(f[p]), h.index = p, this.selection = o.selection = h;
                var d = e.exec ? e.exec(this, t || {}) : e(this, t || {});
                !l && d !== undefined && (l = d), h.toOrientedRange(f[p])
            }
            h.detach(), this.selection = o.selection = u, this.inVirtualSelectionMode = !1, u._eventRegistry = c, u.mergeOverlappingRanges();
            var v = this.renderer.$scrollAnimation;
            return this.onCursorChange(), this.onSelectionChange(), v && v.from == v.to && this.renderer.animateScrolling(v.from), l
        }, this.exitMultiSelectMode = function() {
            if (!this.inMultiSelectMode || this.inVirtualSelectionMode) return;
            this.multiSelect.toSingleRange()
        }, this.getSelectedText = function() {
            var e = "";
            if (this.inMultiSelectMode && !this.inVirtualSelectionMode) {
                var t = this.multiSelect.rangeList.ranges,
                    n = [];
                for (var r = 0; r < t.length; r++) n.push(this.session.getTextRange(t[r]));
                var i = this.session.getDocument().getNewLineCharacter();
                e = n.join(i), e.length == (n.length - 1) * i.length && (e = "")
            } else this.selection.isEmpty() || (e = this.session.getTextRange(this.getSelectionRange()));
            return e
        }, this.$checkMultiselectChange = function(e, t) {
            if (this.inMultiSelectMode && !this.inVirtualSelectionMode) {
                var n = this.multiSelect.ranges[0];
                if (this.multiSelect.isEmpty() && t == this.multiSelect.anchor) return;
                var r = t == this.multiSelect.anchor ? n.cursor == n.start ? n.end : n.start : n.cursor;
                (r.row != t.row || this.session.$clipPositionToDocument(r.row, r.column).column != t.column) && this.multiSelect.toSingleRange(this.multiSelect.toOrientedRange())
            }
        }, this.findAll = function(e, t, n) {
            t = t || {}, t.needle = e || t.needle;
            if (t.needle == undefined) {
                var r = this.selection.isEmpty() ? this.selection.getWordRange() : this.selection.getRange();
                t.needle = this.session.getTextRange(r)
            }
            this.$search.set(t);
            var i = this.$search.findAll(this.session);
            if (!i.length) return 0;
            this.$blockScrolling += 1;
            var s = this.multiSelect;
            n || s.toSingleRange(i[0]);
            for (var o = i.length; o--;) s.addRange(i[o], !0);
            return r && s.rangeList.rangeAtPoint(r.start) && s.addRange(r, !0), this.$blockScrolling -= 1, i.length
        }, this.selectMoreLines = function(e, t) {
            var n = this.selection.toOrientedRange(),
                r = n.cursor == n.end,
                s = this.session.documentToScreenPosition(n.cursor);
            this.selection.$desiredColumn && (s.column = this.selection.$desiredColumn);
            var o = this.session.screenToDocumentPosition(s.row + e, s.column);
            if (!n.isEmpty()) var u = this.session.documentToScreenPosition(r ? n.end : n.start),
                a = this.session.screenToDocumentPosition(u.row + e, u.column);
            else var a = o;
            if (r) {
                var f = i.fromPoints(o, a);
                f.cursor = f.start
            } else {
                var f = i.fromPoints(a, o);
                f.cursor = f.end
            }
            f.desiredColumn = s.column;
            if (!this.selection.inMultiSelectMode) this.selection.addRange(n);
            else if (t) var l = n.cursor;
            this.selection.addRange(f), l && this.selection.substractPoint(l)
        }, this.transposeSelections = function(e) {
            var t = this.session,
                n = t.multiSelect,
                r = n.ranges;
            for (var i = r.length; i--;) {
                var s = r[i];
                if (s.isEmpty()) {
                    var o = t.getWordRange(s.start.row, s.start.column);
                    s.start.row = o.start.row, s.start.column = o.start.column, s.end.row = o.end.row, s.end.column = o.end.column
                }
            }
            n.mergeOverlappingRanges();
            var u = [];
            for (var i = r.length; i--;) {
                var s = r[i];
                u.unshift(t.getTextRange(s))
            }
            e < 0 ? u.unshift(u.pop()) : u.push(u.shift());
            for (var i = r.length; i--;) {
                var s = r[i],
                    o = s.clone();
                t.replace(s, u[i]), s.start.row = o.start.row, s.start.column = o.start.column
            }
        }, this.selectMore = function(e, t, n) {
            var r = this.session,
                i = r.multiSelect,
                s = i.toOrientedRange();
            if (s.isEmpty()) {
                s = r.getWordRange(s.start.row, s.start.column), s.cursor = e == -1 ? s.start : s.end, this.multiSelect.addRange(s);
                if (n) return
            }
            var o = r.getTextRange(s),
                u = h(r, o, e);
            u && (u.cursor = e == -1 ? u.start : u.end, this.$blockScrolling += 1, this.session.unfold(u), this.multiSelect.addRange(u), this.$blockScrolling -= 1, this.renderer.scrollCursorIntoView(null, .5)), t && this.multiSelect.substractPoint(s.cursor)
        }, this.alignCursors = function() {
            var e = this.session,
                t = e.multiSelect,
                n = t.ranges,
                r = -1,
                s = n.filter(function(e) {
                    if (e.cursor.row == r) return !0;
                    r = e.cursor.row
                });
            if (!n.length || s.length == n.length - 1) {
                var o = this.selection.getRange(),
                    u = o.start.row,
                    f = o.end.row,
                    l = u == f;
                if (l) {
                    var c = this.session.getLength(),
                        h;
                    do h = this.session.getLine(f); while (/[=:]/.test(h) && ++f < c);
                    do h = this.session.getLine(u); while (/[=:]/.test(h) && --u > 0);
                    u < 0 && (u = 0), f >= c && (f = c - 1)
                }
                var p = this.session.removeFullLines(u, f);
                p = this.$reAlignText(p, l), this.session.insert({
                    row: u,
                    column: 0
                }, p.join("\n") + "\n"), l || (o.start.column = 0, o.end.column = p[p.length - 1].length), this.selection.setRange(o)
            } else {
                s.forEach(function(e) {
                    t.substractPoint(e.cursor)
                });
                var d = 0,
                    v = Infinity,
                    m = n.map(function(t) {
                        var n = t.cursor,
                            r = e.getLine(n.row),
                            i = r.substr(n.column).search(/\S/g);
                        return i == -1 && (i = 0), n.column > d && (d = n.column), i < v && (v = i), i
                    });
                n.forEach(function(t, n) {
                    var r = t.cursor,
                        s = d - r.column,
                        o = m[n] - v;
                    s > o ? e.insert(r, a.stringRepeat(" ", s - o)) : e.remove(new i(r.row, r.column, r.row, r.column - s + o)), t.start.column = t.end.column = d, t.start.row = t.end.row = r.row, t.cursor = t.end
                }), t.fromOrientedRange(n[0]), this.renderer.updateCursor(), this.renderer.updateBackMarkers()
            }
        }, this.$reAlignText = function(e, t) {
            function u(e) {
                return a.stringRepeat(" ", e)
            }

            function f(e) {
                return e[2] ? u(i) + e[2] + u(s - e[2].length + o) + e[4].replace(/^([=:])\s+/, "$1 ") : e[0]
            }

            function l(e) {
                return e[2] ? u(i + s - e[2].length) + e[2] + u(o, " ") + e[4].replace(/^([=:])\s+/, "$1 ") : e[0]
            }

            function c(e) {
                return e[2] ? u(i) + e[2] + u(o) + e[4].replace(/^([=:])\s+/, "$1 ") : e[0]
            }
            var n = !0,
                r = !0,
                i, s, o;
            return e.map(function(e) {
                var t = e.match(/(\s*)(.*?)(\s*)([=:].*)/);
                return t ? i == null ? (i = t[1].length, s = t[2].length, o = t[3].length, t) : (i + s + o != t[1].length + t[2].length + t[3].length && (r = !1), i != t[1].length && (n = !1), i > t[1].length && (i = t[1].length), s < t[2].length && (s = t[2].length), o > t[3].length && (o = t[3].length), t) : [e]
            }).map(t ? f : n ? r ? l : f : c)
        }
    }).call(d.prototype), t.onSessionChange = function(e) {
        var t = e.session;
        t && !t.multiSelect && (t.$selectionMarkers = [], t.selection.$initRangeList(), t.multiSelect = t.selection), this.multiSelect = t && t.multiSelect;
        var n = e.oldSession;
        n && (n.multiSelect.off("addRange", this.$onAddRange), n.multiSelect.off("removeRange", this.$onRemoveRange), n.multiSelect.off("multiSelect", this.$onMultiSelect), n.multiSelect.off("singleSelect", this.$onSingleSelect), n.multiSelect.lead.off("change", this.$checkMultiselectChange), n.multiSelect.anchor.off("change", this.$checkMultiselectChange)), t && (t.multiSelect.on("addRange", this.$onAddRange), t.multiSelect.on("removeRange", this.$onRemoveRange), t.multiSelect.on("multiSelect", this.$onMultiSelect), t.multiSelect.on("singleSelect", this.$onSingleSelect), t.multiSelect.lead.on("change", this.$checkMultiselectChange), t.multiSelect.anchor.on("change", this.$checkMultiselectChange)), t && this.inMultiSelectMode != t.selection.inMultiSelectMode && (t.selection.inMultiSelectMode ? this.$onMultiSelect() : this.$onSingleSelect())
    }, t.MultiSelect = m, e("./config").defineOptions(d.prototype, "editor", {
        enableMultiselect: {
            set: function(e) {
                m(this), e ? (this.on("changeSession", this.$multiselectOnSessionChange), this.on("mousedown", o)) : (this.off("changeSession", this.$multiselectOnSessionChange), this.off("mousedown", o))
            },
            value: !0
        },
        enableBlockSelect: {
            set: function(e) {
                this.$blockSelectEnabled = e
            },
            value: !0
        }
    })
}), define("ace/mode/folding/fold_mode", ["require", "exports", "module", "ace/range"], function(e, t, n) {
    "use strict";
    var r = e("../../range").Range,
        i = t.FoldMode = function() {};
    (function() {
        this.foldingStartMarker = null, this.foldingStopMarker = null, this.getFoldWidget = function(e, t, n) {
            var r = e.getLine(n);
            return this.foldingStartMarker.test(r) ? "start" : t == "markbeginend" && this.foldingStopMarker && this.foldingStopMarker.test(r) ? "end" : ""
        }, this.getFoldWidgetRange = function(e, t, n) {
            return null
        }, this.indentationBlock = function(e, t, n) {
            var i = /\S/,
                s = e.getLine(t),
                o = s.search(i);
            if (o == -1) return;
            var u = n || s.length,
                a = e.getLength(),
                f = t,
                l = t;
            while (++t < a) {
                var c = e.getLine(t).search(i);
                if (c == -1) continue;
                if (c <= o) break;
                l = t
            }
            if (l > f) {
                var h = e.getLine(l).length;
                return new r(f, u, l, h)
            }
        }, this.openingBracketBlock = function(e, t, n, i, s) {
            var o = {
                    row: n,
                    column: i + 1
                },
                u = e.$findClosingBracket(t, o, s);
            if (!u) return;
            var a = e.foldWidgets[u.row];
            return a == null && (a = e.getFoldWidget(u.row)), a == "start" && u.row > o.row && (u.row--, u.column = e.getLine(u.row).length), r.fromPoints(o, u)
        }, this.closingBracketBlock = function(e, t, n, i, s) {
            var o = {
                    row: n,
                    column: i
                },
                u = e.$findOpeningBracket(t, o);
            if (!u) return;
            return u.column++, o.column--, r.fromPoints(u, o)
        }
    }).call(i.prototype)
}), define("ace/theme/textmate", ["require", "exports", "module", "ace/lib/dom"], function(e, t, n) {
    "use strict";
    t.isDark = !1, t.cssClass = "ace-tm", t.cssText = '.ace-tm .ace_gutter {background: #f0f0f0;color: #333;}.ace-tm .ace_print-margin {width: 1px;background: #e8e8e8;}.ace-tm .ace_fold {background-color: #6B72E6;}.ace-tm {background-color: #FFFFFF;color: black;}.ace-tm .ace_cursor {color: black;}.ace-tm .ace_invisible {color: rgb(191, 191, 191);}.ace-tm .ace_storage,.ace-tm .ace_keyword {color: blue;}.ace-tm .ace_constant {color: rgb(197, 6, 11);}.ace-tm .ace_constant.ace_buildin {color: rgb(88, 72, 246);}.ace-tm .ace_constant.ace_language {color: rgb(88, 92, 246);}.ace-tm .ace_constant.ace_library {color: rgb(6, 150, 14);}.ace-tm .ace_invalid {background-color: rgba(255, 0, 0, 0.1);color: red;}.ace-tm .ace_support.ace_function {color: rgb(60, 76, 114);}.ace-tm .ace_support.ace_constant {color: rgb(6, 150, 14);}.ace-tm .ace_support.ace_type,.ace-tm .ace_support.ace_class {color: rgb(109, 121, 222);}.ace-tm .ace_keyword.ace_operator {color: rgb(104, 118, 135);}.ace-tm .ace_string {color: rgb(3, 106, 7);}.ace-tm .ace_comment {color: rgb(76, 136, 107);}.ace-tm .ace_comment.ace_doc {color: rgb(0, 102, 255);}.ace-tm .ace_comment.ace_doc.ace_tag {color: rgb(128, 159, 191);}.ace-tm .ace_constant.ace_numeric {color: rgb(0, 0, 205);}.ace-tm .ace_variable {color: rgb(49, 132, 149);}.ace-tm .ace_xml-pe {color: rgb(104, 104, 91);}.ace-tm .ace_entity.ace_name.ace_function {color: #0000A2;}.ace-tm .ace_heading {color: rgb(12, 7, 255);}.ace-tm .ace_list {color:rgb(185, 6, 144);}.ace-tm .ace_meta.ace_tag {color:rgb(0, 22, 142);}.ace-tm .ace_string.ace_regex {color: rgb(255, 0, 0)}.ace-tm .ace_marker-layer .ace_selection {background: rgb(181, 213, 255);}.ace-tm.ace_multiselect .ace_selection.ace_start {box-shadow: 0 0 3px 0px white;}.ace-tm .ace_marker-layer .ace_step {background: rgb(252, 255, 0);}.ace-tm .ace_marker-layer .ace_stack {background: rgb(164, 229, 101);}.ace-tm .ace_marker-layer .ace_bracket {margin: -1px 0 0 -1px;border: 1px solid rgb(192, 192, 192);}.ace-tm .ace_marker-layer .ace_active-line {background: rgba(0, 0, 0, 0.07);}.ace-tm .ace_gutter-active-line {background-color : #dcdcdc;}.ace-tm .ace_marker-layer .ace_selected-word {background: rgb(250, 250, 255);border: 1px solid rgb(200, 200, 250);}.ace-tm .ace_indent-guide {background: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAACCAYAAACZgbYnAAAAE0lEQVQImWP4////f4bLly//BwAmVgd1/w11/gAAAABJRU5ErkJggg==") right repeat-y;}';
    var r = e("../lib/dom");
    r.importCssString(t.cssText, t.cssClass)
}), define("ace/line_widgets", ["require", "exports", "module", "ace/lib/oop", "ace/lib/dom", "ace/range"], function(e, t, n) {
    "use strict";

    function o(e) {
        this.session = e, this.session.widgetManager = this, this.session.getRowLength = this.getRowLength, this.session.$getWidgetScreenLength = this.$getWidgetScreenLength, this.updateOnChange = this.updateOnChange.bind(this), this.renderWidgets = this.renderWidgets.bind(this), this.measureWidgets = this.measureWidgets.bind(this), this.session._changedWidgets = [], this.$onChangeEditor = this.$onChangeEditor.bind(this), this.session.on("change", this.updateOnChange), this.session.on("changeEditor", this.$onChangeEditor)
    }
    var r = e("./lib/oop"),
        i = e("./lib/dom"),
        s = e("./range").Range;
    (function() {
        this.getRowLength = function(e) {
            var t;
            return this.lineWidgets ? t = this.lineWidgets[e] && this.lineWidgets[e].rowCount || 0 : t = 0, !this.$useWrapMode || !this.$wrapData[e] ? 1 + t : this.$wrapData[e].length + 1 + t
        }, this.$getWidgetScreenLength = function() {
            var e = 0;
            return this.lineWidgets.forEach(function(t) {
                t && t.rowCount && (e += t.rowCount)
            }), e
        }, this.$onChangeEditor = function(e) {
            this.attach(e.editor)
        }, this.attach = function(e) {
            e && e.widgetManager && e.widgetManager != this && e.widgetManager.detach();
            if (this.editor == e) return;
            this.detach(), this.editor = e, e && (e.widgetManager = this, e.renderer.on("beforeRender", this.measureWidgets), e.renderer.on("afterRender", this.renderWidgets))
        }, this.detach = function(e) {
            var t = this.editor;
            if (!t) return;
            this.editor = null, t.widgetManager = null, t.renderer.off("beforeRender", this.measureWidgets), t.renderer.off("afterRender", this.renderWidgets);
            var n = this.session.lineWidgets;
            n && n.forEach(function(e) {
                e && e.el && e.el.parentNode && (e._inDocument = !1, e.el.parentNode.removeChild(e.el))
            })
        }, this.updateOnChange = function(e) {
            var t = this.session.lineWidgets;
            if (!t) return;
            var n = e.start.row,
                r = e.end.row - n;
            if (r !== 0)
                if (e.action == "remove") {
                    var i = t.splice(n + 1, r);
                    i.forEach(function(e) {
                        e && this.removeLineWidget(e)
                    }, this), this.$updateRows()
                } else {
                    var s = new Array(r);
                    s.unshift(n, 0), t.splice.apply(t, s), this.$updateRows()
                }
        }, this.$updateRows = function() {
            var e = this.session.lineWidgets;
            if (!e) return;
            var t = !0;
            e.forEach(function(e, n) {
                e && (t = !1, e.row = n)
            }), t && (this.session.lineWidgets = null)
        }, this.addLineWidget = function(e) {
            this.session.lineWidgets || (this.session.lineWidgets = new Array(this.session.getLength())), this.session.lineWidgets[e.row] = e;
            var t = this.editor.renderer;
            return e.html && !e.el && (e.el = i.createElement("div"), e.el.innerHTML = e.html), e.el && (i.addCssClass(e.el, "ace_lineWidgetContainer"), e.el.style.position = "absolute", e.el.style.zIndex = 5, t.container.appendChild(e.el), e._inDocument = !0), e.coverGutter || (e.el.style.zIndex = 3), e.pixelHeight || (e.pixelHeight = e.el.offsetHeight), e.rowCount == null && (e.rowCount = e.pixelHeight / t.layerConfig.lineHeight), this.session._emit("changeFold", {
                data: {
                    start: {
                        row: e.row
                    }
                }
            }), this.$updateRows(), this.renderWidgets(null, t), e
        }, this.removeLineWidget = function(e) {
            e._inDocument = !1, e.el && e.el.parentNode && e.el.parentNode.removeChild(e.el);
            if (e.editor && e.editor.destroy) try {
                e.editor.destroy()
            } catch (t) {}
            this.session.lineWidgets && (this.session.lineWidgets[e.row] = undefined), this.session._emit("changeFold", {
                data: {
                    start: {
                        row: e.row
                    }
                }
            }), this.$updateRows()
        }, this.onWidgetChanged = function(e) {
            this.session._changedWidgets.push(e), this.editor && this.editor.renderer.updateFull()
        }, this.measureWidgets = function(e, t) {
            var n = this.session._changedWidgets,
                r = t.layerConfig;
            if (!n || !n.length) return;
            var i = Infinity;
            for (var s = 0; s < n.length; s++) {
                var o = n[s];
                o._inDocument || (o._inDocument = !0, t.container.appendChild(o.el)), o.h = o.el.offsetHeight, o.fixedWidth || (o.w = o.el.offsetWidth, o.screenWidth = Math.ceil(o.w / r.characterWidth));
                var u = o.h / r.lineHeight;
                o.coverLine && (u -= this.session.getRowLineCount(o.row), u < 0 && (u = 0)), o.rowCount != u && (o.rowCount = u, o.row < i && (i = o.row))
            }
            i != Infinity && (this.session._emit("changeFold", {
                data: {
                    start: {
                        row: i
                    }
                }
            }), this.session.lineWidgetWidth = null), this.session._changedWidgets = []
        }, this.renderWidgets = function(e, t) {
            var n = t.layerConfig,
                r = this.session.lineWidgets;
            if (!r) return;
            var i = Math.min(this.firstRow, n.firstRow),
                s = Math.max(this.lastRow, n.lastRow, r.length);
            while (i > 0 && !r[i]) i--;
            this.firstRow = n.firstRow, this.lastRow = n.lastRow, t.$cursorLayer.config = n;
            for (var o = i; o <= s; o++) {
                var u = r[o];
                if (!u || !u.el) continue;
                u._inDocument || (u._inDocument = !0, t.container.appendChild(u.el));
                var a = t.$cursorLayer.getPixelPosition({
                    row: o,
                    column: 0
                }, !0).top;
                u.coverLine || (a += n.lineHeight * this.session.getRowLineCount(u.row)), u.el.style.top = a - n.offset + "px";
                var f = u.coverGutter ? 0 : t.gutterWidth;
                u.fixedWidth || (f -= t.scrollLeft), u.el.style.left = f + "px", u.fixedWidth ? u.el.style.right = t.scrollBar.getWidth() + "px" : u.el.style.right = ""
            }
        }
    }).call(o.prototype), t.LineWidgets = o
}), define("ace/ext/error_marker", ["require", "exports", "module", "ace/line_widgets", "ace/lib/dom", "ace/range"], function(e, t, n) {
    "use strict";

    function o(e, t, n) {
        var r = 0,
            i = e.length - 1;
        while (r <= i) {
            var s = r + i >> 1,
                o = n(t, e[s]);
            if (o > 0) r = s + 1;
            else {
                if (!(o < 0)) return s;
                i = s - 1
            }
        }
        return -(r + 1)
    }

    function u(e, t, n) {
        var r = e.getAnnotations().sort(s.comparePoints);
        if (!r.length) return;
        var i = o(r, {
            row: t,
            column: -1
        }, s.comparePoints);
        i < 0 && (i = -i - 1), i >= r.length ? i = n > 0 ? 0 : r.length - 1 : i === 0 && n < 0 && (i = r.length - 1);
        var u = r[i];
        if (!u || !n) return;
        if (u.row === t) {
            do u = r[i += n]; while (u && u.row === t);
            if (!u) return r.slice()
        }
        var a = [];
        t = u.row;
        do a[n < 0 ? "unshift" : "push"](u), u = r[i += n]; while (u && u.row == t);
        return a.length && a
    }
    var r = e("../line_widgets").LineWidgets,
        i = e("../lib/dom"),
        s = e("../range").Range;
    t.showErrorMarker = function(e, t) {
        var n = e.session;
        n.widgetManager || (n.widgetManager = new r(n), n.widgetManager.attach(e));
        var s = e.getCursorPosition(),
            o = s.row,
            a = n.lineWidgets && n.lineWidgets[o];
        a ? a.destroy() : o -= t;
        var f = u(n, o, t),
            l;
        if (f) {
            var c = f[0];
            s.column = (c.pos && typeof c.column != "number" ? c.pos.sc : c.column) || 0, s.row = c.row, l = e.renderer.$gutterLayer.$annotations[s.row]
        } else {
            if (a) return;
            l = {
                text: ["Looks good!"],
                className: "ace_ok"
            }
        }
        e.session.unfold(s.row), e.selection.moveToPosition(s);
        var h = {
                row: s.row,
                fixedWidth: !0,
                coverGutter: !0,
                el: i.createElement("div")
            },
            p = h.el.appendChild(i.createElement("div")),
            d = h.el.appendChild(i.createElement("div"));
        d.className = "error_widget_arrow " + l.className;
        var v = e.renderer.$cursorLayer.getPixelPosition(s).left;
        d.style.left = v + e.renderer.gutterWidth - 5 + "px", h.el.className = "error_widget_wrapper", p.className = "error_widget " + l.className, p.innerHTML = l.text.join("<br>"), p.appendChild(i.createElement("div"));
        var m = function(e, t, n) {
            if (t === 0 && (n === "esc" || n === "return")) return h.destroy(), {
                command: "null"
            }
        };
        h.destroy = function() {
            if (e.$mouseHandler.isMousePressed) return;
            e.keyBinding.removeKeyboardHandler(m), n.widgetManager.removeLineWidget(h), e.off("changeSelection", h.destroy), e.off("changeSession", h.destroy), e.off("mouseup", h.destroy), e.off("change", h.destroy)
        }, e.keyBinding.addKeyboardHandler(m), e.on("changeSelection", h.destroy), e.on("changeSession", h.destroy), e.on("mouseup", h.destroy), e.on("change", h.destroy), e.session.widgetManager.addLineWidget(h), h.el.onmousedown = e.focus.bind(e), e.renderer.scrollCursorIntoView(null, .5, {
            bottom: h.el.offsetHeight
        })
    }, i.importCssString("    .error_widget_wrapper {        background: inherit;        color: inherit;        border:none    }    .error_widget {        border-top: solid 2px;        border-bottom: solid 2px;        margin: 5px 0;        padding: 10px 40px;        white-space: pre-wrap;    }    .error_widget.ace_error, .error_widget_arrow.ace_error{        border-color: #ff5a5a    }    .error_widget.ace_warning, .error_widget_arrow.ace_warning{        border-color: #F1D817    }    .error_widget.ace_info, .error_widget_arrow.ace_info{        border-color: #5a5a5a    }    .error_widget.ace_ok, .error_widget_arrow.ace_ok{        border-color: #5aaa5a    }    .error_widget_arrow {        position: absolute;        border: solid 5px;        border-top-color: transparent!important;        border-right-color: transparent!important;        border-left-color: transparent!important;        top: -5px;    }", "")
}), define("ace/ace", ["require", "exports", "module", "ace/lib/fixoldbrowsers", "ace/lib/dom", "ace/lib/event", "ace/editor", "ace/edit_session", "ace/undomanager", "ace/virtual_renderer", "ace/worker/worker_client", "ace/keyboard/hash_handler", "ace/placeholder", "ace/multi_select", "ace/mode/folding/fold_mode", "ace/theme/textmate", "ace/ext/error_marker", "ace/config"], function(e, t, n) {
    "use strict";
    e("./lib/fixoldbrowsers");
    var r = e("./lib/dom"),
        i = e("./lib/event"),
        s = e("./editor").Editor,
        o = e("./edit_session").EditSession,
        u = e("./undomanager").UndoManager,
        a = e("./virtual_renderer").VirtualRenderer;
    e("./worker/worker_client"), e("./keyboard/hash_handler"), e("./placeholder"), e("./multi_select"), e("./mode/folding/fold_mode"), e("./theme/textmate"), e("./ext/error_marker"), t.config = e("./config"), t.require = e, t.edit = function(e) {
        if (typeof e == "string") {
            var n = e;
            e = document.getElementById(n);
            if (!e) throw new Error("ace.edit can't find div #" + n)
        }
        if (e && e.env && e.env.editor instanceof s) return e.env.editor;
        var o = "";
        if (e && /input|textarea/i.test(e.tagName)) {
            var u = e;
            o = u.value, e = r.createElement("pre"), u.parentNode.replaceChild(e, u)
        } else e && (o = r.getInnerText(e), e.innerHTML = "");
        var f = t.createEditSession(o),
            l = new s(new a(e));
        l.setSession(f);
        var c = {
            document: f,
            editor: l,
            onResize: l.resize.bind(l, null)
        };
        return u && (c.textarea = u), i.addListener(window, "resize", c.onResize), l.on("destroy", function() {
            i.removeListener(window, "resize", c.onResize), c.editor.container.env = null
        }), l.container.env = l.env = c, l
    }, t.createEditSession = function(e, t) {
        var n = new o(e, t);
        return n.setUndoManager(new u), n
    }, t.EditSession = o, t.UndoManager = u
});
(function() {
    require(["ace/ace"], function(a) {
        a && a.config.init(true);
        if (!window.ace)
            window.ace = a;
        for (var key in a)
            if (a.hasOwnProperty(key))
                window.ace[key] = a[key];
    });
})();
})();
