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

//temporary variables
var strobject;

//Array
var arrDbList = new Array();
var arrPartnerList = new Array();
var arrFinalList = new Array();


var contentType = new Array();
var uri = new Array();
var url = new Array();
var name = new Array();
var attach_eml ="no";
var popup_display = "yes"
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
function handler_function( result ) {
    if ( rpc.onfault( result ) ) { alert( result[0] + "\n" + result[1] ); return; }
    else{
        alert("got result"+result)  
    }
}

//Sets the preference service
function getPref(){
    var prefService = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefService);
    var branchobj = prefService.getBranch("extensions.tiny.");
    branchobj.QueryInterface(Components.interfaces.nsIPrefBranch2);
    return branchobj
}

function setFileName(fname){
    getPref().setCharPref('fname',fname);
}

//set attachment file save or not
function setAttachment(argAttac){
    getPref().setCharPref('attachment',argAttac);
}

//set preference value for server url
function setServer(argServer){
    getPref().setCharPref('serverurl',argServer);
}

//set preference value for server port
function setPort(argPort){
    getPref().setCharPref('serverport',argPort)
}

//set preference value of database name for data searching and selection
function setDbName(argDbName){
    getPref().setCharPref('serverdbname',argDbName);
}

//set webserver url
function setWebServerURL(argWebServerURL){
    getPref().setCharPref('webserverurl',argWebServerURL);
}
//set preference value of username for login
function setUsername(argUsername){
    getPref().setCharPref('username',argUsername);
}

//set preference value of password for login
function setPassword(argPassword){
    getPref().setCharPref('password',argPassword);
}

//set preference value for storing partner id
function setPartnerId(argPartnerId){
    getPref().setCharPref('partnerid',argPartnerId)
}

//set preference value for Resource Id
function setResourceId(argResourceId){
    getPref().setCharPref('res_id',argResourceId)
}
//set server service
function setServerService(argServerService){
    strServerService = argServerService;
}

//set preference value for sender email
function setSenderEmail(argSenderEmail){
    getPref().setCharPref('senderemail',argSenderEmail)
}

//set preference value for receiver email
function setReceiverEmail(argReceiverEmail){
    getPref().setCharPref('receiveremail',argReceiverEmail)
}

//set preference value for sender name
function setSenderName(argSenderName){
    getPref().setCharPref('sendername',argSenderName)
}

//set preference value for email subject
function setSubject(argSubject){
    getPref().setCharPref('subject',argSubject)
}

//set preference value for email received date
function setReceivedDate(argReceivedDate){
    getPref().setCharPref('receiveddate',argReceivedDate)
}

//set preference value for storing contact id which is used while storing mail contents after creating a new partner contact
function setContactId(argContactId){
    getPref().setCharPref('contactid',argContactId)
}

//set preference value for storing attachment option in config
function setAttachValue(argAttachValue){
    getPref().setCharPref('attachvalue',argAttachValue)
}

//set preference value for email cclist
function setCCList(argCCList){
    getPref().setCharPref('cclist',argCCList)
}

//set preference value for email message body
function setMessageBody(argMessageBody){
    getPref().setCharPref('messagebody',argMessageBody)
}

//set preference value for Partner Name
function setPartnerName(argPartnerName){
    getPref().setCharPref('partnername',argPartnerName)
}

//set preference value for Contact Name
function setContactName(argContactName){
    getPref().setCharPref('contactname',argContactName)
}

//set preference value for street
function setStreet(argStreet){
    getPref().setCharPref('street',argStreet)
}

//set preference value for street2
function setStreet2(argStreet2){
    getPref().setCharPref('street2',argStreet2)
}

//set preference value for zipcode
function setZipCode(argZipcode){
    getPref().setCharPref('zipcode',argZipcode)
}

//set preference value for Office Number
function setOfficenumber(argOfficenumber){
    getPref().setCharPref('officeno',argOfficenumber)
}

//set preference value for Phone Number
function setMobilenumber(argMobilenumber){
    getPref().setCharPref('phoneno',argMobilenumber)
}

//set preference value for Fax
function setFax(argFax){
    getPref().setCharPref('fax',argFax)
}

//set preference value for city
function setCity(argCity){
    getPref().setCharPref('city',argCity)
}

//set preference value for country
function setCountry(argCountry){
    getPref().setCharPref('country',argCountry)
}

//set preference value for state
function setState(argState){
    getPref().setCharPref('state',argState)
}


//set the value for the whole server url
function setServerUrl(argServerUrl)
{
    var seperateUrl = argServerUrl.split(':');
    setServer(seperateUrl.slice(0,seperateUrl.length-1).join(":"));
    setPort(seperateUrl[seperateUrl.length-1]);
}

//set preference value for storing user id
function setUserId(argUserId){
    getPref().setIntPref('userid',argUserId);
}

//set database list is displaye or not
function setDBList(argDBList){
    getPref().setCharPref('db_list',argDBList)
}

//set server connect or not
function setconnect_server(argconnect_server){
    getPref().setCharPref('connect_server',argconnect_server)
}

//set module install or not
function setmodule_install(argconnect_module){
    getPref().setCharPref('module_install',argconnect_module)
}

//get module install or not
function getmodule_install(){
    return getPref().getCharPref('module_install');
}


//get server connect or not
function getconnect_server(){
    return getPref().getCharPref('connect_server');
}


//get partner id
function getPartnerId(){
    return getPref().getCharPref('partnerid');
}
//get database list is displaye or not
function getDBList(){
    return getPref().getCharPref('db_list');
}

function getFileName(){
    return getPref().getCharPref('fname');
}

//get attachment save or not
function getAttachment(){
    return getPref().getCharPref('attachment');
}

//get serverurl
function getServer(){
    return getPref().getCharPref('serverurl');
}

//get server port
function getPort(){
    return getPref().getCharPref('serverport');
}

//get database name
function getDbName(){
    return getPref().getCharPref('serverdbname');
}

//get webserver url
function getWebServerURL(){
    return getPref().getCharPref('webserverurl');
}

//get webserver port
function getwebPort(){
    return getPref().getCharPref('webserverport');
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

//get sender email
function getSenderEmail(){
    return getPref().getCharPref('senderemail');
}

//get receiver email
function getReceiverEmail(){
    return getPref().getCharPref('receiveremail');
}

//get resource id
function getResourceId(){
    return getPref().getCharPref('res_id');
}


//get sender name
function getSenderName(){
        str = getPref().getCharPref('sendername');
        if(!str.toString().match(/=?utf-8?q?/))
        {
            return str;
        }
        else
        {

            string = str.replace(/[\'Š',\'Ž',\'š',\'ž',\'Ÿ',\'À',\'Á',\'Â',\'Ã',\'Ä',\'Å',\'Ç',\'È',\'É',\'Ê',\'Ë',\'Ì',\'Í',\'Î',\'Ï',\'Ñ',\'Ò',\'Ó',\'Ô',\'Õ',\'Ö',\'Ø',\'Ù',\'Ú',\'Û',\'Ü',\'Ý',\'à',\'á',\'â',\'ã',\'ä',\'å',\'ç',\'è',\'é',\'ê',\'ë',\'ì',\'í',\'î',\'ï',\'ñ',\'ò',\'ó',\'ô',\'õ',\'ö',\'ø',\'ù',\'ú',\'û',\'ü',\'ý',\'ÿ',\'Þ',\'þ',\'Ð',\'ð',\'ß',\'Œ',\'œ',\'Æ',\'æ',\'µ']/g,'"',"'",'“','”',"\n","\r",'_/',"'S','Z','s','z','Y','A','A','A','A','A','A','C','E','E','E','E','I','I','I','I','N','O','O','O','O','O','O','U','U','U','U','Y','a','a','a','a','a','a','c','e','e','e','e','i','i','i','i','n','o','o','o','o','o','o','u','u','u','u','y','y','TH','th','DH','dh','ss','OE','oe','AE','ae','u','','','','','','','-'");

            var utftext = "";
            var encoded_string = "";
            var convertedString = "";
            for (var n = 0; n < string.length; n++)
            {
                var c = string.charCodeAt(n);
                if (c < 128) {
                    utftext += String.fromCharCode(c);
                }
            }

            encoded_string = encode64(utftext);
           return encoded_string;
        }
}


//get partner name
function getPartnerName(){
    return getPref().getCharPref('partnername');
}

//get contact name
function getContactName(){
    return getPref().getCharPref('contactname');
}


//get street name
function getStreet(){
    return getPref().getCharPref('street');
}

//get street2 name
function getStreet2(){
    return getPref().getCharPref('street2');
}

//get zip code
function getZipCode(){
    return getPref().getCharPref('zipcode');
}

//get city name
function getCity(){
    return getPref().getCharPref('city');
}

//get country name
function getCountry(){
    return getPref().getCharPref('country');
}

//get state name
function getState(){
    return getPref().getCharPref('state');
}

//get office no
function getOfficenumber(){
    return getPref().getCharPref('officeno');
}

//get mobile no
function getMobilenumber(){
    return getPref().getCharPref('phoneno');
}

//get fax no
function getFax(){
    return getPref().getCharPref('fax');
}


//get email subject
function getSubject(){
    return getPref().getCharPref('subject');
}

//get email received date
function getReceivedDate(){
    return getPref().getCharPref('receiveddate');
}

//get contact id which is used while storing mail contents after creating a new partner contact
function getContactId(){
    return getPref().getCharPref('contactid');
}

//get attachment option information from the configuration settings
function getAttachValue(){
    return getPref().getCharPref('attachvalue');
}

//get email cclist information
function getCCList(){
    return getPref().getCharPref('cclist');
}

//get email message body
function getMessageBody(){
    return getPref().getCharPref('messagebody');
}

//get the whole server path
function getServerUrl(){
    return getServer()+"/"+getServerService();
}

//get user id for the xmlrpc request
function getUserId(){
    return getPref().getIntPref('userid');
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

// function to get all basic parameters
function getBasicList(){
    var branchobj = getPref();
    arrBasicList = [];
    arrBasicList[0] = branchobj.getCharPref("serverdbname");
    arrBasicList[1] = branchobj.getIntPref('userid');
    arrBasicList[2] = branchobj.getCharPref("password");
    arrBasicList[3] = getServer()
    arrBasicList[4] = getPort()
    return arrBasicList
}

function createMenuItem_db(aLabel) {
    const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
    var item = document.createElementNS(XUL_NS, "menuitem"); // create a new XUL menuitem
    item.setAttribute("label", aLabel);
    item.setAttribute("value", aLabel);
    return item;
}

//xmlrpc request handler for getting the list of database
var listDbHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var arrMethodList = result.QueryInterface(Components.interfaces.nsISupportsArray);
                // Set the number of results
        var count = arrMethodList.Count();
        // Loop through the results, adding items to the list
        for (i = 0; i < count; i++) {
            var strlDbName = arrMethodList.QueryElementAt(i, Components.interfaces.nsISupportsCString);
                        arrDbList[i] = strlDbName.data;
        }
        var database = ""
        if (count > 0)
        {
            setDBList("true");
            var label = document.getElementById("database_option");
            var vbox = document.createElement("vbox");
            var hbox = document.createElement("hbox");
            var label1 = document.createElement("label");
            label1.setAttribute("width","80");
            label1.setAttribute("value","Database:");
            label1.setAttribute("id","label111");
            var menu1 = document.createElement("menulist");
            var menupopup1 = document.createElement("menupopup");
            menu1.setAttribute("id","DBlist");
            menu1.setAttribute("width","300");
            var menuitem1 = document.createElement("menuitem");
            database = arrDbList[0]
            menuitem1.setAttribute("label", arrDbList[0]);
            menuitem1.setAttribute("value", arrDbList[0]);
            menupopup1.appendChild(menuitem1);
            menu1.appendChild(menupopup1)
            hbox.appendChild(label1);
            hbox.appendChild(menu1);
            vbox.appendChild(hbox);
            label.appendChild(vbox);

            var d = document.getElementById("first"); 
            var d_nested = document.getElementById("lbldb_list1"); 
            var throwawayNode = d.removeChild(d_nested);
            var d_nested = document.getElementById("DBlist_text"); 
            var throwawayNode = d.removeChild(d_nested);


        }
        else
        {
            setDBList("false");
        }
        // Loop through the results, adding items to the list
        if (count)
        {
            const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
            var popup = document.getElementById("DBlist"); // a <menupopup> element
            var arrsec=new Array()
            for (var i=0;i<popup.menupopup.childNodes.length;i++) {
                arrsec.push(popup.menupopup.childNodes[i].label)
            }
            for (i=0;i<arrDbList.length;i++){
                
                if (arrsec.indexOf(arrDbList[i])==-1) {
                    if (arrDbList[i] != database){
                        popup.menupopup.appendChild(createMenuItem_db(arrDbList[i]));
                    }
                }
            }
        }
    },


    onFault: function (client, ctxt, fault) {
        setDBList("false");
    },

    onError: function (client, ctxt, status, errorMsg) {
        setDBList("false");       
    }
};
//function to get the database list
function getDbList(argControl)
{
    setDBList("false");
    setconnect_server("true");
    // Enable correct security
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    // Get the instance of the XML-RPC client
    var xmlRpcClient = getXmlRpc();
    arrDbList = [];
    var cmbDbList = document.getElementById(argControl);

    xmlRpcClient.asyncCall(listDbHandler,cmbDbList,'list',[],0);
    return arrDbList;
}

function createMenuItem_partner(aLabel, aValue) {
    const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
    var item = document.createElementNS(XUL_NS, "menuitem"); // create a new XUL menuitem
    item.setAttribute("label", aLabel);
    item.setAttribute("value", aValue);
    return item;
}

//xmlrpc request handler for getting the list of All objects
var listAllDocumentHandler = {

    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var arrIdList = result.QueryInterface(Components.interfaces.nsISupportsArray);
                // Set the number of results
        var count = arrIdList.Count();

        // Loop through the results, adding items to the list
        for (i = 0; i < count; i++) {
            var strlResult = arrIdList.QueryElementAt(i, Components.interfaces.nsISupportsArray);
            var resultcount = strlResult.Count();
            var arrDataPair = new Array();
            arrDataPair[0] = strlResult.QueryElementAt(0, Components.interfaces.nsISupportsCString);
            arrDataPair[1] = strlResult.QueryElementAt(1, Components.interfaces.nsISupportsCString);
            arrPartnerList[i] = arrDataPair;
        }
        if (context)
        {
            const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
            var popup = document.getElementById("section"); // a <menupopup> element
            for (i=0;i<arrPartnerList.length;i++){
                popup.menupopup.appendChild(createMenuItem_partner(arrPartnerList[i][1],arrPartnerList[i][0]));
            }
        }
        popup_display = "no"
        searchCheckbox()
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}

var listAllCountryHandler = {

    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var arrIdList = result.QueryInterface(Components.interfaces.nsISupportsArray);
        var count = arrIdList.Count();
        // Loop through the results, adding items to the list
        for (i = 0; i < count; i++) {
            var strlResult = arrIdList.QueryElementAt(i, Components.interfaces.nsISupportsArray);
            var resultcount = strlResult.Count();
            var arrDataPair = new Array();
            arrDataPair[0] = strlResult.QueryElementAt(0, Components.interfaces.nsISupportsPRInt32);
          
            arrDataPair[1] = strlResult.QueryElementAt(1, Components.interfaces.nsISupportsCString);
            arrPartnerList[i] = arrDataPair;
        }
        if (!context)
        {
            const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
            var popup = document.getElementById("country"); // a <menupopup> element
            for (i=0;i<arrPartnerList.length;i++){
                popup.menupopup.appendChild(createMenuItem_partner(arrPartnerList[i][1],arrPartnerList[i][0]));
            }
        }
           
    },
    onFault: function (client, ctxt, fault) {
        
    },

    onError: function (client, ctxt, status, errorMsg) {
        
    }
}

var listAllStateHandler = {

    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var arrIdList = result.QueryInterface(Components.interfaces.nsISupportsArray);
                // Set the number of results
        var count = arrIdList.Count();
        
        // Loop through the results, adding items to the list
        for (i = 0; i < count; i++) {
            var strlResult = arrIdList.QueryElementAt(i, Components.interfaces.nsISupportsArray);
            var resultcount = strlResult.Count();
            var arrDataPair = new Array();
            arrDataPair[0] = strlResult.QueryElementAt(0, Components.interfaces.nsISupportsPRInt32);
            arrDataPair[1] = strlResult.QueryElementAt(1, Components.interfaces.nsISupportsCString);
            arrPartnerList1[i] = arrDataPair;

          
        }
        if (!context)
        {
            const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

            var popup = document.getElementById("state"); 
            // a <menupopup> element
            for (i=0;i<arrPartnerList1.length;i++){
                popup.menupopup.appendChild(createMenuItem_partner(arrPartnerList1[i][1],arrPartnerList1[i][0]));

            }
          //  popup.menupopup.selectedItem = popup.menupopup.firstChild;
        }
    
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}


//function to get the list of All object
function getAllDocument(){
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    var xmlRpcClient = getXmlRpc();
    arrPartnerList = [];
    var end = document.getElementById("section")
    length = end.itemCount
    for (i = 0; i < length; i++) {
        end.removeItemAt(0)
    }
    var cmdObjectList = document.getElementById("section");
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struid = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struid.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'list_alldocument';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var strvalue = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strvalue.data = ""
    xmlRpcClient.asyncCall(listAllDocumentHandler,cmdObjectList,'execute',[ strDbName,struid,strpass,strobj,strmethod,strvalue ],6);
}

function getAllCountry(){
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    var xmlRpcClient = getXmlRpc();
    arrPartnerList = [];
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struid = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struid.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'list_allcountry';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var strvalue = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strvalue.data = document.getElementById("country").value;
    xmlRpcClient.asyncCall(listAllCountryHandler,null,'execute',[ strDbName,struid,strpass,strobj,strmethod,strvalue ],6);
}

function getAllState(){
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    var xmlRpcClient = getXmlRpc();
    arrPartnerList1 = [];
    var state = document.getElementById('state').menupopup;
    while (state.firstChild) 
     {
        //The list is LIVE so it will re-index each call
        state.removeChild(state.firstChild);
    };


    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struid = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struid.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'list_allstate';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var strvalue = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strvalue.data = document.getElementById("country").value;
    xmlRpcClient.asyncCall(listAllStateHandler,null,'execute',[ strDbName,struid,strpass,strobj,strmethod,strvalue ],6);
}


//function to create array object to pass as an parameter for xmlrpc request
function dictcreation(value,checkboxobj){
    var temp = xmlRpcClient.createType(xmlRpcClient.ARRAY,{});
    var test = xmlRpcClient.createType(xmlRpcClient.ARRAY,{});
    var strkey = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strkey.data = value;
    test.AppendElement(strkey);
    temp.AppendElement(test);
    var test1 = xmlRpcClient.createType(xmlRpcClient.ARRAY,{});
    for(i=0;i<checkboxobj.length;i++){
        var strvalue = xmlRpcClient.createType(xmlRpcClient.STRING,{});
        strvalue.data = checkboxobj[i];
        test1.AppendElement(strvalue);
    }
    if(checkboxobj.length>0){
        temp.AppendElement(test1);
    }
    return temp;
}

//function to search and fillup section selection box
function createMenuItem(aLabel) {
  const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
  var item = document.createElementNS(XUL_NS, "menuitem"); // create a new XUL menuitem
  item.setAttribute("label", aLabel[1]);
  item.setAttribute("value", aLabel[0]);
  return item;
}


var listinstallmodulehandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var arrIdList = result.QueryInterface(Components.interfaces.nsISupportsArray);
        var count = arrIdList.Count();
        if (count > 0) 
        { 
            setmodule_install('yes')
        }
    
    },
    onFault: function (client, ctxt, fault) {
        setmodule_install('no')
    },

    onError: function (client, ctxt, status, errorMsg) {
        setmodule_install('no')
    }
}

function module_install()
{
    setmodule_install("no")
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struid = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struid.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'name_search';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'ir.model';
    var strvalue = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strvalue.data = 'thunderbird.partner';
    xmlRpcClient.asyncCall(listinstallmodulehandler,null,'execute',[ strDbName,struid,strpass,strobj,strmethod, strvalue],6);
}



var listSearchContactHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var sendername = getSenderEmail();
        var arrIdList = result.QueryInterface(Components.interfaces.nsISupportsArray);
        var count = arrIdList.Count();
        for (i = 0; i < count; i++) {
            var strlResult = arrIdList.QueryElementAt(i, Components.interfaces.nsISupportsArray);
            var strlSearchResult = strlResult.QueryElementAt(0, Components.interfaces.nsISupportsCString);
            var strlSearchResultValue = strlResult.QueryElementAt(1, Components.interfaces.nsISupportsCString);
            if(strlSearchResult=="partner_name"){
                 setPartnerName(strlSearchResultValue);
                 var t = getPartnerName();}

            if(strlSearchResult=="contactname"){
                 setSenderName(strlSearchResultValue);
                 var t = getSenderName();}
            
            if(strlSearchResult=="street"){
                 setStreet(strlSearchResultValue);
                 var t = getStreet();}
            
            if(strlSearchResult=="street2"){
                 setStreet2(strlSearchResultValue);
                 var t = getStreet2();}
            
            if(strlSearchResult=="zip"){
                 setZipCode(strlSearchResultValue);
                 var t = getZipCode();}

            if(strlSearchResult=="city"){
                 setCity(strlSearchResultValue);
                 var t = getCity();}
        
            if(strlSearchResult=="phone"){
                 setOfficenumber(strlSearchResultValue);
                 var t = getOfficenumber();}
        
            if(strlSearchResult=="fax"){
                 setFax(strlSearchResultValue);
                 var t = getFax();}
            
            if(strlSearchResult=="mobile"){
                 setMobilenumber(strlSearchResultValue);
                 var t = getMobilenumber();}

           if(strlSearchResult=="email" && strlSearchResultValue!=''){
                 setSenderEmail(strlSearchResultValue);
                 var t = getSenderEmail();
                 window.open("chrome://openerp_plugin/content/address.xul", "", "chrome, resizable=yes");} 
    
            if(strlSearchResult=="email" && strlSearchResultValue==''){
                alert("Contact is not available.");
            } 

            if(strlSearchResult=="res_id"){
                 setResourceId(strlSearchResultValue);
                 var t = getResourceId();}
        }
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }

}

var listSearchContactdetailHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
     //  var sendername = getSenderEmail();
        var sendername = document.getElementById("txtemail").value
        var arrIdList = result.QueryInterface(Components.interfaces.nsISupportsArray);
        var count = arrIdList.Count();
        for (i = 0; i < count; i++) {
            var strlResult = arrIdList.QueryElementAt(i, Components.interfaces.nsISupportsArray);
            var strlSearchResult = strlResult.QueryElementAt(0, Components.interfaces.nsISupportsCString);
            var strlSearchResultValue = strlResult.QueryElementAt(1, Components.interfaces.nsISupportsCString);
            if(strlSearchResult=="email" && strlSearchResultValue=='')
            {
                alert("Contact is not Available.")
                document.getElementById("txtemail").value = sendername;
            } 
            if(strlSearchResult=="partner_name"){
                 document.getElementById("txtselectpartner").value =strlSearchResultValue;}

            if(strlSearchResult=="contactname"){
                 document.getElementById("txtcontactname").value =strlSearchResultValue;}
            
            if(strlSearchResult=="street"){
                document.getElementById("txtstreet").value =strlSearchResultValue;}
            
            if(strlSearchResult=="street2"){
                 document.getElementById("txtstreet2").value =strlSearchResultValue;}
            if(strlSearchResult=="zip"){
                 document.getElementById("txtzip").value =strlSearchResultValue;}

            if(strlSearchResult=="city"){
                document.getElementById("txtcity").value =strlSearchResultValue;}
            if(strlSearchResult=="phone"){
                 document.getElementById("txtoffice").value =strlSearchResultValue;}
        
            if(strlSearchResult=="fax"){
                 document.getElementById("txtfax").value =strlSearchResultValue;}
            
            if(strlSearchResult=="mobile"){
                 document.getElementById("txtmobile").value =strlSearchResultValue;}

            if(strlSearchResult=="email"&& strlSearchResultValue!=''){
                 alert("Contact is Available.")
                 document.getElementById("txtemail").value =strlSearchResultValue;}

            if(strlSearchResult=="res_id"){
                 setResourceId(strlSearchResultValue);
                 var t = getResourceId();}

        }
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }

}

function searchContactdetail()
{
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    arrFinalList = [];
    var xmlRpcClient = getXmlRpc();
    var cmbSearchList = document.getElementById('listSearchBox');
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struid = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struid.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'search_contact';
    var strname = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strname.data = document.getElementById("txtemail").value;
    xmlRpcClient.asyncCall(listSearchContactdetailHandler,cmbSearchList,'execute',[ strDbName,struid,strpass,strobj,strmethod,strname ],6);
}

//xmlrpc request handler for getting the search results for the particular selected check box object
var listSearchCheckboxHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var arrMethodList = result.QueryInterface(Components.interfaces.nsISupportsArray);
                // Set the number of results
        var count = arrMethodList.Count();
        var close=0;
        if(count == 0  && popup_display != "no"){
            alert("No Records Found");
            return false;
        }
        else if(count ==2 )
        {
            if (arrMethodList.QueryElementAt(0, Components.interfaces.nsISupportsCString)=="error")
            {
                close =1;
            }
        }
        popup_display = "yes"
        // Loop through the results, adding items to the list
        var arr1 = new Array();
        var arr2 = new Array();
        var flag1 = 0;
        var flag2 = 0;
        var er ="";
        var er_val =new Array();
        for (i = 0; i < count; i++) 
        {
            if(i%2==0){
                if (arrMethodList.QueryElementAt(i, Components.interfaces.nsISupportsCString)=="error")
                {
                    er = arrMethodList.QueryElementAt(i, Components.interfaces.nsISupportsCString);
                    er_val[0] =arrMethodList.QueryElementAt(i+1, Components.interfaces.nsISupportsArray);
                    i +=1;
                    continue;
                }
                arr1[flag1] = arrMethodList.QueryElementAt(i, Components.interfaces.nsISupportsCString);
                flag1++;
            }
            else{
                arr2[flag2] = arrMethodList.QueryElementAt(i, Components.interfaces.nsISupportsArray);
                flag2++;
            }
        }
        if (er)
        {
            var arrSearchList1 = new Array();
            for(j=0;j<er_val[0].Count();j++)
            {
                var arrDataPair = new Array();
                arrDataPair[0] = er_val[0].QueryElementAt(j, Components.interfaces.nsISupportsCString)
                arrSearchList1[j]=arrDataPair;
            }
            alert( arrSearchList1 + "  Model not exists")
            if (close == 1)
            {
                alert("No Records Found");
                return false;
            }
        }
        for (i = 0; i < arr2.length; i++) {
            var arrSearchList1 = new Array();
            for(j=0;j<arr2[i].Count();j++){
                var strlSearchResult = arr2[i].QueryElementAt(j, Components.interfaces.nsISupportsArray);
                var resultcount = strlSearchResult.Count();
                var arrDataPair = new Array();
                arrDataPair[0] = strlSearchResult.QueryElementAt(0, Components.interfaces.nsISupportsPRInt32);
                arrDataPair[1] = strlSearchResult.QueryElementAt(1, Components.interfaces.nsISupportsCString);
                arrDataPair[2] = arr1[i];
                arrSearchList1[j] = arrDataPair;
            }
            arrFinalList[i]=arrSearchList1;
        }
        if (context)
        {

            var row_count = context.getRowCount();
            var cmbSearchList = document.getElementById('listSearchBox');
            for (i=0;i<row_count;i++)
            {
                context.removeItemAt(0);
            }
            for (i=0;i<arrFinalList.length;i++)
            {
                for(j=0;j<arrFinalList[i].length;j++){
                //creates the dynamic listbox which shows the searched records for the selected object in checkbox
                    var listcell = document.createElement("listcell");
                    var listItem = document.createElement("listitem");

                    var objectcharpref = getPref().getCharPref("object").split(',');
                    var imagecharpref = getPref().getCharPref("imagename").split(',');
                    var imagename = ''
                    for(k=0;k<objectcharpref.length;k++){
                        if(arr1[i] == objectcharpref[k]){
                            imagename = imagecharpref[k]
                        }
                    }

                    listcell.setAttribute("image",imagename); // stores the image of the object
                    listcell.setAttribute("class","listcell-iconic");
                    listcell.setAttribute("width",12);
                    listcell.setAttribute("height",12);
                    listcell.setAttribute("label",arrFinalList[i][j][1]); //stores the name ofthe record
                    listItem.appendChild(listcell);
                    listItem.value = arrFinalList[i][j][0]; //stores the id of the record
                    listItem.label = arr1[i]; // stores the value of the object   
                    cmbSearchList.appendChild(listItem);
                }
            }
        }
    },

    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
};

//function to search the records of selected checkbox object
function searchCheckbox()
{
    var checkboxlist = getnamesearch();
    if(checkboxlist.length == 0){
        alert("Please Select One or More Document");
        return false;
    }
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    arrFinalList = [];
    var xmlRpcClient = getXmlRpc();
    var end = document.getElementById('listSearchBox').getRowCount();
    for(i=0; i< end; i++){
        document.getElementById('listSearchBox').removeItemAt(0);
    }
    var cmbSearchList = document.getElementById('listSearchBox');
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struid = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struid.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'search_checkbox';
    var strname = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strname.data = document.getElementById('txtvalueobj').value;
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var arrofarr = dictcreation(strname,checkboxlist);
    xmlRpcClient.asyncCall(listSearchCheckboxHandler,cmbSearchList,'execute',[ strDbName,struid,strpass,strobj,strmethod,arrofarr ],6);
}

function searchContact()
{
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    arrFinalList = [];
    var xmlRpcClient = getXmlRpc();
    var cmbSearchList = document.getElementById('listSearchBox');
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struid = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struid.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'search_contact';
    var strname = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strname.data = getSenderEmail();
    
    xmlRpcClient.asyncCall(listSearchContactHandler,cmbSearchList,'execute',[ strDbName,struid,strpass,strobj,strmethod,strname ],6);
}

//xmlrpc request handler for getting the list of partners
var listPartnerHandler = {

    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var arrIdList = result.QueryInterface(Components.interfaces.nsISupportsArray);
                // Set the number of results
        var count = arrIdList.Count();
        // Loop through the results, adding items to the list
        for (i = 0; i < count; i++) {
            var strlResult = arrIdList.QueryElementAt(i, Components.interfaces.nsISupportsArray);
            var resultcount = strlResult.Count();
            var arrDataPair = new Array();
            arrDataPair[0] = strlResult.QueryElementAt(0, Components.interfaces.nsISupportsPRInt32);
            arrDataPair[1] = strlResult.QueryElementAt(1, Components.interfaces.nsISupportsCString);
            arrPartnerList[i] = arrDataPair;
        }
        if (context)
        {
            var row_count = context.getRowCount();
            var cmdPartnerList = document.getElementById('listPartnerBox');
            for (i=0;i<row_count;i++)
            {
                context.removeItemAt(0);
            }
            for (i=0;i<arrPartnerList.length;i++)
            {
                var listcell = document.createElement("listcell");
                var listItem = document.createElement("listitem");
                listcell.setAttribute("label",arrPartnerList[i][1]);
                listItem.appendChild(listcell);
                listItem.value = arrPartnerList[i][0];
                cmdPartnerList.appendChild(listItem);
            }
        }
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}

//function to get the list of partners
function getPartnerList(){
    var branchobj = getPref();
    window.opener.document.getElementById('txtselectpartner').setAttribute('value','');
    setServerService('xmlrpc/object');
    var xmlRpcClient = getXmlRpc();
    arrPartnerList = [];
    var end = document.getElementById('listPartnerBox').getRowCount();
    for(i=0; i< end; i++){
        document.getElementById('listPartnerBox').removeItemAt(0);
    }
    var cmdPartnerList = document.getElementById('listPartnerBox');
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struid = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struid.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'name_search';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'res.partner';
    var strvalue = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strvalue.data = document.getElementById('txtselectpartner').value;
    xmlRpcClient.asyncCall(listPartnerHandler,cmdPartnerList,'execute',[ strDbName,struid,strpass,strobj,strmethod,strvalue ],6);
}

//function to create the xmlrpc supported variables for xmlrpc request
function dictcontact(a,b){
    var temp = xmlRpcClient.createType(xmlRpcClient.ARRAY,{});
    for(i=0;i<a.length;i++){
        var strkey = xmlRpcClient.createType(xmlRpcClient.STRING,{});
        strkey.data = a[i]
        var strvalue = xmlRpcClient.createType(xmlRpcClient.STRING,{});
        strvalue.data = b[i]
        var test = xmlRpcClient.createType(xmlRpcClient.ARRAY,{});
        test.AppendElement(strkey);
        test.AppendElement(strvalue);
        temp.AppendElement(test);
    }
    return temp;
}

//xmlrpc request handler for creating the record of mail
var listArchiveHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        list_documents = document.getElementById('listSearchBox')
        var createId = result.QueryInterface(Components.interfaces.nsISupportsPRInt32);
        createId = parseInt(createId);
        if(createId==0)
        {
            alert("Mail is Already Pushed.");
        }
        else if (createId<0)
        {
            alert("sorry Mail is not Pushed.");
        
        }
    
    else if (createId>=1)
        {
            alert("Mail is Successfully Pushed.");
        }
    window.close();

    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}

//function to archive the mail content through xmlrpc request
function upload_archivemail()
{
    list_documents = document.getElementById('listSearchBox')
    var context = []
    var cnt = list_documents.selectedCount
    var ref_ids = "";
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struids = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struids.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'history_message';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var resobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});

	
    for(i=0;i<cnt;i++)
    {   
        var object = list_documents.getSelectedItem(i);
        var eml_string = parse_eml();
        ref_ids += object.label;
        ref_ids += ",";
        ref_ids += object.value;
        if (i < cnt-1){ref_ids += ";";}
        
    }
    var a = ['ref_ids','message'];
    var b = [ref_ids, eml_string];
    var arrofarr = dictcontact(a,b);
    xmlRpcClient.asyncCall(listArchiveHandler,null,'execute',[strDbName,struids,strpass,strobj,strmethod,arrofarr],6);
     
}

var listArchiveDocumentHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var createId = result.QueryInterface(Components.interfaces.nsISupportsPRInt32);
        var popup = document.getElementById("section").selectedItem; 
        alert("Document Created Successfully For " +" " + ":" + " "+ popup.label);
        window.close();

    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}

function create_archivemail(){
    var popup = document.getElementById("section").selectedItem; 
    // a <menupopup> element

    if (String(popup) != "null"){
        object=popup.value;
        if (object == undefined) { alert("select At Least one Document !")}
        else{
        var branchobj = getPref();
        setServerService('xmlrpc/object');
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var xmlRpcClient = getXmlRpc();
        var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
        strDbName.data = branchobj.getCharPref("serverdbname");
        var struids = xmlRpcClient.createType(xmlRpcClient.INT,{});
        struids.data = branchobj.getIntPref('userid');
        var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
        strpass.data = branchobj.getCharPref("password");
        var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
        strmethod.data = 'process_email';
        var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
        strobj.data = 'thunderbird.partner';
        var eml_string = parse_eml()
        var a = ['model', 'message'];
        var b = [object, eml_string];
        var arrofarr = dictcontact(a,b);
        xmlRpcClient.asyncCall(listArchiveDocumentHandler,null,'execute',[strDbName,struids,strpass,strobj,strmethod,arrofarr],6);
        //alert("Document Created Successfully For " +" " + ":" + " "+ popup.label);
        }
        //window.close();
    }
    else
    {
        alert(" select At Least one Document !")
    }
}


//xmlrpc request handler for creating a new contact
var listCreateContactHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var createId = result.QueryInterface(Components.interfaces.nsISupportsPRInt32);
        setContactId(createId);
        alert("Contact Created Successfully."); 
        window.close();
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}

var listUpdateContactHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        alert("Contact Update Successfully.");
        window.close();
        var partnerId = result.QueryInterface(Components.interfaces.nsISupportsPRInt32);
        setResourceId(partnerId);
        window.close();
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}

//function to create a new contact
function createContact(){
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struids = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struids.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'create_contact';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var a = ['partner_id','name','street','street2','zip','city','country_id','state_id','phone','fax','mobile','email'];
    var b = [getPartnerId(),document.getElementById("txtname").value,document.getElementById("txtstreet").value,document.getElementById("txtstreet2").value,document.getElementById("txtzip").value, document.getElementById("txtcity").value,document.getElementById("country").value,document.getElementById("state").value,document.getElementById("txtoffice").value,document.getElementById("txtfax").value,document.getElementById("txtmobile").value,document.getElementById("txtemail").value];
    var arrofarr = dictcontact(a,b);
    xmlRpcClient.asyncCall(listCreateContactHandler,null,'execute',[strDbName,struids,strpass,strobj,strmethod,arrofarr],6);
}

function UpdateContact(){
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struids = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struids.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'update_contact';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var a = ['res_id','partner_id','name','street','street2','zip','city','country_id','state_id','phone','fax','mobile','email'];
    var b = [getResourceId(),document.getElementById("txtselectpartner").value,document.getElementById("txtcontactname").value,document.getElementById("txtstreet").value,document.getElementById("txtstreet2").value,document.getElementById("txtzip").value, document.getElementById("txtcity").value,document.getElementById("country").value,document.getElementById("state").value,document.getElementById("txtoffice").value,document.getElementById("txtfax").value,document.getElementById("txtmobile").value,document.getElementById("txtemail").value];
    var arrofarr = dictcontact(a,b);
    xmlRpcClient.asyncCall(listUpdateContactHandler,null,'execute',[strDbName,struids,strpass,strobj,strmethod,arrofarr],6);
}

//xmlrpc request handler for creating a attachment record
var listAttachHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var createId = result.QueryInterface(Components.interfaces.nsISupportsPRInt32);

    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}


//function to encode the string into base64
var base64chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'.split("");
function base64_encode (s)
 {
   // the result/encrypted string, the padding string, and the pad count
   var r = ""; var p = ""; var c = s.length % 3;

   // add a right zero pad to make this string a multiple of 3 characters
   if (c > 0) { for (; c < 3; c++) { p += '='; s += "\0"; } }

   // increment over the length of the string, three characters at a time
   for (c = 0; c < s.length; c += 3) {

     // we add newlines after every 76 output characters, according to the MIME specs
     if (c > 0 && (c / 3 * 4) % 76 == 0) { r += "\r\n"; }

     // these three 8-bit (ASCII) characters become one 24-bit number
     var n = (s.charCodeAt(c) << 16) + (s.charCodeAt(c+1) << 8) + s.charCodeAt(c+2);

     // this 24-bit number gets separated into four 6-bit numbers
     n = [(n >>> 18) & 63, (n >>> 12) & 63, (n >>> 6) & 63, n & 63];

     // those four 6-bit numbers are used as indices into the base64 character list
     r += base64chars[n[0]] + base64chars[n[1]] + base64chars[n[2]] + base64chars[n[3]];

     // add the actual padding string, after removing the zero pad
   } return r.substring(0, r.length - p.length) + p;
 }

//function to encode the string into base64
var keyStr = "ABCDEFGHIJKLMNOP" +
                "QRSTUVWXYZabcdef" +
                "ghijklmnopqrstuv" +
                "wxyz0123456789+/" +
                "="+"-_.!~*'()";

function encode64(input) {
var output = "";
var chr1, chr2, chr3 = "";
var enc1, enc2, enc3, enc4 = "";
var i = 0;

do {
 chr1 = input.charCodeAt(i++);
 chr2 = input.charCodeAt(i++);
 chr3 = input.charCodeAt(i++);

 enc1 = chr1 >> 2;
 enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
 enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
 enc4 = chr3 & 63;

 if (isNaN(chr2)) {
    enc3 = enc4 = 64;
 } else if (isNaN(chr3)) {
    enc4 = 64;
 }

 output = output +
    keyStr.charAt(enc1) +
    keyStr.charAt(enc2) +
    keyStr.charAt(enc3) +
    keyStr.charAt(enc4);
 chr1 = chr2 = chr3 = "";
 enc1 = enc2 = enc3 = enc4 = "";
} while (i < input.length);

return output;
}


//function to read the contents of the attachment files from the temp folder
function createInstance(name,test){
    var encoded_string = '';
    var file_name = ''

    for(i=0;i<test.length;i++){
        var stream = Components.classes["@mozilla.org/network/file-input-stream;1"].createInstance(Components.interfaces.nsIFileInputStream);
        stream.init(test[i], 0x01, 00004, 0);
        var bstream = Components.classes["@mozilla.org/binaryinputstream;1"].createInstance(Components.interfaces.nsIBinaryInputStream);
        bstream.setInputStream(stream);
        var r = new Array();
            var fileContents = bstream.readByteArray(bstream.available(),r);
        bstream.close();
        var printstring = '';
        for(j=0;j<fileContents.length;j++)
        {
            printstring += String.fromCharCode(fileContents[j]);
        }
        encoded_string += encode64(printstring)+',';
        file_name += name[i]+',';
        test[i].remove(true);
    }
    encoded_string = encoded_string.substring(0,encoded_string.length-1);
    file_name = file_name.substring(0,file_name.length-1);
    getPref().setCharPref('displayName',file_name);
    getPref().setCharPref('attachmentdata',encoded_string);


}

//xmlrpc request handler for handling the login information
function check_module_install(count){
    if (getmodule_install() == "no")
    {
        if (count <= 0){ return false; }
        count = count - 1;
        return check_module_install(count)
    }
    return true
}
    
var listLoginHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var login = result.QueryInterface(Components.interfaces.nsISupportsPrimitive)
        if(login.type == 12){
            login = result.QueryInterface(Components.interfaces.nsISupportsPRInt32)
            setUserId(login.data);
            module_install();
            alert('Successfully Login To OpenERP.');
            window.close();
        }
        else{
            alert("Login Failed");
        }
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {
        alert("Database does not Exist!\n\n Please specify proper database name.");
    }
}


//function to check the login information
function testConnection(){
    if (getconnect_server() == "false")
    {
        alert("Server is Not Running...Please check it!!"+" "+getServer())
        return false;
    }
    if (getDBList()=="false")
    {
        if (document.getElementById('DBlist_text').value =='')
        {
            alert("You Must Enter Database Name.");
            return false;
        }
        setDbName(document.getElementById('DBlist_text').value);
    }
    else
    {
        if (document.getElementById('DBlist').value == 0 || document.getElementById('DBlist').value =="--select--")
        {
            alert("You Must Select Database Name.");
            return false;
        }
        setDbName(document.getElementById('DBlist').value);
    }
    var branchobj = getPref();
    setServer(document.getElementById('txturl').value);
        var s = document.getElementById('txturl').value;
    var a =s.split(':');
    setPort(a[a.length-1]);
    setUsername(document.getElementById('txtusername').value);
    setPassword(document.getElementById('txtpassword').value);
    setServerService('xmlrpc/common');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = getPref().getCharPref('serverdbname');
    var strusername = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strusername.data = getPref().getCharPref('username');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = getPref().getCharPref('password');
    xmlRpcClient.asyncCall(listLoginHandler,null,'login',[strDbName,strusername,strpass],3);
    
}

function testConnection_web(){
    var branchobj = getPref();
    weburl = getWebServerURL();
    var messenger = Components.classes["@mozilla.org/messenger;1"].createInstance();
    messenger = messenger.QueryInterface(Components.interfaces.nsIMessenger);
    messenger.launchExternalURL(weburl);
    
}

//xmlrpc request handler for handling the login information
var listcreateLoginHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var login = result.QueryInterface(Components.interfaces.nsISupportsPrimitive)
        setconnect_server("true")       
        if(login.type == 12){
            login = result.QueryInterface(Components.interfaces.nsISupportsPRInt32)
            setUserId(login.data);
        }
        else{
            alert("Login Failed.");
        }
    },
    onFault: function (client, ctxt, fault) {
        
    },

    onError: function (client, ctxt, status, errorMsg) {
        setconnect_server("false")
    }
}

//function to check the login information
function createConnection(){
    setconnect_server("true");
    var branchobj = getPref();
    setServerService('xmlrpc/common');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = getPref().getCharPref('serverdbname');
    var strusername = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strusername.data = getPref().getCharPref('username');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = getPref().getCharPref('password');
    xmlRpcClient.asyncCall(listcreateLoginHandler,null,'login',[strDbName,strusername,strpass],3);
}

//xmlrpc request handler for handling the partner information
var listCreatePartnerHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var createId = result.QueryInterface(Components.interfaces.nsISupportsPRInt32);
        setPartnerId(createId);
        txtselectpartner = document.getElementById('txtselectpartner')
        if(typeof(createId.data) == 'number' && createId!=0){
         window.opener.document.getElementById('txtselectpartner').setAttribute('value',txtselectpartner.value);
            window.close();
        }
        if(createId == 0){
            alert("Partner Already Exist.");
        }
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}
//function to create the tiny partner object
function createPartner(){
    var branchobj = getPref();
    txtselectpartner = document.getElementById('txtselectpartner')
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struids = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struids.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'create_partner';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    if(document.getElementById('txtselectpartner').value ==''){
        alert("You Must Enter Partner Name.");
        return false;
    }
    setPartnerId(txtselectpartner.value)
    var a = ['partner_id','name'];
    var b = [getPartnerId(),txtselectpartner.value];
    var arrofarr = dictcontact(a,b);
    xmlRpcClient.asyncCall(listCreatePartnerHandler,null,'execute',[strDbName,struids,strpass,strobj,strmethod,arrofarr],6);
}
//xmlrpc request handler for handling the object information
var listSearchDocumentHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var searchResult = result.QueryInterface(Components.interfaces.nsISupportsPRInt32);
        if(searchResult.data == 0){
            alert("Document Does Not Exist.");
            return false;
        }
        var objvalue = getPref().getCharPref("listobject");
        var objectvalue = getPref().getCharPref("object");
        var imagevalue = getPref().getCharPref("imagename");

        var objcharpref = getPref().getCharPref("listobject").split(',');
        var objectcharpref = getPref().getCharPref("object").split(',');
        var imagecharpref = getPref().getCharPref("imagename").split(',');


        if(objectcharpref.indexOf(document.getElementById("txtobject").value) != -1){
            alert("Document already in List.");
        }
        else{
            var listItem = document.createElement("listitem");
            var listcell1 = document.createElement("listcell");
            var listcell2 = document.createElement("listcell");
            var listcell3 = document.createElement("listcell");
            listcell1.setAttribute("label",document.getElementById("txtobj").value);
            listcell2.setAttribute("label",document.getElementById("txtobject").value);
            listcell3.setAttribute("image",'file://'+document.getElementById("txtimagename").value);
            listcell3.setAttribute("class","listcell-iconic")
            listcell3.setAttribute("width",16)
            listcell3.setAttribute("height",16)
            listItem.appendChild(listcell1);
            listItem.appendChild(listcell2);
            listItem.appendChild(listcell3);
            document.getElementById("listObjectListBox").appendChild(listItem)
            if(getPref().getCharPref("object")!=''){
                getPref().setCharPref("listobject",objvalue+','+document.getElementById("txtobj").value);
                getPref().setCharPref("object",objectvalue+','+document.getElementById("txtobject").value);
                getPref().setCharPref("imagename",imagevalue+','+"file://"+document.getElementById("txtimagename").value);
            }
            else{
                getPref().setCharPref("listobject",document.getElementById("txtobj").value);
                getPref().setCharPref("object",document.getElementById("txtobject").value);
                getPref().setCharPref("imagename","file://"+document.getElementById("txtimagename").value);
            }
        }
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}

//function to search the tiny objects for configuration settings
function searchDocument(){
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struids = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struids.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'search_document';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    if(document.getElementById('txtobj').value =='' ){
        alert("You Must Enter Document.");
        return false;
    }
    if(document.getElementById('txtobject').value =='' ){
        alert("You Must Enter Document Name.");
        return false;
    }
    var a = ['model'];
    var b = [document.getElementById('txtobject').value];
    var arrofarr = dictcontact(a,b);
    xmlRpcClient.asyncCall(listSearchDocumentHandler,null,'execute',[strDbName,struids,strpass,strobj,strmethod,arrofarr],6);
}

//xmlrpc request handler for list of search object exist in database or not.
var listsearchAttachmentHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var objectlist = result.QueryInterface(Components.interfaces.nsISupportsCString);
        getPref().setCharPref('tempobject',objectlist)
        //document.getElementById("txtvalueobj").value= getSenderEmail();
        var checkbox = document.getElementById("checkbox-dynamic");
        
        var object = preferenceBranch.getCharPref("listobject").split(',');
        var obj = preferenceBranch.getCharPref("tempobject").split(',');
        var imagelist = preferenceBranch.getCharPref("imagename").split(',');

        count = 0
        if (object[0]!=''){
            for(var i=0; i<object.length; i++){
                if (obj[i] == "null")
                {
                    continue
                }

                if(count%3==0){
                    var vbox = document.createElement("hbox");
                }
                count += 1
                var hbox = document.createElement("vbox");
                var checkbox1 = document.createElement("checkbox");
            
                checkbox1.setAttribute("label",object[i]);
                checkbox1.setAttribute("id","cbx"+(i+1));
                checkbox1.setAttribute("width",150)
                if (obj[i] =="res.partner.address")
                {
                    checkbox1.setAttribute("checked",true);
                }
                if(i==0){
                    checkbox1.setAttribute("checked",true);
                }

                var image1 = document.createElement("image");
                image1.setAttribute("src",imagelist[i]);
                image1.setAttribute("width",16)
                image1.setAttribute("height",16)

                vbox.appendChild(image1);
                hbox.appendChild(checkbox1);
                vbox.appendChild(hbox);
                checkbox.appendChild(vbox);
            }
        }
        setTimeout("getAllDocument()", 0)
        exis_grp = document.getElementById("existsobjectgroup")
        new_grp = document.getElementById("newobjectgroup")

        new_grp.height = parseInt(parseInt(new_grp.height) + parseInt((count /3) * 23.5))
        win = document.getElementById("pluginwindows").setAttribute("height",1000)

    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
}

//function to create a new attachment record
function listSearchDocumentAttachment(){
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strDbName.data = branchobj.getCharPref("serverdbname");
    var struids = xmlRpcClient.createType(xmlRpcClient.INT,{});
    struids.data = branchobj.getIntPref('userid');
    var strpass = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strpass.data = branchobj.getCharPref("password");
    var strmethod = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strmethod.data = 'search_document_attachment';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var resobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    var popup = document.getElementById("section").selectedItem; // a <menupopup> element
    object=popup.value;
    resobj.data = object;
    var a = ['object'];
    var b = [getPref().getCharPref("object")];
    var arrofarr = dictcontact(a,b);
    xmlRpcClient.asyncCall(listsearchAttachmentHandler,null,'execute',[strDbName,struids,strpass,strobj,strmethod,arrofarr],6);
}


//function to create a new attachment record

function win_close()
{
    var fpath =""
    if(navigator.userAgent.indexOf('Linux')!= -1){
        fpath ="/tmp/"
    }
    else if(navigator.userAgent.indexOf('Win')!= -1){
        fpath ="C:\\"
    }
    else if(navigator.userAgent.indexOf('Mac OS X')!= -1){ 
        fpath ="/tmp/"
    } 
    try
      {
        name = fpath + getFileName() +".eml"

        var file = Components.classes["@mozilla.org/file/local;1"].createInstance(Components.interfaces.nsILocalFile);
        file.initWithPath( name );
        file.remove(true);
        window.close();
      }
    catch(err)
      {
        window.close();
      }
}

function attachmentWidnowOpen(msg)
{

        if (msg=="create")
        {
            var popup = document.getElementById("section").selectedItem; // a <menupopup> element
            if (String(popup) != "null"){
                object=popup.value;
                if (object=="" || object == undefined) { alert("select at least one document !")}
                else{
                    create_archivemail()
                }
            }
            else
            {
                alert("select at least one Document !")
            }
        }
        else if (msg=="upload")
        {   
            if(document.getElementById('listSearchBox').selectedItem)
            {   
                upload_archivemail()
            }
            else{
                alert("Please select at least one record");
            }
        }
}
