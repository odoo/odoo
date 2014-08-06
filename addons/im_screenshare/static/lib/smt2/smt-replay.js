/*! 
 * (smt)2 simple mouse tracking v2.1.0
 * Copyleft (cc) 2006-2012 Luis Leiva
 * http://smt2.googlecode.com & http://smt.speedzinemedia.com
 */
/** 
 * (smt)2 simple mouse tracking - replay script (smt-replay.js)
 * Copyleft (cc) 2006-2012 Luis Leiva
 * Release date: March 23 2012
 * http://smt2.googlecode.com & http://smt.speedzinemedia.com
 * @class smt2-replay
 * @requires smt2-aux Auxiliary (smt)2 functions  
 * @version 2.1.0
 * @author Luis Leiva 
 * @license Dual licensed under the MIT (MIT-LICENSE.txt) and GPL (GPL-LICENSE.txt) licenses. 
 * @see smt2fn
 * @deprecated in favor of the new SWF visualization API 
 */
(function(){
  /** 
   * (smt)2 default replaying options.
   * This Object should be overriden from the 'customize' section at the (smt)2 CMS.
   */ 
  var smtOpt = {
    /** 
     * Entry point color
     * @type string 
     */  
    entryPt:  "#9F6",   
    /** 
     * Exit point color
     * @type string     
     */
    exitPt:   "#F66",   
    /** 
     * Registration points color
     * @type string      
     */
    regPt:    "#F0F",   
    /** 
     * Lines color
     * @type string      
     */ 
    regLn:    "#0CC",   
    /** 
     * Clicks color
     * @type string      
     */
    click:    "#F00",   
    /** 
     * Drag and drop color
     * @type string      
     */
    dDrop:    "#ABC",   
    /** 
     * User stops: time-depending circles color
     * @type string      
     */
    varCir:   "#F99",   
    /** 
     * Centroid color
     * @type string      
     */
    cenPt:    "#DDD",   
    /** 
     * Clusters color
     * @type string      
     */
    clust:    "#00F",
    /**
     * Background layer color
     * @type string
     */
    bgColor: "#555",
    /** 
     * Draw background layer (true) or not (false)
     * @type boolean      
     */
    bgLayer:  true,
    /**
     * Static (false) or dynamic mouse replay (true)
     * @type boolean
     */
    realTime: true,
    /** 
     * Show direction vector (useful if realTime: false)
     * @type boolean      
     */
    dirVect:  false,
    /** 
     * Main layout content diagramation; a.k.a 'how page content flows'. 
     * Values: "left" (fixed), "center" (fixed and centered), or "liquid" (adaptable, default behavior).
     * In "left" and "center" layouts the content is not adapted on resizing the browser.
     * An example of left diagramation is http://smt.speedzinemedia.com
     * @type string
     */
    layoutType: "liquid"    
  };
  
  
  /* do not edit below this line -------------------------------------------- */
  
  // get libraries/globals
  var smtData     = window.smt2data;
  var jsGraphics  = window.jsGraphics;
  var aux         = window.smt2fn;
  // check
  if (typeof smtData === 'undefined')     { throw("user data is malformed or not set");  }
  if (typeof jsGraphics === 'undefined')  { throw("jsGraphics library not found");       } 
  if (typeof aux === 'undefined')         { throw("auxiliar (smt) functions not found"); }
  if (typeof JSON.parse !== 'function')   { throw("JSON parser not found");              }
  
  // when using the JS api, draw only the average path
  var user;
  var users = JSON.parse(unescape(smtData.users));
  var numUsers = users.length;
  if (numUsers > 1) {
    for (var i = 0; i < numUsers; ++i) {
      if (users[i].avg) {
        user = users[i];
        break;
      }
    }
  } else {
    user = users[0];
  }
  
  // remove null distances to compute the mouse path centroid
  var xclean = [];
  var yclean = [];
  
  /** 
   * (smt)2 replaying object.
   * This Object is private. Methods are cited but not documented.
   */
  var smtRep = {
    i:            0,                        // mouse tracking global counter var
    j:            1,                        // registration points size global counter var
    jMax:         0,                        // registration points size limit
    play:         null,                     // mouse tracking identifier
    jg:           null,                     // canvas area for drawing
    jgClust:      null,                     // layer for clustering
    jgHelper:     null,                     // layer for displaying text info
    page:         { width:0, height:0 },    // data normalization
    viewport:     { width:0, height:0 },    // center scrolling
    discrepance:  { x:1, y:1 },             // discrepance ratios
    paused:       false,                    // pause the visualization
    /** 
     * Create drawing canvas layer.
     */
    createCanvas: function(layerName) 
    {
      // canvas layer for mouse trackig
      var jg = document.createElement("div");
          jg.id             = layerName;
          jg.style.position = "absolute";
          jg.style.top      = 0;
          jg.style.left     = 0;
          jg.style.width    = 100 + '%';
          jg.style.height   = 100 + '%';
          jg.style.zIndex   = aux.getNextHighestDepth() + 1;
      
      // helper layer for text
      var jgHelp = document.createElement("div");
          jgHelp.id              = layerName + "Help";
          jgHelp.style.zIndex    = jg.style.zIndex + 1;
          
      // layer for clustering
      var opacity = 40;
      var jgClust = document.createElement("div");
          jgClust.id              = layerName + "Clust";
          jgClust.style.position  = "absolute";
          jgClust.style.top       = 0;
          jgClust.style.left      = 0;
          jgClust.style.width     = 100 + '%';
          jgClust.style.height    = 100 + '%';
          jgClust.style.opacity   = opacity/100; // for W3C browsers
          jgClust.style.filter    = "alpha(opacity="+opacity+")"; // only for IE
          jgClust.style.zIndex    = jg.style.zIndex + 2;
          
      var body  = document.getElementsByTagName("body")[0];
          body.appendChild(jg);
          body.appendChild(jgHelp);
          body.appendChild(jgClust);
          
      // set the canvas areas for drawing both mouse tracking and clustering
      smtRep.jg = new jsGraphics(jg.id);
      smtRep.jgHelper = new jsGraphics(jgHelp.id);
      smtRep.jgClust = new jsGraphics(jgClust.id);
    },
    /** 
     * Create background layer.
     */
    setBgCanvas: function(layerName) 
    {
      var opacity = 80, // background layer opacity (%)
          // set layer above the mouse tracking one
          jg = document.getElementById(layerName);

      var bg = document.createElement("div");
          bg.id                     = layerName + "Bg";
          bg.style.position         = "absolute";
          bg.style.top              = 0;
          bg.style.left             = 0;
          bg.style.width            = smtRep.page.width + 'px';
          bg.style.height           = smtRep.page.height + 'px';
          bg.style.overflow         = "hidden";
          bg.style.backgroundColor  = smtOpt.bgColor;
          bg.style.opacity          = opacity/100; // for W3C browsers
          bg.style.filter           = "alpha(opacity="+opacity+")"; // only for IE
          bg.style.zIndex           = jg.style.zIndex - 1;
          
      var body  = document.getElementsByTagName("body")[0];
          body.appendChild(bg);
    },
    /** 
     * Draw line.
     */
    drawLine: function(ini,end) 
    {
        smtRep.jg.setColor(smtOpt.regLn);
        smtRep.jg.drawLine(ini.x,ini.y, end.x,end.y);
        smtRep.jg.paint();
    },
    /** 
     * Draw mouse click.
     */
    drawClick: function(x,y, isDragAndDrop) 
    {
      var size;
      if (!isDragAndDrop) {
        size = 10;
        smtRep.jg.setColor(smtOpt.click);
        smtRep.jg.setStroke(5);
        smtRep.jg.drawLine(x-size,y-size, x,y);
        smtRep.jg.drawLine(x-size,y+size, x,y);
        smtRep.jg.drawLine(x+size,y-size, x,y);
        smtRep.jg.drawLine(x+size,y+size, x,y);
        /*
        var offset = 3;
        smtRep.jg.drawLine(x-size,y-size, x-offset,y-offset);
        smtRep.jg.drawLine(x-size,y+size, x-offset,y+offset);
        smtRep.jg.drawLine(x+size,y-size, x+offset,y-offset);
        smtRep.jg.drawLine(x+size,y+size, x+offset,y+offset);
        */
        smtRep.jg.setStroke(0);
      } else {
        size = 6;
        smtRep.jg.setColor(smtOpt.dDrop);
        smtRep.jg.drawRect(x-size/2,y-size/2, size,size);
      }
      smtRep.jg.paint();
    },
    /** 
     * Draw direction arrow in a line.
     */
    drawDirectionArrow: function(ini,end)
    {
      var a = ini.x - end.x,
          b = ini.y - end.y,
          s = 4;
      if (a>0 && b>0) {
        smtRep.jg.drawPolyline([end.x-s,end.x,end.x+s], [end.y+s,end.y,end.y+s]);
      } else if (a<0 && b>0) {
        smtRep.jg.drawPolyline([end.x-s,end.x,end.x-s], [end.y-s,end.y,end.y+s]);
      } else if (a<0 && b<0) {
        smtRep.jg.drawPolyline([end.x-s,end.x,end.x+s], [end.y-s,end.y,end.y-s]);
      } else if (a>0 && b<0) {
        smtRep.jg.drawPolyline([end.x+s,end.x,end.x+s], [end.y-s,end.y,end.y+s]);
      }
      smtRep.jg.paint();
    },
    /** 
     * Draw mouse cursor.
     */
    drawCursor: function(x,y, color) 
    {
      smtRep.jg.setColor(color);
      smtRep.jg.fillPolygon([x,x,   x+4, x+6, x+9, x+7, x+15], 
                            [y,y+15,y+15,y+23,y+23,y+15,y+15]);
      smtRep.jg.paint();
    },
    /** 
     * Draw registration point.
     */
    drawRegistrationPoint: function(x,y) 
    {
      smtRep.jg.setColor(smtOpt.regPt);
      smtRep.jg.fillRect(x-1, y-1, 3, 3);
      smtRep.jg.paint();
    },
    /** 
     * Draw time-depending circle.
     */
    drawVariableCircle: function(x,y, size) 
    {
      // use multiplier to normalize all circles: 0 < norm < 1
      var norm = aux.roundTo(size/smtRep.jMax); 
      if (size * norm === 0 ) { return; }
      // limit size to 1/2 of current window width (px)
      if (size > smtData.wcurr/2) { size = Math.round(smtData.wcurr/2 * norm); }
      // draw
      smtRep.jg.setColor(smtOpt.varCir);
      smtRep.jg.drawEllipse(x - size/2, y - size/2, size, size);
      smtRep.jg.paint();
    },
    /** 
     * Gives a visual clue when the user is not using the mouse.
     */
    drawMouseStop: function(x,y) 
    {
      if (!smtOpt.realTime) { return; }
      
      var fontSize   = 16,
          circleSize = 50;
      smtRep.jgHelper.setColor(smtOpt.varCir);
      smtRep.jgHelper.fillEllipse(x - circleSize/2, y - circleSize/2, circleSize, circleSize);
      smtRep.jgHelper.setColor("black");
      smtRep.jgHelper.setFont("sans-serif", fontSize+'px', Font.BOLD);
      // center the text in vertical 
      smtRep.jgHelper.drawString("stopped...", x, y - fontSize/2);
      smtRep.jgHelper.paint();
    },   
    /** 
     * Draw centroid as a star.
     */
    drawCentroid: function()
    {
      smtRep.jg.setColor(smtOpt.cenPt);
      var xsum = aux.array.sum(xclean) / xclean.length;
      var ysum = aux.array.sum(yclean) / yclean.length;
      // the centroid is computed discarding null distances
      if (smtOpt.layoutType == "liquid") {
        xsum *= smtRep.discrepance.x;
        xsum *= smtRep.discrepance.x;
      } else if (smtOpt.layoutType == "center") {
        xsum += smtRep.discrepance.x;
        xsum += smtRep.discrepance.x;
      }
            
      var u = Math.round(xsum),
          v = Math.round(ysum),
          l = 20; // centroid line length
      smtRep.jg.setStroke(5);
      smtRep.jg.drawLine(u, v, u+l, v-l); // 1st quadrant
      smtRep.jg.drawLine(u, v, u-l, v-l); // 2nd quadrant
    	smtRep.jg.drawLine(u, v, u-l, v+l); // 3rd quadrant
    	smtRep.jg.drawLine(u, v, u+l, v+l); // 4th quadrant
    	smtRep.jg.setStroke(0); // reset strokes
    	smtRep.jg.paint();
    },
    /** 
     * Draw cluster as a circle.
     */
    drawClusters: function(response) 
    {
      var K = JSON.parse(response);
      // again (same as in Flash) typeof K is string, so re-parse
      if (typeof K !== 'object') {
        K = JSON.parse(K);
      }
      smtRep.jgClust.setColor(smtOpt.clust);
      for (var i = 0, size = 0, numClusters = K.sizes.length; i < numClusters; ++i) {
        size = K.sizes[i];
        smtRep.jgClust.fillEllipse(K.xclusters[i] * smtRep.discrepance.x - size/2, K.yclusters[i] * smtRep.discrepance.y - size/2, size, size);
      }
      smtRep.jgClust.paint();
    },
    /** 
     * Get euclidean distance from point a to point b.
     */
    distance: function(a,b) 
    {
      return Math.sqrt( Math.pow(a.x - b.x,2) + Math.pow(a.y - b.y,2) );
    },
    /** 
     * Auto scrolls the browser window.
     */
    checkAutoScrolling: function(x,y) 
    {
      if (!smtOpt.realTime) { return; }
      // center current mouse coords on the viewport
      aux.doScroll({xpos:x, ypos:y, width:smtRep.viewport.width, height:smtRep.viewport.height});
    },
    /** 
     * (smt)2 realtime drawing algorithm.
     */
    playMouse: function() 
    {
      if (smtRep.paused) { return; }

      // mouse coords normalization
      var iniMouse = { 
                        x: user.xcoords[smtRep.i] * smtRep.discrepance.x,
                        y: user.ycoords[smtRep.i] * smtRep.discrepance.y 
                     };
      var endMouse = { 
                        x: user.xcoords[smtRep.i+1] * smtRep.discrepance.x,
                        y: user.ycoords[smtRep.i+1] * smtRep.discrepance.y 
                     };

      var currClickType = user.clicks[smtRep.i];
      var nextClickType = user.clicks[smtRep.i+1];
      var currClickX = currClickType > 0 ? user.xcoords[smtRep.i]   : 0;
      var nextClickX = nextClickType > 0 ? user.xcoords[smtRep.i+1] : 0;
      var currClickY = currClickType > 0 ? user.ycoords[smtRep.i]   : 0;
      var nextClickY = nextClickType > 0 ? user.ycoords[smtRep.i+1] : 0;

      var iniClick = {
                        x: currClickX * smtRep.discrepance.x, 
                        y: currClickY * smtRep.discrepance.y
                     };
      var endClick = {
                        x: nextClickX * smtRep.discrepance.x, 
                        y: nextClickY * smtRep.discrepance.y
                     };
      
      // draw entry point
      if (smtRep.i === 0) {
        smtRep.drawCursor(iniMouse.x,iniMouse.y, smtOpt.entryPt);
      }
      
      // main loop to draw mouse trail
      if (smtRep.i < user.xcoords.length) 
      {
        var mouseDistance = smtRep.distance(iniMouse,endMouse);
        // draw registration points
        if (mouseDistance) {
          // there is mouse movement
          if (!smtOpt.dirVect) {
            // show static squares
            smtRep.drawRegistrationPoint(iniMouse.x,iniMouse.y);
          } else {
            // show direction pseudo-arrows
            smtRep.drawDirectionArrow(iniMouse,endMouse);
          }
          // variable circles
          if (smtRep.j > 1) {
            smtRep.drawVariableCircle(iniMouse.x, iniMouse.y, smtRep.j);
            smtRep.jgHelper.clear();
          }
          // reset variable circles size
          smtRep.j = 1;
        } else {
          // mouse stop: store variable size (circles)
          ++smtRep.j;
          smtRep.drawMouseStop(iniMouse.x, iniMouse.y);
        }
        // draw lines
        smtRep.drawLine(iniMouse,endMouse);
        // draw clicks
        if (iniClick.x) {
          var clickDistance = smtRep.distance(iniClick,endClick);
          if (!clickDistance) {
            // is a single click
            smtRep.drawClick(endClick.x,endClick.y, false);
          } else if (endClick.x !== 0) {
            // is drag and drop
            smtRep.drawClick(iniClick.x,iniClick.y, true);
          }
        }
        // update mouse coordinates
        ++smtRep.i;
        // check auto scrolling
        smtRep.checkAutoScrolling(endMouse.x, endMouse.y);
    	}
      
      // draw exit point
      else {
    	  // rewind count 1 step to access the last mouse coordinate
    	  --smtRep.i;
    	  iniMouse.x = user.xcoords[smtRep.i] * smtRep.discrepance.x;
        iniMouse.y = user.ycoords[smtRep.i] * smtRep.discrepance.y;
        // draw exit point
    	  smtRep.drawCursor(iniMouse.x,iniMouse.y, smtOpt.exitPt);
    	  // draw clusters
    	  var data  = "xhr=1"; 
            data += "&xdata=" + JSON.stringify(user.xcoords);
            data += "&ydata=" + JSON.stringify(user.ycoords);
        
        var basepath = aux.getBaseURL();
        // send request
        aux.sendAjaxRequest({
          url:       basepath + "includes/kmeans.php", 
          postdata:  data,
          callback:  smtRep.drawClusters
        });
        
        // draw centroid (average mouse position) 
        smtRep.drawCentroid();
        // clear mouse tracking
        clearInterval(smtRep.play);
        smtRep.play = null;
        smtRep.jgHelper.clear();
        if (numUsers == 1) {
          // load next trail
          aux.loadNextMouseTrail(smtData);
        }
    	}
    },
    /** 
     * Replay method: static or dynamic.
     */
    replay: function(realtime) 
    {
      if (realtime) {
        // fps are stored in smtData object, so we can use that value here
        var interval = Math.round(1000/smtData.fps);
        smtRep.play = setInterval(smtRep.playMouse, interval);
      } else {
        // static mouse tracking visualization 
        for (var k = 0, total = user.xcoords.length; k <= total; ++k) {
          smtRep.playMouse();
        }
      }
    },
    /** 
     * Reload method: mouse tracking layers are redrawn.
     */
    reset: function() 
    {
      clearInterval(smtRep.play);
      smtRep.paused = false;
      // reset counters
      smtRep.i = 0;
      smtRep.j = 1;    
      // clear canvas  
      smtRep.jg.clear();
      smtRep.jgClust.clear();
    },
    /** 
     * User can pause the mouse replay by pressing the SPACE key, 
     * or toggle replay mode by pressing the ESC key.
     */
    helpKeys: function(e) 
    {
      // use helpKeys only in realtime replaying
      if (!smtOpt.realTime) { return; }
      
      if (!e) { e = window.event; }
      var code = e.keyCode || e.which;
      // on press ESC key finish drawing
      if (code == 27) {
        // clear main loop
        clearInterval(smtRep.play);
        smtRep.paused = false;
        // set this flag
        smtOpt.realTime = false;
        // end drawing from the current position
        for (var k = smtRep.i, total = user.xcoords.length; k <= total; ++k) {
          smtRep.playMouse();
        }
      } else if (code == 32) {
        // on press space bar toggle drawing
        smtRep.paused = !smtRep.paused;
      }
    },
    /** 
     * System initialization.
     */
    init: function() 
    {
      // use vieport size to auto-scroll window
      var vp = aux.getWindowSize();
      smtRep.viewport.width = vp.width;
      smtRep.viewport.height = vp.height;
      // normalize data
      var doc = aux.getPageSize();
      smtRep.page.width = doc.width;
      smtRep.page.height = doc.height;
      // compute the discrepance ratio
      if (user.wprev && user.hprev) {
        smtRep.discrepance.x = aux.roundTo(doc.width / user.wprev);
        smtRep.discrepance.y = aux.roundTo(doc.height / user.hprev);
      }
          
      // precalculate the user stops: useful for time-depending circles and path centroid
      var stops = [];      
      var size = 1;
      for (var k = 0, len = user.xcoords.length; k < len; ++k) {
        if (user.xcoords[k] == user.xcoords[k+1] && user.ycoords[k] == user.ycoords[k+1]) {
          ++size;
        } else {
          // store all user stops (time) for drawing variable circles later
          if (size > 1) { stops.push(size); }
          size = 1;
          // store clean mouse coordinates
          xclean.push(user.xcoords[k]);
          yclean.push(user.ycoords[k]);
        }
      }
      // set max size for variable circles
      smtRep.jMax = aux.array.max(stops);       
      // common suffix for tracking canvas and background layers
      var smtName = "smtCanvas";
      // set the canvas layer
      smtRep.createCanvas(smtName);
      // draw the background layer
      if (smtOpt.bgLayer) { smtRep.setBgCanvas(smtName); }
      // init
      smtRep.replay(smtOpt.realTime);
    }
    
  };
  
  // do not overwrite the smt2 namespace
  if (typeof window.smt2 !== 'undefined') { throw("smt2 namespace conflict"); }
  // else expose replay method
  window.smt2 = {
    replay: function(opts) {
      // load custom smtOpt, if set
      if (typeof opts !== "undefined") { aux.overrideTrackingOptions(smtOpt, opts); }
      // replay
      aux.addEvent(document, "keyup",  smtRep.helpKeys);
      //aux.addEvent(window, "resize", smtRep.reset);
      //aux.addEvent(window, "resize", aux.reloadPage);
      aux.onDOMload(function(){
        // replay mouse track over Flash objects 
        aux.allowTrackingOnFlashObjects(document);
      });
      aux.addEvent(window, "load", smtRep.init);
      //aux.onDOMload(smtRep.init);
    }
  }
  
})();
