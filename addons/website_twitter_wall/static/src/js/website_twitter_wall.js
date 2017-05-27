odoo.define('website_twitter_wall.views', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var time = require('web.time');
var Widget = require('web.Widget');
var Model = require('web.Model');
var website = require('website.website');

var _t = core._t;
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
                $(self).siblings("label.odoo-tw-wall-archive").show();
            }
        });
    });

    // Storify View
    //----------------------------------------------

    // Check whether stream is connected or disconnected. if disconnected than display indicator.
    website.if_dom_contains('.odoo-tw-view-cover', function() {
        var $indicator = $('<div class="odoo-indicator"></div>').prependTo("body").hide();
        setInterval(function() {
            ajax.jsonRpc("/twitter_wall/get_stream_state", 'call', {
                'domain': [["id", '=', parseInt($(".odoo-tw-walls").attr("wall_id"))], ["state", '!=', 'archive']],
            }).then(function(res) {
                if(res == 'stop') {
                    $indicator.html(_t('<i class="fa fa-warning" /> <strong>Oops! Something went wrong</strong><br/>You are unable to fetch live tweet. It\'s take few seconds to reconnect automatically. <i class="fa fa-refresh fa-spin" />')).slideDown(400);
                } else {
                    $indicator.html(_t("<strong>Connected!</strong>"));
                    setTimeout(function() {
                        $indicator.slideUp(400);
                    }, 5000);
                }
            });
        }, 15000);
    });

    // Display timeago in view
    $("timeago[data-timeago]").each(function (index, el) {
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
        $(el).text(_t(_.str.capitalize(display_str)));
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
    $("button[data-screen]").on('click', function() {
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
    $(document).on('webkitfullscreenchange mozfullscreenchange fullscreenchange MSFullscreenChange', function() {
        $("#oe_main_menu_navbar, header, .odoo-tw-hide-onlive, footer").slideToggle("normal");
        if (document.fullScreen || document.mozFullScreen || document.webkitIsFullScreen) {
            twitter_wall = new TweetWall(parseInt($(".odoo-tw-walls").attr("wall_id")));
            new Customize(this, $("button[title='Customize']"));
            window.scrollTo(0, 0);
            $("body").css({"position": "fixed", "background-color": "#F1F1F1"});
            $("body").addClass("odoo-tw-view-live");
            $("center.odoo-tw-tweet > span").hide();
            $(".odoo-tw-view-tweet-delete").remove();
            $('.odoo-tw-view-live').on('mouseup', function(e) {
                if(!$(e.target).is('.popover *, .colorpicker *')) {
                    $('.popover').each(function(){
                        $(this.previousSibling).popover('hide');
                    });
                }
            });
        } else {
            setTimeout(function() { window.location.reload(); }, 500);
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
        '#F1F1F1': '#0084B4'
    }, color = '#F1F1F1';
    Qweb.add_template('/website_twitter_wall/static/src/xml/website_twitter_wall_tweet.xml');
    var TweetWall = Widget.extend({
        template: 'twitter_tweets',
        init: function(wall_id) {
            this.wall_id = wall_id;
            this.pool_cache = {};
            this.repeat = false;
            this.shuffle = false;
            this.current_class = 'col-sm-12';
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
                'fields': ['tweet_id', 'tweet', 'agent_id'],
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
            $(document).bind("clear_tweet_queue", function(e) {
                list = [];
            });
            this.tweet_interval = setInterval(function() {
                if(list.length) {
                    var pop_el = list[0];
                    list.shift();
                    if(self.pool_cache[pop_el.id]['seen'] == 0) {
                        self.pool_cache[pop_el.id]['seen'] = self.get_min_view(1) || 1;
                    } else {
                        self.pool_cache[pop_el.id]['seen'] += 1;
                    }
                    var pop_el_desc = $(pop_el.tweet);
                    pop_el_desc.attr("data-link-color", colors[color] || color);
                    if (self.theme == "dark")
                        pop_el_desc.attr({"data-theme": "dark", "data-link-color": color});
                    $(Qweb.render("twitter_tweets", {'res': pop_el_desc.prop('outerHTML'), 'class' : self.current_class})).prependTo('.odoo-tw-walls');
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
                twitter_wall.current_class = 'col-sm-12';
                $(this).siblings().removeClass("active");
                twitter_wall.timeout = 7000;
                break;
            case 'grid':
                $('.odoo-tw-tweet').removeClass().addClass('col-sm-4 odoo-tw-tweet odoo-tw-view-live-option-single');
                twitter_wall.current_class = 'col-sm-4 odoo-tw-view-live-option-single';
                $(this).siblings().removeClass("active");
                twitter_wall.timeout = 5000;
                break;
            case 'single':
                $('.odoo-tw-tweet').removeClass().addClass('col-sm-12 odoo-tw-tweet odoo-tw-view-live-option-single');
                twitter_wall.current_class = 'col-sm-12 odoo-tw-view-live-option-single';
                $(this).siblings().removeClass("active");
                twitter_wall.timeout = 15000;
                break;
            case 'repeat':
                twitter_wall.toggle_repeat();
                break;
            case 'shuffle':
                twitter_wall.toggle_shuffle();
                break;
        }
        $(document).trigger("clear_tweet_queue");
    });

    // Handle customization popover
    Qweb.add_template('/website_twitter_wall/static/src/xml/website_twitter_wall_customize.xml');
    var Customize = Widget.extend({
        template: 'customize',
        init: function(parent, btn) {
            this._super(parent);
            var self= this;
            var picker = btn.popover({
                html: true,
                content: function() {
                    return $(Qweb.render("customize", {"colors": colors}));
                }
            });
            picker.on('shown.bs.popover', function() {
                $(".colorinput > input.form-control").val(color);
                $('.colorinput').colorpicker({horizontal: true});
                $('.theme').removeClass("active");
                $('button[data-operation=' + twitter_wall.theme + ']').addClass("active");
            });
            picker.parent().on('click', '.odoo-tw-view-live-option-color', function() {
                color = $(this).data('color-code');
                $(".colorinput > input.form-control").val(color);
                self.reset_colors(color);
            });
            picker.parent().on('click', '.theme', function(e) {
                var $el = $(e.currentTarget).toggleClass("active");
                twitter_wall.theme = $el.data("operation");
                $el.siblings().removeClass("active");
                $(".odoo-tw-tweet").remove();
            });
            picker.parent().on('changeColor.colorpicker', '.colorinput', function(e) {
                color = e.color.toHex();
                self.reset_colors(color);
            });
        },
        reset_colors:function(color){
            $('<div class="odoo-tw-ripple-wrapper" />').appendTo('body').css("background", color).animate({height: 3000, width: 3000}, 1200, function() {
                $('body').css('background-color', color);
                $('.odoo-tw-ripple-wrapper').remove();
                $(".odoo-tw-tweet").remove();
            });
        }
    });
    $("body").on('mouseover', '.colorpicker', function() {
        $(".odoo-tw-view-live-options").css("opacity", "1");
    });
    $("body").on('mouseout', '.colorpicker', function() {
        $(".odoo-tw-view-live-options").css("opacity", "0");
    });
});
});