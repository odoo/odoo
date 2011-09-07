(function($) {
    var menu,shadow,trigger,content,hash,currentTarget;
    var defaults= {
        menuStyle: {
            listStyle:'none',
            padding:'1px',
            margin:'0px',
            backgroundColor:'#fff',
            border:'1px solid #999',
            width:'100px'
        },
        itemStyle: {
            margin:'0px',
            color:'#000',
            display:'block',
            cursor:'default',
            padding:'3px',
            border:'1px solid #fff',
            backgroundColor:'transparent'
        },
        itemHoverStyle: {
            border:'1px solid #0a246a',
            backgroundColor:'#b6bdd2'
        },
        eventPosX:'pageX',
        eventPosY:'pageY',
        shadow:true,
        onContextMenu:null,
        onShowMenu:null
    };
    $.fn.contextMenu= function(id,options) {
        if(!menu) {
            menu=$('<div id="jqContextMenu"></div>').hide().css({
                position:'absolute',
                zIndex:'2000'
            }).appendTo('body').bind('click', function(e) {
                e.stopPropagation()
            })
        }
        if(!shadow) {
            shadow=$('<div></div>').css({
                backgroundColor:'#000',
                position:'absolute',
                opacity:0.2,
                zIndex:499
            }).appendTo('body').hide()
        }
        hash=hash||[];
        hash.push({
            id:id,
            menuStyle:$.extend({},defaults.menuStyle,options.menuStyle|| {}),
            itemStyle:$.extend({},defaults.itemStyle,options.itemStyle|| {}),
            itemHoverStyle:$.extend({},defaults.itemHoverStyle,options.itemHoverStyle|| {}),
            bindings:options.bindings|| {},
            shadow:options.shadow||options.shadow===false?options.shadow:defaults.shadow,
            onContextMenu:options.onContextMenu||defaults.onContextMenu,
            onShowMenu:options.onShowMenu||defaults.onShowMenu,
            eventPosX:options.eventPosX||defaults.eventPosX,
            eventPosY:options.eventPosY||defaults.eventPosY
        });
        var index=hash.length-1;
        var callback = function(e) {
            var bShowContext=(!!hash[index].onContextMenu)?hash[index].onContextMenu(e):true;
            if(bShowContext)
                display(index,this,e,options);
            return false;
        };
        $(this).bind('contextmenu', callback);
        if(options.leftClickToo) {
            $(this).click(callback);
        }
        return this
    };
    function display(index,trigger,e,options) {
        var cur=hash[index];
        content=$('#'+cur.id).find('ul:first').clone(true);
        content.css(cur.menuStyle).find('li').css(cur.itemStyle).hover( function() {
            $(this).css(cur.itemHoverStyle)
        }, function() {
            $(this).css(cur.itemStyle)
        }).find('img').css({
            verticalAlign:'middle',
            paddingRight:'2px'
        });
        menu.html(content);
        if(!!cur.onShowMenu)
            menu=cur.onShowMenu(e,menu);
        $.each(cur.bindings, function(id,func) {
            $('#'+id,menu).bind('click', function(e) {
                hide();
                func(trigger,currentTarget)
            })
        });
        menu.css({
            'left':e[cur.eventPosX],
            'top':e[cur.eventPosY]
        }).show();
        if(cur.shadow)
            shadow.css({
                width:menu.width(),
                height:menu.height(),
                left:e.pageX+2,
                top:e.pageY+2
            }).show();
        $(document).one('click',hide)
    }

    function hide() {
        menu.hide();
        shadow.hide()
    }

    $.contextMenu= {
        defaults: function(userDefaults) {
            $.each(userDefaults, function(i,val) {
                if(typeof val=='object'&&defaults[i]) {
                    $.extend(defaults[i],val)
                } else
                    defaults[i]=val
            })
        }
    }
})(jQuery);
$( function() {
    $('div.contextMenu').hide()
});