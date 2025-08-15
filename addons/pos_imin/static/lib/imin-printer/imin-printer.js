/*!
  * imin-printer v1.4.0
  * (c) 2022 archiesong
  * @license MIT
  */
(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
  typeof define === 'function' && define.amd ? define(factory) :
  (global = typeof globalThis !== 'undefined' ? globalThis : global || self, global.IminPrinter = factory());
})(this, (function () { 'use strict';

  var _Vue;
  var install = function (Vue) {
    if (install.installed && _Vue === Vue) { return }
    install.installed = true;
    _Vue = Vue;

    var isDef = function (v) { return v !== void 0; };
    var registerInstance = function (vm, callVal) {
      var i = vm.$options._parentVnode;
      if (
        isDef(i) &&
        isDef((i = i.data)) &&
        isDef((i = i.registerPrinterInstance))
      ) {
        i(vm, callVal);
      }
    };
    Vue.mixin({
      beforeCreate: function beforeCreate() {
        if (!this.print) { this.print = {}; }
        if (isDef(this.$options.printer)) {
          this._printerRoot = this;
          this._printer = this.$options.printer;
        } else {
          this._printerRoot = (this.$parent && this.$parent._printerRoot) || this;
        }
        registerInstance(this, this);
      },
      destroyed: function destroyed() {
        registerInstance(this, void 0);
      },
    });
    Object.defineProperty(Vue.prototype, '$printer', {
      get: function get () {
        return this._printerRoot._printer
      }
    });
  };

  /*  */
  function assert (condition, message) {
    if (!condition) {
      throw new Error(("[imin-printer] " + message))
    }
  }

  function warn (condition, message) {
    if (!condition) {
      typeof console !== void 0 && console.warn(("[imin-printer] " + message));
    }
  }

  var PrinterType;
  (function (PrinterType) {
      PrinterType["USB"] = "USB";
      PrinterType["SPI"] = "SPI";
      PrinterType["Bluetooth"] = "Bluetooth";
  })(PrinterType || (PrinterType = {}));
  var PrinterStatus;
  (function (PrinterStatus) {
      PrinterStatus["NORMAL"] = "0";
      PrinterStatus["OPEN"] = "3";
      PrinterStatus["NOPAPERFEED"] = "7";
      PrinterStatus["PAPERRUNNINGOUT"] = "8";
      PrinterStatus["NOTCONNECTED"] = "-1";
      PrinterStatus["NOTPOWEREDON"] = "1";
      PrinterStatus["OTHERERRORS"] = "99";
  })(PrinterStatus || (PrinterStatus = {}));
  var TCPConnectProtocol;
  (function (TCPConnectProtocol) {
      TCPConnectProtocol["WEBSOCKET_WS"] = "ws://";
      TCPConnectProtocol["WEBSOCKET_WSS"] = "wss://";
      TCPConnectProtocol["HTTP"] = "http://";
      TCPConnectProtocol["HTTPS"] = "https://";
  })(TCPConnectProtocol || (TCPConnectProtocol = {}));
  var TCPConnectPrefix;
  (function (TCPConnectPrefix) {
      TCPConnectPrefix["WEBSOCKET"] = "/websocket";
      TCPConnectPrefix["HTTP"] = "/upload";
  })(TCPConnectPrefix || (TCPConnectPrefix = {}));

  /*  */
  var stringify = function (value) {
    return JSON.stringify(value)
  };
  var parse = function (value) {
    return JSON.parse(value)
  };

  var dataURItoBlob = function (base64Data) {
    var byteString = '';
    if (base64Data.split(',')[0].indexOf('base64') >= 0)
      { byteString = atob(base64Data.split(',')[1]); }
    else { byteString = decodeURIComponent(base64Data.split(',')[1]); }
    var mimeString = base64Data.split(',')[0].split(':')[1].split(';')[0];
    var ia = new Uint8Array(byteString.length);
    for (var i = 0; i < byteString.length; i++) {
      ia[i] = byteString.charCodeAt(i);
    }
    return new Blob([ia], {
      type: mimeString,
    })
  };

  var compressImg = function (source, mime) {
    var canvas = document.createElement('canvas');
    var context = canvas.getContext('2d');
    var originWidth = source.width;
    var originHeight = source.height;
    canvas.width = originWidth;
    canvas.height = originHeight;
    context.clearRect(0, 0, originWidth, originHeight);
    context.drawImage(source, 0, 0, originWidth, originHeight);
    return canvas.toDataURL(mime || 'image/png')
  };

  var getPrinterStatusText = function (key) {
    switch (key.toString()) {
      case '0':
        return 'The printer is normal'
      case '3':
        return 'Print head open'
      case '7':
        return 'No Paper Feed'
      case '8':
        return 'Paper Running Out'
      case '99':
        return 'Other errors'
      default:
        return 'The printer is not connected or powered on'
    }
  };

  /*  */
  var inBrowser = typeof window !== 'undefined';

  /*  */
  var PrinterWebSocket = function PrinterWebSocket(address) {
    this.address = address || '127.0.0.1';
    this.port = 8081;
    this.protocol = TCPConnectProtocol.WEBSOCKET_WS;
    this.prefix = TCPConnectPrefix.WEBSOCKET;
    this.isLock = false;
    this.heart_time = 3000;
    this.check_time = 3000;
    this.lock_time = 4000;
    this.callback = function () {
    };
  };
  PrinterWebSocket.prototype.connect = function connect () {
      var this$1$1 = this;

    return new Promise(function (resolve, reject) {
      var Socket = window.MozWebSocket || window.WebSocket;
      if (!Socket) { reject(assert(Socket, 'Browser does not support Websocket!')); }
      try {
        var ws = new Socket(
          ("" + (this$1$1.protocol) + (this$1$1.address) + ":" + (this$1$1.port) + (this$1$1.prefix))
        );
        ws.onopen = function (e) {
          this$1$1.heartCheck();
          if (ws.readyState === ws.OPEN) {
            resolve(true);
          } else {
            reject();
          }
        };
        ws.onclose = function (e) {
          this$1$1.reconnect();
        };
        ws.onerror = function (e) {
          this$1$1.reconnect();
        };
        ws.onmessage = function (e) {
          if (
            e.data === 'request' || (typeof e.data !== 'string' &&
            parse(e.data) &&
            parse(e.data).data &&
            parse(e.data).data.text === 'ping')
          ) {
            this$1$1.heartCheck();
          } else {
            this$1$1.callback(parse(e.data));
          }
        };
        this$1$1.ws = ws;
      } catch (error) {
        this$1$1.reconnect();
        reject(error);
      }
    })
  };
  PrinterWebSocket.prototype.sendParameter = function sendParameter (
    text,
    type,
    value,
    labelData,
    object
  ) {
    return stringify({
      data: Object.assign(
        {},
        {
          text: text !== undefined ? text : '',
          value: value !== undefined ? value : -1,
          labelData: labelData !== undefined ? labelData : {}
        },
        object ? object : {}
      ),
      type: type !== undefined ? type : 0,
    })
  };
  PrinterWebSocket.prototype.heartCheck = function heartCheck () {
      var this$1$1 = this;

    this.h_timer && clearTimeout(this.h_timer);
    this.c_timer && clearTimeout(this.c_timer);
    this.h_timer = setTimeout(function () {
      this$1$1.send(this$1$1.sendParameter('ping'));
      this$1$1.c_timer = setTimeout(function () {
        if (this$1$1.ws.readyState !== 1) {
          this$1$1.close();
        }
      }, this$1$1.check_time);
    }, this.heart_time);
  };
  PrinterWebSocket.prototype.reconnect = function reconnect () {
      var this$1$1 = this;

    if (this.isLock) { return }
    this.isLock = true;
    this.l_timer && clearTimeout(this.l_timer);
    this.l_timer = setTimeout(function () {
      this$1$1.connect();
      this$1$1.isLock = false;
    }, this.lock_time);
  };
  PrinterWebSocket.prototype.send = function send (message) {
    this.ws.send(message);
  };
  PrinterWebSocket.prototype.close = function close () {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  };

  var PrinterWebSocket$1 = PrinterWebSocket;

  /*  */
  var IminPrinter = /*@__PURE__*/(function (PrinterWebSocket) {
    function IminPrinter(url) {
      {
        warn(
          this instanceof IminPrinter,
          "Printer must be called with the new operator."
        );
      }
      PrinterWebSocket.call(this, url);
      IminPrinter.connect_type = PrinterType.SPI;
    }

    if ( PrinterWebSocket ) IminPrinter.__proto__ = PrinterWebSocket;
    IminPrinter.prototype = Object.create( PrinterWebSocket && PrinterWebSocket.prototype );
    IminPrinter.prototype.constructor = IminPrinter;
    /**
     * Initialize the printer
     * @param {string} connectType   example: USB | SPI | Bluetooth
     */
    IminPrinter.prototype.initPrinter = function initPrinter (
      connectType
    ) {
      if ( connectType === void 0 ) connectType = PrinterType.SPI;

      this.connect_type = connectType;
      this.send(this.sendParameter(connectType, 1));
    };
    /**
     * Get printer status
     * @param { string  } connectType  example: USB | SPI | Bluetooth
     */
    IminPrinter.prototype.getPrinterStatus = function getPrinterStatus (connectType) {
      var this$1$1 = this;
      if ( connectType === void 0 ) connectType = PrinterType.SPI;

      return new Promise(function (resolve) {
        this$1$1.connect_type = connectType;
        this$1$1.send(this$1$1.sendParameter(connectType, 2));
        this$1$1.callback = function (data) {
          if (data.type === 2) {
            resolve(
              Object.assign({}, data.data, {
                text: getPrinterStatusText(data.data.value),
              })
            );
          }
        };
      })
    };
    /**
     * Print and feed paper
     */
    IminPrinter.prototype.printAndLineFeed = function printAndLineFeed () {
      this.send(this.sendParameter('', 3));
    };
    /**
     * Print blank lines
     * @param {number} height  example: 0-255
     */
    IminPrinter.prototype.printAndFeedPaper = function printAndFeedPaper (height) {
      this.send(
        this.sendParameter('', 4, height <= 0 ? 0 : height >= 255 ? 255 : height)
      );
    };
    /**
     * Cutter (paper cutting) correlation
     */
    IminPrinter.prototype.partialCut = function partialCut () {
      this.send(this.sendParameter('', 5));
    };
      /**
     * Cutter (paper cutting) correlation
     */
      IminPrinter.prototype.partialCutPaper = function partialCutPaper () {
        this.send(this.sendParameter('', 5));
      };
    /**
     * Set text alignment
     * @param {number} alignment  example: 0 = left / 1 = center / 2 = right / default = 0
     */
    IminPrinter.prototype.setAlignment = function setAlignment (alignment) {
      this.send(
        this.sendParameter(
          '',
          6,
          alignment <= 0 ? 0 : alignment >= 2 ? 2 : alignment
        )
      );
    };
    /**
     * Set text size
     * @param {number} size   example: 28
     */
    IminPrinter.prototype.setTextSize = function setTextSize (size) {
      this.send(this.sendParameter('', 7, size));
    };
    /**
     * Set font
     * @param {number} typeface
     */
    IminPrinter.prototype.setTextTypeface = function setTextTypeface (typeface) {
      this.send(this.sendParameter('', 8, typeface));
    };
    /**
     * Set font style
     * @param {number} style  example: NORMAL = 0 BOLD = 1 ITALIC = 2 BOLD_ITALIC = 3
     */
    IminPrinter.prototype.setTextStyle = function setTextStyle (style) {
      this.send(
        this.sendParameter('', 9, style <= 0 ? 0 : style >= 3 ? 3 : style)
      );
    };
    /**
     * Set line spacing
     * @param {string} space
     */
    IminPrinter.prototype.setTextLineSpacing = function setTextLineSpacing (space) {
      this.send(this.sendParameter('', 10, space));
    };
    /**
     * Set print width
     * @param {number} width
     */
    IminPrinter.prototype.setTextWidth = function setTextWidth (width) {
      this.send(
        this.sendParameter('', 11, width <= 0 ? 0 : width >= 576 ? 576 : width)
      );
    };
    /**
     * Print text
     * @param {string} text
     * @param {number} type
     */
    IminPrinter.prototype.printText = function printText (text, type) {
      this.send(
        this.sendParameter(
          type !== void 0 && !type && text.charAt(text.length - 2) === '\n'
            ? text.slice(0, text.length - 1) + '\n'
            : (type !== void 0 ? text : text + '\n'),
          type !== void 0 ? 13 : 12,
          type !== void 0 ? (type <= 0 ? 0 : type >= 2 ? 2 : type) : void 0
        )
      );

    };
    /**
     * Print a row of the table (not support Arabic)
     * @param {Array} colTextArr
     * @param {Array} colWidthArr
     * @param {Array} colAlign
     * @param {number} width
     * @param {Array} size
     */
    IminPrinter.prototype.printColumnsText = function printColumnsText (
      colTextArr,
      colWidthArr,
      colAlignArr,
      size,
      width
    ) {
      this.send(
        this.sendParameter('', 14, width < 0 ? 0 : width > 576 ? 576 : width, void 0, {
          colTextArr: colTextArr,
          colWidthArr: colWidthArr,
          colAlign: colAlignArr.map(function (item) {
            return item <= 0 ? 0 : item >= 2 ? 2 : item
          }),
          size: size,
        })
      );
    };
    /**
     * Set barcode width
     * @param {number} width
     */
    IminPrinter.prototype.setBarCodeWidth = function setBarCodeWidth (width) {
      this.send(
        this.sendParameter(
          '',
          15,
          width !== void 0 ? (width <= 1 ? 1 : width >= 6 ? 6 : width) : 3
        )
      );
    };
    /**
     * Set the height of the barcode
     * @param {number} height
     */
    IminPrinter.prototype.setBarCodeHeight = function setBarCodeHeight (height) {
      this.send(
        this.sendParameter('', 16, height <= 1 ? 1 : height >= 255 ? 255 : height)
      );
    };
    /**
     * When printing barcodes, select the printing position for HRI characters
     * @param {number} position
     */
    IminPrinter.prototype.setBarCodeContentPrintPos = function setBarCodeContentPrintPos (position) {
      this.send(
        this.sendParameter(
          '',
          17,
          position <= 0 ? 0 : position >= 3 ? 3 : position
        )
      );
    };
    /**
     * Print barcode
     * @param {number} barCodeType
     * @param {string} barCodeContent
     * @param {number} alignmentMode
     */
    IminPrinter.prototype.printBarCode = function printBarCode (
      barCodeType,
      barCodeContent,
      alignmentMode
    ) {
      this.send(
        this.sendParameter(
          barCodeContent,
          alignmentMode !== void 0 ? 19 : 18,
          barCodeType <= 0 ? 0 : barCodeType >= 6 ? 6 : barCodeType,
          void 0,
          alignmentMode !== void 0
            ? {
                alignmentMode:
                  alignmentMode <= 0 ? 0 : alignmentMode >= 2 ? 2 : alignmentMode,
              }
            : {}
        )
      );
    };
    /**
     * Set the size of the QR code
     * @param {number} level
     */
    IminPrinter.prototype.setQrCodeSize = function setQrCodeSize (level) {
      this.send(
        this.sendParameter('', 20, level <= 1 ? 1 : level >= 9 ? 9 : level)
      );
    };
    /**
     * Set QR code error correction
     * @param {number} level
     */
    IminPrinter.prototype.setQrCodeErrorCorrectionLev = function setQrCodeErrorCorrectionLev (level) {
      this.send(
        this.sendParameter('', 21, level <= 48 ? 48 : level >= 51 ? 51 : level)
      );
    };
    /**
     * Set left margin of barcode and QR code
     * @param {number} marginValue
     */
    IminPrinter.prototype.setLeftMargin = function setLeftMargin (marginValue) {
      this.send(
        this.sendParameter(
          '',
          22,
          marginValue <= 0 ? 0 : marginValue >= 576 ? 576 : marginValue
        )
      );
    };
    /**
     * Printer QR code
     * @param {string} qrStr
     * @param {number} alignmentMode
     */
    IminPrinter.prototype.printQrCode = function printQrCode (qrStr, alignmentMode) {
      this.send(
        this.sendParameter(
          qrStr,
          alignmentMode !== void 0 ? 24 : 23,
          alignmentMode !== void 0
            ? alignmentMode <= 0
              ? 0
              : alignmentMode >= 2
              ? 2
              : alignmentMode
            : void 0
        )
      );
    };
    /**
     * Set paper specifications
     * @param {number} style
     */
    IminPrinter.prototype.setPageFormat = function setPageFormat (style) {
      this.send(
        this.sendParameter('', 25, style >= 1 ? 1 : 0)
      );
    };
    /**
     *  Open cash box
     */
    IminPrinter.prototype.openCashBox = function openCashBox () {
      this.send(this.sendParameter('', 100));
    };

    /**
     *  print single image
     * @param {string} bitmap
     * @param {number} alignmentMode
     */
    IminPrinter.prototype.printSingleBitmap = async function printSingleBitmap(bitmap, alignmentMode) {
      var this$1$1 = this;

      return new Promise(async (resolve, reject) => {
        var image = new Image();
        var regex = /^\s*data:([a-z]+\/[a-z0-9-+.]+(;[a-z-]+=[a-z0-9-]+)?)?(;base64)?,([a-z0-9!$&',()*+;=\-._~:@\/?%\s]*?)\s*$/i;
        if (!regex.test(bitmap)) {
          image.crossOrigin = '*';
          image.src = bitmap + "?v=" + (new Date().getTime());
        } else {
          image.src = bitmap;
        }

        image.onload = async function () {
          try {
            var formData = new FormData();
            formData.append(
              'file',
              dataURItoBlob(compressImg(image, dataURItoBlob(bitmap).type))
            );

            const response = await fetch(
              `${TCPConnectProtocol.HTTP}${this$1$1.address}:${this$1$1.port}${TCPConnectPrefix.HTTP}`,
              {
                method: 'POST',
                body: formData
              }
            );

            if (response.ok) {
              const resultValue = await response.text();
              if (resultValue) {
                await this$1$1.send(
                  this$1$1.sendParameter(
                    '',
                    alignmentMode !== void 0 ? 27 : 26,
                    alignmentMode !== void 0 ? alignmentMode : void 0
                  )
                );

                let hasBeenCalled = false;
                if (!hasBeenCalled) {
                  this$1$1.partialCut();
                  hasBeenCalled = true;
                  resolve(1);
                }
              } else {
                reject(new Error("No response data"));
              }
            } else {
              reject(new Error(`Request failed with status: ${response.status}`));
            }
          } catch (error) {
            reject(new Error(`Network request failed: ${error.message}`));
          }
        };

        image.onerror = function () {
          reject(new Error("Failed to load image"));
        };
      });
    };

    IminPrinter.prototype.partialCut = function partialCut () {
      this.send(this.sendParameter('', 5));
    };
    /**
     * set double QR size
     * @param { number} size
     */
    IminPrinter.prototype.setDoubleQRSize = function setDoubleQRSize (size) {
      this.send(this.sendParameter('', 28, size));
    };
    /**
     * set double QR1 level
     * @param {number} level
     */
    IminPrinter.prototype.setDoubleQR1Level = function setDoubleQR1Level (level) {
      this.send(this.sendParameter('', 29, level));
    };
    /**
     * set double QR1 margin left
     * @param {number} marginValue
     */
    IminPrinter.prototype.setDoubleQR1MarginLeft = function setDoubleQR1MarginLeft (marginValue) {
      this.send(this.sendParameter('', 31, marginValue));
    };
    /**
     * set double QR1 version
     * @param {number} version
     */
    IminPrinter.prototype.setDoubleQR1Version = function setDoubleQR1Version (version) {
      this.send(this.sendParameter('', 33, version));
    };
    /**
     * set double QR2 level
     * @param {number} level
     */
    IminPrinter.prototype.setDoubleQR2Level = function setDoubleQR2Level (level) {
      this.send(this.sendParameter('', 30, level));
    };
    /**
     * set double QR2 margin left
     * @param {number} marginValue
     */
    IminPrinter.prototype.setDoubleQR2MarginLeft = function setDoubleQR2MarginLeft (marginValue) {
      this.send(this.sendParameter('', 32, marginValue));
    };
    /**
     * set double QR2 version
     * @param {number} version
     */
    IminPrinter.prototype.setDoubleQR2Version = function setDoubleQR2Version (version) {
      this.send(this.sendParameter('', 34, version));
    };
    /**
     * print double QR
     * @param {Array} colTextArr
     */
    IminPrinter.prototype.printDoubleQR = function printDoubleQR (colTextArr) {
      this.send(
        this.sendParameter('', 35, void 0, void 0, {
          colTextArr: colTextArr,
        })
      );
    };

    /**
     * labelInitCanvas
     * @param {Object} labelData
     */
    IminPrinter.prototype.labelInitCanvas = function labelInitCanvas (labelData) {
      this.send(
        this.sendParameter('', 200, void 0, labelData)
      )
    };

    /**
     * labelAddText
     * @param {Object} labelData
     */
    IminPrinter.prototype.labelAddText = function labelAddText (labelData) {
      this.send(
        this.sendParameter('', 201, void 0, labelData)
      )
    };

    /**
     * labelAddBarCod
     * @param {Object} labelData
     */
    IminPrinter.prototype.labelAddBarCod = function labelAddBarCod (labelData) {
      this.send(
        this.sendParameter('', 202, void 0, labelData)
      )
    };

    /**
     * labelAddQrCode
     * @param {Object} labelData
     */
    IminPrinter.prototype.labelAddQrCode = function labelAddQrCode (labelData) {
      this.send(
        this.sendParameter('', 203, void 0, labelData)
      )
    };

      /**
     * labelAddBitmap
     * @param {Object} labelData
     */
      IminPrinter.prototype.labelAddBitmap = function labelAddBitmap (bitmap, labelData) {

        var this$1$1 = this;

      return new Promise((resolve, reject) => {
        var image = new Image();
        var regex = /^\s*data:([a-z]+\/[a-z0-9-+.]+(;[a-z-]+=[a-z0-9-]+)?)?(;base64)?,([a-z0-9!$&',()*+;=\-._~:@\/?%\s]*?)\s*$/i;
        if (!regex.test(bitmap)) {
          image.crossOrigin = '*';
          image.src = bitmap + "?v=" + (new Date().getTime());
        } else {
          image.src = bitmap;
        }

        image.onload = function () {
          var formData = new FormData();
          formData.append(
            'file',
            dataURItoBlob(compressImg(image, dataURItoBlob(bitmap).type))
          );

          var XHR = null;
          if (window.XMLHttpRequest) {
            XHR = new XMLHttpRequest();
          } else if (window.ActiveXObject) {
            XHR = new ActiveXObject('Microsoft.XMLHTTP');
          } else {
            reject(new Error("XMLHttpRequest is not supported"));
            return;
          }

          XHR.open(
            'POST',
            ("" + (TCPConnectProtocol.HTTP) + (this$1$1.address) + ":" + (this$1$1.port) + (TCPConnectPrefix.HTTP))
          );

          XHR.onreadystatechange = function () {
            if (XHR.readyState === 4) {
              if (XHR.status === 200) {
                var resultValue = XHR.responseText;
                if (resultValue) {
                  this$1$1.send(
                    this$1$1.sendParameter(
                      '',
                      204,
                      void 0,
                      labelData
                    )
                  );

                  this$1$1.callback = (data) => {
                    resolve(data.data.value);
                  };
                } else {
                  reject(new Error("No response data"));
                }
              } else {
                reject(new Error("Request failed with status: " + XHR.status));
              }
              XHR = null;
            }
          };

          XHR.send(formData);
        };

        image.onerror = function () {
          reject(new Error("Failed to load image"));
        };
      });
      };

      /**
     * labelAddArea
     * @param {Object} labelData
     */
      IminPrinter.prototype.labelAddArea = function labelAddArea (labelData) {
        this.send(
          this.sendParameter('', 205, void 0, labelData)
        )
      };

      /**
     * labelPrintCanvas
     * @param {Object} labelData
     */
      IminPrinter.prototype.labelPrintCanvas = function labelPrintCanvas (labelData) {
        this.send(
          this.sendParameter('', 206, void 0, labelData)
        )
      };

    /**
     * labelLearning
     * @param {Object} labelData
     */
          IminPrinter.prototype.labelLearning = function labelLearning (labelData) {
            this.send(
              this.sendParameter('', 207, void 0, labelData)
            )
          };

      /**
     * setPrintMode
     * @param {Object} labelData
     */
       IminPrinter.prototype.setPrintMode = function setPrintMode (labelData) {
        this.send(
          this.sendParameter('', 208, void 0, labelData)
        )
      };

    /**
     * getPrintModel
     * @param {Object} labelData
     */
          IminPrinter.prototype.getPrintModel = function getPrintModel (labelData) {
            this.send(
              this.sendParameter('', 209, void 0, labelData)
            )
          };
    /**
     * printLabelBitmap
     * @param {Object} labelData
     */
    IminPrinter.prototype.printLabelBitmap = function printLabelBitmap (bitmap, labelData) {

      var this$1$1 = this;

    return new Promise((resolve, reject) => {
      var image = new Image();
      var regex = /^\s*data:([a-z]+\/[a-z0-9-+.]+(;[a-z-]+=[a-z0-9-]+)?)?(;base64)?,([a-z0-9!$&',()*+;=\-._~:@\/?%\s]*?)\s*$/i;
      if (!regex.test(bitmap)) {
        image.crossOrigin = '*';
        image.src = bitmap + "?v=" + (new Date().getTime());
      } else {
        image.src = bitmap;
      }

      image.onload = function () {
        var formData = new FormData();
        formData.append(
          'file',
          dataURItoBlob(compressImg(image, dataURItoBlob(bitmap).type))
        );

        var XHR = null;
        if (window.XMLHttpRequest) {
          XHR = new XMLHttpRequest();
        } else if (window.ActiveXObject) {
          XHR = new ActiveXObject('Microsoft.XMLHTTP');
        } else {
          reject(new Error("XMLHttpRequest is not supported"));
          return;
        }

        XHR.open(
          'POST',
          ("" + (TCPConnectProtocol.HTTP) + (this$1$1.address) + ":" + (this$1$1.port) + (TCPConnectPrefix.HTTP))
        );

        XHR.onreadystatechange = function () {
          if (XHR.readyState === 4) {
            if (XHR.status === 200) {
              var resultValue = XHR.responseText;
              if (resultValue) {
                this$1$1.send(
                  this$1$1.sendParameter(
                    '',
                    210,
                    void 0,
                    labelData
                  )
                );

                this$1$1.callback = (data) => {
                  resolve(data.data.value);
                };
              } else {
                reject(new Error("No response data"));
              }
            } else {
              reject(new Error("Request failed with status: " + XHR.status));
            }
            XHR = null;
          }
        };

        XHR.send(formData);
      };

      image.onerror = function () {
        reject(new Error("Failed to load image"));
      };
    });
    };



    return IminPrinter;
  }(PrinterWebSocket$1));
  IminPrinter.install = install;
  IminPrinter.version = '1.4.0';
  if (inBrowser && window.Vue) {
    window.Vue.use(IminPrinter);
  }

  return IminPrinter;

}));
