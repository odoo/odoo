/** @preserve 
jSignature v2 "${buildDate}" "${commitID}"
Copyright (c) 2012 Willow Systems Corp http://willow-systems.com
Copyright (c) 2010 Brinley Ang http://www.unbolt.net
MIT License <http://www.opensource.org/licenses/mit-license.php> 

*/
;(function() {

var apinamespace = 'jSignature'

/**
Allows one to delay certain eventual action by setting up a timer for it and allowing one to delay it
by "kick"ing it. Sorta like "kick the can down the road"

@public
@class
@param
@returns {Type}
*/
var KickTimerClass = function(time, callback) {
    var timer;
    this.kick = function() {
        clearTimeout(timer);
        timer = setTimeout(
            callback
            , time
        );
    }
    this.clear = function() {
        clearTimeout(timer);
    }
    return this;
}

var PubSubClass = function(context){
    'use strict'
    /*  @preserve 
    -----------------------------------------------------------------------------------------------
    JavaScript PubSub library
    2012 (c) Willow Systems Corp (www.willow-systems.com)
    based on Peter Higgins (dante@dojotoolkit.org)
    Loosely based on Dojo publish/subscribe API, limited in scope. Rewritten blindly.
    Original is (c) Dojo Foundation 2004-2010. Released under either AFL or new BSD, see:
    http://dojofoundation.org/license for more information.
    -----------------------------------------------------------------------------------------------
    */
    this.topics = {};
    // here we choose what will be "this" for the called events.
    // if context is defined, it's context. Else, 'this' is this instance of PubSub
    this.context = context ? context : this;
    /**
     * Allows caller to emit an event and pass arguments to event listeners.
     * @public
     * @function
     * @param topic {String} Name of the channel on which to voice this event
     * @param **arguments Any number of arguments you want to pass to the listeners of this event.
     */
    this.publish = function(topic, arg1, arg2, etc) {
        'use strict'
        if (this.topics[topic]) {
            var currentTopic = this.topics[topic]
            , args = Array.prototype.slice.call(arguments, 1)
            , toremove = []
            , torun = []
            , fn
            , i, l
            , pair;

            for (i = 0, l = currentTopic.length; i < l; i++) {
                pair = currentTopic[i]; // this is a [function, once_flag] array
                fn = pair[0];
                if (pair[1] /* 'run once' flag set */){
                  pair[0] = function(){};
                  toremove.push(i);
                }
                /* don't call the callback right now, it might decide to add or
                 * remove subscribers which will wreak havoc on our index-based
                 * iteration */
                torun.push(fn);
            }
            for (i = 0, l = toremove.length; i < l; i++) {
              currentTopic.splice(toremove[i], 1);
            }
            for (i = 0, l = torun.length; i < l; i++) {
              torun[i].apply(this.context, args);
            }
        }
    }
    /**
     * Allows listener code to subscribe to channel and be called when data is available 
     * @public
     * @function
     * @param topic {String} Name of the channel on which to voice this event
     * @param callback {Function} Executable (function pointer) that will be ran when event is voiced on this channel.
     * @param once {Boolean} (optional. False by default) Flag indicating if the function is to be triggered only once.
     * @returns {Object} A token object that cen be used for unsubscribing.  
     */
    this.subscribe = function(topic, callback, once) {
        'use strict'
        if (!this.topics[topic]) {
            this.topics[topic] = [[callback, once]];
        } else {
            this.topics[topic].push([callback,once]);
        }
        return {
            "topic": topic,
            "callback": callback
        };
    };
    /**
     * Allows listener code to unsubscribe from a channel 
     * @public
     * @function
     * @param token {Object} A token object that was returned by `subscribe` method 
     */
    this.unsubscribe = function(token) {
        if (this.topics[token.topic]) {
            var currentTopic = this.topics[token.topic];
            
            for (var i = 0, l = currentTopic.length; i < l; i++) {
                if (currentTopic[i] && currentTopic[i][0] === token.callback) {
                    currentTopic.splice(i, 1);
                }
            }
        }
    }
}

/// Returns front, back and "decor" colors derived from element (as jQuery obj)
function getColors($e){
    var tmp
    , undef
    , frontcolor = $e.css('color')
    , backcolor
    , e = $e[0];
    
    var toOfDOM = false;
    while(e && !backcolor && !toOfDOM){
        try{
            tmp = $(e).css('background-color');
        } catch (ex) {
            tmp = 'transparent';
        }
        if (tmp !== 'transparent' && tmp !== 'rgba(0, 0, 0, 0)'){
            backcolor = tmp;
        }
        toOfDOM = e.body;
        e = e.parentNode;
    }

    var rgbaregex = /rgb[a]*\((\d+),\s*(\d+),\s*(\d+)/ // modern browsers
    , hexregex = /#([AaBbCcDdEeFf\d]{2})([AaBbCcDdEeFf\d]{2})([AaBbCcDdEeFf\d]{2})/ // IE 8 and less.
    , frontcolorcomponents;

    // Decomposing Front color into R, G, B ints
    tmp = undef;
    tmp = frontcolor.match(rgbaregex);
    if (tmp){
        frontcolorcomponents = {'r':parseInt(tmp[1],10),'g':parseInt(tmp[2],10),'b':parseInt(tmp[3],10)};
    } else {
        tmp = frontcolor.match(hexregex);
        if (tmp) {
            frontcolorcomponents = {'r':parseInt(tmp[1],16),'g':parseInt(tmp[2],16),'b':parseInt(tmp[3],16)};
        }
    }
//      if(!frontcolorcomponents){
//          frontcolorcomponents = {'r':255,'g':255,'b':255}
//      }

    var backcolorcomponents
    // Decomposing back color into R, G, B ints
    if(!backcolor){
        // HIghly unlikely since this means that no background styling was applied to any element from here to top of dom.
        // we'll pick up back color from front color
        if(frontcolorcomponents){
            if (Math.max.apply(null, [frontcolorcomponents.r, frontcolorcomponents.g, frontcolorcomponents.b]) > 127){
                backcolorcomponents = {'r':0,'g':0,'b':0};
            } else {
                backcolorcomponents = {'r':255,'g':255,'b':255};
            }
        } else {
            // arg!!! front color is in format we don't understand (hsl, named colors)
            // Let's just go with white background.
            backcolorcomponents = {'r':255,'g':255,'b':255};
        }
    } else {
        tmp = undef;
        tmp = backcolor.match(rgbaregex);
        if (tmp){
            backcolorcomponents = {'r':parseInt(tmp[1],10),'g':parseInt(tmp[2],10),'b':parseInt(tmp[3],10)};
        } else {
            tmp = backcolor.match(hexregex);
            if (tmp) {
                backcolorcomponents = {'r':parseInt(tmp[1],16),'g':parseInt(tmp[2],16),'b':parseInt(tmp[3],16)};
            }
        }
//          if(!backcolorcomponents){
//              backcolorcomponents = {'r':0,'g':0,'b':0}
//          }
    }
    
    // Deriving Decor color
    // THis is LAZY!!!! Better way would be to use HSL and adjust luminocity. However, that could be an overkill. 
    
    var toRGBfn = function(o){return 'rgb(' + [o.r, o.g, o.b].join(', ') + ')'} 
    , decorcolorcomponents
    , frontcolorbrightness
    , adjusted;
    
    if (frontcolorcomponents && backcolorcomponents){
        var backcolorbrightness = Math.max.apply(null, [frontcolorcomponents.r, frontcolorcomponents.g, frontcolorcomponents.b]);
        
        frontcolorbrightness = Math.max.apply(null, [backcolorcomponents.r, backcolorcomponents.g, backcolorcomponents.b]);
        adjusted = Math.round(frontcolorbrightness + (-1 * (frontcolorbrightness - backcolorbrightness) * 0.75)); // "dimming" the difference between pen and back.
        decorcolorcomponents = {'r':adjusted,'g':adjusted,'b':adjusted}; // always shade of gray
    } else if (frontcolorcomponents) {
        frontcolorbrightness = Math.max.apply(null, [frontcolorcomponents.r, frontcolorcomponents.g, frontcolorcomponents.b]);
        var polarity = +1;
        if (frontcolorbrightness > 127){
            polarity = -1;
        }
        // shifting by 25% (64 points on RGB scale)
        adjusted = Math.round(frontcolorbrightness + (polarity * 96)); // "dimming" the pen's color by 75% to get decor color.
        decorcolorcomponents = {'r':adjusted,'g':adjusted,'b':adjusted}; // always shade of gray
    } else {
        decorcolorcomponents = {'r':191,'g':191,'b':191}; // always shade of gray
    }

    return {
        'color': frontcolor
        , 'background-color': backcolorcomponents? toRGBfn(backcolorcomponents) : backcolor
        , 'decor-color': toRGBfn(decorcolorcomponents)
    };
}

function Vector(x,y){
    this.x = x;
    this.y = y;
    this.reverse = function(){
        return new this.constructor( 
            this.x * -1
            , this.y * -1
        );
    };
    this._length = null;
    this.getLength = function(){
        if (!this._length){
            this._length = Math.sqrt( Math.pow(this.x, 2) + Math.pow(this.y, 2) );
        }
        return this._length;
    };
    
    var polarity = function (e){
        return Math.round(e / Math.abs(e));
    };
    this.resizeTo = function(length){
        // proportionally changes x,y such that the hypotenuse (vector length) is = new length
        if (this.x === 0 && this.y === 0){
            this._length = 0;
        } else if (this.x === 0){
            this._length = length;
            this.y = length * polarity(this.y);
        } else if(this.y === 0){
            this._length = length;
            this.x = length * polarity(this.x);
        } else {
            var proportion = Math.abs(this.y / this.x)
                , x = Math.sqrt(Math.pow(length, 2) / (1 + Math.pow(proportion, 2)))
                , y = proportion * x;
            this._length = length;
            this.x = x * polarity(this.x);
            this.y = y * polarity(this.y);
        }
        return this;
    };
    
    /**
     * Calculates the angle between 'this' vector and another.
     * @public
     * @function
     * @returns {Number} The angle between the two vectors as measured in PI. 
     */
    this.angleTo = function(vectorB) {
        var divisor = this.getLength() * vectorB.getLength();
        if (divisor === 0) {
            return 0;
        } else {
            // JavaScript floating point math is screwed up.
            // because of it, the core of the formula can, on occasion, have values
            // over 1.0 and below -1.0.
            return Math.acos(
                Math.min( 
                    Math.max( 
                        ( this.x * vectorB.x + this.y * vectorB.y ) / divisor
                        , -1.0
                    )
                    , 1.0
                )
            ) / Math.PI;
        }
    };
}

function Point(x,y){
    this.x = x;
    this.y = y;
    
    this.getVectorToCoordinates = function (x, y) {
        return new Vector(x - this.x, y - this.y);
    };
    this.getVectorFromCoordinates = function (x, y) {
        return this.getVectorToCoordinates(x, y).reverse();
    };
    this.getVectorToPoint = function (point) {
        return new Vector(point.x - this.x, point.y - this.y);
    };
    this.getVectorFromPoint = function (point) {
        return this.getVectorToPoint(point).reverse();
    };
}

/*
 * About data structure:
 * We don't store / deal with "pictures" this signature capture code captures "vectors"
 * 
 * We don't store bitmaps. We store "strokes" as arrays of arrays. (Actually, arrays of objects containing arrays of coordinates.
 * 
 * Stroke = mousedown + mousemoved * n (+ mouseup but we don't record that as that was the "end / lack of movement" indicator)
 * 
 * Vectors = not classical vectors where numbers indicated shift relative last position. Our vectors are actually coordinates against top left of canvas.
 *          we could calc the classical vectors, but keeping the the actual coordinates allows us (through Math.max / min) 
 *          to calc the size of resulting drawing very quickly. If we want classical vectors later, we can always get them in backend code.
 * 
 * So, the data structure:
 * 
 * var data = [
 *  { // stroke starts
 *      x : [101, 98, 57, 43] // x points
 *      , y : [1, 23, 65, 87] // y points
 *  } // stroke ends
 *  , { // stroke starts
 *      x : [55, 56, 57, 58] // x points
 *      , y : [101, 97, 54, 4] // y points
 *  } // stroke ends
 *  , { // stroke consisting of just a dot
 *      x : [53] // x points
 *      , y : [151] // y points
 *  } // stroke ends
 * ]
 * 
 * we don't care or store stroke width (it's canvas-size-relative), color, shadow values. These can be added / changed on whim post-capture.
 * 
 */
function DataEngine(storageObject, context, startStrokeFn, addToStrokeFn, endStrokeFn){
    this.data = storageObject; // we expect this to be an instance of Array
    this.context = context;

    if (storageObject.length){
        // we have data to render
        var numofstrokes = storageObject.length
        , stroke
        , numofpoints;
        
        for (var i = 0; i < numofstrokes; i++){
            stroke = storageObject[i];
            numofpoints = stroke.x.length;
            startStrokeFn.call(context, stroke);
            for(var j = 1; j < numofpoints; j++){
                addToStrokeFn.call(context, stroke, j);
            }
            endStrokeFn.call(context, stroke);
        }
    }

    this.changed = function(){};
    
    this.startStrokeFn = startStrokeFn;
    this.addToStrokeFn = addToStrokeFn;
    this.endStrokeFn = endStrokeFn;

    this.inStroke = false;
    
    this._lastPoint = null;
    this._stroke = null;
    this.startStroke = function(point){
        if(point && typeof(point.x) == "number" && typeof(point.y) == "number"){
            this._stroke = {'x':[point.x], 'y':[point.y]};
            this.data.push(this._stroke);
            this._lastPoint = point;
            this.inStroke = true;
            // 'this' does not work same inside setTimeout(
            var stroke = this._stroke 
            , fn = this.startStrokeFn
            , context = this.context;
            setTimeout(
                // some IE's don't support passing args per setTimeout API. Have to create closure every time instead.
                function() {fn.call(context, stroke)}
                , 3
            );
            return point;
        } else {
            return null;
        }
    };
    // that "5" at the very end of this if is important to explain.
    // we do NOT render links between two captured points (in the middle of the stroke) if the distance is shorter than that number.
    // not only do we NOT render it, we also do NOT capture (add) these intermediate points to storage.
    // when clustering of these is too tight, it produces noise on the line, which, because of smoothing, makes lines too curvy.
    // maybe, later, we can expose this as a configurable setting of some sort.
    this.addToStroke = function(point){
        if (this.inStroke && 
            typeof(point.x) === "number" && 
            typeof(point.y) === "number" &&
            // calculates absolute shift in diagonal pixels away from original point
            (Math.abs(point.x - this._lastPoint.x) + Math.abs(point.y - this._lastPoint.y)) > 4
        ){
            var positionInStroke = this._stroke.x.length;
            this._stroke.x.push(point.x);
            this._stroke.y.push(point.y);
            this._lastPoint = point;
            
            var stroke = this._stroke
            , fn = this.addToStrokeFn
            , context = this.context;
            setTimeout(
                // some IE's don't support passing args per setTimeout API. Have to create closure every time instead.
                function() {fn.call(context, stroke, positionInStroke)}
                , 3
            );
            return point;
        } else {
            return null;
        }
    };
    this.endStroke = function(){
        var c = this.inStroke;
        this.inStroke = false;
        this._lastPoint = null;
        if (c){
            var stroke = this._stroke
            , fn = this.endStrokeFn // 'this' does not work same inside setTimeout(
            , context = this.context
            , changedfn = this.changed;
            setTimeout(
                // some IE's don't support passing args per setTimeout API. Have to create closure every time instead.
                function(){
                    fn.call(context, stroke);
                    changedfn.call(context);
                }
                , 3
            );
            return true;
        } else {
            return null;
        }
    };
}

var basicDot = function(ctx, x, y, size){
    var fillStyle = ctx.fillStyle;
    ctx.fillStyle = ctx.strokeStyle;
    ctx.fillRect(x + size / -2 , y + size / -2, size, size);
    ctx.fillStyle = fillStyle;
}
, basicLine = function(ctx, startx, starty, endx, endy){
    ctx.beginPath();
    ctx.moveTo(startx, starty);
    ctx.lineTo(endx, endy);
    ctx.closePath();
    ctx.stroke();
}
, basicCurve = function(ctx, startx, starty, endx, endy, cp1x, cp1y, cp2x, cp2y){
    ctx.beginPath();
    ctx.moveTo(startx, starty);
    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, endx, endy);
    ctx.closePath();
    ctx.stroke();
}
, strokeStartCallback = function(stroke) {
    // this = jSignatureClass instance
    basicDot(this.canvasContext, stroke.x[0], stroke.y[0], this.settings.lineWidth);
}
, strokeAddCallback = function(stroke, positionInStroke){
    // this = jSignatureClass instance

    // Because we are funky this way, here we draw TWO curves.
    // 1. POSSIBLY "this line" - spanning from point right before us, to this latest point.
    // 2. POSSIBLY "prior curve" - spanning from "latest point" to the one before it.
    
    // Why you ask?
    // long lines (ones with many pixels between them) do not look good when they are part of a large curvy stroke.
    // You know, the jaggedy crocodile spine instead of a pretty, smooth curve. Yuck!
    // We want to approximate pretty curves in-place of those ugly lines.
    // To approximate a very nice curve we need to know the direction of line before and after.
    // Hence, on long lines we actually wait for another point beyond it to come back from
    // mousemoved before we draw this curve.
    
    // So for "prior curve" to be calc'ed we need 4 points 
    //  A, B, C, D (we are on D now, A is 3 points in the past.)
    // and 3 lines:
    //  pre-line (from points A to B), 
    //  this line (from points B to C), (we call it "this" because if it was not yet, it's the only one we can draw for sure.) 
    //  post-line (from points C to D) (even through D point is 'current' we don't know how we can draw it yet)
    //
    // Well, actually, we don't need to *know* the point A, just the vector A->B
    var Cpoint = new Point(stroke.x[positionInStroke-1], stroke.y[positionInStroke-1])
        , Dpoint = new Point(stroke.x[positionInStroke], stroke.y[positionInStroke])
        , CDvector = Cpoint.getVectorToPoint(Dpoint);
        
    // Again, we have a chance here to draw TWO things:
    //  BC Curve (only if it's long, because if it was short, it was drawn by previous callback) and 
    //  CD Line (only if it's short)
    
    // So, let's start with BC curve.
    // if there is only 2 points in stroke array, we don't have "history" long enough to have point B, let alone point A.
    // Falling through to drawing line CD is proper, as that's the only line we have points for.
    if(positionInStroke > 1) {
        // we are here when there are at least 3 points in stroke array.
        var Bpoint = new Point(stroke.x[positionInStroke-2], stroke.y[positionInStroke-2])
        , BCvector = Bpoint.getVectorToPoint(Cpoint)
        , ABvector;
        if(BCvector.getLength() > this.lineCurveThreshold){
            // Yey! Pretty curves, here we come!
            if(positionInStroke > 2) {
                // we are here when at least 4 points in stroke array.
                ABvector = (new Point(stroke.x[positionInStroke-3], stroke.y[positionInStroke-3])).getVectorToPoint(Bpoint);
            } else {
                ABvector = new Vector(0,0);
            }

            var minlenfraction = 0.05
            , maxlen = BCvector.getLength() * 0.35
            , ABCangle = BCvector.angleTo(ABvector.reverse())
            , BCDangle = CDvector.angleTo(BCvector.reverse())
            , BCP1vector = new Vector(ABvector.x + BCvector.x, ABvector.y + BCvector.y).resizeTo(
                Math.max(minlenfraction, ABCangle) * maxlen
            )
            , CCP2vector = (new Vector(BCvector.x + CDvector.x, BCvector.y + CDvector.y)).reverse().resizeTo(
                Math.max(minlenfraction, BCDangle) * maxlen
            );
            
            basicCurve(
                this.canvasContext
                , Bpoint.x
                , Bpoint.y
                , Cpoint.x
                , Cpoint.y
                , Bpoint.x + BCP1vector.x
                , Bpoint.y + BCP1vector.y
                , Cpoint.x + CCP2vector.x
                , Cpoint.y + CCP2vector.y
            );
        }
    }
    if(CDvector.getLength() <= this.lineCurveThreshold){
        basicLine(
            this.canvasContext
            , Cpoint.x
            , Cpoint.y
            , Dpoint.x
            , Dpoint.y
        );
    }
}
, strokeEndCallback = function(stroke){
    // this = jSignatureClass instance

    // Here we tidy up things left unfinished in last strokeAddCallback run.

    // What's POTENTIALLY left unfinished there is the curve between the last points
    // in the stroke, if the len of that line is more than lineCurveThreshold
    // If the last line was shorter than lineCurveThreshold, it was drawn there, and there
    // is nothing for us here to do.
    // We can also be called when there is only one point in the stroke (meaning, the 
    // stroke was just a dot), in which case, again, there is nothing for us to do.
                
    // So for "this curve" to be calc'ed we need 3 points 
    //  A, B, C
    // and 2 lines:
    //  pre-line (from points A to B), 
    //  this line (from points B to C) 
    // Well, actually, we don't need to *know* the point A, just the vector A->B
    // so, we really need points B, C and AB vector.
    var positionInStroke = stroke.x.length - 1;
    
    if (positionInStroke > 0){
        // there are at least 2 points in the stroke.we are in business.
        var Cpoint = new Point(stroke.x[positionInStroke], stroke.y[positionInStroke])
            , Bpoint = new Point(stroke.x[positionInStroke-1], stroke.y[positionInStroke-1])
            , BCvector = Bpoint.getVectorToPoint(Cpoint)
            , ABvector;
        if (BCvector.getLength() > this.lineCurveThreshold){
            // yep. This one was left undrawn in prior callback. Have to draw it now.
            if (positionInStroke > 1){
                // we have at least 3 elems in stroke
                ABvector = (new Point(stroke.x[positionInStroke-2], stroke.y[positionInStroke-2])).getVectorToPoint(Bpoint);
                var BCP1vector = new Vector(ABvector.x + BCvector.x, ABvector.y + BCvector.y).resizeTo(BCvector.getLength() / 2);
                basicCurve(
                    this.canvasContext
                    , Bpoint.x
                    , Bpoint.y
                    , Cpoint.x
                    , Cpoint.y
                    , Bpoint.x + BCP1vector.x
                    , Bpoint.y + BCP1vector.y
                    , Cpoint.x
                    , Cpoint.y
                );
            } else {
                // Since there is no AB leg, there is no curve to draw. This line is still "long" but no curve.
                basicLine(
                    this.canvasContext
                    , Bpoint.x
                    , Bpoint.y
                    , Cpoint.x
                    , Cpoint.y
                );
            }
        }
    }
}


/*
var getDataStats = function(){
    var strokecnt = strokes.length
        , stroke
        , pointid
        , pointcnt
        , x, y
        , maxX = Number.NEGATIVE_INFINITY
        , maxY = Number.NEGATIVE_INFINITY
        , minX = Number.POSITIVE_INFINITY
        , minY = Number.POSITIVE_INFINITY
    for(strokeid = 0; strokeid < strokecnt; strokeid++){
        stroke = strokes[strokeid]
        pointcnt = stroke.length
        for(pointid = 0; pointid < pointcnt; pointid++){
            x = stroke.x[pointid]
            y = stroke.y[pointid]
            if (x > maxX){
                maxX = x
            } else if (x < minX) {
                minX = x
            }
            if (y > maxY){
                maxY = y
            } else if (y < minY) {
                minY = y
            }
        }
    }
    return {'maxX': maxX, 'minX': minX, 'maxY': maxY, 'minY': minY}
}
*/

function conditionallyLinkCanvasResizeToWindowResize(jSignatureInstance, settingsWidth, apinamespace, globalEvents){
    'use strict'
    if ( settingsWidth === 'ratio' || settingsWidth.split('')[settingsWidth.length - 1] === '%' ) {
        
        this.eventTokens[apinamespace + '.parentresized'] = globalEvents.subscribe(
            apinamespace + '.parentresized'
            , (function(eventTokens, $parent, originalParentWidth, sizeRatio){
                'use strict'

                return function(){
                    'use strict'

                    var w = $parent.width();
                    if (w !== originalParentWidth) {
                    
                        // UNsubscribing this particular instance of signature pad only.
                        // there is a separate `eventTokens` per each instance of signature pad 
                        for (var key in eventTokens){
                            if (eventTokens.hasOwnProperty(key)) {
                                globalEvents.unsubscribe(eventTokens[key]);
                                delete eventTokens[key];
                            }
                        }

                        var settings = jSignatureInstance.settings;
                        jSignatureInstance.$parent.children().remove();
                        for (var key in jSignatureInstance){
                            if (jSignatureInstance.hasOwnProperty(key)) {
                                delete jSignatureInstance[key];
                            }
                        }
                        
                        // scale data to new signature pad size
                        settings.data = (function(data, scale){
                            var newData = [];
                            var o, i, l, j, m, stroke;
                            for ( i = 0, l = data.length; i < l; i++) {
                                stroke = data[i];
                                
                                o = {'x':[],'y':[]};
                                
                                for ( j = 0, m = stroke.x.length; j < m; j++) {
                                    o.x.push(stroke.x[j] * scale);
                                    o.y.push(stroke.y[j] * scale);
                                }
                            
                                newData.push(o);
                            }
                            return newData;
                        })(
                            settings.data
                            , w * 1.0 / originalParentWidth
                        )
                        
                        $parent[apinamespace](settings);
                    }
                }
            })(
                this.eventTokens
                , this.$parent
                , this.$parent.width()
                , this.canvas.width * 1.0 / this.canvas.height
            )
        )
    }
};


function jSignatureClass(parent, options, instanceExtensions) {

    var $parent = this.$parent = $(parent)
    , eventTokens = this.eventTokens = {}
    , events = this.events = new PubSubClass(this)
    , globalEvents = $.fn[apinamespace]('globalEvents')
    , settings = {
        'width' : 'ratio'
        ,'height' : 'ratio'
        ,'sizeRatio': 4 // only used when height = 'ratio'
        ,'color' : '#000'
        ,'background-color': '#fff'
        ,'decor-color': '#eee'
        ,'lineWidth' : 0
        ,'minFatFingerCompensation' : -10
        ,'showUndoButton': false
        ,'readOnly': false
        ,'data': []
    };
    
    $.extend(settings, getColors($parent));
    if (options) {
        $.extend(settings, options);
    }
    this.settings = settings;

    for (var extensionName in instanceExtensions){
        if (instanceExtensions.hasOwnProperty(extensionName)) {
            instanceExtensions[extensionName].call(this, extensionName);
        }
    }

    this.events.publish(apinamespace+'.initializing');

    // these, when enabled, will hover above the sig area. Hence we append them to DOM before canvas.
    this.$controlbarUpper = (function(){
        var controlbarstyle = 'padding:0 !important; margin:0 !important;'+
            'width: 100% !important; height: 0 !important; -ms-touch-action: none; touch-action: none;'+
            'margin-top:-1em !important; margin-bottom:1em !important;';
        return $('<div style="'+controlbarstyle+'"></div>').appendTo($parent);
    })();

    this.isCanvasEmulator = false; // will be flipped by initializer when needed.
    var canvas = this.canvas = this.initializeCanvas(settings)
    , $canvas = $(canvas);

    this.$controlbarLower = (function(){
        var controlbarstyle = 'padding:0 !important; margin:0 !important;'+
            'width: 100% !important; height: 0 !important; -ms-touch-action: none; touch-action: none;'+
            'margin-top:-1.5em !important; margin-bottom:1.5em !important; position: relative;';
        return $('<div style="'+controlbarstyle+'"></div>').appendTo($parent);
    })();

    this.canvasContext = canvas.getContext("2d");

    // Most of our exposed API will be looking for this:
    $canvas.data(apinamespace + '.this', this);

    settings.lineWidth = (function(defaultLineWidth, canvasWidth){
        if (!defaultLineWidth){
            return Math.max(
                Math.round(canvasWidth / 400) /*+1 pixel for every extra 300px of width.*/
                , 2 /* minimum line width */
            );
        } else {
            return defaultLineWidth;
        }
    })(settings.lineWidth, canvas.width);

    this.lineCurveThreshold = settings.lineWidth * 3;

    // Add custom class if defined
    if(settings.cssclass && $.trim(settings.cssclass) != "") {
        $canvas.addClass(settings.cssclass);
    }

    // used for shifting the drawing point up on touch devices, so one can see the drawing above the finger.
    this.fatFingerCompensation = 0;

    var movementHandlers = (function(jSignatureInstance) {

        //================================
        // mouse down, move, up handlers:

        // shifts - adjustment values in viewport pixels drived from position of canvas on the page
        var shiftX
        , shiftY
        , setStartValues = function(){
            var tos = $(jSignatureInstance.canvas).offset()
            shiftX = tos.left * -1
            shiftY = tos.top * -1
        }
        , getPointFromEvent = function(e) {
            var firstEvent = (e.changedTouches && e.changedTouches.length > 0 ? e.changedTouches[0] : e);
            // All devices i tried report correct coordinates in pageX,Y
            // Android Chrome 2.3.x, 3.1, 3.2., Opera Mobile,  safari iOS 4.x,
            // Windows: Chrome, FF, IE9, Safari
            // None of that scroll shift calc vs screenXY other sigs do is needed.
            // ... oh, yeah, the "fatFinger.." is for tablets so that people see what they draw.
            return new Point(
                Math.round(firstEvent.pageX + shiftX)
                , Math.round(firstEvent.pageY + shiftY) + jSignatureInstance.fatFingerCompensation
            );
        }
        , timer = new KickTimerClass(
            750
            , function() { jSignatureInstance.dataEngine.endStroke(); }
        );

        this.drawEndHandler = function(e) {
            if (!jSignatureInstance.settings.readOnly) {
                try { e.preventDefault(); } catch (ex) {}
                timer.clear();
                jSignatureInstance.dataEngine.endStroke();
            }
        };
        this.drawStartHandler = function(e) {
            if (!jSignatureInstance.settings.readOnly) {
                e.preventDefault();
                // for performance we cache the offsets
                // we recalc these only at the beginning the stroke         
                setStartValues();
                jSignatureInstance.dataEngine.startStroke( getPointFromEvent(e) );
                timer.kick();
            }
        };
        this.drawMoveHandler = function(e) {
            if (!jSignatureInstance.settings.readOnly) {
                e.preventDefault();
                if (!jSignatureInstance.dataEngine.inStroke){
                    return;
                } 
                jSignatureInstance.dataEngine.addToStroke( getPointFromEvent(e) );
                timer.kick();
            }
        };

        return this;

    }).call( {}, this )

    //
    //================================

    ;(function(drawEndHandler, drawStartHandler, drawMoveHandler) {
        var canvas = this.canvas
        , $canvas = $(canvas)
        , undef;
        if (this.isCanvasEmulator){
            $canvas.bind('mousemove.'+apinamespace, drawMoveHandler);
            $canvas.bind('mouseup.'+apinamespace, drawEndHandler);
            $canvas.bind('mousedown.'+apinamespace, drawStartHandler);
        } else {
            canvas.addEventListener('touchstart', function(e) {
                canvas.onmousedown = canvas.onmouseup = canvas.onmousemove = undef;

                this.fatFingerCompensation = (
                    settings.minFatFingerCompensation && 
                    settings.lineWidth * -3 > settings.minFatFingerCompensation
                ) ? settings.lineWidth * -3 : settings.minFatFingerCompensation;

                drawStartHandler(e);

                canvas.addEventListener('touchend', drawEndHandler);
                canvas.addEventListener('touchstart', drawStartHandler);
                canvas.addEventListener('touchmove', drawMoveHandler);
            });
            canvas.addEventListener('mousedown', function(e) {
                canvas.ontouchstart = canvas.ontouchend = canvas.ontouchmove = undef;

                drawStartHandler(e);

                canvas.addEventListener('mousedown', drawStartHandler);
                canvas.addEventListener('mouseup', drawEndHandler);
                canvas.addEventListener('mousemove', drawMoveHandler);
            });
            if (window.navigator.msPointerEnabled) {
                canvas.onmspointerdown = drawStartHandler;
                canvas.onmspointerup = drawEndHandler;
                canvas.onmspointermove = drawMoveHandler;
            }
        }
    }).call( 
        this
        , movementHandlers.drawEndHandler
        , movementHandlers.drawStartHandler
        , movementHandlers.drawMoveHandler
    )

    //=========================================
    // various event handlers

    // on mouseout + mouseup canvas did not know that mouseUP fired. Continued to draw despite mouse UP.
    // it is bettr than
    // $canvas.bind('mouseout', drawEndHandler)
    // because we don't want to break the stroke where user accidentally gets ouside and wants to get back in quickly.
    eventTokens[apinamespace + '.windowmouseup'] = globalEvents.subscribe(
        apinamespace + '.windowmouseup'
        , movementHandlers.drawEndHandler
    );

    this.events.publish(apinamespace+'.attachingEventHandlers');

    // If we have proportional width, we sign up to events broadcasting "window resized" and checking if
    // parent's width changed. If so, we (1) extract settings + data from current signature pad,
    // (2) remove signature pad from parent, and (3) reinit new signature pad at new size with same settings, (rescaled) data.
    conditionallyLinkCanvasResizeToWindowResize.call(
        this
        , this
        , settings.width.toString(10)
        , apinamespace, globalEvents
    );
    
    // end of event handlers.
    // ===============================

    this.resetCanvas(settings.data);

    // resetCanvas renders the data on the screen and fires ONE "change" event
    // if there is data. If you have controls that rely on "change" firing
    // attach them to something that runs before this.resetCanvas, like
    // apinamespace+'.attachingEventHandlers' that fires a bit higher.
    this.events.publish(apinamespace+'.initialized');

    return this;
} // end of initBase

//=========================================================================
// jSignatureClass's methods and supporting fn's

jSignatureClass.prototype.resetCanvas = function(data, dontClear){
    var canvas = this.canvas
    , settings = this.settings
    , ctx = this.canvasContext
    , isCanvasEmulator = this.isCanvasEmulator
    , cw = canvas.width
    , ch = canvas.height;
    
    // preparing colors, drawing area
    if (!dontClear){
        ctx.clearRect(0, 0, cw + 30, ch + 30);
    }

    ctx.shadowColor = ctx.fillStyle = settings['background-color']
    if (isCanvasEmulator){
        // FLashCanvas fills with Black by default, covering up the parent div's background
        // hence we refill 
        ctx.fillRect(0,0,cw + 30, ch + 30);
    }

    ctx.lineWidth = Math.ceil(parseInt(settings.lineWidth, 10));
    ctx.lineCap = ctx.lineJoin = "round";
    
    // signature line
    if (null != settings['decor-color']) {
        ctx.strokeStyle = settings['decor-color'];
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
        var lineoffset = Math.round( ch / 5 );
        basicLine(ctx, lineoffset * 1.5, ch - lineoffset, cw - (lineoffset * 1.5), ch - lineoffset);
    }
    ctx.strokeStyle = settings.color;

    if (!isCanvasEmulator){
        ctx.shadowColor = ctx.strokeStyle;
        ctx.shadowOffsetX = ctx.lineWidth * 0.5;
        ctx.shadowOffsetY = ctx.lineWidth * -0.6;
        ctx.shadowBlur = 0;
    }
    
    // setting up new dataEngine

    if (!data) { data = []; }
    
    var dataEngine = this.dataEngine = new DataEngine(
        data
        , this
        , strokeStartCallback
        , strokeAddCallback
        , strokeEndCallback
    );

    settings.data = data; // onwindowresize handler uses it, i think.
    $(canvas).data(apinamespace+'.data', data)
        .data(apinamespace+'.settings', settings);

    // we fire "change" event on every change in data.
    // setting this up:
    dataEngine.changed = (function(target, events, apinamespace) {
        'use strict'
        return function() {
            events.publish(apinamespace+'.change');
            target.trigger('change');
        }
    })(this.$parent, this.events, apinamespace);
    // let's trigger change on all data reloads
    dataEngine.changed();

    // import filters will be passing this back as indication of "we rendered"
    return true;
};

function initializeCanvasEmulator(canvas){
    if (canvas.getContext){
        return false;
    } else {
        // for cases when jSignature, FlashCanvas is inserted
        // from one window into another (child iframe)
        // 'window' and 'FlashCanvas' may be stuck behind
        // in that other parent window.
        // we need to find it
        var window = canvas.ownerDocument.parentWindow;
        var FC = window.FlashCanvas ?
            canvas.ownerDocument.parentWindow.FlashCanvas :
            (
                typeof FlashCanvas === "undefined" ?
                undefined :
                FlashCanvas
            );

        if (FC) {
            canvas = FC.initElement(canvas);
            
            var zoom = 1;
            // FlashCanvas uses flash which has this annoying habit of NOT scaling with page zoom. 
            // It matches pixel-to-pixel to screen instead.
            // Since we are targeting ONLY IE 7, 8 with FlashCanvas, we will test the zoom only the IE8, IE7 way
            if (window && window.screen && window.screen.deviceXDPI && window.screen.logicalXDPI){
                zoom = window.screen.deviceXDPI * 1.0 / window.screen.logicalXDPI;
            }
            if (zoom !== 1){
                try {
                    // We effectively abuse the brokenness of FlashCanvas and force the flash rendering surface to
                    // occupy larger pixel dimensions than the wrapping, scaled up DIV and Canvas elems.
                    $(canvas).children('object').get(0).resize(Math.ceil(canvas.width * zoom), Math.ceil(canvas.height * zoom));
                    // And by applying "scale" transformation we can talk "browser pixels" to FlashCanvas
                    // and have it translate the "browser pixels" to "screen pixels"
                    canvas.getContext('2d').scale(zoom, zoom);
                    // Note to self: don't reuse Canvas element. Repeated "scale" are cumulative.
                } catch (ex) {}
            }
            return true;
        } else {
            throw new Error("Canvas element does not support 2d context. jSignature cannot proceed.");
        }
    }

}

jSignatureClass.prototype.initializeCanvas = function(settings) {
    // ===========
    // Init + Sizing code

    var canvas = document.createElement('canvas')
    , $canvas = $(canvas);

    // We cannot work with circular dependency
    if (settings.width === settings.height && settings.height === 'ratio') {
        settings.width = '100%';
    }

    $canvas.css({
        'margin': 0,
        'padding': 0,
        'border': 'none',
        'height': settings.height === 'ratio' || !settings.height ? 1 : settings.height.toString(10),
        'width': settings.width === 'ratio' || !settings.width ? 1 : settings.width.toString(10),
        '-ms-touch-action': 'none',
        'touch-action': 'none',
        'background-color': settings['background-color'],
    });

    $canvas.appendTo(this.$parent);

    // we could not do this until canvas is rendered (appended to DOM)
    if (settings.height === 'ratio') {
        $canvas.css(
            'height'
            , Math.round( $canvas.width() / settings.sizeRatio )
        );
    } else if (settings.width === 'ratio') {
        $canvas.css(
            'width'
            , Math.round( $canvas.height() * settings.sizeRatio )
        );
    }

    $canvas.addClass(apinamespace);

    // canvas's drawing area resolution is independent from canvas's size.
    // pixels are just scaled up or down when internal resolution does not
    // match external size. So...

    canvas.width = $canvas.width();
    canvas.height = $canvas.height();
    
    // Special case Sizing code

    this.isCanvasEmulator = initializeCanvasEmulator(canvas);

    // End of Sizing Code
    // ===========

    // normally select preventer would be short, but
    // Canvas emulator on IE does NOT provide value for Event. Hence this convoluted line.
    canvas.onselectstart = function(e){if(e && e.preventDefault){e.preventDefault()}; if(e && e.stopPropagation){e.stopPropagation()}; return false;};

    return canvas;
}


var GlobalJSignatureObjectInitializer = function(window){

    var globalEvents = new PubSubClass();
    
    // common "window resized" event listener.
    // jSignature instances will subscribe to this chanel.
    // to resize themselves when needed.
    ;(function(globalEvents, apinamespace, $, window){
        'use strict'

        var resizetimer
        , runner = function(){
            globalEvents.publish(
                apinamespace + '.parentresized'
            )
        };

        // jSignature knows how to resize its content when its parent is resized
        // window resize is the only way we can catch resize events though...
        $(window).bind('resize.'+apinamespace, function(){
            if (resizetimer) {
                clearTimeout(resizetimer);
            }
            resizetimer = setTimeout( 
                runner
                , 500
            );
        })
        // when mouse exists canvas element and "up"s outside, we cannot catch it with
        // callbacks attached to canvas. This catches it outside.
        .bind('mouseup.'+apinamespace, function(e){
            globalEvents.publish(
                apinamespace + '.windowmouseup'
            )
        });

    })(globalEvents, apinamespace, $, window)

    var jSignatureInstanceExtensions = {
        /*
        'exampleExtension':function(extensionName){
            // we are called very early in instance's life.
            // right after the settings are resolved and 
            // jSignatureInstance.events is created 
            // and right before first ("jSignature.initializing") event is called.
            // You don't really need to manupilate 
            // jSignatureInstance directly, just attach
            // a bunch of events to jSignatureInstance.events
            // (look at the source of jSignatureClass to see when these fire)
            // and your special pieces of code will attach by themselves.

            // this function runs every time a new instance is set up.
            // this means every var you create will live only for one instance
            // unless you attach it to something outside, like "window."
            // and pick it up later from there.

            // when globalEvents' events fire, 'this' is globalEvents object
            // when jSignatureInstance's events fire, 'this' is jSignatureInstance

            // Here,
            // this = is new jSignatureClass's instance.

            // The way you COULD approch setting this up is:
            // if you have multistep set up, attach event to "jSignature.initializing"
            // that attaches other events to be fired further lower the init stream.
            // Or, if you know for sure you rely on only one jSignatureInstance's event,
            // just attach to it directly

            this.events.subscribe(
                // name of the event
                apinamespace + '.initializing'
                // event handlers, can pass args too, but in majority of cases,
                // 'this' which is jSignatureClass object instance pointer is enough to get by.
                , function(){
                    if (this.settings.hasOwnProperty('non-existent setting category?')) {
                        console.log(extensionName + ' is here')
                    }
                }
            )
        }
        */
    };

    var exportplugins = {
        'default':function(data){return this.toDataURL()}
        , 'native':function(data){return data}
        , 'image':function(data){
            /*this = canvas elem */
            var imagestring = this.toDataURL();
            
            if (typeof imagestring === 'string' && 
                imagestring.length > 4 && 
                imagestring.slice(0,5) === 'data:' &&
                imagestring.indexOf(',') !== -1){
                
                var splitterpos = imagestring.indexOf(',');

                return [
                    imagestring.slice(5, splitterpos)
                    , imagestring.substr(splitterpos + 1)
                ];
            }
            return [];
        }
    };

    // will be part of "importplugins"
    function _renderImageOnCanvas( data, formattype, rerendercallable ) {
        'use strict'
        // #1. Do NOT rely on this. No worky on IE 
        //   (url max len + lack of base64 decoder + possibly other issues)
        // #2. This does NOT affect what is captured as "signature" as far as vector data is 
        // concerned. This is treated same as "signature line" - i.e. completely ignored
        // the only time you see imported image data exported is if you export as image.

        // we do NOT call rerendercallable here (unlike in other import plugins)
        // because importing image does absolutely nothing to the underlying vector data storage
        // This could be a way to "import" old signatures stored as images
        // This could also be a way to import extra decor into signature area.
        
        var img = new Image()
        // this = Canvas DOM elem. Not jQuery object. Not Canvas's parent div.
        , c = this;

        img.onload = function () {
            var ctx = c.getContext("2d");
            var oldShadowColor = ctx.shadowColor;
            ctx.shadowColor = "transparent";
            ctx.drawImage( 
                img, 0, 0
                , ( img.width < c.width) ? img.width : c.width
                , ( img.height < c.height) ? img.height : c.height
            );
            ctx.shadowColor = oldShadowColor;
        };

        img.src = 'data:' + formattype + ',' + data;
    }

    var importplugins = {
        'native':function(data, formattype, rerendercallable){
            // we expect data as Array of objects of arrays here - whatever 'default' EXPORT plugin spits out.
            // returning Truthy to indicate we are good, all updated.
            rerendercallable( data );
        }
        , 'image': _renderImageOnCanvas
        , 'image/png;base64': _renderImageOnCanvas
        , 'image/jpeg;base64': _renderImageOnCanvas
        , 'image/jpg;base64': _renderImageOnCanvas
    };

    function _clearDrawingArea( data, dontClear ) {
        this.find('canvas.'+apinamespace)
            .add(this.filter('canvas.'+apinamespace))
            .data(apinamespace+'.this').resetCanvas( data, dontClear );
        return this;
    }

    function _setDrawingData( data, formattype ) {
        var undef;

        if (formattype === undef && typeof data === 'string' && data.substr(0,5) === 'data:') {
            formattype = data.slice(5).split(',')[0];
            // 5 chars of "data:" + mimetype len + 1 "," char = all skipped.
            data = data.slice(6 + formattype.length);
            if (formattype === data) {
                return;
            }
        }

        var $canvas = this.find('canvas.'+apinamespace).add(this.filter('canvas.'+apinamespace));

        if (!importplugins.hasOwnProperty(formattype)) {
            throw new Error(apinamespace + " is unable to find import plugin with for format '"+ String(formattype) +"'");
        } else if ($canvas.length !== 0) {
            importplugins[formattype].call(
                $canvas[0]
                , data
                , formattype
                , (function(jSignatureInstance){ 
                    return function(){ return jSignatureInstance.resetCanvas.apply(jSignatureInstance, arguments) }
                })($canvas.data(apinamespace+'.this'))
            );
        }

        return this;
    }

    var elementIsOrphan = function(e){
        var topOfDOM = false;
        e = e.parentNode;
        while (e && !topOfDOM){
            topOfDOM = e.body;
            e = e.parentNode;
        }
        return !topOfDOM;
    }

    //These are exposed as methods under $obj.jSignature('methodname', *args)
    var plugins = {'export':exportplugins, 'import':importplugins, 'instance': jSignatureInstanceExtensions}
    , methods = {
        'init' : function( options ) {
            return this.each( function() {
                if (!elementIsOrphan(this)) {
                    new jSignatureClass(this, options, jSignatureInstanceExtensions);
                }
            })
        }
        , 'getSettings' : function() {
            return this.find('canvas.'+apinamespace)
                .add(this.filter('canvas.'+apinamespace))
                .data(apinamespace+'.this').settings;
        }
        , 'isModified' : function() {
            return this.find('canvas.'+apinamespace)
                .add(this.filter('canvas.'+apinamespace))
                .data(apinamespace+'.this')
                .dataEngine
                ._stroke !== null;
        }
        , 'updateSetting' : function(param, val, forFuture) {
            var $canvas = this.find('canvas.'+apinamespace)
                            .add(this.filter('canvas.'+apinamespace))
                            .data(apinamespace+'.this');
            $canvas.settings[param] = val;
            $canvas.resetCanvas(( forFuture ? null : $canvas.settings.data ), true);
            return $canvas.settings[param];
        }
        // around since v1
        , 'clear' : _clearDrawingArea
        // was mistakenly introduced instead of 'clear' in v2
        , 'reset' : _clearDrawingArea
        , 'addPlugin' : function(pluginType, pluginName, callable){
            if (plugins.hasOwnProperty(pluginType)){
                plugins[pluginType][pluginName] = callable;
            }
            return this;
        }
        , 'listPlugins' : function(pluginType){
            var answer = [];
            if (plugins.hasOwnProperty(pluginType)){
                var o = plugins[pluginType];
                for (var k in o){
                    if (o.hasOwnProperty(k)){
                        answer.push(k);
                    }
                }
            }
            return answer;
        }
        , 'getData' : function( formattype ) {
            var undef, $canvas=this.find('canvas.'+apinamespace).add(this.filter('canvas.'+apinamespace));
            if (formattype === undef) {
                formattype = 'default';
            }
            if ($canvas.length !== 0 && exportplugins.hasOwnProperty(formattype)){              
                return exportplugins[formattype].call(
                    $canvas.get(0) // canvas dom elem
                    , $canvas.data(apinamespace+'.data') // raw signature data as array of objects of arrays
                    , $canvas.data(apinamespace+'.settings')
                );
            }
        }
        // around since v1. Took only one arg - data-url-formatted string with (likely png of) signature image
        , 'importData' : _setDrawingData
        // was mistakenly introduced instead of 'importData' in v2
        , 'setData' : _setDrawingData
        // this is one and same instance for all jSignature.
        , 'globalEvents' : function(){return globalEvents}
        , 'disable' : function() {
            this.find("input").attr("disabled", 1);
            this.find('canvas.'+apinamespace)
                .addClass("disabled")
                .data(apinamespace+'.this')
                .settings
                .readOnly=true;
        }
        , 'enable' : function() {
            this.find("input").removeAttr("disabled");
            this.find('canvas.'+apinamespace)
                .removeClass("disabled")
                .data(apinamespace+'.this')
                .settings
                .readOnly=false;
        }
        // there will be a separate one for each jSignature instance.
        , 'events' : function() {
            return this.find('canvas.'+apinamespace)
                    .add(this.filter('canvas.'+apinamespace))
                    .data(apinamespace+'.this').events;
        }
    } // end of methods declaration.
    
    $.fn[apinamespace] = function(method) {
        'use strict'
        if ( !method || typeof method === 'object' ) {
            return methods.init.apply( this, arguments );
        } else if ( typeof method === 'string' && methods[method] ) {
            return methods[method].apply( this, Array.prototype.slice.call( arguments, 1 ));
        } else {
            $.error( 'Method ' +  String(method) + ' does not exist on jQuery.' + apinamespace );
        }
    }

} // end of GlobalJSignatureObjectInitializer

GlobalJSignatureObjectInitializer(window)

})();
