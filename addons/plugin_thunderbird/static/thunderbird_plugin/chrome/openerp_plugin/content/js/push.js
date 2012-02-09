//xmlrpc request handler for list of search object exist in database or not.
var DocumentTypeHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var modelListRPC = result.QueryInterface(Components.interfaces.nsISupportsArray);
        
        var menu_popup = document.getElementById("model_list");
        for(i = 0; i < modelListRPC.Count(); i++) {
        	var temp_array = modelListRPC.QueryElementAt(i, Components.interfaces.nsISupportsArray);
            var model_value = temp_array.QueryElementAt(0, Components.interfaces.nsISupportsCString);
            var model_name = temp_array.QueryElementAt(1, Components.interfaces.nsISupportsCString);
            if(i == 0) {
            	var menuitem = document.getElementById("first_model_list");
            	menuitem.setAttribute("label", model_name);
            	menuitem.setAttribute("value", model_value);
            }
            else {
            	menu_popup.appendChild(createMenuItem(model_name, model_value));
            }
            
        }
    },

    onFault: function (client, ctxt, fault) {
		log_message("Fault getDocument : " + fault)
    },

    onError: function (client, ctxt, status, errorMsg) {
		log_message("Error getDocument : " + errorMsg)
    }
}

//function to create a new attachment record
function getDocumentType(){
    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var strDbName = get_rpc_string(xmlRpcClient, getPreference("serverdbname"));
    var struid = get_rpc_int(xmlRpcClient, getPreference('userid', 'INT'));
    var strpass = get_rpc_string(xmlRpcClient, getPreference("password"));
    var strobj = get_rpc_string(xmlRpcClient, 'plugin.handler');
    var strmethod = get_rpc_string(xmlRpcClient, 'document_type');
    xmlRpcClient.asyncCall(DocumentTypeHandler,null,'execute',[strDbName,struid,strpass,strobj,strmethod], 5);
}

/**
 * Search Handler : Fill the result of list_document_get in the listbox
 */
//xmlrpc request handler for getting the search results for the particular selected check box object
var listSearchCheckboxHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var arrMethodList = result.QueryInterface(Components.interfaces.nsISupportsArray);
                // Set the number of results
        var count = arrMethodList.Count();
        var close=0;
        clear_search_box('listSearchBox')
        if(count == 0){
            alert("No Records Found");
            return false;
        }
       
        // Loop through the results, adding items to the list
        var cmbSearchList = document.getElementById('listSearchBox');

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
};

//function to search the records of selected checkbox object
function searchCheckbox()
{
	model_name = document.getElementById('menu_model_list').selectedItem.value;
	name = document.getElementById('txtvalueobj').value

    setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var cmbSearchList = document.getElementById('listSearchBox');
    var strDbName = get_rpc_string(xmlRpcClient, getPreference("serverdbname"));
    var struid = get_rpc_int(xmlRpcClient, getPreference('userid', 'INT'));    
    var strpass = get_rpc_string(xmlRpcClient, getPreference("password"));
    var strmethod = get_rpc_string(xmlRpcClient, 'list_document_get');
    var strobj = get_rpc_string(xmlRpcClient, 'plugin.handler');
    var strmodel = get_rpc_string(xmlRpcClient, model_name);
    var strname = get_rpc_string(xmlRpcClient, name);
    
    xmlRpcClient.asyncCall(listSearchCheckboxHandler,cmbSearchList,'execute',[ strDbName,struid,strpass,strobj,strmethod, strmodel, strname],7);
}



//xmlrpc request handler for creating the record of mail
var pushHandler = {
    onResult: function(client, context, result) {
        res = extract_data(result)
        alert(res[ADDITIONAL_INFORMATION])
        open_url(res[URL]);
	    window.close();
    },
    
    onFault: function (client, ctxt, fault) {
		log_message(fault)
    },

    onError: function (client, ctxt, status, errorMsg) {
		log_message(errorMsg)
    }
}


function push(op) {
	var model_name = document.getElementById('menu_model_list').selectedItem.value;
	var res_id = 0;
	if(op == "add") {
		var item = document.getElementById('listSearchBox').selectedItem
		if (String(item) == "null") {
			alert("select at least one Document !")
			return
		}
		
		var res_id = item.value;
		
	}	
	setServerService('xmlrpc/object');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    
    var strDbName = get_rpc_string(xmlRpcClient, getPreference("serverdbname"));
    var struid = get_rpc_int(xmlRpcClient, getPreference('userid', 'INT'));    
    var strpass = get_rpc_string(xmlRpcClient, getPreference("password"));
    var strmethod = get_rpc_string(xmlRpcClient, 'push_message');
    var strobj = get_rpc_string(xmlRpcClient, 'plugin.handler');
    var stremail = get_rpc_string(xmlRpcClient, getPreference('email_text'));
	var strmodel = 	get_rpc_string(xmlRpcClient, model_name);
	var strres_id = get_rpc_int(xmlRpcClient, res_id);
    xmlRpcClient.asyncCall(pushHandler,null,'execute',[strDbName,struid,strpass,strobj,strmethod,strmodel, stremail, strres_id],8);
}


