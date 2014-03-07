$(document).ready(function() {
    var search_object = {};
    $.each($("td#seach_enable"), function(key, element){
        var value_td = ($(element).text()).trim();
        if(value_td)search_object[key] = [value_td.toLowerCase(), element, value_td];
    });
    $("#start_search").bind('keyup',function(e){
        var change_text = ($(this).val()).toLowerCase();
            $.each(search_object, function(key, value){
                $(value[1]).text((value[0].indexOf(change_text) < 0)?"":value[2]);
        });
    });
});
