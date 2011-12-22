function load_contact_dialog() {
	log_message("load contact dialog")
	
}


function load_document(){
    log_message("ceci est un test");
    log_message(getPreference('statutdoc'));
    log_message("fin de test");
        if (getPreference('statutdoc')=='open'){
            document.getElementById('open_document').hidden=false;
            document.getElementById('open').hidden=true; 
            }
        else{           
            document.getElementById('open_document').hidden=true;
            document.getElementById('open').hidden=false;
            }
    
}
