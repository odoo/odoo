/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Mozilla XML-RPC Client component.
 *
 * The Initial Developer of the Original Code is
 * Digital Creations 2, Inc.
 * Portions created by the Initial Developer are Copyright (C) 2000
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Martijn Pieters <mj@digicool.com> (original author)
 *   Samuel Sieb <samuel@sieb.net>
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

/*
 *  nsXmlRpcClient XPCOM component
 *  Version: $Revision: 1.39 $
 *
 *  $Id: nsXmlRpcClient.js,v 1.39 2006/10/24 16:02:01 silver%warwickcompsoc.co.uk Exp $
 */

/*
 * Constants
 */
Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");
const XMLRPCCLIENT_CONTRACTID = '@mozilla.org/xml-rpc/client;1';
const XMLRPCCLIENT_CID =
    Components.ID('{4d7d15c0-3747-4f7f-b6b3-792a5ea1a9aa}');
const XMLRPCCLIENT_IID = Components.interfaces.nsIXmlRpcClient;

const XMLRPCFAULT_CONTRACTID = '@mozilla.org/xml-rpc/fault;1';
const XMLRPCFAULT_CID =
    Components.ID('{691cb864-0a7e-448c-98ee-4a7f359cf145}');
const XMLRPCFAULT_IID = Components.interfaces.nsIXmlRpcFault;

const XMLHTTPREQUEST_CONTRACTID = '@mozilla.org/xmlextras/xmlhttprequest;1';

const NSICHANNEL = Components.interfaces.nsIChannel;

const DEBUG = false;
const DEBUGPARSE = false;

const DOMNode = Components.interfaces.nsIDOMNode;
/*
 * Class definitions
 */

/* The nsXmlRpcFault class constructor. */
function nsXmlRpcFault() {}

/* the nsXmlRpcFault class def */
nsXmlRpcFault.prototype = {
    faultCode: 0,
    faultString: '',

    init: function(faultCode, faultString) {
        this.faultCode = faultCode;
        this.faultString = faultString;
    },

    toString: function() {
        return '<XML-RPC Fault: (' + this.faultCode + ') ' +
            this.faultString + '>';
    },

    // nsISupports interface
    QueryInterface: function(iid) {
        if (!iid.equals(Components.interfaces.nsISupports) &&
            !iid.equals(XMLRPCFAULT_IID))
            throw Components.results.NS_ERROR_NO_INTERFACE;
        return this;
    }
};

/* The nsXmlRpcClient class constructor. */
function nsXmlRpcClient() {}

/* the nsXmlRpcClient class def */
nsXmlRpcClient.prototype = {
    _serverUrl: null,
    _useAuth: false,

    classDescription: "nsXmlRpcClient XPCOM component",
    classID:          Components.ID("{4d7d15c0-3747-4f7f-b6b3-792a5ea1a9aa}"),
    contractID:       "@mozilla.org/xml-rpc/client;1",

    init: function(serverURL) {
        this._serverUrl = serverURL;
        this._encoding = "UTF-8";
    },

    setAuthentication: function(username, password){
        if ((typeof username == "string") &&
            (typeof password == "string")){
          this._useAuth = true;
          this._username = username;
          this._password = password;
        }
    },

    clearAuthentication: function(){
        this._useAuth = false;
    },

    setEncoding: function(encoding){
        this._encoding = encoding;
    },

    get serverUrl() { return this._serverUrl; },

    // Internal copy of the status
    _status: null,
    _listener: null,

    asyncCall: function(listener, context, methodName, methodArgs, count) {
        debug('asyncCall');
        // Check for call in progress.
        if (this._inProgress)   
            return;
            //throw Components.Exception('Call in progress!');

        // Check for the server URL;
        if (!this._serverUrl)
            throw Components.Exception('Not initialized');

        this._inProgress = true;

        // Clear state.
        this._foundFault = false;
        this._passwordTried = false;
        this._result = null;
        this._fault = null;
        this._status = null;
        this._responseStatus = null;
        this._responseString = null;
        this._listener = listener;
        this._seenStart = false;
        this._context = context;
        
        debug('Arguments: ' + methodArgs);

        // Generate request body
        var xmlWriter = new XMLWriter(this._encoding);
        this._generateRequestBody(xmlWriter, methodName, methodArgs);

        var requestBody = xmlWriter.data;

        debug('Request: ' + requestBody);

        this.xmlhttp = Components.classes[XMLHTTPREQUEST_CONTRACTID]
            .createInstance(Components.interfaces.nsIXMLHttpRequest);
        if (this._useAuth) {
            this.xmlhttp.open('POST', this._serverUrl, true,
                              this._username, this._password);
        } else {
            this.xmlhttp.open('POST', this._serverUrl);
        }
        this.xmlhttp.onload = this._onload;
        this.xmlhttp.onerror = this._onerror;
        this.xmlhttp.parent = this;
        this.xmlhttp.setRequestHeader('Content-Type','text/xml');
        this.xmlhttp.send(requestBody);
        var chan = this.xmlhttp.channel.QueryInterface(NSICHANNEL);
        chan.notificationCallbacks = this;
    },

    _onload: function(e) {
        var result;
        var parent = e.target.parent;
        parent._inProgress = false;
        parent._responseStatus = e.target.status;
        parent._responseString = e.target.statusText;
        if (!e.target.responseXML) {
            if (e.target.status) {
                try {
                    parent._listener.onError(parent, parent._context,
                        Components.results.NS_ERROR_FAILURE,
                        'Server returned status ' + e.target.status);
                } catch (ex) {
                    debug('Exception in listener.onError: ' + ex);
                }
            } else {
                try {
                    parent._listener.onError(parent, parent._context,
                                      Components.results.NS_ERROR_FAILURE,
                                      'Unknown network error');
                } catch (ex) {
                    debug('Exception in listener.onError: ' + ex);
                }
            }
            return;
        }
        try {
            e.target.responseXML.normalize();
            result = parent.parse(e.target.responseXML);
        } catch (ex) {
            try {
                parent._listener.onError(parent, parent._context,
                                         ex.result, ex.message);
            } catch (ex) {
                debug('Exception in listener.onError: ' + ex);
            }
            return;
        }
        if (parent._foundFault) {
            parent._fault = result;
            try {
                parent._listener.onFault(parent, parent._context, result);
            } catch(ex) {
                debug('Exception in listener.onFault: ' + ex);
            }
        } else {
            parent._result = result.value;
            try { 
                parent._listener.onResult(parent, parent._context,
                                          result.value);
            } catch (ex) {
                debug('Exception in listener.onResult: ' + ex);
            }
        }
    },

    _onerror: function(e) {
        var parent = e.target.parent;
        parent._inProgress = false;
        try {
            parent._listener.onError(parent, parent._context,
                                Components.results.NS_ERROR_FAILURE,
                                'Unknown network error');
        } catch (ex) {
            debug('Exception in listener.onError: ' + ex);
        }
    },
    
    _foundFault: false,

    _fault: null,
    _result: null,
    _responseStatus: null,
    _responseString: null,

    get fault() { return this._fault; },
    get result() { return this._result; },
    get responseStatus() { return this._responseStatus; },
    get responseString() { return this._responseString; },

    /* Convenience. Create an appropriate XPCOM object for a given type */
    INT:      1,
    BOOLEAN:  2,
    STRING:   3,
    DOUBLE:   4,
    DATETIME: 5,
    ARRAY:    6,
    STRUCT:   7,
    BASE64:   8, // Not part of nsIXmlRpcClient interface, internal use.
    createType: function(type, uuid) {
        const SUPPORTSID = '@mozilla.org/supports-';
        switch(type) {
            case this.INT:
                uuid.value = Components.interfaces.nsISupportsPRInt32
                return createInstance(SUPPORTSID + 'PRInt32;1',
                    'nsISupportsPRInt32');

            case this.BOOLEAN:
                uuid.value = Components.interfaces.nsISupportsPRBool
                return createInstance(SUPPORTSID + 'PRBool;1',
                    'nsISupportsPRBool');

            case this.STRING:
                uuid.value = Components.interfaces.nsISupportsCString
                return createInstance(SUPPORTSID + 'cstring;1',
                    'nsISupportsCString');

            case this.DOUBLE:
                uuid.value = Components.interfaces.nsISupportsDouble
                return createInstance(SUPPORTSID + 'double;1',
                    'nsISupportsDouble');

            case this.DATETIME:
                uuid.value = Components.interfaces.nsISupportsPRTime
                return createInstance(SUPPORTSID + 'PRTime;1',
                    'nsISupportsPRTime');

            case this.ARRAY:
                uuid.value = Components.interfaces.nsISupportsArray
                return createInstance(SUPPORTSID + 'array;1',
                    'nsISupportsArray');

            case this.STRUCT:
                uuid.value = Components.interfaces.nsIDictionary
                return createInstance('@mozilla.org/dictionary;1', 
                    'nsIDictionary');

            default: throw Components.Exception('Unsupported type');
        }
    },

    // nsISupports interface
    QueryInterface: function(iid) {
        if (!iid.equals(Components.interfaces.nsISupports) &&
            !iid.equals(XMLRPCCLIENT_IID) &&
            !iid.equals(Components.interfaces.nsIInterfaceRequestor))
            throw Components.results.NS_ERROR_NO_INTERFACE;
        return this;
    },

    // nsIInterfaceRequester interface
    getInterface: function(iid, result){
        if (iid.equals(Components.interfaces.nsIAuthPrompt)){
            return this;
        }
        Components.returnCode = Components.results.NS_ERROR_NO_INTERFACE;
        return null;
    },

    // nsIAuthPrompt interface
    _passwordTried: false,
    promptUsernameAndPassword: function(dialogTitle, text, passwordRealm,
                                        savePassword, user, pwd){

        if (this._useAuth){
            if (this._passwordTried){
                return false;
            }
            user.value = this._username;
            pwd.value = this._password;
            this._passwordTried = true;
            return true;
        }
        return false;
    },

    /* Generate the XML-RPC request body */
    _generateRequestBody: function(writer, methodName, methodArgs) {
        writer.startElement('methodCall');

        writer.startElement('methodName');
        writer.write(methodName);
        writer.endElement('methodName');

        writer.startElement('params');
        for (var i = 0; i < methodArgs.length; i++) {
            writer.startElement('param');
            this._generateArgumentBody(writer, methodArgs[i]);
            writer.endElement('param');
        }
        writer.endElement('params');

        writer.endElement('methodCall');
    },

    /* Write out a XML-RPC parameter value */
    _generateArgumentBody: function(writer, obj) {
        writer.startElement('value');
        var sType = this._typeOf(obj);
        switch (sType) {
            case 'PRUint8':
            case 'PRUint16':
            case 'PRInt16':
            case 'PRInt32':
                obj=obj.QueryInterface(Components.interfaces['nsISupports' +
                    sType]);
                writer.startElement('i4');
                writer.write(obj.toString());
                writer.endElement('i4');
                break;

            case 'PRBool':
                obj=obj.QueryInterface(Components.interfaces.nsISupportsPRBool);
                writer.startElement('boolean');
                writer.write(obj.data ? '1' : '0');
                writer.endElement('boolean');
                break;

            case 'Char':
            case 'CString':
                obj=obj.QueryInterface(Components.interfaces['nsISupports' +
                    sType]);
                writer.startElement('string');
                writer.write(obj.toString());
                writer.endElement('string');
                break;

            case 'Float':
            case 'Double':
                obj=obj.QueryInterface(Components.interfaces['nsISupports' +
                    sType]);
                writer.startElement('double');
                writer.write(obj.toString());
                writer.endElement('double');
                break;

            case 'PRTime':
                obj = obj.QueryInterface(
                    Components.interfaces.nsISupportsPRTime);
                var date = new Date(obj.data)
                writer.startElement('dateTime.iso8601');
                writer.write(iso8601Format(date));
                writer.endElement('dateTime.iso8601');
                break;
                
            case 'InputStream':
                obj = obj.QueryInterface(Components.interfaces.nsIInputStream);
                obj = toScriptableStream(obj);
                writer.startElement('base64');
                streamToBase64(obj, writer);
                writer.endElement('base64');
                break;
            
            case 'Array':
                obj = obj.QueryInterface(
                    Components.interfaces.nsISupportsArray);
                writer.startElement('array');
                writer.startElement('data');
                for (var i = 0; i < obj.Count(); i++)
                    this._generateArgumentBody(writer, obj.GetElementAt(i));
                writer.endElement('data');
                writer.endElement('array');
                break;

            case 'Dictionary':
                obj = obj.QueryInterface(Components.interfaces.nsIDictionary);
                writer.startElement('struct');
                var keys = obj.getKeys({});
                for (var k = 0; k < keys.length; k++) {
                    writer.startElement('member');
                    writer.startElement('name');
                    writer.write(keys[k]);
                    writer.endElement('name');
                    this._generateArgumentBody(writer, obj.getValue(keys[k]));
                    writer.endElement('member');
                }
                writer.endElement('struct');
                break;

            default:
                throw Components.Exception('Unsupported argument', null, null,
                    obj);
        }

        writer.endElement('value');
    },

    /* Determine type of a nsISupports primitive, array or dictionary. */
    _typeOf: function(obj) {
        // XPConnect alows JS to pass in anything, because we are a regular
        // JS object to it. So we have to test rigorously.
        if (typeof obj != 'object') return 'Unknown';

        // Anything else not nsISupports is not allowed.
        if (typeof obj.QueryInterface != 'function') return 'Unknown';

        // Now we will have to eliminate by trying all possebilities.
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsPRUint8);
            return 'PRUint8';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsPRUint16);
            return 'PRUint16';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsPRInt16);
            return 'PRInt16';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsPRInt32);
            return 'PRInt32';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsPRBool);
            return 'PRBool';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsChar);
            return 'Char';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsCString);
            return 'CString';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsFloat);
            return 'Float';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsDouble);
            return 'Double';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsPRTime);
            return 'PRTime';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsIInputStream);
            return 'InputStream';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsISupportsArray);
            return 'Array';
        } catch(e) {}
        
        try {
            obj.QueryInterface(Components.interfaces.nsIDictionary);
            return 'Dictionary';
        } catch(e) {}
        
        // Not a supported type
        return 'Unknown';
    },

    // Response parsing state
    _valueStack: [],
    _currValue: null,
    _cdata: null,

    parse: function(doc) {
        var node = doc.firstChild;
        var result;
        if (node.nodeType == DOMNode.TEXT_NODE)
            node = node.nextSibling;
        if ((node.nodeType != DOMNode.ELEMENT_NODE) ||
            (node.nodeName != 'methodResponse')) {
            throw Components.Exception('Expecting a methodResponse', null, null,
                                       doc);
        }
        node = node.firstChild;
        if (node.nodeType == DOMNode.TEXT_NODE)
            node = node.nextSibling;
        if (node.nodeType != DOMNode.ELEMENT_NODE)
            throw Components.Exception('Expecting a params or fault', null,
                                       null, doc);
        if (node.nodeName == 'params') {
            node = node.firstChild;
            if (node.nodeType == DOMNode.TEXT_NODE)
                node = node.nextSibling;
            if ((node.nodeType != DOMNode.ELEMENT_NODE) ||
                (node.nodeName != 'param')) {
                throw Components.Exception('Expecting a param', null, null,
                                           doc);
            }
            result = this.parseValue(node.firstChild);
        } else if (node.nodeName == 'fault') {
            this._foundFault = true;
            result = this.parseFault(node.firstChild);
        } else {
            throw Components.Exception('Expecting a params or fault', null,
                                       null, doc);
        }
        debug('Parse finished');
        return result;
    },

    parseValue: function(node) {
        var cValue = new Value();
        if (node && (node.nodeType == DOMNode.TEXT_NODE))
            node = node.nextSibling;
        if (!node || (node.nodeType != DOMNode.ELEMENT_NODE) ||
            (node.nodeName != 'value')) {
            throw Components.Exception('Expecting a value', null, null, node);
        }
        node = node.firstChild;
        if (!node)
            return cValue;
        if (node.nodeType == DOMNode.TEXT_NODE){
            if (!node.nextSibling) {
                cValue.value = node.nodeValue;
                return cValue;
            } else {
                node = node.nextSibling;
            }
        }
        if (node.nodeType != DOMNode.ELEMENT_NODE)
            throw Components.Exception('Expecting a value type', null, null,
                                       node);
        switch (node.nodeName) {
            case 'string':
                cValue.value = this.parseString(node.firstChild);
                break;
            case 'i4':
            case 'int':
                cValue.type = this.INT;
                cValue.value = this.parseString(node.firstChild);
                break;
            case 'boolean':
                cValue.type = this.BOOLEAN;
                cValue.value = this.parseString(node.firstChild);
                break;
            case 'double':
                cValue.type = this.DOUBLE;
                cValue.value = this.parseString(node.firstChild);
                break;
            case 'dateTime.iso8601':
                cValue.type = this.DATETIME;
                cValue.value = this.parseString(node.firstChild);
                break;
            case 'base64':
                cValue.type = this.BASE64;
                cValue.value = this.parseString(node.firstChild);
                break;
            case 'struct':
                cValue.type = this.STRUCT;
                this.parseStruct(cValue, node.firstChild);
                break;
            case 'array':
                cValue.type = this.ARRAY;
                this.parseArray(cValue, node.firstChild);
                break;
            default:
                throw Components.Exception('Expecting a value type', null, null,
                                           node);
        }
        return cValue;
    },

    parseString: function(node) {
        value = '';
        while (node) {
            if (node.nodeType != DOMNode.TEXT_NODE)
                throw Components.Exception('Expecting a text node', null, null,
                                           node);
            value += node.nodeValue; 
            node = node.nextSibling;
        }
        return value;
    },

    parseStruct: function(struct, node) {
        while (node) {
            if (node.nodeType == DOMNode.TEXT_NODE)
                node = node.nextSibling;
            if (!node)
                return;
            if ((node.nodeType != DOMNode.ELEMENT_NODE) ||
                (node.nodeName != 'member')) {
                throw Components.Exception('Expecting a member', null, null,
                                           node);
            }
            this.parseMember(struct, node.firstChild);
            node = node.nextSibling;
        }
    },

    parseMember: function(struct, node) {
        var cValue;
        if (node.nodeType == DOMNode.TEXT_NODE)
            node = node.nextSibling;
        if (!node || (node.nodeType != DOMNode.ELEMENT_NODE) ||
            (node.nodeName != 'name')) {
            throw Components.Exception('Expecting a name', null, null, node);
        }
        struct.name = this.parseString(node.firstChild);
        cValue = this.parseValue(node.nextSibling);
        struct.appendValue(cValue.value);
    },

    parseArray: function(array, node) {
        if (node.nodeType == DOMNode.TEXT_NODE)
            node = node.nextSibling;
        if (!node || (node.nodeType != DOMNode.ELEMENT_NODE) ||
            (node.nodeName != 'data')) {
            throw Components.Exception('Expecting array data', null, null, node);
        }
        for (node = node.firstChild; node; node = node.nextSibling) {
            if (node.nodeType == DOMNode.TEXT_NODE)
                continue;
            array.appendValue(this.parseValue(node).value);
        }
    },

    parseFault: function(node) {
        var fault = createInstance(XMLRPCFAULT_CONTRACTID, 'nsIXmlRpcFault');
        var cValue = this.parseValue(node);
        if ((cValue.type != this.STRUCT) ||
            (!cValue.value.hasKey('faultCode')) ||
            (!cValue.value.hasKey('faultString'))) {
            throw Components.Exception('Invalid fault', null, null, node);
        }
        fault.init(cValue.value.getValue('faultCode').data,
                   cValue.value.getValue('faultString').data);
        return fault;
    }
};

if (XPCOMUtils.generateNSGetFactory)
    var NSGetFactory = XPCOMUtils.generateNSGetFactory([nsXmlRpcClient]);
else
    var NSGetModule = XPCOMUtils.generateNSGetModule([nsXmlRpcClient]);
 

/* The XMLWriter class constructor */
function XMLWriter(encoding) {
    if (!encoding)
        encoding = "UTF-8";
    this.data = '<?xml version="1.0" encoding="' + encoding + '"?>';
}

/* The XMLWriter class def */
XMLWriter.prototype = {
    data: '',
    
    startElement: function(element) {
        this.data += '<' + element + '>';
    },

    endElement: function(element) {
        this.data += '</' + element + '>';
    },
    
    write: function(text) {
        for (var i = 0; i < text.length; i++) {
            var c = text[i];
            switch (c) {
                case '<':
                    this.data += '&lt;';
                    break;
                case '&':
                    this.data += '&amp;';
                    break;
                default:
                    this.data += c;
            }
        }
    },

    markup: function(text) { this.data += text }
};

/* The Value class contructor */
function Value() { this.type = this.STRING; };

/* The Value class def */
Value.prototype = {
    INT:      nsXmlRpcClient.prototype.INT,
    BOOLEAN:  nsXmlRpcClient.prototype.BOOLEAN,
    STRING:   nsXmlRpcClient.prototype.STRING,
    DOUBLE:   nsXmlRpcClient.prototype.DOUBLE,
    DATETIME: nsXmlRpcClient.prototype.DATETIME,
    ARRAY:    nsXmlRpcClient.prototype.ARRAY,
    STRUCT:   nsXmlRpcClient.prototype.STRUCT,
    BASE64:   nsXmlRpcClient.prototype.BASE64,
    
    _createType: nsXmlRpcClient.prototype.createType,

    name: null,
    
    _value: null,
    get value() { return this._value; },
    set value(val) {
        // accepts [0-9]+ or x[0-9a-fA-F]+ and returns the character.
        function entityTrans(substr, code) {
            return String.fromCharCode("0" + code);
        }
        
        switch (this.type) {
            case this.STRING:
                val = val.replace(/&#([0-9]+);/g, entityTrans);
                val = val.replace(/&#(x[0-9a-fA-F]+);/g, entityTrans);
                val = val.replace(/&lt;/g, '<');
                val = val.replace(/&gt;/g, '>');
                val = val.replace(/&amp;/g, '&');
                this._value.data = val;
                break;
        
            case this.BOOLEAN:
                this._value.data = (val == 1);
                break;

            case this.DATETIME:
                this._value.data = Date.UTC(val.slice(0, 4), 
                    val.slice(4, 6) - 1, val.slice(6, 8), val.slice(9, 11),
                    val.slice(12, 14), val.slice(15));
                break;

            case this.BASE64:
                this._value.data = base64ToString(val);
                break;

            default:
                this._value.data = val;
        }
    },

    _type: null,
    get type() { return this._type; },
    set type(type) { 
        this._type = type;
        if (type == this.BASE64) 
            this._value = this._createType(this.STRING, {});
        else this._value = this._createType(type, {});
    },

    appendValue: function(val) {
        switch (this.type) {
            case this.ARRAY:
                this.value.AppendElement(val);
                break;

            case this.STRUCT:
                this.value.setValue(this.name, val);
                break;
        }
    }
};

/*
 * Objects
 */

/* nsXmlRpcClient Module (for XPCOM registration) */
var nsXmlRpcClientModule = {
    registerSelf: function(compMgr, fileSpec, location, type) {
        compMgr = compMgr.QueryInterface(Components.interfaces.nsIComponentRegistrar);

        compMgr.registerFactoryLocation(XMLRPCCLIENT_CID, 
                                        'XML-RPC Client JS component', 
                                        XMLRPCCLIENT_CONTRACTID, 
                                        fileSpec,
                                        location, 
                                        type);
        compMgr.registerFactoryLocation(XMLRPCFAULT_CID, 
                                        'XML-RPC Fault JS component', 
                                        XMLRPCFAULT_CONTRACTID, 
                                        fileSpec,
                                        location, 
                                        type);
    },

    getClassObject: function(compMgr, cid, iid) {
        if (!cid.equals(XMLRPCCLIENT_CID) && !cid.equals(XMLRPCFAULT_CID))
            throw Components.results.NS_ERROR_NO_INTERFACE;

        if (!iid.equals(Components.interfaces.nsIFactory))
            throw Components.results.NS_ERROR_NOT_IMPLEMENTED;

        if (cid.equals(XMLRPCCLIENT_CID))
            return nsXmlRpcClientFactory
        else return nsXmlRpcFaultFactory;
    },

    canUnload: function(compMgr) { return true; }
};

/* nsXmlRpcClient Class Factory */
var nsXmlRpcClientFactory = {
    createInstance: function(outer, iid) {
        if (outer != null)
            throw Components.results.NS_ERROR_NO_AGGREGATION;
    
        if (!iid.equals(XMLRPCCLIENT_IID) &&
            !iid.equals(Components.interfaces.nsISupports))
            throw Components.results.NS_ERROR_INVALID_ARG;

        return new nsXmlRpcClient();
    }
}

/* nsXmlRpcFault Class Factory */
var nsXmlRpcFaultFactory = {
    createInstance: function(outer, iid) {
        if (outer != null)
            throw Components.results.NS_ERROR_NO_AGGREGATION;

        if (!iid.equals(XMLRPCFAULT_IID) &&
            !iid.equals(Components.interfaces.nsISupports))
            throw Components.results.NS_ERROR_INVALID_ARG;

        return new nsXmlRpcFault();
    }
}

/*
 * Functions
 */
/* module initialisation */
function NSGetModule(comMgr, fileSpec) { return nsXmlRpcClientModule; }

/* Create an instance of the given ContractID, with given interface */
function createInstance(contractId, intf) {
    return Components.classes[contractId]
        .createInstance(Components.interfaces[intf]);
}

/* Get a pointer to a service indicated by the ContractID, with given interface */
function getService(contractId, intf) {
    return Components.classes[contractId]
        .getService(Components.interfaces[intf]);
}

/* Convert an inputstream to a scriptable inputstream */
function toScriptableStream(input) {
    var SIStream = Components.Constructor(
        '@mozilla.org/scriptableinputstream;1',
        'nsIScriptableInputStream', 'init');
    return new SIStream(input);
}

/* format a Date object into a iso8601 datetime string, UTC time */
function iso8601Format(date) {
    var datetime = date.getUTCFullYear();
    var month = String(date.getUTCMonth() + 1);
    datetime += (month.length == 1 ?  '0' + month : month);
    var day = date.getUTCDate();
    datetime += (day < 10 ? '0' + day : day);

    datetime += 'T';

    var hour = date.getUTCHours();
    datetime += (hour < 10 ? '0' + hour : hour) + ':';
    var minutes = date.getUTCMinutes();
    datetime += (minutes < 10 ? '0' + minutes : minutes) + ':';
    var seconds = date.getUTCSeconds();
    datetime += (seconds < 10 ? '0' + seconds : seconds);

    return datetime;
}

/* Convert a stream to Base64, writing it away to a string writer */
const BASE64CHUNK = 255; // Has to be dividable by 3!!
function streamToBase64(stream, writer) {
    while (stream.available()) {
        var data = [];
        while (data.length < BASE64CHUNK && stream.available()) {
            var d = stream.read(1).charCodeAt(0);
            // reading a 0 results in NaN, compensate.
            data = data.concat(isNaN(d) ? 0 : d);
        }
        writer.write(toBase64(data));
    }
}

/* Convert data (an array of integers) to a Base64 string. */
const toBase64Table = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' +
    '0123456789+/';
const base64Pad = '=';
function toBase64(data) {
    var result = '';
    var length = data.length;
    var i;
    // Convert every three bytes to 4 ascii characters.
    for (i = 0; i < (length - 2); i += 3) {
        result += toBase64Table[data[i] >> 2];
        result += toBase64Table[((data[i] & 0x03) << 4) + (data[i+1] >> 4)];
        result += toBase64Table[((data[i+1] & 0x0f) << 2) + (data[i+2] >> 6)];
        result += toBase64Table[data[i+2] & 0x3f];
    }

    // Convert the remaining 1 or 2 bytes, pad out to 4 characters.
    if (length%3) {
        i = length - (length%3);
        result += toBase64Table[data[i] >> 2];
        if ((length%3) == 2) {
            result += toBase64Table[((data[i] & 0x03) << 4) + (data[i+1] >> 4)];
            result += toBase64Table[(data[i+1] & 0x0f) << 2];
            result += base64Pad;
        } else {
            result += toBase64Table[(data[i] & 0x03) << 4];
            result += base64Pad + base64Pad;
        }
    }

    return result;
}

/* Convert Base64 data to a string */
const toBinaryTable = [
    -1,-1,-1,-1, -1,-1,-1,-1, -1,-1,-1,-1, -1,-1,-1,-1,
    -1,-1,-1,-1, -1,-1,-1,-1, -1,-1,-1,-1, -1,-1,-1,-1,
    -1,-1,-1,-1, -1,-1,-1,-1, -1,-1,-1,62, -1,-1,-1,63,
    52,53,54,55, 56,57,58,59, 60,61,-1,-1, -1, 0,-1,-1,
    -1, 0, 1, 2,  3, 4, 5, 6,  7, 8, 9,10, 11,12,13,14,
    15,16,17,18, 19,20,21,22, 23,24,25,-1, -1,-1,-1,-1,
    -1,26,27,28, 29,30,31,32, 33,34,35,36, 37,38,39,40,
    41,42,43,44, 45,46,47,48, 49,50,51,-1, -1,-1,-1,-1
];
function base64ToString(data) {
    var result = '';
    var leftbits = 0; // number of bits decoded, but yet to be appended
    var leftdata = 0; // bits decoded, but yet to be appended

    // Convert one by one.
    for (var i = 0; i < data.length; i++) {
        var c = toBinaryTable[data.charCodeAt(i) & 0x7f];
        var padding = (data[i] == base64Pad);
        // Skip illegal characters and whitespace
        if (c == -1) continue;
        
        // Collect data into leftdata, update bitcount
        leftdata = (leftdata << 6) | c;
        leftbits += 6;

        // If we have 8 or more bits, append 8 bits to the result
        if (leftbits >= 8) {
            leftbits -= 8;
            // Append if not padding.
            if (!padding)
                result += String.fromCharCode((leftdata >> leftbits) & 0xff);
            leftdata &= (1 << leftbits) - 1;
        }
    }

    // If there are any bits left, the base64 string was corrupted
    if (leftbits)
        throw Components.Exception('Corrupted base64 string');

    return result;
}

if (DEBUG) debug = function(msg) { 
    dump(' -- XML-RPC client -- : ' + msg + '\n'); 
};
else debug = function() {}

// vim:sw=4:sr:sta:et:sts:
