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

function searchmail()
{   
    var prefService = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefService);
    var dirService = Components.classes["@mozilla.org/file/directory_service;1"].
    	getService(Components.interfaces.nsIProperties).get("Home", Components.interfaces.nsIFile);
    
    
    //gives the selected email uri
    var messageUri= gDBView.URIForFirstSelectedMessage;

    var messenger = Components.classes['@mozilla.org/messenger;1'].createInstance(Components.interfaces.nsIMessenger);

    //gives the selected email object
    var message = messenger.messageServiceFromURI(messageUri).messageURIToMsgHdr(messageUri);

    //gives the received email date
    var stdate = new Date(message.date / 1000);

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
        senderemail = message.author
    }

    //gives the receiver email address
    receiveremail = message.mime2DecodedRecipients;

    //parsing the received date in the particular format
    receivedDate = stdate.getFullYear()+'/'+(stdate.getMonth()+1)+'/'+stdate.getDate();

    //gives the selected email subject
    subject = message.subject;
    log_message("subject: " + subject)
    var uri = message.folder.getUriForMsg(message);
    var messagebody = getMessage(uri);
    getPref().setCharPref('email_text', messagebody);

 
    //set the initial information for the selected email
    window.open("chrome://openerp_plugin/content/push.xul", "", "chrome, resizable=yes");
}


var openPartnerHandler = {
    onResult: function(client, context, result) {
    	log_message('get partner')
    	log_message(1)
        res = extract_data(result)
        log_message(2)
        log_message(res[RES_ID])
        log_message(3)
        log_message(res[URL])
        log_message(4)
        if(res[RES_ID]==0)
        {
            alert("Partner is not Available.");
            window.open("chrome://openerp_plugin/content/create.xul", "", "chrome, resizable=yes");
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
        log_message("open document")
        window.open('chrome://openerp_plugin/content/push_dialog.xul', '', 'chrome', resizable='yes');
        if(res[RES_ID]==0) {
            setPreference('statutdoc','create');
        }
        else {
            setPreference('statutdoc', 'open');
            setPreference('urldoc', res[URL]);
        } 
       setPreference('message_label',setPreference('subject'));// to have the subject to print on the push dialog       

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
