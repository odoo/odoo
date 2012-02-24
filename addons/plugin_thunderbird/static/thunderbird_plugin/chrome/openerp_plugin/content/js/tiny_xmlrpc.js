/************************************************************
*    OpenERP, Open Source Management Solution
*    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
*
*    This program is free software: you can redistribute it and/or modify
*    it under the terms of the GNU Affero General Public License as
*    published by the Free Software Foundation, either version 3 of the
*    License, or (at your option) any later version.
*
*    This program is distributed in the hope that it will be useful,
*    but WITHOUT ANY WARRANTY; without even the implied warranty of
*    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
*    GNU Affero General Public License for more details.
*
*    You should have received a copy of the GNU Affero General Public License
*    along with this program.  If not, see <http://www.gnu.org/licenses/>.
***************************************************************/

var xmlRpcClient;

//Service name on server like /common,/db etc...
var strServerService;


var uri = new Array();
var name = new Array();
var rpc= {
    servers: {},
    addserver: function(name,ip,port,path) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        this.servers[name]= {
            ip: ip,
            port: port,
            path: path,
            avaible: true,
            sock: Components.classes['@mozilla.org/xml-rpc/client;1'].createInstance(Components.interfaces.nsIXmlRpcClient)};
    },
    getany: function(rpcval,n) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var t = ['PRUint8','PRUint16','PRInt16','PRInt32','PRBool','Char','CString','Float','Double','PRTime','InputStream','Array','Dictionary'];
        for (var i=0; i<t.length; i++)
            try { return [t[i],this.Iget(rpcval,Components.interfaces[((i==10 || i==12)? 'nsI': 'nsISupports')+t[i]],n)]; } catch(e) {}
        return [false,'error getany','Undefined type'];
    },
    onfault: function(t) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        return (t.constructor==Array && t.length==3 && !t[0] && (t[1].substr(0,5)=='error' || t[1].substr(0,5)=='fault'))?
            true : false;
    },
    getall: function(rpcval,n) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var t = this.getany(rpcval,n);
        if (this.onfault(t)) return t;
        if (t[0]=='PRBool') return (t[1]=='true');
        if (t[0]=='PRInt32') return parseInt(t[1]+'');
        if (t[0]=='PRTime') {
            dte= new Date("January 1, 1970, 00:00:00");
            dte.setUTCMilliseconds(t[1]+'');
            return dte; }
        if (t[0]=='Double' || t[0]=='Float') return parseFloat(t[1]+'');
        if (t[0]=='Char' || t[0]=='CString') return (t[1]+'').replace(/¬/g,'€');
        if (t[0]=='Array') {
            var a=[];
            for (var i=0; i<t[1].Count(); i++) a[i]= this.getall(t[1],i);
        } else if (t[0]=='Dictionary') {
            var a={};
            var keys = t[1].getKeys({});
            for (var k = 0; k < keys.length; k++)
                a[keys[k]]= this.getall(t[1],keys[k]);
        } else return t[1];
        return a;
    },
    Iget: function(rpcval,itype,n) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        if (n == undefined) return rpcval.QueryInterface(itype);
        else if (n==parseInt(n)) return rpcval.QueryElementAt(n,itype);
        else return rpcval.getValue(n).QueryInterface(itype);
    },
    checktype: function(val) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        if (val != undefined) {
            switch (val.constructor) {
                case Number: return (val==parseInt(val))? 1:4;
                case Boolean: return 2;
                case String: return 3;
                case Date: return 5;
                case Object: return 7;
                case Array: return 6;

            }
        }
        return 7;

    },
    set: function(rpcobj,param) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        if (param==undefined) return [false,'error set','Undefined parameter'];
        var itype= this.checktype(param);
        if (this.onfault(itype)) return itype;
        var p = this.servers[rpcobj].sock.createType(itype,{});
        if (itype==6) {
            if (param.length>0)
                for (var i=0; i<param.length; i++) p.AppendElement( this.set(rpcobj,param[i]) );
        } else if (itype==7) {
            for (var i in param) p.setValue( i, this.set(rpcobj,param[i]) );
        } else if (itype==4) {
            p.data=(''+param).replace(',','.');
        } else p.data=param;
        return p;
    },
    ask: function(rpcobj,method,params,func_out) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var a=this.disableNset(rpcobj) ;
        if (this.onfault(a)) return a;
        var handler = {
            onResult: function(client, async, result) {
                rpc.servers[rpcobj].avaible= true;
                func_out(rpc.getall(result)); },
            onFault: function (client, async, faute) {alert("in ask infault"+result)
                 rpc.servers[rpcobj].avaible= true; func_out([false,'fault',faute]); },
            onError: function (client, async, status, msg) {
                rpc.servers[rpcobj].avaible= true;
                if (status=='2147500037') {
                    status= "no network or no server";
                    msg= "1. Check your network connection.";
                    msg+= "\n2. Check your server connection parameters:";
                    msg+= "\n\t"+rpc.servers[rpcobj].ip+":"+rpc.servers[rpcobj].port+"=>"+params[0];
                    msg+= "\n3. Your server may not be launched or connected to the network.";
                }
                func_out([false,'error '+status,msg]);
                } };
        var p = [];
        for (var i=0; i<params.length; i++)
            p[i]= this.set(rpcobj,params[i]);
        try { this.servers[rpcobj].sock.asyncCall(handler, null, method, p, p.length);
        } catch(e) {
            this.servers[rpcobj].avaible= true;
            this.servers[rpcobj].sock= Components.classes['@mozilla.org/xml-rpc/client;1'].createInstance(Components.interfaces.nsIXmlRpcClient) ;
            func_out([false,'error catch',e]); }
        return true;
    },
    disableNset: function(rpcobj) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        if (this.servers[rpcobj]) {
            this.servers[rpcobj].avaible= false;//alert('http://'+this.servers[rpcobj].ip+':'+this.servers[rpcobj].port+this.servers[rpcobj].path);
            server_path=this.servers[rpcobj].ip+':'+this.servers[rpcobj].port+this.servers[rpcobj].path
            this.servers[rpcobj].sock.init(server_path);
            
            return true; }
        return [false,'error disableNset','Server vars not set'];
    }
}

var callback = null;

//Sets the preference service
function getPref(){
    var prefService = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefService);
    var branchobj = prefService.getBranch("extensions.tiny.");
    branchobj.QueryInterface(Components.interfaces.nsIPrefBranch2);
    return branchobj
}

function getPreference(key, type) {
    if (!type || type == 'STRING') {
        return getPref().getCharPref(key);
    }
    if (type == 'INT') {
        return getPref().getIntPref(key);
    }
}

function getPreferenceDefault(key, default_value, type) {
	res = getPreference(key, type)
	if (!res || res == "") 
		return default_value
	return res
}

function setPreference(key, value, type) {
    
    if (!type || type == 'STRING') {
        getPref().setCharPref(key, value);
    }
    if (type == 'INT') {
        getPref().setIntPref(key, value);
    }
}



function setServerName(server) {
	setPreference('server_name', server)
}

function getServerName(server) {
	getPreference('server_name')
}

//set preference value for server port
function setPort(argPort){
    getPref().setCharPref('serverport',argPort)
}

//get server port
function getPort(){
    return getPref().getCharPref('serverport');
}




//set preference value for server url
function setServer(argServer){
    getPref().setCharPref('serverurl',argServer);
}

//set preference value of username for login
function setUsername(argUsername){
    getPref().setCharPref('username',argUsername);
}

//set preference value of password for login
function setPassword(argPassword){
    getPref().setCharPref('password',argPassword);
}


//set server service
function setServerService(argServerService){
    strServerService = argServerService;
}



//set preference value for storing partner id
function setPartnerId(argPartnerId){
    getPref().setCharPref('partnerid',argPartnerId)
}


//set preference value for storing user id
function setUserId(argUserId){
    getPref().setIntPref('userid',argUserId);
}

//set database list is displaye or not
function setDBList(argDBList){
    getPref().setCharPref('db_list',argDBList)
}

//set module install or not
function setmodule_install(argconnect_module){
    getPref().setCharPref('module_install',argconnect_module)
}

//get module install or not
function getmodule_install(){
    return getPref().getCharPref('module_install');
}


//get partner id
function getPartnerId(){
    return getPref().getCharPref('partnerid');
}
//get database list is displaye or not
function getDBList(){
    return getPref().getCharPref('db_list');
}

//get serverurl
function getServer(){
    return getPref().getCharPref('serverurl');
}


//get database name
function getDbName(){
    return getPref().getCharPref('serverdbname');
}

//get username from config settings
function getUsername(){
    return getPref().getCharPref('username');
}

//get password from config settings
function getPassword(){
    return getPref().getCharPref('password');
}

//get serverservice
function getServerService(){
    return strServerService;

}

//get sender email //TO REMOVE
function getSenderEmail(){
    return getPref().getCharPref('senderemail');
}

//get sender name  //TO REMOVE
function getSenderName() {
        return getPref().getCharPref('sendername');
}

//get the whole server path
function getServerUrl(){
    return getServer()+"/"+getServerService();
}


//Creates and returns and instance of the XML-RPC client
function getClient() {
    // Enable correct security
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    return Components.classes['@mozilla.org/xml-rpc/client;1'].createInstance(Components.interfaces.nsIXmlRpcClient);
}

//returns the xmlrpc client instance
function getXmlRpc() {
    if (!xmlRpcClient) {
        xmlRpcClient = getClient();
    }
    // Initialize the client with the URL
    xmlRpcClient.init(getServerUrl());
    return xmlRpcClient;
}


/**
 * module_install handler
 */
var listinstallmodulehandler = {
    onResult: function(client, context, result) {
        setmodule_install('yes')
        callback()
    },
    onFault: function (client, ctxt, fault) {
        setmodule_install('no')
        callback()
    },

    onError: function (client, ctxt, status, errorMsg) {
        setmodule_install('no')
        callback()
    }
}
/**
 * Check is the plugin module is installed
 */ 
function module_install()
{
    setmodule_install("no")
    
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    
    var strDbName = get_rpc_string(xmlRpcClient, getPreference("serverdbname"));
    var struid = get_rpc_int(xmlRpcClient, getPreference('userid', 'INT'));
    var strpass = get_rpc_string(xmlRpcClient, getPreference("password"));
    var strmethod = get_rpc_string(xmlRpcClient, "is_installed");
    var strobj = get_rpc_string(xmlRpcClient, "plugin.handler");
    xmlRpcClient.asyncCall(listinstallmodulehandler,null,'execute',[ strDbName,struid,strpass,strobj,strmethod], 5);
}


//xmlrpc request handler for handling the login information
var listcreateLoginHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var login = result.QueryInterface(Components.interfaces.nsISupportsPrimitive)
        if(login.type == 12){
            login = result.QueryInterface(Components.interfaces.nsISupportsPRInt32)
            setUserId(login.data);
            module_install()
        }
        else{
        	setUserId(0);
        	callback();
        }
    },
    onFault: function (client, ctxt, fault) {
    	setUserId(0);
    	callback();
    },

    onError: function (client, ctxt, status, errorMsg) {
    	setUserId(0);
    	callback();
    }
}


function login(){
    setServerService('xmlrpc/common');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = get_rpc_string(xmlRpcClient, getPreference("serverdbname"));
    var strusername = get_rpc_string(xmlRpcClient, getPreference('username'));
    var strpass = get_rpc_string(xmlRpcClient, getPreference("password"));
    xmlRpcClient.asyncCall(listcreateLoginHandler,null,'login',[strDbName,strusername,strpass],3);
}

function get_rpc_string(rpc_client, val) {
    var str = rpc_client.createType(rpc_client.STRING,{});
    str.data = val;
    return str;
}

function get_rpc_int(rpc_client, val) {
    var integer = rpc_client.createType(rpc_client.INT,{});
    integer.data = val;
    return integer;
}



