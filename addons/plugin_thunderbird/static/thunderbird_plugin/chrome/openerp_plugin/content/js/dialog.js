function load_contact_dialog() {
	log_message("load contact dialog")
	if (getPreference('statutdoc')=='open') {
		document.getElementById('open_document').hidden=false;
		document.getElementById('new').hidden=false; 
		document.getElementById('message_label').value="Document found"
    }
    else {           
    	document.getElementById('open_document').hidden=true;
    	document.getElementById('new').hidden=false;
    	document.getElementById('message_label').value="Document not found"
	}
}
