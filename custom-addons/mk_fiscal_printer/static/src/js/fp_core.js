/** @namespace */
var Tremol = Tremol || {};
Tremol.FP = function () {
    if (!(this instanceof Tremol.FP)) {
        return new Tremol.FP();
    }
    this.prototype = this;
    var coreVersion = "1.0.0.8";
    var ip = "10.211.55.11";
    var port = 4444;
    var url = "http://10.211.55.11:4444";
    var w = false;
    var defsSent = false;
    var ok = false;
    var psr = (typeof DOMParser !== 'undefined' ? new DOMParser() : (typeof ActiveXObject !== 'undefined' ? new ActiveXObject('Microsoft.XMLDOM') : function(){ throw new Error(); }));
    var req = (typeof XMLHttpRequest !== 'undefined' ? new XMLHttpRequest() : (typeof ActiveXObject !== 'undefined' ? new ActiveXObject('Microsoft.XMLHTTP') : function(){ throw new Error(); }));
    try { req.withCredentials = false; } catch (ignored) { };
    try { req.overrideMimeType("text/xml; charset=UTF-8"); } catch (ignored) { };
    var sendReq = function(verb, prefix, data) {
        try {
            req.open(verb, url + prefix, false);
            req.setRequestHeader("Content-Type", "text/plain");
            // try { req.setRequestHeader("Accept-Charset", "ISO-8859-1,utf-8;q=0.7,*;q=0.7"); } catch (ignored) { }
            req.send(data);
            if (req.status !== 200) {
                throw new Error("HTTP code " + req.status);
            }
            var respXml = req.responseXML;
            if(!respXml || respXml.length === 0) {
                try {
                    if(req.responseText && req.responseText.length > 0) {
                        respXml = psr.parseFromString(req.responseText);
                    } else {
                        throw new Error();
                    }
                }
                catch(ignored) {
                    throw new Tremol.ServerError("Server response missing", Tremol.ServerErrorType.ServerResponseMissing);
                }   
            }
            throwOnServerError(respXml);
            return respXml;
        }
        catch(ex) {
            if (ex instanceof Tremol.ServerError) {
                throw ex;
            }
            else {
                throw new Tremol.ServerError("Server connection error (" + ex.message + ")", Tremol.ServerErrorType.ServerConnectionError)
            }
        }
    };

    var throwOnServerError = function(resp) {
        var resRoot = resp.getElementsByTagName("Res")[0];
        var resCode = Number(resRoot.getAttribute("Code"));
        if (resCode !== 0) {
            var errNode = resp.getElementsByTagName("Err")[0];
            /** var source = errNode.getAttribute("Source"); */
            var errMsg = resp.getElementsByTagName("Message")[0].firstChild.data;
            if(resCode === 40) {
                var ste1 = parseInt(errNode.getAttribute("STE1"), 16);
                var ste2 = parseInt(errNode.getAttribute("STE2"), 16);
                var fpliberror = parseInt(errNode.getAttribute("FPLibErrorCode"), 16);
                throw new Tremol.ServerError(errMsg, resCode, ste1, ste2, fpliberror);
            }
            else {
                throw new Tremol.ServerError(errMsg, resCode);
            }
        }
    }

    var analyzeResponse = function(resp) {
        var resRoot = resp.getElementsByTagName("Res")[0];
        var props = resRoot.getElementsByTagName("Res");
        var resultObj = { };
        var name = "";
        var p = 0;
        for(; p < props.length; p++) {
            var prop = props[p];
            var type = prop.getAttribute("Type");
            name = prop.getAttribute("Name");
            var value = prop.getAttribute("Value");
            if (value === "@") {
                resultObj[name] = null;
                break;
            }
            if (name === "Reserve") {
                continue; /** SKIP */
            }
            switch(type) {
                case "Text":
                    resultObj[name] = value;
                    break;
                case "Number":
                    resultObj[name] = parseFloat(value);
                    break;
                case "Decimal":
                    resultObj[name] = parseFloat(value);
                    break;
                case "Option":
                    resultObj[name] = value;
                    break;
                case "DateTime":
                    resultObj[name] = value.parseDateWithFormat(Date.TremolFpFormat);
                    break;
                case "Reserve":
                case "OptionHardcoded":
                    continue; /** SKIP */
                case "Base64":
                    resultObj[name] = String(value).base64stringToArrayBuffer();
                    break;
                case "Decimal_with_format":
                    resultObj[name] = parseFloat(value);
                    break;
                case "Decimal_plus_80h":
                    resultObj[name] = parseFloat(value);
                    break;
                case "Status":
                    resultObj[name] = (value === "1")
                    break;
                case "Null":
                    resultObj[name] = null;
                    break;
                default: /** unknown type => string */
                    resultObj[name] = value;
                    break;
            }
        }
        w = false;
        if(p === 1) {
            return resultObj[name];
        }
        else {
            return resultObj;
        }
    };

    /**
     * Returns the version of the core library
     * @returns {string}
     */
    this.GetVersionCore = function() {
        return coreVersion;
    };

    /**
     * Returns the version of the generated library
     * @returns {number}
     */
    this.GetVersionDefinitions = function() {
        if (this.prototype.timeStamp) {
            return this.prototype.timeStamp;
        }
        else {
            return 0;
        }
    };

    /**
     * Returns true if there is a command which is currently in progress 
     * @returns {boolean}
     */
    this.IsWorking = function() {
        return w;
    };

    /** 
     * Returns true if server definitions and generated code are with the same versions 
     * @returns {boolean}
     */
    this.IsCompatible = function() {
        return ok;
    };

    /**
     * Sends command to ZfpLab server
     * @param {string} commandName The name of the command
     * @param {...*} var_args Command arguments(ArgumentName, ArgumentValue, ArgumentName2, ArgumentValue2)
     * @return {*} 
     * @throws {Error}
     */
    this.do = function(commandName) {
        w = true;
        try {
            if(arguments.length < 1) {
                throw new Error("Invalid number of arguments!");
            }
            if((arguments.length % 2) === 0) {
                throw new Error("Invalid number of arguments!");
            }
            
            /** var xml = psr.parseFromString("<Command></Command>", "text/xml");
            var rt = xml.getElementsByTagName("Command")[0];
            rt.setAttribute("Name", commandName);
            if(arguments.length > 1)
            {
                var as = xml.createElement("Args");
                rt.appendChild(as);
                for (var a = 1; a < arguments.length; a+=2) 
                {
                    var an = xml.createElement("Arg");
                    an.setAttribute("Name", arguments[a]);
                    if(typeof arguments[a + 1]  === "string")
                    {
                        an.setAttribute("Value", arguments[a + 1].escapeForXML());
                    }
                    else if(arguments[a + 1] instanceof Date)
                    {
                        an.setAttribute("Value", arguments[a + 1].toTremolFpString());
                    }
                    else if (arguments[a + 1] instanceof Uint8Array)
                    {
                        an.setAttribute("Value", arguments[a + 1].toBase64string());
                    }
                    else
                    {
                        an.setAttribute("Value", arguments[a + 1]);
                    }
                    as.appendChild(an);
                }
            }
            var response = sendReq("POST", "", xml); */

            var x = '<Command Name="'+ commandName +'">';
            if(arguments.length > 1) {
                x += "<Args>";
                for (var a = 1; a < arguments.length; a+=2) {
                    if(typeof arguments[a + 1]  === "string")
                    {
                        x += '<Arg Name="' + arguments[a] + '" Value="' + arguments[a + 1].escapeForXML() + '" />';
                    }
                    else if(arguments[a + 1] instanceof Date)
                    {
                        x += '<Arg Name="' + arguments[a] + '" Value="' + arguments[a + 1].toTremolFpString() + '" />';
                    }
                    else if (arguments[a + 1] instanceof Uint8Array)
                    {
                        x += '<Arg Name="' + arguments[a] + '" Value="' + arguments[a + 1].toBase64string() + '" />';
                    }
                    else if (typeof arguments[a]  === "undefined" || typeof arguments[a + 1]  === "undefined" || arguments[a]  ==  null || arguments[a + 1]  == null)
                    {
                        continue;
                    }
                    else
                    {
                        x += '<Arg Name="' + arguments[a] + '" Value="' + String(arguments[a + 1]).escapeForXML() + '" />';
                    }
                }
                x += "</Args>";
            }
            x += "</Command>";
            var response = sendReq("POST", "", x);
            return analyzeResponse(response);
        }
        catch(ex) {
            if(ex instanceof Tremol.ServerError) {
                throw ex;
            }
            else {
                throw new Tremol.ServerError(ex.message, Tremol.ServerErrorType.ServerErr);
            }
        }
        finally {
            w = false;
        }
    };

    /**
     * Gets ZfpLab server settings 
     * @returns {Tremol.FP.ServerSettings}
     */
    this.ServerGetSettings = function () {
        return { ipaddress: ip, tcpport: port};
    };

    /**
     * @param {string} ipaddress Sets IP address
     * @param {number} tcpport Sets TCP port
     */
    this.ServerSetSettings = function (ipaddress, tcpport) {
        ip = ipaddress;
        port = tcpport;
        url = ip;
        if (url.indexOf("//") === -1 && url.indexOf("http") === -1 && url.indexOf("https") === -1) {
            url = "//" + url;
        }
        if (port && port > 0) {
            url += (":" + port);
        }
        if (url.charAt(url.length -1) !== "/") {
            url += "/";
        }
    };

    /**
     * Find device connected on serial port or USB
     * @returns {Tremol.FP.DeviceSettings}
     */
    this.ServerFindDevice = function() {
        w = true;
        try {
            var response = sendReq("GET", "finddevice", null);
            if(response.getElementsByTagName("com")[0].firstChild)
            {
                var comS = response.getElementsByTagName("com")[0].firstChild.nodeValue; //.data
                var baudS = Number(response.getElementsByTagName("baud")[0].firstChild.nodeValue);
                var fps = { serialPort: comS, baudRate: baudS, isWorkingOnTcp: false };
                return fps;
            }
            return null;
        }
        finally {
            w = false;
        }
    }

    /**
     * Gets the device settings
     * @returns {Tremol.FP.DeviceSettings}
     */
    this.ServerGetDeviceSettings = function () {
        w = true;
        try {
            var response = sendReq("GET", "settings", null);
            var isTcp =  Boolean(response.getElementsByTagName("tcp")[0].firstChild.nodeValue);
            var comS = response.getElementsByTagName("com")[0].firstChild.nodeValue; //.data
            var baudS = Number(response.getElementsByTagName("baud")[0].firstChild.nodeValue);
            var ipS = response.getElementsByTagName("ip")[0].firstChild.nodeValue;
            var portS = Number(response.getElementsByTagName("port")[0].firstChild.nodeValue);
            var passS = response.getElementsByTagName("password")[0].firstChild.nodeValue;
            var portOpen = Boolean(response.getElementsByTagName("keepPortOpen")[0].firstChild.nodeValue);
            var df = response.getElementsByTagName("defVer");
            if(this.prototype.timeStamp && df.length > 0) {
                ok = (this.prototype.timeStamp === Number(df[0].firstChild.nodeValue));
            }
            var fps = { isWorkingOnTcp: isTcp, ipaddress: ipS, tcpPort: portS, password: passS, serialPort: comS, baudRate: baudS, keepPortOpen: portOpen };
            return fps;
        }
        finally {
            w = false;
        }
    };


    /**
     * Sets Device Bluetooth communication settings if ZFPLabServer is running on Android device.
     * @throws {Error}
     * @param {string} deviceFriendlyName Bluetooth Device friendly name (ZK900001)
     */
    this.ServerSetAndroidBluetoothDeviceSettings = function (deviceFriendlyName) {
        w = true;
        try {
            if(!Tremol.FP.IsOnAndroid()) {
                throw new Tremol.ServerError("This connection type is used only if ZFPLabServer is running on Android device", Tremol.ServerErrorType.ClientArgValueWrongFormat);
            }
            var response = sendReq("GET", "settings(com=" + deviceFriendlyName +",tcp=0)", null);
            var df = response.getElementsByTagName("defVer");
            if(this.prototype.timeStamp && df.length > 0) {
                ok = (this.prototype.timeStamp === Number(df[0].firstChild.nodeValue));
            }
        }
        finally {
            w = false;
        }
    };

    /**
     * Sets Device serial port communication settings
     * This method is also used to set Bluetooth connection if ZFPLabServer is running on Android device.
     * @throws {Error}
     * @param {string} serialPort The name of the serial port (example: COM1).
     * @param {number} baudRate Baud rate (9600, 19200, 38400, 57600, 115200).
     * @param {boolean} keepPortOpen Keeps serial port open. For Bluetooth connection - not used.
     */
    this.ServerSetDeviceSerialSettings = function (serialPort, baudRate, keepPortOpen) {
        w = true;
        try {
            var response = sendReq("GET", "settings(com=" + serialPort +",baud=" + baudRate + ",keepPortOpen=" + (keepPortOpen ? "1" : "0") + ",tcp=0)", null);
            var df = response.getElementsByTagName("defVer");
            if(this.prototype.timeStamp && df.length > 0) {
                ok = (this.prototype.timeStamp === Number(df[0].firstChild.nodeValue));
            }
        }
        finally {
            w = false;
        }
    };

    /**
     * Sets Device LAN/WIFI communication settings
     * @throws {Error}
     * @param {string} ipaddress IP address
     * @param {number} tcpport TCP port
     * @param {string=} password ZFP password
     */
    this.ServerSetDeviceTcpSettings = function (ipaddress, tcpport, password) {
        w = true;
        try {
            var response = sendReq("GET", "settings(ip=" + ipaddress + ",port=" + tcpport + (password ? (",password=" + password) : "") + ",tcp=1)", null);
            var df = response.getElementsByTagName("defVer");
            if(this.prototype.timeStamp && df.length > 0) {
                ok = (this.prototype.timeStamp === Number(df[0].firstChild.nodeValue));
            }
        }
        finally {
            w = false;
        }
    };

    /**
     * Gets ZfpLab server connected clients
     * @throws {Error}
     * @return {Tremol.FP.ServerClient[]}  Connected clients
     */
    this.ServerGetClients = function () {
        w = true;
        try {
            var response = sendReq("GET", "clients", null);
            var clientNodes = response.getElementsByTagName("Client");
            var clients = [];
            for(var c = 0; c < clientNodes.length; c++) {
                var client = { 
                    id: response.getElementsByTagName("Id")[c].firstChild.nodeValue,
                    ipaddress: response.getElementsByTagName("ip")[c].firstChild.nodeValue,
                    isConnected: (response.getElementsByTagName("PortIsOpen")[c].firstChild.nodeValue === "1")
                };
                clients.push(client);
            }
            return clients;
        }
        finally {
            w = false;
        }
    };
   
    /**
     * Removes client from the server
     * @param {string} ip IP address of the client
     * @throws {Error}
     */
    this.ServerRemoveClient = function (ip) {
        w = true;
        try {
            sendReq("GET", "clientremove(ip=" + ip + ")", null);
        }
        finally {
            w = false;
        }
    };

    this.ServerSendDefs = function (defs) {
        w = true;
        try {
            if(!defsSent) {
                sendReq("POST", "", defs);
                defsSent = true;
            }
        }
        finally {
            w = false;
        }
    };
   
    /**
     * Closes the connection of the current client
     * @throws {Error}
     */
    this.ServerCloseDeviceConnection = function () {
        w = true;
        try {
            sendReq("GET", "clientremove(who=me)", null);
        }
        finally {
            w = false;
        }
    };
   
    /**
     * Removes all clients from the server
     * @throws {Error}
     */
    this.ServerRemoveAllClients = function () {
        w = true;
        try {
            sendReq("GET", "clientremove(who=all)", null);
        }
        finally {
            w = false;
        }
    };
   
     /**
     * Enables or disables ZfpLab server log
     * @throws {Error}
     * @param {boolean} enable enable the log
     */
    this.ServerSetLog = function (enable) {
        w = true;
        try {
            sendReq("GET", "log(on=" + (enable ? "1" : "0") + ")", null);
        }
        finally {
            w = false;
        }
    };
};


Tremol.FP.IsOnAndroid = function() {
    return (navigator.userAgent.toLowerCase().indexOf("android") > -1);
}

/** 
 * @typedef {Tremol.ServerErrorType} Tremol.ServerErrorType
 * @enum
 * @readonly
 */
Tremol.ServerErrorType = {
    /** @memberof Tremol.ServerErrorType */
    OK: 0,
    /** The current library version and the fiscal device firmware is not matching */
    ServMismatchBetweenDefinitionAndFPResult: 9,
    ServDefMissing: 10,
    ServArgDefMissing: 11,
    ServCreateCmdString: 12,
    ServUndefined: 19,
    /** When the server can not connect to the fiscal device */
    ServSockConnectionFailed: 30,
    /** Wrong device ТCP password */
    ServTCPAuth: 31,
    ServWrongTcpConnSettings: 32,
    ServWrongSerialPortConnSettings: 33,
    /** Proccessing of other clients command is taking too long */
    ServWaitOtherClientCmdProcessingTimeOut: 34,
    ServDisconnectOtherClientErr: 35,
    FPException: 40,
    ClientArgDefMissing: 50,
    ClientAttrDefMissing: 51,
    ClientArgValueWrongFormat: 52,
    ClientSettingsNotInitialized: 53,
    ClientInvalidGetFormat: 62,
    ClientInvalidPostFormat: 63,
    ServerAddressNotSet: 100,
    /** Specify server ServerAddress property */
    ServerConnectionError: 101,
    /** Connection from this app to the server is not established */
    ServerResponseMissing: 102,
    ServerResponseError: 103,
    /** The current library version and server definitions version do not match */
    ServerDefsMismatch: 104,
    ClientXMLCanNotParse: 105,
    PaymentNotSupported: 201,
    ServerErr: 1000
};
Object.freeze(Tremol.ServerErrorType);

/**
 * @constructor
 * @class FPError
 * @classdesc Error thrown from Tremol.FP library
 * @param {string} message
 * @param {Tremol.ServerErrorType} type
 * @param {number=} ste1
 * @param {number=} ste2
 * @param {fpliberror=} ste2
 */
Tremol.ServerError = function (message, type, ste1, ste2, fpliberror) {
    if(!(this instanceof Tremol.ServerError)) {
        return new Tremol.ServerError(message, type, ste1, ste2, fpliberror);
    }
    this.type = type;
    this.name = "Tremol.ZFPLabError";
    this.message = (message || "");
    this.ste1;
    this.ste2;
    if(ste1 !== undefined && ste1 !== null) {
        this.ste1 = ste1;
    }
    if(ste2 !== undefined && ste2 !== null) {
        this.ste2 = ste2;
    }
    if(fpliberror !== undefined && fpliberror !== null) {
        this.fpLibError = fpliberror;
    }
    this.isFpException = (this.type === Tremol.ServerErrorType.FPException);
};
Tremol.ServerError.prototype = Error;

Date.TremolFpFormat = "dd-MM-yyyy HH:mm:ss";

Date.prototype.toTremolFpString = function() {
    var d = this.getDate().lpad(2);
    var M = (this.getMonth() + 1).lpad(2);
    var y = this.getFullYear().lpad(4);
    var h = this.getHours().lpad(2);
    var m = this.getMinutes().lpad(2);
    var s = this.getSeconds().lpad(2);
    return d + "-" + M + "-" + y + " " + h + ":" + m  + ":" + s;
};

Date.prototype.toStringWithFormat = function(format) {
    var f = format;
    var d = this.getDate();
    var M = (this.getMonth() + 1);
    var y = this.getFullYear();
    var h = this.getHours();
    var m = this.getMinutes();
    var s = this.getSeconds();
    f = f.replace("dd", d.lpad(2));
    f = f.replace("d", d);f
    f = f.replace("MM", M.lpad(2));
    f = f.replace("M", M);
    f = f.replace("yyyy", y.lpad(4));
    f = f.replace("yy", (y-2000).lpad(2));
    f = f.replace("hh", h.lpad(2));
    f = f.replace("mm", m.lpad(2));
    f = f.replace("m", m);
    f = f.replace("ss", s.lpad(2));
    f = f.replace("s", s);
    return f;
};

Number.prototype.lpad = function(size) {
    var s = String(this);
    while (s.length < (size || 2)) {s = "0" + s;}
    return s;
};

String.prototype.parseDateWithFormat = function(format) {
    var p = this;
    var f = format;
    var y = 0;
    var M = 0;
    var d = 0;
    var h = 0;
    var m = 0;
    var s = 0;
    var yIx = f.indexOf("yyyy");
    var MIx = f.indexOf("MM");
    var dIx = f.indexOf("dd");
    var hIx = f.indexOf("HH");
    var mIx = f.indexOf("mm");
    var sIx = f.indexOf("ss");
    if(yIx !== -1)
    {
        y = parseInt(p.substring(yIx, yIx + 4));
    }
    else
    {
        yIx = f.indexOf("yy");
        if(yIx !== -1)
        {
            y = parseInt(p.substring(yIx, yIx + 2));
        }
    }
    if(MIx !== -1)
    {
        M = parseInt(p.substring(MIx, MIx + 2)) - 1;
    }
    if(dIx !== -1)
    {
        d =  parseInt(p.substring(dIx, dIx + 2));
    }
    if(hIx !== -1)
    {
        h = parseInt(p.substring(hIx, hIx + 2));
    }
    if(mIx !== -1)
    {
        m = parseInt(p.substring(mIx, mIx + 2));
    }
    if(sIx !== -1)
    {
        s =  parseInt(p.substring(sIx, sIx + 2));
    }
    return new Date(y, M, d, h, m, s);
};

/**
 * This method replaces all matches in the string
 * @this {string}
 * @param {string} search the string which shoould be replaced
 * @param {string} replacement the string wich should be put for replacement
 */
String.prototype.replaceAll = function (search, replacement) {
    return this.replace(new RegExp(search.replace(/([.*+?^=!:${}()|\[\]\/\\])/g, "\\$1"), 'g'), replacement);
};

String.prototype.escapeForXML = function () {
    var ss = this.toString();
    ss = ss.replaceAll("&", '&amp;')
            .replaceAll("<", '&lt;')
            .replaceAll(">", '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&apos;')
            .replaceAll("\n", '&#10;')
            .replaceAll("\r", '&#13;');
    return ss;
};

String.prototype.base64stringToArrayBuffer = function () {
    var binary_string =  window.atob(this.toString());
    var len = binary_string.length;
    var bytes = new Uint8Array( len );
    for (var i = 0; i < len; i++)        {
        bytes[i] = binary_string.charCodeAt(i);
    }
    return bytes;
};

Uint8Array.prototype.toBase64string = function () {
    var arr = this;
    var binary = '';
    for (var i = 0; i < arr.byteLength; i++) {
        binary += String.fromCharCode(arr[i]);
    }
    return window.btoa(binary);
};

Uint8Array.prototype.toUnicodeString = function() {
    var arr = this;
    var res = ""
    
    for (var i = 0; i < arr.byteLength; i++) {
        res += String.fromCharCode(arr[i]);
    }
    return res;
};



/**
* @typedef {Object} Tremol.FP.ServerSettings
* @property {string} ipaddress IP address
* @property {number} tcpport TCP port
*/

/**
* @typedef {Object} Tremol.FP.DeviceSettings
* @property {boolean} isWorkingOnTcp True if device is working on tcp
* @property {string} serialPort Serial port (example: COM1). If ZFPLabServer is running on Android device - Device friendly name (ZK999999)
* @property {number} baudRate Baud rate (9600, 19200, 38400, 57600, 115200)
* @property {boolean} keepPortOpen Keeps the port opened
* @property {string} ipaddress IP address
* @property {number} tcpPort TCP port
* @property {string?} password ZFP wifi password
*/
/**
* @typedef {Object} Tremol.FP.ServerClient
* @property {string} id Client id
* @property {string} ipaddress IP address
* @property {boolean} isConnected The client is connected to device
*/