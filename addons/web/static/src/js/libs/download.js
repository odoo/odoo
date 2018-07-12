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
 *
 * @param {Blob | File | String} data
 * @param {String} [filename]
 * @param {String} [mimetype]
 */
odoo.define('web.download', function () {
return function download(data, filename, mimetype) {
    var self = window, // this script is only for browsers anyway...
            defaultMime = "application/octet-stream", // this default mime also triggers iframe downloads
            mimeType = mimetype || defaultMime, payload = data,
            url = !filename && !mimetype && payload,
            anchor = document.createElement("a"),
            toString = function (a) {return String(a);},
            myBlob = (self.Blob || self.MozBlob || self.WebKitBlob || toString),
            fileName = filename || "download", blob, reader;
    myBlob = myBlob.call ? myBlob.bind(self) : Blob;

    if (String(this) === "true") { //reverse arguments, allowing download.bind(true, "text/xml", "export.xml") to act as a callback
        payload = [payload, mimeType];
        mimeType = payload[0];
        payload = payload[1];
    }

    if (url && url.length < 2048) { // if no filename and no mime, assume a url was passed as the only argument
        fileName = url.split("/").pop().split("?")[0];
        anchor.href = url; // assign href prop to temp anchor
        if (anchor.href.indexOf(url) !== -1) { // if the browser determines that it's a potentially valid url path:
            var ajax = new XMLHttpRequest();
            ajax.open("GET", url, true);
            ajax.responseType = 'blob';
            ajax.onload = function (e) {
                download(e.target.response, fileName, defaultMime);
            };
            setTimeout(function () { ajax.send();}, 0); // allows setting custom ajax headers using the return:
            return ajax;
        }
    }

    //go ahead and download dataURLs right away
    if (/^data:[\w+\-]+\/[\w+\-]+[,;]/.test(payload)) {

        if (payload.length > (1024 * 1024 * 1.999) && myBlob !== toString) {
            payload = dataUrlToBlob(payload);
            mimeType = payload.type || defaultMime;
        } else {
            return navigator.msSaveBlob ?  // IE10 can't do a[download], only Blobs:
                    navigator.msSaveBlob(dataUrlToBlob(payload), fileName) : saver(payload); // everyone else can save dataURLs un-processed
        }

    }

    blob = payload instanceof myBlob ? payload : new myBlob([payload], {type: mimeType});


    function dataUrlToBlob(strUrl) {
        var parts = strUrl.split(/[:;,]/), type = parts[1],
                decoder = parts[2] === "base64" ? atob : decodeURIComponent,
                binData = decoder(parts.pop()), mx = binData.length,
                i = 0, uiArr = new Uint8Array(mx);

        for (i; i < mx; ++i) uiArr[i] = binData.charCodeAt(i);

        return new myBlob([uiArr], {type: type});
    }

    function saver(url, winMode) {
        if ('download' in anchor) { //html5 A[download]
            anchor.href = url;
            anchor.setAttribute("download", fileName);
            anchor.className = "download-js-link";
            anchor.innerHTML = "downloading...";
            anchor.style.display = "none";
            document.body.appendChild(anchor);
            setTimeout(function () {
                anchor.click();
                document.body.removeChild(anchor);
                if (winMode === true) {setTimeout(function () { self.URL.revokeObjectURL(anchor.href);}, 250);}
            }, 66);
            return true;
        }

        // handle non-a[download] safari as best we can:
        if (/(Version)\/(\d+)\.(\d+)(?:\.(\d+))?.*Safari\//.test(navigator.userAgent)) {
            url = url.replace(/^data:([\w\/\-+]+)/, defaultMime);
            if (!window.open(url)) { // popup blocked, offer direct download:
                if (confirm("Displaying New Document\n\nUse Save As... to download, then click back to return to this page.")) { location.href = url; }
            }
            return true;
        }

        //do iframe dataURL download (old ch+FF):
        var f = document.createElement("iframe");
        document.body.appendChild(f);

        if (!winMode) { // force a mime that will download:
            url = "data:" + url.replace(/^data:([\w\/\-+]+)/, defaultMime);
        }
        f.src = url;
        setTimeout(function () { document.body.removeChild(f); }, 333);
    }

    if (navigator.msSaveBlob) { // IE10+ : (has Blob, but not a[download] or URL)
        return navigator.msSaveBlob(blob, fileName);
    }

    if (self.URL) { // simple fast and modern way using Blob and URL:
        saver(self.URL.createObjectURL(blob), true);
    } else {
        // handle non-Blob()+non-URL browsers:
        if (typeof blob === "string" || blob.constructor === toString) {
            try {
                return saver("data:" + mimeType + ";base64," + self.btoa(blob));
            } catch (y) {
                return saver("data:" + mimeType + "," + encodeURIComponent(blob));
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
};
});
