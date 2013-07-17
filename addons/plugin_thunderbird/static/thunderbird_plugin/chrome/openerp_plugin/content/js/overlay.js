//global array creation and declaration

var MBstrBundleService = Components.classes["@mozilla.org/intl/stringbundle;1"].
            getService(Components.interfaces.nsIStringBundleService);
var mboximportbundle = MBstrBundleService.createBundle("chrome://mboximport/locale/mboximport.properties"); 
//function to get the required details of the selected email

function check(fun) {
	cb = function() {
		if(GetNumSelectedMessages() < 1 || GetNumSelectedMessages() > 1) {
	        alert("You must select only one mail to archive");
	        return false
    	}
    	return fun()
	}
    if(getPreference('userid', 'INT') == 0 || getmodule_install() == "no") {
    	callback = check_connection(cb)
    	login()
    	return False
    }
    
    return cb()

}

var openPartnerHandler = {
    onResult: function(client, context, result) {
        res = extract_data(result)
        if(res[RES_ID]==0) {
        	open_window("chrome://openerp_plugin/content/create.xul", 550, 250);
            return;
        } 
        open_url(res[URL])
        
        
        
    },
    onFault: function (client, ctxt, fault) {
		log_message(fault);
    },

    onError: function (client, ctxt, status, errorMsg) {
		log_message(errorMsg)
    }

}

function searchPartner(email)
{
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');

    var xmlRpcClient = getXmlRpc();
    var strDbName = get_rpc_string(xmlRpcClient, getPreference("serverdbname"));
    var struid = get_rpc_int(xmlRpcClient, getPreference('userid', 'INT'));
    var strpass = get_rpc_string(xmlRpcClient, getPreference("password"));
    var strobj = get_rpc_string(xmlRpcClient, 'plugin.handler');
    var strmethod = get_rpc_string(xmlRpcClient, 'partner_get');
    var strname = get_rpc_string(xmlRpcClient, email);
    xmlRpcClient.asyncCall(openPartnerHandler,null,'execute',[ strDbName,struid,strpass,strobj,strmethod,strname ],6);
}


function open_partner()
{
    //gives the selected email uri
    var messageUri= gDBView.URIForFirstSelectedMessage;
    

    var messenger = Components.classes['@mozilla.org/messenger;1'].createInstance(Components.interfaces.nsIMessenger);

    //gives the selected email object 
    var message = messenger.messageServiceFromURI(messageUri).messageURIToMsgHdr(messageUri);
    //functionality to split the author name and email
    if(message.author.charAt(0) == '"'){
        sendername = message.author.split('"')[1].split('"')[0];
    }
    else if(message.author.indexOf('<')!=-1){
        sendername = message.author.split('<')[0];
    }
    else{
        sendername = message.author;
    }
    if(message.author.indexOf('<')!=-1){
        senderemail = message.author.split('<')[1].split('>')[0];
    }
    else{
        senderemail = message.author;
    }
    setPreference('senderemail', senderemail);
    setPreference('sendername', sendername);
    searchPartner(senderemail);
}


var listDocumentHandler = {
    onResult: function(client, context, result) {
        res = extract_data(result)
        
        if(res[RES_ID]==0) {
            setPreference('statutdoc','create');
        }
        else {
            setPreference('statutdoc', 'open');
            setPreference('urldoc', res[URL]);
        } 
       open_window("chrome://openerp_plugin/content/push_dialog.xul", 480, 110);       

    },
    onFault: function (client, ctxt, fault) {
		log_message(fault);
    },

    onError: function (client, ctxt, status, errorMsg) {
		log_message(errorMsg)
    }
} 

function open_document() {
    var prefService = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefService);

    //gives the selected email uri
    var messageUri = gDBView.URIForFirstSelectedMessage;
    
    var branchobj = getPref();
    
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    
    var xmlRpcClient = getXmlRpc();
    var strDbName = get_rpc_string(xmlRpcClient, branchobj.getCharPref("serverdbname"));
    var struids = get_rpc_int(xmlRpcClient, branchobj.getIntPref('userid'));
    var strpass = get_rpc_string(xmlRpcClient, branchobj.getCharPref("password"));
    var strmethod = get_rpc_string(xmlRpcClient, 'document_get');
    
    var strobj = get_rpc_string(xmlRpcClient, 'plugin.handler');
    
    var eml_string = getMessage(messageUri);
    setPreference('email_text', eml_string);
    var email = get_rpc_string(xmlRpcClient, eml_string);
    xmlRpcClient.asyncCall(listDocumentHandler,null,'execute',[strDbName,struids,strpass,strobj,strmethod, email],6);
}
