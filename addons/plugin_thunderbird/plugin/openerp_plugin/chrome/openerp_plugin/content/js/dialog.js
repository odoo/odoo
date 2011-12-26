function load_contact_dialog() {
	log_message("load contact dialog")
	
}
function load_document(){
        if (getPreference('statutdoc')=='open'){
            document.getElementById('open_document').hidden=false;
            document.getElementById('open').hidden=true; 
            }
        else{           
            document.getElementById('open_document').hidden=true;
            document.getElementById('open').hidden=false;
            }
    
}

function message_setlabel(){
    log_message(getPreference('subject'));
    document.getElementById('message_label').value=getPreference('subject');    
    }
