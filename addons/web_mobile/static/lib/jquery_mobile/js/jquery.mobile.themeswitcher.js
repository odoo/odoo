//quick & dirty theme switcher, written to potentially work as a bookmarklet
(function($){
    $.themeswitcher = function(){
        if( $('[data-'+ $.mobile.ns +'-url=themeswitcher]').length ){ return; }
        var themesDir = 'http://jquerymobile.com/test/themes/',
            themes = ['default','valencia'],
            currentPage = $.mobile.activePage,
            menuPage = $( '<div data-'+ $.mobile.ns +'url="themeswitcher" data-'+ $.mobile.ns +'role=\'dialog\' data-'+ $.mobile.ns +'theme=\'a\'>' +
                        '<div data-'+ $.mobile.ns +'role=\'header\' data-'+ $.mobile.ns +'theme=\'b\'>' +
                            '<div class=\'ui-title\'>Switch Theme:</div>'+
                        '</div>'+
                        '<div data-'+ $.mobile.ns +'role=\'content\' data-'+ $.mobile.ns +'theme=\'c\'><ul data-'+ $.mobile.ns +'role=\'listview\' data-'+ $.mobile.ns +'inset=\'true\'></ul></div>'+
                    '</div>' )
                    .appendTo( $.mobile.pageContainer ),
            menu = menuPage.find('ul');

        //menu items
        $.each(themes, function( i ){
            $('<li><a href="#" data-'+ $.mobile.ns +'rel="back">' + themes[ i ].charAt(0).toUpperCase() + themes[ i ].substr(1) + '</a></li>')
                .bind("vclick", function(){
                    addTheme( themes[i] );
                    menuPage.dialog( "close" );
                    return false;
                })
                .appendTo(menu);
        });

        //remover, adder
        function addTheme(theme){
            $('head').append( '<link rel=\'stylesheet\' href=\''+ themesDir + theme +'/\' />' );
        }

        //create page, listview
        menuPage.page();

    };
})(jQuery);