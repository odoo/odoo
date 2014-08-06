(function(global) {

    var CursorMirror = function() {

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

        var viewport = smt2fn.getWindowSize();
        var page = smt2fn.getPageSize();
        var discrepanceRatio = {
                x: 1,
                y: 1,
        };
        var mouseCanvas = null;
        var play = null;
        var fps = 24;

        // Compute discrepance ratio ???

        // precalculate the user stops: useful for the time-depending circles and path centroid ???

        var createCanvas = function(layerName) {
            var jg = document.createElement("div");
            jg.id             = layerName;
            jg.style.position = "absolute";
            jg.style.top      = 0;
            jg.style.left     = 0;
            jg.style.width    = 100 + '%';
            jg.style.height   = 100 + '%';
            jg.style.zIndex   = smt2fn.getNextHighestDepth() + 1;

            document.body.appendChild(jg);

            mouseCanvas = new jsGraphics(jg.id);
        };
        createCanvas("mouseCanvas");

        var counter = 0;
        var playMouse = function (coords) {
            // console.log(coords);
            // mouse coords normalization
            var iniMouse = { 
                    x: coords.x[counter] * discrepanceRatio.x,
                    y: coords.y[counter] * discrepanceRatio.y
            };
            var endMouse = { 
                    x: coords.x[counter+1] * discrepanceRatio.x,
                    y: coords.y[counter+1] * discrepanceRatio.y
            };
            if (counter < coords.x.length) {
                counter++;
                // console.log(JSON.stringify(iniMouse)+","+JSON.stringify(endMouse));
                mouseCanvas.clear();
                mouseCanvas.fillPolygon([iniMouse.x, iniMouse.x, iniMouse.x+4, iniMouse.x+6, iniMouse.x+9, iniMouse.x+7, iniMouse.x+15], 
                            [iniMouse.y, iniMouse.y+15, iniMouse.y+15, iniMouse.y+23, iniMouse.y+23, iniMouse.y+15, iniMouse.y+15]);
                mouseCanvas.paint();
            } else {                
                clearInterval(play);
                counter = 0;
            }
        };

        var replay = function(coords) {
            var interval = Math.round(1000/fps);
            play = window.setInterval(playMouse(coords), interval);
        };

        return { 
            forwardData: function(prevPage, coords, elem) {
                // console.log(JSON.stringify(page) + "\n" + JSON.stringify(coords)/* + "\n" + JSON.stringify(elem)*/);
                discrepanceRatio.x = smt2fn.roundTo(page.width / prevPage.width);
                discrepanceRatio.y = smt2fn.roundTo(page.height / prevPage.height);
                replay(coords);
            }
        };
    };

    var CursorMirrorClient = function(mirror) {

        var mirror = mirror;
        var mouse = {
                x: 0,
                y: 0
        };
        var page = {
                width: 0,
                height: 0
        };
        var coords = {
                x: [],
                y: [],
                // p: []
        };
        var elem = {
                hovered: [],
                clicked: []
        };
        var clicked = false;
        var recordingInterval = null;
        var fps = 24;

        var computeAvailableSpace = function() {
            var doc = smt2fn.getPageSize();
            page.width  = doc.width;
            page.height = doc.height;
        };

        computeAvailableSpace();

        var findElement = function(e) {
            if (!e) {
                e = window.event;
            }
            // bind function to widget tracking object
            smt2fn.widget.findDOMElement(e, function(name){
                if (e.type == "mousedown" || e.type == "touchstart") {
                    elem.clicked.push(name);
                } else if (e.type == "mousemove" || e.type == "touchmove") {
                    elem.hovered.push(name);
                }
            });
            // console.log(JSON.stringify(elem)+"\n");
        };

        var getMousePos = function(e) {
            if (!e) {
                var e = window.event;
            }
            var x = 0, y = 0;
            if (e.pageX || e.pageY) {
                x = e.pageX;
                y = e.pageY;
            } else if (e.clientX || e.clientY) {
                x = e.clientX + document.body.scrollLeft + document.documentElement.scrollLeft;
                y = e.clientY + document.body.scrollTop  + document.documentElement.scrollTop;
            }
            // in certain situations the mouse coordinates could be negative values (e.g. Opera)
            if (x < 0 || !x) x = 0;
            if (y < 0 || !y) y = 0;
            
            // coords.x.push(x);
            // coords.y.push(y);
            // coords.p.push(+clicked);
            return {'x': x, 'y': y};
        };


        var onMove = function(e) {
            if (e.touches) {
                e = e.touches[0] || e.targetTouches[0];
            }
            var p = getMousePos.call(this, e);
            coords.x.push(p.x);
            coords.y.push(p.y);
            // findElement.call(this, e);
        };

        var onPress = function(e){
            if (e.touches) {
                e = e.touches[0] || e.targetTouches[0];
            }
            setClick.call(this);
            // findElement.call(this, e);
        };

        var releaseClick = function() {
            clicked = false; 
        };
        var setClick = function() {
            clicked = true;
        };

        document.addEventListener('mousedown', onPress, false);
        document.addEventListener('mousemove', onMove, false);
        document.addEventListener('mouseup', releaseClick, false);
        window.addEventListener('resize', computeAvailableSpace, false);

        var forwardData = function() {
            mirror.forwardData.call(this, page, coords, elem);
        };

        var clearMouseData = function() {
            coords.x = [];
            coords.y = [];
            coords.p = [];
            elem.hovered = [];
            elem.clicked = [];
        };

        var recMouse = function() {
            // store using the UNIPEN format
            // coords.x.push(mouse.x);
            // coords.y.push(mouse.y);
            // coords.p.push(+clicked);
            forwardData();
            clearMouseData();
        };
        var interval = Math.round(1000/fps);
        recordingInterval = window.setInterval(recMouse, interval);                            
                
        return {
                disconnect: function() {
                    window.clearInterval(recordingInterval);
                }
        };
    };

    global.CursorMirrorClient = CursorMirrorClient;
    global.CursorMirror = CursorMirror;

})(this);