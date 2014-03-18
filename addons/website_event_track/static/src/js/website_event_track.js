$(document).ready(function() {
    function set_value(td_contain){
        var search_object = {};
        $.each(td_contain, function(key, element2){
            var value_td = ($(element2).text()).trim();
            if(value_td)search_object[key] = [value_td.toLowerCase(), element2];
        });
        return search_object;
    };
    $.each($("table#table_search"), function(key, element){
        $.each($(element).find("tr#agenda_tr"),function(key, element1){
            var th_child = $(element1).siblings("#agenda_th").children().length;
            var tr_child = $(element1).children();
            var td_contain = $(tr_child).filter("td#seach_enable");
            if(th_child == tr_child.length && td_contain.length == 0){
                $(element1).remove();
            }
        });
        var search_object = set_value($(element).find("td#seach_enable"));
        var element_search = $(element).prev().find("#start_search");
        $(element_search).bind('keyup',function(e){
            var change_text = ($(this).val()).toLowerCase();
            $.each(search_object, function(key, value){
                $(value[1]).css("visibility", (value[0].indexOf(change_text) < 0)?'hidden':'visible');
            });
        });
    });
});
