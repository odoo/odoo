
//function to check all the checkbox
function selectAllCheckbox()
{
	var objectlist = preferenceBranch.getCharPref("object").split(',');
	if(objectlist.length == 1 && objectlist[0]==''){
		return false;
	}
	for (var i=1;i<=objectlist.length;i++)
	{
	 	var checkboxobj = document.getElementById('cbx'+i);
		if (!checkboxobj)
			continue
		if(document.getElementById('cbxselectall').checked == true)
			checkboxobj.checked = true;
		else
		  	checkboxobj.checked = false;
	}
}
