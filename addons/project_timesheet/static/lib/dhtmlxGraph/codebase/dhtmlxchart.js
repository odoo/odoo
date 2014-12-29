/*
Copyright DHTMLX LTD. http://www.dhtmlx.com
You allowed to use this component or parts of it under GPL terms
To use it on other terms or get Professional edition of the component please contact us at sales@dhtmlx.com
*/
window.dhtmlx || (dhtmlx = {});
dhtmlx.version = "3.0";
dhtmlx.codebase = "./";
dhtmlx.extend = function (a, b) {
    for (var c in b) a[c] = b[c];
    b.k && a.k();
    return a
};
dhtmlx.proto_extend = function () {
    for (var a = arguments, b = a[0], c = [], d = a.length - 1; d > 0; d--) {
        if (typeof a[d] == "function") a[d] = a[d].prototype;
        for (var e in a[d]) if (e == "_init") c.push(a[d][e]);
        else b[e] || (b[e] = a[d][e])
    }
    a[0].k && c.push(a[0].k);
    b.k = function () {
        for (var g = 0; g < c.length; g++) c[g].apply(this, arguments)
    };
    b.base = a[1];
    var f = function (g) {
            this.k(g);
            this.B && this.B(g, this.defaults)
        };
    f.prototype = b;
    b = a = null;
    return f
};
dhtmlx.bind = function (a, b) {
    return function () {
        return a.apply(b, arguments)
    }
};
dhtmlx.require = function (a) {
    if (!dhtmlx.ha[a]) {
        dhtmlx.exec(dhtmlx.ajax().sync().get(dhtmlx.codebase + a).responseText);
        dhtmlx.ha[a] = true
    }
};
dhtmlx.ha = {};
dhtmlx.exec = function (a) {
    window.execScript ? window.execScript(a) : window.eval(a)
};
dhtmlx.methodPush = function (a, b) {
    return function () {
        var c = false;
        return c = a[b].apply(a, arguments)
    }
};
dhtmlx.isNotDefined = function (a) {
    return typeof a == "undefined"
};
dhtmlx.delay = function (a, b, c, d) {
    setTimeout(function () {
        var e = a.apply(b, c);
        a = b = c = null;
        return e
    }, d || 1)
};
dhtmlx.uid = function () {
    if (!this.S) this.S = (new Date).valueOf();
    this.S++;
    return this.S
};
dhtmlx.toNode = function (a) {
    if (typeof a == "string") return document.getElementById(a);
    return a
};
dhtmlx.toArray = function (a) {
    return dhtmlx.extend(a || [], dhtmlx.PowerArray)
};
dhtmlx.toFunctor = function (a) {
    return typeof a == "string" ? eval(a) : a
};
dhtmlx.j = {};
dhtmlx.event = function (a, b, c, d) {
    a = dhtmlx.toNode(a);
    var e = dhtmlx.uid();
    dhtmlx.j[e] = [a, b, c];
    if (d) c = dhtmlx.bind(c, d);
    if (a.addEventListener) a.addEventListener(b, c, false);
    else a.attachEvent && a.attachEvent("on" + b, c);
    return e
};
dhtmlx.eventRemove = function (a) {
    if (a) {
        var b = dhtmlx.j[a];
        if (b[0].removeEventListener) b[0].removeEventListener(b[1], b[2], false);
        else b[0].detachEvent && b[0].detachEvent("on" + b[1], b[2]);
        delete this.j[a]
    }
};
dhtmlx.EventSystem = {
    k: function () {
        this.j = {};
        this.A = {};
        this.s = {}
    },
    block: function () {
        this.j.U = true
    },
    unblock: function () {
        this.j.U = false
    },
    mapEvent: function (a) {
        dhtmlx.extend(this.s, a)
    },
    callEvent: function (a, b) {
        if (this.j.U) return true;
        a = a.toLowerCase();
        var c = this.j[a.toLowerCase()],
            d = true;
        if (c) for (var e = 0; e < c.length; e++) if (c[e].apply(this, b || []) === false) d = false;
        if (this.s[a] && !this.s[a].callEvent(a, b)) d = false;
        return d
    },
    attachEvent: function (a, b, c) {
        a = a.toLowerCase();
        c = c || dhtmlx.uid();
        b = dhtmlx.toFunctor(b);
        var d = this.j[a] || dhtmlx.toArray();
        d.push(b);
        this.j[a] = d;
        this.A[c] = {
            f: b,
            t: a
        };
        return c
    },
    detachEvent: function (a) {
        var b = this.A[a].t,
            c = this.A[a].f;
        b = this.j[b];
        b.remove(c);
        delete this.A[a]
    }
};
dhtmlx.PowerArray = {
    removeAt: function (a, b) {
        if (a >= 0) this.splice(a, b || 1)
    },
    remove: function (a) {
        this.removeAt(this.find(a))
    },
    insertAt: function (a, b) {
        if (!b && b !== 0) this.push(a);
        else {
            var c = this.splice(b, this.length - b);
            this[b] = a;
            this.push.apply(this, c)
        }
    },
    find: function (a) {
        for (i = 0; i < this.length; i++) if (a == this[i]) return i;
        return -1
    },
    each: function (a, b) {
        for (var c = 0; c < this.length; c++) a.call(b || this, this[c])
    },
    map: function (a, b) {
        for (var c = 0; c < this.length; c++) this[c] = a.call(b || this, this[c]);
        return this
    }
};
dhtmlx.env = {};
if (navigator.userAgent.indexOf("Opera") != -1) dhtmlx.La = true;
else {
    dhtmlx.r = !! document.all;
    dhtmlx.Ka = !document.all;
    dhtmlx.Ma = navigator.userAgent.indexOf("KHTML") != -1;
    if (navigator.appVersion.indexOf("MSIE 8.0") != -1 && document.compatMode != "BackCompat") dhtmlx.r = 8
}
dhtmlx.env = {};
(function () {
    dhtmlx.env.transform = false;
    dhtmlx.env.transition = false;
    var a = {};
    a.names = ["transform", "transition"];
    a.transform = ["transform", "WebkitTransform", "MozTransform", "oTransform"];
    a.transition = ["transition", "WebkitTransition", "MozTransition", "oTransition"];
    for (var b = document.createElement("DIV"), c = 0; c < a.names.length; c++) for (; p = a[a.names[c]].pop();) if (typeof b.style[p] != "undefined") dhtmlx.env[a.names[c]] = true
})();
dhtmlx.env.transform_prefix = function () {
    var a;
    if (dhtmlx.La) a = "-o-";
    else {
        a = "";
        if (dhtmlx.Ka) a = "-moz-";
        if (dhtmlx.Ma) a = "-webkit-"
    }
    return a
}();
dhtmlx.env.svg = function () {
    return document.implementation.hasFeature("http://www.w3.org/TR/SVG11/feature#BasicStructure", "1.1")
}();
dhtmlx.zIndex = {
    drag: 1E4
};
dhtmlx.html = {
    create: function (a, b, c) {
        b = b || {};
        var d = document.createElement(a);
        for (var e in b) d.setAttribute(e, b[e]);
        if (b.style) d.style.cssText = b.style;
        if (b["class"]) d.className = b["class"];
        if (c) d.innerHTML = c;
        return d
    },
    getValue: function (a) {
        a = dhtmlx.toNode(a);
        if (!a) return "";
        return dhtmlx.isNotDefined(a.value) ? a.innerHTML : a.value
    },
    remove: function (a) {
        if (a instanceof Array) for (var b = 0; b < a.length; b++) this.remove(a[b]);
        else a && a.parentNode && a.parentNode.removeChild(a)
    },
    insertBefore: function (a, b, c) {
        if (a) b ? b.parentNode.insertBefore(a, b) : c.appendChild(a)
    },
    locate: function (a, b) {
        a = a || event;
        for (var c = a.target || a.srcElement; c;) {
            if (c.getAttribute) {
                var d = c.getAttribute(b);
                if (d) return d
            }
            c = c.parentNode
        }
        return null
    },
    offset: function (a) {
        if (a.getBoundingClientRect) {
            var b = a.getBoundingClientRect(),
                c = document.body,
                d = document.documentElement,
                e = window.pageYOffset || d.scrollTop || c.scrollTop,
                f = window.pageXOffset || d.scrollLeft || c.scrollLeft,
                g = d.clientTop || c.clientTop || 0,
                i = d.clientLeft || c.clientLeft || 0,
                j = b.top + e - g,
                k = b.left + f - i;
            return {
                y: Math.round(j),
                x: Math.round(k)
            }
        } else {
            for (k = j = 0; a;) {
                j += parseInt(a.offsetTop, 10);
                k += parseInt(a.offsetLeft, 10);
                a = a.offsetParent
            }
            return {
                y: j,
                x: k
            }
        }
    },
    pos: function (a) {
        a = a || event;
        if (a.pageX || a.pageY) return {
            x: a.pageX,
            y: a.pageY
        };
        var b = dhtmlx.r && document.compatMode != "BackCompat" ? document.documentElement : document.body;
        return {
            x: a.clientX + b.scrollLeft - b.clientLeft,
            y: a.clientY + b.scrollTop - b.clientTop
        }
    },
    preventEvent: function (a) {
        a && a.preventDefault && a.preventDefault();
        dhtmlx.html.stopEvent(a)
    },
    stopEvent: function (a) {
        (a || event).cancelBubble = true;
        return false
    },
    addCss: function (a, b) {
        a.className += " " + b
    },
    removeCss: function (a, b) {
        a.className = a.className.replace(RegExp(b, "g"), "")
    }
};
(function () {
    var a = document.getElementsByTagName("SCRIPT");
    if (a.length) {
        a = (a[a.length - 1].getAttribute("src") || "").split("/");
        a.splice(a.length - 1, 1);
        dhtmlx.codebase = a.slice(0, a.length).join("/") + "/"
    }
})();
dhtmlx.ui = {};
dhtmlx.Destruction = {
    k: function () {
        dhtmlx.destructors.push(this)
    },
    destructor: function () {
        this.destructor = function () {};
        this.ib = this.v = null;
        this.fa && document.body.appendChild(this.fa);
        this.fa = null;
        if (this.g) {
            this.g.innerHTML = "";
            this.g.v = null
        }
        this.data = this.g = this.L = null;
        this.j = this.A = {}
    }
};
dhtmlx.destructors = [];
dhtmlx.event(window, "unload", function () {
    for (var a = 0; a < dhtmlx.destructors.length; a++) dhtmlx.destructors[a].destructor();
    dhtmlx.destructors = [];
    for (var b in dhtmlx.j) {
        a = dhtmlx.j[b];
        if (a[0].removeEventListener) a[0].removeEventListener(a[1], a[2], false);
        else a[0].detachEvent && a[0].detachEvent("on" + a[1], a[2]);
        delete dhtmlx.j[b]
    }
});
dhtmlx.math = {};
dhtmlx.math.fb = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"];
dhtmlx.math.toHex = function (a, b) {
    a = parseInt(a, 10);
    for (str = ""; a > 0;) {
        str = this.fb[a % 16] + str;
        a = Math.floor(a / 16)
    }
    for (; str.length < b;) str = "0" + str;
    return str
};
dhtmlx.ui.Map = function (a) {
    this.name = "Map";
    this.q = "map_" + dhtmlx.uid();
    this.Pa = a;
    this.s = []
};
dhtmlx.ui.Map.prototype = {
    addRect: function (a, b, c) {
        this.X(a, "RECT", b, c)
    },
    addPoly: function (a, b) {
        this.X(a, "POLY", b)
    },
    X: function (a, b, c, d) {
        var e = "";
        if (arguments.length == 4) e = "userdata='" + d + "'";
        this.s.push("<area " + this.Pa + "='" + a + "' shape='" + b + "' coords='" + c.join() + "' " + e + "></area>")
    },
    addSector: function (a, b, c, d, e, f, g) {
        var i = [];
        i.push(d);
        i.push(Math.floor(e * g));
        for (var j = b; j < c; j += Math.PI / 18) {
            i.push(Math.floor(d + f * Math.cos(j)));
            i.push(Math.floor((e + f * Math.sin(j)) * g))
        }
        i.push(Math.floor(d + f * Math.cos(c)));
        i.push(Math.floor((e + f * Math.sin(c)) * g));
        i.push(d);
        i.push(Math.floor(e * g));
        return this.addPoly(a, i)
    },
    render: function (a) {
        var b = dhtmlx.html.create("DIV");
        b.style.cssText = "position:absolute; width:100%; height:100%; top:0px; left:0px;";
        a.appendChild(b);
        var c = dhtmlx.r ? "" : "src='data:image/gif;base64,R0lGODlhEgASAIAAAP///////yH5BAUUAAEALAAAAAASABIAAAIPjI+py+0Po5y02ouz3pwXADs='";
        b.innerHTML = "<map id='" + this.q + "' name='" + this.q + "'>" + this.s.join("\n") + "</map><img " + c + " class='dhx_map_img' usemap='#" + this.q + "'>";
        a.v = b;
        this.s = []
    }
};
dhtmlx.chart = {};
dhtmlx.chart.area = {
    pvt_render_area: function (a, b, c, d, e, f) {
        var g = this.C(a, b, c, d, e),
            i = Math.floor(g.cellWidth / 2);
        if (b.length) {
            a.globalAlpha = this.e.alpha.call(this, b[0]);
            a.fillStyle = this.e.color.call(this, b[0]);
            var j = this.p(b[0], c, d, g),
                k = this.e.offset ? c.x + g.cellWidth * 0.5 : c.x;
            a.beginPath();
            a.moveTo(k, d.y);
            a.lineTo(k, j);
            f.addRect(b[0].id, [k - i, j - i, k + i, j + i]);
            this.e.yAxis || this.renderTextAt(false, !this.e.offset ? false : true, k, j - this.e.labelOffset, this.e.label(b[0]));
            for (var h = 1; h < b.length; h++) {
                var m = k + Math.floor(g.cellWidth * h) - 0.5,
                    l = this.p(b[h], c, d, g);
                a.lineTo(m, l);
                f.addRect(b[h].id, [m - i, l - i, m + i, l + i]);
                this.e.yAxis || this.renderTextAt(false, !this.e.offset && h == b.length - 1 ? "left" : "center", m, l - this.e.labelOffset, this.e.label(b[h]))
            }
            a.lineTo(k + Math.floor(g.cellWidth * [b.length - 1]), d.y);
            a.lineTo(k, d.y);
            a.fill()
        }
    }
};
dhtmlx.chart.stackedArea = {
    pvt_render_stackedArea: function (a, b, c, d, e, f) {
        var g = this.C(a, b, c, d, e),
            i = Math.floor(g.cellWidth / 2),
            j = [];
        if (b.length) {
            a.globalAlpha = this.e.alpha.call(this, b[0]);
            a.fillStyle = this.e.color.call(this, b[0]);
            var k = e ? b[0].$startY : d.y,
                h = this.e.offset ? c.x + g.cellWidth * 0.5 : c.x,
                m = this.p(b[0], c, d, g) - (e ? d.y - k : 0);
            j[0] = m;
            a.beginPath();
            a.moveTo(h, k);
            a.lineTo(h, m);
            f.addRect(b[0].id, [h - i, m - i, h + i, m + i]);
            this.e.yAxis || this.renderTextAt(false, true, h, m - this.e.labelOffset, this.e.label(b[0]));
            for (var l = 1; l < b.length; l++) {
                var n = h + Math.floor(g.cellWidth * l) - 0.5,
                    o = this.p(b[l], c, d, g) - (e ? d.y - b[l].$startY : 0);
                j[l] = o;
                a.lineTo(n, o);
                f.addRect(b[l].id, [n - i, o - i, n + i, o + i]);
                this.e.yAxis || this.renderTextAt(false, true, n, o - this.e.labelOffset, this.e.label(b[l]))
            }
            a.lineTo(h + Math.floor(g.cellWidth * [b.length - 1]), k);
            if (e) for (l = b.length - 1; l >= 0; l--) {
                n = h + Math.floor(g.cellWidth * l) - 0.5;
                var s = b[l].$startY;
                a.lineTo(n, s)
            } else a.lineTo(h + Math.floor(g.cellWidth * (length - 1)) - 0.5, k);
            a.lineTo(h, k);
            a.fill();
            for (l = 0; l < b.length; l++) b[l].$startY = j[l]
        }
    }
};
dhtmlx.chart.spline = {
    pvt_render_spline: function (a, b, c, d, e) {
        var f = this.C(a, b, c, d, e);
        Math.floor(f.cellWidth / 2);
        var g = [];
        if (b.length) {
            var i = this.e.offset ? c.x + f.cellWidth * 0.5 : c.x;
            for (e = 0; e < b.length; e++) {
                var j = !e ? i : Math.floor(f.cellWidth * e) - 0.5 + i,
                    k = this.p(b[e], c, d, f);
                g.push({
                    x: j,
                    y: k
                })
            }
            var h = this.Ha(g);
            for (e = 0; e < g.length - 1; e++) {
                var m = g[e].x;
                c = g[e].y;
                for (var l = g[e + 1].x, n = g[e + 1].y, o = m; o < l; o++) this.i(a, o, this.P(o, m, e, h.a, h.b, h.c, h.d), o + 1, this.P(o + 1, m, e, h.a, h.b, h.c, h.d), this.e.line.color(b[e]), this.e.line.width);
                this.i(a, l - 1, this.P(o, m, e, h.a, h.b, h.c, h.d), l, n, this.e.line.color(b[e]), this.e.line.width);
                this.M(a, m, c, b[e], this.e.label(b[e]))
            }
            this.M(a, l, n, b[e], this.e.label(b[e]))
        }
    },
    Ha: function (a) {
        var b, c, d, e, f, g, i, j, k;
        b = [];
        m = [];
        k = a.length;
        for (var h = 0; h < k - 1; h++) {
            b[h] = a[h + 1].x - a[h].x;
            m[h] = (a[h + 1].y - a[h].y) / b[h]
        }
        c = [];
        d = [];
        c[0] = 0;
        c[1] = 2 * (b[0] + b[1]);
        d[0] = 0;
        d[1] = 6 * (m[1] - m[0]);
        for (h = 2; h < k - 1; h++) {
            c[h] = 2 * (b[h - 1] + b[h]) - b[h - 1] * b[h - 1] / c[h - 1];
            d[h] = 6 * (m[h] - m[h - 1]) - b[h - 1] * d[h - 1] / c[h - 1]
        }
        e = [];
        e[k - 1] = e[0] = 0;
        for (h = k - 2; h >= 1; h--) e[h] = (d[h] - b[h] * e[h + 1]) / c[h];
        f = [];
        g = [];
        i = [];
        j = [];
        for (h = 0; h < k - 1; h++) {
            f[h] = a[h].y;
            g[h] = -b[h] * e[h + 1] / 6 - b[h] * e[h] / 3 + (a[h + 1].y - a[h].y) / b[h];
            i[h] = e[h] / 2;
            j[h] = (e[h + 1] - e[h]) / (6 * b[h])
        }
        return {
            a: f,
            b: g,
            c: i,
            d: j
        }
    },
    P: function (a, b, c, d, e, f, g) {
        return d[c] + (a - b) * (e[c] + (a - b) * (f[c] + (a - b) * g[c]))
    }
};
dhtmlx.chart.barH = {
    pvt_render_barH: function (a, b, c, d, e, f) {
        var g, i, j, k, h = d.x - c.x,
            m = !! this.e.yAxis,
            l = this.O("h");
        g = l.max;
        i = l.min;
        var n = Math.floor((d.y - c.y) / b.length);
        e || this.$(a, b, c, d, i, g, n);
        if (m) {
            g = parseFloat(this.e.xAxis.end);
            i = parseFloat(this.e.xAxis.start)
        }
        var o = this.z(i, g);
        k = o[0];
        j = o[1];
        var s = k ? h / k : 10;
        if (!m) {
            var t = 10;
            s = k ? (h - t) / k : 10
        }
        var q = parseInt(this.e.width, 10);
        if (q * this.h.length + 4 > n) q = n / this.h.length - 4;
        var v = Math.floor((n - q * this.h.length) / 2),
            p = typeof this.e.radius != "undefined" ? parseInt(this.e.radius, 10) : Math.round(q / 5),
            u = false,
            r = this.e.gradient;
        if (r && typeof r != "function") {
            u = r;
            r = false
        } else if (r) {
            r = a.createLinearGradient(c.x, c.y, d.x, c.y);
            this.e.gradient(r)
        }
        m || this.i(a, c.x - 0.5, c.y, c.x - 0.5, d.y, "#000000", 1);
        for (d = 0; d < b.length; d++) {
            var w = parseFloat(this.e.value(b[d]));
            if (w > g) w = g;
            w -= i;
            w *= j;
            var x = c.x,
                y = c.y + v + d * n + (q + 1) * e;
            if (w < 0 || this.e.yAxis && w === 0) this.renderTextAt("middle", true, x + 10, y + q / 2 + v, this.e.label(b[d]));
            else {
                m || (w += t / s);
                var B = r || this.e.color.call(this, b[d]);
                if (this.e.border) {
                    a.beginPath();
                    a.fillStyle = B;
                    this.o(a, x, y, q, p, s, w, 0);
                    a.lineTo(x, 0);
                    a.fill();
                    a.fillStyle = "#000000";
                    a.globalAlpha = 0.37;
                    a.beginPath();
                    this.o(a, x, y, q, p, s, w, 0);
                    a.fill()
                }
                a.globalAlpha = this.e.alpha.call(this, b[d]);
                a.fillStyle = r || this.e.color.call(this, b[d]);
                a.beginPath();
                var z = this.o(a, x, y, q, p, s, w, this.e.border ? 1 : 0);
                if (r && !u) a.lineTo(c.x + h, y + (this.e.border ? 1 : 0));
                a.fill();
                a.globalAlpha = 1;
                if (u != false) {
                    var A = this.G(a, c.x, y + q, c.x + s * w + 2, y, u, B, "x");
                    a.fillStyle = A.gradient;
                    a.beginPath();
                    z = this.o(a, x, y + A.offset, q - A.offset * 2, p, s, w, A.offset);
                    a.fill();
                    a.globalAlpha = 1
                }
                this.renderTextAt("middle", false, z[0] + 3, parseInt(y + (z[1] - y) / 2, 10), this.e.label(b[d]));
                f.addRect(b[d].id, [x, y, z[0], z[1]], e)
            }
        }
    },
    o: function (a, b, c, d, e, f, g, i) {
        var j = 0;
        if (e > f * g) {
            var k = (e - f * g) / e;
            j = -Math.asin(k) + Math.PI / 2
        }
        a.moveTo(b, c + i);
        var h = b + f * g - e - (e ? 0 : i);
        e < f * g && a.lineTo(h, c + i);
        f = c + e;
        e && a.arc(h, f, e - i, -Math.PI / 2 + j, 0, false);
        var m = c + d - e - (e ? 0 : i),
            l = h + e - (e ? i : 0);
        a.lineTo(l, m);
        var n = h;
        e && a.arc(n, m, e - i, 0, Math.PI / 2 - j, false);
        var o = c + d - i;
        a.lineTo(b, o);
        a.lineTo(b, c + i);
        return [l, o]
    },
    $: function (a, b, c, d, e, f, g) {
        this.xa(a, b, c, d, e, f);
        this.ya(a, b, c, d, g)
    },
    ya: function (a, b, c, d, e) {
        if (this.e.yAxis) {
            var f = c.x - 0.5,
                g = d.y + 0.5,
                i = c.y;
            this.i(a, f, g, f, i, this.e.yAxis.color, 1);
            for (a = 0; a < b.length; a++) this.renderTextAt("middle", 0, 0, i + e / 2 + a * e, this.e.yAxis.template(b[a]), "dhx_axis_item_y", c.x - 5);
            this.oa(c, d)
        }
    },
    xa: function (a, b, c, d, e, f) {
        var g, i = {},
            j = this.e.xAxis;
        if (j) {
            b = d.y + 0.5;
            var k = c.x - 0.5,
                h = d.x - 0.5;
            this.i(a, k, b, h, b, j.color, 1);
            if (j.step) g = parseFloat(j.step);
            if (typeof j.step == "undefined" || typeof j.start == "undefined" || typeof j.end == "undefined") {
                i = this.V(e, f);
                e = i.start;
                f = i.end;
                g = i.step;
                this.e.xAxis.end = f;
                this.e.xAxis.start = e;
                this.e.xAxis.step = g
            }
            if (g !== 0) {
                for (var m = (h - k) * g / (f - e), l = 0, n = e; n <= f; n += g) {
                    if (i.fixNum) n = parseFloat((new Number(n)).toFixed(i.fixNum));
                    var o = Math.floor(k + l * m) + 0.5;
                    n != e && j.lines && this.i(a, o, b, o, c.y, this.e.xAxis.color, 0.2);
                    this.renderTextAt(false, true, o, b + 2, j.template(n.toString()), "dhx_axis_item_x");
                    l++
                }
                this.renderTextAt(true, false, k, d.y + this.e.padding.bottom - 3, this.e.xAxis.title, "dhx_axis_title_x", d.x - c.x);
                j.lines && this.i(a, k, c.y - 0.5, h, c.y - 0.5, this.e.xAxis.color, 0.2)
            }
        }
    }
};
dhtmlx.chart.stackedBarH = {
    pvt_render_stackedBarH: function (a, b, c, d, e, f) {
        var g, i, j, k, h = d.x - c.x,
            m = !! this.e.yAxis;
        i = this.Q(b);
        g = i.max;
        i = i.min;
        var l = Math.floor((d.y - c.y) / b.length);
        e || this.$(a, b, c, d, i, g, l);
        if (m) {
            g = parseFloat(this.e.xAxis.end);
            i = parseFloat(this.e.xAxis.start)
        }
        j = this.z(i, g);
        k = j[0];
        j = j[1];
        var n = k ? h / k : 10;
        if (!m) {
            var o = 10;
            n = k ? (h - o) / k : 10
        }
        k = parseInt(this.e.width, 10);
        if (k + 4 > l) k = l - 4;
        var s = Math.floor((l - k) / 2),
            t = 0,
            q = false,
            v = this.e.gradient;
        q = false;
        if (v = this.e.gradient) q = true;
        m || this.i(a, c.x - 0.5, c.y, c.x - 0.5, d.y, "#000000", 1);
        for (d = 0; d < b.length; d++) {
            if (!e) b[d].$startX = c.x;
            var p = parseFloat(this.e.value(b[d]));
            if (p > g) p = g;
            p -= i;
            p *= j;
            var u = c.x,
                r = c.y + s + d * l;
            if (e) u = b[d].$startX || u;
            if (p < 0 || this.e.yAxis && p === 0) this.renderTextAt("middle", true, u + 10, r + k / 2, this.e.label(b[d]));
            else {
                m || (p += o / n);
                var w = this.e.color.call(this, b[d]);
                if (this.e.border) {
                    a.beginPath();
                    a.fillStyle = w;
                    this.o(a, u, r, k, t, n, p, 0);
                    a.lineTo(u, 0);
                    a.fill();
                    a.fillStyle = "#000000";
                    a.globalAlpha = 0.37;
                    a.beginPath();
                    this.o(a, u, r, k, t, n, p, 0);
                    a.fill()
                }
                a.globalAlpha = 1;
                a.globalAlpha = this.e.alpha.call(this, b[d]);
                a.fillStyle = this.e.color.call(this, b[d]);
                a.beginPath();
                var x = this.o(a, u, r, k, t, n, p, this.e.border ? 1 : 0);
                if (v && !q) a.lineTo(c.x + h, r + (this.e.border ? 1 : 0));
                a.fill();
                if (q != false) {
                    w = this.G(a, u, r + k, u, r, q, w, "x");
                    a.fillStyle = w.gradient;
                    a.beginPath();
                    x = this.o(a, u, r, k, t, n, p, 0);
                    a.fill();
                    a.globalAlpha = 1
                }
                this.renderTextAt("middle", true, b[d].$startX + (x[0] - b[d].$startX) / 2 - 1, r + (x[1] - r) / 2, this.e.label(b[d]));
                f.addRect(b[d].id, [b[d].$startX, r, x[0], x[1]], e);
                b[d].$startX = x[0]
            }
        }
    }
};
dhtmlx.chart.stackedBar = {
    pvt_render_stackedBar: function (a, b, c, d, e, f) {
        var g, i, j, k = d.y - c.y;
        j = !! this.e.yAxis;
        var h = !! this.e.xAxis;
        i = this.Q(b);
        g = i.max;
        i = i.min;
        var m = Math.floor((d.x - c.x) / b.length);
        e || this.N(a, b, c, d, i, g, m);
        if (j) {
            g = parseFloat(this.e.yAxis.end);
            i = parseFloat(this.e.yAxis.start)
        }
        g = this.z(i, g);
        j = g[0];
        g = g[1];
        j = j ? k / j : 10;
        var l = parseInt(this.e.width, 10);
        if (l + 4 > m) l = m - 4;
        var n = Math.floor((m - l) / 2),
            o = this.e.gradient ? this.e.gradient : false;
        h || this.i(a, c.x, d.y + 0.5, d.x, d.y + 0.5, "#000000", 1);
        for (h = 0; h < b.length; h++) {
            var s = parseFloat(this.e.value(b[h]));
            if (s) {
                e || (s -= i);
                s *= g;
                var t = c.x + n + h * m,
                    q = d.y;
                if (e) q = b[h].$startY || q;
                if (!(q < c.y + 1)) if (s < 0 || this.e.yAxis && s === 0) this.renderTextAt(true, true, t + Math.floor(l / 2), q, this.e.label(b[h]));
                else {
                    var v = this.e.color.call(this, b[h]);
                    if (this.e.border) {
                        a.beginPath();
                        a.fillStyle = v;
                        this.I(a, t - 1, q, l + 2, j, s, 0, c.y);
                        a.lineTo(t, q);
                        a.fill();
                        a.fillStyle = "#000000";
                        a.globalAlpha = 0.37;
                        a.beginPath();
                        this.I(a, t - 1, q, l + 2, j, s, 0, c.y);
                        a.fill()
                    }
                    a.globalAlpha = this.e.alpha.call(this, b[h]);
                    a.fillStyle = this.e.color.call(this, b[h]);
                    a.beginPath();
                    var p = this.I(a, t, q, l, j, s, this.e.border ? 1 : 0, c.y);
                    a.fill();
                    a.globalAlpha = 1;
                    if (o) {
                        v = this.G(a, t, q, t + l, p[1], o, v, "y");
                        a.fillStyle = v.gradient;
                        a.beginPath();
                        p = this.I(a, t + v.offset, q, l - v.offset * 2, j, s, this.e.border ? 1 : 0, c.y);
                        a.fill();
                        a.globalAlpha = 1
                    }
                    this.renderTextAt(false, true, t + Math.floor(l / 2), p[1] + (q - p[1]) / 2 - 7, this.e.label(b[h]));
                    f.addRect(b[h].id, [t, p[1], p[0], b[h].$startY || q], e);
                    b[h].$startY = this.e.border ? p[1] + 1 : p[1]
                }
            }
        }
    },
    I: function (a, b, c, d, e, f, g, i) {
        a.moveTo(b, c);
        f = c - e * f + g;
        if (f < i) f = i;
        a.lineTo(b, f);
        e = b + d;
        f = f;
        a.lineTo(e, f);
        var j = b + d;
        a.lineTo(j, c);
        a.lineTo(b, c);
        return [j, f - 2 * g]
    }
};
dhtmlx.chart.line = {
    pvt_render_line: function (a, b, c, d, e, f) {
        e = this.C(a, b, c, d, e);
        var g = Math.floor(e.cellWidth / 2);
        if (b.length) for (var i = this.p(b[0], c, d, e), j = this.e.offset ? c.x + e.cellWidth * 0.5 : c.x, k = j, h = 1; h <= b.length; h++) {
            var m = Math.floor(e.cellWidth * h) - 0.5 + k;
            if (b.length != h) {
                var l = this.p(b[h], c, d, e);
                this.i(a, j, i, m, l, this.e.line.color(b[h - 1]), this.e.line.width)
            }
            this.M(a, j, i, b[h - 1], !! this.e.offset);
            f.addRect(b[h - 1].id, [j - g, i - g, j + g, i + g]);
            i = l;
            j = m
        }
    },
    M: function (a, b, c, d, e) {
        var f = parseInt(this.e.item.radius, 10);
        a.lineWidth = parseInt(this.e.item.borderWidth, 10);
        a.fillStyle = this.e.item.color(d);
        a.strokeStyle = this.e.item.borderColor(d);
        a.beginPath();
        a.arc(b, c, f, 0, Math.PI * 2, true);
        a.fill();
        a.stroke();
        e && this.renderTextAt(false, true, b, c - f - this.e.labelOffset, this.e.label(d))
    },
    p: function (a, b, c, d) {
        var e = d.minValue,
            f = d.maxValue,
            g = d.unit,
            i = d.valueFactor;
        a = this.e.value(a);
        i = (parseFloat(a) - e) * i;
        this.e.yAxis || (i += d.startValue / g);
        d = c.y - Math.floor(g * i);
        if (i < 0) d = c.y;
        if (a > f) d = b.y;
        if (a < e) d = c.y;
        return d
    },
    C: function (a, b, c, d, e) {
        var f = {};
        f.totalHeight = d.y - c.y;
        f.cellWidth = Math.round((d.x - c.x) / (!this.e.offset ? b.length - 1 : b.length));
        var g = !! this.e.yAxis,
            i = this.e.view.indexOf("stacked") != -1 ? this.Q(b) : this.O();
        f.maxValue = i.max;
        f.minValue = i.min;
        e || this.N(a, b, c, d, f.minValue, f.maxValue, f.cellWidth);
        if (g) {
            f.maxValue = parseFloat(this.e.yAxis.end);
            f.minValue = parseFloat(this.e.yAxis.start)
        }
        b = this.z(f.minValue, f.maxValue);
        a = b[0];
        f.valueFactor = b[1];
        f.unit = a ? f.totalHeight / a : 10;
        f.startValue = 0;
        if (!g) {
            f.startValue = f.unit > 10 ? f.unit : 10;
            f.unit = a ? (f.totalHeight - f.startValue) / a : 10
        }
        return f
    }
};
dhtmlx.chart.bar = {
    pvt_render_bar: function (a, b, c, d, e, f) {
        var g, i, j, k, h = d.y - c.y,
            m = !! this.e.yAxis,
            l = !! this.e.xAxis;
        i = this.O();
        g = i.max;
        i = i.min;
        var n = Math.floor((d.x - c.x) / b.length);
        !e && !(this.e.origin != "auto" && !m) && this.N(a, b, c, d, i, g, n);
        if (m) {
            g = parseFloat(this.e.yAxis.end);
            i = parseFloat(this.e.yAxis.start)
        }
        j = this.z(i, g);
        k = j[0];
        j = j[1];
        var o = k ? h / k : k;
        if (!m && !(this.e.origin != "auto" && l)) {
            var s = 10;
            o = k ? (h - s) / k : s
        }!e && this.e.origin != "auto" && !m && this.e.origin > i && this.da(a, b, c, d, n, d.y - o * (this.e.origin - i));
        h = parseInt(this.e.width, 10);
        if (this.h && h * this.h.length + 4 > n) h = n / this.h.length - 4;
        k = Math.floor((n - h * this.h.length) / 2);
        var t = typeof this.e.radius != "undefined" ? parseInt(this.e.radius, 10) : Math.round(h / 5),
            q = false,
            v = this.e.gradient;
        if (v && typeof v != "function") {
            q = v;
            v = false
        } else if (v) {
            v = a.createLinearGradient(0, d.y, 0, c.y);
            this.e.gradient(v)
        }
        l || this.i(a, c.x, d.y + 0.5, d.x, d.y + 0.5, "#000000", 1);
        for (var p = 0; p < b.length; p++) {
            var u = parseFloat(this.e.value(b[p]));
            if (u > g) u = g;
            u -= i;
            u *= j;
            var r = c.x + k + p * n + (h + 1) * e,
                w = d.y;
            if (u < 0 || this.e.yAxis && u === 0 && !(this.e.origin != "auto" && this.e.origin > i)) this.renderTextAt(true, true, r + Math.floor(h / 2), w, this.e.label(b[p]));
            else {
                if (!m && !(this.e.origin != "auto" && l)) u += s / o;
                var x = v || this.e.color.call(this, b[p]);
                this.e.border && this.va(a, r, w, h, i, t, o, u, x);
                a.globalAlpha = this.e.alpha.call(this, b[p]);
                var y = this.ua(a, c, r, w, h, i, t, o, u, x, v, q);
                a.globalAlpha = 1;
                q && this.wa(a, r, w, h, i, t, o, u, x, q);
                y[0] != r ? this.renderTextAt(false, true, r + Math.floor(h / 2), y[1], this.e.label(b[p])) : this.renderTextAt(true, true, r + Math.floor(h / 2), y[3], this.e.label(b[p]));
                f.addRect(b[p].id, [r, y[3], y[2], y[1]], e)
            }
        }
    },
    K: function (a, b, c, d, e, f, g) {
        var i = this.e.xAxis,
            j = c;
        if (i && this.e.origin != "auto" && this.e.origin > g) {
            c -= (this.e.origin - g) * e;
            j = c;
            d -= this.e.origin - g;
            if (d < 0) {
                d *= -1;
                a.translate(b + f, c);
                a.rotate(Math.PI);
                c = b = 0
            }
            c -= 0.5
        }
        return {
            value: d,
            x0: b,
            y0: c,
            start: j
        }
    },
    ua: function (a, b, c, d, e, f, g, i, j, k, h, m) {
        a.save();
        a.fillStyle = k;
        var l = this.K(a, c, d, j, i, e, f);
        e = this.H(a, l.x0, l.y0, e, g, i, l.value, this.e.border ? 1 : 0);
        if (h && !m) a.lineTo(l.x0 + (this.e.border ? 1 : 0), b.y);
        a.fill();
        a.restore();
        a = l.x0;
        b = l.x0 != c ? c + e[0] : e[0];
        d = l.x0 != c ? l.start - e[1] : d;
        c = l.x0 != c ? l.start : e[1];
        return [a, d, b, c]
    },
    va: function (a, b, c, d, e, f, g, i, j) {
        a.save();
        b = this.K(a, b, c, i, g, d, e);
        a.fillStyle = j;
        this.H(a, b.x0, b.y0, d, f, g, b.value, 0);
        a.lineTo(b.x0, 0);
        a.fill();
        a.fillStyle = "#000000";
        a.globalAlpha = 0.37;
        this.H(a, b.x0, b.y0, d, f, g, b.value, 0);
        a.fill();
        a.restore()
    },
    wa: function (a, b, c, d, e, f, g, i, j, k) {
        a.save();
        b = this.K(a, b, c, i, g, d, e);
        j = this.G(a, b.x0, b.y0, b.x0 + d, b.y0 - g * b.value + 2, k, j, "y");
        a.fillStyle = j.gradient;
        this.H(a, b.x0 + j.offset, b.y0, d - j.offset * 2, f, g, b.value, j.offset);
        a.fill();
        a.restore()
    },
    H: function (a, b, c, d, e, f, g, i) {
        a.beginPath();
        var j = 0;
        if (e > f * g) {
            var k = (e - f * g) / e;
            j = -Math.acos(k) + Math.PI / 2
        }
        a.moveTo(b + i, c);
        var h = c - Math.floor(f * g) + e + (e ? 0 : i);
        e < f * g && a.lineTo(b + i, h);
        f = b + e;
        e && a.arc(f, h, e - i, -Math.PI + j, -Math.PI / 2, false);
        g = b + d - e - (e ? 0 : i);
        f = h - e + (e ? i : 0);
        a.lineTo(g, f);
        h = h;
        e && a.arc(g, h, e - i, -Math.PI / 2, 0 - j, false);
        d = b + d - i;
        a.lineTo(d, c);
        a.lineTo(b + i, c);
        return [d, f]
    }
};
dhtmlx.chart.pie = {
    pvt_render_pie: function (a, b, c, d, e, f) {
        this.na(a, b, c, d, 1, f)
    },
    na: function (a, b, c, d, e, f) {
        var g = 0,
            i = this.Ga(c, d);
        c = this.e.radius ? this.e.radius : i.radius;
        this.max(this.e.value);
        for (var j = [], k = [], h = 0, m = 0; m < b.length; m++) g += parseFloat(this.e.value(b[m]));
        for (m = 0; m < b.length; m++) {
            k[m] = parseFloat(this.e.value(b[m]));
            j[m] = Math.PI * 2 * (g ? (k[m] + h) / g : 1 / b.length);
            h += k[m]
        }
        d = this.e.x ? this.e.x : i.x;
        var l = this.e.y ? this.e.y : i.y;
        e == 1 && this.e.shadow && this.sa(a, d, l, c);
        l /= e;
        var n = -Math.PI / 2;
        a.scale(1, e);
        for (m = 0; m < b.length; m++) if (k[m]) {
            a.lineWidth = 2;
            a.beginPath();
            a.moveTo(d, l);
            alpha1 = -Math.PI / 2 + j[m] - 1.0E-4;
            a.arc(d, l, c, n, alpha1, false);
            a.lineTo(d, l);
            var o = this.e.color.call(this, b[m]);
            a.fillStyle = o;
            a.strokeStyle = this.e.lineColor(b[m]);
            a.stroke();
            a.fill();
            this.e.pieInnerText && this.ba(d, l, 5 * c / 6, n, alpha1, e, this.e.pieInnerText(b[m], g), true);
            this.e.label && this.ba(d, l, c + this.e.labelOffset, n, alpha1, e, this.e.label(b[m]));
            if (e != 1) {
                this.W(a, d, l, n, alpha1, c, true);
                a.fillStyle = "#000000";
                a.globalAlpha = 0.2;
                this.W(a, d, l, n, alpha1, c, false);
                a.globalAlpha = 1;
                a.fillStyle = o
            }
            f.addSector(b[m].id, n, alpha1, d, l, c, e);
            n = alpha1
        }
        if (this.e.gradient) {
            b = e != 1 ? d + c / 3 : d;
            f = e != 1 ? l + c / 3 : l;
            this.bb(a, d, l, c, b, f)
        }
        a.scale(1, 1 / e)
    },
    Ga: function (a, b) {
        var c = b.x - a.x,
            d = b.y - a.y;
        b = a.x + c / 2;
        a = a.y + d / 2;
        var e = Math.min(c / 2, d / 2);
        return {
            x: b,
            y: a,
            radius: e
        }
    },
    W: function (a, b, c, d, e, f, g) {
        a.lineWidth = 1;
        if (d <= 0 && e >= 0 || d >= 0 && e <= Math.PI || d <= Math.PI && e >= Math.PI) {
            if (d <= 0 && e >= 0) {
                d = 0;
                g = false;
                this.ca(a, b, c, f, d, e)
            }
            if (d <= Math.PI && e >= Math.PI) {
                e = Math.PI;
                g = false;
                this.ca(a, b, c, f, d, e)
            }
            var i = (this.e.height || Math.floor(f / 4)) / this.e.cant;
            a.beginPath();
            a.arc(b, c, f, d, e, false);
            a.lineTo(b + f * Math.cos(e), c + f * Math.sin(e) + i);
            a.arc(b, c + i, f, e, d, true);
            a.lineTo(b + f * Math.cos(d), c + f * Math.sin(d));
            a.fill();
            g && a.stroke()
        }
    },
    ca: function (a, b, c, d, e, f) {
        a.beginPath();
        a.arc(b, c, d, e, f, false);
        a.stroke()
    },
    sa: function (a, b, c, d) {
        for (var e = ["#676767", "#7b7b7b", "#a0a0a0", "#bcbcbc", "#d1d1d1", "#d6d6d6"], f = e.length - 1; f > -1; f--) {
            a.beginPath();
            a.fillStyle = e[f];
            a.arc(b + 2, c + 2, d + f, 0, Math.PI * 2, true);
            a.fill()
        }
    },
    Fa: function (a) {
        a.addColorStop(0, "#ffffff");
        a.addColorStop(0.7, "#7a7a7a");
        a.addColorStop(1, "#000000");
        return a
    },
    bb: function (a, b, c, d, e, f) {
        a.globalAlpha = 0.3;
        a.beginPath();
        var g;
        if (typeof this.e.gradient != "function") {
            g = a.createRadialGradient(e, f, d / 4, b, c, d);
            g = this.Fa(g)
        } else g = this.e.gradient(g);
        a.fillStyle = g;
        a.arc(b, c, d, 0, Math.PI * 2, true);
        a.fill();
        a.globalAlpha = 1
    },
    ba: function (a, b, c, d, e, f, g, i) {
        var j = this.renderText(0, 0, g, 0, 1);
        if (j) {
            var k = j.scrollWidth;
            j.style.width = k + "px";
            if (k > a) k = a;
            var h = 8;
            if (i) h = k / 1.8;
            var m = d + (e - d) / 2;
            c -= (h - 8) / 2;
            var l = -h,
                n = -8,
                o = "left";
            if (m >= Math.PI / 2 && m < Math.PI) {
                l = -k - l + 1;
                o = "right"
            }
            if (m <= 3 * Math.PI / 2 && m >= Math.PI) {
                l = -k - l + 1;
                o = "right"
            }
            d = (b + Math.floor(c * Math.sin(m))) * f + n;
            h = a + Math.floor((c + h / 2) * Math.cos(m)) + l;
            var s = e < Math.PI / 2 + 0.01,
                t = m < Math.PI / 2;
            if (t && s) h = Math.max(h, a + 3);
            else if (!t && !s) h = Math.min(h, a - k);
            if (!i && f < 1 && d > b * f) d += this.e.height || Math.floor(c / 4);
            j.style.top = d + "px";
            j.style.left = h + "px";
            j.style.width = k + "px";
            j.style.textAlign = o;
            j.style.whiteSpace = "nowrap"
        }
    }
};
dhtmlx.chart.pie3D = {
    pvt_render_pie3D: function (a, b, c, d, e, f) {
        this.na(a, b, c, d, this.e.cant, f)
    }
};
dhtmlx.Template = {
    J: {},
    empty: function () {
        return ""
    },
    setter: function (a, b) {
        return dhtmlx.Template.fromHTML(b)
    },
    obj_setter: function (a, b) {
        var c = dhtmlx.Template.setter(a, b),
            d = this;
        return function () {
            return c.apply(d, arguments)
        }
    },
    fromHTML: function (a) {
        if (typeof a == "function") return a;
        if (this.J[a]) return this.J[a];
        a = (a || "").toString();
        a = a.replace(/[\r\n]+/g, "\\n");
        a = a.replace(/\{obj\.([^}?]+)\?([^:]*):([^}]*)\}/g, '"+(obj.$1?"$2":"$3")+"');
        a = a.replace(/\{common\.([^}\(]*)\}/g, '"+common.$1+"');
        a = a.replace(/\{common\.([^\}\(]*)\(\)\}/g, '"+(common.$1?common.$1(obj):"")+"');
        a = a.replace(/\{obj\.([^}]*)\}/g, '"+obj.$1+"');
        a = a.replace(/#([a-z0-9_]+)#/gi, '"+obj.$1+"');
        a = a.replace(/\{obj\}/g, '"+obj+"');
        a = a.replace(/\{-obj/g, "{obj");
        a = a.replace(/\{-common/g, "{common");
        a = 'return "' + a + '";';
        return this.J[a] = Function("obj", "common", a)
    }
};
dhtmlx.Type = {
    add: function (a, b) {
        if (!a.types && a.prototype.types) a = a.prototype;
        var c = b.name || "default";
        this.T(b);
        this.T(b, "edit");
        this.T(b, "loading");
        a.types[c] = dhtmlx.extend(dhtmlx.extend({}, a.types[c] || this.ta), b);
        return c
    },
    ta: {
        css: "default",
        template: function () {
            return ""
        },
        template_edit: function () {
            return ""
        },
        template_loading: function () {
            return "..."
        },
        width: 150,
        height: 80,
        margin: 5,
        padding: 0
    },
    T: function (a, b) {
        b = "template" + (b ? "_" + b : "");
        var c = a[b];
        if (c && typeof c == "string") {
            if (c.indexOf("->") != -1) {
                c = c.split("->");
                switch (c[0]) {
                case "html":
                    c = dhtmlx.html.getValue(c[1]).replace(/\"/g, '\\"');
                    break;
                case "http":
                    c = (new dhtmlx.ajax).sync().get(c[1], {
                        uid: (new Date).valueOf()
                    }).responseText;
                    break;
                default:
                    break
                }
            }
            a[b] = dhtmlx.Template.fromHTML(c)
        }
    }
};
dhtmlx.SingleRender = {
    k: function () {},
    eb: function (a) {
        return this.type.Oa(a, this.type) + this.type.template(a, this.type) + this.type.Na
    },
    render: function () {
        if (!this.callEvent || this.callEvent("onBeforeRender", [this.data])) {
            if (this.data) this.L.innerHTML = this.eb(this.data);
            this.callEvent && this.callEvent("onAfterRender", [])
        }
    }
};
dhtmlx.ui.Tooltip = function (a) {
    this.name = "Tooltip";
    this.version = "3.0";
    if (typeof a == "string") a = {
        template: a
    };
    dhtmlx.extend(this, dhtmlx.Settings);
    dhtmlx.extend(this, dhtmlx.SingleRender);
    this.B(a, {
        type: "default",
        dy: 0,
        dx: 20
    });
    this.L = this.g = document.createElement("DIV");
    this.g.className = "dhx_tooltip";
    dhtmlx.html.insertBefore(this.g, document.body.firstChild)
};
dhtmlx.ui.Tooltip.prototype = {
    show: function (a, b) {
        if (!this.Z) {
            if (this.data != a) {
                this.data = a;
                this.render(a)
            }
            this.g.style.top = b.y + this.e.dy + "px";
            this.g.style.left = b.x + this.e.dx + "px";
            this.g.style.display = "block"
        }
    },
    hide: function () {
        this.data = null;
        this.g.style.display = "none"
    },
    disable: function () {
        this.Z = true
    },
    enable: function () {
        this.Z = false
    },
    types: {
        "default": dhtmlx.Template.fromHTML("{obj.id}")
    },
    template_item_start: dhtmlx.Template.empty,
    template_item_end: dhtmlx.Template.empty
};
dhtmlx.AutoTooltip = {
    tooltip_setter: function (a, b) {
        var c = new dhtmlx.ui.Tooltip(b);
        this.attachEvent("onMouseMove", function (d, e) {
            c.show(this.get(d), dhtmlx.html.pos(e))
        });
        this.attachEvent("onMouseOut", function () {
            c.hide()
        });
        this.attachEvent("onMouseMoving", function () {
            c.hide()
        });
        return c
    }
};
dhtmlx.DataStore = function () {
    this.name = "DataStore";
    dhtmlx.extend(this, dhtmlx.EventSystem);
    this.setDriver("xml");
    this.pull = {};
    this.order = dhtmlx.toArray();
    this.gb = false
};
dhtmlx.DataStore.prototype = {
    setDriver: function (a) {
        this.driver = dhtmlx.DataDriver[a]
    },
    qa: function (a) {
        if (a.item) {
            if (!(a.item instanceof Array)) a.item = [a.item];
            for (var b = 0; b < a.item.length; b++) {
                var c = a.item[b],
                    d = this.id(c);
                a.item[b] = d;
                this.pull[d] = c;
                c.parent = a.id;
                c.level = a.level + 1;
                this.qa(c)
            }
        }
    },
    Wa: function (a) {
        for (var b = this.driver.getInfo(a), c = this.driver.getRecords(a), d = (b.u || 0) * 1, e = 0, f = 0; f < c.length; f++) {
            var g = this.driver.getDetails(c[f]),
                i = this.id(g);
            if (!this.pull[i]) {
                this.order[e + d] = i;
                e++
            }
            this.pull[i] = g;
            if (this.gb) {
                g.level = 1;
                this.qa(g)
            }
        }
        for (f = 0; f < b.w; f++) if (!this.order[f]) {
            i = dhtmlx.uid();
            g = {
                id: i,
                $template: "loading"
            };
            this.pull[i] = g;
            this.order[f] = i
        }
        this.callEvent("onStoreLoad", [this.driver, a]);
        this.refresh()
    },
    id: function (a) {
        return a.id || (a.id = dhtmlx.uid())
    },
    get: function (a) {
        return this.pull[a]
    },
    set: function (a, b) {
        this.pull[a] = b;
        this.refresh()
    },
    refresh: function (a) {
        a ? this.callEvent("onStoreUpdated", [a, this.pull[a], "update"]) : this.callEvent("onStoreUpdated", [null, null, null])
    },
    getRange: function (a, b) {
        if (arguments.length) {
            a = this.indexById(a);
            b = this.indexById(b);
            if (a > b) {
                var c = b;
                b = a;
                a = c
            }
        } else {
            a = this.min || 0;
            b = Math.min(this.max || Infinity, this.dataCount() - 1)
        }
        return this.getIndexRange(a, b)
    },
    getIndexRange: function (a, b) {
        b = Math.min(b, this.dataCount() - 1);
        var c = dhtmlx.toArray();
        for (a = a; a <= b; a++) c.push(this.get(this.order[a]));
        return c
    },
    dataCount: function () {
        return this.order.length
    },
    exists: function (a) {
        return !!this.pull[a]
    },
    move: function (a, b) {
        if (!(a < 0 || b < 0)) {
            var c = this.idByIndex(a),
                d = this.get(c);
            this.order.removeAt(a);
            this.order.insertAt(c, Math.min(this.order.length, b));
            this.callEvent("onStoreUpdated", [c, d, "move"])
        }
    },
    add: function (a, b) {
        var c = this.id(a),
            d = this.dataCount();
        if (dhtmlx.isNotDefined(b) || b < 0) b = d;
        if (b > d) b = Math.min(this.order.length, b);
        if (this.callEvent("onbeforeAdd", [c, b])) {
            if (this.exists(c)) return null;
            this.pull[c] = a;
            this.order.insertAt(c, b);
            if (this.m) {
                var e = this.m.length;
                if (!b && this.order.length) e = 0;
                this.m.insertAt(c, e)
            }
            this.callEvent("onafterAdd", [c, b]);
            this.callEvent("onStoreUpdated", [c, a, "add"]);
            return c
        }
    },
    remove: function (a) {
        if (a instanceof
        Array) for (var b = 0; b < a.length; b++) this.remove(a[b]);
        else if (this.callEvent("onbeforedelete", [a])) {
            if (!this.exists(a)) return null;
            b = this.get(a);
            this.order.remove(a);
            this.m && this.m.remove(a);
            delete this.pull[a];
            this.callEvent("onafterdelete", [a]);
            this.callEvent("onStoreUpdated", [a, b, "delete"])
        }
    },
    clearAll: function () {
        this.pull = {};
        this.order = dhtmlx.toArray();
        this.m = null;
        this.callEvent("onClearAll", []);
        this.refresh()
    },
    idByIndex: function (a) {
        return this.order[a]
    },
    indexById: function (a) {
        return a = this.order.find(a)
    },
    next: function (a, b) {
        return this.order[this.indexById(a) + (b || 1)]
    },
    first: function () {
        return this.order[0]
    },
    last: function () {
        return this.order[this.order.length - 1]
    },
    previous: function (a, b) {
        return this.order[this.indexById(a) - (b || 1)]
    },
    sort: function (a, b, c) {
        var d = a;
        if (typeof a == "function") d = {
            as: a,
            dir: b
        };
        else if (typeof a == "string") d = {
            by: a,
            dir: b,
            as: c
        };
        var e = [d.by, d.dir, d.as];
        if (this.callEvent("onbeforesort", e)) {
            if (this.order.length) {
                var f = dhtmlx.sort.create(d),
                    g = this.getRange(this.first(), this.last());
                g.sort(f);
                this.order = g.map(function (i) {
                    return this.id(i)
                }, this)
            }
            this.refresh();
            this.callEvent("onaftersort", e)
        }
    },
    filter: function (a, b) {
        if (this.m) {
            this.order = this.m;
            delete this.m
        }
        if (a) {
            var c = a;
            if (typeof a == "string") {
                a = dhtmlx.Template.setter(0, a);
                c = function (e, f) {
                    return a(e).toLowerCase().indexOf(f) != -1
                }
            }
            b = (b || "").toString().toLowerCase();
            var d = dhtmlx.toArray();
            this.order.each(function (e) {
                c(this.get(e), b) && d.push(e)
            }, this);
            this.m = this.order;
            this.order = d
        }
        this.refresh()
    },
    each: function (a, b) {
        for (var c = 0; c < this.order.length; c++) a.call(b || this, this.get(this.order[c]))
    },
    provideApi: function (a, b) {
        b && this.mapEvent({
            onbeforesort: a,
            onaftersort: a,
            onbeforeadd: a,
            onafteradd: a,
            onbeforedelete: a,
            onafterdelete: a
        });
        for (var c = ["sort", "add", "remove", "exists", "idByIndex", "indexById", "get", "set", "refresh", "dataCount", "filter", "next", "previous", "clearAll", "first", "last"], d = 0; d < c.length; d++) a[c[d]] = dhtmlx.methodPush(this, c[d])
    }
};
dhtmlx.sort = {
    create: function (a) {
        return dhtmlx.sort.dir(a.dir, dhtmlx.sort.by(a.by, a.as))
    },
    as: {
        "int": function (a, b) {
            a *= 1;
            b *= 1;
            return a > b ? 1 : a < b ? -1 : 0
        },
        string_strict: function (a, b) {
            a = a.toString();
            b = b.toString();
            return a > b ? 1 : a < b ? -1 : 0
        },
        string: function (a, b) {
            a = a.toString().toLowerCase();
            b = b.toString().toLowerCase();
            return a > b ? 1 : a < b ? -1 : 0
        }
    },
    by: function (a, b) {
        if (typeof b != "function") b = dhtmlx.sort.as[b || "string"];
        a = dhtmlx.Template.setter(0, a);
        return function (c, d) {
            return b(a(c), a(d))
        }
    },
    dir: function (a, b) {
        if (a == "asc") return b;
        return function (c, d) {
            return b(c, d) * -1
        }
    }
};
dhtmlx.Group = {
    k: function () {
        this.data.attachEvent("onStoreLoad", dhtmlx.bind(function () {
            this.e.group && this.group(this.e.group, false)
        }, this));
        this.attachEvent("onBeforeRender", dhtmlx.bind(function (a) {
            if (this.e.sort) {
                a.block();
                a.sort(this.e.sort);
                a.unblock()
            }
        }, this));
        this.attachEvent("onBeforeSort", dhtmlx.bind(function () {
            this.e.sort = null
        }, this))
    },
    Ja: function (a, b) {
        a.attachEvent("onClearAll", dhtmlx.bind(function () {
            this.ungroup(false)
        }, b))
    },
    sum: function (a, b) {
        a = dhtmlx.Template.setter(0, a);
        b = b || this.data;
        var c = 0;
        b.each(function (d) {
            c += a(d) * 1
        });
        return c
    },
    min: function (a, b) {
        a = dhtmlx.Template.setter(0, a);
        b = b || this.data;
        var c = Infinity;
        b.each(function (d) {
            if (a(d) * 1 < c) c = a(d) * 1
        });
        return c * 1
    },
    max: function (a, b) {
        a = dhtmlx.Template.setter(0, a);
        b = b || this.data;
        var c = -Infinity;
        b.each(function (d) {
            if (a(d) * 1 > c) c = a(d) * 1
        });
        return c
    },
    cb: function (a) {
        var b = function (j, k) {
                j = dhtmlx.Template.setter(0, j);
                return j(k[0])
            },
            c = dhtmlx.Template.setter(0, a.by);
        a.map[c] || (a.map[c] = [c, b]);
        var d = {},
            e = [];
        this.data.each(function (j) {
            var k = c(j);
            if (!d[k]) {
                e.push({
                    id: k
                });
                d[k] = dhtmlx.toArray()
            }
            d[k].push(j)
        });
        for (var f in a.map) {
            var g = a.map[f][1] || b;
            if (typeof g != "function") g = this[g];
            for (var i = 0; i < e.length; i++) e[i][f] = g.call(this, a.map[f][0], d[e[i].id])
        }
        this.ja = this.data;
        this.data = new dhtmlx.DataStore;
        this.data.provideApi(this, true);
        this.Ja(this.data, this);
        this.parse(e, "json")
    },
    group: function (a, b) {
        this.ungroup(false);
        this.cb(a);
        b !== false && this.render()
    },
    ungroup: function (a) {
        if (this.ja) {
            this.data = this.ja;
            this.data.provideApi(this, true)
        }
        a !== false && this.render()
    },
    group_setter: function (a, b) {
        return b
    },
    sort_setter: function (a, b) {
        if (typeof b != "object") b = {
            by: b
        };
        this.n(b, {
            as: "string",
            dir: "asc"
        });
        return b
    }
};
dhtmlx.KeyEvents = {
    k: function () {
        dhtmlx.event(this.g, "keypress", this.Ta, this)
    },
    Ta: function (a) {
        a = a || event;
        var b = a.which || a.keyCode;
        this.callEvent(this.hb ? "onEditKeyPress" : "onKeyPress", [b, a.ctrlKey, a.shiftKey, a])
    }
};
dhtmlx.MouseEvents = {
    k: function () {
        if (this.on_click) {
            dhtmlx.event(this.g, "click", this.Qa, this);
            dhtmlx.event(this.g, "contextmenu", this.Ra, this)
        }
        this.on_dblclick && dhtmlx.event(this.g, "dblclick", this.Sa, this);
        if (this.on_mouse_move) {
            dhtmlx.event(this.g, "mousemove", this.la, this);
            dhtmlx.event(this.g, dhtmlx.r ? "mouseleave" : "mouseout", this.la, this)
        }
    },
    Qa: function (a) {
        return this.R(a, this.on_click, "ItemClick")
    },
    Sa: function (a) {
        return this.R(a, this.on_dblclick, "ItemDblClick")
    },
    Ra: function (a) {
        var b = dhtmlx.html.locate(a, this.q);
        if (b && !this.callEvent("onBeforeContextMenu", [b, a])) return dhtmlx.html.preventEvent(a)
    },
    la: function (a) {
        if (dhtmlx.r) a = document.createEventObject(event);
        this.ia && window.clearTimeout(this.ia);
        this.callEvent("onMouseMoving", [a]);
        this.ia = window.setTimeout(dhtmlx.bind(function () {
            a.type == "mousemove" ? this.Ua(a) : this.Va(a)
        }, this), 500)
    },
    Ua: function (a) {
        this.R(a, this.on_mouse_move, "MouseMove") || this.callEvent("onMouseOut", [a || event])
    },
    Va: function (a) {
        this.callEvent("onMouseOut", [a || event])
    },
    R: function (a, b, c) {
        a = a || event;
        for (var d = a.target || a.srcElement, e = "", f = null, g = false; d && d.parentNode;) {
            if (!g && d.getAttribute) if (f = d.getAttribute(this.q)) {
                d.getAttribute("userdata") && this.callEvent("onLocateData", [f, d]);
                if (!this.callEvent("on" + c, [f, a, d])) return;
                g = true
            }
            if (e = d.className) {
                e = e.split(" ");
                e = e[0] || e[1];
                if (b[e]) return b[e].call(this, a, f, d)
            }
            d = d.parentNode
        }
        return g
    }
};
dhtmlx.Settings = {
    k: function () {
        this.e = this.config = {}
    },
    define: function (a, b) {
        if (typeof a == "object") return this.ma(a);
        return this.Y(a, b)
    },
    Y: function (a, b) {
        var c = this[a + "_setter"];
        return this.e[a] = c ? c.call(this, a, b) : b
    },
    ma: function (a) {
        if (a) for (var b in a) this.Y(b, a[b])
    },
    B: function (a, b) {
        var c = dhtmlx.extend({}, b);
        typeof a == "object" && !a.tagName && dhtmlx.extend(c, a);
        this.ma(c)
    },
    n: function (a, b) {
        for (var c in b) switch (typeof a[c]) {
        case "object":
            a[c] = this.n(a[c] || {}, b[c]);
            break;
        case "undefined":
            a[c] = b[c];
            break;
        default:
            break
        }
        return a
    },
    Xa: function (a, b, c) {
        if (typeof a == "object" && !a.tagName) a = a.container;
        this.g = dhtmlx.toNode(a);
        if (!this.g && c) this.g = c(a);
        this.g.className += " " + b;
        this.g.onselectstart = function () {
            return false
        };
        this.L = this.g
    },
    ab: function (a) {
        if (typeof a == "object") return this.type_setter("type", a);
        this.type = dhtmlx.extend({}, this.types[a]);
        this.customize()
    },
    customize: function (a) {
        a && dhtmlx.extend(this.type, a);
        this.type.Oa = dhtmlx.Template.fromHTML(this.template_item_start(this.type));
        this.type.Na = this.template_item_end(this.type);
        this.render()
    },
    type_setter: function (a, b) {
        this.ab(typeof b == "object" ? dhtmlx.Type.add(this, b) : b);
        return b
    },
    template_setter: function (a, b) {
        return this.type_setter("type", {
            template: b
        })
    },
    css_setter: function (a, b) {
        this.g.className += " " + b;
        return b
    }
};
dhtmlx.compat = function (a, b) {
    dhtmlx.compat[a] && dhtmlx.compat[a](b)
};
(function () {
    if (!window.dhtmlxError) {
        var a = function () {};
        window.dhtmlxError = {
            catchError: a,
            throwError: a
        };
        window.convertStringToBoolean = function (c) {
            return !!c
        };
        window.dhtmlxEventable = function (c) {
            dhtmlx.extend(c, dhtmlx.EventSystem)
        };
        var b = {
            getXMLTopNode: function () {},
            doXPath: function (c) {
                return dhtmlx.DataDriver.xml.xpath(this.xml, c)
            },
            xmlDoc: {
                responseXML: true
            }
        };
        dhtmlx.compat.dataProcessor = function (c) {
            var d = "_sendData",
                e = "_in_progress",
                f = "_tMode",
                g = "_waitMode";
            c[d] = function (i, j) {
                if (i) {
                    if (j) this[e][j] = (new Date).valueOf();
                    if (!this.callEvent("onBeforeDataSending", j ? [j, this.getState(j)] : [])) return false;
                    var k = this,
                        h = this.serverProcessor;
                    this[f] != "POST" ? dhtmlx.ajax().get(h + (h.indexOf("?") != -1 ? "&" : "?") + this.serialize(i, j), "", function (m, l) {
                        b.xml = dhtmlx.DataDriver.xml.checkResponse(m, l);
                        k.afterUpdate(k, null, null, null, b)
                    }) : dhtmlx.ajax().post(h, this.serialize(i, j), function (m, l) {
                        b.xml = dhtmlx.DataDriver.xml.checkResponse(m, l);
                        k.afterUpdate(k, null, null, null, b)
                    });
                    this[g]++
                }
            }
        }
    }
})();
if (!dhtmlx.attaches) dhtmlx.attaches = {};
dhtmlx.attaches.attachAbstract = function (a, b) {
    var c = document.createElement("DIV");
    c.id = "CustomObject_" + dhtmlx.uid();
    c.style.width = "100%";
    c.style.height = "100%";
    c.cmp = "grid";
    document.body.appendChild(c);
    this.attachObject(c.id);
    b.container = c.id;
    var d = this.vs[this.av];
    d.grid = new window[a](b);
    d.gridId = c.id;
    d.gridObj = c;
    d.grid.setSizes = function () {
        this.resize ? this.resize() : this.render()
    };
    var e = "_viewRestore";
    return this.vs[this[e]()].grid
};
dhtmlx.attaches.attachDataView = function (a) {
    return this.attachAbstract("dhtmlXDataView", a)
};
dhtmlx.attaches.attachChart = function (a) {
    return this.attachAbstract("dhtmlXChart", a)
};
dhtmlx.compat.layout = function () {};
dhtmlx.ajax = function (a, b, c) {
    if (arguments.length !== 0) {
        var d = new dhtmlx.ajax;
        if (c) d.master = c;
        d.get(a, null, b)
    }
    if (!this.getXHR) return new dhtmlx.ajax;
    return this
};
dhtmlx.ajax.prototype = {
    getXHR: function () {
        return dhtmlx.r ? new ActiveXObject("Microsoft.xmlHTTP") : new XMLHttpRequest
    },
    send: function (a, b, c) {
        var d = this.getXHR();
        if (typeof c == "function") c = [c];
        if (typeof b == "object") {
            var e = [];
            for (var f in b) e.push(f + "=" + encodeURIComponent(b[f]));
            b = e.join("&")
        }
        if (b && !this.post) {
            a = a + (a.indexOf("?") != -1 ? "&" : "?") + b;
            b = null
        }
        d.open(this.post ? "POST" : "GET", a, !this.pa);
        this.post && d.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
        if (!this.pa) {
            var g = this;
            d.onreadystatechange = function () {
                if (!d.readyState || d.readyState == 4) {
                    if (c && g) for (var i = 0; i < c.length; i++) if (c[i]) c[i].call(g.master || g, d.responseText, d.responseXML, d);
                    c = d = g = g.master = null
                }
            }
        }
        d.send(b || null);
        return d
    },
    get: function (a, b, c) {
        this.post = false;
        return this.send(a, b, c)
    },
    post: function (a, b, c) {
        this.post = true;
        return this.send(a, b, c)
    },
    sync: function () {
        this.pa = true;
        return this
    }
};
dhtmlx.DataLoader = {
    k: function () {
        this.data = new dhtmlx.DataStore
    },
    load: function (a, b, c) {
        this.callEvent("onXLS", []);
        if (typeof b == "string") {
            this.data.setDriver(b);
            b = c
        }
        if (!this.data.feed) this.data.feed = function (d, e) {
            if (this.F) return this.F = [d, e];
            else this.F = true;
            this.load(a + (a.indexOf("?") == -1 ? "?" : "&") + "posStart=" + d + "&count=" + e, function () {
                var f = this.F;
                this.F = false;
                typeof f == "object" && this.data.feed.apply(this, f)
            })
        };
        dhtmlx.ajax(a, [this.ka, b], this)
    },
    parse: function (a, b) {
        this.callEvent("onXLS", []);
        b && this.data.setDriver(b);
        this.ka(a, null)
    },
    ka: function (a, b) {
        this.data.Wa(this.data.driver.toObject(a, b));
        this.callEvent("onXLE", [])
    }
};
dhtmlx.DataDriver = {};
dhtmlx.DataDriver.json = {
    toObject: function (a) {
        if (typeof a == "string") {
            eval("dhtmlx.temp=" + a);
            return dhtmlx.temp
        }
        return a
    },
    getRecords: function (a) {
        if (a && !(a instanceof Array)) return [a];
        return a
    },
    getDetails: function (a) {
        return a
    },
    getInfo: function (a) {
        return {
            w: a.total_count || 0,
            u: a.pos || 0
        }
    }
};
dhtmlx.DataDriver.html = {
    toObject: function (a) {
        if (typeof a == "string") {
            var b = null;
            if (a.indexOf("<") == -1) b = dhtmlx.toNode(a);
            if (!b) {
                b = document.createElement("DIV");
                b.innerHTML = a
            }
            return b.getElementsByTagName(this.tag)
        }
        return a
    },
    getRecords: function (a) {
        if (a.tagName) return a.childNodes;
        return a
    },
    getDetails: function (a) {
        return dhtmlx.DataDriver.xml.tagToObject(a)
    },
    getInfo: function () {
        return {
            w: 0,
            u: 0
        }
    },
    tag: "LI"
};
dhtmlx.DataDriver.jsarray = {
    toObject: function (a) {
        if (typeof a == "string") {
            eval("dhtmlx.temp=" + a);
            return dhtmlx.temp
        }
        return a
    },
    getRecords: function (a) {
        return a
    },
    getDetails: function (a) {
        for (var b = {}, c = 0; c < a.length; c++) b["data" + c] = a[c];
        return b
    },
    getInfo: function () {
        return {
            w: 0,
            u: 0
        }
    }
};
dhtmlx.DataDriver.csv = {
    toObject: function (a) {
        return a
    },
    getRecords: function (a) {
        return a.split(this.row)
    },
    getDetails: function (a) {
        a = this.stringToArray(a);
        for (var b = {}, c = 0; c < a.length; c++) b["data" + c] = a[c];
        return b
    },
    getInfo: function () {
        return {
            w: 0,
            u: 0
        }
    },
    stringToArray: function (a) {
        a = a.split(this.cell);
        for (var b = 0; b < a.length; b++) a[b] = a[b].replace(/^[ \t\n\r]*(\"|)/g, "").replace(/(\"|)[ \t\n\r]*$/g, "");
        return a
    },
    row: "\n",
    cell: ","
};
dhtmlx.DataDriver.xml = {
    toObject: function (a, b) {
        if (b && (b = this.checkResponse(a, b))) return b;
        if (typeof a == "string") return this.fromString(a);
        return a
    },
    getRecords: function (a) {
        return this.xpath(a, this.records)
    },
    records: "/*/item",
    userdata: "/*/userdata",
    getDetails: function (a) {
        return this.tagToObject(a, {})
    },
    getUserData: function (a, b) {
        b = b || {};
        var c = this.xpath(a, this.userdata);
        for (a = 0; a < c.length; a++) {
            var d = this.tagToObject(c[a]);
            b[d.name] = d.value
        }
        return b
    },
    getInfo: function (a) {
        return {
            w: a.documentElement.getAttribute("total_count") || 0,
            u: a.documentElement.getAttribute("pos") || 0
        }
    },
    xpath: function (a, b) {
        if (window.XPathResult) {
            var c = a;
            if (a.nodeName.indexOf("document") == -1) a = a.ownerDocument;
            var d = [];
            a = a.evaluate(b, c, null, XPathResult.ANY_TYPE, null);
            for (b = a.iterateNext(); b;) {
                d.push(b);
                b = a.iterateNext()
            }
            return d
        }
        return a.selectNodes(b)
    },
    tagToObject: function (a, b) {
        b = b || {};
        for (var c = a.attributes, d = 0; d < c.length; d++) b[c[d].name] = c[d].value;
        var e = false,
            f = a.childNodes;
        for (d = 0; d < f.length; d++) if (f[d].nodeType == 1) {
            var g = f[d].tagName;
            if (typeof b[g] != "undefined") {
                b[g] instanceof Array || (b[g] = [b[g]]);
                b[g].push(this.tagToObject(f[d], {}))
            } else b[f[d].tagName] = this.tagToObject(f[d], {});
            e = true
        }
        if (!c.length && !e) return this.nodeValue(a);
        b.value = this.nodeValue(a);
        return b
    },
    nodeValue: function (a) {
        if (a.firstChild) return a.firstChild.data;
        return ""
    },
    fromString: function (a) {
        if (window.DOMParser) return (new DOMParser).parseFromString(a, "text/xml");
        if (window.ActiveXObject) {
            temp = new ActiveXObject("Microsoft.xmlDOM");
            temp.loadXML(a);
            return temp
        }
    },
    checkResponse: function (a, b) {
        if (b && b.firstChild && b.firstChild.tagName != "parsererror") return b;
        if (a = this.from_string(a.responseText.replace(/^[\s]+/, ""))) return a
    }
};
dhtmlx.DataDriver.dhtmlxgrid = {
    Ia: "_get_cell_value",
    toObject: function (a) {
        return this.ea = a
    },
    getRecords: function (a) {
        return a.rowsBuffer
    },
    getDetails: function (a) {
        for (var b = {}, c = 0; c < this.ea.getColumnsNum(); c++) b["data" + c] = this.ea[this.Ia](a, c);
        return b
    },
    getInfo: function () {
        return {
            w: 0,
            u: 0
        }
    }
};
dhtmlx.Canvas = {
    k: function () {
        this.D = []
    },
    Ya: function (a) {
        this.l = dhtmlx.html.create("canvas", {
            width: a.offsetWidth,
            height: a.offsetHeight
        });
        a.appendChild(this.l);
        if (!this.l.getContext) if (dhtmlx.r) {
            G_vmlCanvasManager.init_(document);
            G_vmlCanvasManager.initElement(this.l)
        }
        return this.l
    },
    getCanvas: function (a) {
        return (this.l || this.Ya(this.g)).getContext(a || "2d")
    },
    $a: function () {
        if (this.l) {
            this.l.setAttribute("width", this.l.parentNode.offsetWidth);
            this.l.setAttribute("height", this.l.parentNode.offsetHeight)
        }
    },
    renderText: function (a, b, c, d, e) {
        if (c) {
            a = dhtmlx.html.create("DIV", {
                "class": "dhx_canvas_text" + (d ? " " + d : ""),
                style: "left:" + a + "px; top:" + b + "px;"
            }, c);
            this.g.appendChild(a);
            this.D.push(a);
            if (e) a.style.width = e + "px";
            return a
        }
    },
    renderTextAt: function (a, b, c, d, e, f, g) {
        if (e = this.renderText.call(this, c, d, e, f, g)) {
            if (a) e.style.top = a == "middle" ? parseInt(d - e.offsetHeight / 2, 10) + "px" : d - e.offsetHeight + "px";
            if (b) e.style.left = b == "left" ? c - e.offsetWidth + "px" : parseInt(c - e.offsetWidth / 2, 10) + "px"
        }
        return e
    },
    clearCanvas: function () {
        for (var a = 0; a < this.D.length; a++) this.g.removeChild(this.D[a]);
        this.D = [];
        if (this.g.v) {
            this.g.v.parentNode.removeChild(this.g.v);
            this.g.v = null
        }
        this.getCanvas().clearRect(0, 0, this.l.offsetWidth, this.l.offsetHeight)
    }
};
dhtmlXChart = function (a) {
    this.name = "Chart";
    this.version = "3.0";
    dhtmlx.extend(this, dhtmlx.Settings);
    this.Xa(a, "dhx_chart");
    dhtmlx.extend(this, dhtmlx.DataLoader);
    this.data.provideApi(this, true);
    dhtmlx.extend(this, dhtmlx.EventSystem);
    dhtmlx.extend(this, dhtmlx.MouseEvents);
    dhtmlx.extend(this, dhtmlx.Destruction);
    dhtmlx.extend(this, dhtmlx.Canvas);
    dhtmlx.extend(this, dhtmlx.Group);
    dhtmlx.extend(this, dhtmlx.AutoTooltip);
    for (var b in dhtmlx.chart) dhtmlx.extend(this, dhtmlx.chart[b]);
    this.B(a, {
        color: "RAINBOW",
        alpha: "1",
        label: false,
        value: "{obj.value}",
        padding: {},
        view: "pie",
        lineColor: "#ffffff",
        cant: 0.5,
        width: 15,
        labelWidth: 100,
        line: {},
        item: {},
        shadow: true,
        gradient: false,
        border: true,
        labelOffset: 20,
        origin: "auto"
    });
    this.h = [this.e];
    this.data.attachEvent("onStoreUpdated", dhtmlx.bind(function () {
        this.render()
    }, this));
    this.attachEvent("onLocateData", this.db)
};
dhtmlXChart.prototype = {
    q: "dhx_area_id",
    on_click: {},
    on_dblclick: {},
    on_mouse_move: {},
    resize: function () {
        this.$a();
        this.render()
    },
    view_setter: function (a, b) {
        if (typeof this.e.offset == "undefined") this.e.offset = b == "area" || b == "stackedArea" ? false : true;
        return b
    },
    render: function () {
        if (this.callEvent("onBeforeRender", [this.data])) {
            this.clearCanvas();
            this.e.legend && this.za(this.getCanvas(), this.data.getRange(), this.g.offsetWidth, this.g.offsetHeight);
            for (var a = this.Ea(this.g.offsetWidth, this.g.offsetHeight), b = new dhtmlx.ui.Map(this.q), c = this.e, d = 0; d < this.h.length; d++) {
                this.e = this.h[d];
                this["pvt_render_" + this.e.view](this.getCanvas(), this.data.getRange(), a.start, a.end, d, b)
            }
            b.render(this.g);
            this.e = c
        }
    },
    value_setter: dhtmlx.Template.obj_setter,
    alpha_setter: dhtmlx.Template.obj_setter,
    label_setter: dhtmlx.Template.obj_setter,
    lineColor_setter: dhtmlx.Template.obj_setter,
    pieInnerText_setter: dhtmlx.Template.obj_setter,
    gradient_setter: function (a, b) {
        if (typeof b != "function" && b && (b === true || b != "3d")) b = "light";
        return b
    },
    colormap: {
        RAINBOW: function (a) {
            a = Math.floor(this.indexById(a.id) / this.dataCount() * 1536);
            if (a == 1536) a -= 1;
            return this.Za[Math.floor(a / 256)](a % 256)
        }
    },
    color_setter: function (a, b) {
        return this.colormap[b] || dhtmlx.Template.obj_setter(a, b)
    },
    legend_setter: function (a, b) {
        if (typeof b != "object") b = {
            template: b
        };
        this.n(b, {
            width: 150,
            height: 18,
            layout: "y",
            align: "left",
            valign: "bottom",
            template: "",
            marker: {
                type: "square",
                width: 25,
                height: 15
            }
        });
        b.template = dhtmlx.Template.setter(0, b.template);
        return b
    },
    item_setter: function (a, b) {
        if (typeof b != "object") b = {
            color: b,
            borderColor: b
        };
        this.n(b, {
            radius: 4,
            color: "#000000",
            borderColor: "#000000",
            borderWidth: 2
        });
        b.color = dhtmlx.Template.setter(0, b.color);
        b.borderColor = dhtmlx.Template.setter(0, b.borderColor);
        return b
    },
    line_setter: function (a, b) {
        if (typeof b != "object") b = {
            color: b
        };
        this.n(b, {
            width: 3,
            color: "#d4d4d4"
        });
        b.color = dhtmlx.Template.setter(0, b.color);
        return b
    },
    padding_setter: function (a, b) {
        if (typeof b != "object") b = {
            left: b,
            right: b,
            top: b,
            bottom: b
        };
        this.n(b, {
            left: 50,
            right: 20,
            top: 35,
            bottom: 40
        });
        return b
    },
    xAxis_setter: function (a, b) {
        if (!b) return false;
        if (typeof b != "object") b = {
            template: b
        };
        this.n(b, {
            title: "",
            color: "#000000",
            template: "{obj}",
            lines: false
        });
        if (b.template) b.template = dhtmlx.Template.setter(0, b.template);
        return b
    },
    yAxis_setter: function (a, b) {
        this.n(b, {
            title: "",
            color: "#000000",
            template: "{obj}",
            lines: true
        });
        if (b.template) b.template = dhtmlx.Template.setter(0, b.template);
        return b
    },
    N: function (a, b, c, d, e, f, g) {
        e = this.Da(a, b, c, d, e, f);
        this.da(a, b, c, d, g, e);
        return e
    },
    da: function (a, b, c, d, e, f) {
        if (this.e.xAxis) {
            var g = c.x - 0.5;
            f = parseInt(f ? f : d.y, 10) + 0.5;
            var i = d.x,
                j, k = true;
            this.i(a, g, f, i, f, this.e.xAxis.color, 1);
            for (var h = 0; h < b.length; h++) {
                if (this.e.offset === true) j = g + e / 2 + h * e;
                else {
                    j = g + h * e;
                    k = !! h
                }
                var m = this.e.origin != "auto" && this.e.view == "bar" && parseFloat(this.e.value(b[h])) < this.e.origin;
                this.Ba(j, f, b[h], k, m);
                this.e.view_setter != "bar" && this.Ca(a, j, d.y, c.y)
            }
            this.renderTextAt(true, false, g, d.y + this.e.padding.bottom - 3, this.e.xAxis.title, "dhx_axis_title_x", d.x - c.x);
            this.e.xAxis.lines && this.e.offset && this.i(a, i + 0.5, d.y, i + 0.5, c.y + 0.5, this.e.xAxis.color, 0.2)
        }
    },
    Da: function (a, b, c, d, e, f) {
        var g;
        b = {};
        if (this.e.yAxis) {
            var i = c.x - 0.5,
                j = d.y,
                k = c.y,
                h = d.y;
            this.i(a, i, j, i, k, this.e.yAxis.color, 1);
            if (this.e.yAxis.step) g = parseFloat(this.e.yAxis.step);
            if (typeof this.e.yAxis.step == "undefined" || typeof this.e.yAxis.start == "undefined" || typeof this.e.yAxis.end == "undefined") {
                b = this.V(e, f);
                e = b.start;
                f = b.end;
                g = b.step;
                this.e.yAxis.end = f;
                this.e.yAxis.start = e
            }
            if (g !== 0) {
                k = (j - k) * g / (f - e);
                for (var m = 0, l = e; l <= f; l += g) {
                    if (b.fixNum) l = parseFloat((new Number(l)).toFixed(b.fixNum));
                    var n = Math.floor(j - m * k) + 0.5;
                    !(l == e && this.e.origin == "auto") && this.e.yAxis.lines && this.i(a, i, n, d.x, n, this.e.yAxis.color, 0.2);
                    if (l == this.e.origin) h = n;
                    this.renderText(0, n - 5, this.e.yAxis.template(l.toString()), "dhx_axis_item_y", c.x - 5);
                    m++
                }
                this.oa(c, d);
                return h
            }
        }
    },
    oa: function (a, b) {
        if (a = this.renderTextAt("middle", false, 0, parseInt((b.y - a.y) / 2 + a.y, 10), this.e.yAxis.title, "dhx_axis_title_y")) a.style.left = (dhtmlx.env.transform ? (a.offsetHeight - a.offsetWidth) / 2 : 0) + "px"
    },
    V: function (a, b) {
        if (this.e.origin != "auto" && this.e.origin < a) a = this.e.origin;
        var c, d, e;
        c = (b - a) / 8 || 1;
        var f = Math.floor(this.ga(c)),
            g = Math.pow(10, f),
            i = c / g;
        i = i > 5 ? 10 : 5;
        c = parseInt(i, 10) * g;
        if (c > Math.abs(a)) d = a < 0 ? -c : 0;
        else {
            var j = Math.abs(a),
                k = Math.floor(this.ga(j)),
                h = j / Math.pow(10, k);
            d = Math.ceil(h * 10) / 10 * Math.pow(10, k) - c;
            if (a < 0) d = -d - 2 * c
        }
        for (e = d; e < b;) {
            e += c;
            e = parseFloat((new Number(e)).toFixed(Math.abs(f)))
        }
        return {
            start: d,
            end: e,
            step: c,
            fixNum: Math.abs(f)
        }
    },
    O: function (a) {
        var b, c;
        if ((c = arguments.length && a == "h" ? this.e.xAxis : this.e.yAxis) && typeof c.end != "undefied" && typeof c.start != "undefied" && c.step) {
            b = parseFloat(c.end);
            c = parseFloat(c.start)
        } else {
            b = this.max(this.h[0].value);
            c = this.min(this.h[0].value);
            if (this.h.length > 1) for (var d = 1; d < this.h.length; d++) {
                var e = this.max(this.h[d].value),
                    f = this.min(this.h[d].value);
                if (e > b) b = e;
                if (f < c) c = f
            }
        }
        return {
            max: b,
            min: c
        }
    },
    ga: function (a) {
        var b = "log";
        return Math.floor(Math[b](a) / Math.LN10)
    },
    Ba: function (a, b, c, d, e) {
        var to = offset = 11,from = 0,
            val =  this.e.xAxis.template(c);
        while(1){
            this.e.xAxis && this.renderTextAt(e, d, a+from, b+from, val.slice(from,to), "dhx_axis_item_x");
            if(to > val.length){break;}
            from += offset;to += offset;
        }
    },
    Ca: function (a, b, c, d) {
        this.e.xAxis && this.e.xAxis.lines && this.i(a, b, c, b, d, this.e.xAxis.color, 0.2)
    },
    i: function (a, b, c, d, e, f, g) {
        a.strokeStyle = f;
        a.lineWidth = g;
        a.beginPath();
        a.moveTo(b, c);
        a.lineTo(d, e);
        a.stroke()
    },
    z: function (a, b) {
        var c = 1;
        if (b != a) {
            a = b - a;
            if (Math.abs(a) < 1) for (; Math.abs(a) < 1;) {
                c *= 10;
                a *= c
            }
        } else a = a;
        return [a, c]
    },
    Za: [function (a) {
        return "#FF" + dhtmlx.math.toHex(a / 2, 2) + "00"
    }, function (a) {
        return "#FF" + dhtmlx.math.toHex(a / 2 + 128, 2) + "00"
    }, function (a) {
        return "#" + dhtmlx.math.toHex(255 - a, 2) + "FF00"
    }, function (a) {
        return "#00FF" + dhtmlx.math.toHex(a, 2)
    }, function (a) {
        return "#00" + dhtmlx.math.toHex(255 - a, 2) + "FF"
    }, function (a) {
        return "#" + dhtmlx.math.toHex(a, 2) + "00FF"
    }],
    addSeries: function (a) {
        var b = this.e;
        this.e = dhtmlx.extend({}, b);
        this.B(a, {});
        this.h.push(this.e);
        this.e = b
    },
    db: function (a, b) {
        this.ra = b.getAttribute("userdata");
        for (a = 0; a < this.h.length; a++) {
            var c = this.h[a].tooltip;
            c && c.disable()
        }(c = this.h[this.ra].tooltip) && c.enable()
    },
    za: function (a, b) {
        var c = 0,
            d = 0,
            e = this.e.legend,
            f, g, i = this.e.legend.layout != "x" ? "width:" + e.width + "px" : "",
            j = dhtmlx.html.create("DIV", {
                "class": "dhx_chart_legend",
                style: "left:" + c + "px; top:" + d + "px;" + i
            }, "");
        this.g.appendChild(j);
        var k = [];
        if (e.values) for (h = 0; h < e.values.length; h++) k.push(this.aa(j, e.values[h].text));
        else for (var h = 0; h < b.length; h++) k.push(this.aa(j, e.template(b[h])));
        g = j.offsetWidth;
        f = j.offsetHeight;
        this.e.legend.width = g;
        this.e.legend.height = f;
        if (g < this.g.offsetWidth) {
            if (e.layout == "x" && e.align == "center") c = (this.g.offsetWidth - g) / 2;
            if (e.align == "right") c = this.g.offsetWidth - g
        }
        if (f < this.g.offsetHeight) if (e.valign == "middle" && e.align != "center" && e.layout != "x") d = (this.g.offsetHeight - f) / 2;
        else if (e.valign == "bottom") d = this.g.offsetHeight - f;
        j.style.left = c + "px";
        j.style.top = d + "px";
        for (h = 0; h < k.length; h++) {
            var m = k[h],
                l = e.values ? e.values[h].color : this.e.color.call(this, b[h]);
            this.Aa(a, m.offsetLeft + c, m.offsetTop + d, l)
        }
        k = null
    },
    aa: function (a, b) {
        var c = "";
        if (this.e.legend.layout == "x") c = "float:left;";
        b = dhtmlx.html.create("DIV", {
            style: c + "padding-left:" + (10 + this.e.legend.marker.width) + "px",
            "class": "dhx_chart_legend_item"
        }, b);
        a.appendChild(b);
        return b
    },
    Aa: function (a, b, c, d) {
        var e = this.e.legend;
        a.strokeStyle = a.fillStyle = d;
        a.lineWidth = e.marker.height;
        a.lineCap = e.marker.type;
        a.beginPath();
        b += a.lineWidth / 2 + 5;
        c += a.lineWidth / 2 + 3;
        a.moveTo(b, c);
        b = b + e.marker.width - e.marker.height + 1;
        a.lineTo(b, c);
        a.stroke()
    },
    Ea: function (a, b) {
        var c, d, e, f;
        c = this.e.padding.left;
        d = this.e.padding.top;
        e = a - this.e.padding.right;
        f = b - this.e.padding.bottom;
        if (this.e.legend) {
            a = this.e.legend;
            b = this.e.legend.width;
            var g = this.e.legend.height;
            if (a.layout == "x") if (a.valign == "center") if (a.align == "right") e -= b;
            else {
                if (a.align == "left") c += b
            } else if (a.valign == "bottom") f -= g;
            else d += g;
            else if (a.align == "right") e -= b;
            else if (a.align == "left") c += b
        }
        return {
            start: {
                x: c,
                y: d
            },
            end: {
                x: e,
                y: f
            }
        }
    },
    Q: function (a) {
        var b, c;
        if (this.e.yAxis && typeof this.e.yAxis.end != "undefied" && typeof this.e.yAxis.start != "undefied" && this.e.yAxis.step) {
            b = parseFloat(this.e.yAxis.end);
            c = parseFloat(this.e.yAxis.start)
        } else {
            for (var d = 0; d < a.length; d++) {
                a[d].$sum = 0;
                a[d].$min = Infinity;
                for (b = 0; b < this.h.length; b++) {
                    c = parseFloat(this.h[b].value(a[d]));
                    if (!isNaN(c)) {
                        a[d].$sum += c;
                        if (c < a[d].$min) a[d].$min = c
                    }
                }
            }
            b = -Infinity;
            c = Infinity;
            for (d = 0; d < a.length; d++) {
                if (a[d].$sum > b) b = a[d].$sum;
                if (a[d].$min < c) c = a[d].$min
            }
            if (c > 0) c = 0
        }
        return {
            max: b,
            min: c
        }
    },
    G: function (a, b, c, d, e, f, g, i) {
        if (f == "light") {
            a = i == "x" ? a.createLinearGradient(b, c, d, c) : a.createLinearGradient(b, c, b, e);
            a.addColorStop(0, "#FFFFFF");
            a.addColorStop(0.9, g);
            a.addColorStop(1, g);
            g = 2
        } else {
            a.globalAlpha = 0.37;
            g = 0;
            a = i == "x" ? a.createLinearGradient(b, e, b, c) : a.createLinearGradient(b, c, d, c);
            a.addColorStop(0, "#000000");
            a.addColorStop(0.5, "#FFFFFF");
            a.addColorStop(0.6, "#FFFFFF");
            a.addColorStop(1, "#000000")
        }
        return {
            gradient: a,
            offset: g
        }
    }
};
dhtmlx.compat("layout");