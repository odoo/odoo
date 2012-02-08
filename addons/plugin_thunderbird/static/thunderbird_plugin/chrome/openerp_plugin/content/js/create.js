function load_createContact() {
    document.getElementById("txtname").value = getSenderName();
    document.getElementById("txtemail").value = getSenderEmail();
    setPartnerId(0);
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

function selectPartner(){
	var item = document.getElementById('listPartnerBox').selectedItem
	if(item) {
		var label = item.label;
		setPartnerId(item.value);
		document.getElementById('txtselectpartner').setAttribute('value', label);
		window.opener.document.getElementById('txtselectpartner').setAttribute('value', label);
	}
}

function clear() {
	setPartnerId(0);
	document.getElementById('txtselectpartner').setAttribute('value', '');
}


//xmlrpc request handler for getting the list of partners
var listPartnerHandler = {

    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var arrMethodList = result.QueryInterface(Components.interfaces.nsISupportsArray);
                // Set the number of results
        var count = arrMethodList.Count();
        var close=0;
        clear_search_box('listPartnerBox')
        // Loop through the results, adding items to the list
        var cmbSearchList = document.getElementById('listPartnerBox');
        for (i = 0; i < count; i++) {
        	var temp = arrMethodList.QueryElementAt(i, Components.interfaces.nsISupportsArray);
            id = temp.QueryElementAt(0, Components.interfaces.nsISupportsPRInt32);
            name = temp.QueryElementAt(1, Components.interfaces.nsISupportsCString);
            var listItem = document.createElement("listitem");
            cmbSearchList.appendItem(name, id)
        }
        
    },
    onFault: function (client, ctxt, fault) {
		log_message(fault)
    },

    onError: function (client, ctxt, status, errorMsg) {
		log_message(errorMsg)
    }
}

//function to get the list of partners
function getPartnerList(){
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    
	var cmdPartnerList = document.getElementById('listPartnerBox');
    
    var name = document.getElementById('txtselectpartner').value;
    var strDbName = get_rpc_string(xmlRpcClient, getPreference("serverdbname"));
    var struid = get_rpc_int(xmlRpcClient, getPreference('userid', 'INT'));    
    var strpass = get_rpc_string(xmlRpcClient, getPreference("password"));
    var strmethod = get_rpc_string(xmlRpcClient, 'list_document_get');
    var strobj = get_rpc_string(xmlRpcClient, 'plugin.handler');
    var strmodel = get_rpc_string(xmlRpcClient, 'res.partner');
    var strname = get_rpc_string(xmlRpcClient, name);
    xmlRpcClient.asyncCall(listPartnerHandler,cmdPartnerList,'execute',[ strDbName,struid,strpass,strobj,strmethod,strmodel, strname ],7);
}



//xmlrpc request handler for creating a new contact
var listCreateContactHandler = {
    onResult: function(client, context, result) {
        res = extract_data(result)
        open_url(res[URL])
        window.close();
    },
    onFault: function (client, ctxt, fault) {
		log_message(fault)
    },

    onError: function (client, ctxt, status, errorMsg) {
		log_message(errorMsg)
    }
}


//function to create a new contact
function createContact(){
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = get_rpc_string(xmlRpcClient, getPreference("serverdbname"));
    var struid = get_rpc_int(xmlRpcClient, getPreference('userid', 'INT'));    
    var strpass = get_rpc_string(xmlRpcClient, getPreference("password"));
    var strmethod = get_rpc_string(xmlRpcClient, 'list_document_get');
    var strobj = get_rpc_string(xmlRpcClient, 'plugin.handler');
    var strmethod = get_rpc_string(xmlRpcClient, 'contact_create');
    var strpartnerid = get_rpc_int(xmlRpcClient, getPartnerId()); 
    var a = ['name','email'];
    var b = [document.getElementById("txtname").value, document.getElementById("txtemail").value];
    var arrofarr = dictcontact(a,b);
    xmlRpcClient.asyncCall(listCreateContactHandler,null,'execute',[strDbName,struid,strpass,strobj,strmethod,arrofarr, strpartnerid], 7);
}
