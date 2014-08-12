jQuery(document).ready(function() {
	jQuery("timeago.timeago").timeago();

    /*modify embed code based on options*/
    jQuery.modifyembedcode = function(currentVal=0) {
        var slide_embed_code = jQuery('#slide_embed_code').val();
        var new_slide_embed_code = slide_embed_code.replace(/(page=)[^\&].*?()/,'$1' + currentVal + '$2');
        jQuery('#slide_embed_code').val(new_slide_embed_code);
    };
	// This button will increment the value
    jQuery('#btnplus').click(function(e){        
        e.preventDefault();        
        fieldName = jQuery(this).attr('field');        
        var currentVal = parseInt(jQuery('input[name='+fieldName+']').val());        
        if (!isNaN(currentVal)) {            
            jQuery('input[name='+fieldName+']').val(currentVal + 1);
            jQuery.modifyembedcode(currentVal + 1)
        } else {            
            jQuery('input[name='+fieldName+']').val(0);
            jQuery.modifyembedcode(0)
        }
    });
    // This button will decrement the value till 0
    jQuery("#btnminus").click(function(e) {        
        e.preventDefault();        
        fieldName = jQuery(this).attr('field');        
        var currentVal = parseInt(jQuery('input[name='+fieldName+']').val());        
        if (!isNaN(currentVal) && currentVal > 0) {            
            jQuery('input[name='+fieldName+']').val(currentVal - 1);
            jQuery.modifyembedcode(currentVal - 1)
        } else {            
            jQuery('input[name='+fieldName+']').val(0);
            jQuery.modifyembedcode(0)
        }
    });

});