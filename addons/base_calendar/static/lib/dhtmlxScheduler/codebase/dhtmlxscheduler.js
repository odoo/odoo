/*
dhtmlxScheduler v.2.3

This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details

(c) DHTMLX Ltd.
*/
dhtmlx = function (B) {
    for (var A in B) {
        dhtmlx[A] = B[A]
    }
    return dhtmlx
};
dhtmlx.extend_api = function (A, D, C) {
    var B = window[A];
    if (!B) {
        return
    }
    window[A] = function (G) {
        if (G && typeof G == "object" && !G.tagName && !(G instanceof Array)) {
            var F = B.apply(this, (D._init ? D._init(G) : arguments));
            for (var E in dhtmlx) {
                if (D[E]) {
                    this[D[E]](dhtmlx[E])
                }
            }
            for (var E in G) {
                if (D[E]) {
                    this[D[E]](G[E])
                } else {
                    if (E.indexOf("on") == 0) {
                        this.attachEvent(E, G[E])
                    }
                }
            }
        } else {
            var F = B.apply(this, arguments)
        }
        if (D._patch) {
            D._patch(this)
        }
        return F || this
    };
    window[A].prototype = B.prototype;
    if (C) {
        dhtmlXHeir(window[A].prototype, C)
    }
};
dhtmlxAjax = {
    get: function (A, C) {
        var B = new dtmlXMLLoaderObject(true);
        B.async = (arguments.length < 3);
        B.waitCall = C;
        B.loadXML(A);
        return B
    },
    post: function (A, C, D) {
        var B = new dtmlXMLLoaderObject(true);
        B.async = (arguments.length < 4);
        B.waitCall = D;
        B.loadXML(A, true, C);
        return B
    },
    getSync: function (A) {
        return this.get(A, null, true)
    },
    postSync: function (A, B) {
        return this.post(A, B, null, true)
    }
};

function dtmlXMLLoaderObject(B, D, C, A) {
    this.xmlDoc = "";
    if (typeof(C) != "undefined") {
        this.async = C
    } else {
        this.async = true
    }
    this.onloadAction = B || null;
    this.mainObject = D || null;
    this.waitCall = null;
    this.rSeed = A || false;
    return this
}
dtmlXMLLoaderObject.prototype.waitLoadFunction = function (B) {
    var A = true;
    this.check = function () {
        if ((B) && (B.onloadAction != null)) {
            if ((!B.xmlDoc.readyState) || (B.xmlDoc.readyState == 4)) {
                if (!A) {
                    return
                }
                A = false;
                if (typeof B.onloadAction == "function") {
                    B.onloadAction(B.mainObject, null, null, null, B)
                }
                if (B.waitCall) {
                    B.waitCall.call(this, B);
                    B.waitCall = null
                }
            }
        }
    };
    return this.check
};
dtmlXMLLoaderObject.prototype.getXMLTopNode = function (C, A) {
    if (this.xmlDoc.responseXML) {
        var B = this.xmlDoc.responseXML.getElementsByTagName(C);
        if (B.length == 0 && C.indexOf(":") != -1) {
            var B = this.xmlDoc.responseXML.getElementsByTagName((C.split(":"))[1])
        }
        var E = B[0]
    } else {
        var E = this.xmlDoc.documentElement
    }
    if (E) {
        this._retry = false;
        return E
    }
    if ((_isIE) && (!this._retry)) {
        var D = this.xmlDoc.responseText;
        var A = this.xmlDoc;
        this._retry = true;
        this.xmlDoc = new ActiveXObject("Microsoft.XMLDOM");
        this.xmlDoc.async = false;
        this.xmlDoc.loadXML(D);
        return this.getXMLTopNode(C, A)
    }
    dhtmlxError.throwError("LoadXML", "Incorrect XML", [(A || this.xmlDoc), this.mainObject]);
    return document.createElement("DIV")
};
dtmlXMLLoaderObject.prototype.loadXMLString = function (B) {
    try {
        var C = new DOMParser();
        this.xmlDoc = C.parseFromString(B, "text/xml")
    } catch (A) {
        this.xmlDoc = new ActiveXObject("Microsoft.XMLDOM");
        this.xmlDoc.async = this.async;
        this.xmlDoc.loadXML(B)
    }
    this.onloadAction(this.mainObject, null, null, null, this);
    if (this.waitCall) {
        this.waitCall();
        this.waitCall = null
    }
};
dtmlXMLLoaderObject.prototype.loadXML = function (C, B, A, D) {
    if (this.rSeed) {
        C += ((C.indexOf("?") != -1) ? "&" : "?") + "a_dhx_rSeed=" + (new Date()).valueOf()
    }
    this.filePath = C;
    if ((!_isIE) && (window.XMLHttpRequest)) {
        this.xmlDoc = new XMLHttpRequest()
    } else {
        this.xmlDoc = new ActiveXObject("Microsoft.XMLHTTP")
    }
    if (this.async) {
        this.xmlDoc.onreadystatechange = new this.waitLoadFunction(this)
    }
    this.xmlDoc.open(B ? "POST" : "GET", C, this.async);
    if (D) {
        this.xmlDoc.setRequestHeader("User-Agent", "dhtmlxRPC v0.1 (" + navigator.userAgent + ")");
        this.xmlDoc.setRequestHeader("Content-type", "text/xml")
    } else {
        if (B) {
            this.xmlDoc.setRequestHeader("Content-type", "application/x-www-form-urlencoded")
        }
    }
    this.xmlDoc.setRequestHeader("X-Requested-With", "XMLHttpRequest");
    this.xmlDoc.send(null || A);
    if (!this.async) {
        (new this.waitLoadFunction(this))()
    }
};
dtmlXMLLoaderObject.prototype.destructor = function () {
    this.onloadAction = null;
    this.mainObject = null;
    this.xmlDoc = null;
    return null
};
dtmlXMLLoaderObject.prototype.xmlNodeToJSON = function (D) {
    var C = {};
    for (var B = 0; B < D.attributes.length; B++) {
        C[D.attributes[B].name] = D.attributes[B].value
    }
    C._tagvalue = D.firstChild ? D.firstChild.nodeValue : "";
    for (var B = 0; B < D.childNodes.length; B++) {
        var A = D.childNodes[B].tagName;
        if (A) {
            if (!C[A]) {
                C[A] = []
            }
            C[A].push(this.xmlNodeToJSON(D.childNodes[B]))
        }
    }
    return C
};

function callerFunction(A, B) {
    this.handler = function (C) {
        if (!C) {
            C = window.event
        }
        A(C, B);
        return true
    };
    return this.handler
}
function getAbsoluteLeft(A) {
    return getOffset(A).left
}
function getAbsoluteTop(A) {
    return getOffset(A).top
}
function getOffsetSum(A) {
    var C = 0,
        B = 0;
    while (A) {
        C = C + parseInt(A.offsetTop);
        B = B + parseInt(A.offsetLeft);
        A = A.offsetParent
    }
    return {
        top: C,
        left: B
    }
}
function getOffsetRect(D) {
    var G = D.getBoundingClientRect();
    var H = document.body;
    var B = document.documentElement;
    var A = window.pageYOffset || B.scrollTop || H.scrollTop;
    var E = window.pageXOffset || B.scrollLeft || H.scrollLeft;
    var F = B.clientTop || H.clientTop || 0;
    var I = B.clientLeft || H.clientLeft || 0;
    var J = G.top + A - F;
    var C = G.left + E - I;
    return {
        top: Math.round(J),
        left: Math.round(C)
    }
}
function getOffset(A) {
    if (A.getBoundingClientRect && !_isChrome) {
        return getOffsetRect(A)
    } else {
        return getOffsetSum(A)
    }
}
function convertStringToBoolean(A) {
    if (typeof(A) == "string") {
        A = A.toLowerCase()
    }
    switch (A) {
    case "1":
    case "true":
    case "yes":
    case "y":
    case 1:
    case true:
        return true;
        break;
    default:
        return false
    }
}
function getUrlSymbol(A) {
    if (A.indexOf("?") != -1) {
        return "&"
    } else {
        return "?"
    }
}
function dhtmlDragAndDropObject() {
    if (window.dhtmlDragAndDrop) {
        return window.dhtmlDragAndDrop
    }
    this.lastLanding = 0;
    this.dragNode = 0;
    this.dragStartNode = 0;
    this.dragStartObject = 0;
    this.tempDOMU = null;
    this.tempDOMM = null;
    this.waitDrag = 0;
    window.dhtmlDragAndDrop = this;
    return this
}
dhtmlDragAndDropObject.prototype.removeDraggableItem = function (A) {
    A.onmousedown = null;
    A.dragStarter = null;
    A.dragLanding = null
};
dhtmlDragAndDropObject.prototype.addDraggableItem = function (A, B) {
    A.onmousedown = this.preCreateDragCopy;
    A.dragStarter = B;
    this.addDragLanding(A, B)
};
dhtmlDragAndDropObject.prototype.addDragLanding = function (A, B) {
    A.dragLanding = B
};
dhtmlDragAndDropObject.prototype.preCreateDragCopy = function (A) {
    if ((A || event) && (A || event).button == 2) {
        return
    }
    if (window.dhtmlDragAndDrop.waitDrag) {
        window.dhtmlDragAndDrop.waitDrag = 0;
        document.body.onmouseup = window.dhtmlDragAndDrop.tempDOMU;
        document.body.onmousemove = window.dhtmlDragAndDrop.tempDOMM;
        return false
    }
    window.dhtmlDragAndDrop.waitDrag = 1;
    window.dhtmlDragAndDrop.tempDOMU = document.body.onmouseup;
    window.dhtmlDragAndDrop.tempDOMM = document.body.onmousemove;
    window.dhtmlDragAndDrop.dragStartNode = this;
    window.dhtmlDragAndDrop.dragStartObject = this.dragStarter;
    document.body.onmouseup = window.dhtmlDragAndDrop.preCreateDragCopy;
    document.body.onmousemove = window.dhtmlDragAndDrop.callDrag;
    window.dhtmlDragAndDrop.downtime = new Date().valueOf();
    if ((A) && (A.preventDefault)) {
        A.preventDefault();
        return false
    }
    return false
};
dhtmlDragAndDropObject.prototype.callDrag = function (C) {
    if (!C) {
        C = window.event
    }
    dragger = window.dhtmlDragAndDrop;
    if ((new Date()).valueOf() - dragger.downtime < 100) {
        return
    }
    if ((C.button == 0) && (_isIE)) {
        return dragger.stopDrag()
    }
    if (!dragger.dragNode && dragger.waitDrag) {
        dragger.dragNode = dragger.dragStartObject._createDragNode(dragger.dragStartNode, C);
        if (!dragger.dragNode) {
            return dragger.stopDrag()
        }
        dragger.dragNode.onselectstart = function () {
            return false
        };
        dragger.gldragNode = dragger.dragNode;
        document.body.appendChild(dragger.dragNode);
        document.body.onmouseup = dragger.stopDrag;
        dragger.waitDrag = 0;
        dragger.dragNode.pWindow = window;
        dragger.initFrameRoute()
    }
    if (dragger.dragNode.parentNode != window.document.body) {
        var A = dragger.gldragNode;
        if (dragger.gldragNode.old) {
            A = dragger.gldragNode.old
        }
        A.parentNode.removeChild(A);
        var B = dragger.dragNode.pWindow;
        if (_isIE) {
            var E = document.createElement("Div");
            E.innerHTML = dragger.dragNode.outerHTML;
            dragger.dragNode = E.childNodes[0]
        } else {
            dragger.dragNode = dragger.dragNode.cloneNode(true)
        }
        dragger.dragNode.pWindow = window;
        dragger.gldragNode.old = dragger.dragNode;
        document.body.appendChild(dragger.dragNode);
        B.dhtmlDragAndDrop.dragNode = dragger.dragNode
    }
    dragger.dragNode.style.left = C.clientX + 15 + (dragger.fx ? dragger.fx * (-1) : 0) + (document.body.scrollLeft || document.documentElement.scrollLeft) + "px";
    dragger.dragNode.style.top = C.clientY + 3 + (dragger.fy ? dragger.fy * (-1) : 0) + (document.body.scrollTop || document.documentElement.scrollTop) + "px";
    if (!C.srcElement) {
        var D = C.target
    } else {
        D = C.srcElement
    }
    dragger.checkLanding(D, C)
};
dhtmlDragAndDropObject.prototype.calculateFramePosition = function (E) {
    if (window.name) {
        var C = parent.frames[window.name].frameElement.offsetParent;
        var D = 0;
        var B = 0;
        while (C) {
            D += C.offsetLeft;
            B += C.offsetTop;
            C = C.offsetParent
        }
        if ((parent.dhtmlDragAndDrop)) {
            var A = parent.dhtmlDragAndDrop.calculateFramePosition(1);
            D += A.split("_")[0] * 1;
            B += A.split("_")[1] * 1
        }
        if (E) {
            return D + "_" + B
        } else {
            this.fx = D
        }
        this.fy = B
    }
    return "0_0"
};
dhtmlDragAndDropObject.prototype.checkLanding = function (B, A) {
    if ((B) && (B.dragLanding)) {
        if (this.lastLanding) {
            this.lastLanding.dragLanding._dragOut(this.lastLanding)
        }
        this.lastLanding = B;
        this.lastLanding = this.lastLanding.dragLanding._dragIn(this.lastLanding, this.dragStartNode, A.clientX, A.clientY, A);
        this.lastLanding_scr = (_isIE ? A.srcElement : A.target)
    } else {
        if ((B) && (B.tagName != "BODY")) {
            this.checkLanding(B.parentNode, A)
        } else {
            if (this.lastLanding) {
                this.lastLanding.dragLanding._dragOut(this.lastLanding, A.clientX, A.clientY, A)
            }
            this.lastLanding = 0;
            if (this._onNotFound) {
                this._onNotFound()
            }
        }
    }
};
dhtmlDragAndDropObject.prototype.stopDrag = function (B, C) {
    dragger = window.dhtmlDragAndDrop;
    if (!C) {
        dragger.stopFrameRoute();
        var A = dragger.lastLanding;
        dragger.lastLanding = null;
        if (A) {
            A.dragLanding._drag(dragger.dragStartNode, dragger.dragStartObject, A, (_isIE ? event.srcElement : B.target))
        }
    }
    dragger.lastLanding = null;
    if ((dragger.dragNode) && (dragger.dragNode.parentNode == document.body)) {
        dragger.dragNode.parentNode.removeChild(dragger.dragNode)
    }
    dragger.dragNode = 0;
    dragger.gldragNode = 0;
    dragger.fx = 0;
    dragger.fy = 0;
    dragger.dragStartNode = 0;
    dragger.dragStartObject = 0;
    document.body.onmouseup = dragger.tempDOMU;
    document.body.onmousemove = dragger.tempDOMM;
    dragger.tempDOMU = null;
    dragger.tempDOMM = null;
    dragger.waitDrag = 0
};
dhtmlDragAndDropObject.prototype.stopFrameRoute = function (C) {
    if (C) {
        window.dhtmlDragAndDrop.stopDrag(1, 1)
    }
    for (var A = 0; A < window.frames.length; A++) {
        try {
            if ((window.frames[A] != C) && (window.frames[A].dhtmlDragAndDrop)) {
                window.frames[A].dhtmlDragAndDrop.stopFrameRoute(window)
            }
        } catch (B) {}
    }
    try {
        if ((parent.dhtmlDragAndDrop) && (parent != window) && (parent != C)) {
            parent.dhtmlDragAndDrop.stopFrameRoute(window)
        }
    } catch (B) {}
};
dhtmlDragAndDropObject.prototype.initFrameRoute = function (C, D) {
    if (C) {
        window.dhtmlDragAndDrop.preCreateDragCopy({});
        window.dhtmlDragAndDrop.dragStartNode = C.dhtmlDragAndDrop.dragStartNode;
        window.dhtmlDragAndDrop.dragStartObject = C.dhtmlDragAndDrop.dragStartObject;
        window.dhtmlDragAndDrop.dragNode = C.dhtmlDragAndDrop.dragNode;
        window.dhtmlDragAndDrop.gldragNode = C.dhtmlDragAndDrop.dragNode;
        window.document.body.onmouseup = window.dhtmlDragAndDrop.stopDrag;
        window.waitDrag = 0;
        if (((!_isIE) && (D)) && ((!_isFF) || (_FFrv < 1.8))) {
            window.dhtmlDragAndDrop.calculateFramePosition()
        }
    }
    try {
        if ((parent.dhtmlDragAndDrop) && (parent != window) && (parent != C)) {
            parent.dhtmlDragAndDrop.initFrameRoute(window)
        }
    } catch (B) {}
    for (var A = 0; A < window.frames.length; A++) {
        try {
            if ((window.frames[A] != C) && (window.frames[A].dhtmlDragAndDrop)) {
                window.frames[A].dhtmlDragAndDrop.initFrameRoute(window, ((!C || D) ? 1 : 0))
            }
        } catch (B) {}
    }
};
var _isFF = false;
var _isIE = false;
var _isOpera = false;
var _isKHTML = false;
var _isMacOS = false;
var _isChrome = false;
if (navigator.userAgent.indexOf("Macintosh") != -1) {
    _isMacOS = true
}
if (navigator.userAgent.toLowerCase().indexOf("chrome") > -1) {
    _isChrome = true
}
if ((navigator.userAgent.indexOf("Safari") != -1) || (navigator.userAgent.indexOf("Konqueror") != -1)) {
    var _KHTMLrv = parseFloat(navigator.userAgent.substr(navigator.userAgent.indexOf("Safari") + 7, 5));
    if (_KHTMLrv > 525) {
        _isFF = true;
        var _FFrv = 1.9
    } else {
        _isKHTML = true
    }
} else {
    if (navigator.userAgent.indexOf("Opera") != -1) {
        _isOpera = true;
        _OperaRv = parseFloat(navigator.userAgent.substr(navigator.userAgent.indexOf("Opera") + 6, 3))
    } else {
        if (navigator.appName.indexOf("Microsoft") != -1) {
            _isIE = true;
            if (navigator.appVersion.indexOf("MSIE 8.0") != -1 && document.compatMode != "BackCompat") {
                _isIE = 8
            }
        } else {
            _isFF = true;
            var _FFrv = parseFloat(navigator.userAgent.split("rv:")[1])
        }
    }
}
dtmlXMLLoaderObject.prototype.doXPath = function (C, E, D, I) {
    if (_isKHTML || (!_isIE && !window.XPathResult)) {
        return this.doXPathOpera(C, E)
    }
    if (_isIE) {
        if (!E) {
            if (!this.xmlDoc.nodeName) {
                E = this.xmlDoc.responseXML
            } else {
                E = this.xmlDoc
            }
        }
        if (!E) {
            dhtmlxError.throwError("LoadXML", "Incorrect XML", [(E || this.xmlDoc), this.mainObject])
        }
        if (D != null) {
            E.setProperty("SelectionNamespaces", "xmlns:xsl='" + D + "'")
        }
        if (I == "single") {
            return E.selectSingleNode(C)
        } else {
            return E.selectNodes(C) || new Array(0)
        }
    } else {
        var A = E;
        if (!E) {
            if (!this.xmlDoc.nodeName) {
                E = this.xmlDoc.responseXML
            } else {
                E = this.xmlDoc
            }
        }
        if (!E) {
            dhtmlxError.throwError("LoadXML", "Incorrect XML", [(E || this.xmlDoc), this.mainObject])
        }
        if (E.nodeName.indexOf("document") != -1) {
            A = E
        } else {
            A = E;
            E = E.ownerDocument
        }
        var G = XPathResult.ANY_TYPE;
        if (I == "single") {
            G = XPathResult.FIRST_ORDERED_NODE_TYPE
        }
        var F = new Array();
        var B = E.evaluate(C, A, function (J) {
            return D
        }, G, null);
        if (G == XPathResult.FIRST_ORDERED_NODE_TYPE) {
            return B.singleNodeValue
        }
        var H = B.iterateNext();
        while (H) {
            F[F.length] = H;
            H = B.iterateNext()
        }
        return F
    }
};

function _dhtmlxError(B, A, C) {
    if (!this.catches) {
        this.catches = new Array()
    }
    return this
}
_dhtmlxError.prototype.catchError = function (B, A) {
    this.catches[B] = A
};
_dhtmlxError.prototype.throwError = function (B, A, C) {
    if (this.catches[B]) {
        return this.catches[B](B, A, C)
    }
    if (this.catches.ALL) {
        return this.catches.ALL(B, A, C)
    }
    alert("Error type: " + arguments[0] + "\nDescription: " + arguments[1]);
    return null
};
window.dhtmlxError = new _dhtmlxError();
dtmlXMLLoaderObject.prototype.doXPathOpera = function (C, A) {
    var E = C.replace(/[\/]+/gi, "/").split("/");
    var D = null;
    var B = 1;
    if (!E.length) {
        return []
    }
    if (E[0] == ".") {
        D = [A]
    } else {
        if (E[0] == "") {
            D = (this.xmlDoc.responseXML || this.xmlDoc).getElementsByTagName(E[B].replace(/\[[^\]]*\]/g, ""));
            B++
        } else {
            return []
        }
    }
    for (B; B < E.length; B++) {
        D = this._getAllNamedChilds(D, E[B])
    }
    if (E[B - 1].indexOf("[") != -1) {
        D = this._filterXPath(D, E[B - 1])
    }
    return D
};
dtmlXMLLoaderObject.prototype._filterXPath = function (B, A) {
    var D = new Array();
    var A = A.replace(/[^\[]*\[\@/g, "").replace(/[\[\]\@]*/g, "");
    for (var C = 0; C < B.length; C++) {
        if (B[C].getAttribute(A)) {
            D[D.length] = B[C]
        }
    }
    return D
};
dtmlXMLLoaderObject.prototype._getAllNamedChilds = function (B, A) {
    var E = new Array();
    if (_isKHTML) {
        A = A.toUpperCase()
    }
    for (var D = 0; D < B.length; D++) {
        for (var C = 0; C < B[D].childNodes.length; C++) {
            if (_isKHTML) {
                if (B[D].childNodes[C].tagName && B[D].childNodes[C].tagName.toUpperCase() == A) {
                    E[E.length] = B[D].childNodes[C]
                }
            } else {
                if (B[D].childNodes[C].tagName == A) {
                    E[E.length] = B[D].childNodes[C]
                }
            }
        }
    }
    return E
};

function dhtmlXHeir(B, A) {
    for (var C in A) {
        if (typeof(A[C]) == "function") {
            B[C] = A[C]
        }
    }
    return B
}
function dhtmlxEvent(B, C, A) {
    if (B.addEventListener) {
        B.addEventListener(C, A, false)
    } else {
        if (B.attachEvent) {
            B.attachEvent("on" + C, A)
        }
    }
}
dtmlXMLLoaderObject.prototype.xslDoc = null;
dtmlXMLLoaderObject.prototype.setXSLParamValue = function (B, C, D) {
    if (!D) {
        D = this.xslDoc
    }
    if (D.responseXML) {
        D = D.responseXML
    }
    var A = this.doXPath("/xsl:stylesheet/xsl:variable[@name='" + B + "']", D, "http://www.w3.org/1999/XSL/Transform", "single");
    if (A != null) {
        A.firstChild.nodeValue = C
    }
};
dtmlXMLLoaderObject.prototype.doXSLTransToObject = function (D, B) {
    if (!D) {
        D = this.xslDoc
    }
    if (D.responseXML) {
        D = D.responseXML
    }
    if (!B) {
        B = this.xmlDoc
    }
    if (B.responseXML) {
        B = B.responseXML
    }
    if (!_isIE) {
        if (!this.XSLProcessor) {
            this.XSLProcessor = new XSLTProcessor();
            this.XSLProcessor.importStylesheet(D)
        }
        var A = this.XSLProcessor.transformToDocument(B)
    } else {
        var A = new ActiveXObject("Msxml2.DOMDocument.3.0");
        try {
            B.transformNodeToObject(D, A)
        } catch (C) {
            A = B.transformNode(D)
        }
    }
    return A
};
dtmlXMLLoaderObject.prototype.doXSLTransToString = function (C, B) {
    var A = this.doXSLTransToObject(C, B);
    if (typeof(A) == "string") {
        return A
    }
    return this.doSerialization(A)
};
dtmlXMLLoaderObject.prototype.doSerialization = function (B) {
    if (!B) {
        B = this.xmlDoc
    }
    if (B.responseXML) {
        B = B.responseXML
    }
    if (!_isIE) {
        var A = new XMLSerializer();
        return A.serializeToString(B)
    } else {
        return B.xml
    }
};
dhtmlxEventable = function (obj) {
    obj.dhx_SeverCatcherPath = "";
    obj.attachEvent = function (name, catcher, callObj) {
        name = "ev_" + name.toLowerCase();
        if (!this[name]) {
            this[name] = new this.eventCatcher(callObj || this)
        }
        return (name + ":" + this[name].addEvent(catcher))
    };
    obj.callEvent = function (name, arg0) {
        name = "ev_" + name.toLowerCase();
        if (this[name]) {
            return this[name].apply(this, arg0)
        }
        return true
    };
    obj.checkEvent = function (name) {
        return ( !! this["ev_" + name.toLowerCase()])
    };
    obj.eventCatcher = function (obj) {
        var dhx_catch = [];
        var z = function () {
            var res = true;
            for (var i = 0; i < dhx_catch.length; i++) {
                if (dhx_catch[i] != null) {
                    var zr = dhx_catch[i].apply(obj, arguments);
                    res = res && zr
                }
            }
            return res
        };
        z.addEvent = function (ev) {
            if (typeof(ev) != "function") {
                ev = eval(ev)
            }
            if (ev) {
                return dhx_catch.push(ev) - 1
            }
            return false
        };
        z.removeEvent = function (id) {
            dhx_catch[id] = null
        };
        return z
    };
    obj.detachEvent = function (id) {
        if (id != false) {
            var list = id.split(":");
            this[list[0]].removeEvent(list[1])
        }
    }
};

function dataProcessor(A) {
    this.serverProcessor = A;
    this.action_param = "!nativeeditor_status";
    this.object = null;
    this.updatedRows = [];
    this.autoUpdate = true;
    this.updateMode = "cell";
    this._tMode = "GET";
    this.post_delim = "_";
    this._waitMode = 0;
    this._in_progress = {};
    this._invalid = {};
    this.mandatoryFields = [];
    this.messages = [];
    this.styles = {
        updated: "font-weight:bold;",
        inserted: "font-weight:bold;",
        deleted: "text-decoration : line-through;",
        invalid: "background-color:FFE0E0;",
        invalid_cell: "border-bottom:2px solid red;",
        error: "color:red;",
        clear: "font-weight:normal;text-decoration:none;"
    };
    this.enableUTFencoding(true);
    dhtmlxEventable(this);
    return this
}
dataProcessor.prototype = {
    setTransactionMode: function (B, A) {
        this._tMode = B;
        this._tSend = A
    },
    escape: function (A) {
        if (this._utf) {
            return encodeURIComponent(A)
        } else {
            return escape(A)
        }
    },
    enableUTFencoding: function (A) {
        this._utf = convertStringToBoolean(A)
    },
    setDataColumns: function (A) {
        this._columns = (typeof A == "string") ? A.split(",") : A
    },
    getSyncState: function () {
        return !this.updatedRows.length
    },
    enableDataNames: function (A) {
        this._endnm = convertStringToBoolean(A)
    },
    enablePartialDataSend: function (A) {
        this._changed = convertStringToBoolean(A)
    },
    setUpdateMode: function (B, A) {
        this.autoUpdate = (B == "cell");
        this.updateMode = B;
        this.dnd = A
    },
    ignore: function (B, A) {
        this._silent_mode = true;
        B.call(A || window);
        this._silent_mode = false
    },
    setUpdated: function (D, C, E) {
        if (this._silent_mode) {
            return
        }
        var B = this.findRow(D);
        E = E || "updated";
        var A = this.obj.getUserData(D, this.action_param);
        if (A && E == "updated") {
            E = A
        }
        if (C) {
            this.set_invalid(D, false);
            this.updatedRows[B] = D;
            this.obj.setUserData(D, this.action_param, E);
            if (this._in_progress[D]) {
                this._in_progress[D] = "wait"
            }
        } else {
            if (!this.is_invalid(D)) {
                this.updatedRows.splice(B, 1);
                this.obj.setUserData(D, this.action_param, "")
            }
        }
        if (!C) {
            this._clearUpdateFlag(D)
        }
        this.markRow(D, C, E);
        if (C && this.autoUpdate) {
            this.sendData(D)
        }
    },
    _clearUpdateFlag: function (A) {},
    markRow: function (F, C, E) {
        var D = "";
        var B = this.is_invalid(F);
        if (B) {
            D = this.styles[B];
            C = true
        }
        if (this.callEvent("onRowMark", [F, C, E, B])) {
            D = this.styles[C ? E : "clear"] + D;
            this.obj[this._methods[0]](F, D);
            if (B && B.details) {
                D += this.styles[B + "_cell"];
                for (var A = 0; A < B.details.length; A++) {
                    if (B.details[A]) {
                        this.obj[this._methods[1]](F, A, D)
                    }
                }
            }
        }
    },
    getState: function (A) {
        return this.obj.getUserData(A, this.action_param)
    },
    is_invalid: function (A) {
        return this._invalid[A]
    },
    set_invalid: function (C, B, A) {
        if (A) {
            B = {
                value: B,
                details: A,
                toString: function () {
                    return this.value.toString()
                }
            }
        }
        this._invalid[C] = B
    },
    checkBeforeUpdate: function (A) {
        return true
    },
    sendData: function (A) {
        if (this._waitMode && (this.obj.mytype == "tree" || this.obj._h2)) {
            return
        }
        if (this.obj.editStop) {
            this.obj.editStop()
        }
        if (typeof A == "undefined" || this._tSend) {
            return this.sendAllData()
        }
        if (this._in_progress[A]) {
            return false
        }
        this.messages = [];
        if (!this.checkBeforeUpdate(A) && this.callEvent("onValidatationError", [A, this.messages])) {
            return false
        }
        this._beforeSendData(this._getRowData(A), A)
    },
    _beforeSendData: function (A, B) {
        if (!this.callEvent("onBeforeUpdate", [B, this.getState(B), A])) {
            return false
        }
        this._sendData(A, B)
    },
    serialize: function (D, E) {
        if (typeof D == "string") {
            return D
        }
        if (typeof E != "undefined") {
            return this.serialize_one(D, "")
        } else {
            var A = [];
            var C = [];
            for (var B in D) {
                if (D.hasOwnProperty(B)) {
                    A.push(this.serialize_one(D[B], B + this.post_delim));
                    C.push(B)
                }
            }
            A.push("ids=" + this.escape(C.join(",")));
            return A.join("&")
        }
    },
    serialize_one: function (D, B) {
        if (typeof D == "string") {
            return D
        }
        var A = [];
        for (var C in D) {
            if (D.hasOwnProperty(C)) {
                A.push(this.escape((B || "") + C) + "=" + this.escape(D[C]))
            }
        }
        return A.join("&")
    },
    _sendData: function (B, C) {
        if (!B) {
            return
        }
        if (!this.callEvent("onBeforeDataSending", C ? [C, this.getState(C), B] : [null, null, B])) {
            return false
        }
        if (C) {
            this._in_progress[C] = (new Date()).valueOf()
        }
        var A = new dtmlXMLLoaderObject(this.afterUpdate, this, true);
        var D = this.serverProcessor + (this._user ? (getUrlSymbol(this.serverProcessor) + ["dhx_user=" + this._user, "dhx_version=" + this.obj.getUserData(0, "version")].join("&")) : "");
        if (this._tMode != "POST") {
            A.loadXML(D + ((D.indexOf("?") != -1) ? "&" : "?") + this.serialize(B, C))
        } else {
            A.loadXML(D, true, this.serialize(B, C))
        }
        this._waitMode++
    },
    sendAllData: function () {
        if (!this.updatedRows.length) {
            return
        }
        this.messages = [];
        var B = true;
        for (var A = 0; A < this.updatedRows.length; A++) {
            B &= this.checkBeforeUpdate(this.updatedRows[A])
        }
        if (!B && !this.callEvent("onValidatationError", ["", this.messages])) {
            return false
        }
        if (this._tSend) {
            this._sendData(this._getAllData())
        } else {
            for (var A = 0; A < this.updatedRows.length; A++) {
                if (!this._in_progress[this.updatedRows[A]]) {
                    if (this.is_invalid(this.updatedRows[A])) {
                        continue
                    }
                    this._beforeSendData(this._getRowData(this.updatedRows[A]), this.updatedRows[A]);
                    if (this._waitMode && (this.obj.mytype == "tree" || this.obj._h2)) {
                        return
                    }
                }
            }
        }
    },
    _getAllData: function (D) {
        var B = {};
        var A = false;
        for (var C = 0; C < this.updatedRows.length; C++) {
            var E = this.updatedRows[C];
            if (this._in_progress[E] || this.is_invalid(E)) {
                continue
            }
            if (!this.callEvent("onBeforeUpdate", [E, this.getState(E)])) {
                continue
            }
            B[E] = this._getRowData(E, E + this.post_delim);
            A = true;
            this._in_progress[E] = (new Date()).valueOf()
        }
        return A ? B : null
    },
    setVerificator: function (B, A) {
        this.mandatoryFields[B] = A || (function (C) {
            return (C != "")
        })
    },
    clearVerificator: function (A) {
        this.mandatoryFields[A] = false
    },
    findRow: function (B) {
        var A = 0;
        for (A = 0; A < this.updatedRows.length; A++) {
            if (B == this.updatedRows[A]) {
                break
            }
        }
        return A
    },
    defineAction: function (A, B) {
        if (!this._uActions) {
            this._uActions = []
        }
        this._uActions[A] = B
    },
    afterUpdateCallback: function (B, G, F, E) {
        var A = B;
        var D = (F != "error" && F != "invalid");
        if (!D) {
            this.set_invalid(B, F)
        }
        if ((this._uActions) && (this._uActions[F]) && (!this._uActions[F](E))) {
            return (delete this._in_progress[A])
        }
        if (this._in_progress[A] != "wait") {
            this.setUpdated(B, false)
        }
        var C = B;
        switch (F) {
        case "inserted":
        case "insert":
            if (G != B) {
                this.obj[this._methods[2]](B, G);
                B = G
            }
            break;
        case "delete":
        case "deleted":
            this.obj.setUserData(B, this.action_param, "true_deleted");
            this.obj[this._methods[3]](B);
            delete this._in_progress[A];
            return this.callEvent("onAfterUpdate", [B, F, G, E]);
            break
        }
        if (this._in_progress[A] != "wait") {
            if (D) {
                this.obj.setUserData(B, this.action_param, "")
            }
            delete this._in_progress[A]
        } else {
            delete this._in_progress[A];
            this.setUpdated(G, true, this.obj.getUserData(B, this.action_param))
        }
        this.callEvent("onAfterUpdate", [B, F, G, E])
    },
    afterUpdate: function (G, K, I, H, F) {
        F.getXMLTopNode("data");
        if (!F.xmlDoc.responseXML) {
            return
        }
        var J = F.doXPath("//data/action");
        for (var D = 0; D < J.length; D++) {
            var E = J[D];
            var C = E.getAttribute("type");
            var A = E.getAttribute("sid");
            var B = E.getAttribute("tid");
            G.afterUpdateCallback(A, B, C, E)
        }
        G.finalizeUpdate()
    },
    finalizeUpdate: function () {
        if (this._waitMode) {
            this._waitMode--
        }
        if ((this.obj.mytype == "tree" || this.obj._h2) && this.updatedRows.length) {
            this.sendData()
        }
        this.callEvent("onAfterUpdateFinish", []);
        if (!this.updatedRows.length) {
            this.callEvent("onFullSync", [])
        }
    },
    init: function (A) {
        this.obj = A;
        if (this.obj._dp_init) {
            this.obj._dp_init(this)
        }
    },
    setOnAfterUpdate: function (A) {
        this.attachEvent("onAfterUpdate", A)
    },
    enableDebug: function (A) {},
    setOnBeforeUpdateHandler: function (A) {
        this.attachEvent("onBeforeDataSending", A)
    },
/* starts autoupdate mode
		@param interval
			time interval for sending update requests
	*/
    setAutoUpdate: function (C, B) {
        C = C || 2000;
        this._user = B || (new Date()).valueOf();
        this._need_update = false;
        this._loader = null;
        this._update_busy = false;
        this.attachEvent("onAfterUpdate", function (D, F, G, E) {
            this.afterAutoUpdate(D, F, G, E)
        });
        this.attachEvent("onFullSync", function () {
            this.fullSync()
        });
        var A = this;
        window.setInterval(function () {
            A.loadUpdate()
        }, C)
    },
/* process updating request answer
		if status == collision version is depricated
		set flag for autoupdating immidiatly
	*/
    afterAutoUpdate: function (A, C, D, B) {
        if (C == "collision") {
            this._need_update = true;
            return false
        } else {
            return true
        }
    },
/* callback function for onFillSync event
		call update function if it's need
	*/
    fullSync: function () {
        if (this._need_update == true) {
            this._need_update = false;
            this.loadUpdate()
        }
        return true
    },
/* sends query to the server and call callback function
	*/
    getUpdates: function (A, B) {
        if (this._update_busy) {
            return false
        } else {
            this._update_busy = true
        }
        this._loader = this._loader || new dtmlXMLLoaderObject(true);
        this._loader.async = true;
        this._loader.waitCall = B;
        this._loader.loadXML(A)
    },
/* returns xml node value
		@param node
			xml node
	*/
    _v: function (A) {
        if (A.firstChild) {
            return A.firstChild.nodeValue
        }
        return ""
    },
/* returns values array of xml nodes array
		@param arr
			array of xml nodes
	*/
    _a: function (A) {
        var C = [];
        for (var B = 0; B < A.length; B++) {
            C[B] = this._v(A[B])
        }
        return C
    },
/* loads updates and processes them
	*/
    loadUpdate: function () {
        var B = this;
        var A = this.obj.getUserData(0, "version");
        var C = this.serverProcessor + getUrlSymbol(this.serverProcessor) + ["dhx_user=" + this._user, "dhx_version=" + A].join("&");
        C = C.replace("editing=true&", "");
        this.getUpdates(C, function () {
            var F = B._loader.doXPath("//userdata");
            B.obj.setUserData(0, "version", B._v(F[0]));
            var D = B._loader.doXPath("//update");
            if (D.length) {
                B._silent_mode = true;
                for (var G = 0; G < D.length; G++) {
                    var E = D[G].getAttribute("status");
                    var I = D[G].getAttribute("id");
                    var H = D[G].getAttribute("parent");
                    switch (E) {
                    case "inserted":
                        B.callEvent("insertCallback", [D[G], I, H]);
                        break;
                    case "updated":
                        B.callEvent("updateCallback", [D[G], I, H]);
                        break;
                    case "deleted":
                        B.callEvent("deleteCallback", [D[G], I, H]);
                        break
                    }
                }
                B._silent_mode = false
            }
            B._update_busy = false;
            B = null
        })
    }
};
if (window.dhtmlXGridObject) {
    dhtmlXGridObject.prototype._init_point_connector = dhtmlXGridObject.prototype._init_point;
    dhtmlXGridObject.prototype._init_point = function () {
        var A = function (E) {
            E = E.replace(/(\?|\&)connector[^\f]*/g, "");
            return E + (E.indexOf("?") != -1 ? "&" : "?") + "connector=true" + (mygrid.hdr.rows.length > 0 ? "&dhx_no_header=1" : "")
        };
        var D = function (E) {
            return A(E) + (this._connector_sorting || "") + (this._connector_filter || "")
        };
        var C = function (F, G, E) {
            this._connector_sorting = "&dhx_sort[" + G + "]=" + E;
            return D.call(this, F)
        };
        var B = function (F, E, H) {
            for (var G = 0; G < E.length; G++) {
                E[G] = "dhx_filter[" + E[G] + "]=" + encodeURIComponent(H[G])
            }
            this._connector_filter = "&" + E.join("&");
            return D.call(this, F)
        };
        this.attachEvent("onCollectValues", function (E) {
            if (this._con_f_used[E]) {
                if (typeof(this._con_f_used[E]) == "object") {
                    return this._con_f_used[E]
                } else {
                    return false
                }
            }
            return true
        });
        this.attachEvent("onDynXLS", function () {
            this.xmlFileUrl = D.call(this, this.xmlFileUrl);
            return true
        });
        this.attachEvent("onBeforeSorting", function (H, G, F) {
            if (G == "connector") {
                var E = this;
                this.clearAndLoad(C.call(this, this.xmlFileUrl, H, F), function () {
                    E.setSortImgState(true, H, F)
                });
                return false
            }
            return true
        });
        this.attachEvent("onFilterStart", function (F, E) {
            if (this._con_f_used.length) {
                this.clearAndLoad(B.call(this, this.xmlFileUrl, F, E));
                return false
            }
            return true
        });
        this.attachEvent("onXLE", function (F, E, H, G) {
            if (!G) {
                return
            }
        });
        if (this._init_point_connector) {
            this._init_point_connector()
        }
    };
    dhtmlXGridObject.prototype._con_f_used = [];
    dhtmlXGridObject.prototype._in_header_connector_text_filter = function (B, A) {
        if (!this._con_f_used[A]) {
            this._con_f_used[A] = 1
        }
        return this._in_header_text_filter(B, A)
    };
    dhtmlXGridObject.prototype._in_header_connector_select_filter = function (B, A) {
        if (!this._con_f_used[A]) {
            this._con_f_used[A] = 2
        }
        return this._in_header_select_filter(B, A)
    };
    dhtmlXGridObject.prototype.load_connector = dhtmlXGridObject.prototype.load;
    dhtmlXGridObject.prototype.load = function (B, E, D) {
        if (!this._colls_loaded && this.cellType) {
            var A = [];
            for (var C = 0; C < this.cellType.length; C++) {
                if (this.cellType[C].indexOf("co") == 0 || this._con_f_used[C] == 2) {
                    A.push(C)
                }
            }
            if (A.length) {
                arguments[0] += (arguments[0].indexOf("?") != -1 ? "&" : "?") + "connector=true&dhx_colls=" + A.join(",")
            }
        }
        return this.load_connector.apply(this, arguments)
    };
    dhtmlXGridObject.prototype._parseHead_connector = dhtmlXGridObject.prototype._parseHead;
    dhtmlXGridObject.prototype._parseHead = function (A, L, I) {
        this._parseHead_connector.apply(this, arguments);
        if (!this._colls_loaded) {
            var J = this.xmlLoader.doXPath("./coll_options", arguments[0]);
            for (var F = 0; F < J.length; F++) {
                var H = J[F].getAttribute("for");
                var K = [];
                var C = null;
                if (this.cellType[H] == "combo") {
                    C = this.getColumnCombo(H)
                }
                if (this.cellType[H].indexOf("co") == 0) {
                    C = this.getCombo(H)
                }
                var E = this.xmlLoader.doXPath("./item", J[F]);
                for (var D = 0; D < E.length; D++) {
                    var B = E[D].getAttribute("value");
                    if (C) {
                        var G = E[D].getAttribute("label") || B;
                        if (C.addOption) {
                            C.addOption([
                                [B, G]
                            ])
                        } else {
                            C.put(B, G)
                        }
                        K[K.length] = G
                    } else {
                        K[K.length] = B
                    }
                }
                if (this._con_f_used[H * 1]) {
                    this._con_f_used[H * 1] = K
                }
            }
            this._colls_loaded = true
        }
    }
}
if (window.dataProcessor) {
    dataProcessor.prototype.init_original = dataProcessor.prototype.init;
    dataProcessor.prototype.init = function (A) {
        this.init_original(A);
        A._dataprocessor = this;
        this.setTransactionMode("POST", true);
        this.serverProcessor += (this.serverProcessor.indexOf("?") != -1 ? "&" : "?") + "editing=true"
    }
}
dhtmlxError.catchError("LoadXML", function (B, A, C) {
    alert(C[0].responseText)
});
window.dhtmlXScheduler = window.scheduler = {
    version: 2.2
};
dhtmlxEventable(scheduler);
scheduler.init = function (C, A, B) {
    A = A || (new Date());
    B = B || "week";
    this._obj = (typeof C == "string") ? document.getElementById(C) : C;
    this._els = [];
    this._scroll = true;
    this._quirks = (_isIE && document.compatMode == "BackCompat");
    this._quirks7 = (_isIE && navigator.appVersion.indexOf("MSIE 8") == -1);
    this.get_elements();
    this.init_templates();
    this.set_actions();
    dhtmlxEvent(window, "resize", function () {
        window.clearTimeout(scheduler._resize_timer);
        scheduler._resize_timer = window.setTimeout(function () {
            if (scheduler.callEvent("onSchedulerResize", [])) {
                scheduler.update_view()
            }
        }, 100)
    });
    this.set_sizes();
    this.setCurrentView(A, B)
};
scheduler.xy = {
    nav_height: 22,
    min_event_height: 40,
    scale_width: 50,
    bar_height: 20,
    scroll_width: 18,
    scale_height: 20,
    month_scale_height: 20,
    menu_width: 25,
    margin_top: 0,
    margin_left: 0,
    editor_width: 140
};
scheduler.keys = {
    edit_save: 13,
    edit_cancel: 27
};
scheduler.set_sizes = function () {
    var B = this._x = this._obj.clientWidth - this.xy.margin_left;
    var D = this._y = this._obj.clientHeight - this.xy.margin_top;
    var E = this._table_view ? 0 : (this.xy.scale_width + this.xy.scroll_width);
    var A = this._table_view ? -1 : this.xy.scale_width;
    this.set_xy(this._els.dhx_cal_navline[0], B, this.xy.nav_height, 0, 0);
    this.set_xy(this._els.dhx_cal_header[0], B - E, this.xy.scale_height, A, this.xy.nav_height + (this._quirks ? -1 : 1));
    var F = this._els.dhx_cal_navline[0].offsetHeight;
    if (F > 0) {
        this.xy.nav_height = F
    }
    var C = this.xy.scale_height + this.xy.nav_height + (this._quirks ? -2 : 0);
    this.set_xy(this._els.dhx_cal_data[0], B, D - (C + 2), 0, C + 2)
};
scheduler.set_xy = function (D, B, C, A, E) {
    D.style.width = Math.max(0, B) + "px";
    D.style.height = Math.max(0, C) + "px";
    if (arguments.length > 3) {
        D.style.left = A + "px";
        D.style.top = E + "px"
    }
};
scheduler.get_elements = function () {
    var D = this._obj.getElementsByTagName("DIV");
    for (var C = 0; C < D.length; C++) {
        var A = D[C].className;
        if (!this._els[A]) {
            this._els[A] = []
        }
        this._els[A].push(D[C]);
        var B = scheduler.locale.labels[D[C].getAttribute("name") || A];
        if (B) {
            D[C].innerHTML = B
        }
    }
};
scheduler.set_actions = function () {
    for (var A in this._els) {
        if (this._click[A]) {
            for (var B = 0; B < this._els[A].length; B++) {
                this._els[A][B].onclick = scheduler._click[A]
            }
        }
    }
    this._obj.onselectstart = function (C) {
        return false
    };
    this._obj.onmousemove = function (C) {
        scheduler._on_mouse_move(C || event)
    };
    this._obj.onmousedown = function (C) {
        scheduler._on_mouse_down(C || event)
    };
    this._obj.onmouseup = function (C) {
        scheduler._on_mouse_up(C || event)
    };
    this._obj.ondblclick = function (C) {
        scheduler._on_dbl_click(C || event)
    }
};
scheduler.select = function (A) {
    if (this._table_view || !this.getEvent(A)._timed) {
        return
    }
    if (this._select_id == A) {
        return
    }
    this.editStop(false);
    this.unselect();
    this._select_id = A;
    this.updateEvent(A)
};
scheduler.unselect = function (B) {
    if (B && B != this._select_id) {
        return
    }
    var A = this._select_id;
    this._select_id = null;
    if (A) {
        this.updateEvent(A)
    }
};
scheduler.getState = function () {
    return {
        mode: this._mode,
        date: this._date,
        min_date: this._min_date,
        max_date: this._max_date,
        editor_id: this._edit_id,
        lightbox_id: this._lightbox_id
    }
};
scheduler._click = {
    dhx_cal_data: function (C) {
        var B = C ? C.target : event.srcElement;
        var D = scheduler._locate_event(B);
        C = C || event;
        if ((D && !scheduler.callEvent("onClick", [D, C])) || scheduler.config.readonly) {
            return
        }
        if (D) {
            scheduler.select(D);
            var A = B.className;
            if (A.indexOf("_icon") != -1) {
                scheduler._click.buttons[A.split(" ")[1].replace("icon_", "")](D)
            }
        } else {
            scheduler._close_not_saved()
        }
    },
    dhx_cal_prev_button: function () {
        scheduler._click.dhx_cal_next_button(0, -1)
    },
    dhx_cal_next_button: function (B, A) {
        scheduler.setCurrentView(scheduler.date.add(scheduler.date[scheduler._mode + "_start"](scheduler._date), (A || 1), scheduler._mode))
    },
    dhx_cal_today_button: function () {
        scheduler.setCurrentView(new Date())
    },
    dhx_cal_tab: function () {
        var A = this.getAttribute("name").split("_")[0];
        scheduler.setCurrentView(scheduler._date, A)
    },
    buttons: {
        "delete": function (B) {
            var A = scheduler.locale.labels.confirm_deleting;
            if (!A || confirm(A)) {
                scheduler.deleteEvent(B)
            }
        },
        edit: function (A) {
            scheduler.edit(A)
        },
        save: function (A) {
            scheduler.editStop(true)
        },
        details: function (A) {
            scheduler.showLightbox(A)
        },
        cancel: function (A) {
            scheduler.editStop(false)
        }
    }
};
scheduler.addEventNow = function (G, B, D) {
    var C = {};
    if (typeof G == "object") {
        C = G;
        G = null
    }
    var E = (this.config.event_duration || this.config.time_step) * 60000;
    if (!G) {
        G = Math.round((new Date()).valueOf() / E) * E
    }
    var A = new Date(G);
    if (!B) {
        var F = this.config.first_hour;
        if (F > A.getHours()) {
            A.setHours(F);
            G = A.valueOf()
        }
        B = G + E
    }
    C.start_date = C.start_date || A;
    C.end_date = C.end_date || new Date(B);
    C.text = C.text || this.locale.labels.new_event;
    C.id = this._drag_id = this.uid();
    this._drag_mode = "new-size";
    this._loading = true;
    this.addEvent(C);
    this.callEvent("onEventCreated", [this._drag_id, D]);
    this._loading = false;
    this._drag_event = {};
    this._on_mouse_up(D)
};
scheduler._on_dbl_click = function (C, D) {
    D = D || (C.target || C.srcElement);
    if (this.config.readonly) {
        return
    }
    var A = D.className.split(" ")[0];
    switch (A) {
    case "dhx_scale_holder":
    case "dhx_scale_holder_now":
    case "dhx_month_body":
        if (!scheduler.config.dblclick_create) {
            break
        }
        var G = this._mouse_coords(C);
        var F = this._min_date.valueOf() + (G.y * this.config.time_step + (this._table_view ? 0 : G.x) * 24 * 60) * 60000;
        F = this._correct_shift(F);
        this.addEventNow(F, null, C);
        break;
    case "dhx_body":
    case "dhx_cal_event_line":
    case "dhx_cal_event_clear":
        var E = this._locate_event(D);
        if (!this.callEvent("onDblClick", [E, C])) {
            return
        }
        if (this.config.details_on_dblclick || this._table_view || !this.getEvent(E)._timed) {
            this.showLightbox(E)
        } else {
            this.edit(E)
        }
        break;
    case "":
        if (D.parentNode) {
            return scheduler._on_dbl_click(C, D.parentNode)
        }
    default:
        var B = this["dblclick_" + A];
        if (B) {
            B.call(this, C)
        }
        break
    }
};
scheduler._mouse_coords = function (D) {
    var F;
    var A = document.body;
    var E = document.documentElement;
    if (D.pageX || D.pageY) {
        F = {
            x: D.pageX,
            y: D.pageY
        }
    } else {
        F = {
            x: D.clientX + (A.scrollLeft || E.scrollLeft || 0) - A.clientLeft,
            y: D.clientY + (A.scrollTop || E.scrollTop || 0) - A.clientTop
        }
    }
    F.x -= getAbsoluteLeft(this._obj) + (this._table_view ? 0 : this.xy.scale_width);
    F.y -= getAbsoluteTop(this._obj) + this.xy.nav_height + (this._dy_shift || 0) + this.xy.scale_height - this._els.dhx_cal_data[0].scrollTop;
    F.ev = D;
    var C = this["mouse_" + this._mode];
    if (C) {
        return C.call(this, F)
    }
    if (!this._table_view) {
        F.x = Math.max(0, Math.ceil(F.x / this._cols[0]) - 1);
        F.y = Math.max(0, Math.ceil(F.y * 60 / (this.config.time_step * this.config.hour_size_px)) - 1) + this.config.first_hour * (60 / this.config.time_step)
    } else {
        var B = 0;
        for (B = 1; B < this._colsS.heights.length; B++) {
            if (this._colsS.heights[B] > F.y) {
                break
            }
        }
        F.y = (Math.max(0, Math.ceil(F.x / this._cols[0]) - 1) + Math.max(0, B - 1) * 7) * 24 * 60 / this.config.time_step;
        F.x = 0
    }
    return F
};
scheduler._close_not_saved = function () {
    if (new Date().valueOf() - (scheduler._new_event || 0) > 500 && scheduler._edit_id) {
        var A = scheduler.locale.labels.confirm_closing;
        if (!A || confirm(A)) {
            scheduler.editStop(scheduler.config.positive_closing)
        }
    }
};
scheduler._correct_shift = function (B, A) {
    return B -= ((new Date(scheduler._min_date)).getTimezoneOffset() - (new Date(B)).getTimezoneOffset()) * 60000 * (A ? -1 : 1)
};
scheduler._on_mouse_move = function (F) {
    if (this._drag_mode) {
        var G = this._mouse_coords(F);
        if (!this._drag_pos || this._drag_pos.x != G.x || this._drag_pos.y != G.y) {
            if (this._edit_id != this._drag_id) {
                this._close_not_saved()
            }
            this._drag_pos = G;
            if (this._drag_mode == "create") {
                this._close_not_saved();
                this._loading = true;
                var B = this._min_date.valueOf() + (G.y * this.config.time_step + (this._table_view ? 0 : G.x) * 24 * 60) * 60000;
                B = this._correct_shift(B);
                if (!this._drag_start) {
                    this._drag_start = B;
                    return
                }
                var E = B;
                if (E == this._drag_start) {
                    return
                }
                this._drag_id = this.uid();
                this.addEvent(new Date(this._drag_start), new Date(E), this.locale.labels.new_event, this._drag_id, G.fields);
                this.callEvent("onEventCreated", [this._drag_id, F]);
                this._loading = false;
                this._drag_mode = "new-size"
            }
            var H = this.getEvent(this._drag_id);
            var B, E;
            if (this._drag_mode == "move") {
                B = this._min_date.valueOf() + (G.y * this.config.time_step + G.x * 24 * 60) * 60000;
                if (!G.custom && this._table_view) {
                    B += this.date.time_part(H.start_date) * 1000
                }
                B = this._correct_shift(B);
                E = H.end_date.valueOf() - (H.start_date.valueOf() - B)
            } else {
                B = H.start_date.valueOf();
                if (this._table_view) {
                    E = this._min_date.valueOf() + G.y * this.config.time_step * 60000 + (G.custom ? 0 : 24 * 60 * 60000)
                } else {
                    E = this.date.date_part(new Date(H.end_date)).valueOf() + G.y * this.config.time_step * 60000;
                    this._els.dhx_cal_data[0].style.cursor = "s-resize";
                    if (this._mode == "week" || this._mode == "day") {
                        E = this._correct_shift(E)
                    }
                }
                if (this._drag_mode == "new-size") {
                    if (E <= this._drag_start) {
                        var D = G.shift || ((this._table_view && !G.custom) ? 24 * 60 * 60000 : 0);
                        B = E - D;
                        E = this._drag_start + (D || (this.config.time_step * 60000))
                    } else {
                        B = this._drag_start
                    }
                } else {
                    if (E <= B) {
                        E = B + this.config.time_step * 60000
                    }
                }
            }
            var I = new Date(E - 1);
            var C = new Date(B);
            if (this._table_view || (I.getDate() == C.getDate() && I.getHours() < this.config.last_hour)) {
                H.start_date = C;
                H.end_date = new Date(E);
                if (this.config.update_render) {
                    this.update_view()
                } else {
                    this.updateEvent(this._drag_id)
                }
            }
            if (this._table_view) {
                this.for_rendered(this._drag_id, function (J) {
                    J.className += " dhx_in_move"
                })
            }
        }
    } else {
        if (scheduler.checkEvent("onMouseMove")) {
            var A = this._locate_event(F.target || F.srcElement);
            this.callEvent("onMouseMove", [A, F])
        }
    }
};
scheduler._on_mouse_context = function (A, B) {
    return this.callEvent("onContextMenu", [this._locate_event(B), A])
};
scheduler._on_mouse_down = function (A, B) {
    if (this.config.readonly || this._drag_mode) {
        return
    }
    B = B || (A.target || A.srcElement);
    if (A.button == 2 || A.ctrlKey) {
        return this._on_mouse_context(A, B)
    }
    switch (B.className.split(" ")[0]) {
    case "dhx_cal_event_line":
    case "dhx_cal_event_clear":
        if (this._table_view) {
            this._drag_mode = "move"
        }
        break;
    case "dhx_header":
    case "dhx_title":
        this._drag_mode = "move";
        break;
    case "dhx_footer":
        this._drag_mode = "resize";
        break;
    case "dhx_scale_holder":
    case "dhx_scale_holder_now":
    case "dhx_month_body":
    case "dhx_matrix_cell":
        this._drag_mode = "create";
        break;
    case "":
        if (B.parentNode) {
            return scheduler._on_mouse_down(A, B.parentNode)
        }
    default:
        this._drag_mode = null;
        this._drag_id = null
    }
    if (this._drag_mode) {
        var C = this._locate_event(B);
        if (!this.config["drag_" + this._drag_mode] || !this.callEvent("onBeforeDrag", [C, this._drag_mode, A])) {
            this._drag_mode = this._drag_id = 0
        } else {
            this._drag_id = C;
            this._drag_event = this._copy_event(this.getEvent(this._drag_id) || {})
        }
    }
    this._drag_start = null
};
scheduler._on_mouse_up = function (B) {
    if (this._drag_mode && this._drag_id) {
        this._els.dhx_cal_data[0].style.cursor = "default";
        var A = this.getEvent(this._drag_id);
        if (this._drag_event._dhx_changed || !this._drag_event.start_date || A.start_date.valueOf() != this._drag_event.start_date.valueOf() || A.end_date.valueOf() != this._drag_event.end_date.valueOf()) {
            var C = (this._drag_mode == "new-size");
            if (!this.callEvent("onBeforeEventChanged", [A, B, C])) {
                if (C) {
                    this.deleteEvent(A.id, true)
                } else {
                    A.start_date = this._drag_event.start_date;
                    A.end_date = this._drag_event.end_date;
                    this.updateEvent(A.id)
                }
            } else {
                if (C && this.config.edit_on_create) {
                    this.unselect();
                    this._new_event = new Date();
                    if (this._table_view || this.config.details_on_create) {
                        this._drag_mode = null;
                        return this.showLightbox(this._drag_id)
                    }
                    this._drag_pos = true;
                    this._select_id = this._edit_id = this._drag_id
                } else {
                    if (!this._new_event) {
                        this.callEvent(C ? "onEventAdded" : "onEventChanged", [this._drag_id, this.getEvent(this._drag_id)])
                    }
                }
            }
        }
        if (this._drag_pos) {
            this.render_view_data()
        }
    }
    this._drag_mode = null;
    this._drag_pos = null
};
scheduler.update_view = function () {
    this._reset_scale();
    if (this._load_mode && this._load()) {
        return this._render_wait = true
    }
    this.render_view_data()
};
scheduler.setCurrentView = function (B, E) {
    if (!this.callEvent("onBeforeViewChange", [this._mode, this._date, E, B])) {
        return
    }
    if (this[this._mode + "_view"] && E && this._mode != E) {
        this[this._mode + "_view"](false)
    }
    this._close_not_saved();
    this._mode = E || this._mode;
    this._date = B;
    this._table_view = (this._mode == "month");
    var D = this._els.dhx_cal_tab;
    for (var C = 0; C < D.length; C++) {
        D[C].className = "dhx_cal_tab" + ((D[C].getAttribute("name") == this._mode + "_tab") ? " active" : "")
    }
    var A = this[this._mode + "_view"];
    A ? A(true) : this.update_view();
    this.callEvent("onViewChange", [this._mode, this._date])
};
scheduler._render_x_header = function (B, D, E, C) {
    var A = document.createElement("DIV");
    A.className = "dhx_scale_bar";
    this.set_xy(A, this._cols[B] - 1, this.xy.scale_height - 2, D, 0);
    A.innerHTML = this.templates[this._mode + "_scale_date"](E, this._mode);
    C.appendChild(A)
};
scheduler._reset_scale = function () {
    if (!this.templates[this._mode + "_date"]) {
        return
    }
    var M = this._els.dhx_cal_header[0];
    var R = this._els.dhx_cal_data[0];
    var P = this.config;
    M.innerHTML = "";
    R.scrollTop = 0;
    R.innerHTML = "";
    var K = ((P.readonly || (!P.drag_resize)) ? " dhx_resize_denied" : "") + ((P.readonly || (!P.drag_move)) ? " dhx_move_denied" : "");
    if (K) {
        R.className = "dhx_cal_data" + K
    }
    this._cols = [];
    this._colsS = {
        height: 0
    };
    this._dy_shift = 0;
    this.set_sizes();
    var I = parseInt(M.style.width);
    var C = 0;
    var O, Q, A, N;
    Q = this.date[this._mode + "_start"](new Date(this._date.valueOf()));
    O = A = this._table_view ? scheduler.date.week_start(Q) : Q;
    N = this.date.date_part(new Date());
    var D = scheduler.date.add(Q, 1, this._mode);
    var E = 7;
    if (!this._table_view) {
        var G = this.date["get_" + this._mode + "_end"];
        if (G) {
            D = G(Q)
        }
        E = Math.round((D.valueOf() - Q.valueOf()) / (1000 * 60 * 60 * 24))
    }
    this._min_date = O;
    this._els.dhx_cal_date[0].innerHTML = this.templates[this._mode + "_date"](Q, D, this._mode);
    for (var L = 0; L < E; L++) {
        this._cols[L] = Math.floor(I / (E - L));
        this._render_x_header(L, C, O, M);
        if (!this._table_view) {
            var F = document.createElement("DIV");
            var B = "dhx_scale_holder";
            if (O.valueOf() == N.valueOf()) {
                B = "dhx_scale_holder_now"
            }
            F.className = B + " " + this.templates.week_date_class(O, N);
            this.set_xy(F, this._cols[L] - 1, P.hour_size_px * (P.last_hour - P.first_hour), C + this.xy.scale_width + 1, 0);
            R.appendChild(F)
        }
        O = this.date.add(O, 1, "day");
        I -= this._cols[L];
        C += this._cols[L];
        this._colsS[L] = (this._cols[L - 1] || 0) + (this._colsS[L - 1] || (this._table_view ? 0 : this.xy.scale_width + 2))
    }
    this._max_date = O;
    this._colsS[E] = this._cols[E - 1] + this._colsS[E - 1];
    if (this._table_view) {
        this._reset_month_scale(R, Q, A)
    } else {
        this._reset_hours_scale(R, Q, A);
        if (P.multi_day) {
            var J = document.createElement("DIV");
            J.className = "dhx_multi_day";
            J.style.visibility = "hidden";
            this.set_xy(J, parseInt(M.style.width), 0, this.xy.scale_width, 0);
            R.appendChild(J);
            var H = J.cloneNode(true);
            H.className = "dhx_multi_day_icon";
            H.style.visibility = "hidden";
            this.set_xy(H, this.xy.scale_width - 1, 0, 0, 0);
            R.appendChild(H);
            this._els.dhx_multi_day = [J, H]
        }
    }
};
scheduler._reset_hours_scale = function (B, A, E) {
    var G = document.createElement("DIV");
    G.className = "dhx_scale_holder";
    var C = new Date(1980, 1, 1, this.config.first_hour, 0, 0);
    for (var D = this.config.first_hour * 1; D < this.config.last_hour; D++) {
        var F = document.createElement("DIV");
        F.className = "dhx_scale_hour";
        F.style.height = this.config.hour_size_px - (this._quirks ? 0 : 1) + "px";
        F.style.width = this.xy.scale_width + "px";
        F.innerHTML = scheduler.templates.hour_scale(C);
        G.appendChild(F);
        C = this.date.add(C, 1, "hour")
    }
    B.appendChild(G);
    if (this.config.scroll_hour) {
        B.scrollTop = this.config.hour_size_px * (this.config.scroll_hour - this.config.first_hour)
    }
};
scheduler._reset_month_scale = function (J, K, I) {
    var H = scheduler.date.add(K, 1, "month");
    var A = new Date();
    this.date.date_part(A);
    this.date.date_part(I);
    var N = Math.ceil((H.valueOf() - I.valueOf()) / (60 * 60 * 24 * 1000 * 7));
    var B = [];
    var L = (Math.floor(J.clientHeight / N) - 22);
    this._colsS.height = L + 22;
    var G = this._colsS.heights = [];
    for (var E = 0; E <= 7; E++) {
        B[E] = " style='height:" + L + "px; width:" + ((this._cols[E] || 0) - 1) + "px;' "
    }
    var D = 0;
    this._min_date = I;
    var F = "<table cellpadding='0' cellspacing='0'>";
    for (var E = 0; E < N; E++) {
        F += "<tr>";
        for (var C = 0; C < 7; C++) {
            F += "<td";
            var M = "";
            if (I < K) {
                M = "dhx_before"
            } else {
                if (I >= H) {
                    M = "dhx_after"
                } else {
                    if (I.valueOf() == A.valueOf()) {
                        M = "dhx_now"
                    }
                }
            }
            F += " class='" + M + " " + this.templates.month_date_class(I, A) + "' ";
            F += "><div class='dhx_month_head'>" + this.templates.month_day(I) + "</div><div class='dhx_month_body' " + B[C] + "></div></td>";
            I = this.date.add(I, 1, "day")
        }
        F += "</tr>";
        G[E] = D;
        D += this._colsS.height
    }
    F += "</table>";
    this._max_date = I;
    J.innerHTML = F;
    return I
};
scheduler.getLabel = function (E, D) {
    var F = this.config.lightbox.sections;
    for (var C = 0; C < F.length; C++) {
        if (F[C].map_to == E) {
            var B = F[C].options;
            for (var A = 0; A < B.length; A++) {
                if (B[A].key == D) {
                    return B[A].label
                }
            }
        }
    }
    return ""
};
scheduler.date = {
    date_part: function (A) {
        A.setHours(0);
        A.setMinutes(0);
        A.setSeconds(0);
        A.setMilliseconds(0);
        return A
    },
    time_part: function (A) {
        return (A.valueOf() / 1000 - A.getTimezoneOffset() * 60) % 86400
    },
    week_start: function (B) {
        var A = B.getDay();
        if (scheduler.config.start_on_monday) {
            if (A == 0) {
                A = 6
            } else {
                A--
            }
        }
        return this.date_part(this.add(B, -1 * A, "day"))
    },
    month_start: function (A) {
        A.setDate(1);
        return this.date_part(A)
    },
    year_start: function (A) {
        A.setMonth(0);
        return this.month_start(A)
    },
    day_start: function (A) {
        return this.date_part(A)
    },
    add: function (B, C, D) {
        var A = new Date(B.valueOf());
        switch (D) {
        case "day":
            A.setDate(A.getDate() + C);
            break;
        case "week":
            A.setDate(A.getDate() + 7 * C);
            break;
        case "month":
            A.setMonth(A.getMonth() + C);
            break;
        case "year":
            A.setYear(A.getFullYear() + C);
            break;
        case "hour":
            A.setHours(A.getHours() + C);
            break;
        case "minute":
            A.setMinutes(A.getMinutes() + C);
            break;
        default:
            return scheduler.date["add_" + D](B, C, D)
        }
        return A
    },
    to_fixed: function (A) {
        if (A < 10) {
            return "0" + A
        }
        return A
    },
    copy: function (A) {
        return new Date(A.valueOf())
    },
    date_to_str: function (B, A) {
        B = B.replace(/%[a-zA-Z]/g, function (C) {
            switch (C) {
            case "%d":
                return '"+scheduler.date.to_fixed(date.getDate())+"';
            case "%m":
                return '"+scheduler.date.to_fixed((date.getMonth()+1))+"';
            case "%j":
                return '"+date.getDate()+"';
            case "%n":
                return '"+(date.getMonth()+1)+"';
            case "%y":
                return '"+scheduler.date.to_fixed(date.getFullYear()%100)+"';
            case "%Y":
                return '"+date.getFullYear()+"';
            case "%D":
                return '"+scheduler.locale.date.day_short[date.getDay()]+"';
            case "%l":
                return '"+scheduler.locale.date.day_full[date.getDay()]+"';
            case "%M":
                return '"+scheduler.locale.date.month_short[date.getMonth()]+"';
            case "%F":
                return '"+scheduler.locale.date.month_full[date.getMonth()]+"';
            case "%h":
                return '"+scheduler.date.to_fixed((date.getHours()+11)%12+1)+"';
            case "%g":
                return '"+((date.getHours()+11)%12+1)+"';
            case "%G":
                return '"+date.getHours()+"';
            case "%H":
                return '"+scheduler.date.to_fixed(date.getHours())+"';
            case "%i":
                return '"+scheduler.date.to_fixed(date.getMinutes())+"';
            case "%a":
                return '"+(date.getHours()>11?"pm":"am")+"';
            case "%A":
                return '"+(date.getHours()>11?"PM":"AM")+"';
            case "%s":
                return '"+scheduler.date.to_fixed(date.getSeconds())+"';
            case "%W":
                return '"+scheduler.date.to_fixed(scheduler.date.getISOWeek(date))+"';
            default:
                return C
            }
        });
        if (A) {
            B = B.replace(/date\.get/g, "date.getUTC")
        }
        return new Function("date", 'return "' + B + '";')
    },
    str_to_date: function (E, C) {
        var F = "var temp=date.split(/[^0-9a-zA-Z]+/g);";
        var A = E.match(/%[a-zA-Z]/g);
        for (var B = 0; B < A.length; B++) {
            switch (A[B]) {
            case "%j":
            case "%d":
                F += "set[2]=temp[" + B + "]||1;";
                break;
            case "%n":
            case "%m":
                F += "set[1]=(temp[" + B + "]||1)-1;";
                break;
            case "%y":
                F += "set[0]=temp[" + B + "]*1+(temp[" + B + "]>50?1900:2000);";
                break;
            case "%g":
            case "%G":
            case "%h":
            case "%H":
                F += "set[3]=temp[" + B + "]||0;";
                break;
            case "%i":
                F += "set[4]=temp[" + B + "]||0;";
                break;
            case "%Y":
                F += "set[0]=temp[" + B + "]||0;";
                break;
            case "%a":
            case "%A":
                F += "set[3]=set[3]%12+((temp[" + B + "]||'').toLowerCase()=='am'?0:12);";
                break;
            case "%s":
                F += "set[5]=temp[" + B + "]||0;";
                break
            }
        }
        var D = "set[0],set[1],set[2],set[3],set[4],set[5]";
        if (C) {
            D = " Date.UTC(" + D + ")"
        }
        return new Function("date", "var set=[0,0,1,0,0,0]; " + F + " return new Date(" + D + ");")
    },
    getISOWeek: function (C) {
        if (!C) {
            return false
        }
        var B = C.getDay();
        if (B == 0) {
            B = 7
        }
        var D = new Date(C.valueOf());
        D.setDate(C.getDate() + (4 - B));
        var A = D.getFullYear();
        var F = Math.floor((D.getTime() - new Date(A, 0, 1).getTime()) / 86400000);
        var E = 1 + Math.floor(F / 7);
        return E
    },
    getUTCISOWeek: function (A) {
        return this.getISOWeek(A)
    }
};
scheduler.locale = {
    date: {
        month_full: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        month_short: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        day_full: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        day_short: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    },
    labels: {
        dhx_cal_today_button: "Today",
        day_tab: "Day",
        week_tab: "Week",
        month_tab: "Month",
        new_event: "New event",
        icon_save: "Save",
        icon_cancel: "Cancel",
        icon_details: "Details",
        icon_edit: "Edit",
        icon_delete: "Delete",
        confirm_closing: "",
        confirm_deleting: "Event will be deleted permanently, are you sure?",
        section_description: "Description",
        section_time: "Time period",
        full_day: "Full day",
        confirm_recurring: "Do you want to edit the whole set of repeated events?",
        section_recurring: "Repeat event",
        button_recurring: "Disabled",
        button_recurring_open: "Enabled",
        agenda_tab: "Agenda",
        date: "Date",
        description: "Description",
        year_tab: "Year"
    }
};
scheduler.config = {
    default_date: "%j %M %Y",
    month_date: "%F %Y",
    load_date: "%Y-%m-%d",
    week_date: "%l",
    day_date: "%D, %F %j",
    hour_date: "%H:%i",
    month_day: "%d",
    xml_date: "%m/%d/%Y %H:%i",
    api_date: "%d-%m-%Y %H:%i",
    hour_size_px: 42,
    time_step: 5,
    start_on_monday: 1,
    first_hour: 0,
    last_hour: 24,
    readonly: false,
    drag_resize: 1,
    drag_move: 1,
    drag_create: 1,
    dblclick_create: 1,
    edit_on_create: 1,
    details_on_create: 0,
    click_form_details: 0,
    server_utc: false,
    positive_closing: false,
    icons_edit: ["icon_save", "icon_cancel"],
    icons_select: ["icon_details", "icon_edit", "icon_delete"],
    lightbox: {
        sections: [{
            name: "description",
            height: 200,
            map_to: "text",
            type: "textarea",
            focus: true
        }, {
            name: "time",
            height: 72,
            type: "time",
            map_to: "auto"
        }]
    }
};
scheduler.templates = {};
scheduler.init_templates = function () {
    var B = scheduler.date.date_to_str;
    var C = scheduler.config;
    var A = function (E, D) {
        for (var F in D) {
            if (!E[F]) {
                E[F] = D[F]
            }
        }
    };
    A(scheduler.templates, {
        day_date: B(C.default_date),
        month_date: B(C.month_date),
        week_date: function (E, D) {
            return scheduler.templates.day_date(E) + " &ndash; " + scheduler.templates.day_date(scheduler.date.add(D, -1, "day"))
        },
        day_scale_date: B(C.default_date),
        month_scale_date: B(C.week_date),
        week_scale_date: B(C.day_date),
        hour_scale: B(C.hour_date),
        time_picker: B(C.hour_date),
        event_date: B(C.hour_date),
        month_day: B(C.month_day),
        xml_date: scheduler.date.str_to_date(C.xml_date, C.server_utc),
        load_format: B(C.load_date, C.server_utc),
        xml_format: B(C.xml_date, C.server_utc),
        api_date: scheduler.date.str_to_date(C.api_date),
        event_header: function (F, D, E) {
            return scheduler.templates.event_date(F) + " - " + scheduler.templates.event_date(D)
        },
        event_text: function (F, D, E) {
            return E.text
        },
        event_class: function (F, D, E) {
            return ""
        },
        month_date_class: function (D) {
            return ""
        },
        week_date_class: function (D) {
            return ""
        },
        event_bar_date: function (F, D, E) {
            return scheduler.templates.event_date(F) + " "
        },
        event_bar_text: function (F, D, E) {
            return E.text
        }
    });
    this.callEvent("onTemplatesReady", [])
};
scheduler.uid = function () {
    if (!this._seed) {
        this._seed = (new Date).valueOf()
    }
    return this._seed++
};
scheduler._events = {};
scheduler.clearAll = function () {
    this._events = {};
    this._loaded = {};
    this.clear_view()
};
scheduler.addEvent = function (A, G, D, F, B) {
    var C = A;
    if (arguments.length != 1) {
        C = B || {};
        C.start_date = A;
        C.end_date = G;
        C.text = D;
        C.id = F
    }
    C.id = C.id || scheduler.uid();
    C.text = C.text || "";
    if (typeof C.start_date == "string") {
        C.start_date = this.templates.api_date(C.start_date)
    }
    if (typeof C.end_date == "string") {
        C.end_date = this.templates.api_date(C.end_date)
    }
    C._timed = this.is_one_day_event(C);
    var E = !this._events[C.id];
    this._events[C.id] = C;
    this.event_updated(C);
    if (!this._loading) {
        this.callEvent(E ? "onEventAdded" : "onEventChanged", [C.id, C])
    }
};
scheduler.deleteEvent = function (C, A) {
    var B = this._events[C];
    if (!A && !this.callEvent("onBeforeEventDelete", [C, B])) {
        return
    }
    if (B) {
        delete this._events[C];
        this.unselect(C);
        this.event_updated(B)
    }
};
scheduler.getEvent = function (A) {
    return this._events[A]
};
scheduler.setEvent = function (B, A) {
    this._events[B] = A
};
scheduler.for_rendered = function (C, B) {
    for (var A = this._rendered.length - 1; A >= 0; A--) {
        if (this._rendered[A].getAttribute("event_id") == C) {
            B(this._rendered[A], A)
        }
    }
};
scheduler.changeEventId = function (C, A) {
    if (C == A) {
        return
    }
    var B = this._events[C];
    if (B) {
        B.id = A;
        this._events[A] = B;
        delete this._events[C]
    }
    this.for_rendered(C, function (D) {
        D.setAttribute("event_id", A)
    });
    if (this._select_id == C) {
        this._select_id = A
    }
    if (this._edit_id == C) {
        this._edit_id = A
    }
    this.callEvent("onEventIdChange", [C, A])
};
(function () {
    var A = ["text", "Text", "start_date", "StartDate", "end_date", "EndDate"];
    var C = function (E) {
        return function (F) {
            return (scheduler.getEvent(F))[E]
        }
    };
    var D = function (E) {
        return function (H, G) {
            var F = scheduler.getEvent(H);
            F[E] = G;
            F._changed = true;
            F._timed = this.is_one_day_event(F);
            scheduler.event_updated(F, true)
        }
    };
    for (var B = 0; B < A.length; B += 2) {
        scheduler["getEvent" + A[B + 1]] = C(A[B]);
        scheduler["setEvent" + A[B + 1]] = D(A[B])
    }
})();
scheduler.event_updated = function (A, B) {
    if (this.is_visible_events(A)) {
        this.render_view_data()
    } else {
        this.clear_event(A.id)
    }
};
scheduler.is_visible_events = function (A) {
    if (A.start_date < this._max_date && this._min_date < A.end_date) {
        return true
    }
    return false
};
scheduler.is_one_day_event = function (A) {
    var B = A.end_date.getDate() - A.start_date.getDate();
    if (!B) {
        return A.start_date.getMonth() == A.end_date.getMonth() && A.start_date.getFullYear() == A.end_date.getFullYear()
    } else {
        if (B < 0) {
            B = Math.ceil((A.end_date.valueOf() - A.start_date.valueOf()) / (24 * 60 * 60 * 1000))
        }
        return (B == 1 && !A.end_date.getHours() && !A.end_date.getMinutes() && (A.start_date.getHours() || A.start_date.getMinutes()))
    }
};
scheduler.get_visible_events = function () {
    var A = [];
    var B = this["filter_" + this._mode];
    for (var C in this._events) {
        if (this.is_visible_events(this._events[C])) {
            if (this._table_view || this.config.multi_day || this._events[C]._timed) {
                if (!B || B(C, this._events[C])) {
                    A.push(this._events[C])
                }
            }
        }
    }
    return A
};
scheduler.render_view_data = function () {
    if (this._not_render) {
        this._render_wait = true;
        return
    }
    this._render_wait = false;
    this.clear_view();
    var B = this.get_visible_events();
    if (this.config.multi_day && !this._table_view) {
        var D = [];
        var A = [];
        for (var C = 0; C < B.length; C++) {
            if (B[C]._timed) {
                D.push(B[C])
            } else {
                A.push(B[C])
            }
        }
        this._table_view = true;
        this.render_data(A);
        this._table_view = false;
        this.render_data(D)
    } else {
        this.render_data(B)
    }
};
scheduler.render_data = function (A, C) {
    A = this._pre_render_events(A, C);
    for (var B = 0; B < A.length; B++) {
        if (this._table_view) {
            this.render_event_bar(A[B])
        } else {
            this.render_event(A[B])
        }
    }
};
scheduler._pre_render_events = function (M, A) {
    var G = this.xy.bar_height;
    var D = this._colsS.heights;
    var F = this._colsS.heights = [0, 0, 0, 0, 0, 0, 0];
    if (!this._table_view) {
        M = this._pre_render_events_line(M, A)
    } else {
        M = this._pre_render_events_table(M, A)
    }
    if (this._table_view) {
        if (A) {
            this._colsS.heights = D
        } else {
            var B = this._els.dhx_cal_data[0].firstChild;
            if (B.rows) {
                for (var E = 0; E < B.rows.length; E++) {
                    F[E]++;
                    if ((F[E]) * G > this._colsS.height - 22) {
                        var N = B.rows[E].cells;
                        for (var C = 0; C < N.length; C++) {
                            N[C].childNodes[1].style.height = F[E] * G + "px"
                        }
                        F[E] = (F[E - 1] || 0) + N[0].offsetHeight
                    }
                    F[E] = (F[E - 1] || 0) + B.rows[E].cells[0].offsetHeight
                }
                F.unshift(0);
                if (B.parentNode.offsetHeight < B.parentNode.scrollHeight && !B._h_fix) {
                    for (var E = 0; E < B.rows.length; E++) {
                        var L = B.rows[E].cells[6].childNodes[0];
                        var J = L.offsetWidth - scheduler.xy.scroll_width + "px";
                        L.style.width = J;
                        L.nextSibling.style.width = J
                    }
                    B._h_fix = true
                }
            } else {
                if (!M.length && this._els.dhx_multi_day[0].style.visibility == "visible") {
                    F[0] = -1
                }
                if (M.length || F[0] == -1) {
                    var H = B.parentNode.childNodes;
                    var I = (F[0] + 1) * G + "px";
                    for (var E = 0; E < H.length; E++) {
                        if (this._colsS[E]) {
                            H[E].style.top = I
                        }
                    }
                    var K = this._els.dhx_multi_day[0];
                    K.style.top = "0px";
                    K.style.height = I;
                    K.style.visibility = (F[0] == -1 ? "hidden" : "visible");
                    K = this._els.dhx_multi_day[1];
                    K.style.height = I;
                    K.style.visibility = (F[0] == -1 ? "hidden" : "visible");
                    K.className = F[0] ? "dhx_multi_day_icon" : "dhx_multi_day_icon_small";
                    this._dy_shift = (F[0] + 1) * G;
                    F[0] = 0
                }
            }
        }
    }
    return M
};
scheduler._get_event_sday = function (A) {
    return Math.floor((A.start_date.valueOf() - this._min_date.valueOf()) / (24 * 60 * 60 * 1000))
};
scheduler._pre_render_events_line = function (H, A) {
    H.sort(function (K, J) {
        return K.start_date > J.start_date ? 1 : -1
    });
    var G = [];
    var I = [];
    for (var C = 0; C < H.length; C++) {
        var F = H[C];
        var D = F.start_date.getHours();
        var B = F.end_date.getHours();
        F._sday = this._get_event_sday(F);
        if (!G[F._sday]) {
            G[F._sday] = []
        }
        if (!A) {
            F._inner = false;
            var E = G[F._sday];
            while (E.length && E[E.length - 1].end_date <= F.start_date) {
                E.splice(E.length - 1, 1)
            }
            if (E.length) {
                E[E.length - 1]._inner = true
            }
            F._sorder = E.length;
            E.push(F);
            if (E.length > (E.max_count || 0)) {
                E.max_count = E.length
            }
        }
        if (D < this.config.first_hour || B >= this.config.last_hour) {
            I.push(F);
            H[C] = F = this._copy_event(F);
            if (D < this.config.first_hour) {
                F.start_date.setHours(this.config.first_hour);
                F.start_date.setMinutes(0)
            }
            if (B >= this.config.last_hour) {
                F.end_date.setMinutes(0);
                F.end_date.setHours(this.config.last_hour)
            }
            if (F.start_date > F.end_date || D == this.config.last_hour) {
                H.splice(C, 1);
                C--;
                continue
            }
        }
    }
    if (!A) {
        for (var C = 0; C < H.length; C++) {
            H[C]._count = G[H[C]._sday].max_count
        }
        for (var C = 0; C < I.length; C++) {
            I[C]._count = G[I[C]._sday].max_count
        }
    }
    return H
};
scheduler._time_order = function (A) {
    A.sort(function (C, B) {
        if (C.start_date.valueOf() == B.start_date.valueOf()) {
            if (C._timed && !B._timed) {
                return 1
            }
            if (!C._timed && B._timed) {
                return -1
            }
            return 0
        }
        return C.start_date > B.start_date ? 1 : -1
    })
};
scheduler._pre_render_events_table = function (P, C) {
    this._time_order(P);
    var F = [];
    var A = [
        [],
        [],
        [],
        [],
        [],
        [],
        []
    ];
    var N = this._colsS.heights;
    var I;
    var M = this._cols.length;
    for (var G = 0; G < P.length; G++) {
        var L = P[G];
        var J = (I || L.start_date);
        var H = L.end_date;
        if (J < this._min_date) {
            J = this._min_date
        }
        if (H > this._max_date) {
            H = this._max_date
        }
        var E = this.locate_holder_day(J, false, L);
        L._sday = E % M;
        var O = this.locate_holder_day(H, true, L) || M;
        L._eday = (O % M) || M;
        L._length = O - E;
        L._sweek = Math.floor((this._correct_shift(J.valueOf(), 1) - this._min_date.valueOf()) / (60 * 60 * 1000 * 24 * M));
        var K = A[L._sweek];
        var D;
        for (D = 0; D < K.length; D++) {
            if (K[D]._eday <= L._sday) {
                break
            }
        }
        L._sorder = D;
        if (L._sday + L._length <= M) {
            I = null;
            F.push(L);
            K[D] = L;
            N[L._sweek] = K.length - 1
        } else {
            var B = this._copy_event(L);
            B._length = M - L._sday;
            B._eday = M;
            B._sday = L._sday;
            B._sweek = L._sweek;
            B._sorder = L._sorder;
            B.end_date = this.date.add(J, B._length, "day");
            F.push(B);
            K[D] = B;
            I = B.end_date;
            N[L._sweek] = K.length - 1;
            G--;
            continue
        }
    }
    return F
};
scheduler._copy_dummy = function () {
    this.start_date = new Date(this.start_date);
    this.end_date = new Date(this.end_date)
};
scheduler._copy_event = function (A) {
    this._copy_dummy.prototype = A;
    return new this._copy_dummy()
};
scheduler._rendered = [];
scheduler.clear_view = function () {
    for (var A = 0; A < this._rendered.length; A++) {
        var B = this._rendered[A];
        if (B.parentNode) {
            B.parentNode.removeChild(B)
        }
    }
    this._rendered = []
};
scheduler.updateEvent = function (B) {
    var A = this.getEvent(B);
    this.clear_event(B);
    if (A && this.is_visible_events(A)) {
        this.render_data([A], true)
    }
};
scheduler.clear_event = function (A) {
    this.for_rendered(A, function (C, B) {
        if (C.parentNode) {
            C.parentNode.removeChild(C)
        }
        scheduler._rendered.splice(B, 1)
    })
};
scheduler.render_event = function (L) {
    var D = scheduler.xy.menu_width;
    if (L._sday < 0) {
        return
    }
    var M = scheduler.locate_holder(L._sday);
    if (!M) {
        return
    }
    var F = L.start_date.getHours() * 60 + L.start_date.getMinutes();
    var C = (L.end_date.getHours() * 60 + L.end_date.getMinutes()) || (scheduler.config.last_hour * 60);
    var K = (Math.round((F * 60 * 1000 - this.config.first_hour * 60 * 60 * 1000) * this.config.hour_size_px / (60 * 60 * 1000))) % (this.config.hour_size_px * 24) + 1;
    var O = Math.max(scheduler.xy.min_event_height, (C - F) * this.config.hour_size_px / 60) + 1;
    var B = Math.floor((M.clientWidth - D) / L._count);
    var E = L._sorder * B + 1;
    if (!L._inner) {
        B = B * (L._count - L._sorder)
    }
    var J = this._render_v_bar(L.id, D + E, K, B, O, L._text_style, scheduler.templates.event_header(L.start_date, L.end_date, L), scheduler.templates.event_text(L.start_date, L.end_date, L));
    this._rendered.push(J);
    M.appendChild(J);
    E = E + parseInt(M.style.left, 10) + D;
    K += this._dy_shift;
    if (this._edit_id == L.id) {
        J.style.zIndex = 1;
        B = Math.max(B - 4, scheduler.xy.editor_width);
        var J = document.createElement("DIV");
        J.setAttribute("event_id", L.id);
        this.set_xy(J, B, O - 20, E, K + 14);
        J.className = "dhx_cal_editor";
        var A = document.createElement("DIV");
        this.set_xy(A, B - 6, O - 26);
        A.style.cssText += ";margin:2px 2px 2px 2px;overflow:hidden;";
        J.appendChild(A);
        this._els.dhx_cal_data[0].appendChild(J);
        this._rendered.push(J);
        A.innerHTML = "<textarea class='dhx_cal_editor'>" + L.text + "</textarea>";
        if (this._quirks7) {
            A.firstChild.style.height = O - 12 + "px"
        }
        this._editor = A.firstChild;
        this._editor.onkeypress = function (Q) {
            if ((Q || event).shiftKey) {
                return true
            }
            var P = (Q || event).keyCode;
            if (P == scheduler.keys.edit_save) {
                scheduler.editStop(true)
            }
            if (P == scheduler.keys.edit_cancel) {
                scheduler.editStop(false)
            }
        };
        this._editor.onselectstart = function (P) {
            return (P || event).cancelBubble = true
        };
        A.firstChild.focus();
        this._els.dhx_cal_data[0].scrollLeft = 0;
        A.firstChild.select()
    }
    if (this._select_id == L.id) {
        var N = this.config["icons_" + ((this._edit_id == L.id) ? "edit" : "select")];
        var I = "";
        for (var H = 0; H < N.length; H++) {
            I += "<div class='dhx_menu_icon " + N[H] + "' title='" + this.locale.labels[N[H]] + "'></div>"
        }
        var G = this._render_v_bar(L.id, E - D + 1, K, D, N.length * 20 + 26, "", "<div class='dhx_menu_head'></div>", I, true);
        G.style.left = E - D + 1;
        this._els.dhx_cal_data[0].appendChild(G);
        this._rendered.push(G)
    }
};
scheduler._render_v_bar = function (D, M, L, N, H, B, F, E, A) {
    var J = document.createElement("DIV");
    var K = this.getEvent(D);
    var I = "dhx_cal_event";
    var C = scheduler.templates.event_class(K.start_date, K.end_date, K);
    if (C) {
        I = I + " " + C
    }
	var G = jQuery('<div>',
					{
						'event_id': D,
						'class': I
					}).css({
						'position':'absolute',
						'top': L,
						'left': M,
						'width': (N - 4),
						'height': H
					}).append(
						jQuery('<div>', {
							'class': 'dhx_header',
							'width': (N - 6)
						}),
						jQuery('<div>', {
							'class': 'dhx_title'
						}).html(F),
						jQuery('<div>', {
							'class': 'dhx_body',
							'width': (N - (this._quirks ? 4 : 14)),
							'height': (H - (this._quirks ? 20 : 30))
							
						}).html(E),
						jQuery('<div>', {
							'class': 'dhx_footer',
							'width': (N - 8),
							'margin-top': A ? 1 : '' 
						})
					)
		if(K.color) {
			jQuery('div', G).css({'background': K.color, 'color': '#FFFFFF'})
		}
	jQuery(J).html(G);
    return J.firstChild
};
scheduler.locate_holder = function (A) {
    if (this._mode == "day") {
        return this._els.dhx_cal_data[0].firstChild
    }
    return this._els.dhx_cal_data[0].childNodes[A]
};
scheduler.locate_holder_day = function (B, C) {
    var A = Math.floor((this._correct_shift(B, 1) - this._min_date) / (60 * 60 * 24 * 1000));
    if (C && this.date.time_part(B)) {
        A++
    }
    return A
};
scheduler.render_event_bar = function (H) {
    var J = this._els.dhx_cal_data[0];
    var I = this._colsS[H._sday];
    var A = this._colsS[H._eday];
    if (A == I) {
        A = this._colsS[H._eday + 1]
    }
    var D = this.xy.bar_height;
    var G = this._colsS.heights[H._sweek] + (this._colsS.height ? (this.xy.month_scale_height + 2) : 2) + H._sorder * D;
    var F = document.createElement("DIV");
    var E = H._timed ? "dhx_cal_event_clear" : "dhx_cal_event_line";
    var B = scheduler.templates.event_class(H.start_date, H.end_date, H);
    if (B) {
        E = E + " " + B
    }
	
	var c_innerHTML = " ";
	var C = jQuery('<div>',
					{
						'event_id': H.id, 
						'class': E
					}).css({
						'position': 'absolute',
						'top': G,
						'left': I,
						'width': (A - I - 15)
					})
    if (H._timed) {
		c_innerHTML = scheduler.templates.event_bar_date(H.start_date, H.end_date, H)
    }
	
	C.html(c_innerHTML + scheduler.templates.event_bar_text(H.start_date, H.end_date, H))
	jQuery(F).html(C);
	
	if (H.color) {
		if (H._length) {
			C.css({'background-color':H.color, 'color': '#FFFFFF'});
		} else {
			C.css('color',H.color);;
		}
	}
	
	if(H.title) {
		C.attr('title',H.title);
	}
	
    this._rendered.push(F.firstChild);
    J.appendChild(F.firstChild)
};

scheduler._locate_event = function (A) {
    var B = null;
    while (A && !B && A.getAttribute) {
        B = A.getAttribute("event_id");
        A = A.parentNode
    }
    return B
};
scheduler.edit = function (A) {
    if (this._edit_id == A) {
        return
    }
    this.editStop(false, A);
    this._edit_id = A;
    this.updateEvent(A)
};
scheduler.editStop = function (B, C) {
    if (C && this._edit_id == C) {
        return
    }
    var A = this.getEvent(this._edit_id);
    if (A) {
        if (B) {
            A.text = this._editor.value
        }
        this._edit_id = null;
        this._editor = null;
        this.updateEvent(A.id);
        this._edit_stop_event(A, B)
    }
};
scheduler._edit_stop_event = function (A, B) {
    if (this._new_event) {
        if (!B) {
            this.deleteEvent(A.id, true)
        } else {
            this.callEvent("onEventAdded", [A.id, A])
        }
        this._new_event = null
    } else {
        if (B) {
            this.callEvent("onEventChanged", [A.id, A])
        }
    }
};
scheduler.getEvents = function (E, D) {
    var A = [];
    for (var B in this._events) {
        var C = this._events[B];
        if (C && C.start_date < D && C.end_date > E) {
            A.push(C)
        }
    }
    return A
};
scheduler._loaded = {};
scheduler._load = function (C, F) {
    C = C || this._load_url;
    C += (C.indexOf("?") == -1 ? "?" : "&") + "timeshift=" + (new Date()).getTimezoneOffset();
    if (this.config.prevent_cache) {
        C += "&uid=" + this.uid()
    }
    var E;
    F = F || this._date;
    if (this._load_mode) {
        var B = this.templates.load_format;
        F = this.date[this._load_mode + "_start"](new Date(F.valueOf()));
        while (F > this._min_date) {
            F = this.date.add(F, -1, this._load_mode)
        }
        E = F;
        var D = true;
        while (E < this._max_date) {
            E = this.date.add(E, 1, this._load_mode);
            if (this._loaded[B(F)] && D) {
                F = this.date.add(F, 1, this._load_mode)
            } else {
                D = false
            }
        }
        var A = E;
        do {
            E = A;
            A = this.date.add(E, -1, this._load_mode)
        } while (A > F && this._loaded[B(A)]);
        if (E <= F) {
            return false
        }
        dhtmlxAjax.get(C + "&from=" + B(F) + "&to=" + B(E), function (G) {
            scheduler.on_load(G)
        });
        while (F < E) {
            this._loaded[B(F)] = true;
            F = this.date.add(F, 1, this._load_mode)
        }
    } else {
        dhtmlxAjax.get(C, function (G) {
            scheduler.on_load(G)
        })
    }
    this.callEvent("onXLS", []);
    return true
};
scheduler.on_load = function (A) {
    this._loading = true;
    if (this._process) {
        var B = this[this._process].parse(A.xmlDoc.responseText)
    } else {
        var B = this._magic_parser(A)
    }
    this._not_render = true;
    for (var C = 0; C < B.length; C++) {
        if (!this.callEvent("onEventLoading", [B[C]])) {
            continue
        }
        this.addEvent(B[C])
    }
    this._not_render = false;
    if (this._render_wait) {
        this.render_view_data()
    }
    if (this._after_call) {
        this._after_call()
    }
    this._after_call = null;
    this._loading = false;
    this.callEvent("onXLE", [])
};
scheduler.json = {};
scheduler.json.parse = function (data) {
    if (typeof data == "string") {
        eval("scheduler._temp = " + data + ";");
        data = scheduler._temp
    }
    var evs = [];
    for (var i = 0; i < data.length; i++) {
        data[i].start_date = scheduler.templates.xml_date(data[i].start_date);
        data[i].end_date = scheduler.templates.xml_date(data[i].end_date);
        evs.push(data[i])
    }
    return evs
};
scheduler.parse = function (B, A) {
    this._process = A;
    this.on_load({
        xmlDoc: {
            responseText: B
        }
    })
};
scheduler.load = function (A, B) {
    if (typeof B == "string") {
        this._process = B;
        B = arguments[2]
    }
    this._load_url = A;
    this._after_call = B;
    this._load(A, this._date)
};
scheduler.setLoadMode = function (A) {
    if (A == "all") {
        A = ""
    }
    this._load_mode = A
};
scheduler.refresh = function (A) {
    alert("not implemented")
};
scheduler.serverList = function (A) {
    return this.serverList[A] = (this.serverList[A] || [])
};
scheduler._userdata = {};
scheduler._magic_parser = function (I) {
    if (!I.getXMLTopNode) {
        var B = I.xmlDoc.responseText;
        I = new dtmlXMLLoaderObject(function () {});
        I.loadXMLString(B)
    }
    var F = I.getXMLTopNode("data");
    if (F.tagName != "data") {
        return []
    }
    var A = I.doXPath("//coll_options");
    for (var E = 0; E < A.length; E++) {
        var H = A[E].getAttribute("for");
        var G = this.serverList[H];
        if (!G) {
            continue
        }
        G.splice(0, G.length);
        var K = I.doXPath(".//item", A[E]);
        for (var C = 0; C < K.length; C++) {
            G.push({
                key: K[C].getAttribute("value"),
                label: K[C].getAttribute("label")
            })
        }
    }
    if (A.length) {
        scheduler.callEvent("onOptionsLoad", [])
    }
    var L = I.doXPath("//userdata");
    for (var E = 0; E < L.length; E++) {
        var D = this.xmlNodeToJSON(L[E]);
        this._userdata[D.name] = D.text
    }
    var J = [];
    var F = I.doXPath("//event");
    for (var E = 0; E < F.length; E++) {
        J[E] = this.xmlNodeToJSON(F[E]);
        J[E].text = J[E].text || J[E]._tagvalue;
        J[E].start_date = this.templates.xml_date(J[E].start_date);
        J[E].end_date = this.templates.xml_date(J[E].end_date)
    }
    return J
};
scheduler.xmlNodeToJSON = function (C) {
    var B = {};
    for (var A = 0; A < C.attributes.length; A++) {
        B[C.attributes[A].name] = C.attributes[A].value
    }
    for (var A = 0; A < C.childNodes.length; A++) {
        var D = C.childNodes[A];
        if (D.nodeType == 1) {
            B[D.tagName] = D.firstChild ? D.firstChild.nodeValue : ""
        }
    }
    if (!B.text) {
        B.text = C.firstChild ? C.firstChild.nodeValue : ""
    }
    return B
};
scheduler.attachEvent("onXLS", function () {
    if (this.config.show_loading === true) {
        var A;
        A = this.config.show_loading = document.createElement("DIV");
        A.className = "dhx_loading";
        A.style.left = Math.round((this._x - 128) / 2) + "px";
        A.style.top = Math.round((this._y - 15) / 2) + "px";
        this._obj.appendChild(A)
    }
});
scheduler.attachEvent("onXLE", function () {
    var A;
    if (A = this.config.show_loading) {
        if (typeof A == "object") {
            this._obj.removeChild(A);
            this.config.show_loading = true
        }
    }
});
scheduler.ical = {
    parse: function (H) {
        var E = H.match(RegExp(this.c_start + "[^\f]*" + this.c_end, ""));
        if (!E.length) {
            return
        }
        E[0] = E[0].replace(/[\r\n]+(?=[a-z \t])/g, " ");
        E[0] = E[0].replace(/\;[^:\r\n]*/g, "");
        var B = [];
        var D;
        var C = RegExp("(?:" + this.e_start + ")([^\f]*?)(?:" + this.e_end + ")", "g");
        while (D = C.exec(E)) {
            var F = {};
            var G;
            var A = /[^\r\n]+[\r\n]+/g;
            while (G = A.exec(D[1])) {
                this.parse_param(G.toString(), F)
            }
            if (F.uid && !F.id) {
                F.id = F.uid
            }
            B.push(F)
        }
        return B
    },
    parse_param: function (E, C) {
        var D = E.indexOf(":");
        if (D == -1) {
            return
        }
        var A = E.substr(0, D).toLowerCase();
        var B = E.substr(D + 1).replace(/\\\,/g, ",").replace(/[\r\n]+$/, "");
        if (A == "summary") {
            A = "text"
        } else {
            if (A == "dtstart") {
                A = "start_date";
                B = this.parse_date(B, 0, 0)
            } else {
                if (A == "dtend") {
                    A = "end_date";
                    if (C.start_date && C.start_date.getHours() == 0) {
                        B = this.parse_date(B, 24, 0)
                    } else {
                        B = this.parse_date(B, 23, 59)
                    }
                }
            }
        }
        C[A] = B
    },
    parse_date: function (G, F, D) {
        var E = G.split("T");
        if (E[1]) {
            F = E[1].substr(0, 2);
            D = E[1].substr(2, 2)
        }
        var C = E[0].substr(0, 4);
        var B = parseInt(E[0].substr(4, 2), 10) - 1;
        var A = E[0].substr(6, 2);
        if (scheduler.config.server_utc && !E[1]) {
            return new Date(Date.UTC(C, B, A, F, D))
        }
        return new Date(C, B, A, F, D)
    },
    c_start: "BEGIN:VCALENDAR",
    e_start: "BEGIN:VEVENT",
    e_end: "END:VEVENT",
    c_end: "END:VCALENDAR"
};
scheduler.form_blocks = {
    textarea: {
        render: function (B) {
            var A = (B.height || "130") + "px";
            return "<div class='dhx_cal_ltext' style='height:" + A + ";'><textarea></textarea></div>"
        },
        set_value: function (B, C, A) {
            B.firstChild.value = C || ""
        },
        get_value: function (B, A) {
            return B.firstChild.value
        },
        focus: function (B) {
            var A = B.firstChild;
            A.select();
            A.focus()
        }
    },
    select: {
        render: function (D) {
            var A = (D.height || "23") + "px";
            var C = "<div class='dhx_cal_ltext' style='height:" + A + ";'><select style='width:552px;'>";
            for (var B = 0; B < D.options.length; B++) {
                C += "<option value='" + D.options[B].key + "'>" + D.options[B].label + "</option>"
            }
            C += "</select></div>";
            return C
        },
        set_value: function (B, C, A) {
            if (typeof C == "undefined") {
                C = (B.firstChild.options[0] || {}).value
            }
            B.firstChild.value = C || ""
        },
        get_value: function (B, A) {
            return B.firstChild.value
        },
        focus: function (B) {
            var A = B.firstChild;
            if (A.select) {
                A.select()
            }
            A.focus()
        }
    },
    time: {
        render: function () {
            var A = scheduler.config;
            var E = this.date.date_part(new Date());
            var D = 24 * 60,
                G = 0;
            if (scheduler.config.limit_time_select) {
                D = 60 * A.last_hour + 1;
                G = 60 * A.first_hour;
                E.setHours(A.first_hour)
            }
            var C = "<select>";
            for (var B = G; B < D; B += this.config.time_step * 1) {
                var F = this.templates.time_picker(E);
                C += "<option value='" + B + "'>" + F + "</option>";
                E = this.date.add(E, this.config.time_step, "minute")
            }
            C += "</select> <select>";
            for (var B = 1; B < 32; B++) {
                C += "<option value='" + B + "'>" + B + "</option>"
            }
            C += "</select> <select>";
            for (var B = 0; B < 12; B++) {
                C += "<option value='" + B + "'>" + this.locale.date.month_full[B] + "</option>"
            }
            C += "</select> <select>";
            E = E.getFullYear() - 5;
            for (var B = 0; B < 10; B++) {
                C += "<option value='" + (E + B) + "'>" + (E + B) + "</option>"
            }
            C += "</select> ";
            return "<div style='height:30px; padding-top:0px; font-size:inherit;' class='dhx_cal_lsection dhx_section_time'>" + C + "<span style='font-weight:normal; font-size:10pt;'> &nbsp;&ndash;&nbsp; </span>" + C + "</div>"
        },
        set_value: function (A, I, G) {
            var J = A.getElementsByTagName("select");
            if (scheduler.config.full_day) {
                if (!A._full_day) {
                    A.previousSibling.innerHTML += "<div class='dhx_fullday_checkbox'><label><input type='checkbox' name='full_day' value='true'> " + scheduler.locale.labels.full_day + "&nbsp;</label></input></div>";
                    A._full_day = true
                }
                var H = A.previousSibling.getElementsByTagName("input")[0];
                var F = (scheduler.date.time_part(G.start_date) == 0 && scheduler.date.time_part(G.end_date) == 0 && G.end_date.valueOf() - G.start_date.valueOf() < 2 * 24 * 60 * 60 * 1000);
                H.checked = F;
                for (var B in J) {
                    J[B].disabled = H.checked
                }
                H.onclick = function () {
                    if (H.checked) {
                        var K = new Date(G.start_date);
                        var M = new Date(G.end_date);
                        scheduler.date.date_part(K);
                        M = scheduler.date.add(K, 1, "day")
                    }
                    for (var L in J) {
                        J[L].disabled = H.checked
                    }
                    C(J, 0, K || G.start_date);
                    C(J, 4, M || G.end_date)
                }
            }
            if (scheduler.config.auto_end_date && scheduler.config.event_duration) {
                function E() {
                    G.start_date = new Date(J[3].value, J[2].value, J[1].value, 0, J[0].value);
                    G.end_date.setTime(G.start_date.getTime() + (scheduler.config.event_duration * 60 * 1000));
                    C(J, 4, G.end_date)
                }
                for (var D = 0; D < 4; D++) {
                    J[D].onchange = E
                }
            }
            function C(L, K, M) {
                L[K + 0].value = Math.round((M.getHours() * 60 + M.getMinutes()) / scheduler.config.time_step) * scheduler.config.time_step;
                L[K + 1].value = M.getDate();
                L[K + 2].value = M.getMonth();
                L[K + 3].value = M.getFullYear()
            }
            C(J, 0, G.start_date);
            C(J, 4, G.end_date)
        },
        get_value: function (B, A) {
            s = B.getElementsByTagName("select");
            A.start_date = new Date(s[3].value, s[2].value, s[1].value, 0, s[0].value);
            A.end_date = new Date(s[7].value, s[6].value, s[5].value, 0, s[4].value);
            if (A.end_date <= A.start_date) {
                A.end_date = scheduler.date.add(A.start_date, scheduler.config.time_step, "minute")
            }
        },
        focus: function (A) {
            A.getElementsByTagName("select")[0].focus()
        }
    }
};
scheduler.showCover = function (A) {
    this.show_cover();
    if (A) {
        A.style.display = "block";
        var B = getOffset(this._obj);
        A.style.top = Math.round(B.top + (this._obj.offsetHeight - A.offsetHeight) / 2) + "px";
        A.style.left = Math.round(B.left + (this._obj.offsetWidth - A.offsetWidth) / 2) + "px"
    }
};
scheduler.showLightbox = function (B) {
    if (!B) {
        return
    }
    if (!this.callEvent("onBeforeLightbox", [B])) {
        return
    }
    var A = this._get_lightbox();
    this.showCover(A);
    this._fill_lightbox(B, A);
    this.callEvent("onLightbox", [B])
};
scheduler._fill_lightbox = function (H, E) {
    var D = this.getEvent(H);
    var B = E.getElementsByTagName("span");
    if (scheduler.templates.lightbox_header) {
        B[1].innerHTML = "";
        B[2].innerHTML = scheduler.templates.lightbox_header(D.start_date, D.end_date, D)
    } else {
        B[1].innerHTML = this.templates.event_header(D.start_date, D.end_date, D);
        B[2].innerHTML = (this.templates.event_bar_text(D.start_date, D.end_date, D) || "").substr(0, 70)
    }
    var F = this.config.lightbox.sections;
    for (var A = 0; A < F.length; A++) {
        var C = document.getElementById(F[A].id).nextSibling;
        var G = this.form_blocks[F[A].type];
        G.set_value.call(this, C, D[F[A].map_to], D, F[A]);
        if (F[A].focus) {
            G.focus.call(this, C)
        }
    }
    scheduler._lightbox_id = H
};
scheduler._lightbox_out = function (D) {
    var E = this.config.lightbox.sections;
    for (var B = 0; B < E.length; B++) {
        var C = document.getElementById(E[B].id).nextSibling;
        var F = this.form_blocks[E[B].type];
        var A = F.get_value.call(this, C, D, E[B]);
        if (E[B].map_to != "auto") {
            D[E[B].map_to] = A
        }
    }
    return D
};
scheduler._empty_lightbox = function () {
    var C = scheduler._lightbox_id;
    var B = this.getEvent(C);
    var A = this._get_lightbox();
    this._lightbox_out(B);
    B._timed = this.is_one_day_event(B);
    this.setEvent(B.id, B);
    this._edit_stop_event(B, true);
    this.render_view_data()
};
scheduler.hide_lightbox = function (A) {
    this.hideCover(this._get_lightbox());
    this._lightbox_id = null;
    this.callEvent("onAfterLightbox", [])
};
scheduler.hideCover = function (A) {
    if (A) {
        A.style.display = "none"
    }
    this.hide_cover()
};
scheduler.hide_cover = function () {
    if (this._cover) {
        this._cover.parentNode.removeChild(this._cover)
    }
    this._cover = null
};
scheduler.show_cover = function () {
    this._cover = document.createElement("DIV");
    this._cover.className = "dhx_cal_cover";
    document.body.appendChild(this._cover)
};
scheduler.save_lightbox = function () {
    if (this.checkEvent("onEventSave") && !this.callEvent("onEventSave", [this._lightbox_id, this._lightbox_out({
        id: this._lightbox_id
    }), this._new_event])) {
        return
    }
    this._empty_lightbox();
    this.hide_lightbox()
};
scheduler.startLightbox = function (B, A) {
    this._lightbox_id = B;
    this.showCover(A)
};
scheduler.endLightbox = function (B, A) {
    this._edit_stop_event(scheduler.getEvent(this._lightbox_id), B);
    if (B) {
        scheduler.render_view_data()
    }
    this.hideCover(A)
};
scheduler.resetLightbox = function () {
    scheduler._lightbox = null
};
scheduler.cancel_lightbox = function () {
    this.callEvent("onEventCancel", [this._lightbox_id, this._new_event]);
    this.endLightbox(false);
    this.hide_lightbox()
};
scheduler._init_lightbox_events = function () {
    this._get_lightbox().onclick = function (C) {
        var E = C ? C.target : event.srcElement;
        if (!E.className) {
            E = E.previousSibling
        }
        if (E && E.className) {
            switch (E.className) {
            case "dhx_save_btn":
                scheduler.save_lightbox();
                break;
            case "dhx_delete_btn":
                var F = scheduler.locale.labels.confirm_deleting;
                if (!F || confirm(F)) {
                    scheduler.deleteEvent(scheduler._lightbox_id);
                    scheduler._new_event = null;
                    scheduler.hide_lightbox()
                }
                break;
            case "dhx_cancel_btn":
                scheduler.cancel_lightbox();
                break;
            default:
                if (E.className.indexOf("dhx_custom_button_") != -1) {
                    var A = E.parentNode.getAttribute("index");
                    var D = scheduler.form_blocks[scheduler.config.lightbox.sections[A].type];
                    var B = E.parentNode.parentNode;
                    D.button_click(A, E, B, B.nextSibling)
                }
            }
        }
    };
    this._get_lightbox().onkeypress = function (A) {
        switch ((A || event).keyCode) {
        case scheduler.keys.edit_save:
            if ((A || event).shiftKey) {
                return
            }
            scheduler.save_lightbox();
            break;
        case scheduler.keys.edit_cancel:
            scheduler.cancel_lightbox();
            break
        }
    }
};
scheduler.setLightboxSize = function () {
    var B = this._lightbox;
    if (!B) {
        return
    }
    var A = B.childNodes[1];
    A.style.height = "0px";
    A.style.height = A.scrollHeight + "px";
    B.style.height = A.scrollHeight + 50 + "px";
    A.style.height = A.scrollHeight + "px"
};
scheduler._get_lightbox = function () {
    if (!this._lightbox) {
        var G = document.createElement("DIV");
        G.className = "dhx_cal_light";
        if (/msie|MSIE 6/.test(navigator.userAgent)) {
            G.className += " dhx_ie6"
        }
        G.style.visibility = "hidden";
        G.innerHTML = this._lightbox_template;
        document.body.insertBefore(G, document.body.firstChild);
        this._lightbox = G;
        var E = this.config.lightbox.sections;
        var C = "";
        for (var B = 0; B < E.length; B++) {
            var F = this.form_blocks[E[B].type];
            if (!F) {
                continue
            }
            E[B].id = "area_" + this.uid();
            var A = "";
            if (E[B].button) {
                A = "<div style='float:right;' class='dhx_custom_button' index='" + B + "'><div class='dhx_custom_button_" + E[B].name + "'></div><div>" + this.locale.labels["button_" + E[B].button] + "</div></div>"
            }
            C += "<div id='" + E[B].id + "' class='dhx_cal_lsection'>" + A + this.locale.labels["section_" + E[B].name] + "</div>" + F.render.call(this, E[B])
        }
        var D = G.getElementsByTagName("div");
        D[4].innerHTML = scheduler.locale.labels.icon_save;
        D[7].innerHTML = scheduler.locale.labels.icon_cancel;
        D[10].innerHTML = scheduler.locale.labels.icon_delete;
        D[1].innerHTML = C;
        this.setLightboxSize();
        this._init_lightbox_events(this);
        G.style.display = "none";
        G.style.visibility = "visible"
    }
    return this._lightbox
};
scheduler._lightbox_template = "<div class='dhx_cal_ltitle'><span class='dhx_mark'>&nbsp;</span><span class='dhx_time'></span><span class='dhx_title'></span></div><div class='dhx_cal_larea'></div><div class='dhx_btn_set'><div class='dhx_save_btn'></div><div>&nbsp;</div></div><div class='dhx_btn_set'><div class='dhx_cancel_btn'></div><div>&nbsp;</div></div><div class='dhx_btn_set' style='float:right;'><div class='dhx_delete_btn'></div><div>&nbsp;</div></div>";
scheduler._dp_init = function (A) {
    A._methods = ["setEventTextStyle", "", "changeEventId", "deleteEvent"];
    this.attachEvent("onEventAdded", function (B) {
        if (!this._loading && this.validId(B)) {
            A.setUpdated(B, true, "inserted")
        }
    });
    this.attachEvent("onBeforeEventDelete", function (C) {
        if (!this.validId(C)) {
            return
        }
        var B = A.getState(C);
        if (B == "inserted" || this._new_event) {
            A.setUpdated(C, false);
            return true
        }
        if (B == "deleted") {
            return false
        }
        if (B == "true_deleted") {
            return true
        }
        A.setUpdated(C, true, "deleted");
        return false
    });
    this.attachEvent("onEventChanged", function (B) {
        if (!this._loading && this.validId(B)) {
            A.setUpdated(B, true, "updated")
        }
    });
    A._getRowData = function (F, B) {
        var D = this.obj.getEvent(F);
        var E = {};
        for (var C in D) {
            if (C.indexOf("_") == 0) {
                continue
            }
            if (D[C] && D[C].getUTCFullYear) {
                E[C] = this.obj.templates.xml_format(D[C])
            } else {
                E[C] = D[C]
            }
        }
        return E
    };
    A._clearUpdateFlag = function () {};
    A.attachEvent("insertCallback", scheduler._update_callback);
    A.attachEvent("updateCallback", scheduler._update_callback);
    A.attachEvent("deleteCallback", function (B, C) {
        this.obj.setUserData(C, this.action_param, "true_deleted");
        this.obj.deleteEvent(C)
    })
};
scheduler.setUserData = function (C, A, B) {
    if (C) {
        this.getEvent(C)[A] = B
    } else {
        this._userdata[A] = B
    }
};
scheduler.getUserData = function (B, A) {
    return B ? this.getEvent(B)[A] : this._userdata[A]
};
scheduler.setEventTextStyle = function (C, A) {
    this.for_rendered(C, function (D) {
        D.style.cssText += ";" + A
    });
    var B = this.getEvent(C);
    B._text_style = A;
    this.event_updated(B)
};
scheduler.validId = function (A) {
    return true
};
scheduler._update_callback = function (B, C) {
    var A = scheduler.xmlNodeToJSON(B.firstChild);
    A.text = A.text || A._tagvalue;
    A.start_date = scheduler.templates.xml_date(A.start_date);
    A.end_date = scheduler.templates.xml_date(A.end_date);
    scheduler.addEvent(A)
};

/*
dhtmlxScheduler v.2.3

This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details

(c) DHTMLX Ltd.
*/