/*!
  * @license MIT
  */

!(function (t, e) {
    "object" == typeof exports && "undefined" != typeof module
        ? (module.exports = e())
        : "function" == typeof define && define.amd
            ? define(e)
            : ((t = "undefined" != typeof globalThis ? globalThis : t || self).SUNMI = e());
})(this, function () {
    "use strict";
    var t, e, n, o, i, s, r, c, u, a = function (t) {
        var e = this;
        (this.initCanvas = function (t) {
            return new Promise(function (n, o) {
                e.socket.connected
                    ? e.socket.sendMessage(
                        e.socket.getRequestData("Printer", {
                            type: "CanvasApi",
                            methodName: "initCanvas",
                            LabelStyle: t,
                        }),
                        function (t) {
                            n(t);
                        }
                    )
                    : o("Socket not connected");
            });
        }),
            (this.renderText = function (t, n) {
                return new Promise(function (o, i) {
                    e.socket.connected
                        ? e.socket.sendMessage(
                            e.socket.getRequestData("Printer", {
                                type: "CanvasApi",
                                methodName: "renderText",
                                TextStyle: n,
                                text: t,
                            }),
                            function (t) {
                                o(t);
                            }
                        )
                        : i("Socket not connected");
                });
            }),
            (this.renderBarCode = function (t, n) {
                return new Promise(function (o, i) {
                    e.socket.connected
                        ? e.socket.sendMessage(
                            e.socket.getRequestData("Printer", {
                                type: "CanvasApi",
                                methodName: "renderBarCode",
                                code: t,
                                BarcodeStyle: n,
                            }),
                            function (t) {
                                o(t);
                            }
                        )
                        : i("Socket not connected");
                });
            }),
            (this.renderQrCode = function (t, n) {
                return new Promise(function (o, i) {
                    e.socket.connected
                        ? e.socket.sendMessage(
                            e.socket.getRequestData("Printer", {
                                type: "CanvasApi",
                                methodName: "renderQrCode",
                                code: t,
                                QrStyle: n,
                            }),
                            function (t) {
                                o(t);
                            }
                        )
                        : i("Socket not connected");
                });
            }),
            (this.renderBitmap = function (t, n) {
                return new Promise(function (o, i) {
                    if (e.socket.connected)
                        try {
                            for (var s = [], r = 0; r < t.length; r += 1e4) s.push(t.slice(r, r + 1e4));
                            if (s.length > 1) {
                                var c = function (t) {
                                    setTimeout(function () {
                                        var i = t === s.length - 1;
                                        e.socket.sendMessage(
                                            e.socket.getRequestData("Printer", {
                                                type: "CanvasApi",
                                                methodName: "renderBitmap",
                                                Bitmap: s[t],
                                                BitmapStyle: n,
                                                totalPackage: s.length,
                                                currentPackage: t + 1,
                                            }),
                                            i
                                                ? function (t) {
                                                    o(t);
                                                }
                                                : void 0
                                        );
                                    }, 200);
                                };
                                for (r = 0; r < s.length; r++) c(r);
                            } else
                                e.socket.sendMessage(
                                    e.socket.getRequestData("Printer", {
                                        type: "CanvasApi",
                                        methodName: "renderBitmap",
                                        Bitmap: t,
                                        BitmapStyle: n,
                                    }),
                                    function (t) {
                                        o(t);
                                    }
                                );
                        } catch (t) {
                            i(t);
                        }
                    else i("Socket not connected");
                });
            }),
            (this.renderArea = function (t) {
                return new Promise(function (n, o) {
                    e.socket.connected
                        ? e.socket.sendMessage(
                            e.socket.getRequestData("Printer", {
                                type: "CanvasApi",
                                methodName: "renderArea",
                                AreaStyle: t,
                            }),
                            function (t) {
                                n(t);
                            }
                        )
                        : o("Socket not connected");
                });
            }),
            (this.printCanvas = function (t) {
                return new Promise(function (n, o) {
                    e.socket.connected
                        ? e.socket.sendMessage(
                            e.socket.getRequestData("Printer", {
                                type: "CanvasApi",
                                methodName: "printCanvas",
                                count: t,
                            }),
                            function (t) {
                                n(t);
                            }
                        )
                        : o("Socket not connected");
                });
            }),
            (this.socket = t),
            console.log("CanvasApi module loaded");
    },
        h = function (t) {
            var e = this;
            (this.sendEscCommand = function (t) {
                return new Promise(function (n, o) {
                    if (e.socket.connected) {
                        var i = t.join("");
                        console.log("data", i),
                            e.socket.sendMessage(
                                e.socket.getRequestData("Printer", {
                                    type: "CommandApi",
                                    methodName: "sendEscCommand",
                                    esc: i,
                                }),
                                function (t) {
                                    n(t);
                                }
                            );
                    } else o("Socket not connected");
                });
            }),
                (this.sendTsplCommand = function (t) {
                    return new Promise(function (n, o) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", {
                                    type: "CommandApi",
                                    methodName: "sendTsplCommand",
                                    tspl: t.toString(),
                                }),
                                function (t) {
                                    n(t);
                                }
                            )
                            : o("Socket not connected");
                    });
                }),
                (this.socket = t),
                console.log("CommandApi module loaded");
        },
        p = function (t) {
            var e = this;
            (this.initLine = function (t) {
                return new Promise(function (n, o) {
                    e.socket.connected
                        ? e.socket.sendMessage(
                            e.socket.getRequestData("Printer", {
                                type: "LineApi",
                                methodName: "initLine",
                                BaseStyle: t,
                            }),
                            function (t) {
                                n(t);
                            }
                        )
                        : o("Socket not connected");
                });
            }),
                (this.addText = function (t, n) {
                    return new Promise(function (o, i) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", {
                                    type: "LineApi",
                                    methodName: "addText",
                                    text: t,
                                    TextStyle: n,
                                }),
                                function (t) {
                                    o(t);
                                }
                            )
                            : i("Socket not connected");
                    });
                }),
                (this.printText = function (t, n) {
                    return new Promise(function (o, i) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", {
                                    type: "LineApi",
                                    methodName: "printText",
                                    text: t,
                                    TextStyle: n,
                                }),
                                function (t) {
                                    o(t);
                                }
                            )
                            : i("Socket not connected");
                    });
                }),
                (this.printTexts = function (t, n, o) {
                    return new Promise(function (i, s) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", {
                                    type: "LineApi",
                                    methodName: "printTexts",
                                    texts: t,
                                    colsWidthArrs: n,
                                    styles: o,
                                }),
                                function (t) {
                                    i(t);
                                }
                            )
                            : s("Socket not connected");
                    });
                }),
                (this.printBarCode = function (t, n) {
                    return new Promise(function (o, i) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", {
                                    type: "LineApi",
                                    methodName: "printBarCode",
                                    code: t,
                                    BarcodeStyle: n,
                                }),
                                function (t) {
                                    o(t);
                                }
                            )
                            : i("Socket not connected");
                    });
                }),
                (this.printQrCode = function (t, n) {
                    return new Promise(function (o, i) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", {
                                    type: "LineApi",
                                    methodName: "printQrCode",
                                    code: t,
                                    QrStyle: n,
                                }),
                                function (t) {
                                    o(t);
                                }
                            )
                            : i("Socket not connected");
                    });
                }),
                (this.printBitmap = function (t, n) {
                    return new Promise(function (o, i) {
                        if (e.socket.connected)
                            try {
                                for (var s = [], r = 0; r < t.length; r += 1e4) s.push(t.slice(r, r + 1e4));
                                if (s.length > 1) {
                                    var c = function (t) {
                                        setTimeout(function () {
                                            var i = t === s.length - 1;
                                            e.socket.sendMessage(
                                                e.socket.getRequestData("Printer", {
                                                    type: "LineApi",
                                                    methodName: "printBitmap",
                                                    Bitmap: s[t],
                                                    BitmapStyle: n,
                                                    totalPackage: s.length,
                                                    currentPackage: t + 1,
                                                }),
                                                i
                                                    ? function (t) {
                                                        o(t);
                                                    }
                                                    : void 0
                                            );
                                        }, 200);
                                    };
                                    for (r = 0; r < s.length; r++) c(r);
                                } else
                                    e.socket.sendMessage(
                                        e.socket.getRequestData("Printer", {
                                            type: "LineApi",
                                            methodName: "printBitmap",
                                            Bitmap: t,
                                            BitmapStyle: n,
                                        }),
                                        function (t) {
                                            o(t);
                                        }
                                    );
                            } catch (t) {
                                i(t);
                            }
                        else i("Socket not connected");
                    });
                }),
                (this.printDividingLine = function (t, n) {
                    return new Promise(function (o, i) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", {
                                    type: "LineApi",
                                    methodName: "printDividingLine",
                                    DividingLine: t,
                                    offset: n,
                                }),
                                function (t) {
                                    o(t);
                                }
                            )
                            : i("Socket not connected");
                    });
                }),
                (this.autoOut = function () {
                    return new Promise(function (t, n) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", { type: "LineApi", methodName: "autoOut" }),
                                function (e) {
                                    t(e);
                                }
                            )
                            : n("Socket not connected");
                    });
                }),
                (this.enableTransMode = function (t) {
                    return new Promise(function (n, o) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", {
                                    type: "LineApi",
                                    methodName: "enableTransMode",
                                    enable: t,
                                }),
                                function (t) {
                                    n(t);
                                }
                            )
                            : o("Socket not connected");
                    });
                }),
                (this.printTrans = function () {
                    return new Promise(function (t, n) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", { type: "LineApi", methodName: "printTrans" }),
                                function (e) {
                                    t(e);
                                }
                            )
                            : n("Socket not connected");
                    });
                }),
                (this.socket = t),
                console.log("LineApi module loaded");
        },
        l = function (t) {
            var e = this;
            (this.getStatus = function () {
                return new Promise(function (t, n) {
                    e.socket.connected
                        ? e.socket.sendMessage(
                            e.socket.getRequestData("Printer", { type: "QueryApi", methodName: "getStatus" }),
                            function (e) {
                                t(e);
                            }
                        )
                        : n("Socket not connected");
                });
            }),
                (this.getInfo = function (t) {
                    return new Promise(function (n, o) {
                        e.socket.connected
                            ? e.socket.sendMessage(
                                e.socket.getRequestData("Printer", {
                                    type: "QueryApi",
                                    methodName: "getInfo",
                                    PrinterInfo: t,
                                }),
                                function (t) {
                                    n(t);
                                }
                            )
                            : o("Socket not connected");
                    });
                }),
                (this.socket = t),
                console.log("QueryApi module loaded");
        },
        d = function (t) {
            (this.helloWorld = function () {
                console.log("Hello, World!");
            }),
                console.log("Printer module loaded"),
                (this.queryApi = new l(t)),
                (this.lineApi = new p(t)),
                (this.canvasApi = new a(t)),
                (this.commandApi = new h(t));
        },
        f = (function () {
            function t(t) {
                void 0 === t && (t = "ws://localhost:7070/ws"),
                    console.log("ws://localhost:7070/ws"),
                    (this.socket = new WebSocket(t)),
                    (this.connected = !1),
                    (this.eventsCallback = {}),
                    this.initializeEventListeners();
            }
            return (
                (t.prototype.initializeEventListeners = function () {
                    var t = this;
                    this.socket.addEventListener("open", function () {
                        console.log("Connected to WebSocket server"), (t.connected = !0);
                    }),
                        this.socket.addEventListener("error", function (t) {
                            console.error("Connection error:", t);
                        }),
                        this.socket.addEventListener("close", function (e) {
                            console.log("Disconnected:", e.reason), (t.connected = !1);
                        }),
                        this.socket.addEventListener("message", function (e) {
                            try {
                                var n = JSON.parse(e.data),
                                    o = n.code,
                                    i = n.data,
                                    s = n.messageId;
                                if ((console.log("1111", n), console.log("2222", o, i, s), 1 === o)) {
                                    var r = t.eventsCallback[s];
                                    r && (r(i), delete t.eventsCallback[s]);
                                } else console.log("code不为1");
                            } catch (t) {
                                console.log("返回格式解析错误");
                            }
                        });
                }),
                (t.prototype.getSocket = function () {
                    return this.socket;
                }),
                (t.prototype.sendMessage = function (t, e) {
                    var n = JSON.stringify(t);
                    this.socket.send(n), e && "function" == typeof e && (this.eventsCallback[t.messageId] = e);
                }),
                (t.prototype.on = function (t, e) { }),
                (t.prototype.disconnect = function () {
                    this.socket.close();
                }),
                (t.prototype.generateMessageId = function () {
                    return Date.now().toString();
                }),
                (t.prototype.getRequestData = function (t, e) {
                    return { module: t, data: e, messageId: this.generateMessageId() };
                }),
                t
            );
        })(),
        g = (function () {
            function t(t, e) {
                (this.code = t), (this.name = e);
            }
            return (
                (t.prototype.getCode = function () {
                    return this.code;
                }),
                (t.prototype.getName = function () {
                    return this.name;
                }),
                (t.valueOf = function (e) {
                    var n = [
                        t.UPCA,
                        t.UPCE,
                        t.EAN13,
                        t.EAN8,
                        t.CODE39,
                        t.ITF,
                        t.CODABAR,
                        t.CODE93,
                        t.CODE128,
                        t.EAN128,
                        t.CODE128A,
                        t.ITF_C,
                        t.CODE39_S,
                        t.CODE39_C,
                        t.EAN13_2,
                        t.UPCA_2,
                        t.UPCA_5,
                        t.EAN13_5,
                        t.EAN8_2,
                        t.EAN8_5,
                        t.UPCE_2,
                        t.UPCE_5,
                    ];
                    return e >= 0 && e < n.length ? n[e].getName() : "";
                }),
                (t.UPCA = new t(0, "UPCA")),
                (t.UPCE = new t(1, "UPCE")),
                (t.EAN13 = new t(2, "EAN13")),
                (t.EAN8 = new t(3, "EAN8")),
                (t.CODE39 = new t(4, "39")),
                (t.ITF = new t(5, "25")),
                (t.CODABAR = new t(6, "CODA")),
                (t.CODE93 = new t(7, "93")),
                (t.CODE128 = new t(8, "128M")),
                (t.EAN128 = new t(9, "EAN128")),
                (t.CODE128A = new t(10, "128")),
                (t.ITF_C = new t(11, "25C")),
                (t.CODE39_S = new t(12, "39S")),
                (t.CODE39_C = new t(13, "39C")),
                (t.EAN13_2 = new t(14, "EAN13+2")),
                (t.UPCA_2 = new t(15, "UPCA+2")),
                (t.UPCA_5 = new t(16, "UPCA+5")),
                (t.EAN13_5 = new t(17, "EAN13+5")),
                (t.EAN8_2 = new t(18, "EAN8+2")),
                (t.EAN8_5 = new t(19, "EAN8+5")),
                (t.UPCE_2 = new t(20, "UPCE+2")),
                (t.UPCE_5 = new t(21, "UPCE+5")),
                t
            );
        })();
    !(function (t) {
        (t.DEFAULT = "DEFAULT"), (t.LEFT = "LEFT"), (t.CENTER = "CENTER"), (t.RIGHT = "RIGHT");
    })(t || (t = {})),
        (function (t) {
            (t.L = "L"), (t.M = "M"), (t.Q = "Q"), (t.H = "H");
        })(e || (e = {})),
        (function (t) {
            (t.BINARIZATION = "BINARIZATION"), (t.DITHERING = "DITHERING");
        })(n || (n = {})),
        (function (t) {
            (t.EMPTY = "EMPTY"), (t.SOLID = "SOLID"), (t.DOTTED = "DOTTED");
        })(o || (o = {})),
        (function (t) {
            (t.ROTATE_0 = "ROTATE_0"),
                (t.ROTATE_90 = "ROTATE_90"),
                (t.ROTATE_180 = "ROTATE_180"),
                (t.ROTATE_270 = "ROTATE_270");
        })(i || (i = {})),
        (function (t) {
            (t.HIDE = "HIDE"), (t.POS_ONE = "POS_ONE"), (t.POS_TWO = "POS_TWO"), (t.POS_THREE = "POS_THREE");
        })(s || (s = {})),
        (function (t) {
            (t.RECT_FILL = "RECT_FILL"),
                (t.RECT_WHITE = "RECT_WHITE"),
                (t.RECT_REVERSE = "RECT_REVERSE"),
                (t.BOX = "BOX"),
                (t.CIRCLE = "CIRCLE"),
                (t.OVAL = "OVAL"),
                (t.PATH = "PATH");
        })(r || (r = {})),
        (function (t) {
            (t.BLACK = "BLACK"), (t.RED = "RED");
        })(c || (c = {})),
        (function (t) {
            (t.ID = "ID"),
                (t.NAME = "NAME"),
                (t.VERSION = "VERSION"),
                (t.DISTANCE = "DISTANCE"),
                (t.CUTTER = "CUTTER"),
                (t.HOT = "HOT"),
                (t.DENSITY = "DENSITY"),
                (t.TYPE = "TYPE"),
                (t.PAPER = "PAPER");
        })(u || (u = {}));
    var y = Object.freeze({
        __proto__: null,
        get Align() {
            return t;
        },
        get ErrorLevel() {
            return e;
        },
        get ImageAlgorithm() {
            return n;
        },
        get DividingLine() {
            return o;
        },
        get Rotate() {
            return i;
        },
        get HumanReadable() {
            return s;
        },
        get Shape() {
            return r;
        },
        get RenderColor() {
            return c;
        },
        get PrinterInfo() {
            return u;
        },
        Symbology: g,
    }),
        m = (function () {
            function t() {
                (this.width = 0),
                    (this.height = 0),
                    (this.posX = 0),
                    (this.posY = 0),
                    (this.align = 0),
                    (this.renderColor = 0);
            }
            return (
                (t.prototype.setAlign = function (t) {
                    return (this.align = t), this;
                }),
                (t.prototype.setWidth = function (t) {
                    return (this.width = t), this;
                }),
                (t.prototype.setHeight = function (t) {
                    return (this.height = t), this;
                }),
                (t.prototype.setPosX = function (t) {
                    return (this.posX = t), this;
                }),
                (t.prototype.setPosY = function (t) {
                    return (this.posY = t), this;
                }),
                (t.prototype.setRenderColor = function (t) {
                    return (this.renderColor = t), this;
                }),
                (t.getStyle = function () {
                    return new t();
                }),
                t
            );
        })(),
        k = (function () {
            function t() {
                (this.textSize = 24),
                    (this.textWidthRatio = 0),
                    (this.textHeightRatio = 0),
                    (this.textSpace = 0),
                    (this.enableUnderline = !1),
                    (this.enableStrikethrough = !1),
                    (this.enableItalics = !1),
                    (this.enableInvert = !1),
                    (this.enableAntiColor = !1),
                    (this.enableBold = !1),
                    (this.customFont = ""),
                    (this.width = 0),
                    (this.height = 0),
                    (this.posX = 0),
                    (this.posY = 0),
                    (this.align = 0),
                    (this.rotate = 0);
            }
            return (
                (t.prototype.setTextSize = function (t) {
                    return (this.textSize = t), this;
                }),
                (t.prototype.setTextWidthRatio = function (t) {
                    return (this.textWidthRatio = t), this;
                }),
                (t.prototype.setTextHeightRatio = function (t) {
                    return (this.textHeightRatio = t), this;
                }),
                (t.prototype.setTextSpace = function (t) {
                    return (this.textSpace = t), this;
                }),
                (t.prototype.setEnableUnderline = function (t) {
                    return (this.enableUnderline = t), this;
                }),
                (t.prototype.setEnableStrikethrough = function (t) {
                    return (this.enableStrikethrough = t), this;
                }),
                (t.prototype.setEnableItalics = function (t) {
                    return (this.enableItalics = t), this;
                }),
                (t.prototype.setEnableInvert = function (t) {
                    return (this.enableInvert = t), this;
                }),
                (t.prototype.setEnableAntiColor = function (t) {
                    return (this.enableAntiColor = t), this;
                }),
                (t.prototype.setEnableBold = function (t) {
                    return (this.enableBold = t), this;
                }),
                (t.prototype.setPosX = function (t) {
                    return (this.posX = t), this;
                }),
                (t.prototype.setPosY = function (t) {
                    return (this.posY = t), this;
                }),
                (t.prototype.setWidth = function (t) {
                    return (this.width = t), this;
                }),
                (t.prototype.setHeight = function (t) {
                    return (this.height = t), this;
                }),
                (t.prototype.setAlign = function (t) {
                    return (this.align = t), this;
                }),
                (t.prototype.setRotate = function (t) {
                    return (this.rotate = t), this;
                }),
                (t.prototype.setFont = function (t) {
                    return (this.customFont = t), this;
                }),
                (t.prototype.setRenderColor = function (t) {
                    return (this.renderColor = t), this;
                }),
                (t.getStyle = function () {
                    return new t();
                }),
                t
            );
        })(),
        E = (function () {
            function t() {
                (this.dotWidth = 2),
                    (this.barHeight = 162),
                    (this.readable = 0),
                    (this.symbology = 8),
                    (this.width = -1),
                    (this.height = -1),
                    (this.posX = 0),
                    (this.posY = 0),
                    (this.align = 0),
                    (this.rotate = 0);
            }
            return (
                (t.prototype.setDotWidth = function (t) {
                    return (this.dotWidth = t), this;
                }),
                (t.prototype.setBarHeight = function (t) {
                    return (this.barHeight = t), this;
                }),
                (t.prototype.setReadable = function (t) {
                    return (this.readable = t), this;
                }),
                (t.prototype.setSymbology = function (t) {
                    return (this.symbology = t.getCode()), this;
                }),
                (t.prototype.setWidth = function (t) {
                    return (this.width = t), this;
                }),
                (t.prototype.setHeight = function (t) {
                    return (this.height = t), this;
                }),
                (t.prototype.setPosX = function (t) {
                    return (this.posX = t), this;
                }),
                (t.prototype.setPosY = function (t) {
                    return (this.posY = t), this;
                }),
                (t.prototype.setAlign = function (t) {
                    return (this.align = t), this;
                }),
                (t.prototype.setRotate = function (t) {
                    return (this.rotate = t), this;
                }),
                (t.prototype.format = function () {
                    return this;
                }),
                (t.getStyle = function () {
                    return new t();
                }),
                t
            );
        })(),
        C = (function () {
            function t() {
                (this.dot = 4),
                    (this.errorLevel = 0),
                    (this.symbology = 1),
                    (this.width = -1),
                    (this.height = -1),
                    (this.posX = 0),
                    (this.posY = 0),
                    (this.align = 0),
                    (this.rotate = 0);
            }
            return (
                (t.prototype.setDot = function (t) {
                    return (this.dot = t), this;
                }),
                (t.prototype.setErrorLevel = function (t) {
                    return (this.errorLevel = t), this;
                }),
                (t.prototype.setWidth = function (t) {
                    return (this.width = t), this;
                }),
                (t.prototype.setHeight = function (t) {
                    return (this.height = t), this;
                }),
                (t.prototype.setPosX = function (t) {
                    return (this.posX = t), this;
                }),
                (t.prototype.setPosY = function (t) {
                    return (this.posY = t), this;
                }),
                (t.prototype.setRotate = function (t) {
                    return (this.rotate = t), this;
                }),
                (t.prototype.setAlign = function (t) {
                    return (this.align = t), this;
                }),
                (t.getStyle = function () {
                    return new t();
                }),
                t
            );
        })(),
        A = (function () {
            function t() {
                (this.style = 0),
                    (this.value = -1),
                    (this.width = -1),
                    (this.height = -1),
                    (this.posX = 0),
                    (this.posY = 0),
                    (this.align = 0),
                    (this.rotate = 0);
            }
            return (
                (t.prototype.setAlgorithm = function (t) {
                    return (this.style = t), this;
                }),
                (t.prototype.setValue = function (t) {
                    return (this.value = t), this;
                }),
                (t.prototype.setWidth = function (t) {
                    return (this.width = t), this;
                }),
                (t.prototype.setHeight = function (t) {
                    return (this.height = t), this;
                }),
                (t.prototype.setPosX = function (t) {
                    return (this.posX = t), this;
                }),
                (t.prototype.setPosY = function (t) {
                    return (this.posY = t), this;
                }),
                (t.prototype.setAlign = function (t) {
                    return (this.align = t), this;
                }),
                (t.getStyle = function () {
                    return new t();
                }),
                t
            );
        })(),
        P = (function () {
            function t() {
                (this.style = 0),
                    (this.endX = 50),
                    (this.endY = 50),
                    (this.thick = 1),
                    (this.posX = 0),
                    (this.posY = 0),
                    (this.width = 50),
                    (this.height = 50),
                    (this.align = 0),
                    (this.rotate = 0);
            }
            return (
                (t.prototype.setStyle = function (t) {
                    return (this.style = t), this;
                }),
                (t.prototype.setWidth = function (t) {
                    return (this.width = t), this;
                }),
                (t.prototype.setHeight = function (t) {
                    return (this.height = t), this;
                }),
                (t.prototype.setPosX = function (t) {
                    return (this.posX = t), this;
                }),
                (t.prototype.setPosY = function (t) {
                    return (this.posY = t), this;
                }),
                (t.prototype.setEndX = function (t) {
                    return (this.endX = t), this;
                }),
                (t.prototype.setEndY = function (t) {
                    return (this.endY = t), this;
                }),
                (t.prototype.setThick = function (t) {
                    return (this.thick = t), this;
                }),
                (t.getStyle = function () {
                    return new t();
                }),
                t
            );
        })(),
        S = function (t, e) {
            return (
                (S =
                    Object.setPrototypeOf ||
                    ({ __proto__: [] } instanceof Array &&
                        function (t, e) {
                            t.__proto__ = e;
                        }) ||
                    function (t, e) {
                        for (var n in e) Object.prototype.hasOwnProperty.call(e, n) && (t[n] = e[n]);
                    }),
                S(t, e)
            );
        };
    "function" == typeof SuppressedError && SuppressedError;
    var T = (function (t) {
        function e() {
            var e = t.call(this) || this;
            return (e.width = 0), (e.height = 0), (e.posX = 0), (e.posY = 0), (e.align = 0), (e.renderColor = 0), e;
        }
        return (
            (function (t, e) {
                if ("function" != typeof e && null !== e)
                    throw new TypeError("Class extends value " + String(e) + " is not a constructor or null");
                function n() {
                    this.constructor = t;
                }
                S(t, e), (t.prototype = null === e ? Object.create(e) : ((n.prototype = e.prototype), new n()));
            })(e, t),
            (e.prototype.setEnableReverse = function (t) {
                return (this.enableReverse = t), this;
            }),
            (e.prototype.setEnableMirror = function (t) {
                return (this.enableMirror = t), this;
            }),
            (e.prototype.setEnableBack = function (t) {
                return (this.enableBack = t), this;
            }),
            (e.prototype.setEnableTear = function (t) {
                return (this.enableTear = t), this;
            }),
            (e.prototype.setAlign = function (e) {
                return t.prototype.setAlign.call(this, e), (this.align = e), this;
            }),
            (e.prototype.setWidth = function (e) {
                return t.prototype.setWidth.call(this, e), (this.width = e), this;
            }),
            (e.prototype.setHeight = function (e) {
                return t.prototype.setHeight.call(this, e), (this.height = e), this;
            }),
            (e.prototype.setPosX = function (e) {
                return t.prototype.setPosX.call(this, e), (this.posX = e), this;
            }),
            (e.prototype.setPosY = function (e) {
                return t.prototype.setPosY.call(this, e), (this.posY = e), this;
            }),
            (e.prototype.setRenderColor = function (e) {
                return t.prototype.setRenderColor.call(this, e), (this.renderColor = e), this;
            }),
            (e.getStyle = function () {
                return new e();
            }),
            e
        );
    })(m);
    return (function () {
        function t() {
            (this.printer = null),
                (this.socketManager = null),
                (this.ENUM = y),
                (this.class = {
                    BaseStyle: m,
                    TextStyle: k,
                    BarcodeStyle: E,
                    QrStyle: C,
                    BitmapStyle: A,
                    AreaStyle: P,
                    LabelStyle: T,
                });
            var t = document.createElement("a");
            (t.id = "sunmi-init-link"),
                (t.href = "sunmi://com.sunmi:8888/websdk"),
                (t.style.display = "none"),
                document.body.appendChild(t);
        }
        return (
            (t.prototype.launchPrinterService = function () {
                return new Promise(function (t, e) {
                    var n = document.getElementById("sunmi-init-link");
                    null == n || n.click(),
                        n && document.body.removeChild(n),
                        setTimeout(function () {
                            t(!0);
                        }, 3e3);
                });
            }),
            (t.prototype.init = function () {
                var t = this;
                this.socketManager ||
                    ((this.socketManager = new f()),
                        this.socketManager.on("chat message", function (e) {
                            var n, o, i, s;
                            console.log("Received message:", e),
                                console.log(
                                    "this.socketManager.eventsCallback",
                                    null === (n = null == t ? void 0 : t.socketManager) || void 0 === n
                                        ? void 0
                                        : n.eventsCallback
                                );
                            var r = e.messageId;
                            console.log(
                                "this.socketManager.eventsCallback[messageId]",
                                null === (o = t.socketManager) || void 0 === o ? void 0 : o.eventsCallback[r]
                            ),
                                (null === (i = t.socketManager) || void 0 === i ? void 0 : i.eventsCallback[r]) &&
                                (null === (s = t.socketManager) || void 0 === s || s.eventsCallback[r](e),
                                    Reflect.deleteProperty(t.socketManager.eventsCallback, r));
                        }),
                        (this.printer = new d(this.socketManager)));
            }),
            t
        );
    })();
});
