/*::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
 jquery.mb.components
 
 file: jquery.mb.YTPlayer.src.js
 last modified: 11/2/18 7:23 PM
 Version:  3.2.9
 Build:  7421
 
 Open Lab s.r.l., Florence - Italy
 email:  matteo@open-lab.com
 blog: 	http://pupunzi.open-lab.com
 site: 	http://pupunzi.com
 	http://open-lab.com
 
 Licences: MIT, GPL
 https://www.opensource.org/licenses/mit-license.php
 https://www.gnu.org/licenses/gpl.html
 
 Copyright (c) 2001-2018. Matteo Bicocchi (Pupunzi)
 :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::*/



var ytp = ytp || {};

function onYouTubeIframeAPIReady() {
  if (ytp.YTAPIReady) return;
  ytp.YTAPIReady = true;
  jQuery(document).trigger("YTAPIReady");
}

var getYTPVideoID = function (url) {
  var videoID, playlistID;
  if (url.indexOf("youtu.be") > 0 || url.indexOf("youtube.com/embed") > 0) {
    videoID = url.substr(url.lastIndexOf("/") + 1, url.length);
    playlistID = videoID.indexOf("?list=") > 0 ? videoID.substr(videoID.lastIndexOf("="), videoID.length) : null;
    videoID = playlistID ? videoID.substr(0, videoID.lastIndexOf("?")) : videoID;
  } else if (url.indexOf("http") > -1) {
    //videoID = url.match( /([\/&]v\/([^&#]*))|([\\?&]v=([^&#]*))/ )[ 1 ];
    videoID = url.match(/[\\?&]v=([^&#]*)/)[1];
    playlistID = url.indexOf("list=") > 0 ? url.match(/[\\?&]list=([^&#]*)/)[1] : null;
  } else {
    videoID = url.length > 15 ? null : url;
    playlistID = videoID ? null : url;
  }
  return {
    videoID   : videoID,
    playlistID: playlistID
  };
};

function iOSversion() {
  if (/iP(hone|od|ad)/.test(navigator.platform)) {
    var v = (navigator.appVersion).match(/OS (\d+)_(\d+)_?(\d+)?/);
    return [parseInt(v[1], 10), parseInt(v[2], 10), parseInt(v[3] || 0, 10)];
  }
}

(function (jQuery, ytp) {
  
  jQuery.mbYTPlayer = {
    name   : "jquery.mb.YTPlayer",
    version: "3.2.9",
    build  : "7421",
    author : "Matteo Bicocchi (pupunzi)",
    apiKey : "",
    
    /*
     * Default options for the player
     */
    defaults        : {
      /**
       videoURL (string)
       the complete Youtube video URL or the short url or the videoID
       */
      videoURL: null,
      
      /**
       containment (string)
       default containment for the player
       */
      containment: "body",
      
      /**
       ratio (string or number)
       "auto", "16/9", "4/3" or number: 4/3, 16/9
       */
      ratio: "auto",
      
      /**
       fadeOnStartTime (int)
       fade in timing at video start
       */
      fadeOnStartTime: 1000,
      
      /**
       startAt (int)
       start second
       */
      startAt: 0,
      
      /**
       stopAt (int)
       stop second
       */
      stopAt: 0,
      
      /**
       autoPlay (bool)
       on page load video should start or pause
       */
      autoPlay: true,
      
      /**
       coverImage (string)
       The path to the image to be used as cover if the autoPlay option is set to false
       */
      coverImage: false,
      
      /**
       loop (bool or int)
       video should loop or not; if number it will loop for the specified times
       */
      loop: true,
      
      /**
       addRaster (bool)
       shows a raster image over the video (added via CSS)
       You can change the raster image via CSS:
       .YTPOverlay.raster { background: url(images/raster.png)}
       */
      addRaster: false,
      
      /**
       mask (bool or object) the key is the second and the value is the path to the image
       Ex: mask:{ 0:'assets/mask-1.png', 5:'assets/mask-2.png', 30: false, 50:'assets/mask-3.png'}
       */
      mask: false,
      
      /**
       opacity (int)
       0 to 1
       */
      opacity: 1,
      
      /**
       quality (string)
       “small”, “medium”, “large”, “hd720”, “hd1080”, “highres”, "default"
       */
      quality: "default",
      
      /**
       vol (int)
       0 to 100
       */
      vol: 50,
      
      /**
       mute (bool)
       mute the video at start
       */
      mute: false,
      
      /**
       showControls (bool)
       shows the control bar at the bottom of the containment
       */
      showControls: true,
      
      /**
       anchor (string)
       center,top,bottom,left,right combined in pair
       */
      anchor: "center,center",
      
      /**
       showAnnotations (bool)
       display the annotations on video
       */
      showAnnotations: false,
      
      /**
       cc_load_policy (bool)
       display the subtitles
       */
      cc_load_policy: false,
      
      /**
       showYTLogo (bool)
       display the Youtube logotype inside the button bar
       */
      showYTLogo: true,
      
      /**
       useOnMobile (bool)
       activate the player also on mobile
       */
      useOnMobile: true,
      
      /**
       mobileFallbackImage (bool)
       mobile fallback image if useOnMobile is set to false
       */
      mobileFallbackImage: null,
      
      /**
       playOnlyIfVisible (bool)
       play the video only if the containment is on screen
       */
      playOnlyIfVisible: false,
      
      /**
       onScreenPercentage (bool)
       percentage of the player height the video should stop or start when visible
       */
      onScreenPercentage: 30,
      
      /**
       stopMovieOnBlur (bool)
       stop the video if the window loose the focus
       */
      stopMovieOnBlur: true,
      
      /**
       realfullscreen (bool)
       the video when in full screen covers all the display
       */
      realFullscreen: true,
      
      /**
       optimizeDisplay (bool)
       The video always fit the containment without displaying the black strips
       */
      optimizeDisplay: true,
      
      /**
       abundance (bool)
       the abudance of the video size
       */
      abundance: 0.3,
      
      /**
       gaTrack (bool)
       track the video plays on GA
       */
      gaTrack: true,
      
      /**
       remember_last_time (bool)
       when the page is reloaded the video will start from the last position
       */
      remember_last_time: false,
      
      /**
       addFilters (bool or string)
       add one or more CSS filters as object to the video
       Ex: {sepia: 50, hue_rotate : 220}
       */
      addFilters: false,
      
      /**
       onReady (function)
       a callback function fired once the player is ready
       */
      onReady: function (player) {},
      
      /**
       onReady (function)
       a callback function fired if there's an error
       */
      onError: function (player, err) {}
    },
    /**
     *  @fontface icons
     *  */
    controls        : {
      play    : "P",
      pause   : "p",
      mute    : "M",
      unmute  : "A",
      onlyYT  : "O",
      showSite: "R",
      ytLogo  : "Y"
    },
    controlBar      : null,
    locationProtocol: "https:",
    
    /**
     * Applicable filters
     */
    defaultFilters: {
      grayscale : {value: 0, unit: "%"},
      hue_rotate: {value: 0, unit: "deg"},
      invert    : {value: 0, unit: "%"},
      opacity   : {value: 0, unit: "%"},
      saturate  : {value: 0, unit: "%"},
      sepia     : {value: 0, unit: "%"},
      brightness: {value: 0, unit: "%"},
      contrast  : {value: 0, unit: "%"},
      blur      : {value: 0, unit: "px"}
    },
    
    /**
     * build the player
     * @param options
     * @returns [players]
     */
    buildPlayer: function (options) {
      
      if (!ytp.YTAPIReady && typeof window.YT === 'undefined') {
        jQuery("#YTAPI").remove();
        var tag = jQuery("<script>").attr({
          "src": "https://www.youtube.com/iframe_api?v=" + jQuery.mbYTPlayer.version,
          "id" : "YTAPI"
        });
        jQuery("head").prepend(tag);
      } else {
        setTimeout(function () {
          jQuery(document).trigger("YTAPIReady");
          ytp.YTAPIReady = true;
        }, 100);
      }
      
      function isIframe() {
        var isIfr = false;
        try {
          if (self.location.href != top.location.href) isIfr = true;
        } catch (e) {
          isIfr = true;
        }
        return isIfr;
      };


      
      //console.time( "YTPlayerInit" );
      
      return this.each(function () {
        var YTPlayer = this;
        var $YTPlayer = jQuery(YTPlayer);
        $YTPlayer.hide();
        YTPlayer.loop = 0;
        YTPlayer.state = 0;
        YTPlayer.filters = jQuery.extend(true, {}, jQuery.mbYTPlayer.defaultFilters);
        YTPlayer.filtersEnabled = true;
        YTPlayer.id = YTPlayer.id || "YTP_" + new Date().getTime();
        $YTPlayer.addClass("mb_YTPlayer");
        
        /**
         Set properties
         */
        var property = $YTPlayer.data("property") && typeof $YTPlayer.data("property") == "string" ?
            eval('(' + $YTPlayer.data("property") + ')') :
            $YTPlayer.data("property");
        
        if (typeof property !== "object")
          property = {};
        
        YTPlayer.opt = jQuery.extend(true, {}, jQuery.mbYTPlayer.defaults, YTPlayer.opt, options, property);
        
        YTPlayer.opt.elementId = YTPlayer.id;
        
        if (YTPlayer.opt.vol === 0) {
          YTPlayer.opt.vol = 1;
          YTPlayer.opt.mute = true;
        }
        
        /**
         * If autoPlay is set to true and  mute is set to false
         * Webkit browser will not auto-play
         * Start playing after the first click
         */
        if (YTPlayer.opt.autoPlay && YTPlayer.opt.mute == false && jQuery.mbBrowser.chrome) {
          //YTPlayer.opt.mute = true;
          jQuery(document).one("mousedown.YTPstart", function () {
            $YTPlayer.YTPPlay();
          });
          console.info("YTPlayer info: On Webkit browsers you can not autoplay the video if the audio is on.")
        }
        
        if (YTPlayer.opt.loop && typeof YTPlayer.opt.loop === "boolean") {
          YTPlayer.opt.loop = 9999;
        }
        
        /**
         Disable fullScreen if is in an iframe or full-screen API is not available
         */
        var fullScreenAvailable = document.fullscreenEnabled || document.webkitFullscreenEnabled || document.mozFullScreenEnabled || document.msFullscreenEnabled;
        YTPlayer.opt.realFullscreen = isIframe() || !fullScreenAvailable ? false : YTPlayer.opt.realFullscreen;
        
        /**
         Manage annotations
         */
        YTPlayer.opt.showAnnotations = YTPlayer.opt.showAnnotations ? '1' : '3';
        
        /**
         Manage show subtitle and caption
         */
        YTPlayer.opt.cc_load_policy = YTPlayer.opt.cc_load_policy ? '1' : '0';
        
        /**
         Manage cover image
         */
        YTPlayer.opt.coverImage = YTPlayer.opt.coverImage || YTPlayer.opt.backgroundImage;
        
        /**
         Manage Opacity for IE < 10
         */
        if (jQuery.mbBrowser.msie && jQuery.mbBrowser.version < 9)
          YTPlayer.opt.opacity = 1;
        
        YTPlayer.opt.containment = YTPlayer.opt.containment === "self" ? $YTPlayer : jQuery(YTPlayer.opt.containment);
        YTPlayer.isRetina = (window.retina || window.devicePixelRatio > 1);
        
        YTPlayer.opt.ratio = YTPlayer.opt.ratio === "auto" ? 16 / 9 : YTPlayer.opt.ratio;
        YTPlayer.opt.ratio = eval(YTPlayer.opt.ratio);
        
        YTPlayer.orig_containment_background = YTPlayer.opt.containment.css("background-image");
        
        if (!$YTPlayer.attr("id"))
          $YTPlayer.attr("id", "ytp_" + new Date().getTime());
        
        YTPlayer.playerID = "iframe_" + YTPlayer.id;
        
        YTPlayer.isAlone = false;
        YTPlayer.hasFocus = true;
        YTPlayer.videoID = YTPlayer.opt.videoURL ?
            getYTPVideoID(YTPlayer.opt.videoURL).videoID : $YTPlayer.attr("href") ?
                getYTPVideoID($YTPlayer.attr("href")).videoID :
                false;
        
        /**
         Check if it is a video list
         */
        YTPlayer.playlistID = YTPlayer.opt.videoURL ?
            getYTPVideoID(YTPlayer.opt.videoURL).playlistID : $YTPlayer.attr("href") ?
                getYTPVideoID($YTPlayer.attr("href")).playlistID :
                false;
        
        var start_from_last = 0;
        if (jQuery.mbCookie.get("YTPlayer_start_from" + YTPlayer.videoID))
          start_from_last = parseFloat(jQuery.mbCookie.get("YTPlayer_start_from" + YTPlayer.videoID));
        if (YTPlayer.opt.remember_last_time && start_from_last) {
          YTPlayer.start_from_last = start_from_last;
          jQuery.mbCookie.remove("YTPlayer_start_from" + YTPlayer.videoID);
        }
        
        YTPlayer.isPlayer = $YTPlayer.is(YTPlayer.opt.containment);
        YTPlayer.isBackground = YTPlayer.opt.containment.is("body");
        
        if (YTPlayer.isBackground && ytp.backgroundIsInited)
          return;
        
        /**
         Hide the placeholder if it's not the target of the player
         */
        if (YTPlayer.isPlayer)
          $YTPlayer.show();
        
        /**
         create the overlay
         */
        YTPlayer.overlay = jQuery("<div/>").css({
          position: "absolute",
          top     : 0,
          left    : 0,
          width   : "100%",
          height  : "100%"
        }).addClass("YTPOverlay");
        
        if (YTPlayer.opt.coverImage || YTPlayer.orig_containment_background != "none") {
          // if (YTPlayer.isPlayer && !YTPlayer.opt.autoPlay) {
          var bgndURL = YTPlayer.opt.coverImage ? "url(" + YTPlayer.opt.coverImage + ") center center" : YTPlayer.orig_containment_background;
          
          YTPlayer.opt.containment.css({
            background      : bgndURL,
            backgroundColor : "#000",
            backgroundSize  : "cover",
            backgroundRepeat: "no-repeat"
          });
          
        }
        
        /**
         create the wrapper
         */
        YTPlayer.wrapper = jQuery("<div/>").attr("id", "wrapper_" + YTPlayer.id).css({
          position : "absolute",
          zIndex   : 0,
          minWidth : "100%",
          minHeight: "100%",
          left     : 0,
          top      : 0,
          overflow : "hidden",
          opacity  : 0
        }).addClass("mbYTP_wrapper");
        
        /**
         If is an inline player toggle play if the overlay is clicked
         */
        if (YTPlayer.isPlayer) {
          YTPlayer.inlinePlayButton = jQuery("<div/>").addClass("inlinePlayButton").html(jQuery.mbYTPlayer.controls.play);
          $YTPlayer.append(YTPlayer.inlinePlayButton);
          YTPlayer.inlinePlayButton.on("click", function (e) {
            $YTPlayer.YTPPlay();
            e.stopPropagation();
          });
          
          if (YTPlayer.opt.autoPlay)
            YTPlayer.inlinePlayButton.hide();
          
          YTPlayer.overlay.on("click", function () {
            $YTPlayer.YTPTogglePlay();
          }).css({cursor: "pointer"})
        }
        
        /**
         create the playerBox where the YT iframe will be placed
         */
        var playerBox = jQuery("<div/>").attr("id", YTPlayer.playerID).addClass("playerBox");
        playerBox.css({
          position: "absolute",
          zIndex  : 0,
          width   : "100%",
          height  : "100%",
          top     : 0,
          left    : 0,
          overflow: "hidden",
          opacity : 1
        });
        
        YTPlayer.wrapper.append(playerBox);
        playerBox.after(YTPlayer.overlay);
        
        if (YTPlayer.isPlayer) {
          YTPlayer.inlineWrapper = jQuery("<div/>").addClass("inline-YTPlayer");
          
          YTPlayer.inlineWrapper.css({
            position: "relative",
            maxWidth: YTPlayer.opt.containment.css("width")
          });
          
          YTPlayer.opt.containment.css({
            position     : "relative",
            paddingBottom: "56.25%",
            overflow     : "hidden",
            height       : 0
          });
          YTPlayer.opt.containment.wrap(YTPlayer.inlineWrapper);
        }
        
        /**
         Loop all the elements inside the container and check if their position is not "static"
         */
        YTPlayer.opt.containment.children().not("script, style").each(function () {
          if (jQuery(this).css("position") == "static")
            jQuery(this).css("position", "relative");
        });
        
        if (YTPlayer.isBackground) {
          jQuery("body").css({
            boxSizing: "border-box"
          });
          
          YTPlayer.wrapper.css({
            position: "fixed",
            top     : 0,
            left    : 0,
            zIndex  : 0
          });
          
        } else if (YTPlayer.opt.containment.css("position") == "static") {
          
          YTPlayer.opt.containment.css({
            position: "relative"
          });
          $YTPlayer.show();
        }
        YTPlayer.opt.containment.prepend(YTPlayer.wrapper);
        
        if (!YTPlayer.isBackground) {
          YTPlayer.overlay.on("mouseenter", function () {
            if (YTPlayer.controlBar && YTPlayer.controlBar.length)
              YTPlayer.controlBar.addClass("visible");
          }).on("mouseleave", function () {
            if (YTPlayer.controlBar && YTPlayer.controlBar.length)
              YTPlayer.controlBar.removeClass("visible");
          });
        }
        
        if (jQuery.mbBrowser.mobile && !YTPlayer.opt.useOnMobile) {
          if (YTPlayer.opt.mobileFallbackImage) {
            YTPlayer.wrapper.css({
              backgroundImage   : "url(" + YTPlayer.opt.mobileFallbackImage + ")",
              backgroundPosition: "center center",
              backgroundSize    : "cover",
              backgroundRepeat  : "no-repeat",
              opacity           : 1
            });
            YTPlayer.wrapper.css({opacity: 1})
          }
          return $YTPlayer;
        }
        
        /**
         If is on device start playing on first touch
         */
        if (jQuery.mbBrowser.mobile && YTPlayer.opt.autoPlay && YTPlayer.opt.useOnMobile)
          jQuery("body").one("touchstart", function () {
            YTPlayer.player.playVideo();
          });
        
        jQuery(document).one("YTAPIReady", function () {
          $YTPlayer.trigger("YTAPIReady_" + YTPlayer.id);
          ytp.YTAPIReady = true;
        });
        
        YTPlayer.isOnScreen = jQuery.mbYTPlayer.isOnScreen(YTPlayer, YTPlayer.opt.onScreenPercentage);
        
        $YTPlayer.one("YTAPIReady_" + YTPlayer.id, function () {
          
          var YTPlayer = this;
          var $YTPlayer = jQuery(YTPlayer);
          
          if ((YTPlayer.isBackground && ytp.backgroundIsInited) || YTPlayer.isInit)
            return;
          
          if (YTPlayer.isBackground)
            ytp.backgroundIsInited = true;
          
          YTPlayer.opt.autoPlay = typeof YTPlayer.opt.autoPlay == "undefined" ? (YTPlayer.isBackground ? true : false) : YTPlayer.opt.autoPlay;
          YTPlayer.opt.vol = YTPlayer.opt.vol ? YTPlayer.opt.vol : 100;
          
          jQuery.mbYTPlayer.getDataFromAPI(YTPlayer);
          
          jQuery(YTPlayer).on("YTPChanged", function (e) {
            
            if (YTPlayer.isInit)
              return;
            
            YTPlayer.isInit = true;
            
            /** Initialize the YT player ------------------------------------
             * Youtube player variables
             * @type {{modestbranding: number, autoplay: number, controls: number, showinfo: number, rel: number, enablejsapi: number, version: number, playerapiid: string, origin: string, allowfullscreen: boolean, iv_load_policy: (string|*|jQuery.mbYTPlayer.opt.showAnnotations), playsinline: number}}
             */
            var playerVars = {
              'modestbranding' : 1,
              'autoplay'       : 0,
              'controls'       : 0,
              'showinfo'       : 0,
              'rel'            : 0,
              'enablejsapi'    : 1,
              'version'        : 3,
              'playerapiid'    : YTPlayer.playerID,
              'origin'         : '*',
              'allowfullscreen': true,
              'wmode'          : 'transparent',
              'iv_load_policy' : YTPlayer.opt.showAnnotations,
              'cc_load_policy' : YTPlayer.opt.cc_load_policy,
              'playsinline'    : jQuery.mbBrowser.mobile ? 1 : 0,
              
              /**
               Check if the browser can play HTML5 videos
               */
              'html5': document.createElement('video').canPlayType ? 1 : 0
            };
            
            new YT.Player(YTPlayer.playerID, {
              //videoId: YTPlayer.videoID.toString(),
              playerVars: playerVars,
              events    : {
                'onReady'                : function (event) {
                  
                  YTPlayer.player = event.target;
                  
                  //todo: make playlist works
                  /* if (YTPlayer.playlistID && YTPlayer.apiKey) {
                      YTPlayer.isList = true;
                      YTPlayer.videos = [];
                      YTPlayer.player.cuePlaylist({
                        listType: 'playlist',
                        list: YTPlayer.playlistID.toString(),
                        startSeconds: YTPlayer.opt.startAt,
                        endSeconds: YTPlayer.opt.stopAt,
                        suggestedQuality: YTPlayer.opt.quality
                      });
                    }
                     else { */
                  
                  YTPlayer.player.loadVideoById({
                    videoId         : YTPlayer.videoID.toString(),
                    // startSeconds: YTPlayer.start_from_last || YTPlayer.opt.startAt,
                    // endSeconds: YTPlayer.opt.stopAt,
                    suggestedQuality: YTPlayer.opt.quality
                  });
                  
                  /*}*/
                  
                  $YTPlayer.trigger("YTPlayerIsReady_" + YTPlayer.id);
                },
                /**
                 * on State Change
                 * @param event
                 *
                 * -1 (unstarted)
                 * 0 (ended)
                 * 1 (playing)
                 * 2 (paused)
                 * 3 (buffering)
                 * 5 (video cued)
                 */
                'onStateChange'          : function (event) {
                  
                  if (typeof event.target.getPlayerState != "function")
                    return;
                  
                  var state = event.target.getPlayerState();

                  if (YTPlayer.preventTrigger || YTPlayer.isStarting) {
                    YTPlayer.preventTrigger = false;
                    return
                  }
                  
                  YTPlayer.state = state;
                  // console.debug(YTPlayer.state);

                  if (event.data == YT.PlayerState.PLAYING) {
                    // console.debug('YTPlayer.opt.quality', YTPlayer.opt.quality)
                    event.target.setPlaybackQuality(YTPlayer.opt.quality);
                  }

                  // console.debug('YTPGetVideoQuality', jQuery(YTPlayer).YTPGetVideoQuality());

                  var eventType;
                  switch (state) {
                      
                      /** unstarted */
                    case -1:
                      eventType = "YTPUnstarted";
                      break;
                      
                      /** unstarted */
                    case 0:
                      eventType = "YTPRealEnd";
                      break;
                      
                      /** play */
                    case 1:
                      eventType = "YTPPlay";
                      if (YTPlayer.controlBar.length)
                        YTPlayer.controlBar.find(".mb_YTPPlayPause").html(jQuery.mbYTPlayer.controls.pause);
                      
                      if (YTPlayer.isPlayer)
                        YTPlayer.inlinePlayButton.hide();
                      
                      jQuery(document).off("mousedown.YTPstart");
                      break;
                      
                      /** pause */
                    case 2:
                      eventType = "YTPPause";
                      if (YTPlayer.controlBar.length)
                        YTPlayer.controlBar.find(".mb_YTPPlayPause").html(jQuery.mbYTPlayer.controls.play);
                      
                      if (YTPlayer.isPlayer)
                        YTPlayer.inlinePlayButton.show();
                      break;
                      
                      /** buffer */
                    case 3:
                      YTPlayer.player.setPlaybackQuality(YTPlayer.opt.quality);
                      eventType = "YTPBuffering";
                      if (YTPlayer.controlBar.length)
                        YTPlayer.controlBar.find(".mb_YTPPlayPause").html(jQuery.mbYTPlayer.controls.play);
                      break;
                      
                      /** cued */
                    case 5:
                      eventType = "YTPCued";
                      break;
                    
                    default:
                      break;
                  }
                  
                  /**
                   Trigger state events
                   */
                  var YTPEvent = jQuery.Event(eventType);
                  YTPEvent.time = YTPlayer.currentTime;
                  jQuery(YTPlayer).trigger(YTPEvent);
                },
                /**
                 * onPlaybackQualityChange
                 * @param e
                 */
                'onPlaybackQualityChange': function (e) {
                  var quality = e.target.getPlaybackQuality();
                  var YTPQualityChange = jQuery.Event("YTPQualityChange");
                  YTPQualityChange.quality = quality;
                  jQuery(YTPlayer).trigger(YTPQualityChange);
                },
                /**
                 * onError
                 * @param err
                 *
                 2 – The request contains an invalid parameter value. For example, this error occurs if you specify a video ID that does not have 11 characters, or if the video ID contains invalid characters, such as exclamation points or asterisks.
                 5 – The requested content cannot be played in an HTML5 player or another error related to the HTML5 player has occurred.
                 100 – The video requested was not found. This error occurs when a video has been removed (for any reason) or has been marked as private.
                 101 – The owner of the requested video does not allow it to be played in embedded players.
                 150 – This error is the same as 101. It's just a 101 error in disguise!
                 */
                'onError'                : function (err) {
                  
                  if (typeof YTPlayer.opt.onError == "function")
                    YTPlayer.opt.onError($YTPlayer, err);
                  
                  switch (err.data) {
                    case 2:
                      console.error("video ID:: " + YTPlayer.videoID + ": The request contains an invalid parameter value. For example, this error occurs if you specify a video ID that does not have 11 characters, or if the video ID contains invalid characters, such as exclamation points or asterisks.");
                      break;
                    case 5:
                      console.error("video ID:: " + YTPlayer.videoID + ": The requested content cannot be played in an HTML5 player or another error related to the HTML5 player has occurred.");
                      break;
                    case 100:
                      console.error("video ID:: " + YTPlayer.videoID + ": The video requested was not found. This error occurs when a video has been removed (for any reason) or has been marked as private.");
                      break;
                    case 101:
                    case 150:
                      console.error("video ID:: " + YTPlayer.videoID + ": The owner of the requested video does not allow it to be played in embedded players.");
                      break;
                  }
                  
                  if (YTPlayer.isList)
                    jQuery(YTPlayer).YTPPlayNext();
                  
                }
              }
            });
            
            $YTPlayer.on("YTPlayerIsReady_" + YTPlayer.id, function () {
              
              if (YTPlayer.isReady)
                return this;
              
              YTPlayer.playerEl = YTPlayer.player.getIframe();
              jQuery(YTPlayer.playerEl).unselectable();
              $YTPlayer.optimizeDisplay();
              
              /**
               * Optimize display on resize
               */
              jQuery(window).off("resize.YTP_" + YTPlayer.id).on("resize.YTP_" + YTPlayer.id, function () {
                $YTPlayer.optimizeDisplay();
              });
              
              /**
               * Set the time of the last visit progress
               */
              if (YTPlayer.opt.remember_last_time) {
                jQuery(window).on("unload.YTP_" + YTPlayer.id, function () {
                  var current_time = YTPlayer.player.getCurrentTime();
                  jQuery.mbCookie.set("YTPlayer_start_from" + YTPlayer.videoID, current_time, 0);
                });
              }
              
              $YTPlayer.YTPCheckForState();
              
            });
          });
        });
        
        $YTPlayer.off("YTPTime.mask");
        jQuery.mbYTPlayer.applyMask(YTPlayer);
        
        // console.timeEnd( "YTPlayerInit" );
      });
    },
    
    /**
     * isOnScreen
     * Check if the YTPlayer is on screen
     * @param YTPlayer
     * @returns {boolean}
     */
    isOnScreen: function (YTPlayer, perc) {
      perc = perc || 10;
      var playerBox = YTPlayer.wrapper;
      var winTop = jQuery(window).scrollTop();
      var winBottom = winTop + jQuery(window).height();
      
      var margin = (playerBox.height() * perc) / 100;
      var elTop = playerBox.offset().top + margin;
      var elBottom = playerBox.offset().top + (playerBox.height() - margin);
      
      return ((elBottom <= winBottom) && (elTop >= winTop));
    },
    
    /**
     * getDataFromAPI
     * @param YTPlayer
     */
    getDataFromAPI: function (YTPlayer) {
      
      //console.debug("getDataFromAPI", YTPlayer.id, YTPlayer.videoID)
      
      YTPlayer.videoData = jQuery.mbStorage.get("YTPlayer_data_" + YTPlayer.videoID);
      /*
            jQuery(YTPlayer).off("YTPData.YTPlayer").on("YTPData.YTPlayer", function () {
              if (YTPlayer.hasData) {
                if (YTPlayer.opt.coverImage || YTPlayer.orig_containment_background != "none") {
                  // if (YTPlayer.isPlayer && !YTPlayer.opt.autoPlay) {
                  var bgndURL = YTPlayer.opt.coverImage ? "url(" + YTPlayer.opt.coverImage + ") center center" : YTPlayer.orig_containment_background;
                  YTPlayer.opt.containment.css({
                    background: bgndURL,
                    backgroundColor: "#000",
                    backgroundSize: "cover",
                    backgroundRepeat: "no-repeat"
                  });
                }
              }
            });
      */
      
      if (YTPlayer.videoData) {
        
        setTimeout(function () {
          YTPlayer.dataReceived = true;
          
          var YTPChanged = jQuery.Event("YTPChanged");
          YTPChanged.time = YTPlayer.currentTime;
          YTPChanged.videoId = YTPlayer.videoID;
          YTPChanged.opt = YTPlayer.opt;
          jQuery(YTPlayer).trigger(YTPChanged);
          
          var YTPData = jQuery.Event("YTPData");
          YTPData.prop = {};
          for (var x in YTPlayer.videoData)
            YTPData.prop[x] = YTPlayer.videoData[x];
          jQuery(YTPlayer).trigger(YTPData);
          
        }, YTPlayer.opt.fadeOnStartTime);
        
        YTPlayer.hasData = true;
        
      } else if (jQuery.mbYTPlayer.apiKey) {
        
        /**
         * Get video info from API3 (needs api key)
         * snippet,player,contentDetails,statistics,status
         */
        jQuery.getJSON("https://www.googleapis.com/youtube/v3/videos?id=" + YTPlayer.videoID + "&key=" + jQuery.mbYTPlayer.apiKey + "&part=snippet", function (data) {
          YTPlayer.dataReceived = true;
          
          var YTPChanged = jQuery.Event("YTPChanged");
          YTPChanged.time = YTPlayer.currentTime;
          YTPChanged.videoId = YTPlayer.videoID;
          jQuery(YTPlayer).trigger(YTPChanged);
          
          function parseYTPlayer_data(data) {
            YTPlayer.videoData = {};
            YTPlayer.videoData.id = YTPlayer.videoID;
            YTPlayer.videoData.channelTitle = data.channelTitle;
            YTPlayer.videoData.title = data.title;
            YTPlayer.videoData.description = data.description.length < 400 ? data.description : data.description.substring(0, 400) + " ...";
            YTPlayer.videoData.thumb_max = data.thumbnails.maxres ? data.thumbnails.maxres.url : null;
            YTPlayer.videoData.thumb_high = data.thumbnails.high ? data.thumbnails.high.url : null;
            YTPlayer.videoData.thumb_medium = data.thumbnails.medium ? data.thumbnails.medium.url : null;
            jQuery.mbStorage.set("YTPlayer_data_" + YTPlayer.videoID, YTPlayer.videoData);
          }
          
          if (!data.items[0]) {
            YTPlayer.videoData = {};
            YTPlayer.hasData = false;
          } else {
            parseYTPlayer_data(data.items[0].snippet);
            YTPlayer.hasData = true;
          }
          
          var YTPData = jQuery.Event("YTPData");
          YTPData.prop = {};
          for (var x in YTPlayer.videoData) YTPData.prop[x] = YTPlayer.videoData[x];
          jQuery(YTPlayer).trigger(YTPData);
        });
        
      } else {
        
        setTimeout(function () {
          var YTPChanged = jQuery.Event("YTPChanged");
          YTPChanged.time = YTPlayer.currentTime;
          YTPChanged.videoId = YTPlayer.videoID;
          jQuery(YTPlayer).trigger(YTPChanged);
        }, 10);
        
        /*
                if (!YTPlayer.opt.autoPlay) {
                  // if (YTPlayer.isPlayer && !YTPlayer.opt.autoPlay) {
                  var bgndURL = YTPlayer.opt.coverImage ? "url(" + YTPlayer.opt.coverImage + ") center center" : YTPlayer.orig_containment_background;
                  
                  if (bgndURL) {
                    
                    YTPlayer.opt.containment.css({
                      background: bgndURL,
                      backgroundSize: "cover"
                    });
                  }
                }
        */
        YTPlayer.videoData = null;
        
      }
      
      YTPlayer.opt.ratio = YTPlayer.opt.ratio == "auto" ? 16 / 9 : YTPlayer.opt.ratio;
      
      if (YTPlayer.isPlayer && !YTPlayer.opt.autoPlay) { //&& ( !jQuery.mbBrowser.mobile && !jQuery.isTablet )
        YTPlayer.loading = jQuery("<div/>").addClass("loading").html("Loading").hide();
        jQuery(YTPlayer).append(YTPlayer.loading);
        YTPlayer.loading.fadeIn();
      }
    },
    
    /**
     * removeStoredData
     */
    removeStoredData: function () {
      jQuery.mbStorage.remove();
    },
    
    /**
     * getVideoData
     * @returns {*|YTPlayer.videoData}
     */
    getVideoData: function () {
      var YTPlayer = this.get(0);
      return YTPlayer.videoData;
    },
    
    /**
     * getVideoID
     * @returns {*|YTPlayer.videoID|boolean}
     */
    getVideoID: function () {
      var YTPlayer = this.get(0);
      return YTPlayer.videoID || false;
    },
    
    /**
     * getPlaylistID
     * @returns {*|YTPlayer.videoID|boolean}
     */
    getPlaylistID  : function () {
      var YTPlayer = this.get(0);
      return YTPlayer.playlistID || false;
    },
    /**
     * setVideoQuality
     * @param quality
     * @returns {jQuery.mbYTPlayer}
     */
    setVideoQuality: function (quality) {
      var YTPlayer = this.get(0);
      jQuery(YTPlayer).YTPPause();
      YTPlayer.opt.quality = quality;
      YTPlayer.player.setPlaybackQuality(quality);
       jQuery(YTPlayer).YTPPlay();
      return this;
    },

     /**
     * getVideoQuality
     * @returns {jQuery.mbYTPlayer}
     */
    getVideoQuality: function () {
      var YTPlayer = this.get(0);
      var quality = YTPlayer.player.getPlaybackQuality();
      return quality;
    },

    /**
     * playlist
     * @param videos -> Array or String (videoList ID)
     * @param shuffle
     * @param callback
     * @returns {jQuery.mbYTPlayer}
     *
     * To retrieve a Youtube playlist the Youtube API key is required:
     * https://console.developers.google.com/
     * jQuery.mbYTPlayer.apiKey
     */
    playlist: function (videos, shuffle, callback) {
      
      var $YTPlayer = this;
      var YTPlayer = $YTPlayer.get(0);
      
      /*
      if (typeof videos == "String" && jQuery.mbYTPlayer.apiKey != "") {
        function getVideoListFromYoutube(playListID, page) {
          page = page || '';
          var youtubeAPI = "https://www.googleapis.com/youtube/v3/playlistItems";
          jQuery.getJSON(youtubeAPI, {
            part      : "snippet,contentDetails",
            playlistId: playListID, //You have to enter the PlaylistID
            maxResults: 50,
            pageToken : page,
            key       : jQuery.mbYTPlayer.apiKey //You have to enter your own YoutubeAPIKey
          }).done(function (response) {
            CreateVideosArray(response);
            if (response.nextPageToken) {
              page = response.nextPageToken;
              getVideoListFromYoutube(plID, page, videos);
            } else {
              $YTPlayer.YTPlaylist(YTPlayer.videos, shuffle, callback)
            }
            ;
          });
        };
        
        function CreateVideosArray(response) {
          var k = response.items.length;
          for (var i = 0; i < k; i++) {
            YTPlayer.videos.push({
              "videoURL": response.items[i].contentDetails.videoId
            });
          }
          ;
        };
        
        getVideoListFromYoutube(videos);
        return this;
      }
      */
      
      YTPlayer.isList = true;
      
      if (shuffle)
        videos = jQuery.shuffle(videos);
      
      if (!YTPlayer.videoID) {
        YTPlayer.videos = videos;
        YTPlayer.videoCounter = 1;
        YTPlayer.videoLength = videos.length;
        jQuery(YTPlayer).data("property", videos[0]);
        jQuery(YTPlayer).YTPlayer();
      }
      
      if (typeof callback == "function")
        jQuery(YTPlayer).on("YTPChanged", function () {
          callback(YTPlayer);
        });
      
      jQuery(YTPlayer).on("YTPEnd", function () {
        jQuery(YTPlayer).YTPPlayNext();
      });
      return this;
    },
    
    /**
     * playNext
     * @returns {jQuery.mbYTPlayer}
     */
    playNext: function () {
      var YTPlayer = this.get(0);
      YTPlayer.videoCounter++;
      if (YTPlayer.videoCounter > YTPlayer.videoLength)
        YTPlayer.videoCounter = 1;
      jQuery(YTPlayer).YTPPlayIndex(YTPlayer.videoCounter);
      return this;
    },
    
    /**
     * playPrev
     * @returns {jQuery.mbYTPlayer}
     */
    playPrev: function () {
      var YTPlayer = this.get(0);
      YTPlayer.videoCounter--;
      if (YTPlayer.videoCounter <= 0)
        YTPlayer.videoCounter = YTPlayer.videoLength;
      jQuery(YTPlayer).YTPPlayIndex(YTPlayer.videoCounter);
      return this;
    },
    
    /**
     * playIndex
     * @param idx
     * @returns {jQuery.mbYTPlayer}
     */
    playIndex: function (idx) {
      var YTPlayer = this.get(0);
      if (YTPlayer.checkForStartAt) {
        clearInterval(YTPlayer.checkForStartAt);
        clearInterval(YTPlayer.getState);
      }
      YTPlayer.videoCounter = idx;
      
      if (YTPlayer.videoCounter >= YTPlayer.videoLength)
        YTPlayer.videoCounter = YTPlayer.videoLength;
      
      var video = YTPlayer.videos[YTPlayer.videoCounter - 1];
      
      jQuery(YTPlayer).YTPChangeVideo(video);
      return this;
    },
    
    /**
     * changeVideo
     * @param opt
     * @returns {jQuery.mbYTPlayer}
     */
    changeVideo: function (opt) {
      var $YTPlayer = this;
      var YTPlayer = $YTPlayer.get(0);
      
      YTPlayer.opt.startAt = 0;
      YTPlayer.opt.stopAt = 0;
      YTPlayer.opt.mask = false;
      YTPlayer.opt.mute = true;
      YTPlayer.opt.autoPlay = true;
      YTPlayer.opt.addFilters = false;
      YTPlayer.opt.coverImage = false;
      
      YTPlayer.hasData = false;
      YTPlayer.hasChanged = true;
      
      YTPlayer.player.loopTime = undefined;
      
      if (opt)
        jQuery.extend(YTPlayer.opt, opt);
      
      //console.debug("changeVideo::", YTPlayer.opt);
      
      YTPlayer.videoID = getYTPVideoID(YTPlayer.opt.videoURL).videoID;
      
      if (YTPlayer.opt.loop && typeof YTPlayer.opt.loop == "boolean")
        YTPlayer.opt.loop = 9999;
      
      YTPlayer.wrapper.css({
        background: "none"
      });
      
      jQuery(YTPlayer.playerEl).CSSAnimate({
        opacity: 0
      }, YTPlayer.opt.fadeOnStartTime, function () {
        
        jQuery.mbYTPlayer.getDataFromAPI(YTPlayer);
        
        //console.debug("YTPGetPlayer::", $YTPlayer.YTPGetPlayer());
        
        $YTPlayer.YTPGetPlayer().loadVideoById({
          videoId         : YTPlayer.videoID,
          // startSeconds: YTPlayer.opt.startAt,
          // endSeconds: YTPlayer.opt.stopAt,
          suggestedQuality: YTPlayer.opt.quality
        });
        $YTPlayer.YTPPause();
        $YTPlayer.optimizeDisplay();
        
        $YTPlayer.YTPCheckForState();
      });
      
      var YTPChangeVideo = jQuery.Event("YTPChangeVideo");
      YTPChangeVideo.time = YTPlayer.currentTime;
      jQuery(YTPlayer).trigger(YTPChangeVideo);
      
      jQuery.mbYTPlayer.applyMask(YTPlayer);
      
      return this;
    },
    
    /**
     * getPlayer
     * @returns {player}
     */
    getPlayer: function () {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return null;
      return YTPlayer.player || null;
    },
    
    /**
     * playerDestroy
     * @returns {jQuery.mbYTPlayer}
     */
    playerDestroy: function () {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      ytp.YTAPIReady = true;
      ytp.backgroundIsInited = false;
      YTPlayer.isInit = false;
      YTPlayer.videoID = null;
      YTPlayer.isReady = false;
      YTPlayer.wrapper.remove();
      jQuery("#controlBar_" + YTPlayer.id).remove();
      clearInterval(YTPlayer.checkForStartAt);
      clearInterval(YTPlayer.getState);
      return this;
    },
    
    /**
     * fullscreen
     * @param real
     * @returns {jQuery.mbYTPlayer}
     */
    fullscreen: function (real) {
      var YTPlayer = this.get(0);
      
      if (typeof real == "undefined")
        real = eval(YTPlayer.opt.realFullscreen);
      
      var controls = jQuery("#controlBar_" + YTPlayer.id);
      var fullScreenBtn = controls.find(".mb_OnlyYT");
      var videoWrapper = YTPlayer.isPlayer ? YTPlayer.opt.containment : YTPlayer.wrapper;
      
      if (real) {
        var fullscreenchange = jQuery.mbBrowser.mozilla ? "mozfullscreenchange" : jQuery.mbBrowser.webkit ? "webkitfullscreenchange" : "fullscreenchange";
        jQuery(document).off(fullscreenchange).on(fullscreenchange, function () {
          var isFullScreen = RunPrefixMethod(document, "IsFullScreen") || RunPrefixMethod(document, "FullScreen");
          if (!isFullScreen) {
            YTPlayer.isAlone = false;
            fullScreenBtn.html(jQuery.mbYTPlayer.controls.onlyYT);
            jQuery(YTPlayer).YTPSetVideoQuality(YTPlayer.opt.quality);
            videoWrapper.removeClass("YTPFullscreen");
            videoWrapper.CSSAnimate({
              opacity: YTPlayer.opt.opacity
            }, YTPlayer.opt.fadeOnStartTime);
            
            videoWrapper.css({
              zIndex: 0
            });
            
            if (YTPlayer.isBackground) {
              jQuery("body").after(controls);
            } else {
              YTPlayer.wrapper.before(controls);
            }
            jQuery(window).resize();
            jQuery(YTPlayer).trigger("YTPFullScreenEnd");
            
          } else {
            
            jQuery(YTPlayer).YTPSetVideoQuality("default");
            jQuery(YTPlayer).trigger("YTPFullScreenStart");
            
          }
        });
      }
      if (!YTPlayer.isAlone) {
        function hideMouse() {
          YTPlayer.overlay.css({
            cursor: "none"
          });
        }
        
        jQuery(document).on("mousemove.YTPlayer", function (e) {
          YTPlayer.overlay.css({
            cursor: "auto"
          });
          clearTimeout(YTPlayer.hideCursor);
          if (!jQuery(e.target).parents().is(".mb_YTPBar"))
            YTPlayer.hideCursor = setTimeout(hideMouse, 3000);
        });
        
        hideMouse();
        
        if (real) {
          videoWrapper.css({
            opacity: 0
          });
          videoWrapper.addClass("YTPFullscreen");
          launchFullscreen(videoWrapper.get(0));
          
          setTimeout(function () {
            videoWrapper.CSSAnimate({
              opacity: 1
            }, YTPlayer.opt.fadeOnStartTime * 2);
            
            videoWrapper.append(controls);
            jQuery(YTPlayer).optimizeDisplay();
            YTPlayer.player.seekTo(YTPlayer.player.getCurrentTime() + .1, true);
            
          }, YTPlayer.opt.fadeOnStartTime)
        } else
          videoWrapper.css({
            zIndex: 10000
          }).CSSAnimate({
            opacity: 1
          }, YTPlayer.opt.fadeOnStartTime * 2);
        fullScreenBtn.html(jQuery.mbYTPlayer.controls.showSite);
        YTPlayer.isAlone = true;
      } else {
        jQuery(document).off("mousemove.YTPlayer");
        clearTimeout(YTPlayer.hideCursor);
        YTPlayer.overlay.css({
          cursor: "auto"
        });
        if (real) {
          cancelFullscreen();
        } else {
          videoWrapper.CSSAnimate({
            opacity: YTPlayer.opt.opacity
          }, YTPlayer.opt.fadeOnStartTime);
          videoWrapper.css({
            zIndex: 0
          });
        }
        fullScreenBtn.html(jQuery.mbYTPlayer.controls.onlyYT);
        YTPlayer.isAlone = false;
      }
      
      function RunPrefixMethod(obj, method) {
        var pfx = ["webkit", "moz", "ms", "o", ""];
        var p = 0,
            m, t;
        while (p < pfx.length && !obj[m]) {
          m = method;
          if (pfx[p] == "") {
            m = m.substr(0, 1).toLowerCase() + m.substr(1);
          }
          m = pfx[p] + m;
          t = typeof obj[m];
          if (t != "undefined") {
            pfx = [pfx[p]];
            return (t == "function" ? obj[m]() : obj[m]);
          }
          p++;
        }
      }
      
      function launchFullscreen(element) {
        RunPrefixMethod(element, "RequestFullScreen");
      }
      
      function cancelFullscreen() {
        if (RunPrefixMethod(document, "FullScreen") || RunPrefixMethod(document, "IsFullScreen")) {
          RunPrefixMethod(document, "CancelFullScreen");
        }
      }
      
      return this;
    },
    
    /**
     * toggleLoops
     * @returns {jQuery.mbYTPlayer}
     */
    toggleLoops: function () {
      var YTPlayer = this.get(0);
      var data = YTPlayer.opt;
      if (data.loop == 1) {
        data.loop = 0;
      } else {
        if (data.startAt) {
          YTPlayer.player.seekTo(data.startAt);
        } else {
          YTPlayer.player.playVideo();
        }
        data.loop = 1;
      }
      return this;
    },
    
    /**
     * play
     * @returns {jQuery.mbYTPlayer}
     */
    play: function () {
      var YTPlayer = this.get(0);
      var $YTPlayer = jQuery(YTPlayer);
      
      if (!YTPlayer.isReady)
        return this;
      
      setTimeout(function () {
        $YTPlayer.YTPSetAbundance(YTPlayer.opt.abundance);
      }, 300)
      
      YTPlayer.player.playVideo();
      
      jQuery(YTPlayer.playerEl).css({
        opacity: 1
      });
      
      YTPlayer.wrapper.css({
        backgroundImage: "none"
      });
      
      YTPlayer.wrapper.CSSAnimate({
        opacity: YTPlayer.isAlone ? 1 : YTPlayer.opt.opacity
      }, YTPlayer.opt.fadeOnStartTime);
      
      var controls = jQuery("#controlBar_" + YTPlayer.id);
      var playBtn = controls.find(".mb_YTPPlayPause");
      playBtn.html(jQuery.mbYTPlayer.controls.pause);
      YTPlayer.state = 1;
      
      return this;
    },
    
    /**
     * togglePlay
     * @param callback
     * @returns {jQuery.mbYTPlayer}
     */
    togglePlay: function (callback) {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      if (YTPlayer.state == 1)
        this.YTPPause();
      else
        this.YTPPlay();
      
      if (typeof callback == "function")
        callback(YTPlayer.state);
      
      return this;
    },
    
    /**
     * stop
     * @returns {jQuery.mbYTPlayer}
     */
    stop: function () {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      var controls = jQuery("#controlBar_" + YTPlayer.id);
      var playBtn = controls.find(".mb_YTPPlayPause");
      playBtn.html(jQuery.mbYTPlayer.controls.play);
      YTPlayer.player.stopVideo();
      return this;
    },
    
    /**
     * pause
     * @returns {jQuery.mbYTPlayer}
     */
    pause: function () {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      if (YTPlayer.opt.abundance < .2)
        this.YTPSetAbundance(.2);
      
      YTPlayer.player.pauseVideo();
      YTPlayer.state = 2;
      return this;
    },
    
    /**
     * seekTo
     * @param sec
     * @returns {jQuery.mbYTPlayer}
     */
    seekTo: function (sec) {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      YTPlayer.player.seekTo(sec, true);
      return this;
    },
    
    /**
     * setVolume
     * @param val
     * @returns {jQuery.mbYTPlayer}
     */
    setVolume: function (val) {
      var YTPlayer = this.get(0);

      if (!YTPlayer.isReady)
        return this;
      
      YTPlayer.opt.vol = val;
      this.YTPUnmute();
      YTPlayer.player.setVolume(YTPlayer.opt.vol);

      if (YTPlayer.volumeBar && YTPlayer.volumeBar.length)
        YTPlayer.volumeBar.updateSliderVal(val);
      
      return this;
    },
    /**
     * getVolume
     * @returns {*}
     */
    getVolume: function () {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      return YTPlayer.player.getVolume();
    },
    
    /**
     * toggleVolume
     * @returns {jQuery.mbYTPlayer}
     */
    toggleVolume: function () {
      
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      if (YTPlayer.isMute) {
        if (!jQuery.mbBrowser.mobile)
          this.YTPSetVolume(YTPlayer.opt.vol)
        this.YTPUnmute();
      } else {
        this.YTPMute();
      }
      return this;
    },
    
    /**
     * mute
     * @returns {jQuery.mbYTPlayer}
     */
    mute: function () {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      if (YTPlayer.isMute)
        return this;
      YTPlayer.player.mute();
      YTPlayer.isMute = true;
      YTPlayer.player.setVolume(0);
      if (YTPlayer.volumeBar && YTPlayer.volumeBar.length && YTPlayer.volumeBar.width() > 10) {
        YTPlayer.volumeBar.updateSliderVal(0);
      }
      var controls = jQuery("#controlBar_" + YTPlayer.id);
      var muteBtn = controls.find(".mb_YTPMuteUnmute");
      muteBtn.html(jQuery.mbYTPlayer.controls.unmute);
      jQuery(YTPlayer).addClass("isMuted");
      if (YTPlayer.volumeBar && YTPlayer.volumeBar.length) YTPlayer.volumeBar.addClass("muted");
      var YTPEvent = jQuery.Event("YTPMuted");
      YTPEvent.time = YTPlayer.currentTime;
      
      if (!YTPlayer.preventTrigger)
        jQuery(YTPlayer).trigger(YTPEvent);
      
      return this;
    },
    
    /**
     * unmute
     * @returns {jQuery.mbYTPlayer}
     */
    unmute: function () {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;

      // console.debug("unmute::", YTPlayer.isMute,"Vol::", YTPlayer.opt.vol)

      if (!YTPlayer.isMute)
        return this;

      YTPlayer.player.unMute();
      YTPlayer.isMute = false;
      jQuery(YTPlayer).YTPSetVolume(YTPlayer.opt.vol);
      if (YTPlayer.volumeBar && YTPlayer.volumeBar.length)
        YTPlayer.volumeBar.updateSliderVal(YTPlayer.opt.vol > 10 ? YTPlayer.opt.vol : 10);
      var controls = jQuery("#controlBar_" + YTPlayer.id);
      var muteBtn = controls.find(".mb_YTPMuteUnmute");
      muteBtn.html(jQuery.mbYTPlayer.controls.mute);
      jQuery(YTPlayer).removeClass("isMuted");
      if (YTPlayer.volumeBar && YTPlayer.volumeBar.length)
        YTPlayer.volumeBar.removeClass("muted");
      var YTPEvent = jQuery.Event("YTPUnmuted");
      YTPEvent.time = YTPlayer.currentTime;
      
      if (!YTPlayer.preventTrigger)
        jQuery(YTPlayer).trigger(YTPEvent);
      
      return this;
    },
    
    /* FILTERS ---------------------------------------------------------------------------------------------------------*/
    
    /**
     * applyFilter
     * @param filter
     * @param value
     * @returns {jQuery.mbYTPlayer}
     */
    applyFilter: function (filter, value) {
      var $YTPlayer = this;
      var YTPlayer = $YTPlayer.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      YTPlayer.filters[filter].value = value;
      if (YTPlayer.filtersEnabled)
        $YTPlayer.YTPEnableFilters();
    },
    
    /**
     * applyFilters
     * @param filters
     * @returns {jQuery.mbYTPlayer}
     */
    applyFilters: function (filters) {
      var $YTPlayer = this;
      var YTPlayer = $YTPlayer.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      if (!YTPlayer.isReady) {
        jQuery(YTPlayer).on("YTPReady", function () {
          $YTPlayer.YTPApplyFilters(filters);
        });
        return this;
      }
      
      for (var key in filters) {
        $YTPlayer.YTPApplyFilter(key, filters[key]);
      }
      
      $YTPlayer.trigger("YTPFiltersApplied");
    },
    
    /**
     * toggleFilter
     * @param filter
     * @param value
     * @returns {jQuery.mbYTPlayer}
     */
    toggleFilter: function (filter, value) {
      var $YTPlayer = this;
      var YTPlayer = $YTPlayer.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      if (!YTPlayer.filters[filter].value)
        YTPlayer.filters[filter].value = value;
      else
        YTPlayer.filters[filter].value = 0;
      
      if (YTPlayer.filtersEnabled)
        jQuery(YTPlayer).YTPEnableFilters();
      
      return this;
    },
    
    /**
     * toggleFilters
     * @param callback
     * @returns {jQuery.mbYTPlayer}
     */
    toggleFilters: function (callback) {
      var $YTPlayer = this;
      var YTPlayer = $YTPlayer.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      if (YTPlayer.filtersEnabled) {
        jQuery(YTPlayer).trigger("YTPDisableFilters");
        jQuery(YTPlayer).YTPDisableFilters();
      } else {
        jQuery(YTPlayer).YTPEnableFilters();
        jQuery(YTPlayer).trigger("YTPEnableFilters");
      }
      if (typeof callback == "function")
        callback(YTPlayer.filtersEnabled);
      
      return this;
    },
    
    /**
     * disableFilters
     * @returns {jQuery.mbYTPlayer}
     */
    disableFilters: function () {
      var $YTPlayer = this;
      var YTPlayer = $YTPlayer.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      var iframe = jQuery(YTPlayer.playerEl);
      iframe.css("-webkit-filter", "");
      iframe.css("filter", "");
      YTPlayer.filtersEnabled = false;
      
      return this;
    },
    
    /**
     * enableFilters
     * @returns {jQuery.mbYTPlayer}
     */
    enableFilters: function () {
      var $YTPlayer = this;
      var YTPlayer = $YTPlayer.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      var iframe = jQuery(YTPlayer.playerEl);
      var filterStyle = "";
      for (var key in YTPlayer.filters) {
        if (YTPlayer.filters[key].value)
          filterStyle += key.replace("_", "-") + "(" + YTPlayer.filters[key].value + YTPlayer.filters[key].unit + ") ";
      }
      iframe.css("-webkit-filter", filterStyle);
      iframe.css("filter", filterStyle);
      YTPlayer.filtersEnabled = true;
      
      return this;
    },
    
    /**
     * removeFilter
     * @param filter
     * @param callback
     * @returns {jQuery.mbYTPlayer}
     */
    removeFilter: function (filter, callback) {
      var $YTPlayer = this;
      var YTPlayer = $YTPlayer.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      if (typeof filter == "function") {
        callback = filter;
        filter = null;
      }
      
      if (!filter) {
        for (var key in YTPlayer.filters) {
          $YTPlayer.YTPApplyFilter(key, 0);
        }
        
        if (typeof callback == "function")
          callback(key);
        
        YTPlayer.filters = jQuery.extend(true, {}, jQuery.mbYTPlayer.defaultFilters);
        
      } else {
        $YTPlayer.YTPApplyFilter(filter, 0);
        if (typeof callback == "function") callback(filter);
      }
      
      var YTPEvent = jQuery.Event("YTPFiltersApplied");
      $YTPlayer.trigger(YTPEvent);
      
      return this;
    },
    
    /**
     * getFilters
     * @returns {filters}
     */
    getFilters: function () {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      return YTPlayer.filters;
    },
    
    /* MASK ---------------------------------------------------------------------------------------------------------*/
    
    /**
     * addMask
     * @param mask
     * @returns {jQuery.mbYTPlayer}
     */
    addMask: function (mask) {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      if (!mask)
        mask = YTPlayer.actualMask;
      
      var tempImg = jQuery("<img/>").attr("src", mask).on("load", function () {
        YTPlayer.overlay.CSSAnimate({
          opacity: 0
        }, YTPlayer.opt.fadeOnStartTime, function () {
          YTPlayer.hasMask = true;
          tempImg.remove();
          YTPlayer.overlay.css({
            backgroundImage   : "url(" + mask + ")",
            backgroundRepeat  : "no-repeat",
            backgroundPosition: "center center",
            backgroundSize    : "cover"
          });
          YTPlayer.overlay.CSSAnimate({
            opacity: 1
          }, YTPlayer.opt.fadeOnStartTime);
        });
      });
      
      return this;
    },
    
    /**
     * removeMask
     * @returns {jQuery.mbYTPlayer}
     */
    removeMask: function () {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      YTPlayer.overlay.CSSAnimate({
        opacity: 0
      }, YTPlayer.opt.fadeOnStartTime, function () {
        YTPlayer.hasMask = false;
        YTPlayer.overlay.css({
          backgroundImage   : "",
          backgroundRepeat  : "",
          backgroundPosition: "",
          backgroundSize    : ""
        });
        YTPlayer.overlay.CSSAnimate({
          opacity: 1
        }, YTPlayer.opt.fadeOnStartTime);
      });
      
      return this;
    },
    
    /**
     * Apply mask
     * @param YTPlayer
     */
    applyMask: function (YTPlayer) {
      var $YTPlayer = jQuery(YTPlayer);
      if (!YTPlayer.isReady)
        return this;
      
      $YTPlayer.off("YTPTime.mask");
      
      if (YTPlayer.opt.mask) {
        if (typeof YTPlayer.opt.mask == "string") {
          $YTPlayer.YTPAddMask(YTPlayer.opt.mask);
          YTPlayer.actualMask = YTPlayer.opt.mask;
        } else if (typeof YTPlayer.opt.mask == "object") {
          for (var time in YTPlayer.opt.mask) {
            if (YTPlayer.opt.mask[time])
              var img = jQuery("<img/>").attr("src", YTPlayer.opt.mask[time]);
          }
          if (YTPlayer.opt.mask[0])
            $YTPlayer.YTPAddMask(YTPlayer.opt.mask[0]);
          $YTPlayer.on("YTPTime.mask", function (e) {
            for (var time in YTPlayer.opt.mask) {
              if (e.time == time)
                if (!YTPlayer.opt.mask[time]) {
                  $YTPlayer.YTPRemoveMask();
                } else {
                  $YTPlayer.YTPAddMask(YTPlayer.opt.mask[time]);
                  YTPlayer.actualMask = YTPlayer.opt.mask[time];
                }
            }
          });
        }
      }
    },
    
    /**
     * toggleMask
     * @returns {jQuery.mbYTPlayer}
     */
    toggleMask: function () {
      var YTPlayer = this.get(0);
      if (!YTPlayer.isReady)
        return this;
      
      var $YTPlayer = jQuery(YTPlayer);
      if (YTPlayer.hasMask)
        $YTPlayer.YTPRemoveMask();
      else
        $YTPlayer.YTPAddMask();
      return this;
    },
    
    /* CONTROLS --------------------------------------------------------------------------------------------------------*/
    
    /**
     * manageProgress
     * @returns {{totalTime: number, currentTime: number}}
     */
    manageProgress: function () {
      var YTPlayer = this.get(0);
      var controls = jQuery("#controlBar_" + YTPlayer.id);
      var progressBar = controls.find(".mb_YTPProgress");
      var loadedBar = controls.find(".mb_YTPLoaded");
      var timeBar = controls.find(".mb_YTPseekbar");
      var totW = progressBar.outerWidth();
      var currentTime = Math.floor(YTPlayer.player.getCurrentTime());
      var totalTime = Math.floor(YTPlayer.player.getDuration());
      var timeW = (currentTime * totW) / totalTime;
      var startLeft = 0;
      var loadedW = YTPlayer.player.getVideoLoadedFraction() * 100;
      loadedBar.css({
        left : startLeft,
        width: loadedW + "%"
      });
      timeBar.css({
        left : 0,
        width: timeW
      });
      return {
        totalTime  : totalTime,
        currentTime: currentTime
      };
    },
    
    /**
     * buildControls
     * @param YTPlayer
     */
    buildControls: function (YTPlayer) {
      
      jQuery("#controlBar_" + YTPlayer.id).remove();
      if (!YTPlayer.opt.showControls) {
        YTPlayer.controlBar = false;
        return;
      }
      
      // @YTPlayer.opt.printUrl: is deprecated; use YTPlayer.opt.showYTLogo
      YTPlayer.opt.showYTLogo = YTPlayer.opt.showYTLogo || YTPlayer.opt.printUrl;
      if (jQuery("#controlBar_" + YTPlayer.id).length)
        return;
      YTPlayer.controlBar = jQuery("<div/>").attr("id", "controlBar_" + YTPlayer.id).addClass("mb_YTPBar").css({
        whiteSpace: "noWrap",
        position  : YTPlayer.isBackground ? "fixed" : "absolute",
        zIndex    : YTPlayer.isBackground ? 10000 : 1000
      }).hide().on("click", function (e) {
        e.stopPropagation();
      });
      var buttonBar = jQuery("<div/>").addClass("buttonBar");
      /**
       *  play/pause button
       * */
      var playpause = jQuery("<span>" + jQuery.mbYTPlayer.controls.play + "</span>").addClass("mb_YTPPlayPause ytpicon").on("click", function (e) {
        e.stopPropagation();
        jQuery(YTPlayer).YTPTogglePlay();
      });
      /**
       *  mute/unmute button
       * */
      var MuteUnmute = jQuery("<span>" + jQuery.mbYTPlayer.controls.mute + "</span>").addClass("mb_YTPMuteUnmute ytpicon").on("click", function (e) {
        e.stopPropagation();
        jQuery(YTPlayer).YTPToggleVolume();
      });
      /**
       *  volume bar
       * */
      var volumeBar = jQuery("<div/>").addClass("mb_YTPVolumeBar").css({
        display: "inline-block"
      });
      YTPlayer.volumeBar = volumeBar;
      
      /**
       * time elapsed
       * */
      var idx = jQuery("<span/>").addClass("mb_YTPTime");
      var vURL = YTPlayer.opt.videoURL ? YTPlayer.opt.videoURL : "";
      if (vURL.indexOf("http") < 0) vURL = "https://www.youtube.com/watch?v=" + YTPlayer.opt.videoURL;
      var movieUrl = jQuery("<span/>").html(jQuery.mbYTPlayer.controls.ytLogo).addClass("mb_YTPUrl ytpicon").attr("title", "view on YouTube").on("click", function () {
        window.open(vURL, "viewOnYT")
      });
      var onlyVideo = jQuery("<span/>").html(jQuery.mbYTPlayer.controls.onlyYT).addClass("mb_OnlyYT ytpicon").on("click", function (e) {
        e.stopPropagation();
        jQuery(YTPlayer).YTPFullscreen(YTPlayer.opt.realFullscreen);
      });
      var progressBar = jQuery("<div/>").addClass("mb_YTPProgress").css("position", "absolute").on("click", function (e) {
        e.stopPropagation();
        timeBar.css({
          width: (e.clientX - timeBar.offset().left)
        });
        YTPlayer.timeW = e.clientX - timeBar.offset().left;
        YTPlayer.controlBar.find(".mb_YTPLoaded").css({
          width: 0
        });
        var totalTime = Math.floor(YTPlayer.player.getDuration());
        YTPlayer.goto = (timeBar.outerWidth() * totalTime) / progressBar.outerWidth();
        YTPlayer.player.seekTo(parseFloat(YTPlayer.goto), true);
        YTPlayer.controlBar.find(".mb_YTPLoaded").css({
          width: 0
        });
      });
      var loadedBar = jQuery("<div/>").addClass("mb_YTPLoaded").css("position", "absolute");
      var timeBar = jQuery("<div/>").addClass("mb_YTPseekbar").css("position", "absolute");
      progressBar.append(loadedBar).append(timeBar);
      buttonBar.append(playpause).append(MuteUnmute).append(volumeBar).append(idx);
      
      if (YTPlayer.opt.showYTLogo) {
        buttonBar.append(movieUrl);
      }
      
      /**
       * Full screen button
       */
      if (YTPlayer.isBackground || (eval(YTPlayer.opt.realFullscreen) && !YTPlayer.isBackground))
        buttonBar.append(onlyVideo);
      
      YTPlayer.controlBar.append(buttonBar).append(progressBar);
      
      if (!YTPlayer.isBackground) {
        YTPlayer.controlBar.addClass("inlinePlayer");
        YTPlayer.wrapper.before(YTPlayer.controlBar);
      } else {
        jQuery("body").after(YTPlayer.controlBar);
      }
      
      /**
       * Volume slider
       */
      volumeBar.simpleSlider({
        initialval : YTPlayer.opt.vol,
        scale      : 100,
        orientation: "h",
        callback   : function (el) {

          if (el.value == 0) {
            jQuery(YTPlayer).YTPMute();
          } else {
            jQuery(YTPlayer).YTPUnmute();
          }
          YTPlayer.player.setVolume(el.value);
          if (!YTPlayer.isMute)
            YTPlayer.opt.vol = el.value;

          // console.debug(jQuery(YTPlayer).YTPGetVolume())
        }

      });
    },
    
    /* MANAGE PLAYER STATE ------------------------------------------------------------------------------------------*/
    
    /**
     * checkForState
     */
    checkForState: function () {
      var YTPlayer = this.get(0);
      var $YTPlayer = jQuery(YTPlayer);
      
      clearInterval(YTPlayer.getState);
      var interval = 100;
      //Checking if player has been removed from the scene
      if (!jQuery.contains(document, YTPlayer)) {
        $YTPlayer.YTPPlayerDestroy();
        clearInterval(YTPlayer.getState);
        clearInterval(YTPlayer.checkForStartAt);
        return;
      }
      
      jQuery.mbYTPlayer.checkForStart(YTPlayer);
      
      YTPlayer.getState = setInterval(function () {
        var $YTPlayer = jQuery(YTPlayer);
        
        if (!YTPlayer.isReady)
          return;
        
        var prog = jQuery(YTPlayer).YTPManageProgress();
        
        var stopAt = YTPlayer.opt.stopAt > YTPlayer.opt.startAt ? YTPlayer.opt.stopAt : 0;
        stopAt = stopAt < YTPlayer.player.getDuration() ? stopAt : 0;

        if (YTPlayer.currentTime != prog.currentTime) {
          var YTPEvent = jQuery.Event("YTPTime");
          YTPEvent.time = YTPlayer.currentTime;
          jQuery(YTPlayer).trigger(YTPEvent);
        }
        
        YTPlayer.currentTime = prog.currentTime;
        YTPlayer.totalTime = YTPlayer.player.getDuration();
        if (YTPlayer.player.getVolume() == 0) $YTPlayer.addClass("isMuted");
        else $YTPlayer.removeClass("isMuted");
        
        if (YTPlayer.opt.showControls)
          if (prog.totalTime) {
            YTPlayer.controlBar.find(".mb_YTPTime").html(jQuery.mbYTPlayer.formatTime(prog.currentTime) + " / " + jQuery.mbYTPlayer.formatTime(prog.totalTime));
          } else {
            YTPlayer.controlBar.find(".mb_YTPTime").html("-- : -- / -- : --");
          }
        
        /**
         * Manage video pause on window blur
         */
        if (eval(YTPlayer.opt.stopMovieOnBlur)) {
          if (!document.hasFocus()) {
            if (YTPlayer.state == 1) {
              YTPlayer.hasFocus = false;
              YTPlayer.preventTrigger = true;
              $YTPlayer.YTPPause();
            }
          } else if (document.hasFocus() && !YTPlayer.hasFocus && !(YTPlayer.state == -1 || YTPlayer.state == 0)) {
            YTPlayer.hasFocus = true;
            YTPlayer.preventTrigger = true;
            $YTPlayer.YTPPlay();
          }
        }
        
        /**
         * Manage video pause if not on screen
         */
        if (YTPlayer.opt.playOnlyIfVisible) {
          var isOnScreen = jQuery.mbYTPlayer.isOnScreen(YTPlayer, YTPlayer.opt.onScreenPercentage);
          if (!isOnScreen && YTPlayer.state == 1) {
            YTPlayer.isOnScreen = false;
            $YTPlayer.YTPPause();
          } else if (isOnScreen && !YTPlayer.isOnScreen) {
            YTPlayer.isOnScreen = true;
            YTPlayer.player.playVideo();
          }
        }
        
        if (YTPlayer.controlBar.length && YTPlayer.controlBar.outerWidth() <= 400 && !YTPlayer.isCompact) {
          YTPlayer.controlBar.addClass("compact");
          YTPlayer.isCompact = true;
          if (!YTPlayer.isMute && YTPlayer.volumeBar) YTPlayer.volumeBar.updateSliderVal(YTPlayer.opt.vol);
        } else if (YTPlayer.controlBar.length && YTPlayer.controlBar.outerWidth() > 400 && YTPlayer.isCompact) {
          YTPlayer.controlBar.removeClass("compact");
          YTPlayer.isCompact = false;
          
          if (!YTPlayer.isMute && YTPlayer.volumeBar)
            YTPlayer.volumeBar.updateSliderVal(YTPlayer.opt.vol);
        }
        // the video is ended
        if (YTPlayer.player.getPlayerState() > 0 && ((parseFloat(YTPlayer.player.getDuration() - (YTPlayer.opt.fadeOnStartTime / 1000)) < YTPlayer.player.getCurrentTime()) || (stopAt > 0 && parseFloat(YTPlayer.player.getCurrentTime()) >= stopAt))) {
          
          if (YTPlayer.isEnded)
            return;
          
          YTPlayer.isEnded = true;

          setTimeout(function () {
            YTPlayer.isEnded = false
          }, 1000);
          
          if (YTPlayer.isList) {
            if (!YTPlayer.opt.loop || (YTPlayer.opt.loop > 0 && YTPlayer.player.loopTime === YTPlayer.opt.loop - 1)) {
              YTPlayer.player.loopTime = undefined;
              clearInterval(YTPlayer.getState);
              var YTPEnd = jQuery.Event("YTPEnd");
              YTPEnd.time = YTPlayer.currentTime;
              jQuery(YTPlayer).trigger(YTPEnd);
              return;
            }
          } else if (!YTPlayer.opt.loop || (YTPlayer.opt.loop > 0 && YTPlayer.player.loopTime === YTPlayer.opt.loop - 1)) {
            YTPlayer.player.loopTime = undefined;
            
            YTPlayer.state = 2;
            
            var bgndURL = YTPlayer.opt.coverImage ? "url(" + YTPlayer.opt.coverImage + ") center center" : YTPlayer.orig_containment_background;
            
            YTPlayer.opt.containment.css({
              background    : bgndURL,
              backgroundSize: "cover"
            });
            
            jQuery(YTPlayer).YTPPause();
            YTPlayer.wrapper.CSSAnimate({
              opacity: 0
            }, YTPlayer.opt.fadeOnStartTime, function () {
              
              if (YTPlayer.controlBar.length)
                YTPlayer.controlBar.find(".mb_YTPPlayPause").html(jQuery.mbYTPlayer.controls.play);
              
              var YTPEnd = jQuery.Event("YTPEnd");
              YTPEnd.time = YTPlayer.currentTime;
              jQuery(YTPlayer).trigger(YTPEnd);
              YTPlayer.player.seekTo(YTPlayer.opt.startAt, true);
              
              var bgndURL = YTPlayer.opt.coverImage ? "url(" + YTPlayer.opt.coverImage + ") center center" : YTPlayer.orig_containment_background;
              YTPlayer.opt.containment.css({
                background    : bgndURL,
                backgroundSize: "cover"
              });
              
            });
            return;
          }
          
          YTPlayer.player.loopTime = YTPlayer.player.loopTime ? ++YTPlayer.player.loopTime : 1;
          YTPlayer.opt.startAt = YTPlayer.opt.startAt || 1;
          YTPlayer.preventTrigger = true;
          YTPlayer.state = 2;
          //YTPlayer.player.pauseVideo();
          YTPlayer.player.seekTo(YTPlayer.opt.startAt, true);
          //YTPlayer.player.playVideo();
        }
      }, interval);
    },
    
    /**
     * checkForStart
     * @param YTPlayer
     */
    checkForStart: function (YTPlayer) {
      var $YTPlayer = jQuery(YTPlayer);
      
      /* If the player has been removed from scene destroy it */
      if (!jQuery.contains(document, YTPlayer)) {
        $YTPlayer.YTPPlayerDestroy();
        return;
      }
      
      /* CREATE CONTROL BAR */
      jQuery.mbYTPlayer.buildControls(YTPlayer);
      
      if (YTPlayer.overlay)
        if (YTPlayer.opt.addRaster) {
          var classN = YTPlayer.opt.addRaster == "dot" ? "raster-dot" : "raster";
          YTPlayer.overlay.addClass(YTPlayer.isRetina ? classN + " retina" : classN);
        } else {
          YTPlayer.overlay.removeClass(function (index, classNames) {
            // change the list into an array
            var current_classes = classNames.split(" "),
                // array of classes which are to be removed
                classes_to_remove = [];
            jQuery.each(current_classes, function (index, class_name) {
              // if the classname begins with bg add it to the classes_to_remove array
              if (/raster.*/.test(class_name)) {
                classes_to_remove.push(class_name);
              }
            });
            classes_to_remove.push("retina");
            // turn the array back into a string
            return classes_to_remove.join(" ");
          })
        }
      
      YTPlayer.preventTrigger = true;
      YTPlayer.state = 2;
      YTPlayer.preventTrigger = true;
      
      YTPlayer.player.mute();
      YTPlayer.player.playVideo();
      YTPlayer.isStarting = true;
      
      var startAt = YTPlayer.start_from_last ? YTPlayer.start_from_last : YTPlayer.opt.startAt ? YTPlayer.opt.startAt : 1;
      
      YTPlayer.preventTrigger = true;
      YTPlayer.checkForStartAt = setInterval(function () {
        
        YTPlayer.player.mute();
        YTPlayer.player.seekTo(startAt, true);
        
        var canPlayVideo = YTPlayer.player.getVideoLoadedFraction() >= startAt / YTPlayer.player.getDuration();
        if (YTPlayer.player.getDuration() > 0 && YTPlayer.player.getCurrentTime() >= startAt && canPlayVideo) {
          YTPlayer.start_from_last = null;
          
          YTPlayer.preventTrigger = true;
          $YTPlayer.YTPPause();
          
          clearInterval(YTPlayer.checkForStartAt);
          
          if (typeof YTPlayer.opt.onReady == "function")
            YTPlayer.opt.onReady(YTPlayer);
          
          YTPlayer.isReady = true;
          
          $YTPlayer.YTPRemoveFilter();
          
          if (YTPlayer.opt.addFilters) {
            $YTPlayer.YTPApplyFilters(YTPlayer.opt.addFilters);
          } else {
            $YTPlayer.YTPApplyFilters();
          }
          $YTPlayer.YTPEnableFilters();
          var YTPready = jQuery.Event("YTPReady");
          YTPready.time = YTPlayer.currentTime;
          $YTPlayer.trigger(YTPready);
          
          YTPlayer.state = 2;
          
          if (!YTPlayer.opt.mute) {
            YTPlayer.player.unMute();
            if (YTPlayer.opt.autoPlay)
              console.debug("To make the video 'auto-play' you must mute the audio according with the new vendor policy");
          }
          else{
            $YTPlayer.YTPMute();
/*
            YTPlayer.isMute = true;
            YTPlayer.player.mute();
*/
          }

          if (typeof _gaq != "undefined" && eval(YTPlayer.opt.gaTrack))
            _gaq.push(['_trackEvent', 'YTPlayer', 'Play', (YTPlayer.hasData ? YTPlayer.videoData.title : YTPlayer.videoID.toString())]);
          else if (typeof ga != "undefined" && eval(YTPlayer.opt.gaTrack))
            ga('send', 'event', 'YTPlayer', 'play', (YTPlayer.hasData ? YTPlayer.videoData.title : YTPlayer.videoID.toString()));
          
          if (YTPlayer.opt.autoPlay) {
            
            var YTPStart = jQuery.Event("YTPStart");
            YTPStart.time = YTPlayer.currentTime;
            jQuery(YTPlayer).trigger(YTPStart);
            
            YTPlayer.isStarting = false;
            
            /* Fix for Safari freeze */
            if (jQuery.mbBrowser.os.name == "mac" && jQuery.mbBrowser.safari) {
              jQuery("body").one("mousedown.YTPstart", function () {
                $YTPlayer.YTPPlay();
              });
            }
            
            $YTPlayer.YTPPlay();
            
          } else {
            
            YTPlayer.preventTrigger = true;
            $YTPlayer.YTPPause();
            
            if (YTPlayer.start_from_last)
              YTPlayer.player.seekTo(startAt, true);
            
            
            setTimeout(function () {
              YTPlayer.preventTrigger = true;
              $YTPlayer.YTPPause();
              
              // console.debug("YTPPause");
              
              if (!YTPlayer.isPlayer) {
                if (!YTPlayer.opt.coverImage) {
                  jQuery(YTPlayer.playerEl).CSSAnimate({
                    opacity: 1
                  }, YTPlayer.opt.fadeOnStartTime);
                  YTPlayer.wrapper.CSSAnimate({
                    opacity: YTPlayer.isAlone ? 1 : YTPlayer.opt.opacity
                  }, YTPlayer.opt.fadeOnStartTime);
                } else {
                  YTPlayer.wrapper.css({opacity: 0});
                  setTimeout(function () {
                    var bgndURL = YTPlayer.opt.coverImage ? "url(" + YTPlayer.opt.coverImage + ") center center" : YTPlayer.orig_containment_background;
                    YTPlayer.wrapper.css({
                      background      : bgndURL,
                      backgroundSize  : "cover",
                      backgroundRepeat: "no-repeat"
                    })
                  }, YTPlayer.opt.fadeOnStartTime)
                }
              }
              YTPlayer.isStarting = false;
            }, 500);
            
            if (YTPlayer.controlBar.length)
              YTPlayer.controlBar.find(".mb_YTPPlayPause").html(jQuery.mbYTPlayer.controls.play);
          }
          
          if (YTPlayer.isPlayer && !YTPlayer.opt.autoPlay && (YTPlayer.loading && YTPlayer.loading.length)) {
            YTPlayer.loading.html("Ready");
            setTimeout(function () {
              YTPlayer.loading.fadeOut();
            }, 100)
          }
          
          if (YTPlayer.controlBar && YTPlayer.controlBar.length)
            YTPlayer.controlBar.slideDown(1000);
        }
        
        if (jQuery.mbBrowser.os.name == "mac" && jQuery.mbBrowser.safari) {
          
          YTPlayer.player.playVideo();
          if (startAt >= 0)
            YTPlayer.player.seekTo(startAt, true);
          
        }
        
      }, 100);
      
      return $YTPlayer;
    },
    
    /* TIME METHODS -------------------------------------------------------------------------------------------*/
    
    /**
     * getTime
     * @returns {string} time
     */
    getTime: function () {
      var YTPlayer = this.get(0);
      return jQuery.mbYTPlayer.formatTime(YTPlayer.currentTime);
    },
    
    /**
     * getTotalTime
     * @returns {string} total time
     */
    getTotalTime: function (format) {
      var YTPlayer = this.get(0);
      return jQuery.mbYTPlayer.formatTime(YTPlayer.totalTime);
    },
    
    /**
     * formatTime
     * @param s
     * @returns {string}
     */
    formatTime: function (s) {
      var min = Math.floor(s / 60);
      var sec = Math.floor(s - (60 * min));
      return (min <= 9 ? "0" + min : min) + " : " + (sec <= 9 ? "0" + sec : sec);
    },
    
    /* PLAYER POSITION AND SIZE OPTIMIZATION-------------------------------------------------------------------------------------------*/
    
    /**
     * setAnchor
     * @param anchor
     */
    setAnchor: function (anchor) {
      var $YTplayer = this;
      $YTplayer.optimizeDisplay(anchor);
    },
    
    /**
     * getAnchor
     * @param anchor
     */
    getAnchor: function () {
      var YTPlayer = this.get(0);
      return YTPlayer.opt.anchor;
    },
    
    /**
     * setAbundance
     * @param val
     * @returns {jQuery.mbYTPlayer}
     */
    setAbundance: function (val, updateOptions) {
      var YTPlayer = this.get(0);
      var $YTPlayer = this;
      if (updateOptions)
        YTPlayer.opt.abundance = val;
      $YTPlayer.optimizeDisplay(YTPlayer.opt.anchor, val);
      return $YTPlayer;
    },
    
    /**
     * getAbundance
     * @returns {*}
     */
    getAbundance: function () {
      var YTPlayer = this.get(0);
      return YTPlayer.opt.abundance;
    },
    
    /**
     *
     * @param opt
     * @param val
     * @returns {jQuery.mbYTPlayer}
     */
    setOption: function (opt, val) {
      var YTPlayer = this.get(0);
      var $YTPlayer = this;
      YTPlayer.opt[opt] = val;
      return $YTPlayer;
    }
  };


  /**
   * optimizeDisplay
   * @param anchor
   * can be center, top, bottom, right, left; (default is center,center)
   */
  jQuery.fn.optimizeDisplay = function (anchor, abundanceX) {
    var YTPlayer = this.get(0);
    var vid = {};
    var el = YTPlayer.wrapper;
    var iframe = jQuery(YTPlayer.playerEl);

    YTPlayer.opt.anchor = anchor || YTPlayer.opt.anchor;

    // console.debug(YTPlayer.opt.anchor);

    YTPlayer.opt.anchor = typeof YTPlayer.opt.anchor != "undefined " ? YTPlayer.opt.anchor : "center,center";
    var YTPAlign = YTPlayer.opt.anchor.split(",");
    var ab = abundanceX ? abundanceX : YTPlayer.opt.abundance;

    if (YTPlayer.opt.optimizeDisplay) {
      var abundance = el.height() * ab;
      var win = {};
      win.width = el.outerWidth();
      win.height = el.outerHeight() + abundance;

      YTPlayer.opt.ratio = YTPlayer.opt.ratio === "auto" ? 16 / 9 : YTPlayer.opt.ratio;
      YTPlayer.opt.ratio = eval(YTPlayer.opt.ratio);

      vid.width = win.width + abundance;
      vid.height = Math.ceil(vid.width / YTPlayer.opt.ratio);
      vid.marginTop = Math.ceil(-((vid.height - win.height + abundance) / 2));
      vid.marginLeft = -(abundance / 2);
      var lowest = vid.height < win.height;

      if (lowest) {
        vid.height = win.height + abundance;
        vid.width = Math.ceil(vid.height * YTPlayer.opt.ratio);
        vid.marginTop = -(abundance/2);
        vid.marginLeft = Math.ceil(-((vid.width - win.width) / 2));
      }

      for (var a in YTPAlign) {
        if (YTPAlign.hasOwnProperty(a)) {
          var al = YTPAlign[a].replace(/ /g, "");

          switch (al) {
            case "top":
              vid.marginTop = -abundance;
              break;
            case "bottom":
              vid.marginTop = Math.ceil( -(vid.height - win.height) - (abundance / 2) );
              break;
            case "left":
              vid.marginLeft = -(abundance);
              break;
            case "right":
              vid.marginLeft = Math.ceil(-(vid.width - win.width) + (abundance / 2));
              break;
          }

        }
      }

    } else {
      vid.width = "100%";
      vid.height = "100%";
      vid.marginTop = 0;
      vid.marginLeft = 0;
    }

    iframe.css({
      width     : vid.width,
      height    : vid.height,
      marginTop : vid.marginTop,
      marginLeft: vid.marginLeft,
      maxWidth  : "initial"
    });


  };
  
  
  /* UTILITIES -----------------------------------------------------------------------------------------------------------------------*/
  
  /**
   * shuffle
   * @param arr
   * @returns {Array|string|Blob|*}
   *
   */
  jQuery.shuffle = function (arr) {
    var newArray = arr.slice();
    var len = newArray.length;
    var i = len;
    while (i--) {
      var p = parseInt(Math.random() * len);
      var t = newArray[i];
      newArray[i] = newArray[p];
      newArray[p] = t;
    }
    return newArray;
  };
  
  /**
   * Unselectable
   * @returns {*}
   */
  jQuery.fn.unselectable = function () {
    return this.each(function () {
      jQuery(this).css({
        "-moz-user-select"   : "none",
        "-webkit-user-select": "none",
        "user-select"        : "none"
      }).attr("unselectable", "on");
    });
  };
  
  /* EXTERNAL METHODS -----------------------------------------------------------------------------------------------------------------------*/
  
  jQuery.fn.YTPlayer = jQuery.mbYTPlayer.buildPlayer;
  jQuery.fn.mb_YTPlayer = jQuery.mbYTPlayer.buildPlayer;
  
  jQuery.fn.YTPCheckForState = jQuery.mbYTPlayer.checkForState;
  
  jQuery.fn.YTPGetPlayer = jQuery.mbYTPlayer.getPlayer;
  jQuery.fn.YTPGetVideoID = jQuery.mbYTPlayer.getVideoID;
  jQuery.fn.YTPGetPlaylistID = jQuery.mbYTPlayer.getPlaylistID;
  jQuery.fn.YTPChangeVideo = jQuery.fn.YTPChangeMovie = jQuery.mbYTPlayer.changeVideo;
  jQuery.fn.YTPPlayerDestroy = jQuery.mbYTPlayer.playerDestroy;
  
  jQuery.fn.YTPPlay = jQuery.mbYTPlayer.play;
  jQuery.fn.YTPTogglePlay = jQuery.mbYTPlayer.togglePlay;
  jQuery.fn.YTPStop = jQuery.mbYTPlayer.stop;
  jQuery.fn.YTPPause = jQuery.mbYTPlayer.pause;
  jQuery.fn.YTPSeekTo = jQuery.mbYTPlayer.seekTo;
  
  jQuery.fn.YTPlaylist = jQuery.mbYTPlayer.playlist;
  jQuery.fn.YTPPlayNext = jQuery.mbYTPlayer.playNext;
  jQuery.fn.YTPPlayPrev = jQuery.mbYTPlayer.playPrev;
  jQuery.fn.YTPPlayIndex = jQuery.mbYTPlayer.playIndex;
  
  jQuery.fn.YTPMute = jQuery.mbYTPlayer.mute;
  jQuery.fn.YTPUnmute = jQuery.mbYTPlayer.unmute;
  jQuery.fn.YTPToggleVolume = jQuery.mbYTPlayer.toggleVolume;
  jQuery.fn.YTPSetVolume = jQuery.mbYTPlayer.setVolume;
  jQuery.fn.YTPGetVolume = jQuery.mbYTPlayer.getVolume;
  
  jQuery.fn.YTPGetVideoData = jQuery.mbYTPlayer.getVideoData;
  jQuery.fn.YTPFullscreen = jQuery.mbYTPlayer.fullscreen;
  jQuery.fn.YTPToggleLoops = jQuery.mbYTPlayer.toggleLoops;
  jQuery.fn.YTPManageProgress = jQuery.mbYTPlayer.manageProgress;

  jQuery.fn.YTPSetVideoQuality = jQuery.mbYTPlayer.setVideoQuality;
  jQuery.fn.YTPGetVideoQuality = jQuery.mbYTPlayer.getVideoQuality;

  jQuery.fn.YTPApplyFilter = jQuery.mbYTPlayer.applyFilter;
  jQuery.fn.YTPApplyFilters = jQuery.mbYTPlayer.applyFilters;
  jQuery.fn.YTPToggleFilter = jQuery.mbYTPlayer.toggleFilter;
  jQuery.fn.YTPToggleFilters = jQuery.mbYTPlayer.toggleFilters;
  jQuery.fn.YTPRemoveFilter = jQuery.mbYTPlayer.removeFilter;
  jQuery.fn.YTPDisableFilters = jQuery.mbYTPlayer.disableFilters;
  jQuery.fn.YTPEnableFilters = jQuery.mbYTPlayer.enableFilters;
  jQuery.fn.YTPGetFilters = jQuery.mbYTPlayer.getFilters;
  
  jQuery.fn.YTPGetTime = jQuery.mbYTPlayer.getTime;
  jQuery.fn.YTPGetTotalTime = jQuery.mbYTPlayer.getTotalTime;
  
  jQuery.fn.YTPAddMask = jQuery.mbYTPlayer.addMask;
  jQuery.fn.YTPRemoveMask = jQuery.mbYTPlayer.removeMask;
  jQuery.fn.YTPToggleMask = jQuery.mbYTPlayer.toggleMask;
  
  jQuery.fn.YTPGetAbundance = jQuery.mbYTPlayer.getAbundance;
  jQuery.fn.YTPSetAbundance = jQuery.mbYTPlayer.setAbundance;
  
  jQuery.fn.YTPSetAnchor = jQuery.mbYTPlayer.setAnchor;
  jQuery.fn.YTPGetAnchor = jQuery.mbYTPlayer.getAnchor;
  
  jQuery.fn.YTPSetOption = jQuery.mbYTPlayer.setOption;
  
})(jQuery, ytp);
;/*___________________________________________________________________________________________________________________________________________________
 _ jquery.mb.components                                                                                                                             _
 _                                                                                                                                                  _
 _ file: jquery.mb.browser.min.js                                                                                                                   _
 _ last modified: 24/05/17 19.56                                                                                                                    _
 _                                                                                                                                                  _
 _ Open Lab s.r.l., Florence - Italy                                                                                                                _
 _                                                                                                                                                  _
 _ email: matbicoc@gmail.com                                                                                                                       _
 _ site: http://pupunzi.com                                                                                                                         _
 _       http://open-lab.com                                                                                                                        _
 _ blog: http://pupunzi.open-lab.com                                                                                                                _
 _ Q&A:  http://jquery.pupunzi.com                                                                                                                  _
 _                                                                                                                                                  _
 _ Licences: MIT, GPL                                                                                                                               _
 _    http://www.opensource.org/licenses/mit-license.php                                                                                            _
 _    http://www.gnu.org/licenses/gpl.html                                                                                                          _
 _                                                                                                                                                  _
 _ Copyright (c) 2001-2017. Matteo Bicocchi (Pupunzi);                                                                                              _
 ___________________________________________________________________________________________________________________________________________________*/

var nAgt=navigator.userAgent;jQuery.browser=jQuery.browser||{};jQuery.browser.mozilla=!1;jQuery.browser.webkit=!1;jQuery.browser.opera=!1;jQuery.browser.safari=!1;jQuery.browser.chrome=!1;jQuery.browser.androidStock=!1;jQuery.browser.msie=!1;jQuery.browser.edge=!1;jQuery.browser.ua=nAgt;function isTouchSupported(){var a=nAgt.msMaxTouchPoints,e="ontouchstart"in document.createElement("div");return a||e?!0:!1}
var getOS=function(){var a={version:"Unknown version",name:"Unknown OS"};-1!=navigator.appVersion.indexOf("Win")&&(a.name="Windows");-1!=navigator.appVersion.indexOf("Mac")&&0>navigator.appVersion.indexOf("Mobile")&&(a.name="Mac");-1!=navigator.appVersion.indexOf("Linux")&&(a.name="Linux");/Mac OS X/.test(nAgt)&&!/Mobile/.test(nAgt)&&(a.version=/Mac OS X (10[\.\_\d]+)/.exec(nAgt)[1],a.version=a.version.replace(/_/g,".").substring(0,5));/Windows/.test(nAgt)&&(a.version="Unknown.Unknown");/Windows NT 5.1/.test(nAgt)&&
(a.version="5.1");/Windows NT 6.0/.test(nAgt)&&(a.version="6.0");/Windows NT 6.1/.test(nAgt)&&(a.version="6.1");/Windows NT 6.2/.test(nAgt)&&(a.version="6.2");/Windows NT 10.0/.test(nAgt)&&(a.version="10.0");/Linux/.test(nAgt)&&/Linux/.test(nAgt)&&(a.version="Unknown.Unknown");a.name=a.name.toLowerCase();a.major_version="Unknown";a.minor_version="Unknown";"Unknown.Unknown"!=a.version&&(a.major_version=parseFloat(a.version.split(".")[0]),a.minor_version=parseFloat(a.version.split(".")[1]));return a};
jQuery.browser.os=getOS();jQuery.browser.hasTouch=isTouchSupported();jQuery.browser.name=navigator.appName;jQuery.browser.fullVersion=""+parseFloat(navigator.appVersion);jQuery.browser.majorVersion=parseInt(navigator.appVersion,10);var nameOffset,verOffset,ix;
if(-1!=(verOffset=nAgt.indexOf("Opera")))jQuery.browser.opera=!0,jQuery.browser.name="Opera",jQuery.browser.fullVersion=nAgt.substring(verOffset+6),-1!=(verOffset=nAgt.indexOf("Version"))&&(jQuery.browser.fullVersion=nAgt.substring(verOffset+8));else if(-1!=(verOffset=nAgt.indexOf("OPR")))jQuery.browser.opera=!0,jQuery.browser.name="Opera",jQuery.browser.fullVersion=nAgt.substring(verOffset+4);else if(-1!=(verOffset=nAgt.indexOf("MSIE")))jQuery.browser.msie=!0,jQuery.browser.name="Microsoft Internet Explorer",
		jQuery.browser.fullVersion=nAgt.substring(verOffset+5);else if(-1!=nAgt.indexOf("Trident")){jQuery.browser.msie=!0;jQuery.browser.name="Microsoft Internet Explorer";var start=nAgt.indexOf("rv:")+3,end=start+4;jQuery.browser.fullVersion=nAgt.substring(start,end)}else-1!=(verOffset=nAgt.indexOf("Edge"))?(jQuery.browser.edge=!0,jQuery.browser.name="Microsoft Edge",jQuery.browser.fullVersion=nAgt.substring(verOffset+5)):-1!=(verOffset=nAgt.indexOf("Chrome"))?(jQuery.browser.webkit=!0,jQuery.browser.chrome=
		!0,jQuery.browser.name="Chrome",jQuery.browser.fullVersion=nAgt.substring(verOffset+7)):-1<nAgt.indexOf("mozilla/5.0")&&-1<nAgt.indexOf("android ")&&-1<nAgt.indexOf("applewebkit")&&!(-1<nAgt.indexOf("chrome"))?(verOffset=nAgt.indexOf("Chrome"),jQuery.browser.webkit=!0,jQuery.browser.androidStock=!0,jQuery.browser.name="androidStock",jQuery.browser.fullVersion=nAgt.substring(verOffset+7)):-1!=(verOffset=nAgt.indexOf("Safari"))?(jQuery.browser.webkit=!0,jQuery.browser.safari=!0,jQuery.browser.name=
		"Safari",jQuery.browser.fullVersion=nAgt.substring(verOffset+7),-1!=(verOffset=nAgt.indexOf("Version"))&&(jQuery.browser.fullVersion=nAgt.substring(verOffset+8))):-1!=(verOffset=nAgt.indexOf("AppleWebkit"))?(jQuery.browser.webkit=!0,jQuery.browser.safari=!0,jQuery.browser.name="Safari",jQuery.browser.fullVersion=nAgt.substring(verOffset+7),-1!=(verOffset=nAgt.indexOf("Version"))&&(jQuery.browser.fullVersion=nAgt.substring(verOffset+8))):-1!=(verOffset=nAgt.indexOf("Firefox"))?(jQuery.browser.mozilla=
		!0,jQuery.browser.name="Firefox",jQuery.browser.fullVersion=nAgt.substring(verOffset+8)):(nameOffset=nAgt.lastIndexOf(" ")+1)<(verOffset=nAgt.lastIndexOf("/"))&&(jQuery.browser.name=nAgt.substring(nameOffset,verOffset),jQuery.browser.fullVersion=nAgt.substring(verOffset+1),jQuery.browser.name.toLowerCase()==jQuery.browser.name.toUpperCase()&&(jQuery.browser.name=navigator.appName));
-1!=(ix=jQuery.browser.fullVersion.indexOf(";"))&&(jQuery.browser.fullVersion=jQuery.browser.fullVersion.substring(0,ix));-1!=(ix=jQuery.browser.fullVersion.indexOf(" "))&&(jQuery.browser.fullVersion=jQuery.browser.fullVersion.substring(0,ix));jQuery.browser.majorVersion=parseInt(""+jQuery.browser.fullVersion,10);isNaN(jQuery.browser.majorVersion)&&(jQuery.browser.fullVersion=""+parseFloat(navigator.appVersion),jQuery.browser.majorVersion=parseInt(navigator.appVersion,10));
jQuery.browser.version=jQuery.browser.majorVersion;jQuery.browser.android=/Android/i.test(nAgt);jQuery.browser.blackberry=/BlackBerry|BB|PlayBook/i.test(nAgt);jQuery.browser.ios=/iPhone|iPad|iPod|webOS/i.test(nAgt);jQuery.browser.operaMobile=/Opera Mini/i.test(nAgt);jQuery.browser.windowsMobile=/IEMobile|Windows Phone/i.test(nAgt);jQuery.browser.kindle=/Kindle|Silk/i.test(nAgt);
jQuery.browser.mobile=jQuery.browser.android||jQuery.browser.blackberry||jQuery.browser.ios||jQuery.browser.windowsMobile||jQuery.browser.operaMobile||jQuery.browser.kindle;jQuery.isMobile=jQuery.browser.mobile;jQuery.isTablet=jQuery.browser.mobile&&765<jQuery(window).width();jQuery.isAndroidDefault=jQuery.browser.android&&!/chrome/i.test(nAgt);jQuery.mbBrowser=jQuery.browser;
jQuery.browser.versionCompare=function(a,e){if("stringstring"!=typeof a+typeof e)return!1;for(var c=a.split("."),d=e.split("."),b=0,f=Math.max(c.length,d.length);b<f;b++){if(c[b]&&!d[b]&&0<parseInt(c[b])||parseInt(c[b])>parseInt(d[b]))return 1;if(d[b]&&!c[b]&&0<parseInt(d[b])||parseInt(c[b])<parseInt(d[b]))return-1}return 0};
;
/*
 * ******************************************************************************
 *  jquery.mb.components
 *  file: jquery.mb.CSSAnimate.min.js
 *
 *  Copyright (c) 2001-2014. Matteo Bicocchi (Pupunzi);
 *  Open lab srl, Firenze - Italy
 *  email: matbicoc@gmail.com
 *  site: 	http://pupunzi.com
 *  blog:	http://pupunzi.open-lab.com
 * 	http://open-lab.com
 *
 *  Licences: MIT, GPL
 *  http://www.opensource.org/licenses/mit-license.php
 *  http://www.gnu.org/licenses/gpl.html
 *
 *  last modified: 26/03/14 21.40
 *  *****************************************************************************
 */

jQuery.support.CSStransition=function(){var d=(document.body||document.documentElement).style;return void 0!==d.transition||void 0!==d.WebkitTransition||void 0!==d.MozTransition||void 0!==d.MsTransition||void 0!==d.OTransition}();function uncamel(d){return d.replace(/([A-Z])/g,function(a){return"-"+a.toLowerCase()})}function setUnit(d,a){return"string"!==typeof d||d.match(/^[\-0-9\.]+jQuery/)?""+d+a:d}
function setFilter(d,a,b){var c=uncamel(a),g=jQuery.browser.mozilla?"":jQuery.CSS.sfx;d[g+"filter"]=d[g+"filter"]||"";b=setUnit(b>jQuery.CSS.filters[a].max?jQuery.CSS.filters[a].max:b,jQuery.CSS.filters[a].unit);d[g+"filter"]+=c+"("+b+") ";delete d[a]}
jQuery.CSS={name:"mb.CSSAnimate",author:"Matteo Bicocchi",version:"2.0.0",transitionEnd:"transitionEnd",sfx:"",filters:{blur:{min:0,max:100,unit:"px"},brightness:{min:0,max:400,unit:"%"},contrast:{min:0,max:400,unit:"%"},grayscale:{min:0,max:100,unit:"%"},hueRotate:{min:0,max:360,unit:"deg"},invert:{min:0,max:100,unit:"%"},saturate:{min:0,max:400,unit:"%"},sepia:{min:0,max:100,unit:"%"}},normalizeCss:function(d){var a=jQuery.extend(!0,{},d);jQuery.browser.webkit||jQuery.browser.opera?jQuery.CSS.sfx=
		"-webkit-":jQuery.browser.mozilla?jQuery.CSS.sfx="-moz-":jQuery.browser.msie&&(jQuery.CSS.sfx="-ms-");jQuery.CSS.sfx="";for(var b in a){"transform"===b&&(a[jQuery.CSS.sfx+"transform"]=a[b],delete a[b]);"transform-origin"===b&&(a[jQuery.CSS.sfx+"transform-origin"]=d[b],delete a[b]);"filter"!==b||jQuery.browser.mozilla||(a[jQuery.CSS.sfx+"filter"]=d[b],delete a[b]);"blur"===b&&setFilter(a,"blur",d[b]);"brightness"===b&&setFilter(a,"brightness",d[b]);"contrast"===b&&setFilter(a,"contrast",d[b]);"grayscale"===
b&&setFilter(a,"grayscale",d[b]);"hueRotate"===b&&setFilter(a,"hueRotate",d[b]);"invert"===b&&setFilter(a,"invert",d[b]);"saturate"===b&&setFilter(a,"saturate",d[b]);"sepia"===b&&setFilter(a,"sepia",d[b]);if("x"===b){var c=jQuery.CSS.sfx+"transform";a[c]=a[c]||"";a[c]+=" translateX("+setUnit(d[b],"px")+")";delete a[b]}"y"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" translateY("+setUnit(d[b],"px")+")",delete a[b]);"z"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" translateZ("+
		setUnit(d[b],"px")+")",delete a[b]);"rotate"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" rotate("+setUnit(d[b],"deg")+")",delete a[b]);"rotateX"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" rotateX("+setUnit(d[b],"deg")+")",delete a[b]);"rotateY"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" rotateY("+setUnit(d[b],"deg")+")",delete a[b]);"rotateZ"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" rotateZ("+setUnit(d[b],"deg")+")",delete a[b]);"scale"===b&&
(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" scale("+setUnit(d[b],"")+")",delete a[b]);"scaleX"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" scaleX("+setUnit(d[b],"")+")",delete a[b]);"scaleY"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" scaleY("+setUnit(d[b],"")+")",delete a[b]);"scaleZ"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" scaleZ("+setUnit(d[b],"")+")",delete a[b]);"skew"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" skew("+setUnit(d[b],
		"deg")+")",delete a[b]);"skewX"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" skewX("+setUnit(d[b],"deg")+")",delete a[b]);"skewY"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" skewY("+setUnit(d[b],"deg")+")",delete a[b]);"perspective"===b&&(c=jQuery.CSS.sfx+"transform",a[c]=a[c]||"",a[c]+=" perspective("+setUnit(d[b],"px")+")",delete a[b])}return a},getProp:function(d){var a=[],b;for(b in d)0>a.indexOf(b)&&a.push(uncamel(b));return a.join(",")},animate:function(d,a,b,c,g){return this.each(function(){function n(){e.called=
		!0;e.CSSAIsRunning=!1;h.off(jQuery.CSS.transitionEnd+"."+e.id);clearTimeout(e.timeout);h.css(jQuery.CSS.sfx+"transition","");"function"==typeof g&&g.apply(e);"function"==typeof e.CSSqueue&&(e.CSSqueue(),e.CSSqueue=null)}var e=this,h=jQuery(this);e.id=e.id||"CSSA_"+(new Date).getTime();var k=k||{type:"noEvent"};if(e.CSSAIsRunning&&e.eventType==k.type&&!jQuery.browser.msie&&9>=jQuery.browser.version)e.CSSqueue=function(){h.CSSAnimate(d,a,b,c,g)};else if(e.CSSqueue=null,e.eventType=k.type,0!==h.length&&
		d){d=jQuery.normalizeCss(d);e.CSSAIsRunning=!0;"function"==typeof a&&(g=a,a=jQuery.fx.speeds._default);"function"==typeof b&&(c=b,b=0);"string"==typeof b&&(g=b,b=0);"function"==typeof c&&(g=c,c="cubic-bezier(0.65,0.03,0.36,0.72)");if("string"==typeof a)for(var l in jQuery.fx.speeds)if(a==l){a=jQuery.fx.speeds[l];break}else a=jQuery.fx.speeds._default;a||(a=jQuery.fx.speeds._default);"string"===typeof g&&(c=g,g=null);if(jQuery.support.CSStransition){var f={"default":"ease","in":"ease-in",out:"ease-out",
	"in-out":"ease-in-out",snap:"cubic-bezier(0,1,.5,1)",easeOutCubic:"cubic-bezier(.215,.61,.355,1)",easeInOutCubic:"cubic-bezier(.645,.045,.355,1)",easeInCirc:"cubic-bezier(.6,.04,.98,.335)",easeOutCirc:"cubic-bezier(.075,.82,.165,1)",easeInOutCirc:"cubic-bezier(.785,.135,.15,.86)",easeInExpo:"cubic-bezier(.95,.05,.795,.035)",easeOutExpo:"cubic-bezier(.19,1,.22,1)",easeInOutExpo:"cubic-bezier(1,0,0,1)",easeInQuad:"cubic-bezier(.55,.085,.68,.53)",easeOutQuad:"cubic-bezier(.25,.46,.45,.94)",easeInOutQuad:"cubic-bezier(.455,.03,.515,.955)",
	easeInQuart:"cubic-bezier(.895,.03,.685,.22)",easeOutQuart:"cubic-bezier(.165,.84,.44,1)",easeInOutQuart:"cubic-bezier(.77,0,.175,1)",easeInQuint:"cubic-bezier(.755,.05,.855,.06)",easeOutQuint:"cubic-bezier(.23,1,.32,1)",easeInOutQuint:"cubic-bezier(.86,0,.07,1)",easeInSine:"cubic-bezier(.47,0,.745,.715)",easeOutSine:"cubic-bezier(.39,.575,.565,1)",easeInOutSine:"cubic-bezier(.445,.05,.55,.95)",easeInBack:"cubic-bezier(.6,-.28,.735,.045)",easeOutBack:"cubic-bezier(.175, .885,.32,1.275)",easeInOutBack:"cubic-bezier(.68,-.55,.265,1.55)"};
	f[c]&&(c=f[c]);h.off(jQuery.CSS.transitionEnd+"."+e.id);f=jQuery.CSS.getProp(d);var m={};jQuery.extend(m,d);m[jQuery.CSS.sfx+"transition-property"]=f;m[jQuery.CSS.sfx+"transition-duration"]=a+"ms";m[jQuery.CSS.sfx+"transition-delay"]=b+"ms";m[jQuery.CSS.sfx+"transition-timing-function"]=c;setTimeout(function(){h.one(jQuery.CSS.transitionEnd+"."+e.id,n);h.css(m)},1);e.timeout=setTimeout(function(){e.called||!g?(e.called=!1,e.CSSAIsRunning=!1):(h.css(jQuery.CSS.sfx+"transition",""),g.apply(e),e.CSSAIsRunning=
			!1,"function"==typeof e.CSSqueue&&(e.CSSqueue(),e.CSSqueue=null))},a+b+10)}else{for(f in d)"transform"===f&&delete d[f],"filter"===f&&delete d[f],"transform-origin"===f&&delete d[f],"auto"===d[f]&&delete d[f],"x"===f&&(k=d[f],l="left",d[l]=k,delete d[f]),"y"===f&&(k=d[f],l="top",d[l]=k,delete d[f]),"-ms-transform"!==f&&"-ms-filter"!==f||delete d[f];h.delay(b).animate(d,a,g)}}})}};jQuery.fn.CSSAnimate=jQuery.CSS.animate;jQuery.normalizeCss=jQuery.CSS.normalizeCss;
jQuery.fn.css3=function(d){return this.each(function(){var a=jQuery(this),b=jQuery.normalizeCss(d);a.css(b)})};
;/*___________________________________________________________________________________________________________________________________________________
 _ jquery.mb.components                                                                                                                             _
 _                                                                                                                                                  _
 _ file: jquery.mb.simpleSlider.min.js                                                                                                              _
 _ last modified: 09/05/17 19.31                                                                                                                    _
 _                                                                                                                                                  _
 _ Open Lab s.r.l., Florence - Italy                                                                                                                _
 _                                                                                                                                                  _
 _ email: matteo@open-lab.com                                                                                                                       _
 _ site: http://pupunzi.com                                                                                                                         _
 _       http://open-lab.com                                                                                                                        _
 _ blog: http://pupunzi.open-lab.com                                                                                                                _
 _ Q&A:  http://jquery.pupunzi.com                                                                                                                  _
 _                                                                                                                                                  _
 _ Licences: MIT, GPL                                                                                                                               _
 _    http://www.opensource.org/licenses/mit-license.php                                                                                            _
 _    http://www.gnu.org/licenses/gpl.html                                                                                                          _
 _                                                                                                                                                  _
 _ Copyright (c) 2001-2017. Matteo Bicocchi (Pupunzi);                                                                                              _
 ___________________________________________________________________________________________________________________________________________________*/


var nAgt=navigator.userAgent;jQuery.browser=jQuery.browser||{};jQuery.browser.mozilla=!1;jQuery.browser.webkit=!1;jQuery.browser.opera=!1;jQuery.browser.safari=!1;jQuery.browser.chrome=!1;jQuery.browser.androidStock=!1;jQuery.browser.msie=!1;jQuery.browser.edge=!1;jQuery.browser.ua=nAgt;function isTouchSupported(){var a=nAgt.msMaxTouchPoints,e="ontouchstart"in document.createElement("div");return a||e?!0:!1}
var getOS=function(){var a={version:"Unknown version",name:"Unknown OS"};-1!=navigator.appVersion.indexOf("Win")&&(a.name="Windows");-1!=navigator.appVersion.indexOf("Mac")&&0>navigator.appVersion.indexOf("Mobile")&&(a.name="Mac");-1!=navigator.appVersion.indexOf("Linux")&&(a.name="Linux");/Mac OS X/.test(nAgt)&&!/Mobile/.test(nAgt)&&(a.version=/Mac OS X (10[\.\_\d]+)/.exec(nAgt)[1],a.version=a.version.replace(/_/g,".").substring(0,5));/Windows/.test(nAgt)&&(a.version="Unknown.Unknown");/Windows NT 5.1/.test(nAgt)&&
(a.version="5.1");/Windows NT 6.0/.test(nAgt)&&(a.version="6.0");/Windows NT 6.1/.test(nAgt)&&(a.version="6.1");/Windows NT 6.2/.test(nAgt)&&(a.version="6.2");/Windows NT 10.0/.test(nAgt)&&(a.version="10.0");/Linux/.test(nAgt)&&/Linux/.test(nAgt)&&(a.version="Unknown.Unknown");a.name=a.name.toLowerCase();a.major_version="Unknown";a.minor_version="Unknown";"Unknown.Unknown"!=a.version&&(a.major_version=parseFloat(a.version.split(".")[0]),a.minor_version=parseFloat(a.version.split(".")[1]));return a};
jQuery.browser.os=getOS();jQuery.browser.hasTouch=isTouchSupported();jQuery.browser.name=navigator.appName;jQuery.browser.fullVersion=""+parseFloat(navigator.appVersion);jQuery.browser.majorVersion=parseInt(navigator.appVersion,10);var nameOffset,verOffset,ix;
if(-1!=(verOffset=nAgt.indexOf("Opera")))jQuery.browser.opera=!0,jQuery.browser.name="Opera",jQuery.browser.fullVersion=nAgt.substring(verOffset+6),-1!=(verOffset=nAgt.indexOf("Version"))&&(jQuery.browser.fullVersion=nAgt.substring(verOffset+8));else if(-1!=(verOffset=nAgt.indexOf("OPR")))jQuery.browser.opera=!0,jQuery.browser.name="Opera",jQuery.browser.fullVersion=nAgt.substring(verOffset+4);else if(-1!=(verOffset=nAgt.indexOf("MSIE")))jQuery.browser.msie=!0,jQuery.browser.name="Microsoft Internet Explorer",
		jQuery.browser.fullVersion=nAgt.substring(verOffset+5);else if(-1!=nAgt.indexOf("Trident")){jQuery.browser.msie=!0;jQuery.browser.name="Microsoft Internet Explorer";var start=nAgt.indexOf("rv:")+3,end=start+4;jQuery.browser.fullVersion=nAgt.substring(start,end)}else-1!=(verOffset=nAgt.indexOf("Edge"))?(jQuery.browser.edge=!0,jQuery.browser.name="Microsoft Edge",jQuery.browser.fullVersion=nAgt.substring(verOffset+5)):-1!=(verOffset=nAgt.indexOf("Chrome"))?(jQuery.browser.webkit=!0,jQuery.browser.chrome=
		!0,jQuery.browser.name="Chrome",jQuery.browser.fullVersion=nAgt.substring(verOffset+7)):-1<nAgt.indexOf("mozilla/5.0")&&-1<nAgt.indexOf("android ")&&-1<nAgt.indexOf("applewebkit")&&!(-1<nAgt.indexOf("chrome"))?(verOffset=nAgt.indexOf("Chrome"),jQuery.browser.webkit=!0,jQuery.browser.androidStock=!0,jQuery.browser.name="androidStock",jQuery.browser.fullVersion=nAgt.substring(verOffset+7)):-1!=(verOffset=nAgt.indexOf("Safari"))?(jQuery.browser.webkit=!0,jQuery.browser.safari=!0,jQuery.browser.name=
		"Safari",jQuery.browser.fullVersion=nAgt.substring(verOffset+7),-1!=(verOffset=nAgt.indexOf("Version"))&&(jQuery.browser.fullVersion=nAgt.substring(verOffset+8))):-1!=(verOffset=nAgt.indexOf("AppleWebkit"))?(jQuery.browser.webkit=!0,jQuery.browser.safari=!0,jQuery.browser.name="Safari",jQuery.browser.fullVersion=nAgt.substring(verOffset+7),-1!=(verOffset=nAgt.indexOf("Version"))&&(jQuery.browser.fullVersion=nAgt.substring(verOffset+8))):-1!=(verOffset=nAgt.indexOf("Firefox"))?(jQuery.browser.mozilla=
		!0,jQuery.browser.name="Firefox",jQuery.browser.fullVersion=nAgt.substring(verOffset+8)):(nameOffset=nAgt.lastIndexOf(" ")+1)<(verOffset=nAgt.lastIndexOf("/"))&&(jQuery.browser.name=nAgt.substring(nameOffset,verOffset),jQuery.browser.fullVersion=nAgt.substring(verOffset+1),jQuery.browser.name.toLowerCase()==jQuery.browser.name.toUpperCase()&&(jQuery.browser.name=navigator.appName));
-1!=(ix=jQuery.browser.fullVersion.indexOf(";"))&&(jQuery.browser.fullVersion=jQuery.browser.fullVersion.substring(0,ix));-1!=(ix=jQuery.browser.fullVersion.indexOf(" "))&&(jQuery.browser.fullVersion=jQuery.browser.fullVersion.substring(0,ix));jQuery.browser.majorVersion=parseInt(""+jQuery.browser.fullVersion,10);isNaN(jQuery.browser.majorVersion)&&(jQuery.browser.fullVersion=""+parseFloat(navigator.appVersion),jQuery.browser.majorVersion=parseInt(navigator.appVersion,10));
jQuery.browser.version=jQuery.browser.majorVersion;jQuery.browser.android=/Android/i.test(nAgt);jQuery.browser.blackberry=/BlackBerry|BB|PlayBook/i.test(nAgt);jQuery.browser.ios=/iPhone|iPad|iPod|webOS/i.test(nAgt);jQuery.browser.operaMobile=/Opera Mini/i.test(nAgt);jQuery.browser.windowsMobile=/IEMobile|Windows Phone/i.test(nAgt);jQuery.browser.kindle=/Kindle|Silk/i.test(nAgt);
jQuery.browser.mobile=jQuery.browser.android||jQuery.browser.blackberry||jQuery.browser.ios||jQuery.browser.windowsMobile||jQuery.browser.operaMobile||jQuery.browser.kindle;jQuery.isMobile=jQuery.browser.mobile;jQuery.isTablet=jQuery.browser.mobile&&765<jQuery(window).width();jQuery.isAndroidDefault=jQuery.browser.android&&!/chrome/i.test(nAgt);jQuery.mbBrowser=jQuery.browser;
jQuery.browser.versionCompare=function(a,e){if("stringstring"!=typeof a+typeof e)return!1;for(var c=a.split("."),d=e.split("."),b=0,f=Math.max(c.length,d.length);b<f;b++){if(c[b]&&!d[b]&&0<parseInt(c[b])||parseInt(c[b])>parseInt(d[b]))return 1;if(d[b]&&!c[b]&&0<parseInt(d[b])||parseInt(c[b])<parseInt(d[b]))return-1}return 0};

(function(b){b.simpleSlider={defaults:{initialval:0,scale:100,orientation:"h",readonly:!1,callback:!1},events:{start:b.browser.mobile?"touchstart":"mousedown",end:b.browser.mobile?"touchend":"mouseup",move:b.browser.mobile?"touchmove":"mousemove"},init:function(c){return this.each(function(){var a=this,d=b(a);d.addClass("simpleSlider");a.opt={};b.extend(a.opt,b.simpleSlider.defaults,c);b.extend(a.opt,d.data());var e="h"==a.opt.orientation?"horizontal":"vertical";e=b("<div/>").addClass("level").addClass(e);
	d.prepend(e);a.level=e;d.css({cursor:"default"});"auto"==a.opt.scale&&(a.opt.scale=b(a).outerWidth());d.updateSliderVal();a.opt.readonly||(d.on(b.simpleSlider.events.start,function(c){b.browser.mobile&&(c=c.changedTouches[0]);a.canSlide=!0;d.updateSliderVal(c);"h"==a.opt.orientation?d.css({cursor:"col-resize"}):d.css({cursor:"row-resize"});b.browser.mobile||(c.preventDefault(),c.stopPropagation())}),b(document).on(b.simpleSlider.events.move,function(c){b.browser.mobile&&(c=c.changedTouches[0]);a.canSlide&&
	(b(document).css({cursor:"default"}),d.updateSliderVal(c),b.browser.mobile||(c.preventDefault(),c.stopPropagation()))}).on(b.simpleSlider.events.end,function(){b(document).css({cursor:"auto"});a.canSlide=!1;d.css({cursor:"auto"})}))})},updateSliderVal:function(c){var a=this.get(0);if(a.opt){a.opt.initialval="number"==typeof a.opt.initialval?a.opt.initialval:a.opt.initialval(a);var d=b(a).outerWidth(),e=b(a).outerHeight();a.x="object"==typeof c?c.clientX+document.body.scrollLeft-this.offset().left:
				"number"==typeof c?c*d/a.opt.scale:a.opt.initialval*d/a.opt.scale;a.y="object"==typeof c?c.clientY+document.body.scrollTop-this.offset().top:"number"==typeof c?(a.opt.scale-a.opt.initialval-c)*e/a.opt.scale:a.opt.initialval*e/a.opt.scale;a.y=this.outerHeight()-a.y;a.scaleX=a.x*a.opt.scale/d;a.scaleY=a.y*a.opt.scale/e;a.outOfRangeX=a.scaleX>a.opt.scale?a.scaleX-a.opt.scale:0>a.scaleX?a.scaleX:0;a.outOfRangeY=a.scaleY>a.opt.scale?a.scaleY-a.opt.scale:0>a.scaleY?a.scaleY:0;a.outOfRange="h"==a.opt.orientation?
		a.outOfRangeX:a.outOfRangeY;a.value="undefined"!=typeof c?"h"==a.opt.orientation?a.x>=this.outerWidth()?a.opt.scale:0>=a.x?0:a.scaleX:a.y>=this.outerHeight()?a.opt.scale:0>=a.y?0:a.scaleY:"h"==a.opt.orientation?a.scaleX:a.scaleY;"h"==a.opt.orientation?a.level.width(Math.floor(100*a.x/d)+"%"):a.level.height(Math.floor(100*a.y/e));"function"==typeof a.opt.callback&&a.opt.callback(a)}}};b.fn.simpleSlider=b.simpleSlider.init;b.fn.updateSliderVal=b.simpleSlider.updateSliderVal})(jQuery);
;/*___________________________________________________________________________________________________________________________________________________
 _ jquery.mb.components                                                                                                                             _
 _                                                                                                                                                  _
 _ file: jquery.mb.storage.min.js                                                                                                                   _
 _ last modified: 24/05/15 16.08                                                                                                                    _
 _                                                                                                                                                  _
 _ Open Lab s.r.l., Florence - Italy                                                                                                                _
 _                                                                                                                                                  _
 _ email: matteo@open-lab.com                                                                                                                       _
 _ site: http://pupunzi.com                                                                                                                         _
 _       http://open-lab.com                                                                                                                        _
 _ blog: http://pupunzi.open-lab.com                                                                                                                _
 _ Q&A:  http://jquery.pupunzi.com                                                                                                                  _
 _                                                                                                                                                  _
 _ Licences: MIT, GPL                                                                                                                               _
 _    http://www.opensource.org/licenses/mit-license.php                                                                                            _
 _    http://www.gnu.org/licenses/gpl.html                                                                                                          _
 _                                                                                                                                                  _
 _ Copyright (c) 2001-2015. Matteo Bicocchi (Pupunzi);                                                                                              _
 ___________________________________________________________________________________________________________________________________________________*/

(function(d){d.mbCookie={set:function(a,c,f,b){"object"==typeof c&&(c=JSON.stringify(c));b=b?"; domain="+b:"";var e=new Date,d="";0<f&&(e.setTime(e.getTime()+864E5*f),d="; expires="+e.toGMTString());document.cookie=a+"="+c+d+"; path=/"+b},get:function(a){a+="=";for(var c=document.cookie.split(";"),d=0;d<c.length;d++){for(var b=c[d];" "==b.charAt(0);)b=b.substring(1,b.length);if(0==b.indexOf(a))try{return JSON.parse(b.substring(a.length,b.length))}catch(e){return b.substring(a.length,b.length)}}return null},
	remove:function(a){d.mbCookie.set(a,"",-1)}};d.mbStorage={set:function(a,c){"object"==typeof c&&(c=JSON.stringify(c));localStorage.setItem(a,c)},get:function(a){if(localStorage[a])try{return JSON.parse(localStorage[a])}catch(c){return localStorage[a]}else return null},remove:function(a){a?localStorage.removeItem(a):localStorage.clear()}}})(jQuery);
