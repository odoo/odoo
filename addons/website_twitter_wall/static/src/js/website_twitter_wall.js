odoo.define('website_twitter_wall.views', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var time = require('web.time');
var Widget = require('web.Widget');
var Model = require('web.Model');
var website = require('website.website');

var Qweb = core.qweb;

website.if_dom_contains('.odoo-tw-walls', function() {

    // Wall List
    //----------------------------------------------

    // Archive Wall
    $("button.odoo-tw-wall-archive").on('click', function() {
        var self = this;
        new Model("twitter.agent").call("write",
            [[$(this).data("wall-id")], {'state': 'archive'}, website.get_context()]
        ).then(function(res) {
            if(res) {
                $(self).hide();
                $(self).siblings("label").show();
            }
        });
    });

    // Storify View
    //----------------------------------------------

    // Display timeago in view
    $("timeago.odoo-tw-timeago").each(function (index, el) {
        var datetime = $(el).attr('datetime'),
            datetime_obj = time.str_to_datetime(datetime),
            // if wall 7 days, 24 hours, 60 min, 60 second, 1000 millis old(one week)
            // then return fix formate string else timeago
            display_str = "";
        if (datetime_obj && new Date().getTime() - datetime_obj.getTime() > 7 * 24 * 60 * 60 * 1000) {
            display_str = datetime_obj.toDateString();
        } else {
            display_str = $.timeago(datetime_obj);
        }
        $(el).text(display_str.charAt(0).toUpperCase() + display_str.slice(1));
    });

    // Delete tweet
    $(".odoo-tw-view-tweet-delete").on('click', function() {
        var tweet = $(this).parent().parent(".odoo-tw-tweet");
        new Model("twitter.tweet").call("unlink", [[tweet.data("tweet-id")]], {
            context: website.get_context()
        }).then(function(res) {
            if(res) tweet.slideUp(500);
        });
    });

    // Do fullscreen or Exit fullscreen on button click
    $(".odoo-tw-screen").on('click', function() {
        if ((document.fullScreenElement && document.fullScreenElement !== null) || (!document.mozFullScreen && !document.webkitIsFullScreen)) {
            if (document.documentElement.requestFullScreen) {
                document.documentElement.requestFullScreen();
            } else if (document.documentElement.mozRequestFullScreen) {
                document.documentElement.mozRequestFullScreen();
            } else if (document.documentElement.webkitRequestFullScreen) {
                document.documentElement.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);
            }
        } else {
            if (document.cancelFullScreen) {
                document.cancelFullScreen();
            } else if (document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
            } else if (document.webkitCancelFullScreen) {
                document.webkitCancelFullScreen();
            }
        }
    });

    // Event fire on window fullscreen and exit fullscreen
    var twitter_wall;
    $(document).on('webkitfullscreenchange mozfullscreenchange fullscreenchange', function() {
        $("#oe_main_menu_navbar, header, .odoo-tw-hide-onlive, footer").slideToggle("normal");
        if (!window.screenTop && !window.screenY) {
            twitter_wall = new TweetWall(parseInt($(".odoo-tw-walls").attr("wall_id")));
            window.scrollTo(0, 0);
            $("body").css({"position": "fixed", "background-color": "#F1F1F1"});
            $("body").addClass("odoo-tw-view-live-remove-border");
            $(".odoo-tw-view-tweet-delete").remove();
        } else {
            setTimeout(function() {window.location.reload();}, 500);
        }
    });

    // Live view with it's options and mode
    //----------------------------------------------

    var colors = {
        '#AC6DAD': '#8E508F',
        '#6C6DEC': '#3839EF',
        '#EB6D6D': '#EB6D6D',
        '#9ACD32': '#779E27',
        '#35D374': '#35D374',
        '#4ED2BE': '#29A390',
        '#FFA500': '#FFA500',
        '#EBBF6D': '#CE901C',
        '#EBEC6D': '#CFD01B',
        '#6C6D6D': '#0084B4',
        '#ACADAD': '#0084B4',
        '#F0F0F0': '#0084B4'
    }, current_class = 'col-sm-12', color = '#F0F0F0';
    Qweb.add_template('/website_twitter_wall/static/src/xml/website_twitter_wall_tweet.xml');
    var TweetWall = Widget.extend({
        template: 'twitter_tweets',
        init: function(wall_id) {
            this.wall_id = wall_id;
            this.pool_cache = {};
            this.repeat = false;
            this.shuffle = false;
            this.theme = "light";
            this.limit = 25;
            this.timeout = 7000;
            this.last_tweet_id = $(".odoo-tw-tweet:first").data("tweet-id") || 0;
            this.tweet_interval;
            this.get_data();
        },
        toggle_repeat: function() {
            if(this.repeat) {
                this.repeat = false;
                this.limit = 25;
                _.each(this.pool_cache, function(t) {
                    t.seen = t.seen ? 1 : 0;
                });
            } else {
                this.repeat = true;
                this.limit = 5;
            }
        },
        toggle_shuffle: function() {
            this.shuffle = (this.shuffle==false) ? true : false;
        },
        get_domain: function() {
            var domain = [['agent_id', '=', this.wall_id], ['id', 'not in', _.keys(this.pool_cache)]];
            if(!this.repeat)
                domain.push(['id', '>', this.last_tweet_id]);
            return domain;
        },
        get_data: function() {
            var self = this;
            return ajax.jsonRpc("/twitter_wall/get_tweet/", 'call', {
                'domain': this.get_domain(),
                'fields': ['tweet_id', 'html_description', 'agent_id'],
                'limit': this.limit
            }).then(function(res) {
                if (res.length || self.repeat) {
                    _.each(res, function(r) {
                        r['seen'] = 0;
                        self.pool_cache[r.id] = r;
                    });
                    self.process_tweet();
                } else {
                    setTimeout(function() {
                        self.get_data();
                    }, 5000);
                }
            });
        },
        get_min_view:function(skip){
            return _.min(this.pool_cache, function(f) {
                if(skip && f.seen < 1) return undefined;
                return f.seen;
            }).seen;
        },
        process_tweet: function() {
            var self = this, min_view = this.get_min_view(0);
            var list = _.filter(this.pool_cache, function(f) {
                if(f.seen == min_view)
                    return f;
            });
            if(this.shuffle)
                list = _.shuffle(list);
            list = _.first(list, this.limit);
            this.tweet_interval = setInterval(function() {
                if(list.length) {
                    var pop_el = list[0];
                    list.shift();
                    if(self.pool_cache[pop_el.id]['seen'] == 0) {
                        self.pool_cache[pop_el.id]['seen'] = self.get_min_view(1) || 1;
                    } else {
                        self.pool_cache[pop_el.id]['seen'] += 1;
                    }
                    var pop_el_desc = $(pop_el.html_description);
                    pop_el_desc.attr("data-link-color", colors[color] || color);
                    if (self.theme == "dark")
                        pop_el_desc.attr({"data-theme": "dark", "data-link-color": color});
                    $(Qweb.render("twitter_tweets", {'res': pop_el_desc.prop('outerHTML'), 'class' : current_class})).prependTo('.odoo-tw-walls');
                } else {
                    clearInterval(self.tweet_interval);
                    self.get_data();
                }
            }, this.timeout);
        },
    });

    // Handle all options
    $(".odoo-tw-view-live-option-btn").on('click', function() {
        $(this).toggleClass("active");
        switch($(this).data('operation')) {
            case 'list':
                $('.odoo-tw-tweet').removeClass().addClass('col-sm-12 odoo-tw-tweet');
                current_class = 'col-sm-12';
                $(this).siblings().removeClass("active");
                twitter_wall.timeout = 7000;
                break;
            case 'grid':
                $('.odoo-tw-tweet').removeClass().addClass('col-sm-4 odoo-tw-tweet odoo-tw-view-live-option-single');
                current_class = 'col-sm-4 odoo-tw-view-live-option-single';
                $(this).siblings().removeClass("active");
                twitter_wall.timeout = 5000;
                break;
            case 'single':
                $('.odoo-tw-tweet').removeClass().addClass('col-sm-12 odoo-tw-tweet odoo-tw-view-live-option-single');
                current_class = 'col-sm-12 odoo-tw-view-live-option-single';
                $(this).siblings().removeClass("active");
                twitter_wall.timeout = 15000;
                break;
            case 'repeat':
                twitter_wall.toggle_repeat();
                break;
            case 'shuffle':
                twitter_wall.toggle_shuffle();
                break;
            case 'theme':
                twitter_wall.theme = twitter_wall.theme == "light" ? "dark" : "light";
                break;
        }
    });

    // Set background color of live view
    var content = "<center><b class='text-muted'>Your Custom Color</b></center>
                    <div class='input-group odoo-tw-view-live-option-colorinput'>
                        <input type='text' class='form-control' />
                        <span class='input-group-addon'><i></i></span>
                    </div>
                    <script>$('.odoo-tw-view-live-option-colorinput').colorpicker({horizontal:true});</script><br/>
                    <center><b class='text-muted'>Standard Colors</b></center>", i = 1;
    _.map(colors, function(primary, secondary) {
        content += "<span class='odoo-tw-view-live-option-color' data-color-code=" + secondary + " style='background-color:" + secondary + "' />";
        if(i%6 == 0) content += "<br/>";
        i++;
    });
    var picker = $('.odoo-tw-view-live-color-picker').popover({
        html: true,
        content: content
    });
    picker.parent().on('click', '.odoo-tw-view-live-option-color', function() {
        color = $(this).data('color-code');
        $('body').css('background-color', color);
    });
    picker.parent().on('changeColor.colorpicker', '.odoo-tw-view-live-option-colorinput', function(e) {
        color = e.color.toHex();
        $('body').css('background-color', color);
    });
});
});