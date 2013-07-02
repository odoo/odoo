$(function(){

    var selected_snippet = null;
    function snippet_click(event){
        if(selected_snippet){
            selected_snippet.removeClass('oe_selected');
            if(selected_snippet[0] === $(this)[0]){
                selected_snippet = null;
                event.preventDefault();
                make_static();
                return;
            }
        }
        $(this).addClass('oe_selected');
        selected_snippet = $(this);
        make_editable();
        event.preventDefault();
    }
    $('.oe_snippet').click(snippet_click);

    var hover_element = null;

    function make_editable( constraint_after, constraint_inside ){
        if(selected_snippet && selected_snippet.hasClass('oe_new')){
            $('.oe_snippet_demo').addClass('oe_new');
        }else{
            $('.oe_snippet_demo').removeClass('oe_new');
        }
    
        $('.oe_page *').off('mouseover');
        $('.oe_page *').off('mouseleave');
        $('.oe_page *').mouseover(function(event){
            console.log('hover:',this);
            if(hover_element){
                hover_element.removeClass('oe_selected');
                hover_element.off('click');
            }
            $(this).addClass('oe_selected');
            $(this).click(append_snippet);
            hover_element = $(this);
            event.stopPropagation();
        });
        $('.oe_page *').mouseleave(function(){
            if(hover_element && $(this) === hover_element){
                hover_element = null;
                $(this).removeClass('oe_selected');
            }
        });
    }

    function make_static(){
        $('.oe_snippet_demo').removeClass('oe_new');
        $('.oe_page *').off('mouseover');
        $('.oe_page *').off('mouseleave');
        $('.oe_page .oe_selected').removeClass('oe_selected');
    }
        

    function append_snippet(event){
        console.log('click',this,event.button);
        if(event.button === 0){
            if(selected_snippet){
                if(selected_snippet.hasClass('oe_new')){
                    var new_snippet = $("<div class='oe_snippet'></div>");
                    new_snippet.append($(this).clone());
                    new_snippet.click(snippet_click);
                    $('.oe_snippet.oe_selected').before(new_snippet);
                }else{
                    $(this).after($('.oe_snippet.oe_selected').contents().clone());
                }
                selected_snippet.removeClass('oe_selected');
                selected_snippet = null;
                make_static();
            }
        }else if(event.button === 1){
            $(this).remove();
        }
        event.preventDefault();
    }

});
