function load_config_data() {
	    getDbList('DBlist');
	    document.getElementById("txturl").value = getServer();
	    document.getElementById("txtusername").value = getUsername();
	    document.getElementById("txtpassword").value = getPassword();
	    document.getElementById("DBlist_text").value = getDbName();
}

function config_close() {
   window.close("chrome://openerp_plugin/content/config_change.xul", "", "chrome");
   open_window('chrome://openerp_plugin/content/config.xul', 580,500);
}

//set the value of the configuration fields
function config_change_load() {
    document.getElementById('txtcurl').value = getPreferenceDefault('server_name', 'localhost')
    document.getElementById('txtcport').value = getPreferenceDefault('serverport', '8069')
}


function config_ok()
{
    var protocol = document.getElementById("dbprotocol_list").value
    if (document.getElementById('txtcurl').value == '' || document.getElementById('txtcport').value == '') {
        alert("You Must Enter Server Name and a Port!")
        return false;
    }
    setPreference('serverport', document.getElementById('txtcport').value)
    setPreference('server_name', document.getElementById('txtcurl').value)
    setServer(document.getElementById("dbprotocol_list").value+document.getElementById('txtcurl').value +":" + document.getElementById('txtcport').value);
    config_close()
}

function openConfigChange() {
    window.close("chrome://openerp_plugin/content/config.xul", "", "chrome");
    open_window("chrome://openerp_plugin/content/config_change.xul", 350,200);
}

//xmlrpc request handler for getting the list of database
var listDbHandler = {
    onResult: function(client, context, result) {
        netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
        var arrMethodList = result.QueryInterface(Components.interfaces.nsISupportsArray);
        var count = arrMethodList.Count();
        if (count < 1) {
        	setDBList("false");
        	return
        }

        setDBList("true");
        dbname_saved = getPreference("serverdbname")
        
        var menu1 = document.createElement("menulist");
        menu1.setAttribute("id","DBlist");
        menu1.setAttribute("width","300");
        var menupopup1 = document.createElement("menupopup");
        menu1.appendChild(menupopup1)
        
        // Loop through the results, adding items to the list
        for (i = 0; i < count; i++) {
            var dbname  = arrMethodList.QueryElementAt(i, Components.interfaces.nsISupportsCString).data;
	        menupopup1.appendChild(createMenuItem(dbname, dbname));
	        if (dbname == dbname_saved) {
	        	index = i
	        }
        }
        
        var db_text_field = document.getElementById("DBlist_text");
        db_text_field.parentNode.replaceChild(menu1, db_text_field);

        menu1.selectedIndex = index
    },


    onFault: function (client, ctxt, fault) {
        setDBList("false");
    },

    onError: function (client, ctxt, status, errorMsg) {
        setDBList("false");       
    }
};
//function to get the database list
function getDbList(argControl) {
    setDBList("false");
    setServerService('xmlrpc/db');
    netscape.security.PrivilegeManager.enablePrivilege('UniversalXPConnect UniversalBrowserAccess');
    var xmlRpcClient = getXmlRpc();
    var cmbDbList = document.getElementById(argControl);

    xmlRpcClient.asyncCall(listDbHandler,cmbDbList,'list',[],0);
    return [];
}


function check_database() {
	if (getDBList()=="false") {
        if (document.getElementById('DBlist_text').value =='') {
            alert("You Must Enter Database Name.");
            return false;
        }
        return document.getElementById('DBlist_text').value;
    }
    else {
        return document.getElementById('DBlist').value;
    }
	
}

function connection() {
	callback = check_connection(login_success)
    setPreference('serverdbname', check_database())
    setServer(document.getElementById('txturl').value);
    setUsername(document.getElementById('txtusername').value);
    setPassword(document.getElementById('txtpassword').value);
	login()	
}
//function to check the login information
function login_success() {
	alert("login successfull");
	window.close("chrome://openerp_plugin/content/config.xul", "", "chrome");
}
