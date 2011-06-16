//global array creation and declaration
var contentType = new Array();
var uri = new Array();
var url = new Array();
var name = new Array();
var test = new Array();

var MBstrBundleService = Components.classes["@mozilla.org/intl/stringbundle;1"].
            getService(Components.interfaces.nsIStringBundleService);
var mboximportbundle = MBstrBundleService.createBundle("chrome://mboximport/locale/mboximport.properties"); 
//function to get the required details of the selected email

function check()
{
    setTimeout("createConnection()",5000)
    if (getconnect_server() == "false")
    {
        alert("Please Login To The Database First !")
        return false;
    }
    setTimeout("module_install()", 10000)
    if (getmodule_install() == "no")
    {
        alert("Please install the thunderbird module on your '" + getDbName() +"' database and try again !");
        return false
    }
    if(GetNumSelectedMessages() < 1 || GetNumSelectedMessages() > 1){
        alert("You must select only one mail to archive");
        return false
    }
    return true

}

function searchmail()
{   
    if (check() == false){
        return true
    }
    var prefService = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefService);
    var dirService = Components.classes["@mozilla.org/file/directory_service;1"].
    	getService(Components.interfaces.nsIProperties).get("Home", Components.interfaces.nsIFile);
    var homeDir = dirService.path;
    var path = ((homeDir.search(/\\/) != -1) ? homeDir + "\\" : homeDir + "/")
    var version_obj = prefService.getBranch("extensions.");
    version_obj.QueryInterface(Components.interfaces.nsIPrefBranch2);
    version = version_obj.getCharPref("lastAppVersion");
    version = parseInt(version[0])
    
    file = getPredefinedFolder(2);
    
    if (version > 2)
    {
        var emlsArray = gFolderDisplay.selectedMessages;
    }
    else
    {
        var emlsArray = GetSelectedMessages();
    }

    IETtotal = emlsArray.length;
    IETexported = 0;
    var msguri = emlsArray[0];

    
    //gives the selected email uri
    var messageUri= gDBView.URIForFirstSelectedMessage;

    var messenger = Components.classes['@mozilla.org/messenger;1'].createInstance(Components.interfaces.nsIMessenger);

    //gives the selected email object
    var message = messenger.messageServiceFromURI(messageUri).messageURIToMsgHdr(messageUri);


    if (version > 2)
    {
        m_uri = message.folder.getUriForMsg(message);
        saveMsgAsEML(m_uri,file,false,emlsArray,null);
    }
    else
    {
        saveMsgAsEML(msguri,file,false,emlsArray,null);
    }

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

    //gives the selected email cclist
    cclist = message.ccList;

    //gives the selected email message body in text format
    if (version > 2)
    {
        var listener = Components.classes["@mozilla.org/network/sync-stream-listener;1"].createInstance(Components.interfaces.nsISyncStreamListener);  
        var uri = message.folder.getUriForMsg(message);
        messenger.messageServiceFromURI(uri)  
            .streamMessage(uri, listener, null, null, false, "");    
        var folder = message.folder;  
        messagebody = folder.getMsgTextFromStream(listener.inputStream,message.Charset,65536,32768,false,true,{})
    }
    else
    {
        messagebody = getMessageBrowser().docShell.contentViewer.DOMDocument.body.textContent;
    }
    //gives the selected email message body in html format
    msghtmlbody = ""// getMessageBrowser().docShell.contentViewer.DOMDocument.body.innerHTML;

    //set the initial information for the selected email
    setSenderEmail(senderemail);
    setSenderName(sendername);
    setReceiverEmail(receiveremail);
    setSubject(subject);
    setReceivedDate(receivedDate);
    setCCList(cclist);
    setMessageBody(messagebody);
    getPref().setCharPref('displayName','');
    getPref().setCharPref('attachmentdata','');
    name = [];
    test = [];
    getPref().setCharPref('attachmentlength',currentAttachments.length);
    //retrieving the information for the selected email's attachment
    if(currentAttachments.length > 0){
        for(i=0;i<currentAttachments.length;i++){
            contentType[i] = currentAttachments[i].contentType;
            uri = currentAttachments[i].uri;
            url[i] = currentAttachments[i].url;
            name[i] = currentAttachments[i].displayName;
            var obj = Components.classes["@mozilla.org/file/local;1"].createInstance(Components.interfaces.nsILocalFile);
            obj.initWithPath(path)
            //saving the attachment files in system's temp folder
            test[i] = messenger.saveAttachmentToFolder(contentType[i],url[i],name[i],uri,obj);
        }
        //function to read the attachment file contents
        att =getAttachValue()
        window.open("chrome://openerp_plugin/content/plugin.xul", "", "chrome, resizable=yes");
        createInstance(name,test)

    }
    else
    {
        window.open("chrome://openerp_plugin/content/plugin.xul", "", "chrome, resizable=yes");
    }
}


var openPartnerHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
     //  var sendername = getSenderEmail();
        var arrIdList = result.QueryInterface(Components.interfaces.nsISupportsArray);
        var count = arrIdList.Count();
        for (var i = 0; i < count; i++) {
            var strlResult = arrIdList.QueryElementAt(i, Components.interfaces.nsISupportsArray);
            var strlSearchResult = strlResult.QueryElementAt(0, Components.interfaces.nsISupportsCString);
            var strlSearchResultValue = strlResult.QueryElementAt(1, Components.interfaces.nsISupportsCString);
            if(strlSearchResult=="email" && strlSearchResultValue=='')
            {
                alert("Partner is not Available.");
                return;
            } 
            if(strlSearchResult=="partner_id"){
                partner_id = strlSearchResultValue;
                weburl = getWebServerURL();

                if (parseInt(partner_id) > 0){
                    //Encode the url and form an url to have menu in webclient
                    var encoded = encodeURIComponent("/openerp/form/view?model=res.partner&id="+partner_id)
                    var t = weburl + "?next=" + encoded
                    var messenger = Components.classes["@mozilla.org/messenger;1"].createInstance();
                    messenger = messenger.QueryInterface(Components.interfaces.nsIMessenger);
                    messenger.launchExternalURL(t);
                }
                else{
                    alert("Partner is not Available.");
                    return;
                }
            }
        }
    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }

}

function searchPartner(email)
{
    var branchobj = getPref();
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    arrFinalList = [];
    var xmlRpcClient = getXmlRpc();
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
    strname.data = email;
    xmlRpcClient.asyncCall(openPartnerHandler,null,'execute',[ strDbName,struid,strpass,strobj,strmethod,strname ],6);
}


function open_partner()
{
    if (check() == false){
        return true
    }
    var prefService = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefService);
    var version_obj = prefService.getBranch("extensions.");
    version_obj.QueryInterface(Components.interfaces.nsIPrefBranch2);
    version = version_obj.getCharPref("lastAppVersion");
    version = parseInt(version[0])
    
    file = getPredefinedFolder(2);
    
    if (version > 2)
    {
        var emlsArray = gFolderDisplay.selectedMessages;
    }
    else
    {
        var emlsArray = GetSelectedMessages();
    }

    IETtotal = emlsArray.length;
    IETexported = 0;
    var msguri = emlsArray[0];

    
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
        senderemail = message.author
    }
    searchPartner(senderemail);
}


var listDocumentHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var res = result.QueryInterface(Components.interfaces.nsISupportsArray);
        res_id = res.QueryElementAt(1, Components.interfaces.nsISupportsPRInt32);
        model = res.QueryElementAt(0, Components.interfaces.nsISupportsCString); 
        weburl = getWebServerURL();
        if(res_id==0)
        {
            alert("Document is not available.");
            return;
        }
        else
        {
    
            var encoded = encodeURIComponent("/openerp/form/view?model=" + model +"&id=" + res_id)
            var t = weburl + "?next=" + encoded
            var messenger = Components.classes["@mozilla.org/messenger;1"].createInstance();
            messenger = messenger.QueryInterface(Components.interfaces.nsIMessenger);
            messenger.launchExternalURL(t);
        }

    },
    onFault: function (client, ctxt, fault) {

    },

    onError: function (client, ctxt, status, errorMsg) {

    }
} 

//function to archive the mail content through xmlrpc request
function parse_eml(){
    var fpath =""
    var dirService = Components.classes["@mozilla.org/file/directory_service;1"].
        getService(Components.interfaces.nsIProperties).get("Home", Components.interfaces.nsIFile);
    var homeDir = dirService.path;
    fpath = ((homeDir.search(/\\/) != -1) ? homeDir + "\\" : homeDir + "/")
    name = fpath + getPref().getCharPref('fname') +".eml"
    var file = Components.classes["@mozilla.org/file/local;1"].createInstance(Components.interfaces.nsILocalFile);
    file.initWithPath( name );
    if ( file.exists() == false ) {
        return null;
    } else {
        var is = Components.classes["@mozilla.org/network/file-input-stream;1"].createInstance( Components.interfaces.nsIFileInputStream );
        is.init( file,0x01, 00004, null);
        var sis = Components.classes["@mozilla.org/scriptableinputstream;1"].createInstance( Components.interfaces.nsIScriptableInputStream );
        sis.init( is );
        var output = sis.read( sis.available() );
        return output
    }
    
}
function open_document()
{
    if (check() == false){
        return true
    }
    var prefService = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefService);
    var version_obj = prefService.getBranch("extensions.");
    version_obj.QueryInterface(Components.interfaces.nsIPrefBranch2);
    version = version_obj.getCharPref("lastAppVersion");
    version = parseInt(version[0])
    file = getPredefinedFolder(2);
    if (version > 2)
    {
        var emlsArray = gFolderDisplay.selectedMessages;
    }
    else
    {
        var emlsArray = GetSelectedMessages();
    }
    IETtotal = emlsArray.length;
    IETexported = 0;
    var msguri = emlsArray[0];
    //gives the selected email uri
    var messageUri= gDBView.URIForFirstSelectedMessage;
    var messenger = Components.classes['@mozilla.org/messenger;1'].createInstance(Components.interfaces.nsIMessenger);
    //gives the selected email object
    var message = messenger.messageServiceFromURI(messageUri).messageURIToMsgHdr(messageUri);
    if (version > 2)
    {
        m_uri = message.folder.getUriForMsg(message);
        saveMsgAsEML(m_uri,file,false,emlsArray,null);
    }
    else
    {
        saveMsgAsEML(msguri,file,false,emlsArray,null);
    }
    //gives the received email date
    var stdate = new Date(message.date / 1000);
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
    strmethod.data = 'search_message';
    var strobj = xmlRpcClient.createType(xmlRpcClient.STRING,{});
    strobj.data = 'thunderbird.partner';
    var eml_string = parse_eml()
    var a = ['message'];
    var b = [eml_string];
    var arrofarr = dictcontact(a,b); 
    xmlRpcClient.asyncCall(listDocumentHandler,null,'execute',[strDbName,struids,strpass,strobj,strmethod,arrofarr],6);
}

function open_contact()
{   
    if (check() == false){
        return true
    }
    
    var prefService = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefService);
    var version_obj = prefService.getBranch("extensions.");
    version_obj.QueryInterface(Components.interfaces.nsIPrefBranch2);
    version = version_obj.getCharPref("lastAppVersion");
    version = parseInt(version[0])
    
    file = getPredefinedFolder(2);
    
    if (version > 2)
    {
        var emlsArray = gFolderDisplay.selectedMessages;
    }
    else
    {
        var emlsArray = GetSelectedMessages();
    }

    IETtotal = emlsArray.length;
    IETexported = 0;
    var msguri = emlsArray[0];

    
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
        senderemail = message.author
    }

    //set the initial information for the selected email
    setSenderEmail(senderemail);
    setSenderName(sendername);
    setPartnerName("");
    setStreet("");
    setStreet2("");
    setZipCode("");
    setCity("");
    setOfficenumber("");
    setFax("");
    setMobilenumber("");
    searchContact();
}


//function to open the configuration window
var Config = {
  onLoad: function() {
    // initialization code
    this.initialized = true;
  },

  onMenuItemCommand: function() {
    window.open("chrome://openerp_plugin/content/config.xul", "", "chrome");
  }
};
window.addEventListener("load", function(e) { Config.onLoad(e); }, false);

//function to open the plugin window for searching the records for a particular object
var Plugin = {
    onLoad: function() {
    this.initialized = true;
    },

    onMenuItemCommand: function() {
        window.open("chrome://openerp_plugin/content/plugin.xul", "", "chrome, resizable=yes");
    }
};
window.addEventListener("load", function(e) { Plugin.onLoad(e); }, false);

//function to open the window for creating a new partner contact
var Create = {
    onLoad: function(){
    this.initialized=true;
    },

    onMenuItemCommand: function(){
        window.open("chrome://openerp_plugin/content/create.xul", "", "chrome");
    }
};
window.addEventListener("load", function(e) { Create.onLoad(e); }, false);

var Address = {
    onLoad: function(){
    this.initialized=true;
    },

    onMenuItemCommand: function(){
       open_contact();
       
    }
};


//function to open the window for selecting the partner for a new contact creation
var Select = {
    onLoad: function(){
    this.initialized=true;
    },

    onMenuItemCommand: function(){
        // document.getElementById("txtselectpartner").value="";
         window.open("chrome://openerp_plugin/content/selectpartner.xul", "", "chrome");
    }
};


var CreatePartner = {
    onLoad: function(){
    this.initialized=true;
    },

    onMenuItemCommand: function(){
        window.open("chrome://openerp_plugin/content/createpartner.xul", "", "chrome");
    }
};
window.addEventListener("load", function(e) { CreatePartner.onLoad(e); }, false);

