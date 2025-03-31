import { _t } from "@web/core/l10n/translation";
import { makeErrorFromResponse, ConnectionLostError } from "@web/core/network/rpc";
import { browser } from "@web/core/browser/browser";

/* eslint-disable */
/**
 * The following sections are from libraries, they have been slightly modified
 * to allow patching them during tests, but should not be linted, so that we can
 * keep a minimal diff that is easy to reapply when upgrading
 */
// -----------------------------------------------------------------------------
// Content Disposition Library
// -----------------------------------------------------------------------------

/*
(The MIT License)
Copyright (c) 2014-2017 Douglas Christopher Wilson
Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:
The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

/**
 * Stripped down to only parsing/decoding.
 * Slightly changed for export and lint compliance
 */

/**
 * RegExp to match percent encoding escape.
 * @private
 */
const HEX_ESCAPE_REPLACE_REGEXP = /%([0-9A-Fa-f]{2})/g;

/**
 * RegExp to match non-latin1 characters.
 * @private
 */
const NON_LATIN1_REGEXP = /[^\x20-\x7e\xa0-\xff]/g;

/**
 * RegExp to match quoted-pair in RFC 2616
 *
 * quoted-pair = "\" CHAR
 * CHAR        = <any US-ASCII character (octets 0 - 127)>
 * @private
 */
const QESC_REGEXP = /\\([\u0000-\u007f])/g;

/**
 * RegExp for various RFC 2616 grammar
 *
 * parameter     = token "=" ( token | quoted-string )
 * token         = 1*<any CHAR except CTLs or separators>
 * separators    = "(" | ")" | "<" | ">" | "@"
 *               | "," | ";" | ":" | "\" | <">
 *               | "/" | "[" | "]" | "?" | "="
 *               | "{" | "}" | SP | HT
 * quoted-string = ( <"> *(qdtext | quoted-pair ) <"> )
 * qdtext        = <any TEXT except <">>
 * quoted-pair   = "\" CHAR
 * CHAR          = <any US-ASCII character (octets 0 - 127)>
 * TEXT          = <any OCTET except CTLs, but including LWS>
 * LWS           = [CRLF] 1*( SP | HT )
 * CRLF          = CR LF
 * CR            = <US-ASCII CR, carriage return (13)>
 * LF            = <US-ASCII LF, linefeed (10)>
 * SP            = <US-ASCII SP, space (32)>
 * HT            = <US-ASCII HT, horizontal-tab (9)>
 * CTL           = <any US-ASCII control character (octets 0 - 31) and DEL (127)>
 * OCTET         = <any 8-bit sequence of data>
 * @private
 */
const PARAM_REGEXP = /;[\x09\x20]*([!#$%&'*+.0-9A-Z^_`a-z|~-]+)[\x09\x20]*=[\x09\x20]*("(?:[\x20!\x23-\x5b\x5d-\x7e\x80-\xff]|\\[\x20-\x7e])*"|[!#$%&'*+.0-9A-Z^_`a-z|~-]+)[\x09\x20]*/g;

/**
 * RegExp for various RFC 5987 grammar
 *
 * ext-value     = charset  "'" [ language ] "'" value-chars
 * charset       = "UTF-8" / "ISO-8859-1" / mime-charset
 * mime-charset  = 1*mime-charsetc
 * mime-charsetc = ALPHA / DIGIT
 *               / "!" / "#" / "$" / "%" / "&"
 *               / "+" / "-" / "^" / "_" / "`"
 *               / "{" / "}" / "~"
 * language      = ( 2*3ALPHA [ extlang ] )
 *               / 4ALPHA
 *               / 5*8ALPHA
 * extlang       = *3( "-" 3ALPHA )
 * value-chars   = *( pct-encoded / attr-char )
 * pct-encoded   = "%" HEXDIG HEXDIG
 * attr-char     = ALPHA / DIGIT
 *               / "!" / "#" / "$" / "&" / "+" / "-" / "."
 *               / "^" / "_" / "`" / "|" / "~"
 * @private
 */
const EXT_VALUE_REGEXP = /^([A-Za-z0-9!#$%&+\-^_`{}~]+)'(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}|[A-Za-z]{4,8}|)'((?:%[0-9A-Fa-f]{2}|[A-Za-z0-9!#$&+.^_`|~-])+)$/;

/**
 * RegExp for various RFC 6266 grammar
 *
 * disposition-type = "inline" | "attachment" | disp-ext-type
 * disp-ext-type    = token
 * disposition-parm = filename-parm | disp-ext-parm
 * filename-parm    = "filename" "=" value
 *                  | "filename*" "=" ext-value
 * disp-ext-parm    = token "=" value
 *                  | ext-token "=" ext-value
 * ext-token        = <the characters in token, followed by "*">
 * @private
 */
const DISPOSITION_TYPE_REGEXP = /^([!#$%&'*+.0-9A-Z^_`a-z|~-]+)[\x09\x20]*(?:$|;)/;

/**
 * Decode a RFC 6987 field value (gracefully).
 *
 * @param {string} str
 * @return {string}
 * @private
 */
function decodefield(str) {
    const match = EXT_VALUE_REGEXP.exec(str);

    if (!match) {
        throw new TypeError("invalid extended field value");
    }

    const charset = match[1].toLowerCase();
    const encoded = match[2];

    switch (charset) {
        case "iso-8859-1":
            return encoded
                .replace(HEX_ESCAPE_REPLACE_REGEXP, pdecode)
                .replace(NON_LATIN1_REGEXP, "?");
        case "utf-8":
            return decodeURIComponent(encoded);
        default:
            throw new TypeError("unsupported charset in extended field");
    }
}

/**
 * Parse Content-Disposition header string.
 *
 * @param {string} string
 * @return {ContentDisposition}
 * @public
 */
function parse(string) {
    if (!string || typeof string !== "string") {
        throw new TypeError("argument string is required");
    }

    let match = DISPOSITION_TYPE_REGEXP.exec(string);

    if (!match) {
        throw new TypeError("invalid type format");
    }

    // normalize type
    let index = match[0].length;
    const type = match[1].toLowerCase();

    let key;
    const names = [];
    const params = {};
    let value;

    // calculate index to start at
    index = PARAM_REGEXP.lastIndex = match[0].substr(-1) === ";" ? index - 1 : index;

    // match parameters
    while ((match = PARAM_REGEXP.exec(string))) {
        if (match.index !== index) {
            throw new TypeError("invalid parameter format");
        }

        index += match[0].length;
        key = match[1].toLowerCase();
        value = match[2];

        if (names.indexOf(key) !== -1) {
            throw new TypeError("invalid duplicate parameter");
        }

        names.push(key);

        if (key.indexOf("*") + 1 === key.length) {
            // decode extended value
            key = key.slice(0, -1);
            value = decodefield(value);

            // overwrite existing value
            params[key] = value;
            continue;
        }

        if (typeof params[key] === "string") {
            continue;
        }

        if (value[0] === '"') {
            // remove quotes and escapes
            value = value.substr(1, value.length - 2).replace(QESC_REGEXP, "$1");
        }

        params[key] = value;
    }

    if (index !== -1 && index !== string.length) {
        throw new TypeError("invalid parameter format");
    }

    return new ContentDisposition(type, params);
}

/**
 * Percent decode a single character.
 *
 * @param {string} str
 * @param {string} hex
 * @return {string}
 * @private
 */
function pdecode(str, hex) {
    return String.fromCharCode(parseInt(hex, 16));
}

/**
 * Class for parsed Content-Disposition header for v8 optimization
 *
 * @public
 * @param {string} type
 * @param {object} parameters
 * @constructor
 */
function ContentDisposition(type, parameters) {
    this.type = type;
    this.parameters = parameters;
}

// -----------------------------------------------------------------------------
// download.js library
// -----------------------------------------------------------------------------

/*
MIT License
Copyright (c) 2016 dandavis
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
 */

/**
 * download.js v4.2, by dandavis; 2008-2018. [MIT] see http://danml.com/download.html for tests/usage
 * v1 landed a FF+Chrome compat way of downloading strings to local un-named files, upgraded to use a hidden frame and optional mime
 * v2 added named files via a[download], msSaveBlob, IE (10+) support, and window.URL support for larger+faster saves than dataURLs
 * v3 added dataURL and Blob Input, bind-toggle arity, and legacy dataURL fallback was improved with force-download mime and base64 support. 3.1 improved safari handling.
 * v4 adds AMD/UMD, commonJS, and plain browser support
 * v4.1 adds url download capability via solo URL argument (same domain/CORS only)
 * v4.2 adds semantic variable names, long (over 2MB) dataURL support, and hidden by default temp anchors
 *
 * Slightly modified for export and lint compliance
 *
 * @param {Blob | File | String} data
 * @param {String} [filename]
 * @param {String} [mimetype]
 */
function _download(data, filename, mimetype) {
    let self = window, // this script is only for browsers anyway...
        defaultMime = "application/octet-stream", // this default mime also triggers iframe downloads
        mimeType = mimetype || defaultMime,
        payload = data,
        url = !filename && !mimetype && payload,
        anchor = document.createElement("a"),
        toString = function (a) {
            return String(a);
        },
        myBlob = self.Blob || self.MozBlob || self.WebKitBlob || toString,
        fileName = filename || "download",
        blob,
        reader;
    myBlob = myBlob.call ? myBlob.bind(self) : Blob;

    if (String(this) === "true") {
        //reverse arguments, allowing download.bind(true, "text/xml", "export.xml") to act as a callback
        payload = [payload, mimeType];
        mimeType = payload[0];
        payload = payload[1];
    }

    if (url && url.length < 2048) {
        // if no filename and no mime, assume a url was passed as the only argument
        fileName = url.split("/").pop().split("?")[0];
        anchor.href = url; // assign href prop to temp anchor
        if (anchor.href.indexOf(url) !== -1) {
            // if the browser determines that it's a potentially valid url path:
            return new Promise((resolve, reject) => {
                let xhr = new browser.XMLHttpRequest();
                xhr.open("GET", url, true);
                configureBlobDownloadXHR(xhr, {
                    onSuccess: resolve,
                    onFailure: reject,
                    url
                });
                xhr.send();
            });
        }
    }

    //go ahead and download dataURLs right away
    if (/^data:[\w+\-]+\/[\w+\-]+[,;]/.test(payload)) {
        if (payload.length > 1024 * 1024 * 1.999 && myBlob !== toString) {
            payload = dataUrlToBlob(payload);
            mimeType = payload.type || defaultMime;
        } else {
            return navigator.msSaveBlob // IE10 can't do a[download], only Blobs:
                ? navigator.msSaveBlob(dataUrlToBlob(payload), fileName)
                : saver(payload); // everyone else can save dataURLs un-processed
        }
    }

    blob = payload instanceof myBlob ? payload : new myBlob([payload], { type: mimeType });

    function dataUrlToBlob(strUrl) {
        let parts = strUrl.split(/[:;,]/),
            type = parts[1],
            decoder = parts[2] === "base64" ? atob : decodeURIComponent,
            binData = decoder(parts.pop()),
            mx = binData.length,
            i = 0,
            uiArr = new Uint8Array(mx);

        for (i; i < mx; ++i) {
            uiArr[i] = binData.charCodeAt(i);
        }

        return new myBlob([uiArr], { type });
    }

    function saver(url, winMode) {
        if ("download" in anchor) {
            //html5 A[download]
            anchor.href = url;
            anchor.setAttribute("download", fileName);
            anchor.className = "download-js-link";
            anchor.innerText = _t("downloading...");
            anchor.style.display = "none";
            anchor.target = "_blank";
            document.body.appendChild(anchor);
            setTimeout(() => {
                anchor.click();
                document.body.removeChild(anchor);
                if (winMode === true) {
                    setTimeout(() => {
                        self.URL.revokeObjectURL(anchor.href);
                    }, 250);
                }
            }, 66);
            return true;
        }

        // handle non-a[download] safari as best we can:
        if (/(Version)\/(\d+)\.(\d+)(?:\.(\d+))?.*Safari\//.test(navigator.userAgent)) {
            url = url.replace(/^data:([\w\/\-+]+)/, defaultMime);
            if (!window.open(url)) {
                // popup blocked, offer direct download:
                if (
                    confirm(
                        "Displaying New Document\n\nUse Save As... to download, then click back to return to this page."
                    )
                ) {
                    location.href = url;
                }
            }
            return true;
        }

        //do iframe dataURL download (old ch+FF):
        let f = document.createElement("iframe");
        document.body.appendChild(f);

        if (!winMode) {
            // force a mime that will download:
            url = `data:${url.replace(/^data:([\w\/\-+]+)/, defaultMime)}`;
        }
        f.src = url;
        setTimeout(() => {
            document.body.removeChild(f);
        }, 333);
    }

    if (navigator.msSaveBlob) {
        // IE10+ : (has Blob, but not a[download] or URL)
        return navigator.msSaveBlob(blob, fileName);
    }

    if (self.URL) {
        // simple fast and modern way using Blob and URL:
        saver(self.URL.createObjectURL(blob), true);
    } else {
        // handle non-Blob()+non-URL browsers:
        if (typeof blob === "string" || blob.constructor === toString) {
            try {
                return saver(`data:${mimeType};base64,${self.btoa(blob)}`);
            } catch {
                return saver(`data:${mimeType},${encodeURIComponent(blob)}`);
            }
        }

        // Blob but not URL support:
        reader = new FileReader();
        reader.onload = function () {
            saver(this.result);
        };
        reader.readAsDataURL(blob);
    }
    return true;
}
/* eslint-enable */

// -----------------------------------------------------------------------------
// Exported download functions
// -----------------------------------------------------------------------------

/**
 * Download data as a file
 *
 * @param {Object} data
 * @param {String} filename
 * @param {String} mimetype
 * @returns {Boolean}
 *
 * Note: the actual implementation is certainly unconventional, but sadly
 * necessary to be able to test code using the download function
 */
export function downloadFile(data, filename, mimetype) {
    return downloadFile._download(data, filename, mimetype);
}
downloadFile._download = _download;

/**
 * Download a file from form or server url
 *
 * This function is meant to call a controller with some data
 * and download the response.
 *
 * Note: the actual implementation is certainly unconventional, but sadly
 * necessary to be able to test code using the download function
 *
 * @param {*} options
 * @returns {Promise<any>}
 */
export function download(options) {
    return download._download(options);
}

download._download = (options) => {
    return new Promise((resolve, reject) => {
        const xhr = new browser.XMLHttpRequest();
        let data;
        if (Object.prototype.hasOwnProperty.call(options, "form")) {
            xhr.open(options.form.method, options.form.action);
            data = new FormData(options.form);
        } else {
            xhr.open("POST", options.url);
            data = new FormData();
            Object.entries(options.data).forEach((entry) => {
                const [key, value] = entry;
                data.append(key, value);
            });
        }
        data.append("token", "dummy-because-api-expects-one");
        if (odoo.csrf_token) {
            data.append("csrf_token", odoo.csrf_token);
        }
        configureBlobDownloadXHR(xhr, {
            onSuccess: resolve,
            onFailure: reject,
            url: options.url,
        });
        xhr.send(data);
    });
};

/**
 * Setup a download xhr request response handling
 * (onload, onerror, responseType), with hooks when the download succeeds or
 * fails.
 *
 * @param {XMLHttpRequest} xhr
 * @param {object} [options]
 * @param {(filename: string) => void} [options.onSuccess]
 * @param {(Error) => void} [options.onFailure]
 * @param {string} [options.url]
 */
export function configureBlobDownloadXHR(
    xhr,
    { onSuccess = () => {}, onFailure = () => {}, url } = {}
) {
    xhr.responseType = "blob";
    xhr.onload = () => {
        const mimetype = xhr.response.type;
        const header = (xhr.getResponseHeader("Content-Disposition") || "").replace(/;$/, "");
        // replace because apparently we send some C-D headers with a trailing ";"
        const filename = header ? parse(header).parameters.filename : null;
        // In Odoo, the default mimetype, including for JSON errors is text/html (ref: http.py:Root.get_response )
        // in that case, in order to also be able to download html files, we check if we get a proper filename to be able to download
        if (xhr.status === 200 && (mimetype !== "text/html" || filename)) {
            _download(xhr.response, filename, mimetype);
            onSuccess(filename);
        } else if (xhr.status === 502) {
            // If Odoo is behind another server (nginx)
            onFailure(new ConnectionLostError(url));
        } else {
            const decoder = new FileReader();
            decoder.onload = () => {
                const contents = decoder.result;
                const doc = new DOMParser().parseFromString(contents, "text/html");
                const nodes =
                    doc.body.children.length === 0 ? [doc.body] : doc.body.children;

                let error;
                try {
                    // a Serialized python Error
                    const node = nodes[1] || nodes[0];
                    error = JSON.parse(node.textContent);
                } catch {
                    error = {
                        message: "Arbitrary Uncaught Python Exception",
                        data: {
                            debug:
                                `${xhr.status}` +
                                `\n` +
                                `${nodes.length > 0 ? nodes[0].textContent : ""}
                                ${nodes.length > 1 ? nodes[1].textContent : ""}`,
                        },
                    };
                }
                error = makeErrorFromResponse(error);
                onFailure(error);
            };
            decoder.readAsText(xhr.response);
        }
    };
    xhr.onerror = () => {
        onFailure(new ConnectionLostError(url));
    };
}
