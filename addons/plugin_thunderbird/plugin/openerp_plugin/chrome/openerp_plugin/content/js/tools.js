function log_message(message) {
    window.dump("[OPENERP-PLUGIN LOG]: " + message + "\n")
}

function getMessage(uri) {
    var content;
    var MsgService = messenger.messageServiceFromURI(uri);
    var MsgStream = Components.classes["@mozilla.org/network/sync-stream-listener;1"].createInstance();
    var MsgStrem_Inputstream = MsgStream.QueryInterface(Components.interfaces.nsIInputStream);
    var ScriptInput = Components.classes["@mozilla.org/scriptableinputstream;1"].createInstance();
    var ScriptInputStream = ScriptInput.QueryInterface(Components.interfaces.nsIScriptableInputStream);
    ScriptInputStream.init(MsgStream);
    try {
        MsgService.streamMessage(uri,MsgStream, msgWindow, null, false, null);
    } catch (ex) {
        return;
    }
    ScriptInputStream .available();
    while (ScriptInputStream .available()) {
        content = content + ScriptInputStream.read(512);
    }
    return content
    
}

function createMenuItem(aLabel, aValue) {
    const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
    var item = document.createElementNS(XUL_NS, "menuitem"); // create a new XUL menuitem
    item.setAttribute("label", aLabel);
    item.setAttribute("value", aValue);
    return item;
}

    
function clear_search_box(element) {
	var cmbSearchList = document.getElementById(element);
	count = cmbSearchList.itemCount
	for(i = 1; i <= count; i++) {
		cmbSearchList.removeItemAt(count - i)	
	}
}

function open_url(url) {
	netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
	var messenger = Components.classes['@mozilla.org/messenger;1'].createInstance(Components.interfaces.nsIMessenger);
    messenger.launchExternalURL(url);
}

function extract_data(result) {
	var returnArray = new Array();
	
	netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var res = result.QueryInterface(Components.interfaces.nsISupportsArray);
    returnArray[0] = res.QueryElementAt(0, Components.interfaces.nsISupportsCString); 
    returnArray[1] = res.QueryElementAt(1, Components.interfaces.nsISupportsPRInt32);
    
    for(i = 2; i < res.Count(); i++) {
    	returnArray[i] = res.QueryElementAt(i, Components.interfaces.nsISupportsCString); 
    }
    return returnArray
}


var MODEL = 0;
var RES_ID = 1;
var URL = 2;
var ADDITIONAL_INFORMATION = 3

function check_connection(callback) {
	return function () {
		if(getPreference('userid', 'INT') == 0) {
			alert("Server unreachable or login Failed, please check your connection settings")
			return
		} 
		else if (getmodule_install() == "no") {
			alert("Please install the thunderbird module on your '" + getDbName() +"' database and try again !");
    		return
    	}
    	return callback()
	}
}

function open_window(url,width,height) {
	var win = window.open(url, '', 'chrome,width='+width+',height='+height+',resizable=yes');
	var w = ((window.screen.availWidth/2)-(width/2));
	var h=((window.screen.availHeight/2)-(height/2));
	win.moveTo(w,h);
}



