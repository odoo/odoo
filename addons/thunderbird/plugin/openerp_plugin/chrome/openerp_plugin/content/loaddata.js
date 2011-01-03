//gives the preference branch instance
var preferenceBranch = getPref();

//returns the selected checkbox for searching
function getnamesearch()
{
	var checkboxlist = [];
	var j=0;
	var objectlist = preferenceBranch.getCharPref("object").split(',');
	if (objectlist[0]!=''){
		for (var i=1;i<=objectlist.length;i++)
		{
			if(document.getElementById('cbx'+i) && document.getElementById('cbx'+i).checked == true)
			{
				checkboxlist[j] = objectlist[i-1] //document.getElementById('cbx'+i).label;
				j++;
			}
		}
	}
	return checkboxlist;
}
//function to set the text value for the selected partner for contact creation
function selectPartner(){
	if(document.getElementById('listPartnerBox').selectedItem){
		var listselectedItem = document.getElementById('listPartnerBox').selectedItem;
		var value = listselectedItem.firstChild.getAttribute('label');
		setPartnerId(listselectedItem.value);
		document.getElementById('txtselectpartner').setAttribute('value',value);
		window.opener.document.getElementById('txtselectpartner').setAttribute('value',value);
		}
	else{
		window.opener.document.getElementById('txtselectpartner').setAttribute('value','');
	}
}


//function for the intialization procedure //used while loading and unloading of the window
var myPrefObserver =
{
	//set the intial value of the email for the text field in plugin window and also loads the listbox of objects with image
	loaddata: function()
	{	
		setTimeout("listSearchDocumentAttachment()", 0)
	},

	//set the initial value of name and email field of create contact window
	createContact: function()
	{
        document.getElementById("txtname").value = getSenderName();
        document.getElementById("txtemail").value = getSenderEmail();
        document.getElementById("country").value = getAllCountry();
        setPartnerId(0);
	},
    

	//sets the value of email information in preferences and adds observer for the window
	register: function()
  	{
	    appendDbList()
    	preferenceBranch.addObserver("", myPrefObserver, false);
	    document.getElementById("txturl").value = getServer();
    	    var s = document.getElementById('txturl').value;
	    var a =s.split(':');
	    setPort(a[a.length-1]);
	    document.getElementById("txtusername").value = getUsername();
	    document.getElementById("txtpassword").value = getPassword();
	    document.getElementById("DBlist_text").value = getDbName();
		if(getPref().getCharPref("object") != ''){
	    	var objectlist = getPref().getCharPref("object").split(',');
	    	var imagelist = getPref().getCharPref("imagename").split(',');
	    	var obj = getPref().getCharPref("listobject").split(',');
			if(objectlist.length>0){
				for(i=0;i<objectlist.length;i++){
					var	listItem = document.createElement("listitem");
					var listcell1 = document.createElement("listcell");
					var listcell2 = document.createElement("listcell");
					var listcell3 = document.createElement("listcell");
					listcell1.setAttribute("label",obj[i]);
					listcell2.setAttribute("label",objectlist[i]);
					listcell3.setAttribute("image",imagelist[i]);
					listcell3.setAttribute("class","listcell-iconic")
					listcell3.setAttribute("width",16)
					listcell3.setAttribute("height",16)
					listItem.appendChild(listcell1);
				  	listItem.appendChild(listcell2);
				  	listItem.appendChild(listcell3);
					document.getElementById("listObjectListBox").appendChild(listItem);
                   
				}
			}
		}
    },

    webregister: function()
  	{
    	preferenceBranch.addObserver("", myPrefObserver, false);
        weburl = getWebServerURL();
	    document.getElementById("txtweburl").value = weburl;
    	var s = document.getElementById('txtweburl').value;
	   
    },

    createContactAddress: function()
	{
	  	document.getElementById("txtselectpartner").value = getPartnerName();
        document.getElementById("txtcontactname").value = getSenderName();
        document.getElementById("txtstreet").value = getStreet();
        document.getElementById("txtstreet2").value = getStreet2();
        document.getElementById("txtzip").value = getZipCode();
        document.getElementById("txtcity").value = getCity();
        document.getElementById("txtoffice").value = getOfficenumber();
        document.getElementById("txtfax").value = getFax();
        document.getElementById("txtmobile").value = getMobilenumber();
	    document.getElementById("txtemail").value = getSenderEmail();
        document.getElementById("country").value =getAllCountry();
        document.getElementById("state").value = getAllState();
	},

	//unregistering the window observer
	unregister: function()
	{
		if(!preferenceBranch) return;
	    preferenceBranch.removeObserver("", myPrefObserver);
	},

  	observe: function(aSubject, aTopic, aData)
  	{
    	if(aTopic != "nsPref:changed") return;
    	// aSubject is the nsIPrefBranch we're observing (after appropriate QI)
    	// aData is the name of the pref that's been changed (relative to aSubject)
    	switch (aData) {
      		case "serverport":
        	break;
      	case "serverurl":
        	break;
      	case "serverdbname":
        	break;
    	}
  	},
}

function runMoreCode() 
{
} 
