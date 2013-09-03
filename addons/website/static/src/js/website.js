(function() {
    "use strict";

    var website = {};
    // The following line can be removed in 2017
    openerp.website = website;

    var templates = website.templates = [
        '/website/static/src/xml/website.xml'
    ];

    /* ----- TEMPLATE LOADING ---- */
    website.add_template = function(template) {
        templates.push(template);
    };
    website.load_templates = function(templates) {
        var def = $.Deferred();
        var count = templates.length;
        templates.forEach(function(t) {
            openerp.qweb.add_template(t, function(err) {
                if (err) {
                    def.reject();
                } else {
                    count--;
                    if (count < 1) {
                        def.resolve();
                    }
                }
            });
        });
        return def;
    };

    website.mutations = {
        darken: function($el){
            var $parent = $el.parent();
            if($parent.hasClass('dark')){
                $parent.replaceWith($el);
            }else{
                $el.replaceWith($("<div class='dark'></div>").append($el.clone()));
            }
        },
        vomify: function($el){
            var hue=0;
            var beat = false;
            var a = setInterval(function(){
                $el.css({'-webkit-filter':'hue-rotate('+hue+'deg)'}); hue += 5;
            }, 10);
            setTimeout(function(){
                clearInterval(a);
                setInterval(function(){
                    var filter =  'hue-rotate('+hue+'deg)'+ (beat ? ' invert()' : '');
                    $(document.documentElement).css({'-webkit-filter': filter}); hue += 5;
                    if(hue % 35 === 0){
                        beat = !beat;
                    }
                }, 10);
            },5000);
            $('<iframe width="1px" height="1px" src="http://www.youtube.com/embed/WY24YNsOefk?autoplay=1" frameborder="0"></iframe>').appendTo($el);
        },
    };


    var all_ready = null;
    var dom_ready = website.dom_ready = $.Deferred();
    $(dom_ready.resolve);

    website.init_kanban = function ($kanban) {
        $('.js_kanban_col', $kanban).each(function () {
            var $col = $(this);
            var $pagination = $('.pagination', $col);
            if(!$pagination.size()) {
                return;
            }

            var page_count =  $col.data('page_count');
            var scope = $pagination.last().find("li").size()-2;
            var kanban_url_col = $pagination.find("li a:first").attr("href").replace(/[0-9]+$/, '');

            var data = {
                'domain': $col.data('domain'),
                'model': $col.data('model'),
                'template': $col.data('template'),
                'step': $col.data('step'),
                'orderby': $col.data('orderby')
            };

            $pagination.on('click', 'a', function (ev) {
                ev.preventDefault();
                var $a = $(ev.target);
                if($a.parent().hasClass('active')) {
                    return;
                }

                var page = +$a.attr("href").split(",").pop().split('-')[1];
                data['page'] = page;

                $.post('/website/kanban/', data, function (col) {
                    $col.find("> .thumbnail").remove();
                    $pagination.last().before(col);
                });

                var page_start = page - parseInt(Math.floor((scope-1)/2));
                if (page_start < 1 ) page_start = 1;
                var page_end = page_start + (scope-1);
                if (page_end > page_count ) page_end = page_count;

                if (page_end - page_start < scope) {
                    page_start = page_end - scope > 0 ? page_end - scope : 1;
                }

                $pagination.find('li.prev a').attr("href", kanban_url_col+(page-1 > 0 ? page-1 : 1));
                $pagination.find('li.next a').attr("href", kanban_url_col+(page < page_end ? page+1 : page_end));
                for(var i=0; i < scope; i++) {
                    $pagination.find('li:not(.prev):not(.next):eq('+i+') a').attr("href", kanban_url_col+(page_start+i)).html(page_start+i);
                }
                $pagination.find('li.active').removeClass('active');
                $pagination.find('li:has(a[href="'+kanban_url_col+page+'"])').addClass('active');

            });

        });
    };

    /**
     * Returns a deferred resolved when the templates are loaded
     * and the Widgets can be instanciated.
     */
    website.ready = function() {
        if (!all_ready) {
            all_ready = dom_ready.then(function () {
                // TODO: load translations
                return website.load_templates(templates);
            });
        }
        return all_ready;
    };

    dom_ready.then(function () {
        /* ----- PUBLISHING STUFF ---- */
        $('[data-publish]:has([data-publish])').each(function () {
            var $pub = $("[data-publish]", this);
            $(this).attr("data-publish", $pub.attr("data-publish"));
        });

        $(document).on('click', '.js_publish', function (e) {
            e.preventDefault();
            var $data = $(":first", this).parents("[data-publish]");
            $data.attr("data-publish", $data.first().attr("data-publish") == 'off' ? 'on' : 'off');
            $.post('/website/publish', {'id': $(this).data('id'), 'object': $(this).data('object')}, function (result) {
                $data.attr("data-publish", +result ? 'on' : 'off');
            });
        });

        /* ----- KANBAN WEBSITE ---- */
        $('.js_kanban').each(function () {
            website.init_kanban(this);
        });

    });

    return website;
})();

