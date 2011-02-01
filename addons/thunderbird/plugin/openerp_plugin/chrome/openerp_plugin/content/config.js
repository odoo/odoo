
function config_close()
{
   window.close("chrome://openerp_plugin/content/config_change.xul", "", "chrome");
    window.open("chrome://openerp_plugin/content/config.xul", "", "chrome");
}

//set the value of the configuration fields
function config_change_load()
{
    var s = getServer();
    var a =s.split(':');
    if (String(a)=="" || String(a)=="undefined"){
        document.getElementById('txtcurl').value = "localhost"
        document.getElementById('txtcport').value = "8069"
    }
    else
    {
        len = a[1];
        var url = "";
        for (i=0;i<len.length;i++)
        {   if (len[i] == "/")
            {
                continue
            }
            url += len[i]
        }
        if (String(url) == "" || String(url) == "undefined"){
            document.getElementById('txtcurl').value = "localhost"
        }
        else
        {
            document.getElementById('txtcurl').value = url
        }

        if (String(a[2]) == "" || String(a[2]) == "undefined"){
            document.getElementById('txtcport').value = "8069"
            setPort("8069");
        }
        else
        {
            document.getElementById('txtcport').value = a[2]
            setPort(a[2]);
        }

    }
}

function config_change_load_web()
{
    //var s = getServer();
    weburl = getWebServerURL();
    webport = getwebPort();
    var urlport = weburl+':'+webport;
    var a =urlport.split(':');
    if (String(a)=="" || String(a)=="undefined"){
        document.getElementById('txtcweburl').value = "localhost"
        document.getElementById('txtcwebport').value = "8069"
    }
    else
    {
        len = a[1];
        var url = "";
        for (i=0;i<len.length;i++)
        {   if (len[i] == "/")
            {
                continue
            }
            url += len[i]
        }
        if (String(url) == "" || String(url) == "undefined"){
            document.getElementById('txtcweburl').value = "localhost"
        }
        else
        {
            document.getElementById('txtcweburl').value = url
        }

        if (String(a[2]) == "" || String(a[2]) == "undefined"){
            document.getElementById('txtcwebport').value = "8069"
            setwebPort("8069");
        }
        else
        {
            document.getElementById('txtcwebport').value = a[2]
            setwebPort(a[2]);
        }

    }
}

function config_ok()
{
    if (document.getElementById('txtcurl').value == '')
    {
        alert("You Must Enter Server Name!")
        return false;
      
    }
    if (document.getElementById('txtcport').value == '')
    {
        alert("You Must Enter Port!")
        return false;
    }
    setServer("http://"+document.getElementById('txtcurl').value +":" + document.getElementById('txtcport').value);
    window.close("chrome://openerp_plugin/content/config_change.xul", "", "chrome");
    window.open("chrome://openerp_plugin/content/config.xul", "", "chrome");
}

function config_ok_web()
{
    if (document.getElementById('txtcweburl').value == '')
    {
        alert("You Must Enter Server Name!")
        return false;
      
    }
    if (document.getElementById('txtcwebport').value == '' && !document.getElementById('lblssl').checked)
    {
        alert("You Must Enter Port!")
        return false;
    }
    var protocol = "http://";
    var port = document.getElementById('txtcwebport').value
    if(document.getElementById('lblssl').checked) {
        protocol = "https://";
        if(port == '') {
            port = 443
        }
    }
    setWebServerURL(protocol + document.getElementById('txtcweburl').value +":" + port);
    window.close("chrome://openerp_plugin/content/config_change_web.xul", "", "chrome");
    window.open("chrome://openerp_plugin/content/config.xul", "", "chrome");
}

function openConfigChange()
{
    window.close("chrome://openerp_plugin/content/config.xul", "", "chrome");
    window.open("chrome://openerp_plugin/content/config_change.xul", "", "chrome");
}

function openConfigChangeweb()
{
    window.close("chrome://openerp_plugin/content/config.xul", "", "chrome");
    window.open("chrome://openerp_plugin/content/config_change_web.xul", "", "chrome");
}

function appendDbList()
{
    setServerService('xmlrpc/db');
    getDbList('DBlist');
}

//set the database list in the listbox in configuration window
function setDb()
{
    var cmbDbList = document.getElementById('listDBListBox');
    document.getElementById('DBlist').value = cmbDbList.getItemAtIndex(cmbDbList.selectedIndex).value;
}

//stores the value of configuration fields in preferences
function okClick()
{
    if (getDBList()=="false")
    {
        if (document.getElementById('DBlist_text').value =='')
        {
            alert("You Must Enter Database Name");
            return false;
        }
        setDbName(document.getElementById('DBlist_text').value);
    }
    else if(document.getElementById('DBlist') != null)
    {
        setDbName(document.getElementById('DBlist').value);
    }
    setServer(document.getElementById('txturl').value);
    var s = document.getElementById('txturl').value;
    var a =s.split(':');
    setPort(a[a.length-1]);
    setUsername(document.getElementById('txtusername').value);
    setPassword(document.getElementById('txtpassword').value);
    window.close();
}

//deletes the value of the selected value in the listbox in configuraton menu
function deleteDocument(){
    if(document.getElementById("listObjectListBox").selectedItem){
        var objectlist = getPref().getCharPref("object").split(',');
        var imagelist = getPref().getCharPref("imagename").split(',');
        var objlist = getPref().getCharPref("listobject").split(',');
        if(objectlist.length>0){
            var objectcharpref = '';
            var imagecharpref = '';
            var objcharpref = '';
            var nodelist = document.getElementById("listObjectListBox").selectedItem.childNodes
            var childnode = document.getElementById("listObjectListBox").childNodes
            for(i=2;i<childnode.length;i++){
                if(childnode[i].hasChildNodes){
                    var secondchild = childnode[i].childNodes;
                    if (secondchild[1].getAttribute("label") != nodelist[1].getAttribute("label")){
                        objcharpref += secondchild[0].getAttribute("label")+',';
                        objectcharpref += secondchild[1].getAttribute("label")+',';
                        imagecharpref += secondchild[2].getAttribute("image")+',';
                    }
                }
            }
            var demo3 = objectcharpref.substring(0,objectcharpref.length-1);
            var demo4 = imagecharpref.substring(0,imagecharpref.length-1);
            var demo5 = objcharpref.substring(0,objcharpref.length-1);

            getPref().setCharPref("listobject",demo5);
            getPref().setCharPref("object",demo3);
            getPref().setCharPref("imagename",demo4);
        }
        document.getElementById("listObjectListBox").removeItemAt(document.getElementById("listObjectListBox").selectedIndex)
    }
    else{
        alert("Please Select Any One Document ");
    }
}

//function to add the image file for the checkbox
function addFile(){
    var nsIFilePicker = Components.interfaces.nsIFilePicker;
    var fp = Components.classes["@mozilla.org/filepicker;1"].createInstance(nsIFilePicker);
    fp.init(this, "Select a File", nsIFilePicker.modeOpen);
    fp.appendFilters(nsIFilePicker.filterImages);
    var res = fp.show();
    if (res == nsIFilePicker.returnOK){
      var thefile = fp.file;
      document.getElementById("txtimagename").value = thefile.path
    }
}

